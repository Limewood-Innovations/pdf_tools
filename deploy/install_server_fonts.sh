#!/usr/bin/env bash
# Idempotent server provisioning for pdf_tools font handling.
# Installs MS core fonts + Carlito and the cidfmap drop-in that maps
# Arial / Times New Roman / Calibri to local TrueType files.
# Without this, Ghostscript silently substitutes embedded Arial subset
# fonts with DroidSansFallback and renders broken glyphs.
#
# Usage (Ubuntu/Debian, run as root or via sudo):
#   sudo bash deploy/install_server_fonts.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CIDFMAP_SRC="${SCRIPT_DIR}/95-arial-liberation.conf"
CIDFMAP_DST="/etc/ghostscript/cidfmap.d/95-arial-liberation.conf"

if [[ $EUID -ne 0 ]]; then
    echo "Must be run as root (use sudo)." >&2
    exit 1
fi

echo "==> Pre-accept ttf-mscorefonts EULA"
echo "msttcorefonts msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections
echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections

echo "==> Install font packages"
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    fonts-liberation \
    ttf-mscorefonts-installer \
    fonts-crosextra-carlito

echo "==> Install cidfmap drop-in"
install -m 0644 -o root -g root "${CIDFMAP_SRC}" "${CIDFMAP_DST}"

echo "==> Regenerate Ghostscript fontmap"
/usr/sbin/update-gsfontmap

echo "==> Verify mappings present in /var/lib/ghostscript/fonts/cidfmap"
for token in ArialMT TimesNewRoman Calibri; do
    count=$(grep -c "${token}" /var/lib/ghostscript/fonts/cidfmap || true)
    printf "  %-15s %s entries\n" "${token}:" "${count}"
done

echo "==> Done."
