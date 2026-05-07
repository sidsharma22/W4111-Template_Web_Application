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
        "table": "customers",
        "primary_key_field": "customerNumber",
    }


class Customer(BaseModel):
    customerNumber: Optional[int] = None
    customerName: str = ""
    contactLastName: str = ""
    contactFirstName: str = ""
    phone: str = ""
    addressLine1: str = ""
    addressLine2: Optional[str] = None
    city: str = ""
    state: Optional[str] = None
    postalCode: Optional[str] = None
    country: str = ""
    salesRepEmployeeNumber: Optional[int] = None
    creditLimit: Optional[Decimal] = None


class CustomerCollection(BaseModel):
    items: list[Customer] = Field(default_factory=list)


class CustomerResource(AbstractBaseResource):
    def __init__(self, config: dict | None = None) -> None:
        cfg = dict(config or {})
        super().__init__(cfg)
        svc_config = {**_mysql_config(), **cfg}
        svc_config["table"] = "customers"
        svc_config["primary_key_field"] = "customerNumber"
        self._service = MySQLDataService(svc_config)

    def get(self, template: dict) -> CustomerCollection:
        rows = self._service.retrieveByTemplate(template)
        return CustomerCollection(items=[Customer.model_validate(r) for r in rows])

    def get_by_id(self, id: str) -> Customer:
        row = self._service.retrieveByPrimaryKey(id)
        if not row:
            raise ValueError(f"No customer with customerNumber {id!r}")
        return Customer.model_validate(row)

    def post(self, new_data: Customer) -> str:
        data = new_data.model_dump(exclude_none=True)
        pk = self._service.create(data)
        return str(pk)

    def put(self, character_id: str, new_data: Customer) -> int:
        data = new_data.model_dump(exclude_none=True)
        data.pop("customerNumber", None)
        return self._service.updateByPrimaryKey(character_id, data)

    def delete(self, id: str) -> int:
        return self._service.deleteByPrimaryKey(id)
