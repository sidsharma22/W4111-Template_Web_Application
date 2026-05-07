from __future__ import annotations

import os
from decimal import Decimal
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
        "table": "orderdetails",
        "primary_key_fields": ["orderNumber", "productCode"],
    }


class OrderDetail(BaseModel):
    orderNumber: Optional[int] = None
    productCode: Optional[str] = None
    quantityOrdered: Optional[int] = None
    priceEach: Optional[Decimal] = None
    orderLineNumber: Optional[int] = None


class OrderDetailCollection(BaseModel):
    items: list[OrderDetail] = Field(default_factory=list)


class OrderDetailsResource(AbstractBaseResource):
    """
    Handles order details (orderdetails table).
    Composite primary key: (orderNumber, productCode).
    """

    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        svc_config = {**_mysql_config(), **cfg}
        svc_config["table"] = "orderdetails"
        svc_config["primary_key_fields"] = ["orderNumber", "productCode"]
        self._service = MySQLDataService(svc_config)

    def get(self, template: dict) -> OrderDetailCollection:
        rows = self._service.retrieveByTemplate(template)
        return OrderDetailCollection(items=[OrderDetail.model_validate(r) for r in rows])

    def get_by_id(self, id) -> OrderDetail:
        """id should be a tuple/list (orderNumber, productCode) or a dict with those keys."""
        if isinstance(id, dict):
            pk = (id["orderNumber"], id["productCode"])
        else:
            pk = id
        row = self._service.retrieveByPrimaryKey(pk)
        if not row:
            raise ValueError(f"No order detail with pk {pk!r}")
        return OrderDetail.model_validate(row)

    def post(self, new_data: OrderDetail) -> str:
        data = new_data.model_dump(exclude_none=True)
        pk = self._service.create(data)
        return str(pk)

    def put(self, character_id, new_data: OrderDetail) -> int:
        """character_id is (orderNumber, productCode) tuple."""
        data = new_data.model_dump(exclude_none=True)
        data.pop("orderNumber", None)
        data.pop("productCode", None)
        return self._service.updateByPrimaryKey(character_id, data)

    def delete(self, id) -> int:
        """id is (orderNumber, productCode) tuple."""
        return self._service.deleteByPrimaryKey(id)
