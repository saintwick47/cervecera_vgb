# Importar recetas de Brew‑o‑Matic

[Brew‑o‑Matic](https://www.brew-o-matic.com.ar) (Lautaro Cozzani / Somos Cerveceros, licencia MIT)
guarda cada receta en una dirección como:

```
https://www.brew-o-matic.com.ar/#/recipe/clone/RBKSourJunio2026Jabalinum-5bb3fd021c1071000401038a-1782315265480
```

Esta herramienta copia esas recetas al formato que importa Cervecera VGB (PC y Android).

## Uso

```bash
# una receta (URL o ID)
python herramientas/importar_brewomatic.py "https://www.brew-o-matic.com.ar/#/recipe/clone/XXXX"

# varias a la vez
python herramientas/importar_brewomatic.py URL1 URL2 URL3 -o recetas_brewomatic.json

# desde un archivo de texto, una URL por línea (admite líneas con #)
python herramientas/importar_brewomatic.py lista.txt -o recetas_brewomatic.json
```

El JSON resultante se importa en la app con **📂 Importar JSON** (PC: menú Archivo/Utilidades · Android: pestaña Cerveza).
Las recetas que ya existen no se duplican.

## Qué se convierte

| Brew‑o‑Matic | Cervecera VGB |
|---|---|
| `BATCH_SIZE` | litros del lote |
| `FG` | FG estimada |
| `FERMENTABLES` (POTENTIAL en PPG) | extracto en L°/kg (`× 8,345`) |
| `FERMENTABLES.COLOR` | color (SRM/Lovibond) |
| `HOPS.AMOUNT` (kg) | gramos |
| `HOPS.ALPHA` / `TIME` / `FORM` | alfa, minutos, pellet/flor |
| `YEASTS.ATTENUATION` | atenuación de la levadura |
| `STYLE.NAME` | estilo |

> Brew‑o‑Matic **no publica un listado** de recetas: hay que pasarle las direcciones
> de las recetas que quieras (las que abras en la web). El campo `_bom` del JSON guarda
> el OG/FG originales para poder comparar los cálculos.

---

## Reemplazar las recetas genéricas por recetas reales

Las 66 recetas del catálogo original eran genéricas (sin estilo y con errores de
ingredientes). Estos dos scripts las reemplazan por recetas reales publicadas en
Brew‑o‑Matic, **validadas una por una** contra nuestro propio motor.

```bash
# 1) Busca y valida una receta real por cada receta del catálogo
python herramientas/reemplazar_genericas.py

# 2) Pasa el resultado al recetario de la app (hace copia de seguridad)
python herramientas/aplicar_recetario_real.py
```

- Solo acepta una receta si su OG **y** FG calculados por Cervecera VGB coinciden
  con los publicados por Brew‑o‑Matic (diferencia ≤ 0,002).
- Los códigos BJCP se comparan **exactos** (1A ≠ 21A), para no mezclar estilos.
- `recetario_real.json` guarda lo conseguido; `reemplazo_informe.txt`, el detalle.
- `recetas_base_genericas.json` es la copia de seguridad del catálogo viejo.

El listado público de Brew‑o‑Matic se obtiene de:

```
https://www.brew-o-matic.com.ar/recipe/public?google_id=undefined     (8.600+ recetas)
```

> El `google_id=undefined` es necesario: sin ese parámetro el servidor responde 500.

## Cómo llegan las recetas corregidas a los usuarios

La app **refresca** las recetas que ya tenía si vinieron del recetario oficial
(quedan anotadas en `settings -> recetas_refrescables`, con una huella de su
contenido). Las recetas creadas o editadas por el usuario **nunca** se tocan.
Así, los usuarios que ya tenían las recetas genéricas reciben las reales sin
reinstalar nada, y solo se reescribe lo que realmente cambió.
