#!/bin/bash
# Cervecera VGB - Build paquete .deb (Debian/Ubuntu/Mint/Pop!_OS)
# Uso: bash packaging/linux/build_linux_deb.sh   (repo raíz; espera dist/Cervecera_VGB ya compilado por PyInstaller)
set -euo pipefail
cd "$(dirname "$0")/../.."
version=$(cat packaging/VERSION)
APP=cervecera-vgb
DEST=opt/${APP}
PKGROOT="build/deb_${APP}_${version}"
BUILD_DIR="${PKGROOT}"

rm -rf "$BUILD_DIR"; mkdir -p "$BUILD_DIR"

# ── Estructura del paquete ────────────────────────────────────────────────
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/${DEST}"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$BUILD_DIR/usr/bin"

# Copiar toda la app (onedir de PyInstaller)
cp -r dist/Cervecera_VGB/* "$BUILD_DIR/${DEST}/"
chmod -R a+rX "$BUILD_DIR/${DEST}"

# Ícono y acceso directo
cp packaging/icons/linux/logo.png "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps/${APP}.png"

cat > "$BUILD_DIR/usr/share/applications/${APP}.desktop" <<EOF
[Desktop Entry]
Name=Cervecera VGB
Comment=Asistente cervecero offline (Tinseth, Morey, Palmer, BJCP 2021)
Exec=/opt/${APP}/Cervecera_VGB
Icon=${APP}
Terminal=false
Type=Application
Categories=Utility;Office;
StartupWMClass=Cervecera_VGB
EOF

# Comando en la terminal (cervecera-vgb)
ln -sf "/opt/${APP}/Cervecera_VGB" "$BUILD_DIR/usr/bin/${APP}"

# Tamano instalado (KB)
installed_kb=$(du -sk "$BUILD_DIR/${DEST}" | cut -f1)

cat > "$BUILD_DIR/DEBIAN/control" <<EOF
Package: ${APP}
Version: ${version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: SaintWick <nicoweb45@proton.me>
Installed-Size: ${installed_kb}
Depends: libc6 (>= 2.31), libglib2.0-0
Description: Cervecera VGB - asistente cervecero offline
 App offline para disenar recetas de cerveza con motor Tinseth, Morey y
 Palmer, mas de 80 estilos BJCP 2021, inventario, perfil de agua con pH y
 exportacion PDF/BeerXML. Sin suscripciones y sin nube.
EOF

# md5sums
( cd "$BUILD_DIR" && find "${DEST}" usr -type f -print0 | xargs -0 md5sum | sed "s#  ${DEST}/#  /${DEST}/#; s#  usr/#  /usr/#" > DEBIAN/md5sums )

echo "== Compilando .deb (dpkg-deb) =="
mkdir -p dist_installers
dpkg-deb --build --root-owner-group "$BUILD_DIR" "dist_installers/CerveceraVGB-${version}-x86_64.deb"
echo "INSTALADOR LISTO: dist_installers/CerveceraVGB-${version}-x86_64.deb"
