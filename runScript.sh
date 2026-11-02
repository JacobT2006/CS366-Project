#!/usr/bin/env bash
# ./runScript.sh              Check prerequisites, start MariaDB, prepare the database, and run the app.
# ./runScript.sh --reset      Rebuild the database tables.
# ./runScript.sh --update     Pull the latest project changes before starting.
# ./runScript.sh stop         Shut down this project's local MariaDB server.

set -euo pipefail

cd "$(dirname "$0")"
PATH="$PATH:/usr/sbin:/usr/local/sbin:/opt/homebrew/bin"

db_name="retailInfo_db"
port="${DB_PORT:-3307}"
if [[ ! "$port" =~ ^[0-9]+$ ]]; then
    echo "DB_PORT must be a number from 1 to 65535." >&2
    exit 2
fi
port_number=$((10#$port))
if (( port_number < 1 || port_number > 65535 )); then
    echo "DB_PORT must be a number from 1 to 65535." >&2
    exit 2
fi
port="$port_number"
state_dir="${XDG_DATA_HOME:-$HOME/.local/share}/$db_name"
data_dir="$state_dir/data"
dbSocket="$state_dir/mariadb.sock"
pid_file="$state_dir/mariadb.pid"
log_file="$state_dir/mariadb.log"
reset=0
update=0

find_bin() {
    local binary
    for binary in "$@"; do
        if command -v "$binary" >/dev/null 2>&1; then
            command -v "$binary"
            return 0
        fi
    done
    return 1
}

if [ "${1:-}" = "stop" ]; then
    admin_bin=$(find_bin mariadb-admin mysqladmin) || {
        echo "MariaDB admin tool was not found." >&2
        exit 1
    }
    if "$admin_bin" --no-defaults -uroot --socket="$dbSocket" ping >/dev/null 2>&1; then
        "$admin_bin" --no-defaults -uroot --socket="$dbSocket" shutdown
        echo "MariaDB stopped."
    else
        echo "Local MariaDB is not running."
    fi
    exit 0
fi

for argument in "$@"; do
    case "$argument" in
        --reset) reset=1 ;;
        --update) update=1 ;;
        --help|-h)
            sed -n '2,5p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $argument" >&2
            echo "Usage: ./runScript.sh [--reset] [--update] | stop" >&2
            exit 2
            ;;
    esac
done

if [ -x "$PWD/.venv/bin/python" ]; then
    python_bin="$PWD/.venv/bin/python"
else
    python_bin=$(find_bin python3) || {
        echo "Python 3.8 or newer was not found. Please install it and try again." >&2
        exit 1
    }
fi
if ! "$python_bin" -c 'import sys; sys.exit(sys.version_info < (3, 8))'; then
    echo "Python 3.8 or newer is required; found $("$python_bin" --version)." >&2
    exit 1
fi
echo "$("$python_bin" --version) is installed"
if ! "$python_bin" -c 'import mariadb' >/dev/null 2>&1; then
    echo "MariaDB Connector/Python is missing. Run: python3 -m pip install -r requirements.txt" >&2
    exit 1
fi

mariadb_bin=$(find_bin mariadb) || {
    echo "MariaDB was not found. Please install MariaDB and try again." >&2
    exit 1
}
echo "$("$mariadb_bin" --version | cut -c 1-27) is installed"

server_bin=$(find_bin mariadbd mysqld) || {
    echo "MariaDB server was not found. Install the MariaDB server package and try again." >&2
    exit 1
}
admin_bin=$(find_bin mariadb-admin mysqladmin) || {
    echo "MariaDB admin tool was not found. Install the MariaDB server package and try again." >&2
    exit 1
}

if [ ! -d "$data_dir/mysql" ]; then
    install_db_bin=$(find_bin mariadb-install-db mysql_install_db) || {
        echo "MariaDB install-db tool was not found. Install the MariaDB server package and try again." >&2
        exit 1
    }
fi

if [ "$update" -eq 1 ]; then
    if [ ! -f updateProject.sh ]; then
        echo "updateProject.sh was not found." >&2
        exit 1
    fi
    bash ./updateProject.sh
fi

for required_file in \
    createDB.sql InsertTables.sql stored_procedures.sql load_data.py \
    backEnd.py frontEnd.py query_catalog.py queries.sql \
    apple_db/category.csv apple_db/stores.csv apple_db/products.csv \
    apple_db/sales.csv apple_db/warranty.csv "apple_db/Apple 2009-2024.csv"; do
    if [ ! -f "$required_file" ]; then
        echo "Required project file not found: $required_file" >&2
        exit 1
    fi
done

admin() {
    "$admin_bin" --no-defaults -uroot --socket="$dbSocket" "$@"
}

sql() {
    "$mariadb_bin" --no-defaults -uroot --socket="$dbSocket" --local-infile=1 "$@"
}

mkdir -p "$state_dir"
if [ ! -d "$data_dir/mysql" ]; then
    echo "Initialising local MariaDB data directory..."
    "$install_db_bin" --no-defaults --datadir="$data_dir" --user="$(id -un)" \
        --auth-root-authentication-method=normal >"$log_file" 2>&1 || {
        echo "Initialisation failed; see $log_file" >&2
        exit 1
    }
fi

if admin ping >/dev/null 2>&1; then
    echo "Local MariaDB already running."
else
    echo "Starting local MariaDB on 127.0.0.1:$port ..."
    nohup "$server_bin" --no-defaults --datadir="$data_dir" --socket="$dbSocket" \
        --pid-file="$pid_file" --port="$port" --bind-address=127.0.0.1 \
        --local-infile=1 --character-set-server=utf8mb4 >>"$log_file" 2>&1 &
    server_pid=$!
    for ((attempt = 1; attempt <= 30; attempt++)); do
        if admin ping >/dev/null 2>&1; then
            break
        fi
        if ! kill -0 "$server_pid" 2>/dev/null; then
            echo "MariaDB exited during startup; see $log_file" >&2
            exit 1
        fi
        sleep 1
    done
    if ! admin ping >/dev/null 2>&1; then
        echo "MariaDB did not start within 30 seconds; see $log_file" >&2
        exit 1
    fi
fi

if [ ! -f createDB.sql ] || [ ! -f InsertTables.sql ]; then
    echo "createDB.sql or InsertTables.sql was not found." >&2
    exit 1
fi

sql < createDB.sql
table_count=$(sql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$db_name';")
if [ "$reset" -eq 1 ] || [ "$table_count" -eq 0 ]; then
    echo "Creating tables from InsertTables.sql ..."
    sql < InsertTables.sql
else
    import_table_count=$(sql -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$db_name' AND table_name='dataset_imports';")
    if [ "$import_table_count" -eq 0 ]; then
        echo "The existing database schema is outdated. Back up any needed data, then run ./runScript.sh --reset." >&2
        exit 1
    fi
    echo "Tables already exist ($table_count). Use ./runScript.sh --reset to rebuild."
fi

if [ ! -f stored_procedures.sql ]; then
    echo "stored_procedures.sql was not found." >&2
    exit 1
fi
sql < stored_procedures.sql
echo "Database $db_name is ready."

export dbHost=127.0.0.1 port db_name dbSocket
export dbUser=retail_app DB_PASSWORD=retail_pass
if [ "$reset" -eq 1 ]; then
    "$python_bin" load_data.py --force
else
    "$python_bin" load_data.py
fi
if [ -f frontEnd.py ]; then
    "$python_bin" frontEnd.py
else
    echo "frontEnd.py not found; nothing to run."
fi
