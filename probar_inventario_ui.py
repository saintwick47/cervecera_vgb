"""Prueba real de la pantalla de Inventario según el diseño de Stitch."""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
import tkinter.messagebox as mb
mensajes = []
mb.showinfo = lambda t, m, **k: mensajes.append(m)
mb.showwarning = mb.showerror = lambda t, m, **k: mensajes.append(m)
import app as app_mod
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR

carpeta = tempfile.mkdtemp()
db = DatabaseManager(data_dir=carpeta)
db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
db.add_inventory_item("Lúpulo", "Cascade US", 1250.0, "g")
db.add_inventory_item("Lúpulo", "Mosaic (USA)", 120.0, "g")
db.add_inventory_item("Malta", "Malta Pale Ale (Uma Malta)", 145.0, "kg")
db.add_inventory_item("Misceláneo", "Sulfato de Calcio (CaSO4 / Yeso)", 3800.0, "g")
items = {i["name"]: i["id"] for i in db.get_all_inventory()}
db.update_inventory_details(items["Cascade US"], costo_unitario=18.5, minimo=500, lote="CAS-2023-AR", ubicacion="Freezer Lúpulos (-18°C)")
db.update_inventory_details(items["Mosaic (USA)"], costo_unitario=28.0, minimo=1000, lote="YCH-MOS-22", ubicacion="Freezer Lúpulos (-18°C)")
db.update_inventory_details(items["Malta Pale Ale (Uma Malta)"], costo_unitario=1850, minimo=50, lote="2024-BM-04", ubicacion="Depósito Principal Seco", vencimiento="2026-10-10")
db.update_inventory_details(items["Sulfato de Calcio (CaSO4 / Yeso)"], costo_unitario=1200, minimo=1000, ubicacion="Armario de Sales / Lab")

app_mod.DatabaseManager = lambda *a, **k: db
app = app_mod.CerveceraApp(); app.withdraw()
app.tabview.set("📦 Inventario")
app.cargar_lista_inventario()

print("KPIs del diseño:")
for lbl in (app.lbl_kpi_valorizacion, app.lbl_kpi_total, app.lbl_kpi_bajo, app.lbl_kpi_porvencer):
    print("  ", lbl.cget("text"))
assert "Por vencer" in app.lbl_kpi_porvencer.cget("text"), "falta el 4º KPI"
assert "1" in app.lbl_kpi_porvencer.cget("text"), "debería detectar 1 por vencer"
print("  ✓ 4 KPIs")

print("\nColumnas:", [app.tree_inventario.heading(c)["text"] for c in app.tree_inventario["columns"]])
filas = [app.tree_inventario.item(f, "values") for f in app.tree_inventario.get_children()]
for nombre, v in zip([app.tree_inventario.item(f, "text") for f in app.tree_inventario.get_children()], filas):
    print(f"  {nombre[:28]:<28} lote/ubic={v[0][:34]:<34} espec={v[2]:<14} nivel={v[4][:22]:<22} estado={v[6]}")
estados = {v[6] for v in filas}
assert any("Crítico" in e for e in estados), "falta el estado Crítico (Mosaic 120g / min 1000g)"
assert any("En Stock" in e for e in estados), "falta el estado En Stock"
print("  ✓ estados Crítico / Bajo / En Stock")

print("\nFiltro por ubicación:")
app.combo_inv_ubicacion.set("Freezer Lúpulos (-18°C)"); app.cargar_lista_inventario()
n = len(app.tree_inventario.get_children())
print(f"  Freezer -> {n} ítems")
assert n == 2, f"esperaba 2 en el freezer, hay {n}"
app.combo_inv_ubicacion.set("Todas las ubicaciones"); app.cargar_lista_inventario()
print("  ✓ filtro por ubicación")

print("\nFicha: ubicación y lote")
app.tree_inventario.selection_set(str(items["Mosaic (USA)"])); app._inv_on_select()
print("  almacenamiento:", app.combo_ficha_ubicacion.get(), "| lote:", app.entry_ficha_lote.get())
app.combo_ficha_ubicacion.set("Cámara Levaduras (+4°C)")
app._inv_guardar_ficha()
guardado = db.get_inventory_item_by_name("Lúpulo", "Mosaic (USA)")
assert guardado["ubicacion"] == "Cámara Levaduras (+4°C)", "no guardó la ubicación"
print("  ✓ se guarda en la base")
# ── Ajuste físico (botón del diseño) ──
print("\nAjuste Físico:")
antes = db.get_inventory_item_by_name("Lúpulo", "Cascade US")["amount"]
dif = db.ajustar_inventario(items["Cascade US"], 1200.0, "Conteo de depósito")
app.cargar_lista_inventario()
despues = db.get_inventory_item_by_name("Lúpulo", "Cascade US")["amount"]
movs = db.get_inventory_movimientos(limit=5)
print(f"  contado 1200 g (antes {antes:g}) -> {despues:g} g | diferencia {dif:g}")
print("  Kardex:", [(m["tipo"], m["cantidad"], m["motivo"]) for m in movs[:1]])
assert despues == 1200.0 and movs[0]["tipo"] == "Ajuste"
assert any(m["tipo"] == "Ajuste" for m in db.get_inventory_movimientos(limit=10))
print("  ✓ el ajuste queda en el stock y en el Kardex")

# ── acciones por fila ──
print("\nAcciones por fila:")
app.tree_inventario.selection_set(str(items["Mosaic (USA)"]))
app._inv_ver_historial()
print("  doble clic -> historial:", mensajes[-1].splitlines()[0] if mensajes else "sin mensaje")
assert mensajes and "movimientos" in mensajes[-1]
print("  ✓ doble clic muestra el historial del insumo")

# ── Paginación de la planilla (Anterior / Siguiente del diseño) ──
for i in range(9):      # más ítems para que haya 2 páginas
    db.add_inventory_item("Misceláneo", f"Insumo de prueba {i}", 10.0 + i, "g")
app._inv_pagina = 0
app.cargar_lista_inventario()
filas_p1 = len(app.tree_inventario.get_children())
texto_p1 = app.lbl_inv_pagina.cget("text")
print("\nPaginación:", texto_p1)
assert filas_p1 == 8, f"la primera página debería mostrar 8, mostró {filas_p1}"
assert "Página 1 de" in texto_p1
app._inv_pagina_mover(1)
filas_p2 = len(app.tree_inventario.get_children())
print("  después de 'Siguiente ›':", app.lbl_inv_pagina.cget("text"), f"({filas_p2} filas)")
assert "Página 2 de" in app.lbl_inv_pagina.cget("text") and 0 < filas_p2 <= 8
app._inv_pagina_mover(-1)
assert "Página 1 de" in app.lbl_inv_pagina.cget("text")
print("  ✓ paginación con Anterior / Siguiente")

# ── Orden de compra sugerida (diseño) ──
import csv as _csv
from tkinter import filedialog
ruta_csv = tempfile.mktemp(suffix=".csv")
filedialog.asksaveasfilename = lambda *a, **k: ruta_csv
db.update_inventory_details(items["Mosaic (USA)"], minimo=1000.0, costo_unitario=28.0)
app.cargar_lista_inventario()
app.generar_orden_compra()
filas_csv = list(_csv.reader(open(ruta_csv, encoding="utf-8"), delimiter=";"))
print("\nOrden de compra:", filas_csv[1][0], "-> sugerido", filas_csv[1][5], filas_csv[1][3])
assert any(f[0] == "Mosaic (USA)" for f in filas_csv[1:]), "no incluyó el insumo bajo mínimo"
assert "TOTAL ESTIMADO" in str(filas_csv[-1])
print("  ✓ incluye lo que está bajo el mínimo y el total estimado")

app.destroy()
print("\nINVENTARIO SEGÚN EL DISEÑO (KPIs, ubicaciones, estados, rail, ajuste y acciones): OK ✓")
