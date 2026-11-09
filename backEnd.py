"""Database operations used by the terminal interface."""

from __future__ import annotations

import os
from typing import Any

from query_catalog import QueryDefinition, load_queries


def connect(
    *, host: str | None = None, port: int | None = None,
    database: str | None = None, user: str | None = None,
    password: str | None = None,
) -> Any:
    try:
        import mariadb
    except ImportError as error:
        raise RuntimeError(
            "MariaDB Connector/Python is missing. Run: python3 -m pip install -r requirements.txt"
        ) from error

    connection_options: dict[str, Any] = {
        "user": user if user is not None else os.environ.get("dbUser", "retail_app"),
        "database": database if database is not None else os.environ.get("db_name", "retailInfo_db"),
        "connect_timeout": 10,
    }
    selected_password = password if password is not None else os.environ.get("DB_PASSWORD")
    if selected_password:
        connection_options["password"] = selected_password
    socket_path = os.environ.get("dbSocket") if host is None else None
    if socket_path:
        connection_options["unix_socket"] = socket_path
    else:
        connection_options["host"] = host or os.environ.get("dbHost", "127.0.0.1")
        connection_options["port"] = port if port is not None else int(os.environ.get("port", "3307"))
    return mariadb.connect(**connection_options)


def _call(
    connection: Any,
    procedure: str,
    parameters: tuple[Any, ...],
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    cursor = connection.cursor()
    try:
        placeholders = ", ".join("?" for _ in parameters)
        cursor.execute(f"CALL {procedure}({placeholders})", parameters)
        columns: tuple[str, ...] = ()
        rows: list[tuple[Any, ...]] = []
        while True:
            if cursor.description:
                columns = tuple(item[0] for item in cursor.description)
                rows = list(cursor.fetchall())
            if not cursor.nextset():
                break
        connection.commit()
        return columns, rows
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def search_products(
    connection: Any,
    search: str | None,
    category_id: str | None,
    active: bool | None,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(
        connection,
        "sp_search_products",
        (search or None, category_id or None, None if active is None else int(active)),
    )


def add_product(
    connection: Any,
    product_id: str,
    name: str,
    category_id: str,
    launch_date: str,
    price: str,
) -> None:
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO products
               (product_id, product_name, category_id, launch_date, price, is_active)
               VALUES (?, ?, ?, ?, ?, TRUE)""",
            (product_id, name, category_id, launch_date, price),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def record_sale(
    connection: Any,
    sale_id: str,
    sale_date: str,
    store_id: str,
    product_id: str,
    quantity: int,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(
        connection,
        "sp_record_sale",
        (sale_id, sale_date, store_id, product_id, quantity),
    )


def update_product_price(
    connection: Any,
    product_id: str,
    new_price: str,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(connection, "sp_update_product_price", (product_id, new_price))


def set_product_active(
    connection: Any,
    product_id: str,
    active: bool,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(connection, "sp_set_product_active", (product_id, int(active)))


def update_warranty_status(
    connection: Any,
    claim_id: str,
    status: str,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(connection, "sp_update_warranty_status", (claim_id, status))


def store_sales_summary(
    connection: Any,
    store_id: str | None,
    year: int | None,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]]]:
    return _call(connection, "sp_store_sales_summary", (store_id or None, year))


def run_query(
    connection: Any,
    query: QueryDefinition,
    row_limit: int = 25,
) -> tuple[tuple[str, ...], list[tuple[Any, ...]], bool]:
    cursor = connection.cursor()
    try:
        cursor.execute(query.sql)
        columns = tuple(item[0] for item in (cursor.description or ()))
        rows = list(cursor.fetchmany(row_limit + 1))
        has_more = len(rows) > row_limit
        return columns, rows[:row_limit], has_more
    finally:
        cursor.close()


def get_categories(connection: Any) -> list[tuple[str, str]]:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT category_id, category_name FROM categories ORDER BY category_id")
        return list(cursor.fetchall())
    finally:
        cursor.close()


def get_stores(connection: Any) -> list[tuple[str, str]]:
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT store_id, store_name FROM stores ORDER BY store_id")
        return list(cursor.fetchall())
    finally:
        cursor.close()


def get_queries() -> tuple[QueryDefinition, ...]:
    return load_queries()
