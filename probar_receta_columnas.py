"""Prueba real de las columnas del diseño en Recetas: % Total, Uso, g/L e IBU Aporte."""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
import tkinter.messagebox as mb
mb.showinfo = mb.showwarning = mb.showerror = lambda *a, **k: None
import app as app_mod
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR

db = DatabaseManager(data_dir=tempfile.mkdtemp())
db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
app_mod.DatabaseManager = lambda *a, **k: db
app = app_mod.CerveceraApp(); app.withdraw()

# Receta de prueba: 5 kg base + 1 kg caramelo, 30 g Mosaic a 60 min, en 20 L
app.add_fila_malta({'nombre': 'Malta Pale Ale (Uma Malta)', 'cantidad': 5, 'extracto': 309, 'color': 4})
app.add_fila_malta({'nombre': 'Caramelo 60L (CaraAroma)', 'cantidad': 1, 'extracto': 292, 'color': 35})
app.add_fila_lupulo({'nombre': 'Mosaic (USA)', 'cantidad': 30, 'aa': 11.5, 'tiempo': 60, 'formato': 'pellet'})
app.combo_volumen.set("20")
app.calcular_y_mostrar()

filas_m = app._filas_de(app.frame_lista_maltas)
pcts = [f.lbl_pct.cget("text") for f in filas_m]
print("Granos — % Total:", pcts, "| Uso:", [f.c_uso.get() for f in filas_m])
assert pcts[0].startswith("83") and pcts[1].startswith("16"), f"porcentajes mal: {pcts}"
print("  ✓ el % del total suma 100 y respeta las cantidades")

filas_l = app._filas_de(app.frame_lista_lupulos)
gl = filas_l[0].lbl_gl.cget("text")
ibu = float(filas_l[0].lbl_ibu.cget("text"))
print(f"Lúpulos — g/L: {gl} | IBU Aporte: {ibu}")
assert abs(float(gl) - 1.5) < 0.01, f"g/L mal: {gl}"          # 30 g / 20 L
assert 20 < ibu < 50, f"IBU fuera de rango razonable: {ibu}"   # 30 g Mosaic 11.5% a 60 min
print("  ✓ g/L y el IBU que aporta cada adición")

# Al cambiar la cantidad, se recalculan
filas_l[0].e_cantidad.delete(0, "end"); filas_l[0].e_cantidad.insert(0, "60")
app.calcular_y_mostrar()
gl2 = filas_l[0].lbl_gl.cget("text"); ibu2 = float(filas_l[0].lbl_ibu.cget("text"))
print(f"  con 60 g -> g/L {gl2} | IBU {ibu2}")
assert abs(float(gl2) - 3.0) < 0.01 and ibu2 > ibu, "no recalculó al cambiar la cantidad"
print("  ✓ se recalculan al editar")

# ── Momento del lúpulo (Hervor / Whirlpool / Dry hop) ──
print("\nMomento del lúpulo:")
fila = filas_l[0]
for momento in ("Hervor", "Whirlpool", "Dry hop"):
    fila.c_momento.set(momento)
    app.calcular_y_mostrar()
    print(f"  {momento:<10} -> {fila.lbl_ibu.cget('text')} IBU")
fila.c_momento.set("Dry hop"); app.calcular_y_mostrar()
assert float(fila.lbl_ibu.cget("text")) == 0.0, "el dry hop no debe aportar IBU"
fila.c_momento.set("Whirlpool"); app.calcular_y_mostrar()
ibu_wp = float(fila.lbl_ibu.cget("text"))
assert ibu_wp > 0, "el whirlpool debe aportar algo de IBU"
fila.c_momento.set("Hervor"); app.calcular_y_mostrar()
ibu_hervor = float(fila.lbl_ibu.cget("text"))
assert ibu_hervor > ibu_wp, "el hervor a 60 min debe amargar más que el whirlpool"
print(f"  ✓ Dry hop 0 IBU y el hervor amarga más que el whirlpool ({ibu_hervor} vs {ibu_wp})")

# ── Indicadores lineales del diseño (atenuación y eficiencia) ──
print("\nGauges del diseño:")
gauges = app._gauges
print("  Atenuación real    :", f"{gauges['atenuacion'].get()*100:.1f}%",
      "->", gauges["atenuacion"].cget("progress_color"))
print("  Eficiencia macerado:", f"{gauges['eficiencia'].get()*100:.1f}%",
      "->", gauges["eficiencia"].cget("progress_color"))
assert len(gauges) == 2, "faltan indicadores"
assert 0 < gauges["atenuacion"].get() <= 1, "la atenuación no se calculó"
assert gauges["eficiencia"].get() > 0, "la eficiencia no se calculó"
assert gauges["atenuacion"].cget("progress_color") in ("#22C55E", "#D97706"), "color fuera de la paleta"
assert abs(gauges["eficiencia"].get() - 0.75) < 0.01, "la eficiencia debería reflejar el 75 %"
print("  ✓ dos indicadores con color según el estado")

# ── Mosaico SRM con texto adaptativo (diseño) ──
print("\nMosaico SRM (texto adaptativo):")
for w in app._filas_de(app.frame_lista_maltas):
    w.destroy()
app.add_fila_malta({'nombre': 'Malta Pale Ale (Uma Malta)', 'cantidad': 5, 'extracto': 309, 'color': 2})
app.calcular_y_mostrar()
claro = app.lbl_srm_hex.cget("text_color")
for w in app._filas_de(app.frame_lista_maltas):
    w.destroy()
app.add_fila_malta({'nombre': 'Weyermann Carafa Special III', 'cantidad': 5, 'extracto': 288, 'color': 500})
app.calcular_y_mostrar()
oscuro = app.lbl_srm_hex.cget("text_color")
print(f"  cerveza clara -> texto {claro} | cerveza oscura -> texto {oscuro}")
assert claro == "#1E1E24" and oscuro == "#FFFFFF", "el texto del mosaico no se adapta al color"
print("  ✓ texto oscuro sobre claro y blanco sobre oscuro")

# Encabezados del diseño
encabezados = []
def rec(w):
    for h in w.winfo_children():
        try:
            t = h.cget("text")
            if isinstance(t, str): encabezados.append(t)
        except Exception: pass
        rec(h)
rec(app.tab_receta)
for quiero in ("Grano / Fermentable", "Cantidad (Kg)", "% Total", "Uso",
               "Alpha Ac.", "Modo", "Momento", "g/L", "IBU Aporte"):
    assert any(quiero == e for e in encabezados), f"falta el encabezado {quiero}"
print("  ✓ encabezados del diseño presentes")

app.destroy()
print("\nCOLUMNAS DE RECETAS SEGÚN EL DISEÑO: OK ✓")
