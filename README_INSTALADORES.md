# Cervecera VGB — Instaladores de escritorio (Windows / Linux / macOS)

El código de la versión PC vive en la raíz de este repositorio. Con un
clic en **Actions** se generan los instaladores en la nube (GitHub) y se
adjuntan solos al release indicado:

| Sistema | Archivos que se generan |
|---|---|
| Windows | `CerveceraVGB-Setup-1.0.0.exe` (instalador con logo en el escritorio) |
| Linux (Debian/Ubuntu/Mint/Pop!) | `CerveceraVGB-1.0.0-x86_64.deb` ⭐ (doble clic → instalar → menú) |
| Linux (Fedora/RHEL/openSUSE) | `CerveceraVGB-1.0.0-x86_64.rpm` |
| Linux (Arch/Manjaro) | `packaging/arch/PKGBUILD` |
| Linux (otras) | `CerveceraVGB-1.0.0-x86_64.AppImage` |
| macOS | `CerveceraVGB-1.0.0-macos-arm64.dmg` (Apple Silicon) |
| Todos | `checksums.txt` (SHA-256 de cada instalador) |

## Pasos para publicar (mantenimiento)

1. Trabajar sobre la rama `main`, subir cambios y disparar la Action:
   `Actions → Build instaladores → Run workflow → tag v1.0.0 → Run`.
2. Al terminar, los instaladores y `checksums.txt` aparecen adjuntos en
   https://github.com/saintwick47/cervecera_vgb/releases/tag/v1.0.0
3. (Opcional) Editá el release y pegá la descripción de
   `packaging/legends/RELEASE_NOTES.md`.

> Tip: si publicás un **release nuevo** (ej. tag `v1.1.0`) con sus notas,
> el workflow se dispara solo y adjunta todo a ese release.

## Compilar en tu máquina (sin GitHub Actions)

- Windows: instalá Python 3.12 + Inno Setup 6 → `packaging/windows/build_windows.ps1`.
- Linux: `bash packaging/linux/build_linux_appimage.sh` (AppImage),
  `bash packaging/linux/build_linux_deb.sh` (deb) y
  `bash packaging/linux/build_linux_rpm.sh` (rpm; requiere rpmbuild).
- macOS: `bash packaging/macos/build_macos.sh intel|arm64`.
- Arch: `cd packaging/arch && makepkg -si`.
- Luego subí los archivos de `dist_installers/` (o usá la web de GitHub).

## Notas
- El ícono de escritorio usa el logo oficial (`logo.png` / `app_icon.ico`).
- En la primera instalación macOS pedirá confirmar la app descargada
  (clic derecho → Abrir). En Linux, el `.deb`/`.rpm`/PKGBUILD dejan la
  app en el menú de aplicaciones con su icono; el **AppImage** (otras
  distros) requiere `chmod +x`.
- Los datos se guardan en la carpeta del **usuario** (nunca en
  Program Files ni en la carpeta de la app), así que no da errores de permisos.
