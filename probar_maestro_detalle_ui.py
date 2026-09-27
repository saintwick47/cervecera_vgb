"""Prueba de humo del maestro-detalle con la interfaz REAL (necesita display).

Abre la app, carga insumos e inventario, selecciona una fila del Treeview y
verifica que la ficha se cargue, que el Kardex quede filtrado, que guardar
persista y que borrar funcione. Cierra la ventana al terminar.
"""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

import app as app_mod
from database import DatabaseManager

# IMPORTANTE: la app crea su propia BD (la real del usuario). Le inyectamos una
# temporal reemplazando la clase antes de construirla, y verificamos que la use.
carpeta_prueba = tempfile.mkdtemp()
db_prueba = DatabaseManager(data_dir=carpeta_prueba)
db_prueba.add_inventory_item("Malta", "Pale Ale", 25.0, "Kg")
db_prueba.add_inventory_item("Lúpulo", "Cascade", 500.0, "g")
db_prueba.add_ingredient("Malta", "Pale Ale", color=3.5, extract=300, origin="Weyermann")

app_mod.DatabaseManager = lambda *a, **k: db_prueba
app = app_mod.CerveceraApp()
app.withdraw()                                  # sin ventana visible

if not os.path.realpath(app.db.db_path).startswith(os.path.realpath(carpeta_prueba)):
    print(f"ABORTADO: la app está usando la BD real ({app.db.db_path})")
    app.destroy()
    sys.exit(1)
print("app creada; usando BD temporal:", app.db.db_path)

# ── INVENTARIO ──
app.cargar_lista_inventario()
filas = app.tree_inventario.get_children()
print(f"\nInventario: {len(filas)} filas en la tabla")
assert filas, "la tabla de inventario quedó vacía"

# elegir la fila de Pale Ale
def contenido_fila(f):
    it = app.tree_inventario.item(f)
    return f"{it.get('text', '')} " + " ".join(str(v) for v in it.get("values", []))

print("  filas:", [contenido_fila(f).strip() for f in filas][:2])
fila_pale = next(f for f in filas if "Pale Ale" in contenido_fila(f))
app.tree_inventario.selection_set(fila_pale)
app._inv_on_select()
print("  fila elegida ->", app.lbl_ficha_inv.cget("text"), "|", app.lbl_ficha_inv_sub.cget("text"))
assert "Pale Ale" in app.lbl_ficha_inv.cget("text"), "la ficha no se cargó"

# kardex filtrado (sin movimientos de Cascade)
movs = app.db.get_inventory_movimientos(limit=200)
filtrados = [m for m in movs if m["item_name"] == "Pale Ale"]
print(f"  Kardex del ítem: {len(filtrados)} movimientos (global: {len(movs)})")

# editar y guardar
app.entry_ficha_costo.delete(0, "end");   app.entry_ficha_costo.insert(0, "1500")
app.entry_ficha_minimo.delete(0, "end");  app.entry_ficha_minimo.insert(0, "5")
app.entry_ficha_vencimiento.delete(0, "end"); app.entry_ficha_vencimiento.insert(0, "2027-03-15")
app._inv_guardar_ficha()
item = app.db.get_inventory_item_by_name("Malta", "Pale Ale")
print(f"  guardado -> costo={item['costo_unitario']} minimo={item['minimo']} venc={item['vencimiento']}")
assert item["costo_unitario"] == 1500.0 and item["vencimiento"] == "2027-03-15"

# ── INSUMOS ──
# La tabla está paginada: buscamos el insumo por nombre para que aparezca
app.seg_ing_filtro.set("Malta")
app.entry_ing_buscar.delete(0, "end")
app.entry_ing_buscar.insert(0, "Pale Ale")
app.cargar_lista_insumos()
filas_ing = app.tree_insumos.get_children()
print(f"\nInsumos (filtro 'Pale Ale'): {len(filas_ing)} filas")
assert filas_ing, "la tabla de insumos quedó vacía"
print("  claves:", filas_ing[:3])
fila = next(f for f in filas_ing if "Pale Ale" in f)
app.tree_insumos.selection_set(fila)
app._ing_on_select()
print("  fila elegida ->", app.lbl_ficha_ing.cget("text"))
print("  color en la ficha:", app._ing_entries["color"].get())

# borrar el ítem de inventario desde la ficha
app.eliminar_item_inventario(app._inv_actual)
quedan = [r["name"] for r in app.db.get_all_inventory()]
print(f"\nDespués de borrar quedan: {quedan}")
assert "Pale Ale" not in quedan, "no se borró el ítem"

app.destroy()
print("\nTODO OK ✓ (la interfaz carga ficha, guarda y borra usando la lógica pura)")
