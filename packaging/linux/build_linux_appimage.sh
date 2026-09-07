#!/bin/bash
# Cervecera VGB - Build AppImage Linux x86_64 (repo raíz)
set -euo pipefail
cd "$(dirname "$0")/../.."
version=$(cat packaging/VERSION)

echo "== PyInstaller (onedir) =="
python3 -m PyInstaller --noconfirm --clean --onedir --windowed \
    --name "Cervecera_VGB" \
    --add-data "recetas_base.json:." \
    --add-data "logo.png:." \
    --add-data "logo.ico:." \
    app.py

echo "== Armar AppDir =="
APPDIR="packaging/linux/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib/cervecera_vgb" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps" \
         "$APPDIR/usr/share/applications"
cp -r dist/Cervecera_VGB/* "$APPDIR/usr/lib/cervecera_vgb/"
cp packaging/linux/AppRun "$APPDIR/AppRun"; chmod +x "$APPDIR/AppRun"
cp packaging/linux/cervecera-vgb.desktop "$APPDIR/cervecera-vgb.desktop"
cp packaging/icons/linux/logo.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/cervecera-vgb.png"
cp packaging/icons/linux/logo.png "$APPDIR/cervecera-vgb.png"

echo "== appimagetool =="
mkdir -p dist_installers
if [ ! -f /tmp/appimagetool ]; then
  curl -sL -o /tmp/appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x /tmp/appimagetool
fi
ARCH=x86_64 /tmp/appimagetool --appimage-extract-and-run "$APPDIR" \
    "dist_installers/CerveceraVGB-${version}-x86_64.AppImage"
echo "INSTALADOR LISTO: dist_installers/CerveceraVGB-${version}-x86_64.AppImage"
