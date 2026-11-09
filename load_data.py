"""Load the project CSV files into the normalized MariaDB schema."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "apple_db"
BATCH_SIZE = 5_000
DATASET_NAME = "apple_db"


def parse_decimal(value: str | None) -> Decimal | None:
    """Parse CSV currency, comma-formatted numbers, and percentages."""
    if value is None or not value.strip():
        return None
    cleaned = value.strip().replace("$", "").replace(",", "").replace("%", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation as error:
        raise ValueError(f"Invalid numeric value: {value!r}") from error


def parse_integer(value: str | None) -> int | None:
    number = parse_decimal(value)
    if number is None:
        return None
    if number != number.to_integral_value():
        raise ValueError(f"Expected a whole number, got {value!r}")
    return int(number)


def parse_date(value: str, date_format: str) -> str:
    return datetime.strptime(value.strip(), date_format).date().isoformat()


def read_csv(filename: str) -> Iterator[dict[str, str]]:
    path = DATA_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required dataset was not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def parse_product(row: dict[str, str]) -> tuple[Any, ...]:
    price = parse_decimal(row["Price"])
    if price is None:
        raise ValueError(f"Missing product price for {row['Product_ID']}")
    return (
        row["Product_ID"],
        row["Product_Name"],
        row["Category_ID"],
        parse_date(row["Launch_Date"], "%Y-%m-%d"),
        price,
        True,
    )


def parse_sale(row: dict[str, str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    sale_id = row["sale_id"]
    quantity = parse_integer(row["quantity"])
    if quantity is None or quantity <= 0:
        raise ValueError(f"Invalid quantity for sale {sale_id}: {row['quantity']!r}")
    return (
        (sale_id, parse_date(row["sale_date"], "%d-%m-%Y"), row["store_id"]),
        (sale_id, row["product_id"], quantity),
    )


def parse_financial(row: dict[str, str]) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    year = parse_integer(row["year"])
    employees = parse_integer(row["Employees"])
    if year is None:
        raise ValueError("Financial data row is missing its year")
    return (
        (
            year,
            parse_decimal(row["EBITDA (millions)"]),
            parse_decimal(row["Revenue (millions)"]),
            parse_decimal(row["Gross Profit (millions)"]),
            parse_decimal(row["Op Income (millions)"]),
            parse_decimal(row["Net Income (millions)"]),
            parse_decimal(row["EPS"]),
            parse_integer(row["Shares Outstanding"]),
            parse_decimal(row["Year Close Price"]),
            parse_decimal(row["Gross Margin"]),
            parse_decimal(row["PE ratio"]),
        ),
        (
            year,
            parse_decimal(row["Total Assets (millions)"]),
            parse_decimal(row["Cash on Hand (millions)"]),
            parse_decimal(row["Long Term Debt (millions)"]),
            parse_decimal(row["Total Liabilities (millions)"]),
            employees,
        ),
    )


def insert_rows(
    cursor: Any,
    connection: Any,
    statement: str,
    rows: Iterable[Sequence[Any]],
) -> int:
    batch: list[Sequence[Any]] = []
    count = 0
    for row in rows:
        batch.append(row)
        if len(batch) == BATCH_SIZE:
            cursor.executemany(statement, batch)
            connection.commit()
            count += len(batch)
            batch.clear()
    if batch:
        cursor.executemany(statement, batch)
        connection.commit()
        count += len(batch)
    return count


def clear_dataset(cursor: Any, connection: Any) -> None:
    cursor.execute("DELETE FROM dataset_imports WHERE dataset_name = ?", (DATASET_NAME,))
    for table in (
        "store_sales",
        "warranty_cases",
        "sale_items",
        "sales",
        "products",
        "categories",
        "stores",
        "year_financials",
        "year_sales",
    ):
        cursor.execute(f"DELETE FROM {table}")
    connection.commit()


def load_dataset(connection: Any, force: bool = False) -> dict[str, int]:
    cursor = connection.cursor()
    cursor.execute(
        "SELECT row_count FROM dataset_imports WHERE dataset_name = ?",
        (DATASET_NAME,),
    )
    existing = cursor.fetchone()
    if existing is not None and not force:
        print(f"Dataset already loaded ({existing[0]} source rows). Use --force to reload.")
        return {}

    clear_dataset(cursor, connection)
    counts: dict[str, int] = {}

    counts["categories"] = insert_rows(
        cursor,
        connection,
        "INSERT INTO categories (category_id, category_name) VALUES (?, ?)",
        ((row["category_id"], row["category_name"]) for row in read_csv("category.csv")),
    )
    counts["stores"] = insert_rows(
        cursor,
        connection,
        "INSERT INTO stores (store_id, store_name, city, country) VALUES (?, ?, ?, ?)",
        (
            (row["Store_ID"], row["Store_Name"], row["City"], row["Country"])
            for row in read_csv("stores.csv")
        ),
    )
    counts["products"] = insert_rows(
        cursor,
        connection,
        """INSERT INTO products
           (product_id, product_name, category_id, launch_date, price, is_active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (parse_product(row) for row in read_csv("products.csv")),
    )

    def sale_headers() -> Iterator[Sequence[Any]]:
        for row in read_csv("sales.csv"):
            header, _ = parse_sale(row)
            yield header

    def sale_items() -> Iterator[Sequence[Any]]:
        for row in read_csv("sales.csv"):
            _, item = parse_sale(row)
            yield item

    counts["sales"] = insert_rows(
        cursor,
        connection,
        "INSERT INTO sales (sale_id, sale_date, store_id) VALUES (?, ?, ?)",
        sale_headers(),
    )
    counts["sale_items"] = insert_rows(
        cursor,
        connection,
        "INSERT INTO sale_items (sale_id, product_id, quantity) VALUES (?, ?, ?)",
        sale_items(),
    )
    counts["warranty_cases"] = load_warranties(cursor, connection)

    def financial_rows(index: int) -> Iterator[Sequence[Any]]:
        for row in read_csv("Apple 2009-2024.csv"):
            yield parse_financial(row)[index]

    counts["year_sales"] = insert_rows(
        cursor,
        connection,
        """INSERT INTO year_sales
           (year, ebitda, revenue, gross_profit, operating_income, net_income, eps,
            shares_outstanding, year_close_price, gross_margin, pe_ratio)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        financial_rows(0),
    )
    counts["year_financials"] = insert_rows(
        cursor,
        connection,
        """INSERT INTO year_financials
           (year, total_assets, cash_on_hand, long_term_debt, total_liabilities, employees)
           VALUES (?, ?, ?, ?, ?, ?)""",
        financial_rows(1),
    )

    total_rows = sum(counts.values())
    cursor.execute(
        """INSERT INTO dataset_imports (dataset_name, row_count)
           VALUES (?, ?)""",
        (DATASET_NAME, total_rows),
    )
    connection.commit()
    return counts


def load_warranties(cursor: Any, connection: Any) -> int:
    cursor.execute(
        """CREATE TEMPORARY TABLE warranty_import (
               claim_id VARCHAR(20) PRIMARY KEY,
               claim_date DATE NOT NULL,
               sale_id VARCHAR(20) NOT NULL,
               repair_status VARCHAR(30) NOT NULL
           ) ENGINE=InnoDB"""
    )
    count = insert_rows(
        cursor,
        connection,
        """INSERT INTO warranty_import
           (claim_id, claim_date, sale_id, repair_status) VALUES (?, ?, ?, ?)""",
        (
            (
                row["claim_id"],
                parse_date(row["claim_date"], "%Y-%m-%d"),
                row["sale_id"],
                row["repair_status"],
            )
            for row in read_csv("warranty.csv")
        ),
    )
    cursor.execute(
        """INSERT INTO warranty_cases (claim_id, sale_id, product_id, claim_date, repair_status)
           SELECT w.claim_id, w.sale_id, si.product_id, w.claim_date, w.repair_status
           FROM warranty_import AS w
           JOIN sale_items AS si ON si.sale_id = w.sale_id"""
    )
    connection.commit()
    cursor.execute("DROP TEMPORARY TABLE warranty_import")
    connection.commit()
    return count


def connect() -> Any:
    try:
        from dotenv import load_dotenv
    except ImportError as error:
        raise RuntimeError(
            "python-dotenv is missing. Run: python3 -m pip install -r requirements.txt"
        ) from error
    load_dotenv()

    try:
        import mariadb
    except ImportError as error:
        raise RuntimeError(
            "MariaDB Connector/Python is missing. Run: python3 -m pip install -r requirements.txt"
        ) from error

    connection_options: dict[str, Any] = {
        "user": os.environ.get("DATABASE_USERNAME", ""),
        "database": os.environ.get("DATABASE_NAME", "retailInfo_db"),
        "connect_timeout": 10,
    }
    password = os.environ.get("DATABASE_PASSWORD")
    if password:
        connection_options["password"] = password
    connection_options["host"] = os.environ.get("DATABASE_HOST", "127.0.0.1")
    connection_options["port"] = int(os.environ.get("DATABASE_PORT", "3307"))
    return mariadb.connect(**connection_options)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="clear and reload all CSV data")
    args = parser.parse_args(argv)

    try:
        connection = connect()
        try:
            counts = load_dataset(connection, force=args.force)
        finally:
            connection.close()
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Data load failed: {error}", file=sys.stderr)
        return 1

    if counts:
        for table, count in counts.items():
            print(f"{table}: {count:,} rows loaded")
        print(f"Loaded {sum(counts.values()):,} source records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
