# Mantener PC y Android a la par

Las dos versiones de Cervecera VGB tienen que tener **lo mismo**: mismas funciones,
mismos cálculos, mismo recetario. Lo único que cambia es la forma de usarlas
(ventana de escritorio en PC, pantalla táctil en Android).

## Cómo se comprueba

```bash
python herramientas/paridad.py
```

Revisa, y avisa si algo quedó atrás:

1. **Archivos compartidos** que deben ser iguales byte a byte (motor, catálogos,
   recetario, herramientas).
2. **Versión** (`APP_VERSION`) igual en las dos.
3. **Recetario** con la misma cantidad de recetas en las dos.
4. **Base de datos**: las mismas 8 tablas con las mismas columnas.
5. **Funciones** que tienen que existir en las dos apps, aunque se llamen distinto
   (refresco del recetario, levadura al importar, módulo de agua, fórmulas
   elegibles, equipos, insumos).

Termina con `RESULTADO: las dos versiones están a la par ✓` o lista las diferencias.

## Cómo se arregla

```bash
python herramientas/paridad.py --sync                 # copia los compartidos de PC a Android
python herramientas/paridad.py --sync --desde android # al revés
```

Los archivos de **interfaz nunca se copian** (son distintos a propósito). Si una
función nueva es de interfaz, hay que escribirla en las dos: en `app.py` (PC) y en
`main.py` (Android).

## Qué es compartido y qué no

| Compartido (idéntico siempre) | Propio de cada versión |
|---|---|
| `brew_engine.py` (todos los cálculos) | `app.py` (ventana PC) |
| `catalogo_ar.py`, `bjcp_styles.py` | `main.py` (app Android) |
| `export_engine.py` (PDF/BeerXML) | `database.py`, `logger.py` (rutas del sistema) |
| `recetas_base.json`, `recetas_cervecera_vgb.json` | `app_paths.py` (solo PC) |
| `herramientas/` | `ui_base.py`, `build_apk.py` (solo Android) |

## En la build del APK

`build_apk.py` hace esta comprobación antes de compilar (modo estricto, solo los
archivos compartidos): si el motor, los catálogos o el recetario de Android no son
idénticos a los de PC, **frena la build** en vez de publicar un APK desincronizado.

```bash
python herramientas/paridad.py --solo-compartidos
```

## Regla práctica

> Si el cambio toca un cálculo, una receta o el catálogo → va en el archivo
> compartido y las dos versiones lo reciben solas.
> Si el cambio toca la pantalla → hay que hacerlo en `app.py` **y** en `main.py`.

Antes de publicar: `python herramientas/paridad.py` y que dé todo ✓.
