#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/JacobT2006/CS366-Project.git"
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "Error: this script must be run from within a Git repository." >&2
	exit 1
fi

BRANCH="$(git -C "$PROJECT_DIR" branch --show-current)"
if [[ -z "$BRANCH" ]]; then
	echo "Error: cannot sync while in detached HEAD state." >&2
	exit 1
fi

if git -C "$PROJECT_DIR" remote get-url origin >/dev/null 2>&1; then
	git -C "$PROJECT_DIR" remote set-url origin "$REPO_URL"
else
	git -C "$PROJECT_DIR" remote add origin "$REPO_URL"
fi

echo "Fetching latest changes for '$BRANCH'..."
git -C "$PROJECT_DIR" pull --ff-only origin "$BRANCH"
echo "Sync complete."
