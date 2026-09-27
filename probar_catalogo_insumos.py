"""Prueba real de los filtros y columnas del catálogo de Insumos (según el diseño)."""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app as app_mod
import tkinter.messagebox as mb
mb.showinfo = lambda *a, **k: None
mb.showwarning = lambda *a, **k: None
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR

carpeta = tempfile.mkdtemp()
db = DatabaseManager(data_dir=carpeta)
db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
app_mod.DatabaseManager = lambda *a, **k: db
app = app_mod.CerveceraApp(); app.withdraw()
assert os.path.realpath(app.db.db_path).startswith(os.path.realpath(carpeta)), "¡ojo, BD real!"
app.cargar_lista_insumos()

def filas():
    return [app.tree_insumos.item(f, "values") for f in app.tree_insumos.get_children()]

print("Sin filtros:", len(filas()), "insumos")
print("Columnas   :", [app.tree_insumos.heading(c)["text"] for c in app.tree_insumos["columns"]])
print("Ejemplo    :", filas()[0])

app.combo_ing_productor.set("Weyermann Malting (Alemania)")
app.cargar_lista_insumos()
n = len(filas()); print(f"\nProductor = Weyermann -> {n} insumos")
assert n and all("Weyermann" in f[0] for f in filas()), "el filtro por productor no filtra"
print("  ✓ todos son de Weyermann")

app.combo_ing_productor.set("Todos los productores")
app.combo_ing_familia.set("Maltas Especiales / Caramelo")
app.cargar_lista_insumos()
n2 = len(filas()); print(f"\nFamilia = Maltas Especiales/Caramelo -> {n2} insumos")
assert n2 and n2 < 43, "el filtro por familia no filtra"
print("  ✓", [f[0] for f in filas()[:3]])

app.combo_ing_familia.set("Todos los granos")
app.seg_ing_filtro.set("Lúpulo")
app.cargar_lista_insumos()
print(f"\nSolo lúpulos -> {len(filas())} | ejemplo: {filas()[0]}")

app.seg_ing_filtro.set("Todos")
app.entry_ing_buscar.insert(0, "special")
app.cargar_lista_insumos()
print(f"Buscar 'special' -> {len(filas())} | {[f[0] for f in filas()]}")
# ── rail de categorías con contadores ──
app.seg_ing_filtro.set("Todos"); app.entry_ing_buscar.delete(0, "end")
app.cargar_lista_insumos()
print("\nRail de categorías:", {t: b.cget("text") for t, b in app._rail_insumos.items()})
esperadas = len([i for i in app.db.get_ingredients("Malta")])
assert str(esperadas) in app._rail_insumos["Malta"].cget("text"), \
    f"el rail debería mostrar {esperadas} maltas"
print("  ✓ contadores del rail")

# ── paginación ──
print("\nPaginación:")
print(" ", app.lbl_ing_pagina.cget("text"))
assert "Mostrando 1 a 8 de" in app.lbl_ing_pagina.cget("text"), "falta el texto de paginación"
app._ing_pagina_mover(1)
print(" ", app.lbl_ing_pagina.cget("text"))
assert "Mostrando 9 a 16 de" in app.lbl_ing_pagina.cget("text"), "no avanza de página"
app._ing_pagina_mover(-1)
print("  ✓ paginación")

# ── ID del insumo (SKU) como el diseño ──
sku = app._sku_insumo(app.db.get_ingredient("Malta", "Malta Pale Ale (Uma Malta)")
                      or app.db.get_ingredients("Malta")[0])
print("\nID del insumo:", sku)
assert sku.startswith("INS-MLT-"), "el ID no sigue el formato del diseño"
adj = next(i for i in app.db.get_ingredients("Malta") if i["category"] == "Adjuntos y Copos")
print("  adjunto:", adj["name"], "->", app._sku_insumo(adj))
assert app._sku_insumo(adj).startswith("INS-ADJ-"), "los adjuntos deben llevar ADJ"
print("  ✓ IDs tipo INS-MLT / INS-ADJ")

# ── ficha: se muestra el ID y el botón Duplicar ──
app.seg_ing_filtro.set("Malta"); app._ing_pagina = 0; app.cargar_lista_insumos()
primera = app.tree_insumos.get_children()[0]          # la tabla está paginada
nombre_prueba = primera.split("|", 1)[1]
app.tree_insumos.selection_set(primera)
app._ing_on_select()
ing = app.db.get_ingredient("Malta", nombre_prueba)     # el insumo que vamos a duplicar
print("\nFicha:", app.lbl_ficha_ing.cget("text").replace("\n", " | "))
assert "ID: INS-" in app.lbl_ficha_ing.cget("text"), "la ficha no muestra el ID"

antes = len(app.db.get_ingredients("Malta"))
app._ing_duplicar()
despues = len(app.db.get_ingredients("Malta"))
copia = app.db.get_ingredient("Malta", f"{nombre_prueba} (copia)")
print(f"\nDuplicar: {antes} -> {despues} maltas | copia creada: {bool(copia)}")
assert despues == antes + 1 and copia, "no duplicó el insumo"
assert copia["origin"] == ing["origin"] and copia["color"] == ing["color"], "la copia no trae los datos"
app.db.delete_ingredient("Malta", f"{nombre_prueba} (copia)")
print("  ✓ duplicar (y limpieza de la copia de prueba)")

# ── Filas alternadas del diseño (#24242C / #282834) ──
app.seg_ing_filtro.set("Todos"); app.entry_ing_buscar.delete(0, "end")
app._ing_pagina = 0; app.cargar_lista_insumos()
tags = [app.tree_insumos.item(f, "tags") for f in app.tree_insumos.get_children()]
print("\nFilas alternadas:", [t[0] if t else "—" for t in tags[:4]])
assert len(tags) >= 2, "no hay filas para comprobar"
assert all(t and t[0] in ("fila_par", "fila_impar") for t in tags), f"faltan tags: {tags[:3]}"
assert tags[0][0] != tags[1][0], "las filas consecutivas comparten el mismo fondo"
print("  ✓ fondos alternados como el diseño")

# ── Ficha técnica: secciones del diseño, color SRM/EBC y maceración ──
app.seg_ing_filtro.set("Malta"); app._ing_pagina = 0
app.entry_ing_buscar.delete(0, "end"); app.entry_ing_buscar.insert(0, "Pale Ale")
app.cargar_lista_insumos()
primera = app.tree_insumos.get_children()[0]
app.tree_insumos.selection_set(primera); app._ing_on_select()
print("\nFicha técnica:")
print("  ", app.lbl_ing_color_estimado.cget("text"))
assert "SRM" in app.lbl_ing_color_estimado.cget("text") and "EBC" in app.lbl_ing_color_estimado.cget("text"), \
    "falta el color estimado en SRM/EBC"
textos_ficha = []
def rec_ficha(w):
    for h in w.winfo_children():
        try:
            t = h.cget("text")
            if isinstance(t, str) and t.strip(): textos_ficha.append(t)
        except Exception: pass
        rec_ficha(h)
rec_ficha(app.tab_insumos)
for quiero in ("1. Información General y Fabricante",
               "2. Parámetros Físico-Químicos de Elaboración",
               "3. Reglas de Dosificación en Olla",
               "Maceración", "Notas de Cata y Perfil Sensorial del Proveedor",
               "% Máximo en Grist", "Uso Recomendado"):
    limpios = [t.rstrip(":") for t in textos_ficha]
    assert any(quiero == t for t in limpios), f"falta '{quiero}' en la ficha"
print("  ✓ secciones 1/2/3 y campos del diseño")
assert "maceracion" in app._ing_combos, "falta el campo Maceración"
assert "uso" in app._ing_combos, "Uso Recomendado debería ser una lista desplegable"
print("  ✓ campos Maceración y Uso Recomendado como listas del diseño")

# ── Importar BeerXML ──
import tempfile as _tmp
from tkinter import filedialog
xml = """<?xml version="1.0"?><RECIPES><RECIPE><NAME>T</NAME>
<FERMENTABLES><FERMENTABLE><NAME>Malta Importada Test</NAME><TYPE>Grain</TYPE><AMOUNT>1</AMOUNT>
<YIELD>80</YIELD><COLOR>5</COLOR><ORIGIN>Importlandia</ORIGIN></FERMENTABLE></FERMENTABLES>
<HOPS><HOP><NAME>Lúpulo Importado Test</NAME><ALPHA>9.5</ALPHA><AMOUNT>0.02</AMOUNT><FORM>Pellet</FORM></HOP></HOPS>
<YEASTS><YEAST><NAME>Levadura Importada Test</NAME><LABORATORY>LabTest</LABORATORY><ATTENUATION>78</ATTENUATION></YEAST></YEASTS>
</RECIPE></RECIPES>"""
ruta_xml = _tmp.mktemp(suffix=".xml")
open(ruta_xml, "w", encoding="utf-8").write(xml)
filedialog.askopenfilename = lambda *a, **k: ruta_xml
antes = len(app.db.get_ingredients())
app.importar_insumos_beerxml()
despues = app.db.get_ingredients()
print(f"\nImportar BeerXML: {antes} -> {len(despues)} insumos (+{len(despues)-antes})")
malta = app.db.get_ingredient("Malta", "Malta Importada Test")
print("  malta importada:", malta["extract"], malta["color"], malta["category"], "|", malta["origin"])
assert malta and malta["category"] == "Maltas Base" and malta["origin"] == "Importlandia"
assert app.db.get_ingredient("Lúpulo", "Lúpulo Importado Test")["alpha"] == 9.5
assert app.db.get_ingredient("Levadura", "Levadura Importada Test")["attenuation"] == 78
print("  ✓ insumos de los 3 tipos importados con sus datos")

app.destroy()
print("\nFILTROS, COLUMNAS, RAIL, PAGINACIÓN, ID, DUPLICAR E IMPORTAR BEERXML: TODO OK ✓")
