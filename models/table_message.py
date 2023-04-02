from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute,
    NumberAttribute,
    UTCDateTimeAttribute
)
from datetime import datetime
from main import APP_CONFIG


IS_DEV = APP_CONFIG["environment"]["value"] == "development"


# ChatGPTとのやり取りを保存するテーブル
class TableMessage(Model):
    # テーブルの基本情報
    class Meta:
        table_name = f"Generating3dcg-Message{'-dev' if IS_DEV else ''}"
        # 東京リージョン
        region = "ap-northeast-1"
        primary_key = "id"
        # リード・ライトの単位
        read_capacity_units = 5
        write_capacity_units = 5
        # host = "http://localhost:5050"

    # 列の定義
    id = NumberAttribute(hash_key=True, null=False)
    user_id = UnicodeAttribute(null=False)
    role = UnicodeAttribute(null=False)
    content = UnicodeAttribute(null=False)
    created_at = UTCDateTimeAttribute(null=False, default=datetime.now())

    # id列の最大値を取得する
    @classmethod
    def __get_max_id(cls) -> int:
        max_id = 0

        for item in cls.scan():
            if item.id > max_id:
                max_id = item.id

        return max_id

    # レコードを追加する
    @classmethod
    def insert_record(cls, user_id: str, role: str, content: str) -> None:
        # id列の最大値を取得
        max_id = cls.__get_max_id()
        # レコードを追加
        record = cls(
            id=max_id+1,
            user_id=user_id,
            role=role,
            content=content
        )
        record.save()

    # レコードを複数追加する
    @classmethod
    def insert_records(
        cls, user_id: str, messages: list[dict[str, str]]
    ) -> None:
        # id列の最大値を取得
        max_id = cls.__get_max_id()

        # レコードを1件ずつ追加
        for message in messages:
            # アンパック代入
            role, content = message.values()
            # レコードを追加
            record = cls(
                id=max_id+1,
                user_id=user_id,
                role=role,
                content=content
            )
            record.save()
            # id列の最大値を更新
            max_id += 1

    # レコードを削除する
    @classmethod
    def delete_record(cls, user_id: str) -> int:
        # 削除したレコード件数
        count = 0

        # user_idが一致するレコードを削除
        for item in cls.scan(cls.user_id == user_id):
            item.delete()
            count += 1

        return count

    # レコードを全件削除する
    @classmethod
    def delete_all_records(cls) -> int:
        # 削除したレコード件数
        count = 0

        # レコードを削除
        for item in cls.scan():
            item.delete()
            count += 1

        return count

    # レコードを検索する
    @classmethod
    def select_records(cls, user_id: str) -> list[dict[str, any]]:
        # 検索結果
        records: list[dict[str, any]] = []

        # レコードを検索し、listに格納
        for item in cls.scan(cls.user_id == user_id):
            records.append({
                "id": item.id,
                "user_id": item.user_id,
                "role": item.role,
                "content": item.content,
                "created_at": item.created_at
            })
        # id列の昇順にソート
        records.sort(key=lambda x: x["id"])

        return records

    # user_idの件数を取得する（重複を除く）
    @classmethod
    def count_user_id(cls) -> int:
        # user_idのリスト
        user_ids: list[str] = []

        # user_idをリストに格納
        for item in cls.scan():
            if item.user_id not in user_ids:
                user_ids.append(item.user_id)

        return len(user_ids)
