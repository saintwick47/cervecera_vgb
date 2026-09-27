"""Verifica que la barra de menú del diseño exista y tenga las opciones correctas."""

import os as _os
_os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import os, sys, tempfile
sys.path.insert(0, os.getcwd())
import tkinter.messagebox as mb
mb.showinfo = mb.showwarning = mb.showerror = lambda *a, **k: None
import app as app_mod
from database import DatabaseManager
from catalogo_ar import MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR
carpeta = tempfile.mkdtemp()
db = DatabaseManager(data_dir=carpeta); db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR)
app_mod.DatabaseManager = lambda *a, **k: db
a = app_mod.CerveceraApp(); a.withdraw()
barra = a._barra_menu
menus = [barra.entrycget(i, "label") for i in range(1, barra.index("end") + 1)]
print("Menús:", menus)
assert menus == ["Archivo", "Herramientas", "Ayuda"], "faltan menús del diseño"
esperado = {
    "Archivo": ["Importar JSON", "Exportar PDF", "Exportar BeerXML", "Salir"],
    "Herramientas": ["Buscar recetas nuevas", "Recetas de la Comunidad",
                     "Comprobar actualizaciones", "Ver log"],
    "Ayuda": ["Manual de Usuario", "Acerca de Cervecera VGB"],
}
for i, nombre in enumerate(menus, start=1):
    sub = barra.nametowidget(barra.entrycget(i, "menu"))
    opciones = []
    for j in range(sub.index("end") + 1):
        try: opciones.append(sub.entrycget(j, "label"))
        except Exception: opciones.append("---")
    opciones = [o for o in opciones if o != "---"]
    print(f"  {nombre}: {opciones}")
    for quiero in esperado[nombre]:
        assert any(quiero in o for o in opciones), f"falta '{quiero}' en {nombre}"
print("\n¿Existe la ventana 'Acerca de'? ", end="")
a.mostrar_acerca(); a.update()
print("sí ✓")
for w in a.winfo_children():
    if w.winfo_class() == "Toplevel": w.destroy()
a.destroy()
print("\nBARRA DE MENÚ DEL DISEÑO: OK ✓")
