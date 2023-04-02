import openai
import re

from .utility import Utility


# ChatGPTとやり取りするためのクラス
class ChatGpt:
    def __init__(self, api_key: str) -> None:
        openai.api_key = api_key
        self.messages: list[dict[str, str]] = []

    # APIのレスポンスからメッセージを取得する
    def __get_content(self, response: dict) -> str:
        return response["choices"][0]["message"]["content"]

    # 前提となる初期メッセージを設定する
    def set_message_init(self, content: str) -> None:
        self.messages = [{"role": "system", "content": content}]

    # オブジェクトからroleとcontentを取得し、messagesに格納する
    def set_messages_past(self, objects: list[dict[str, str]]) -> None:
        is_include_role = False
        is_include_content = False

        # objectsにキーroleとcontentが存在しない場合はエラーを発生させる
        for item in objects:
            if "role" in item:
                is_include_role = True
            if "content" in item:
                is_include_content = True

        if not (is_include_role and is_include_content):
            raise ValueError("引数objectsにキーroleとcontentが存在しません。")

        self.messages = []

        # messagesに格納する
        for items in objects:
            self.messages.append(
                {"role": items["role"], "content": items["content"]}
            )

    # ユーザーのメッセージを追加する
    def add_message_user(
            self, content: str, max_content_length: int = 0
    ) -> None:
        # contentの長さがmax_content_lengthを超えている場合はエラーを発生させる
        if max_content_length > 0 and len(content) > max_content_length:
            raise ValueError(
                f"引数contentの長さは{max_content_length}文字以下にしてください。"
            )
        self.messages.append({"role": "user", "content": content})

    # メッセージを圧縮する
    def compress_message(self) -> None:
        role_first = self.messages[0]["role"]
        role_second = self.messages[1]["role"]
        role_last = self.messages[-1]["role"]

        if not (
            role_first == "system" and
            role_second == "user" and
            role_last == "assistant"
        ):
            raise ValueError("messagesの順番が不正です。")

        self.messages = [self.messages[0], self.messages[1], self.messages[-1]]

    # メッセージを送信する
    def send_message(self, temperature: float, max_count: int = 0) -> None:
        response = None
        user_message_count = 0

        # ユーザーのメッセージの数を取得する
        for message in self.messages:
            if message["role"] == "user":
                user_message_count += 1

        # 引数の値が0.0以上1.0以下でない場合はエラーを発生させる
        if temperature < 0.0 or temperature > 1.0:
            raise ValueError("引数temperatureは0.0以上1.0以下の値を指定してください。")
        elif max_count > 0 and user_message_count > max_count:
            raise ValueError(
                f"ユーザーのメッセージの数は{max_count}以下にしてください。"
            )
        # APIへのリクエストを送信する
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=temperature,
            messages=self.messages
        )
        # ChatGPTからの返答をmessagesに追加する
        self.messages.append(
            {"role": "assistant", "content": self.__get_content(response)}
        )

    # ChatGPTの返答を取得する
    def get_content_assistant(self) -> str:
        return self.messages[-1]["content"]

    # ChatGPTの返答からjavascriptのソースコードをコメント、改行コード付きで抽出する
    def get_source_code_javascript_with_comment(self) -> str:
        # 正規表現パターンを設定する
        pattern = (
            r"```javascript\n(.*?)\n```"
            if r"```javascript" in self.get_content_assistant()
            else r"```\n(.*?)\n```"
        )
        # javascriptのソースコードを抽出する
        source_code = re.search(
            pattern, self.get_content_assistant(), re.DOTALL
        ).group(1)

        return source_code

    # ChatGPTの返答からjavascriptのソースコードを抽出する
    def get_source_code_javascript(self) -> str:
        # javascriptのソースコードをコメント、改行コード付きで抽出する
        source_code = self.get_source_code_javascript_with_comment()
        # コメントを削除する
        source_code = re.sub(
            r"(?<!:)//.*?$|\/\*.*?\*\/",
            "",
            source_code,
            flags=re.DOTALL | re.MULTILINE
        )
        # 改行コードを削除する
        source_code = source_code.replace("\n", "")

        return source_code

    # javascriptのソースコードでimportされているモジュールを抽出する
    def get_import_modules(self) -> list[str]:
        import_modules = []

        # ソースコードを";"で分割し、配列にする→ループ
        for item in self.get_source_code_javascript().split(";"):
            # 両端の空白を削除する
            sentence = item.strip()
            import_module = ""

            # 最初の6文字が"import"でない場合は、処理を抜ける
            if sentence[:6] != "import":
                break

            # importとfromの間を取得する
            import_module = sentence[7:sentence.find("from")].strip()
            # "*"、" as "、"{"、"}"を削除し、全ての空白を削除する
            import_module = Utility.remove_chars(
                import_module, ["*", " as ", "{", "}", " "])
            # ","が含まれる場合は","で分割し、ng_import_modulesに追加する
            import_modules.extend(
                import_module.split(",") if "," in import_module else [
                    import_module]
            )
        return import_modules

    # javascriptのソースコードにNGワードが含まれているか確認し、含まれている場合はそのNGワードを返す
    def check_ng_words(self, ng_words: list[str]) -> list[str]:
        # javascriptのソースコードを取得する
        source_code = self.get_source_code_javascript()
        results = []

        # NGワードが含まれているか確認する
        for ng_word in ng_words:
            if ng_word in source_code:
                results.append(ng_word)

        return results

    # javascriptのソースコードから、シングルクォートで囲まれたURL（https://~, http://~）を抽出する
    def get_urls(self) -> list[str]:
        # javascriptのソースコードを取得する
        source_code = self.get_source_code_javascript()
        # 正規表現パターンを設定する
        pattern = r"'(https?://[\w/:%#\$&\?\(\)~\.=\+\-]+)'"

        return re.findall(pattern, source_code)
