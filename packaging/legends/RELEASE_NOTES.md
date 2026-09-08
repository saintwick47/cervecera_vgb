# Cervecera VGB — Instalación por plataforma (v1.0.0)

Versión PC (Windows / Linux / macOS) en paridad funcional con la app Android.
Diferencia: solo cambia el medio de uso.

## 📱 Android
- `CerveceraVGB.apk` → instalar directo (permitir orígenes desconocidos).

## 🪟 Windows
- `CerveceraVGB-Setup-1.0.0.exe` → instalador Inno: elegís carpeta, crea
  **acceso directo en el escritorio con el logo** y menú Inicio. Incluye desinstalador.

## 🐧 Linux — instalación por distribución

| Distribución | Formato | Cómo se instala |
|---|---|---|
| Ubuntu / Debian / Mint / Pop!_OS / elementary | `.deb` ⭐ | **Doble clic → Instalar → menú de aplicaciones** (con icono, sin terminal) |
| Fedora / RHEL / CentOS / openSUSE | `.rpm` | `sudo dnf install ./CerveceraVGB-1.0.0-x86_64.rpm` (o doble clic en el instalador) |
| Arch / Manjaro / EndeavourOS | `PKGBUILD` | Copiá `packaging/arch/` y `makepkg -si` (instala en el menú) |
| Otras distros | `.AppImage` | `chmod +x` y doble clic (o `--appimage-extract-and-run`) |

- Archivos Linux: `CerveceraVGB-1.0.0-x86_64.deb` · `…-x86_64.rpm` · `…-x86_64.AppImage`.

## 🍎 macOS
- `CerveceraVGB-1.0.0-macos-arm64.dmg` (Apple Silicon) → arrastrar a Aplicaciones.
- Variante Intel (x86_64): próximamente.

## ✅ Funciones (iguales en todas las plataformas)
Recetas completas (maltas, lúpulos, levaduras, perfil de agua con pH, altitud,
ratio, absorción y hervor), motor profesional (OG, FG, ABV, IBU, SRM, BU/GU,
calorías, aguas con evaporación, pH y ácido láctico), catálogo argentino,
comparador BJCP 2021, inventario y exportación PDF/BeerXML.

## 🔒 Integridad
Cada instalador se publica con su checksum SHA‑256 en `checksums.txt`.

## 📧 Soporte
nicoweb45@proton.me (Asunto: beer_vgb)
