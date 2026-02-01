#!/bin/sh
# Install git hooks to prevent Cursor Co-authored-by in commits
cd "$(dirname "$0")/.." || exit 1
cp scripts/prepare-commit-msg .git/hooks/prepare-commit-msg
chmod +x .git/hooks/prepare-commit-msg
echo "Installed prepare-commit-msg hook. Co-authored-by: Cursor will be stripped from commits."
