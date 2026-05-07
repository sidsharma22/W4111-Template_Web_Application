from __future__ import annotations

import os
from typing import Any

import mysql.connector

from .AbstractBaseDataService import AbstractBaseDataService


def _get_env(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default)
    if val is None:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return val


class MySQLDataService(AbstractBaseDataService):
    """
    Concrete data service backed by MySQL.

    Config keys (all optional — fall back to environment variables):
      host              MYSQL_HOST         (default: localhost)
      port              MYSQL_PORT         (default: 3306)
      user              MYSQL_USER
      password          MYSQL_PASSWORD
      database          MYSQL_DATABASE     (default: classicmodels)
      unix_socket       MYSQL_UNIX_SOCKET
      table             table name to operate on
      primary_key_field primary key column name (single-column PKs only)
                        For composite PKs, pass primary_key_fields (list).
    """

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._table: str = str(config["table"])
        # Single-column PK (string) OR composite PK (list of strings)
        pk = config.get("primary_key_field") or config.get("primary_key_fields")
        if isinstance(pk, list):
            self._pk_fields: list[str] = pk
        elif pk:
            self._pk_fields = [str(pk)]
        else:
            self._pk_fields = ["id"]

        self._conn_kwargs: dict[str, Any] = {
            "host": config.get("host") or _get_env("MYSQL_HOST", "localhost"),
            "port": int(config.get("port") or _get_env("MYSQL_PORT", "3307")),
            "user": config.get("user") or _get_env("MYSQL_USER", "root"),
            "password": config.get("password") or _get_env("MYSQL_PASSWORD", ""),
            "database": config.get("database") or _get_env("MYSQL_DATABASE", "classicmodels"),
            "unix_socket": config.get("unix_socket") or os.getenv("MYSQL_UNIX_SOCKET"),
        }
        # Remove None values so mysql.connector doesn't reject them
        self._conn_kwargs = {k: v for k, v in self._conn_kwargs.items() if v is not None}

    def _connect(self):
        return mysql.connector.connect(**self._conn_kwargs)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pk_where_clause(self) -> str:
        """Returns 'col1 = %s AND col2 = %s ...' for WHERE clauses."""
        return " AND ".join(f"`{f}` = %s" for f in self._pk_fields)

    def _pk_values(self, primary_key) -> tuple:
        """Normalises a primary key to a tuple of values."""
        if isinstance(primary_key, (list, tuple)):
            return tuple(primary_key)
        if len(self._pk_fields) == 1:
            return (primary_key,)
        raise ValueError(
            f"Expected composite key ({self._pk_fields}), got scalar: {primary_key!r}"
        )

    # ------------------------------------------------------------------
    # AbstractBaseDataService implementation
    # ------------------------------------------------------------------

    def retrieveByPrimaryKey(self, primary_key) -> dict:
        """Return the row matching the given primary key, or {} if not found."""
        where = self._pk_where_clause()
        sql = f"SELECT * FROM `{self._table}` WHERE {where}"
        conn = self._connect()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql, self._pk_values(primary_key))
            row = cursor.fetchone()
            return dict(row) if row else {}
        finally:
            conn.close()

    def retrieveByTemplate(self, template: dict) -> list[dict]:
        """Return all rows matching the equality template dict (empty == all rows)."""
        conn = self._connect()
        try:
            cursor = conn.cursor(dictionary=True)
            if template:
                where = " AND ".join(f"`{k}` = %s" for k in template)
                sql = f"SELECT * FROM `{self._table}` WHERE {where}"
                cursor.execute(sql, tuple(template.values()))
            else:
                sql = f"SELECT * FROM `{self._table}`"
                cursor.execute(sql)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def create(self, payload: dict) -> Any:
        """Insert a new row. Returns the primary key value (or tuple for composite PKs)."""
        columns = list(payload.keys())
        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(f"`{c}`" for c in columns)
        sql = f"INSERT INTO `{self._table}` ({col_names}) VALUES ({placeholders})"
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, tuple(payload[c] for c in columns))
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            # For composite or non-autoincrement PKs, return the PK value(s) from payload
            pk_vals = [payload.get(f) for f in self._pk_fields]
            return tuple(pk_vals) if len(pk_vals) > 1 else pk_vals[0]
        finally:
            conn.close()

    def updateByPrimaryKey(self, primary_key, payload: dict) -> int:
        """Update columns in payload for the row with the given PK. Returns rows affected."""
        if not payload:
            return 0
        set_clause = ", ".join(f"`{k}` = %s" for k in payload)
        where = self._pk_where_clause()
        sql = f"UPDATE `{self._table}` SET {set_clause} WHERE {where}"
        params = tuple(payload.values()) + self._pk_values(primary_key)
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def deleteByPrimaryKey(self, primary_key) -> int:
        """Delete the row with the given PK. Returns rows deleted."""
        where = self._pk_where_clause()
        sql = f"DELETE FROM `{self._table}` WHERE {where}"
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, self._pk_values(primary_key))
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()
