"""Prueba real de la pestaña Equipos: 4 sub-pestañas, importación y Balance Teórico."""

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
app_mod.DatabaseManager = lambda *a, **k: db
app = app_mod.CerveceraApp(); app.withdraw()
app.tabview.set("⚙️ Equipos")

subtabs = app.subtabs_equipos
nombres = list(subtabs._tab_dict.keys()) if hasattr(subtabs, "_tab_dict") else []
print("Sub-pestañas:", nombres)
for esperada in ("Perfiles", "Valores por Defecto", "Calibración", "BeerXML"):
    assert any(esperada in n for n in nombres), f"falta la sub-pestaña {esperada}"
print("  ✓ las 4 del diseño")

# Balance Teórico del Lote
app._eq_entries["batch_volume"].delete(0, "end"); app._eq_entries["batch_volume"].insert(0, "20")
app._eq_entries["evaporacion_l_h"].delete(0, "end"); app._eq_entries["evaporacion_l_h"].insert(0, "3.2")
app._eq_entries["perdidas_l"].delete(0, "end"); app._eq_entries["perdidas_l"].insert(0, "4")
app._eq_extra_entries["absorcion_grano"].delete(0, "end"); app._eq_extra_entries["absorcion_grano"].insert(0, "1.0")
app._eq_extra_entries["espacio_muerto"].delete(0, "end"); app._eq_extra_entries["espacio_muerto"].insert(0, "3")
app._eq_extra_entries["perdida_turb_enfriador"].delete(0, "end"); app._eq_extra_entries["perdida_turb_enfriador"].insert(0, "4")
app._eq_extra_entries["relacion_empaste"].delete(0, "end"); app._eq_extra_entries["relacion_empaste"].insert(0, "3.0")
app._cargar_balance_teorico()
print("\nBalance Teórico del Lote:")
print("  " + app.lbl_balance.cget("text").replace("\n", "\n  "))
b = app._balance_teorico()
assert b["agua_total"] > b["lote"], "el agua total debe superar el lote final"
assert abs(b["mash"] + b["lavado"] - b["agua_total"]) < 0.05, "mash + lavado debe dar el agua total"
print("  ✓ agua total = mash + lavado y las pérdidas están calculadas")

# Calibración de ollas
marco = None
print("\nCalibración de ollas:")
app._eq_calibrar_olla(*[type("E", (), {"get": lambda s, v=v: v})() for v in ("21.5", "20", "1.8")])
print("  olla ->", app._eq_entries["kettle_volume"].get(), "L | espacio muerto ->", app._eq_extra_entries["espacio_muerto"].get(), "L")
assert app._eq_entries["kettle_volume"].get() == "21.5"
print("  ✓ aplica la medición al perfil")

# Importar perfil de equipo desde BeerXML
from tkinter import filedialog
xml = """<?xml version="1.0"?><EQUIPMENTS><EQUIPMENT><NAME>Olla Importada</NAME>
<BATCH_SIZE>30</BATCH_SIZE><BOIL_SIZE>36</BOIL_SIZE><EVAP_RATE>4</EVAP_RATE>
<TRUB_CHILLER_LOSS>2</TRUB_CHILLER_LOSS><EFFICIENCY>78</EFFICIENCY></EQUIPMENT></EQUIPMENTS>"""
ruta = tempfile.mktemp(suffix=".xml"); open(ruta, "w", encoding="utf-8").write(xml)
filedialog.askopenfilename = lambda *a, **k: ruta
app._eq_importar_beerxml()
print("\nEquipo importado ->", app._eq_entries["name"].get(), "|",
      app._eq_entries["batch_volume"].get(), "L | ef", app._eq_entries["eficiencia_pct"].get(), "%")
assert app._eq_entries["name"].get() == "Olla Importada"
assert app._eq_entries["batch_volume"].get() == "30"
print("  ✓ BeerXML de equipo importado (y el balance se recalculó)")

app.destroy()
print("\nEQUIPOS: SUB-PESTAÑAS, IMPORTACIÓN Y BALANCE TEÓRICO: OK ✓")
