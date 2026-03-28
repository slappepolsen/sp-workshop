#!/usr/bin/env bash
# Regenerate app icons (PNG, ICO, ICNS) for SP Workshop from a square-friendly logo PNG.
#
# Usage (from repo): ./media/build_app_icon.sh [source.png]
# Default source: icon-source.png in this directory. Writes icon.png, icon.ico, and icon.icns (macOS only).
# Compare raw logos at small sizes: ./preview_logo_icons.sh
#
# Requires: ImageMagick (magick), macOS iconutil for .icns. On Linux/Windows, PNG+ICO are still produced.
# iconutil can fail on 16-bit/P3 PNG sources; this script forces 8-bit RGBA for the iconset. Run on a real macOS
# host for .icns (some sandboxes block iconutil even when the iconset is valid).
#
# macOS Dock uses a squircle mask. Logos that fill the whole canvas look oversized next to Apple icons.
# Shrink artwork inside the square with ICON_INSET_PERCENT (default 72 = logo fits in 72% of edge, rest transparent).
# Example: ICON_INSET_PERCENT=68 ./build_app_icon.sh my-logo.png
#
# Qt / python app.py often shows a sharp square in the Dock (no system squircle). Other apps bake a rounded
# “plate” into the PNG. ICON_PLATE=light (default) draws a light gray rounded rectangle behind the logo;
# use ICON_PLATE=none for fully transparent corners, ICON_PLATE=dark for a dark plate.
# Optional: ICON_PLATE_COLOR='#f5f5f7' with ICON_PLATE=light

set -euo pipefail
cd "$(dirname "$0")"
SRC=${1:-"icon-source.png"}
BASE="icon"
ICON_INSET_PERCENT="${ICON_INSET_PERCENT:-72}"
ICON_PLATE="${ICON_PLATE:-light}"
if [[ ! -f "$SRC" ]]; then
  echo "Source not found: $SRC" >&2
  exit 1
fi

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
ICONSET="$TMP/AppIcon.iconset"
mkdir "$ICONSET"

square_resize() {
  local w=$1 out=$2
  local inner=$(( w * ICON_INSET_PERCENT / 100 ))
  [[ "$inner" -lt 1 ]] && inner=1
  # ~22% corner radius matches Apple-style app icons at a glance (not a true superellipse).
  local rad=$(( w * 22 / 100 ))
  [[ "$rad" -lt 1 ]] && rad=1

  local plate_fill=""
  case "$ICON_PLATE" in
    none|off|transparent) plate_fill="" ;;
    dark) plate_fill="${ICON_PLATE_COLOR:-#1c1c1e}" ;;
    light|*) plate_fill="${ICON_PLATE_COLOR:-#ebebf0}" ;;
  esac

  # 8-bit RGBA, no palette: iconutil rejects 16-bit and palette-indexed PNGs.
  if [[ -z "$plate_fill" ]]; then
    magick -size "${w}x${w}" xc:none \
      \( "$SRC" -background none -resize "${inner}x${inner}" \) \
      -gravity center -compose Over -composite -alpha on -type TrueColorAlpha -depth 8 "$out"
  else
    magick -size "${w}x${w}" xc:none \
      \( -size "${w}x${w}" xc:none -fill "$plate_fill" \
         -draw "roundrectangle 0,0 $((w-1)),$((w-1)) ${rad},${rad}" \) \
      \( "$SRC" -background none -resize "${inner}x${inner}" \) \
      -gravity center -compose Over -composite -alpha on -type TrueColorAlpha -depth 8 "$out"
  fi
}

square_resize 1024 "${BASE}.png"

magick "${BASE}.png" -define icon:auto-resize=16,32,48,64,128,256 "${BASE}.ico"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Skipping ${BASE}.icns (iconutil is macOS-only). Wrote ${BASE}.png and ${BASE}.ico from $SRC"
  exit 0
fi

square_resize 16 "$ICONSET/icon_16x16.png"
square_resize 32 "$ICONSET/icon_16x16@2x.png"
square_resize 32 "$ICONSET/icon_32x32.png"
square_resize 64 "$ICONSET/icon_32x32@2x.png"
square_resize 128 "$ICONSET/icon_128x128.png"
square_resize 256 "$ICONSET/icon_128x128@2x.png"
square_resize 256 "$ICONSET/icon_256x256.png"
square_resize 512 "$ICONSET/icon_256x256@2x.png"
square_resize 512 "$ICONSET/icon_512x512.png"
square_resize 1024 "$ICONSET/icon_512x512@2x.png"

iconutil -c icns -o "${BASE}.icns" "$ICONSET"
echo "Wrote ${BASE}.png, ${BASE}.ico, ${BASE}.icns from $SRC (plate=$ICON_PLATE, inset=${ICON_INSET_PERCENT}%)"
