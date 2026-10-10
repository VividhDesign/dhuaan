"""Subscriber store (DynamoDB single table)."""
import os
import time

import boto3

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
    return _table


def put_tg(chat_id: int, lat: float, lon: float, cell: str, lang: str, role: str) -> None:
    table().put_item(Item={"pk": f"SUB#tg#{chat_id}", "sk": "META", "kind": "tg", "chat_id": chat_id,
                           "lat": str(lat), "lon": str(lon), "cell": cell, "lang": lang, "role": role,
                           "created_at": int(time.time()), "last_alert_at": 0})


def get_tg(chat_id: int) -> dict | None:
    return table().get_item(Key={"pk": f"SUB#tg#{chat_id}", "sk": "META"}).get("Item")


def update_tg(chat_id: int, **fields) -> None:
    expr = "SET " + ", ".join(f"#{k} = :{k}" for k in fields)
    table().update_item(Key={"pk": f"SUB#tg#{chat_id}", "sk": "META"}, UpdateExpression=expr,
                        ExpressionAttributeNames={f"#{k}": k for k in fields},
                        ExpressionAttributeValues={f":{k}": v for k, v in fields.items()})


def delete_tg(chat_id: int) -> None:
    table().delete_item(Key={"pk": f"SUB#tg#{chat_id}", "sk": "META"})


def put_email(sub_hash: str, cell: str, lang: str, role: str, sub_arn: str) -> None:
    table().put_item(Item={"pk": f"SUB#email#{sub_hash}", "sk": "META", "kind": "email", "cell": cell,
                           "lang": lang, "role": role, "sub_arn": sub_arn, "created_at": int(time.time())})


def all_of(kind: str) -> list[dict]:
    items, kw = [], {"FilterExpression": "#k = :k", "ExpressionAttributeNames": {"#k": "kind"},
                     "ExpressionAttributeValues": {":k": kind}}
    while True:
        r = table().scan(**kw)
        items += r.get("Items", [])
        if "LastEvaluatedKey" not in r:
            return items
        kw["ExclusiveStartKey"] = r["LastEvaluatedKey"]


def all_tg() -> list[dict]:
    return all_of("tg")
