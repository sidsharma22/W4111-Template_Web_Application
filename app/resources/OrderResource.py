from __future__ import annotations

import os
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .AbstractBaseResource import AbstractBaseResource
from ..services.MySQLDataService import MySQLDataService


def _mysql_config() -> dict:
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3307")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "classicmodels"),
        "unix_socket": os.getenv("MYSQL_UNIX_SOCKET"),
        "table": "orders",
        "primary_key_field": "orderNumber",
    }


class Order(BaseModel):
    orderNumber: Optional[int] = None
    orderDate: Optional[date] = None
    requiredDate: Optional[date] = None
    shippedDate: Optional[date] = None
    status: str = ""
    comments: Optional[str] = None
    customerNumber: Optional[int] = None


class OrderCollection(BaseModel):
    items: list[Order] = Field(default_factory=list)


class OrderResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        svc_config = {**_mysql_config(), **cfg}
        svc_config["table"] = "orders"
        svc_config["primary_key_field"] = "orderNumber"
        self._service = MySQLDataService(svc_config)

    def get(self, template: dict) -> OrderCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderCollection(items=[Order.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Order:
        row = self._service.retrieveByPrimaryKey(id)
        if not row:
            raise ValueError(f"No order with orderNumber {id!r}")
        return Order.model_validate(row)

    def post(self, new_data: Order) -> str:
        data = new_data.model_dump(exclude_none=True)
        pk = self._service.create(data)
        return str(pk)

    def put(self, character_id: str, new_data: Order) -> int:
        data = new_data.model_dump(exclude_none=True)
        data.pop("orderNumber", None)
        return self._service.updateByPrimaryKey(character_id, data)

    def delete(self, id: str) -> int:
        return self._service.deleteByPrimaryKey(id)
