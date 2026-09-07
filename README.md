# Cervecera VGB 🍺

Cervecera VGB: App **offline** para diseñar recetas con motor profesional
(Tinseth/IBU, Morey/SRM, Palmer/pH y correcciones por altitud), valida
+80 estilos BJCP 2021, gestiona inventario, estima el pH con perfil de
agua (Ca/Mg/HCO₃/pH) y exporta a PDF/BeerXML. Precisión técnica
profesional, sin suscripciones ni nube.

## 📲 Plataformas

| Plataforma | Cómo obtenerla |
|---|---|
| **Android (APK)** | Release → `CerveceraVGB.apk` (instalación directa) |
| **Windows** | Release → `CerveceraVGB-Setup-*.exe` (instalador con acceso directo y logo en el escritorio) |
| **Linux** | Release → `CerveceraVGB-*-x86_64.AppImage` |
| **macOS** | Release → `CerveceraVGB-*-macos-intel.dmg` / `-arm64.dmg` |

> Los instaladores de escritorio se generan automáticamente con GitHub
> Actions (ver `.github/workflows/build-installers.yml`). Cada release
> incluye `checksums.txt` con el SHA-256 de cada archivo.

## 🧪 Funciones

- Editor completo de recetas: maltas, lúpulos (escalonados), levaduras,
  perfil de agua con pH, altitud, ratio L/kg, absorción y hervor.
- Resultados: OG, FG (por atenuación de levadura), ABV, IBU, SRM,
  BU/GU, calorías, aguas con evaporación, pH entrada/maceración/
  post-hervor/final y corrección con ácido láctico.
- Catálogo argentino de maltas, lúpulos, levaduras y aguas de Córdoba.
- Comparador BJCP 2021, inventario inteligente y exportación PDF/BeerXML.

## 🗂️ Estructura del repositorio

- `app.py` y módulos `*.py` → app de escritorio (PC).
- `packaging/` → scripts e íconos para generar los instaladores.
- `test_cervecera.py` → suite de tests (`python -m unittest test_cervecera.py -v`).

## 🚀 Publicar instaladores

Ver `README_INSTALADORES.md` (paso a paso para generar y adjuntar los
instaladores al release desde GitHub Actions).

## 📧 Soporte
nicoweb45@proton.me (Asunto: beer_vgb)
