#!/usr/bin/env bash
# ./runScript.sh              Check prerequisites and run the app.
# ./runScript.sh --update     Pull the latest project changes before starting.
# ./runScript.sh --db         Open the MariaDB CLI with settings from .env.

set -euo pipefail

# Run every command from the repository root.
cd "$(dirname "$0")"
update=0
open_db=0

# Read supported command-line options.
for argument in "$@"; do
    case "$argument" in
        --update) update=1 ;;
        --db) open_db=1 ;;
        --help|-h)
            sed -n '2,4p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $argument" >&2
            echo "Usage: ./runScript.sh [--update] [--db]" >&2
            exit 2
            ;;
    esac
done

# Prefer the project's virtual environment when it exists.
if [ -x "$PWD/.venv/bin/python" ]; then
    python_bin="$PWD/.venv/bin/python"
else
    python_bin=$(command -v python3) || {
        echo "Python 3.8 or newer was not found. Please install it and try again." >&2
        exit 1
    }
fi
if ! "$python_bin" -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
    echo "Python 3.8 or newer is required; found $("$python_bin" --version)." >&2
    exit 1
fi
echo "$("$python_bin" --version) is installed"
# Require both the SQL connector and .env reader before continuing.
if ! "$python_bin" -c 'import mariadb, dotenv' >/dev/null 2>&1; then
    echo "Project dependencies are missing. Run: python3 -m pip install -r requirements.txt" >&2
    exit 1
fi

# Optionally synchronize this checkout before database work.
if [ "$update" -eq 1 ]; then
    if [ ! -f updateProject.sh ]; then
        echo "updateProject.sh was not found." >&2
        exit 1
    fi
    bash ./updateProject.sh
fi

# Optionally open a MariaDB CLI session with the private .env settings.
if [ "$open_db" -eq 1 ]; then
    exec "$python_bin" -c '
import os
import shutil
import sys

from dotenv import load_dotenv

load_dotenv()
client = shutil.which("mariadb")
if client is None:
    sys.exit("MariaDB CLI was not found. Install the MariaDB client and try again.")
username = os.environ.get("DATABASE_USERNAME")
if not username:
    sys.exit("DATABASE_USERNAME is missing from .env.")
database = os.environ.get("DATABASE_NAME")
if not database:
    sys.exit("DATABASE_NAME is missing from .env.")
password = os.environ.get("DATABASE_PASSWORD")
if password:
    os.environ["MYSQL_PWD"] = password
os.execv(client, [
    client,
    "--host", os.environ.get("DATABASE_HOST", "140.146.23.39"),
    "--port", os.environ.get("DATABASE_PORT", "3306"),
    "--user", username,
    database,
])
'
fi

# Inspect project tables before offering to run the destructive DDL script.
project_table_count=$("$python_bin" -c '
from dotenv import load_dotenv
load_dotenv()
from load_data import PROJECT_TABLES, connect, existing_project_tables

connection = connect()
try:
    print(len(existing_project_tables(connection)))
finally:
    connection.close()
')
project_table_total=10

run_schema_sql() {
    local sql_file="$1"
    "$python_bin" -c '
import os
import shutil
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()
client = shutil.which("mariadb")
if client is None:
    sys.exit("MariaDB CLI was not found. Install the MariaDB client and try again.")
database = os.environ.get("DATABASE_NAME")
username = os.environ.get("DATABASE_USERNAME")
if not database or not username:
    sys.exit("DATABASE_NAME and DATABASE_USERNAME must be set in .env.")
password = os.environ.get("DATABASE_PASSWORD")
if password:
    os.environ["MYSQL_PWD"] = password
with open(sys.argv[1], "rb") as source:
    subprocess.run([
        client,
        "--host", os.environ.get("DATABASE_HOST", "140.146.23.39"),
        "--port", os.environ.get("DATABASE_PORT", "3306"),
        "--user", username,
        database,
    ], stdin=source, env=os.environ.copy(), check=True)
' "$sql_file"
}

if [ "$project_table_count" -eq 0 ]; then
    echo "No project tables found. Creating project tables..."
    run_schema_sql InsertTables.sql
    run_schema_sql stored_procedures.sql
elif [ "$project_table_count" -eq "$project_table_total" ]; then
    echo "Found all $project_table_total project tables."
    read -r -p "Skip InsertTables.sql? [Y/n] " skip_schema
    case "$skip_schema" in
        ""|y|Y|yes|YES) echo "Skipping InsertTables.sql." ;;
        n|N|no|NO)
            read -r -p "Rebuilding drops and recreates project tables and deletes their data. Continue? [y/N] " rebuild_schema
            case "$rebuild_schema" in
                y|Y|yes|YES)
                    run_schema_sql InsertTables.sql
                    run_schema_sql stored_procedures.sql
                    ;;
                *) echo "Keeping existing project tables." ;;
            esac
            ;;
        *) echo "Please answer yes or no." >&2; exit 2 ;;
    esac
else
    echo "Found $project_table_count of $project_table_total project tables."
    read -r -p "Rebuild all project tables? This drops existing project data. [y/N] " rebuild_schema
    case "$rebuild_schema" in
        y|Y|yes|YES)
            run_schema_sql InsertTables.sql
            run_schema_sql stored_procedures.sql
            ;;
        *) echo "Cannot continue with a partial schema; no tables were changed." >&2; exit 1 ;;
    esac
fi

# Import data if needed, then start the interactive application.
echo "Checking CSV data load..."
"$python_bin" load_data.py
exec "$python_bin" frontEnd.py
