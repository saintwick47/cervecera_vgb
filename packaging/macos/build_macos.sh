#!/bin/bash
# Cervecera VGB - Build .app + DMG macOS (repo raíz)
# Uso: bash packaging/macos/build_macos.sh [intel|arm64]
set -euo pipefail
cd "$(dirname "$0")/../.."
ARCH="${1:-arm64}"
version=$(cat packaging/VERSION)
APP_NAME="Cervecera_VGB"

echo "== Ícono .icns =="
rm -rf build/macos_icons.iconset
mkdir -p build/macos_icons.iconset
for s in 16 32 128 256 512; do
  d=$((s * 2))
  sips -z $s $s  packaging/icons/macos/logo.png --out build/macos_icons.iconset/icon_${s}x${s}.png >/dev/null
  sips -z $d $d  packaging/icons/macos/logo.png --out build/macos_icons.iconset/icon_${s}x${s}@2x.png >/dev/null
done
iconutil -c icns build/macos_icons.iconset -o build/app_icon.icns

echo "== PyInstaller (.app) =="
python3 -m PyInstaller --noconfirm --clean --windowed \
    --name "$APP_NAME" \
    --icon "build/app_icon.icns" \
    --osx-bundle-identifier "com.saintwick.cervecera_vgb" \
    --add-data "recetas_base.json:." \
    --add-data "logo.png:." \
    --add-data "logo.ico:." \
    app.py

echo "== DMG =="
STAGE="build/dmg_stage_${ARCH}"
rm -rf "$STAGE"; mkdir -p "$STAGE" dist_installers
cp -R "dist/${APP_NAME}.app" "$STAGE/"
cp packaging/legends/LEYENDA_MACOS.txt "$STAGE/LEYENDA_MACOS.txt"
ln -s /Applications "$STAGE/Aplicaciones"
hdiutil create -volname "Cervecera VGB" \
    -srcfolder "$STAGE" -ov -format UDZO \
    "dist_installers/CerveceraVGB-${version}-macos-${ARCH}.dmg"
echo "INSTALADOR LISTO: dist_installers/CerveceraVGB-${version}-macos-${ARCH}.dmg"
