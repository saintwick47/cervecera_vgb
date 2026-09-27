"""Prueba de arranque y uso completo de la app (detecta errores en tiempo de ejecución).

Abre la app de verdad, recorre las 4 pestañas y los flujos principales como lo haría
un usuario, y falla si el logger registró algún error por el camino.

Uso:  python probar_arranque.py
"""
import os
import sys

os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter.messagebox as mb
mb.showinfo = mb.showwarning = mb.showerror = lambda *a, **k: None
mb.askyesno = lambda *a, **k: True

from tkinter import filedialog

# ── Capturamos todo lo que se registre como error ──
import logger as logger_mod
errores = []
_error_original = logger_mod.logger.error


def _error_capturado(mensaje, *args, **kwargs):
    errores.append(str(mensaje))
    return _error_original(mensaje, *args, **kwargs)


logger_mod.logger.error = _error_capturado

import app as app_mod
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR

# Ruidos esperables en un entorno de prueba (sin red / sin releases)
PERMITIDOS = ("_auto_actualizar", "404", "HTTPSConnectionPool", "urlopen")

carpeta = tempfile.mkdtemp()
db = DatabaseManager(data_dir=carpeta)
db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
db.add_inventory_item("Malta", "Malta Pale Ale (Uma Malta)", 145.0, "kg")
db.add_inventory_item("Lúpulo", "Mosaic (USA)", 600.0, "g")
db.add_inventory_item("Levadura", "Fermentis US-05 (Ale Americana)", 14.0, "sobres")
app_mod.DatabaseManager = lambda *a, **k: db

app = app_mod.CerveceraApp()
app.withdraw()
assert os.path.realpath(app.db.db_path).startswith(os.path.realpath(carpeta)), "¡usaría la base real!"

pasos = []


def paso(descripcion, funcion):
    antes = len(errores)
    try:
        funcion()
    except Exception as e:
        errores.append(f"{descripcion}: {type(e).__name__}: {e}")
    nuevos = [x for x in errores[antes:] if not any(p in x for p in PERMITIDOS)]
    pasos.append((descripcion, nuevos))
    print(f"  {'✗' if nuevos else '✓'} {descripcion}" + (f"  -> {nuevos}" if nuevos else ""))


print("Recorrido de la app:")

# ── Navegación: control segmentado del diseño ──
import customtkinter as ctk
assert isinstance(app.nav_segmentada, ctk.CTkSegmentedButton), "la navegación no es segmentada"
valores = app.nav_segmentada.cget("values")
print("  ✓ navegación segmentada:", valores)
assert valores == ["🛠️ Receta", "📦 Inventario", "🧪 Insumos", "⚙️ Equipos"], valores

def seccion_visible():
    for nombre, marco in (("Receta", app.tab_receta), ("Inventario", app.tab_inventario),
                          ("Insumos", app.tab_insumos), ("Equipos", app.tab_equipos)):
        if marco.winfo_ismapped() or marco.grid_info():
            if marco.winfo_manager() == "grid" and marco.grid_info():
                return nombre
    return "?"

for nombre in ("🛠️ Receta", "📦 Inventario", "🧪 Insumos", "⚙️ Equipos"):
    paso(f"abrir la sección {nombre}", lambda n=nombre: app.tabview.set(n))

# ── Recetas: crear, calcular, guardar, cargar ──
def crear_receta():
    app.entry_nombre.delete(0, "end"); app.entry_nombre.insert(0, "Prueba de arranque")
    app.combo_volumen.set("20")
    for w in app._filas_de(app.frame_lista_maltas):
        w.destroy()
    for w in app._filas_de(app.frame_lista_lupulos):
        w.destroy()
    app.maltas_rows = [] if hasattr(app, "maltas_rows") else []
    app.add_fila_malta({'nombre': 'Malta Pale Ale (Uma Malta)', 'cantidad': 5, 'extracto': 309, 'color': 4})
    app.add_fila_malta({'nombre': 'Caramelo 60L (CaraAroma)', 'cantidad': 0.6, 'extracto': 292, 'color': 35})
    app.add_fila_lupulo({'nombre': 'Mosaic (USA)', 'cantidad': 30, 'aa': 11.5, 'tiempo': 60, 'formato': 'pellet'})
    app.calcular_y_mostrar()

paso("crear una receta con 2 maltas y 1 lúpulo y calcular", crear_receta)
paso("guardar la receta", lambda: app.guardar_receta())
paso("recargar la lista de recetas", lambda: app.cargar_lista_recetas())

def clonar():
    listado = app.db.get_all_recipes_summary()
    app.seleccionar_receta(listado[0]["id"])
    app.clonar_receta_actual()

paso("clonar la receta", clonar)

# ── Insumos ──
paso("listar insumos", lambda: app.cargar_lista_insumos())
paso("filtrar por productor", lambda: (app.combo_ing_productor.set("Uma Malta (Argentina)"),
                                       app.cargar_lista_insumos()))
paso("limpiar el filtro de productor", lambda: (app.combo_ing_productor.set(
    "Todos los productores (Uma Malta, Weyermann, Castle, BestMalz...)"), app.cargar_lista_insumos()))
paso("pasar de página en el catálogo", lambda: app._ing_pagina_mover(1))
paso("elegir un insumo de la tabla", lambda: (app.tree_insumos.selection_set(
    app.tree_insumos.get_children()[0]), app._ing_on_select()))
paso("guardar la ficha del insumo", lambda: app._ing_guardar())

# ── Inventario ──
paso("listar el inventario", lambda: app.cargar_lista_inventario())
paso("elegir un ítem y ver su ficha", lambda: (app.tree_inventario.selection_set(
    app.tree_inventario.get_children()[0]), app._inv_on_select()))
paso("guardar la ficha del ítem", lambda: app._inv_guardar_ficha())
paso("pasar de página en la planilla", lambda: app._inv_pagina_mover(1))
paso("volver de página", lambda: app._inv_pagina_mover(-1))
paso("ajuste físico", lambda: db.ajustar_inventario(
    app.db.get_inventory_item_by_name("Lúpulo", "Mosaic (USA)")["id"], 580.0, "Prueba"))

def orden_compra():
    ruta = os.path.join(carpeta, "orden.csv")
    filedialog.asksaveasfilename = lambda *a, **k: ruta
    app.generar_orden_compra()

paso("generar orden de compra", orden_compra)

# ── Cocciones ──
def programar():
    receta = app.db.get_all_recipes_summary()[0]
    app.db.planificar_lote(receta["id"], fecha_coccion="2026-10-01 08:00", volumen=20)
    app.cargar_lista_inventario()

paso("programar una cocción", programar)
paso("ver todas las cocciones", lambda: app.mostrar_todas_las_cocciones())

def etiqueta():
    ruta = os.path.join(carpeta, "etiqueta.pdf")
    filedialog.asksaveasfilename = lambda *a, **k: ruta
    app._escribir_etiqueta(app.db.get_lotes()[0])
    assert os.path.getsize(ruta) > 500

paso("generar la etiqueta QR / Lote", etiqueta)

# ── Equipos ──
paso("listar equipos", lambda: app.cargar_lista_equipos())
paso("recalcular el balance teórico", lambda: app._cargar_balance_teorico())
paso("calcular el strike water", lambda: app._eq_aplicar_strike())

def guardar_equipo():
    app._eq_entries["name"].delete(0, "end")
    app._eq_entries["name"].insert(0, "Equipo de prueba")
    app._eq_guardar()

paso("guardar un perfil de equipo", guardar_equipo)

# ── Menú y ventanas de ayuda ──
paso("abrir el manual de usuario", lambda: app.mostrar_ayuda())
paso("abrir 'Acerca de'", lambda: app.mostrar_acerca())

app.destroy()

# ── Resultado ──
reales = [(d, e) for d, e in pasos if e]
print(f"\nPasos ejecutados: {len(pasos)} | con problemas: {len(reales)}")
if reales:
    for d, e in reales:
        print(f"  ✗ {d}\n      {e}")
    print("\nARRANQUE CON ERRORES ✗")
    sys.exit(1)
print("ARRANQUE Y USO COMPLETO: OK ✓ (sin errores en el log)")
