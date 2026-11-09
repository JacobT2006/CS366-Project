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
PROJECT_TABLES = (
    "categories",
    "stores",
    "products",
    "sales",
    "sale_items",
    "warranty_cases",
    "year_sales",
    "year_financials",
    "store_sales",
    "dataset_imports",
)


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
    """Parse an optional whole-number CSV value."""
    number = parse_decimal(value)
    if number is None:
        return None
    if number != number.to_integral_value():
        raise ValueError(f"Expected a whole number, got {value!r}")
    return int(number)


def parse_date(value: str, date_format: str) -> str:
    """Convert a source date into ISO format."""
    return datetime.strptime(value.strip(), date_format).date().isoformat()


def read_csv(filename: str) -> Iterator[dict[str, str]]:
    """Yield rows from a required dataset CSV."""
    path = DATA_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required dataset was not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as source:
        yield from csv.DictReader(source)


def parse_product(row: dict[str, str]) -> tuple[Any, ...]:
    """Convert one product CSV row into database column order."""
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
    """Split one sales CSV row into sale header and item values."""
    sale_id = row["sale_id"]
    quantity = parse_integer(row["quantity"])
    if quantity is None or quantity <= 0:
        raise ValueError(f"Invalid quantity for sale {sale_id}: {row['quantity']!r}")
    return (
        (sale_id, parse_date(row["sale_date"], "%d-%m-%Y"), row["store_id"]),
        (sale_id, row["product_id"], quantity),
    )


def parse_financial(row: dict[str, str]) -> tuple[tuple[Any, ...], tuple[Any, ...]]:
    """Split an annual finance row into its two table records."""
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
    """Insert rows in batches and return the number inserted."""
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


def sql_literal(value: Any) -> str:
    """Format one Python value as an SQL literal for export."""
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, Decimal)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def write_sql_inserts(
    output: Any,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
) -> int:
    """Write batched INSERT statements and return the row count."""
    column_list = ", ".join(f"`{column}`" for column in columns)
    batch: list[Sequence[Any]] = []
    count = 0

    def flush() -> None:
        if not batch:
            return
        values = ",\n".join(
            "(" + ", ".join(sql_literal(value) for value in row) + ")"
            for row in batch
        )
        output.write(f"INSERT INTO `{table}` ({column_list}) VALUES\n{values};\n\n")
        batch.clear()

    for row in rows:
        batch.append(row)
        count += 1
        if len(batch) == BATCH_SIZE:
            flush()
    flush()
    return count


def export_dataset_sql(output_path: Path) -> dict[str, int]:
    """Generate an offline SQL import file from all CSV datasets."""
    counts: dict[str, int] = {}
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        output.write("-- Generated from apple_db CSV files; run after InsertTables.sql.\n")
        output.write("-- Select DATABASE_NAME before running this file.\n\n")

        counts["categories"] = write_sql_inserts(
            output,
            "categories",
            ("category_id", "category_name"),
            ((row["category_id"], row["category_name"]) for row in read_csv("category.csv")),
        )
        counts["stores"] = write_sql_inserts(
            output,
            "stores",
            ("store_id", "store_name", "city", "country"),
            (
                (row["Store_ID"], row["Store_Name"], row["City"], row["Country"])
                for row in read_csv("stores.csv")
            ),
        )
        counts["products"] = write_sql_inserts(
            output,
            "products",
            ("product_id", "product_name", "category_id", "launch_date", "price", "is_active"),
            (parse_product(row) for row in read_csv("products.csv")),
        )

        def sale_headers() -> Iterator[Sequence[Any]]:
            for row in read_csv("sales.csv"):
                yield parse_sale(row)[0]

        def sale_items() -> Iterator[Sequence[Any]]:
            for row in read_csv("sales.csv"):
                yield parse_sale(row)[1]

        counts["sales"] = write_sql_inserts(
            output,
            "sales",
            ("sale_id", "sale_date", "store_id"),
            sale_headers(),
        )
        counts["sale_items"] = write_sql_inserts(
            output,
            "sale_items",
            ("sale_id", "product_id", "quantity"),
            sale_items(),
        )

        output.write(
            "CREATE TEMPORARY TABLE warranty_import ("
            "claim_id VARCHAR(20) PRIMARY KEY, claim_date DATE NOT NULL, "
            "sale_id VARCHAR(20) NOT NULL, repair_status VARCHAR(30) NOT NULL);\n\n"
        )
        counts["warranty_cases"] = write_sql_inserts(
            output,
            "warranty_import",
            ("claim_id", "claim_date", "sale_id", "repair_status"),
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
        output.write(
            "INSERT INTO warranty_cases (claim_id, sale_id, product_id, claim_date, repair_status)\n"
            "SELECT w.claim_id, w.sale_id, si.product_id, w.claim_date, w.repair_status\n"
            "FROM warranty_import AS w\n"
            "JOIN sale_items AS si ON si.sale_id = w.sale_id;\n"
            "DROP TEMPORARY TABLE warranty_import;\n\n"
        )

        def financial_rows(index: int) -> Iterator[Sequence[Any]]:
            for row in read_csv("Apple 2009-2024.csv"):
                yield parse_financial(row)[index]

        counts["year_sales"] = write_sql_inserts(
            output,
            "year_sales",
            (
                "year", "ebitda", "revenue", "gross_profit", "operating_income",
                "net_income", "eps", "shares_outstanding", "year_close_price",
                "gross_margin", "pe_ratio",
            ),
            financial_rows(0),
        )
        counts["year_financials"] = write_sql_inserts(
            output,
            "year_financials",
            (
                "year", "total_assets", "cash_on_hand", "long_term_debt",
                "total_liabilities", "employees",
            ),
            financial_rows(1),
        )
        total_rows = sum(counts.values())
        write_sql_inserts(
            output,
            "dataset_imports",
            ("dataset_name", "row_count"),
            ((DATASET_NAME, total_rows),),
        )
    return counts


def clear_dataset(cursor: Any, connection: Any) -> None:
    """Delete previously imported rows in foreign-key-safe order."""
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


def existing_project_tables(connection: Any) -> set[str]:
    placeholders = ", ".join("?" for _ in PROJECT_TABLES)
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"SELECT table_name FROM information_schema.tables "
            f"WHERE table_schema = DATABASE() AND table_name IN ({placeholders})",
            PROJECT_TABLES,
        )
        return {row[0] for row in cursor.fetchall()}
    finally:
        cursor.close()


def load_dataset(connection: Any, force: bool = False) -> dict[str, int]:
    """Import all CSV datasets unless already loaded and not forced."""
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
    """Load claims and resolve each product through its sale item."""
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
    """Connect using database settings loaded from the environment or .env."""
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

    host = os.environ.get("DATABASE_HOST", "140.146.23.39")
    port = int(os.environ.get("DATABASE_PORT", "3306"))
    database = os.environ.get("DATABASE_NAME", "")
    connection_options: dict[str, Any] = {
        "user": os.environ.get("DATABASE_USERNAME", ""),
        "database": database,
        "connect_timeout": 10,
    }
    password = os.environ.get("DATABASE_PASSWORD")
    if password:
        connection_options["password"] = password
    connection_options["host"] = host
    connection_options["port"] = port
    connection = mariadb.connect(**connection_options)
    print(f"Connected to MariaDB at {host}:{port}/{database}.", file=sys.stderr)
    return connection


def main(argv: list[str] | None = None) -> int:
    """Run the online loader or offline SQL exporter from CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="clear and reload all CSV data")
    parser.add_argument(
        "--sql-out",
        type=Path,
        metavar="PATH",
        help="write an offline SQL import script instead of connecting to MariaDB",
    )
    args = parser.parse_args(argv)

    try:
        if args.sql_out is not None:
            counts = export_dataset_sql(args.sql_out)
            print(f"Wrote SQL import script to {args.sql_out}.")
            print(f"Included {sum(counts.values()):,} source records.")
            return 0

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
