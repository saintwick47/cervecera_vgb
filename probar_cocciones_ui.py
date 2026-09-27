"""Prueba real del rail de cocciones programadas (diseño de Stitch)."""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
import tkinter.messagebox as mb
mensajes = []
mb.showinfo = lambda t, m, **k: mensajes.append(("info", t, m))
mb.showwarning = lambda t, m, **k: mensajes.append(("warn", t, m))
mb.showerror = lambda t, m, **k: mensajes.append(("error", t, m))
mb.askyesno = lambda *a, **k: True
import app as app_mod
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR

carpeta = tempfile.mkdtemp()
db = DatabaseManager(data_dir=carpeta)
db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
rid = db.save_recipe({"name": "West Coast IPA", "style": "21A", "volume": 50, "efficiency": 0.75, "notes": "",
    "maltas": [{"nombre": "Malta Pale Ale (Uma Malta)", "cantidad": 10, "extracto": 309, "color": 4}],
    "lupulos": [{"nombre": "Mosaic (USA)", "cantidad": 250, "aa": 11.5, "tiempo": 60, "formato": "pellet"}],
    "levaduras": [{"nombre": "Fermentis US-05 (Ale Americana)", "atenuacion": 81.0, "tolerancia": 12.0}]})
db.add_inventory_item("Malta", "Malta Pale Ale (Uma Malta)", 145.0, "kg")
db.add_inventory_item("Lúpulo", "Mosaic (USA)", 120.0, "g")     # falta: 250 necesarios
db.add_inventory_item("Levadura", "Fermentis US-05 (Ale Americana)", 14.0, "sobres")

app_mod.DatabaseManager = lambda *a, **k: db
app = app_mod.CerveceraApp(); app.withdraw()
app.tabview.set("📦 Inventario")
app.cargar_lista_inventario()

print("Rail — encabezado:", app.lbl_cocciones_estado.cget("text"))
assert "No hay cocciones" in app.lbl_cocciones_estado.cget("text"), "el rail debería arrancar vacío"

# Programar la cocción directamente (misma lógica que el diálogo)
lote_id = db.planificar_lote(rid, fecha_coccion="Mañana 08:00", volumen=50)
app.cargar_lista_inventario()
print("Rail — encabezado:", app.lbl_cocciones_estado.cget("text"))
tarjetas = [w for w in app.lista_cocciones.winfo_children()]
print(f"Tarjetas en el rail: {len(tarjetas)}")
textos = []
for t in tarjetas:
    for hijo in t.winfo_children():
        try: textos.append(hijo.cget("text"))
        except Exception: pass
for t in textos: print("   ", t)
assert any("West Coast IPA" in t for t in textos), "no aparece el lote"
assert any("Faltante" in t and "Mosaic" in t for t in textos), "no avisa el faltante de Mosaic"
print("  ✓ lote con faltante visible")

# Resolver: ingresar el stock que llega
lote = db.lotes_para_rail()[0]
print("\nResolver faltantes:")
print("  faltante:", {k: v for k, v in lote["faltantes"][0].items() if k in ("nombre", "requerido", "disponible")})
db.add_inventory_item("Lúpulo", "Mosaic (USA)", 200.0, "g")     # llega el pedido
app.cargar_lista_inventario()
print("  Rail — encabezado:", app.lbl_cocciones_estado.cget("text"))
assert "1 de 1 con insumos completos" in app.lbl_cocciones_estado.cget("text"), \
    "al ingresar el stock el lote debería quedar completo"
print("  ✓ el lote pasa a 'insumos completos'")

# Distribución de espacio
print("\nDistribución de Espacio de Acopio:")
print("  ", app.lbl_capacidad.cget("text"))
print("  ", app.lbl_distribucion.cget("text").replace("\n", " | "))
assert "Capacidad estimada" in app.lbl_capacidad.cget("text")
# ── Etiqueta QR / Lote ──
from tkinter import filedialog
ruta_pdf = tempfile.mktemp(suffix=".pdf")
filedialog.asksaveasfilename = lambda *a, **k: ruta_pdf
app._escribir_etiqueta(db.get_lotes()[0])
tamaño = os.path.getsize(ruta_pdf)
print(f"\nEtiqueta QR / Lote -> PDF de {tamaño/1024:.1f} KB")
assert tamaño > 500, "la etiqueta quedó vacía"
with open(ruta_pdf, "rb") as f:
    assert f.read(4) == b"%PDF", "no se generó un PDF"
print("  ✓ etiqueta PDF generada" + (" con QR" if __import__("importlib").util.find_spec("qrcode") else " (sin librería QR)"))

# ── Ver todo ──
app.mostrar_todas_las_cocciones()
print("\nVer todo:", (mensajes[-1][2][:60] + "…") if mensajes else "sin mensaje")
assert mensajes and "West Coast IPA" in mensajes[-1][2]
print("  ✓ lista completa de cocciones")

app.destroy()
print("\nRAIL DE COCCIONES Y DISTRIBUCIÓN: OK ✓")
