#!/usr/bin/env bash
# ./runScript.sh              Check prerequisites and run the app.
# ./runScript.sh --update     Pull the latest project changes before starting.

set -euo pipefail

cd "$(dirname "$0")"
update=0

for argument in "$@"; do
    case "$argument" in
        --update) update=1 ;;
        --help|-h)
            sed -n '2,3p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown option: $argument" >&2
            echo "Usage: ./runScript.sh [--update]" >&2
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
if ! "$python_bin" -c 'import mariadb, dotenv' >/dev/null 2>&1; then
    echo "Project dependencies are missing. Run: python3 -m pip install -r requirements.txt" >&2
    exit 1
fi

if [ "$update" -eq 1 ]; then
    if [ ! -f updateProject.sh ]; then
        echo "updateProject.sh was not found." >&2
        exit 1
    fi
    bash ./updateProject.sh
fi

exec "$python_bin" frontEnd.py
