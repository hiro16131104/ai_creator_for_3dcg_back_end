from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .file_access import FileAccess


# Flaskアプリの初期設定を行うためのクラス
class AppSetting:
    # Flaskインスタンスのconfig変数を設定する
    @classmethod
    def set_config(cls, app: Flask, path_config_file: str) -> None:
        # 設定ファイルから情報を取得する
        file_access = FileAccess(path_config_file)
        environment = file_access.read_json_file()["environment"]["value"]
        dict_config = file_access.read_json_file()["config"][environment]

        app.config["ENV"] = environment
        app.config["DEBUG"] = dict_config["debug"]
        app.config["TESTING"] = dict_config["testing"]
        app.config["JSON_AS_ASCII"] = dict_config["jsonAsAscii"]
        app.config["MAX_CONTENT_LENGTH"] = dict_config["maxContentLength"]

    # サーバーを跨いでのリクエストを許可する
    @classmethod
    def allow_cors(cls, app: Flask) -> CORS:
        return CORS(app)

    # リクエストの頻度を制限する
    @classmethod
    def limit_request(cls, app: Flask, path_config_file: str) -> Limiter:
        # 設定ファイルから情報を取得する
        file_access = FileAccess(path_config_file)
        environment = file_access.read_json_file()["environment"]["value"]
        limit = file_access.read_json_file()["limit"][environment]

        return Limiter(get_remote_address, app=app, default_limits=[limit])
