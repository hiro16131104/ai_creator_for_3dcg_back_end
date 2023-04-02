import json


# ファイルにアクセスするためのクラス
class FileAccess:
    def __init__(self, file_path: str, encoding: str = "utf-8") -> None:
        # ファイルの相対パス
        self.file_path = file_path
        # 文字コード
        self.encoding = encoding

    # jsonファイルを読み込む
    def read_json_file(self) -> dict:
        with open(self.file_path, "r", encoding=self.encoding) as file:
            return json.loads(file.read())

    # jsonファイルに書き込む（洗い替え）
    def write_json_file(self, json_data: dict) -> None:
        with open(self.file_path, "w", encoding=self.encoding) as file:
            json.dump(json_data, file, indent=4, ensure_ascii=False)
