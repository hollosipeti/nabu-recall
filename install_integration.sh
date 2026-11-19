#!/bin/sh
# Review script before executing; copies ONLY the custom integration to /config.
set -eu
if [ ! -d /config ]; then
  echo "HIBA: /config nem található. Home Assistant Terminalból futtasd." >&2
  exit 1
fi
for command in curl unzip mktemp cp; do
  command -v "$command" >/dev/null 2>&1 || { echo "Hiányzó parancs: $command" >&2; exit 1; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --retry 2 https://github.com/hollosipeti/nabu-recall/archive/refs/heads/main.zip -o "$TMP/repo.zip"
unzip -q "$TMP/repo.zip" -d "$TMP"
SRC="$TMP/nabu-recall-main/custom_components/nabu_recall"
DEST="/config/custom_components/nabu_recall"
[ -f "$SRC/manifest.json" ] || { echo "Hiányzó integráció, leállás." >&2; exit 1; }
mkdir -p "/config/custom_components"
if [ -d "$DEST" ]; then
  BACKUP="$DEST.backup.$(date +%Y%m%d%H%M%S)"
  mv "$DEST" "$BACKUP"
  echo "Korábbi integráció mentése: $BACKUP"
fi
cp -R "$SRC" "$DEST"
echo "Nabu Recall integráció telepítve: $DEST"
echo "Indítsd újra a Home Assistant Core-t, az alkalmazást önmagában nem elég frissíteni."
