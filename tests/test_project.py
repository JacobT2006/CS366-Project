from __future__ import annotations

from io import StringIO
import unittest
from decimal import Decimal

from load_data import (
    read_csv,
    parse_date,
    parse_decimal,
    parse_financial,
    parse_integer,
    parse_product,
    parse_sale,
    write_sql_inserts,
)
from query_catalog import load_queries


class CsvParsingTests(unittest.TestCase):
    def test_sql_export_quotes_text_and_preserves_numbers(self) -> None:
        output = StringIO()
        count = write_sql_inserts(
            output,
            "categories",
            ("category_id", "category_name", "price"),
            [("CAT-1", "Men's wear", Decimal("12.50"))],
        )
        self.assertEqual(count, 1)
        self.assertIn("('CAT-1', 'Men''s wear', 12.50);", output.getvalue())

    def test_supplied_dataset_keys_and_relationships(self) -> None:
        category_ids = {row["category_id"] for row in read_csv("category.csv")}
        store_ids = {row["Store_ID"] for row in read_csv("stores.csv")}
        products = {row["Product_ID"]: row["Category_ID"] for row in read_csv("products.csv")}
        self.assertEqual(len(category_ids), 10)
        self.assertEqual(len(store_ids), 75)
        self.assertEqual(len(products), 89)
        self.assertTrue(all(category in category_ids for category in products.values()))

        sale_ids: set[str] = set()
        sales_count = 0
        for row in read_csv("sales.csv"):
            self.assertNotIn(row["sale_id"], sale_ids)
            self.assertIn(row["store_id"], store_ids)
            self.assertIn(row["product_id"], products)
            sale_ids.add(row["sale_id"])
            sales_count += 1
        self.assertEqual(sales_count, 1_040_200)

        claims = 0
        for row in read_csv("warranty.csv"):
            self.assertIn(row["sale_id"], sale_ids)
            claims += 1
        self.assertEqual(claims, 30_000)

        financial_rows = list(read_csv("Apple 2009-2024.csv"))
        self.assertEqual(len(financial_rows), 16)

    def test_currency_and_percent_values_are_parsed(self) -> None:
        self.assertEqual(parse_decimal("$134,661"), Decimal("134661"))
        self.assertEqual(parse_decimal("46.21%"), Decimal("46.21"))
        self.assertIsNone(parse_decimal(""))

    def test_integer_fields_reject_fractional_values(self) -> None:
        self.assertEqual(parse_integer("164,000"), 164000)
        with self.assertRaises(ValueError):
            parse_integer("2.5")

    def test_sales_date_and_keys_are_normalized(self) -> None:
        self.assertEqual(parse_date("16-06-2023", "%d-%m-%Y"), "2023-06-16")
        sale, item = parse_sale(
            {
                "sale_id": "YG-8782",
                "sale_date": "16-06-2023",
                "store_id": "ST-10",
                "product_id": "P-38",
                "quantity": "10",
            }
        )
        self.assertEqual(sale, ("YG-8782", "2023-06-16", "ST-10"))
        self.assertEqual(item, ("YG-8782", "P-38", 10))

    def test_product_and_financial_rows_match_schema_order(self) -> None:
        product = parse_product(
            {
                "Product_ID": "P-1",
                "Product_Name": "MacBook",
                "Category_ID": "CAT-1",
                "Launch_Date": "2023-09-17",
                "Price": "1149",
            }
        )
        self.assertEqual(product, ("P-1", "MacBook", "CAT-1", "2023-09-17", Decimal("1149"), True))

        yearly, financials = parse_financial(
            {
                "year": "2024",
                "EBITDA (millions)": "$134,661",
                "Revenue (millions)": "$391,035",
                "Gross Profit (millions)": "$180,683",
                "Op Income (millions)": "$123,216",
                "Net Income (millions)": "$93,736",
                "EPS": "$6.08",
                "Shares Outstanding": "15,408",
                "Year Close Price": "243.04",
                "Gross Margin": "46.21%",
                "PE ratio": "39.97",
                "Total Assets (millions)": "$364,980",
                "Cash on Hand (millions)": "$65,171",
                "Long Term Debt (millions)": "$85,750",
                "Total Liabilities (millions)": "$308,030",
                "Employees": "164,000",
            }
        )
        self.assertEqual(yearly[0], 2024)
        self.assertEqual(yearly[1], Decimal("134661"))
        self.assertEqual(yearly[8], Decimal("243.04"))
        self.assertEqual(financials[-1], 164000)

    def test_invalid_date_and_nonpositive_quantity_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_date("not-a-date", "%d-%m-%Y")
        with self.assertRaises(ValueError):
            parse_sale(
                {
                    "sale_id": "BAD",
                    "sale_date": "16-06-2023",
                    "store_id": "ST-1",
                    "product_id": "P-1",
                    "quantity": "0",
                }
            )


class QueryCatalogTests(unittest.TestCase):
    def test_all_ten_queries_are_level_two_or_three(self) -> None:
        queries = load_queries()
        self.assertEqual(len(queries), 10)
        self.assertEqual([query.query_id for query in queries], [f"Q{i:02}" for i in range(1, 11)])
        self.assertTrue(all(query.level in {"Level 2", "Level 3"} for query in queries))
        self.assertTrue(all("JOIN" in query.sql.upper() for query in queries))


if __name__ == "__main__":
    unittest.main()
