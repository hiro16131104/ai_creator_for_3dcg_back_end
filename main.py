from flask import Flask, request, jsonify, Response
from werkzeug.exceptions import NotFound, BadRequest, InternalServerError

from models.app_setting import AppSetting
from models.utility import Utility
from models.chat_gpt import ChatGpt
from models.file_access import FileAccess


# 共通変数（定数）の定義
PATH_CONFIG_FILE = "./appconfig.json"
APP_CONFIG = FileAccess(PATH_CONFIG_FILE).read_json_file()
SECRET = FileAccess(APP_CONFIG["filePath"]["secret"]).read_json_file()
RETRY_COUNT = APP_CONFIG["chatGpt"]["sendingMessage"]["retryCount"]

# Flaskアプリのインスタンスを作成
app = Flask(__name__)
# アプリの初期設定
AppSetting.set_config(app, PATH_CONFIG_FILE)
AppSetting.allow_cors(app)
AppSetting.limit_request(app, PATH_CONFIG_FILE)


# 接続テスト用
@app.route("/", methods=["GET"])
def index() -> str:
    return "接続テストOK。このURLは有効です。"


# ChatGPTに最初のメッセージを送信する
@app.route("/sendFirstMessage", methods=["POST"])
def send_first_message() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    content = request.form["content"]
    # 日付+16桁ランダムな文字列をuser_idとする
    user_id = f"{Utility.get_date_str()}{Utility.generate_random_string(16)}"
    # 設定ファイルからAPIキーを取得する
    chat_gpt = ChatGpt(SECRET["apiKey"]["openAi"])
    message_user = ""

    # ChatGPTに送信する初期メッセージを設定する
    chat_gpt.set_message_init(
        "`Three.js`を使って完全なjavascriptのコードを書いてください。"
    )
    # ユーザーメッセージを作成する
    message_user = (
        f"{content}`を描いてください。\n" +
        "ただし、以下のコーディングルールを遵守してください。\n" +
        "・import文から始めてください。\n" +
        "・`html`の`body`には、何もタグが記述されていないと仮定する。\n" +
        "・生成した`canvas`は`document.body`に追加する。"
    )
    # ChatGPTに送信するメッセージを設定する
    chat_gpt.add_message_user(
        message_user,
        APP_CONFIG["chatGpt"]["sendingMessage"]["maxContentLength"]
    )
    # ChatGPTにメッセージを送信する
    chat_gpt.send_message(1.0)

    for i in range(RETRY_COUNT):
        # ChatGPTからの返答に使用できないモジュールやクラス、無効なURLが含まれている場合、
        # 追加のメッセージを作成する
        message_user = make_additional_message(chat_gpt)

        if message_user:
            # ChatGPTに送信するメッセージを設定する
            chat_gpt.add_message_user(message_user)
            # ChatGPTにメッセージを送信する
            chat_gpt.send_message(1.0)
        else:
            break

    # ChatGPTとのやりとりをテーブルに保存する
    TableMessage.insert_records(user_id, chat_gpt.messages)

    # user_idとソースコードを返す
    return jsonify({
        "userId": user_id,
        "content": chat_gpt.get_source_code_javascript_with_comment(),
        "sourceCode": chat_gpt.get_source_code_javascript()
    })


# ChatGPTに2回目以降のメッセージを送信する
@app.route("/sendMessage", methods=["POST"])
def send_message() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    user_id = request.form["userId"]
    content = request.form["content"]
    # 設定ファイルからAPIキーと送信メッセージの設定を取得する
    chat_gpt = ChatGpt(SECRET["apiKey"]["openAi"])
    setting = APP_CONFIG["chatGpt"]["sendingMessage"]
    # テーブルからレコードを取得する
    records = TableMessage.select_records(user_id)
    count_record_user = 0

    # レコードが存在しない場合はエラーを返す
    if len(records) == 0:
        raise NotFound("レコードが存在しません。")

    # ユーザーのメッセージの送信回数を数える
    for record in records:
        if record["role"] == "user":
            count_record_user += 1

    # ユーザーのメッセージの送信回数が上限に達している場合はエラーを返す
    if count_record_user >= setting["maxCount"]:
        raise BadRequest("メッセージの送信回数が上限に達しました。")

    # レコードをChatGPTクラスに渡し、メッセージを圧縮する
    chat_gpt.set_messages_past(records)
    chat_gpt.compress_message()
    # ChatGPTに送信するメッセージを追加し、送信する
    chat_gpt.add_message_user(
        f"{content}\nただし、前述したコーディングルールは遵守してください。",
        setting["maxContentLength"]
    )
    chat_gpt.send_message(1.0, setting["maxCount"])
    # ChatGPTとのやりとりの最後の2件をテーブルに保存する
    TableMessage.insert_records(user_id, chat_gpt.messages[-2:])

    for i in range(RETRY_COUNT):
        # ChatGPTからの返答に使用できないモジュールやクラス、無効なURLが含まれている場合、
        # 追加のメッセージを作成する
        message_user = make_additional_message(chat_gpt)

        if message_user:
            # 再度テーブルからレコードを取得する
            records = TableMessage.select_records(user_id)
            chat_gpt = ChatGpt(SECRET["apiKey"]["openAi"])
            # レコードをChatGPTクラスに渡す→メッセージを圧縮する→メッセージを追加する
            chat_gpt.set_messages_past(records)
            chat_gpt.compress_message()
            chat_gpt.add_message_user(message_user)
            # ChatGPTにメッセージを送信する
            chat_gpt.send_message(1.0)
            # ChatGPTとのやりとりの最後の2件をテーブルに保存する
            TableMessage.insert_records(user_id, chat_gpt.messages[-2:])
        else:
            break

    # ソースコードを返す
    return jsonify({
        "userId": user_id,
        "content": chat_gpt.get_source_code_javascript_with_comment(),
        "sourceCode": chat_gpt.get_source_code_javascript()
    })


# ChatGPTから受け取ったソースコードを再度取得する
@app.route("/getLastSourceCode", methods=["GET"])
def get_last_source_code() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    user_id = request.args.get("userId")
    # テーブルからレコードを取得する
    records = TableMessage.select_records(user_id)
    chat_gpt = ChatGpt("")

    # レコードが存在しない場合はエラーを返す
    if len(records) == 0:
        raise NotFound("レコードが存在しません。")

    # レコードをChatGPTクラスに渡す
    chat_gpt.set_messages_past(records)

    # ソースコードを返す
    return jsonify({
        "userId": user_id,
        "content": chat_gpt.get_source_code_javascript_with_comment(),
        "sourceCode": chat_gpt.get_source_code_javascript()
    })


# DynamoDBにテーブルを作成する
@app.route("/createTable", methods=["GET"])
def create_table() -> Response:
    from models.table_message import TableMessage

    # テーブルが存在しない場合は作成する
    if TableMessage.exists():
        return jsonify({"message": "テーブルは既に存在しています。"})
    else:
        TableMessage.create_table()

        return jsonify({"message": "テーブルを作成しました。"})


# テーブルのレコードを1件追加する
@app.route("/insertRecord", methods=["POST"])
def insert_record() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    user_id = request.form["userId"]
    role = request.form["role"]
    content = request.form["content"]

    # レコードの追加
    TableMessage.insert_record(user_id, role, content)

    return jsonify({"message": "レコードを1件追加しました。"})


# user_idを指定して、テーブルのレコードを削除する
@app.route("/deleteRecord/<user_id>", methods=["DELETE"])
def delete_record(user_id: str) -> Response:
    from models.table_message import TableMessage

    # レコードの削除
    count_records = TableMessage.delete_record(user_id)

    return jsonify({"message": f"レコードを{count_records}件削除しました。"})


# テーブルのレコードを全件削除する
@app.route("/deleteAllRecords", methods=["POST"])
def delete_all_records() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    password = request.form["password"]
    # 削除したレコード件数
    count_records = 0

    # パスワードが不正である場合は処理を中断する
    if password != SECRET["password"]["database"]:
        raise BadRequest("パスワードが不正です。")

    # レコードの削除
    count_records = TableMessage.delete_all_records()

    return jsonify({"message": f"レコードを{count_records}件削除しました。"})


# user_idを指定して、テーブルのレコードを取得する
@app.route("/selectRecords", methods=["GET"])
def select_records() -> Response:
    from models.table_message import TableMessage

    # リクエストの受取り
    user_id = request.args.get("userId")
    # レコードの取得
    records = TableMessage.select_records(user_id)

    return jsonify({"records": records})


# テーブルに登録されているuser_idを取得する（重複なし）
@app.route("/countUserId", methods=["GET"])
def count_user_id() -> Response:
    from models.table_message import TableMessage

    return jsonify({"count": TableMessage.count_user_id()})


# エラーが発生したとき処理
@app.errorhandler(BadRequest)
@app.errorhandler(NotFound)
@app.errorhandler(InternalServerError)
def error_handler(error) -> tuple[Response, int]:
    print(error)

    return jsonify({
        "error": {"name": error.name, "description": error.description}
    }), error.code


# その他のエラーが発生したとき処理
@app.errorhandler(Exception)
def error_handler_other(error) -> tuple[Response, int]:
    print(error)

    return error_handler(InternalServerError("サーバー内部でエラーが発生しました。"))


# 使用できないモジュールやクラス、無効なURLが含まれている場合、メッセージを作成する
def make_additional_message(chat_gpt: ChatGpt) -> str:
    IMPORTABLE_MODULES = APP_CONFIG["chatGpt"]["receivingMessage"]["importableModules"]
    WORDS = APP_CONFIG["chatGpt"]["receivingMessage"]["words"]
    # importされているモジュールを抽出する
    import_modules = chat_gpt.get_import_modules()
    # 共通変数（定数）WORDSに含まれるNGワードを抽出する
    ng_words = chat_gpt.check_ng_words(list(map(lambda x: x["NG"], WORDS)))
    # 無効なURLを抽出する
    invalid_urls = list(filter(
        lambda x: not Utility.validate_url(x),
        chat_gpt.get_urls()
    ))
    message_user = ""

    # import_modulesの要素から使用可能なモジュールの名称を削除する
    for module in import_modules:
        if module in IMPORTABLE_MODULES:
            import_modules.remove(module)

    # 使用できないモジュールやクラスが含まれている場合、ChatGPTに修正を依頼する
    if len(import_modules + ng_words + invalid_urls) > 0:
        message_user = "以下のルールを加えて、コードを書き直してください。"

        # 使用できないモジュールが含まれている場合
        if len(import_modules) > 0:
            # メッセージを追加する
            message_user += f"・{','.join(import_modules)}は使用しない。"

        # 使用できないクラスが含まれている場合
        if len(ng_words) > 0:
            # 使用できる類似クラスを取得する
            ok_words = list(filter(lambda x: x["NG"] in ng_words, WORDS))

            # メッセージ追加する
            for ng_word, ok_word in zip(ng_words, ok_words):
                message_user += f"・{ng_word}の代わりに{ok_word}を使用する。"

        # 無効なURLが含まれている場合
        if len(invalid_urls) > 0:
            message_user += "・テクスチャは使用しない。"

    return message_user


# Flaskアプリの起動
if __name__ == ("__main__"):
    # localhost以外からのアクセスを許可
    app.run(host="0.0.0.0", port=5050, threaded=True)
