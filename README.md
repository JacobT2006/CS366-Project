# CS366 Retail Information Database

This project is a working MariaDB-backed application for the Apple retail dataset. It creates a normalized schema, loads the supplied CSV files, provides SQL reports and stored procedures, and exposes search and data-maintenance features through a menu-driven Python interface.

## Project files

- `createDB.sql` — creates `retailInfo_db` and the local application account.
- `InsertTables.sql` — creates the relational tables and their constraints.
- `load_data.py` — imports all six CSV datasets under `apple_db/`.
- `queries.sql` — ten Level 2/3 application reports, with descriptions and uses.
- `stored_procedures.sql` — product search, sale entry, updates, and store reporting procedures.
- `backEnd.py`, `frontEnd.py` — database operations and interactive terminal interface.
- `tests/` — database-independent parser and query-catalog tests.
- `runScript.sh` — selects the project Python environment and runs the app.

## Requirements and setup (WSL/Ubuntu)

The launcher is a Bash script and is intended to be run in Linux or WSL, not directly in Windows PowerShell. From an Ubuntu/WSL terminal:

```bash
cd /mnt/c/Git/CS366-Project
sudo apt update
sudo apt install python3 python3-dev python3-venv python3-pip libmariadb-dev build-essential pkg-config
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your database connection settings.
./runScript.sh
```

The project requires Python 3.8 or newer and MariaDB Connector/Python. The launcher automatically uses `.venv/bin/python` when present, so activating the environment is optional. Configure `.env` with a reachable MariaDB database that already has this project's schema, stored procedures, and data. The launcher does not start, stop, or configure a database server.

The dataset includes 1,040,200 sales, 30,000 warranty claims, 89 products, 75 stores, 10 categories, and 16 years of Apple financial data. The annual financial CSV reports monetary values in millions; the loader preserves those source units.

### Common commands

```bash
./runScript.sh               # Run the app using the configured database
./runScript.sh --update      # Pull project changes, then run the app
python load_data.py          # Load CSV data into a prepared, empty schema
python load_data.py --force  # Clear and reload the CSV data
python -m unittest discover -s tests
```

For the checkpoint submission, create your own Word or PDF document. Copy the schema from `InsertTables.sql`, the ten annotated queries from `queries.sql`, and the procedures from `stored_procedures.sql`. Run each query and procedure in MariaDB to collect real result samples. Capture the running menu and result tables for interface evidence. Before adding secondary indexes for Checkpoint 4, run `EXPLAIN` on at least five queries and record their runtimes and plans. Add group member names and team-specific management updates.

## Interface features

1. Search products by name, category, and active status.
2. Run any of the ten documented SQL reports.
3. Insert a product.
4. Record a sale through `sp_record_sale`.
5. Change a product's price.
6. Deactivate or reactivate a product (rather than deleting referenced sales).
7. Update a warranty claim status.
8. View a store/year sales summary.

Copy `.env.example` to `.env` and enter the database connection settings there. The `.env` file is ignored by Git. Use the remote server's reachable hostname/IP and port, and ensure its network rules and database grants allow the client. Leave `DATABASE_PASSWORD` empty if the server does not require one. The remote database must already contain this project's schema, stored procedures, and data; the application connects to it and runs its normal reports and operations. The sample credentials in `createDB.sql` are for coursework use only; change them before exposing the database to a network.

## Data and schema notes

The sales CSV has one product per uniquely identified sale row. The importer stores each record as a `sales` header and a matching `sale_items` row. Warranty CSV rows contain a sale ID but no product ID, so the loader joins through `sale_items` when populating `warranty_cases`. CSV imports are batch-inserted and marked in `dataset_imports` so ordinary launches do not reload the large sales file.

The schema includes primary and foreign keys, uniqueness and not-null constraints, and nonnegative price/positive quantity checks.

## Checkpoint 3 document checklist

Build the PDF or Word document yourself and include:

1. `InsertTables.sql`, one successful `SELECT COUNT(*) FROM sales`, plus a duplicate product ID or invalid category insert showing a database constraint error.
2. All ten queries from `queries.sql`, with each query's included level, description, usefulness, and an actual result sample. Connect in WSL with `mariadb --host=127.0.0.1 --port=3307 --user=retail_app --password retailInfo_db`.
3. At least five procedures from `stored_procedures.sql`. Try `CALL sp_search_products('Mac', NULL, 1);` and `CALL sp_store_sales_summary(NULL, NULL);` for read-only examples. For write examples, use disposable test rows and restore any modified values after evidence capture.

| Procedure | Purpose and inputs | Expected result |
|---|---|---|
| `sp_search_products` | Search by optional name, category, and active flag | Matching product rows |
| `sp_record_sale` | Add a sale header and line item using sale ID, date, store, product, and positive quantity | New sale and line item, or a clear validation/constraint error |
| `sp_update_product_price` | Change a product's price using product ID and nonnegative price | Updated product ID and price |
| `sp_set_product_active` | Activate/deactivate using product ID and 0/1 flag | Updated product ID and active flag |
| `sp_update_warranty_status` | Change claim status using claim ID and allowed status | Updated claim ID and status |
| `sp_store_sales_summary` | Summarize sales using optional store ID and year | Grouped sales counts, units, and revenue |

4. Screenshots of the interface menu and its search/report results. The interface also supports inserting products and sales, editing prices and warranty statuses, and deactivating products.
5. A test plan with at least five normal/error cases. Objective: check data loading, searches and changes, and database constraints. A test passes only when observed rows/errors match the expected behavior; otherwise it fails. Suggested cases:

| Feature | Input | Expected result / pass criterion |
|---|---|---|
| Search products | Name `Mac`, active only | Matching active products appear and match the database query |
| Record sale | Existing store/product and quantity 2 | Sale and line item are created and returned |
| Insert product with invalid category | New product ID and nonexistent category ID | Foreign-key error; no product is added |
| Change product price | Existing product and nonnegative price | New price is returned and persists after reconnect |
| Invalid sale quantity | Quantity 0 | Procedure rejects the request; neither sale row is created |
| Deactivate product | Existing product ID | Product becomes inactive and is hidden by the default active search |

6. Baselines for five queries: before adding secondary indexes, record each query's runtime and `EXPLAIN FORMAT=JSON` output.
7. Any group-specific design/management changes, group member names, and the course-required AI-use statement. Suggested disclosure: “AI assisted with drafting and debugging code; the team reviewed the implementation and is responsible for validating the submitted SQL results.”

## Updating the checkout

The launcher does not pull from Git by default. To explicitly run the repository update script first, use `./runScript.sh --update`. `updateProject.sh` changes the `origin` remote to this project's GitHub URL and performs a fast-forward-only pull.

## License

This project is distributed under the MIT License. See [`LICENSE`](LICENSE).
