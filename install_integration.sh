#!/bin/sh
# Review script before executing; copies ONLY the custom integration to /config.
set -eu
# Optional controlled branch selection for one-at-a-time staging.
BRANCH="${1:-main}"
case "$BRANCH" in
  main|stable-2026-11-24-before-v2|dev-2.0.3-qa|stable-2.0.6-before-3.0.0) ;;
  *) echo "HIBA: nem engedélyezett ág." >&2; exit 1 ;;
esac
if [ ! -d /config ]; then
  echo "HIBA: /config nem található. Home Assistant Terminalból futtasd." >&2
  exit 1
fi
for command in curl unzip mktemp cp mv basename date; do
  command -v "$command" >/dev/null 2>&1 || { echo "Hiányzó parancs: $command" >&2; exit 1; }
done
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
curl -fsSL --retry 2 https://github.com/hollosipeti/nabu-recall/archive/refs/heads/${BRANCH}.zip -o "$TMP/repo.zip"
unzip -q "$TMP/repo.zip" -d "$TMP"
SRC="$TMP/nabu-recall-${BRANCH}/custom_components/nabu_recall"
DEST="/config/custom_components/nabu_recall"
[ -f "$SRC/manifest.json" ] || { echo "Hiányzó integráció, leállás." >&2; exit 1; }
mkdir -p "/config/custom_components"
# HA scans every folder inside custom_components as an integration.
# Dotted backup directories (nabu_recall.backup.TIMESTAMP) cause an import
# failure: "No module named 'custom_components.nabu_recall.backup'".
BACKUP_ROOT="/config/nabu_recall_backups"
mkdir -p "$BACKUP_ROOT"
for OLD in /config/custom_components/nabu_recall.backup.*; do
  [ -d "$OLD" ] || continue
  OLD_DEST="$BACKUP_ROOT/$(basename "$OLD")"
  if [ -e "$OLD_DEST" ]; then
    echo "HIBA: Mentési névütközés, a korábbi mentés érintetlen: $OLD" >&2
    exit 1
  fi
  mv "$OLD" "$OLD_DEST"
  echo "Korábbi hibás helyű mentés áthelyezve: $OLD_DEST"
done
if [ -d "$DEST" ]; then
  BACKUP="$BACKUP_ROOT/nabu_recall.$(date +%Y%m%d%H%M%S)"
  if [ -e "$BACKUP" ]; then
    echo "HIBA: Mentési névütközés: $BACKUP" >&2
    exit 1
  fi
  mv "$DEST" "$BACKUP"
  echo "Korábbi integráció mentése: $BACKUP"
fi
cp -R "$SRC" "$DEST"
echo "Nabu Recall integráció telepítve: $DEST (ág: $BRANCH)"
echo "Telepített manifest: $(cat "$DEST/manifest.json")"
[ -f "$DEST/brand/icon.png" ] && echo "Integráció ikon: telepítve" || echo "FIGYELEM: integráció ikon hiányzik!"
echo "Indítsd újra a Home Assistant Core-t, az alkalmazást önmagában nem elég frissíteni."
