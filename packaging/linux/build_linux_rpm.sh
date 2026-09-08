#!/bin/bash
# Cervecera VGB - Build paquete .rpm (Fedora/RHEL/openSUSE)
# Uso: bash packaging/linux/build_linux_rpm.sh   (repo raíz; espera dist/Cervecera_VGB de PyInstaller)
# Requiere: rpmbuild (CI: sudo apt install rpm)
set -euo pipefail
cd "$(dirname "$0")/../.."
version=$(cat packaging/VERSION)
APP=cervecera-vgb
ROOT="$(pwd)/build/rpmroot"
TOP="$(pwd)/rpmbuild"

rm -rf "$ROOT"; mkdir -p "$ROOT/opt/${APP}" "$ROOT/usr/share/applications" \
                 "$ROOT/usr/share/icons/hicolor/256x256/apps" "$ROOT/usr/bin"
cp -r dist/Cervecera_VGB/* "$ROOT/opt/${APP}/"
chmod -R a+rX "$ROOT/opt/${APP}"
cp packaging/icons/linux/logo.png "$ROOT/usr/share/icons/hicolor/256x256/apps/${APP}.png"

cat > "$ROOT/usr/share/applications/${APP}.desktop" <<EOF
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
ln -sf "/opt/${APP}/Cervecera_VGB" "$ROOT/usr/bin/${APP}"

mkdir -p "$TOP/SPECS" "$TOP/BUILD" "$TOP/RPMS" "$TOP/SOURCES" "$TOP/SRPMS"
cat > "$TOP/SPECS/${APP}.spec" <<EOF
Name: ${APP}
Version: ${version}
Release: 1
Summary: Cervecera VGB - asistente cervecero offline
License: Proprietary
BuildArch: x86_64
AutoReqProv: no

%description
App offline para disenar recetas de cerveza con motor Tinseth, Morey y
Palmer, mas de 80 estilos BJCP 2021, inventario, perfil de agua con pH y
exportacion PDF/BeerXML. Sin suscripciones y sin nube.

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}/opt/${APP}
cp -a ${ROOT}/opt/${APP}/. %{buildroot}/opt/${APP}/
mkdir -p %{buildroot}/usr/share/applications
cp -a ${ROOT}/usr/share/applications/${APP}.desktop %{buildroot}/usr/share/applications/
mkdir -p %{buildroot}/usr/share/icons/hicolor/256x256/apps
cp -a ${ROOT}/usr/share/icons/hicolor/256x256/apps/${APP}.png %{buildroot}/usr/share/icons/hicolor/256x256/apps/
mkdir -p %{buildroot}/usr/bin
ln -sf /opt/${APP}/Cervecera_VGB %{buildroot}/usr/bin/${APP}

%files
/opt/${APP}
/usr/share/applications/${APP}.desktop
/usr/share/icons/hicolor/256x256/apps/${APP}.png
/usr/bin/${APP}

%postun
if [ \$1 -eq 0 ]; then
  rm -f /etc/ld.so.cache 2>/dev/null || true
fi
EOF

echo "== Compilando .rpm (rpmbuild) =="
rpmbuild --define "_topdir $TOP" -bb "$TOP/SPECS/${APP}.spec"
mkdir -p dist_installers
cp "$TOP/RPMS/x86_64/${APP}-${version}-1.x86_64.rpm" "dist_installers/CerveceraVGB-${version}-x86_64.rpm"
echo "INSTALADOR LISTO: dist_installers/CerveceraVGB-${version}-x86_64.rpm"
