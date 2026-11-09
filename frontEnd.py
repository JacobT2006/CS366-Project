"""Interactive menu for browsing and maintaining the retail database."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import os
from typing import Any, Sequence

from dotenv import load_dotenv

from backEnd import (
    add_product,
    connect,
    get_categories,
    get_queries,
    get_stores,
    record_sale,
    run_query,
    search_products,
    set_product_active,
    store_sales_summary,
    update_product_price,
    update_warranty_status,
)

# Connection settings live in the untracked .env file; see .env.example.
load_dotenv()
DATABASE_HOST = os.getenv("DATABASE_HOST", "127.0.0.1")
DATABASE_PORT = int(os.getenv("DATABASE_PORT", "3307"))
DATABASE_NAME = os.getenv("DATABASE_NAME", "retailInfo_db")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME", "")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")


def prompt(label: str) -> str:
    return input(f"{label}: ").strip()


def prompt_required(label: str) -> str:
    value = prompt(label)
    if not value:
        raise ValueError(f"{label} is required.")
    return value


def prompt_price(label: str = "Price") -> str:
    raw = prompt_required(label)
    try:
        amount = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("Enter a valid price.") from error
    if amount < 0:
        raise ValueError("Price must be zero or greater.")
    return str(amount.quantize(Decimal("0.01")))


def prompt_date(label: str) -> str:
    raw = prompt_required(label)
    try:
        return date.fromisoformat(raw).isoformat()
    except ValueError as error:
        raise ValueError("Enter a date in YYYY-MM-DD format.") from error


def print_table(columns: Sequence[str], rows: Sequence[Sequence[Any]]) -> None:
    if not rows:
        print("No matching records.")
        return
    display_rows = [[str(value) for value in row] for row in rows]
    widths = [
        min(32, max(len(column), *(len(row[index]) for row in display_rows)))
        for index, column in enumerate(columns)
    ]

    def format_row(values: Sequence[str]) -> str:
        return " | ".join(value[:width].ljust(width) for value, width in zip(values, widths))

    print(format_row(columns))
    print("-+-".join("-" * width for width in widths))
    for row in display_rows:
        print(format_row(row))


def show_results(
    result: tuple[tuple[str, ...], list[tuple[Any, ...]]],
) -> None:
    print_table(*result)


def search_menu(connection: Any) -> None:
    search = prompt("Product name contains (blank for all)") or None
    categories = get_categories(connection)
    print_table(("Category ID", "Category"), categories)
    category_id = prompt("Category ID (blank for all)") or None
    active_choice = prompt("Status [active/inactive/all] (default active)").lower()
    if active_choice not in ("", "active", "inactive", "all"):
        raise ValueError("Choose active, inactive, or all.")
    active = None if active_choice == "all" else active_choice != "inactive"
    show_results(search_products(connection, search, category_id, active))


def add_product_menu(connection: Any) -> None:
    print_table(("Category ID", "Category"), get_categories(connection))
    add_product(
        connection,
        prompt_required("Product ID"),
        prompt_required("Product name"),
        prompt_required("Category ID"),
        prompt_date("Launch date (YYYY-MM-DD)"),
        prompt_price(),
    )
    print("Product added.")


def record_sale_menu(connection: Any) -> None:
    print_table(("Store ID", "Store"), get_stores(connection))
    show_results(
        record_sale(
            connection,
            prompt_required("Sale ID"),
            prompt_date("Sale date (YYYY-MM-DD)"),
            prompt_required("Store ID"),
            prompt_required("Product ID"),
            int(prompt_required("Quantity")),
        )
    )
    print("Sale recorded.")


def product_price_menu(connection: Any) -> None:
    show_results(
        update_product_price(
            connection,
            prompt_required("Product ID"),
            prompt_price("New price"),
        )
    )
    print("Product price updated.")


def product_status_menu(connection: Any) -> None:
    product_id = prompt_required("Product ID")
    choice = prompt("Deactivate this product? [y/N]").lower()
    if choice not in ("y", "yes", "n", "no", ""):
        raise ValueError("Enter y or n.")
    active = choice not in ("y", "yes")
    show_results(set_product_active(connection, product_id, active))
    print("Product status updated.")


def warranty_status_menu(connection: Any) -> None:
    print("Allowed statuses: Pending, In Progress, Completed, Rejected")
    show_results(
        update_warranty_status(
            connection,
            prompt_required("Claim ID"),
            prompt_required("New status"),
        )
    )
    print("Warranty claim updated.")


def report_menu(connection: Any) -> None:
    queries = get_queries()
    for query in queries:
        print(f"{query.query_id} [{query.level}] {query.title}")
    query_id = prompt_required("Query ID").upper()
    selected = next((query for query in queries if query.query_id == query_id), None)
    if selected is None:
        raise ValueError("Choose one of the listed query IDs.")
    columns, rows, has_more = run_query(connection, selected)
    print_table(columns, rows)
    if has_more:
        print("Showing the first 25 rows. The query returned additional results.")


def store_summary_menu(connection: Any) -> None:
    store_id = prompt("Store ID (blank for all stores)") or None
    year_text = prompt("Year (blank for all years)")
    try:
        year = int(year_text) if year_text else None
    except ValueError as error:
        raise ValueError("Year must be a four-digit number.") from error
    show_results(store_sales_summary(connection, store_id, year))


MENU = (
    "1. Search products",
    "2. Run an SQL report",
    "3. Insert a product",
    "4. Record a sale",
    "5. Modify a product price",
    "6. Deactivate or reactivate a product",
    "7. Modify a warranty claim",
    "8. View store sales summary",
    "0. Exit",
)


def run_menu(connection: Any, database_error: type[Exception]) -> None:
    actions = {
        "1": search_menu,
        "2": report_menu,
        "3": add_product_menu,
        "4": record_sale_menu,
        "5": product_price_menu,
        "6": product_status_menu,
        "7": warranty_status_menu,
        "8": store_summary_menu,
    }
    while True:
        print("\nRetail Information Database")
        print("\n".join(MENU))
        choice = prompt("Select an option")
        if choice == "0":
            return
        action = actions.get(choice)
        if action is None:
            print("Choose a listed menu option.")
            continue
        try:
            action(connection)
        except ValueError as error:
            print(f"Input error: {error}")
        except database_error as error:
            connection.rollback()
            print(f"Database error: {error}")


def main() -> int:
    try:
        import mariadb
    except ImportError:
        print(
            "MariaDB Connector/Python is missing. "
            "Run: python3 -m pip install -r requirements.txt"
        )
        return 1

    try:
        if not 1 <= DATABASE_PORT <= 65535:
            print("Invalid database connection setting: port must be between 1 and 65535.")
            return 1
        connection = connect(
            host=DATABASE_HOST,
            port=DATABASE_PORT,
            database=DATABASE_NAME,
            user=DATABASE_USERNAME,
            password=DATABASE_PASSWORD,
        )
    except mariadb.Error as error:
        print(f"Could not connect to MariaDB: {error}")
        return 1

    try:
        run_menu(connection, mariadb.Error)
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
