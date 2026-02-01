#!/bin/sh
# Re-push tags in ascending version order so GitHub Releases appear correctly.
# Run AFTER deleting all releases and tags on GitHub manually.
# Usage: ./scripts/reorder-releases.sh [delay_seconds]
# Default delay: 30 seconds between pushes to let each release workflow complete.

set -e
cd "$(dirname "$0")/.."
DELAY="${1:-30}"

TAGS="v8.1.0 v8.1.1 v8.1.2 v9.0.0 v9.0.1 v9.1.0 v9.1.1 v9.1.2 v9.1.3 v9.2.0 v9.2.1 v9.2.2"

echo "Step 1: Delete remote tags (run these first if not done)..."
for tag in $TAGS; do
  echo "  git push origin :refs/tags/$tag"
done

echo ""
echo "Step 2: Re-push tags in order (${DELAY}s delay between each)..."
for tag in $TAGS; do
  echo "Pushing $tag..."
  git push origin "$tag"
  if [ "$tag" != "v9.2.2" ]; then
    echo "Waiting ${DELAY}s..."
    sleep "$DELAY"
  fi
done

echo ""
echo "Done. Set v9.2.2 as 'Latest' on GitHub Releases page."
