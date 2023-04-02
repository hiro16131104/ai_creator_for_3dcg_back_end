import string
import random
import requests
from datetime import datetime


# インスタンス化せずに使用できるメソッドを集約したクラス
class Utility:
    # 指定した桁数のランダムな文字列を生成する
    @classmethod
    def generate_random_string(cls, length) -> str:
        letters_and_digits = string.ascii_letters + string.digits
        result = ""

        for _ in range(length):
            result += random.choice(letters_and_digits)

        return result

    # "yyyy-mm-dd"形式で日付を取得する
    @classmethod
    def get_date_str(cls) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # 文字列から指定した文字を削除する
    @classmethod
    def remove_chars(self, sentence: str, chars: list[str]) -> str:
        result = sentence

        for char in chars:
            result = result.replace(char, "")

        return result

    # URLが有効であるか確認する
    @classmethod
    def validate_url(cls, url: str) -> bool:
        # HEADリクエストを送信し、ステータスコードが200以上400未満であれば有効とする
        try:  
            response = requests.head(url, timeout=5)
            # 200番代のステータスコードであれば有効とする
            return response.status_code // 100 == 2
        # タイムアウトや接続エラーが発生した場合は、無効とみなす
        except requests.RequestException:
            return False