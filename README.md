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
| **macOS** | Release → `CerveceraVGB-*-macos-arm64.dmg` |

> Los instaladores de escritorio se generan automáticamente con GitHub
> Actions (ver `.github/workflows/build-installers.yml`). Cada release
> incluye `checksums.txt` con el SHA-256 de cada archivo.

## 🧪 Funciones

- Editor completo de recetas: maltas, lúpulos (escalonados), levaduras,
  perfil de agua con pH, altitud, ratio L/kg, absorción y hervor. Organizado
  en sub-pestañas (Receta, Agua, Macerado, Hervido, Fermentación, Embotellado).
- Resultados: OG, FG (por atenuación de levadura), ABV, IBU, SRM,
  BU/GU, calorías, aguas con evaporación, pH entrada/maceración/
  post-hervor/final y corrección con ácido láctico. Incluye radar de perfil
  sensorial y curva de gravedad estimada (OG→FG) en tiempo real.
- Calculadora de priming/carbonatación en botella (Embotellado), con fórmula
  estándar Zahm & Nagel / Hall 1995 y factor según tipo de azúcar.
- Catálogo argentino de maltas, lúpulos, levaduras y aguas de Córdoba.
- **Insumos e Inventario** unificados en una sola sección: catálogo editable
  por tipo, alta/consumo de stock con Kardex de movimientos, valorización
  en $, alerta de stock bajo y vencimientos, más importación rápida
  "Pegar productos" (detecta nombre/cantidad/unidad y matchea con el catálogo).
- **Equipos** con perfiles guardables y parámetros extendidos de maceración,
  mermas/pérdidas y pH objetivo por etapa.
- **Comunidad**: compartir recetas propias (vía GitHub, sin backend propio) y
  descargar las que compartieron otros usuarios de la app.
- **Química del agua**: perfiles objetivo por estilo, sales (yeso, CaCl₂, epsom,
  sal, bicarbonato), dilución con ósmosis inversa y relación SO₄:Cl.
- Comparador BJCP 2021, y exportación PDF/BeerXML.
- Fórmulas elegibles: IBU Tinseth/Rager (con whirlpool real), FG Normal/Simple,
  ABV Standard/Alternative, color Morey + EBC.
- Tema visual propio (BrewTk Utilitarian, `Tema brewtk.json`).

## 📖 Recetario

- **66 recetas** con su estilo BJCP y sus ingredientes reales.
- Los números están **verificados contra Brew-o-Matic**: las 66 recetas se
  recalcularon con nuestro motor y coinciden con las originales (desvío máximo
  0,0009 en OG/FG).
- La app **refresca sola** las recetas del recetario cuando mejoran, y **nunca**
  toca las recetas creadas o editadas por el usuario.
- En `herramientas/` están los scripts para importar recetas de Brew-o-Matic,
  reemplazar las genéricas por reales y generar el catálogo descargable
  (ver `herramientas/LEEME_importar_brewomatic.md`).

## 🔄 PC y Android siempre a la par

Las dos versiones comparten el mismo motor, catálogos y recetario; solo cambia la
interfaz. Para comprobar que ninguna quedó atrás:

```bash
python herramientas/paridad.py            # verifica todo
python herramientas/paridad.py --sync     # copia los archivos compartidos de PC a Android
```

Compara los módulos compartidos, la versión, la cantidad de recetas, el esquema de
la base de datos y que cada función exista en las dos apps. La build del APK hace
esta comprobación sola antes de compilar y **frena** si algo no coincide
(ver `herramientas/LEEME_paridad.md`).

## 🗂️ Estructura del repositorio

- `app.py` y módulos `*.py` → app de escritorio (PC).
- `packaging/` → scripts e íconos para generar los instaladores.
- `test_cervecera.py` → suite de tests (`python -m unittest test_cervecera.py -v`).

## 🚀 Publicar instaladores

Ver `README_INSTALADORES.md` (paso a paso para generar y adjuntar los
instaladores al release desde GitHub Actions).

## 📧 Soporte
nicoweb45@proton.me (Asunto: beer_vgb)

## 📝 Historial de cambios (CHANGELOG)

### 2026-09-20 11:19 — archivos corregidos

- Archivos: README.md, app.py, database.py, test_cervecera.py, Tema brewtk.json, app_gestion.py, archivos proyecto y comandos..txt, beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-20 11:15 — archivos corregidos

- Archivos: app.py, app_gestion.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, Tema brewtk.json, .gitignore, README.md, archivos proyecto y comandos..txt, beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-20 11:12 — archivos corregidos

- Archivos: app.py, app_gestion.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, Tema brewtk.json, .gitignore, README.md, "Tema brewtk.json", "archivos proyecto y comandos..txt", beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-20 16:45 — feat: Comunidad, Insumos+Inventario con Kardex, Equipos extendido, sub-pestañas de Receta + priming + tema BrewTk

- Archivos: app.py, app_gestion.py, database.py, "Tema brewtk.json", README.md


### 2026-09-20 11:06 — version nueva con funciones mejoradas

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, .gitignore, README.md, "Tema brewtk.json", app_gestion.py, "archivos proyecto y comandos..txt", beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-19 19:16 — reestructuracion y nuevas funciones

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, .gitignore, README.md, app_gestion.py, "archivos proyecto y comandos..txt", beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-18 17:59 — actualizacion app.py con menu

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, .gitignore, README.md, "archivos proyecto y comandos..txt", beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-17 13:29 — fix: database.py v4 - duplicados de receta a logger.debug (silencia spam de warnings)

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, .gitignore, README.md, "archivos proyecto y comandos..txt", beer_vgb.png, build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, packaging/icons/linux/logo-512.png, packaging/icons/logo-128.png, packaging/icons/logo-16.png, packaging/icons/logo-256.png, packaging/icons/logo-32.png, packaging/icons/logo-48.png, packaging/icons/logo-512.png, packaging/icons/logo-64.png, recetario_vgb.json, recetas_base_genericas.json


### 2026-09-17 13:05 — fix: database.py v4 - duplicados de receta a logger.debug (silencia spam de warnings)

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, database.py, README.md, "archivos proyecto y comandos..txt", build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, recetario_vgb.json, recetas_base_genericas.json, subir_github.py


### 2026-09-17 13:03 — fix: database.py v4 - duplicados de receta a logger.debug (silencia spam de warnings)

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, README.md, database.py, "archivos proyecto y comandos..txt", build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, recetario_vgb.json, recetas_base_genericas.json, subir_github.py


### 2026-09-17 12:19 — feat: auto-amargor (Tinseth/Rager) + calibración Dry Irish Stout + layout v16.1

- Archivos: app.py, brew_engine.py, catalogo_ar.py, test_cervecera.py, "archivos proyecto y comandos..txt", build.bat, build.sh, herramientas/recetario_real.json, herramientas/urls_brewomatic.txt, recetario_vgb.json, recetas_base_genericas.json, subir_github.py


### 2026-09-17 12:14 — feat: auto-amargor (Tinseth/Rager) + calibración Dry Irish Stout + layout v16.1

- Archivos: README.md, comitgit.py


### 2026-09-17 12:03 — feat: auto-amargor (Tinseth/Rager) + calibración Dry Irish Stout + layout v16.1

- Archivos: .github/workflows/build-installers.yml, README.md, app.py, brew_engine.py, catalogo_ar.py, comitgit.py, test_cervecera.py
