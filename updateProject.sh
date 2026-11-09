echo "---------------------------------------------------------------------------"
set -euo pipefail

# Repository location and its canonical remote URL.
REPO_URL="https://github.com/JacobT2006/CS366-Project.git"
PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Ensure this script is running inside a checked-out Git repository.
if ! git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "Error: this script must be run from within a Git repository." >&2
	exit 1
fi

# Require a named branch so the update can be fast-forwarded safely.
BRANCH="$(git -C "$PROJECT_DIR" branch --show-current)"
if [[ -z "$BRANCH" ]]; then
	echo "Error: cannot sync while in detached HEAD state." >&2
	exit 1
fi

# Point origin at the project repository and fast-forward the branch.
if git -C "$PROJECT_DIR" remote get-url origin >/dev/null 2>&1; then
	git -C "$PROJECT_DIR" remote set-url origin "$REPO_URL"
else
	git -C "$PROJECT_DIR" remote add origin "$REPO_URL"
fi

echo "Fetching latest changes for '$BRANCH'..."
git -C "$PROJECT_DIR" pull --ff-only origin "$BRANCH"
echo "Sync complete."
echo "---------------------------------------------------------------------------"
