#!/usr/bin/env bash
# One preview image: each row is one logo at 16 / 32 / 64 / 128 / 256 px (how the dock & title bar see it).
# Run from repo after adding or changing logo-v*.png files.

set -euo pipefail
cd "$(dirname "$0")"
shopt -s nullglob
logos=( logo*.png )
if [[ ${#logos[@]} -eq 0 ]]; then
  echo "No logo*.png files in $(pwd)" >&2
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
rows=()
r=0
for src in "${logos[@]}"; do
  name="${src%.png}"
  magick montage \
    \( -size 152x280 xc:'#2a2a2a' -gravity center -fill white -font Helvetica -pointsize 12 \
       -annotate +0+0 "${name}" \) \
    \( "$src" -background none -gravity center -resize 16x16 -extent 16x16 -bordercolor '#555' -border 1 \) \
    \( "$src" -background none -gravity center -resize 32x32 -extent 32x32 -bordercolor '#555' -border 1 \) \
    \( "$src" -background none -gravity center -resize 64x64 -extent 64x64 -bordercolor '#555' -border 1 \) \
    \( "$src" -background none -gravity center -resize 128x128 -extent 128x128 -bordercolor '#555' -border 1 \) \
    \( "$src" -background none -gravity center -resize 256x256 -extent 256x256 -bordercolor '#555' -border 1 \) \
    -tile 6x1 -geometry '+10+10' -background '#1a1a1a' "$TMP/row_${r}.png"
  rows+=( "$TMP/row_${r}.png" )
  r=$((r + 1))
done

magick montage "${rows[@]}" -tile 1x -geometry '+0+12' -background '#121212' logo_icon_preview.png
echo "Wrote $(pwd)/logo_icon_preview.png (${#logos[@]} logos × 5 sizes)"
