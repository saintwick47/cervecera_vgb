# app_gestion.py
# Autor: SaintWick
"""
Módulo de gestión de Cervecera VGB (split de app.py, demasiado grande).

Contiene:
- Constantes y utilidades compartidas con app.py (format_num, resource_path,
  _flotar, valores por defecto de receta) — quedaron acá para que este
  archivo no dependa de app.py (evita import circular); app.py las importa
  de vuelta.
- Parser de "Pegar productos" del inventario (matchea contra el catálogo de
  insumos, al estilo del import de facturas de BrewersFriend).
- AyudaDialog (Manual de Usuario).
- GestionMixin: catálogo de insumos, inventario, equipos, CRUD de recetas,
  import/export (JSON/PDF/BeerXML), actualización web, menú y log.

Se combina con la clase principal en app.py por herencia múltiple:
    class CerveceraApp(GestionMixin, ctk.CTk): ...
"""
import customtkinter as ctk
import tkinter.messagebox as mb
from tkinter import filedialog
import hashlib
import json
import os
import re
import sys
import subprocess
import threading
import tempfile
import base64
import urllib.request
import urllib.error
import difflib
from logger import logger
from app_paths import get_data_dir
from brew_engine import BrewEngine
from bjcp_styles import get_style_list
from catalogo_ar import LEVADURAS_AR, ALTITUDES_CORDOBA, PERFILES_AGUA_CORDOBA
from export_engine import exportar_pdf, exportar_beerxml

VOLUMENES_PRESET = ["5", "10", "20", "50", "100", "250", "500", "750", "1000", "1200", "1500", "2000", "3000", "5000", "10000"]
TIPOS_INVENTARIO = ["Malta", "Lúpulo", "Levadura", "Otro"]

_RE_CANTIDAD_UNIDAD = re.compile(
    r"(?P<cantidad>\d+(?:[.,]\d+)?)\s*(?P<unidad>kgs?|gr?s?|gramos?|lts?|litros?|uds?|unidades?|u|l|g)\b",
    re.IGNORECASE,
)
_UNIDADES_NORM = {"kg": "Kg", "kgs": "Kg", "g": "g", "gr": "g", "grs": "g", "gramos": "g",
                  "l": "L", "lt": "L", "lts": "L", "litros": "L",
                  "u": "Uds", "ud": "Uds", "uds": "Uds", "unidad": "Uds", "unidades": "Uds"}


def parsear_texto_productos(texto: str, catalogo: dict[str, tuple[str, str]]) -> list[dict[str, str | float]]:
    """Extrae productos (tipo, nombre, cantidad, unidad) de texto pegado en bruto
    (una línea por producto: factura, lista de proveedor, etc.), al estilo del
    matching automático de BrewersFriend contra su catálogo de insumos.
    `catalogo`: {nombre_en_minuscula: (tipo, nombre_original)} ya cargado desde la base.
    """
    nombres_catalogo = list(catalogo.keys())
    productos: list[dict[str, str | float]] = []
    for linea in texto.splitlines():
        linea = linea.strip(" \t-–—•*")
        if not linea:
            continue
        # Soporta también líneas separadas por coma/tab (pegado desde planilla/factura)
        partes = re.split(r"\t|;", linea)
        linea_norm = partes[0] if len(partes) > 1 else linea
        m = _RE_CANTIDAD_UNIDAD.search(linea_norm)
        if m:
            cantidad = float(m.group("cantidad").replace(",", "."))
            unidad = _UNIDADES_NORM.get(m.group("unidad").lower(), "Kg")
            nombre = (linea_norm[:m.start()] + linea_norm[m.end():]).strip(" \t-–—:.,x×*")
        else:
            cantidad, unidad, nombre = 1.0, "Uds", linea_norm.strip()
        # si el resto de la línea trae cantidad/unidad sueltas (formato CSV), las tomamos
        for extra in partes[1:]:
            extra = extra.strip()
            if not extra:
                continue
            if re.fullmatch(r"\d+(?:[.,]\d+)?", extra):
                cantidad = float(extra.replace(",", "."))
                continue
            me = _RE_CANTIDAD_UNIDAD.fullmatch(extra)
            if me:
                cantidad = float(me.group("cantidad").replace(",", "."))
                unidad = _UNIDADES_NORM.get(me.group("unidad").lower(), unidad)
                continue
            unidad_sola = _UNIDADES_NORM.get(extra.lower())
            if unidad_sola:
                unidad = unidad_sola
        if not nombre:
            continue
        match = difflib.get_close_matches(nombre.lower(), nombres_catalogo, n=1, cutoff=0.6)
        if match:
            tipo, nombre = catalogo[match[0]]
        else:
            tipo = "Otro"
        productos.append({"tipo": tipo, "nombre": nombre, "cantidad": cantidad, "unidad": unidad})
    return productos

# Valores por defecto (paridad con beer_vgb_mobile)
DEF_PERFIL_AGUA   = "Córdoba Capital (Agua de Red) "
DEF_LEVADURA      = "Fermentis US-05 (Ale Americana) "
DEF_ALTITUD       = "Córdoba Capital "
DEF_FORMATO       = "pellet"
EVAPORACION_PCT   = 10.0  # evaporación por hora de hervor (%)
APP_VERSION       = "1.4.2"  # versión instalada (para comprobar actualizaciones)
RECETARIO_URL     = ("https://github.com/saintwick47/cervecera_vgb/"
                     "releases/latest/download/recetas_cervecera_vgb.json")
RELEASE_API_URL   = "https://api.github.com/repos/saintwick47/cervecera_vgb/releases/latest"
COMUNIDAD_OWNER_REPO = "saintwick47/cervecera_vgb"
COMUNIDAD_CARPETA    = "recetas_comunidad"
COMUNIDAD_LISTADO_URL = f"https://api.github.com/repos/{COMUNIDAD_OWNER_REPO}/contents/{COMUNIDAD_CARPETA}"
COMUNIDAD_ARCHIVO_URL = COMUNIDAD_LISTADO_URL + "/{archivo}"
COMUNIDAD_TOKEN_ENV   = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT")
COMUNIDAD_TOKEN_FILE  = os.path.expanduser("~/.config/cervecera_vgb/token")

# Parámetros extendidos de equipo (Equipos > Valores por Defecto), guardados como
# JSON en equipment.extra_params. (clave, etiqueta, unidad, default, es_texto)
EQUIPO_EXTRA_GRUPOS = [
    ("Maceración, Empaste y Térmica", [
        ("temp_grano", "Temp. del grano", "°C", 20.0, False),
        ("relacion_empaste", "Relación Empaste", "L/Kg", 3.0, False),
        ("perdida_termica", "Pérdida Térmica", "°C", 6.0, False),
        ("temp_lavado", "Temperatura Lavado", "°C", 75.0, False),
        ("tiempo_agua_mash", "Tiempo Agua Mash", "min", 60.0, False),
        ("duracion_lavado", "Duración Lavado", "min", 40.0, False),
        ("precalentamiento_hlt", "Precalentamiento HLT", "°C", 80.0, False),
    ]),
    ("Mermas, Absorción y Pérdidas", [
        ("espacio_muerto", "Espacio Muerto", "L", 3.0, False),
        ("absorcion_grano", "Absorción del Grano", "L/Kg", 1.0, False),
        ("duracion_prehervor", "Duración Pre-Hervor", "min", 30.0, False),
        ("duracion_enfriado", "Duración Enfriado", "min", 40.0, False),
        ("caudal_enfriador", "Caudal Bomba/Enfriador", "L/min", 3.5, False),
        ("perdida_turb_enfriador", "Pérdida Turb/Enfriador", "L", 4.0, False),
        ("expansion_termica", "Expansión Térmica Mosto", "%", 4.0, False),
    ]),
    ("Control de pH y Fermentación", [
        ("ph_mash", "pH Mash Objetivo", "pH", 5.3, False),
        ("ph_lavado", "pH Lavado Objetivo", "pH", 5.2, False),
        ("ph_prehervor", "pH Pre-Hervor Objetivo", "pH", 5.2, False),
        ("ph_posthervor", "pH Post-Hervor Objetivo", "pH", 5.2, False),
        ("tasa_inoculacion", "Tasa de Inoculación", "", "0.75 M cel/ml/°P", True),
    ]),
]


def _huella(obj):
    """Huella del contenido de una receta: sirve para saber si cambió de verdad."""
    try:
        return hashlib.md5(json.dumps(obj, sort_keys=True,
                                      ensure_ascii=False).encode()).hexdigest()[:12]
    except Exception:
        return ""


def format_num(val):
    """Formatea números para la UI, quitando el .0 si es entero (ej. 300.0 -> 300)"""
    try:
        num = float(val)
        return str(int(num)) if num.is_integer() else str(num)
    except (ValueError, TypeError):
        return str(val) if val is not None else ""


def resource_path(relative_path):
    """ Retorna la ruta absoluta para recursos, estables tanto en dev como en el EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def _flotar(val, por_defecto=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return por_defecto


class AyudaDialog(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Manual de Usuario - Cervecera VGB")
        self.geometry("750x650")
        self.minsize(400, 300)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.texto_ayuda = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=14))
        self.texto_ayuda.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        frame_contacto = ctk.CTkFrame(self, fg_color="#2c2c2c", corner_radius=8)
        frame_contacto.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="ew")
        ctk.CTkLabel(frame_contacto, text="👨‍💻 Autor: SaintWick", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(frame_contacto, text="📧 nicoweb45@proton.me (Asunto: beer_vgb)", font=ctk.CTkFont(size=13)).pack(side="right", padx=15, pady=10)
        btn_cerrar = ctk.CTkButton(self, text="Cerrar Manual", command=self.destroy, fg_color="#6B7280", hover_color="#4B5563")
        btn_cerrar.grid(row=2, column=0, padx=20, pady=(10, 20))
        mensaje = """
🍺 MANUAL DE USUARIO - CERVECERA VGB (v17 - auto-amargor)

📝 1. RECETA:
Nombre, volumen, eficiencia, ALTITUD (afecta IBU) y LEVADURA
(define FG por atenuación y tolerancia de ABV).
Maceración: ratio L/kg, absorción L/kg y tiempo de hervor (min)
→ calcula agua de maceración, lavado y evaporación.
LOS RESULTADOS (OG, FG, ABV, IBU, SRM, color, BU/GU, calorías, pH)
se muestran en el PANEL DERECHO y se recalculan EN TIEMPO REAL
mientras editás los inputs. Abajo, los PROCESOS en orden
(Macerado → Lavado → Hervor → Fermentación).
🎯 AUTO-AMARGOR: botón en el header de Lúpulos. Calcula los gramos de UNA
única adición de amargor @60 min para el IBU objetivo (medio del rango BJCP
del estilo elegido, o cargado a mano), usando la FÓRMULA ACTIVA del combo
"Fórmula IBU" (Tinseth o Rager). El diálogo muestra también el gramaje de
la otra fórmula como referencia. Reemplaza los lúpulos actuales tras confirmar.

💧 Perfil del Agua: elegí un perfil de Córdoba o cargá Ca/Mg/HCO3/pH.
El pH del agua de entrada participa en el pH estimado de maceración.
Maltas y Lúpulos desde el catálogo argentino (autocompletan Ext/Color y
AA%/formato). Podés escalonar lúpulos (varias líneas).
Resultados: OG, FG (auto por levadura), ABV, atenuación, IBU, SRM,
BU/GU, calorías, aguas, pH (entrada/maceración/post-hervor/final),
ácido láctico recomendado para fijar pH 5.3 y alerta de levadura.

📊 2. COMPARADOR BJCP: estilo objetivo con rangos oficiales (OG, FG, IBU, SRM).
📦 3. INVENTARIO: carga tu stock real; al calcular, valida disponibilidad.
💾 4. EXPORTACIÓN: PDF profesional y BeerXML (Brewfather/Grainfather…).
📖 5. AGREGAR RECETAS (sin reinstalar):
Al abrir la app, se busca solo el recetario más reciente en la web y se
fusiona automáticamente (sin que hagas nada).
También podés usar "🔄 Buscar recetas nuevas" (manual) o "📂 Importar JSON"
con un archivo descargado. Las recetas nuevas quedan guardadas.
⬆️ 6. ACTUALIZAR LA APP:
Botón "⬆️ Comprobar actualizaciones": si hay una versión nueva, la descarga.
En Windows se instala sola (en silencio); en Linux/macOS la descarga y la abre.
🧾 7. REGISTRO DE ERRORES:
Si algo falla, usá el botón "🧾 Ver log" (arriba) para ver la ruta del archivo
de registro. Windows: %LOCALAPPDATA%\\Cervecera VGB\\cervecera_debug.log

🔬 FUENTES DE LAS FÓRMULAS
OG/Extracto: potencial PPG x eficiencia (BeerSmith / Brewfather).
FG: atenuacion de levadura; modo Normal ajusta por temperatura de macerado
(beta-amilasa 60-65 C = mas fermentable; alfa-amilasa 67-72 C = mas dextrinas).
IBU: Tinseth (Glenn Tinseth) y Rager (libreria brauhaus). Para flameout/whirlpool
se estima la isomerizacion posterior al apagado (John-Paul Hosom - alchemyoverlord:
la utilizacion cae y se detiene ~82 C).
Color: Morey (MCU -> SRM). Conversion EBC = SRM x 1.97 (Brewfather).
ABV: Standard (OG-FG)x131.25 ; Alternative 76.08*(OG-FG)/(1.775-OG)*(FG/0.794)
(formulas documentadas por Brewfather).
Densimetro: correccion ASBC. pH: alcalinidad residual (Palmer) + acidez del grano
(tope de acidez tostada calibrado con ficha Dry Irish Stout).
Agua: referencia DM Riffe (homebrewingphysics) y Kai Troester (braukaiser).
Levadura: Kai Troester y Chris White. Refractometro: Petr Novotny.
Estilos: BJCP 2021 - Brewers Association - Norbrygg - SHBF.
Interoperabilidad: BeerXML (beerxml.com).
Refs: docs.brewfather.app/settings.md - docs.brewfather.app/recipes/calculations.md

📧 9. CONTACTO: nicoweb45@proton.me (Asunto: beer_vgb)
"""
        self.texto_ayuda.insert("1.0", mensaje)
        self.texto_ayuda.configure(state="disabled")
        # Forzar el foco para que la ventana se abra siempre en primer plano en Windows
        self.after(200, lambda: self.focus_force())


class GestionMixin:
    def setup_tab_inventario(self, parent):
        # Contenedor propio: evita pisar la numeración de filas del padre (Insumos).
        cont = ctk.CTkFrame(parent, fg_color="transparent")
        cont.grid(row=3, column=0, sticky="nsew")
        cont.grid_columnconfigure(0, weight=1)

        kpis = ctk.CTkFrame(cont)
        kpis.grid(row=0, column=0, padx=20, pady=(8, 4), sticky="ew")
        kpis.grid_columnconfigure((0, 1, 2), weight=1)
        self.lbl_kpi_valorizacion = ctk.CTkLabel(kpis, text="💲 Valorización: $0",
                                                 font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_kpi_valorizacion.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.lbl_kpi_total = ctk.CTkLabel(kpis, text="📦 Insumos: 0", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_kpi_total.grid(row=0, column=1, padx=10, pady=8)
        self.lbl_kpi_bajo = ctk.CTkLabel(kpis, text="⚠️ Stock bajo: 0", font=ctk.CTkFont(size=13, weight="bold"),
                                         text_color="#F59E0B")
        self.lbl_kpi_bajo.grid(row=0, column=2, padx=10, pady=8, sticky="e")

        frame_add = ctk.CTkFrame(cont)
        frame_add.grid(row=1, column=0, padx=20, pady=8, sticky="ew")
        cab = ctk.CTkFrame(frame_add, fg_color="transparent")
        cab.grid(row=0, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
        cab.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(cab, text="📦 Inventario — Añadir / Sumar Stock", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(cab, text="📋 Pegar productos", command=self.abrir_dialogo_pegar_productos,
                      fg_color="#0D9488", hover_color="#0F766E").grid(row=0, column=1, sticky="e", padx=4)
        ctk.CTkButton(cab, text="🔻 Consumo / Merma", command=self.abrir_dialogo_consumo_inventario,
                      fg_color="#D97706", hover_color="#B45309").grid(row=0, column=2, sticky="e")
        ctk.CTkLabel(frame_add, text="Tipo:").grid(row=1, column=0, padx=5, pady=5)
        self.combo_tipo_inv = ctk.CTkComboBox(frame_add, values=TIPOS_INVENTARIO, width=120)
        self.combo_tipo_inv.set("Malta")
        self.combo_tipo_inv.grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Nombre:").grid(row=1, column=2, padx=5, pady=5)
        self.entry_nombre_inv = ctk.CTkEntry(frame_add, placeholder_text="Ej: Pale Malt", width=150)
        self.entry_nombre_inv.grid(row=1, column=3, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Cantidad:").grid(row=2, column=0, padx=5, pady=5)
        self.entry_cantidad_inv = ctk.CTkEntry(frame_add, placeholder_text="Ej: 5", width=120)
        self.entry_cantidad_inv.grid(row=2, column=1, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Unidad:").grid(row=2, column=2, padx=5, pady=5)
        self.combo_unidad_inv = ctk.CTkComboBox(frame_add, values=["Kg", "g", "Uds", "L"], width=120)
        self.combo_unidad_inv.set("Kg")
        self.combo_unidad_inv.grid(row=2, column=3, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Costo unit. $:").grid(row=3, column=0, padx=5, pady=5)
        self.entry_costo_inv = ctk.CTkEntry(frame_add, placeholder_text="Ej: 1500 (opcional)", width=120)
        self.entry_costo_inv.grid(row=3, column=1, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Mínimo (alerta):").grid(row=3, column=2, padx=5, pady=5)
        self.entry_minimo_inv = ctk.CTkEntry(frame_add, placeholder_text="Ej: 2 (opcional)", width=120)
        self.entry_minimo_inv.grid(row=3, column=3, padx=5, pady=5)
        ctk.CTkLabel(frame_add, text="Vencimiento:").grid(row=4, column=0, padx=5, pady=5)
        self.entry_vencimiento_inv = ctk.CTkEntry(frame_add, placeholder_text="AAAA-MM-DD (opcional)", width=150)
        self.entry_vencimiento_inv.grid(row=4, column=1, columnspan=3, padx=5, pady=5, sticky="w")
        ctk.CTkButton(frame_add, text="Añadir al Inventario", command=self.agregar_inventario_ui, fg_color="#059669", hover_color="#047857").grid(row=5, column=0, columnspan=4, pady=15)

        frame_lista_inv = ctk.CTkFrame(cont)
        frame_lista_inv.grid(row=2, column=0, padx=20, pady=(0, 8), sticky="nsew")
        ctk.CTkLabel(frame_lista_inv, text="📦 Stock Disponible", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        self.lista_inventario_ui = ctk.CTkScrollableFrame(frame_lista_inv, height=220)
        self.lista_inventario_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        frame_kardex = ctk.CTkFrame(cont)
        frame_kardex.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")
        ctk.CTkLabel(frame_kardex, text="📜 Historial de Movimientos (Kardex)",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=8)
        self.lista_kardex_ui = ctk.CTkScrollableFrame(frame_kardex, height=150)
        self.lista_kardex_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.cargar_lista_inventario()

    def setup_tab_equipos(self):
        self.tab_equipos.grid_columnconfigure(0, weight=1)
        self.tab_equipos.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self.tab_equipos, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        c = ctk.CTkFrame(scroll)
        c.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        c.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(c, text="⚙️ Perfiles de equipo", font=ctk.CTkFont(size=16, weight="bold")
                     ).grid(row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(8, 4))
        campos = [("name", "Nombre"), ("batch_volume", "Lote (L)"), ("kettle_volume", "Olla (L)"),
                  ("perdidas_l", "Pérdidas (L)"), ("evaporacion_l_h", "Evap. (L/h)"),
                  ("eficiencia_pct", "Eficiencia %"), ("temp_macerado", "Temp. macerado (C)"),
                  ("notas", "Notas")]
        self._eq_entries = {}
        fila = 1
        for i, (clave, etiqueta) in enumerate(campos):
            col = (i % 3) * 2
            if i > 0 and i % 3 == 0:
                fila += 1
            ctk.CTkLabel(c, text=f"{etiqueta}:").grid(row=fila, column=col, sticky="w", padx=6, pady=3)
            e = ctk.CTkEntry(c, width=110)
            e.grid(row=fila, column=col + 1, sticky="ew", padx=4, pady=3)
            self._eq_entries[clave] = e
        fila += 1
        # ---- Valores por defecto extendidos (Maceración/Mermas/pH), tal cual Brewomatic ----
        self._eq_extra_entries = {}
        for titulo_grupo, campos_grupo in EQUIPO_EXTRA_GRUPOS:
            ctk.CTkLabel(c, text=titulo_grupo.upper(), font=ctk.CTkFont(size=11, weight="bold"),
                         text_color="#9ecaff").grid(row=fila, column=0, columnspan=6, sticky="w",
                                                    padx=8, pady=(10, 2))
            fila += 1
            for i, (clave, etiqueta, unidad, default, es_texto) in enumerate(campos_grupo):
                col = (i % 3) * 2
                if i > 0 and i % 3 == 0:
                    fila += 1
                lbl = f"{etiqueta} ({unidad}):" if unidad else f"{etiqueta}:"
                ctk.CTkLabel(c, text=lbl).grid(row=fila, column=col, sticky="w", padx=6, pady=3)
                e = ctk.CTkEntry(c, width=110)
                e.grid(row=fila, column=col + 1, sticky="ew", padx=4, pady=3)
                self._eq_extra_entries[clave] = e
            fila += 1
        ctk.CTkButton(c, text="💾 Guardar / Actualizar", command=self._eq_guardar,
                      fg_color="#059669", hover_color="#047857"
                      ).grid(row=fila, column=0, columnspan=2, padx=6, pady=10, sticky="w")
        ctk.CTkButton(c, text="🧹 Limpiar", command=self._eq_limpiar,
                      fg_color="#6B7280", hover_color="#4B5563").grid(row=fila, column=2, padx=6, pady=10, sticky="w")
        fl = ctk.CTkFrame(scroll)
        fl.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.lista_equipos_ui = ctk.CTkScrollableFrame(fl, height=220)
        self.lista_equipos_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.cargar_lista_equipos()

    def _eq_limpiar(self):
        for e in self._eq_entries.values():
            e.delete(0, "end")
        for e in self._eq_extra_entries.values():
            e.delete(0, "end")

    def cargar_lista_equipos(self):
        for w in self.lista_equipos_ui.winfo_children():
            w.destroy()
        for eq in self.db.get_equipment():
            f = ctk.CTkFrame(self.lista_equipos_ui, fg_color="transparent")
            f.pack(fill="x", pady=2)
            txt_eq = (f"[Equipo] {eq['name']} — lote {format_num(eq['batch_volume'])} L · "
                      f"olla {format_num(eq['kettle_volume'])} L · pérdidas {format_num(eq['perdidas_l'])} L · "
                      f"evap {format_num(eq['evaporacion_l_h'])} L/h · ef {format_num(round(eq['eficiencia']*100,1))}% · "
                      f"macerado {format_num(eq['temp_macerado'])} C")
            ctk.CTkLabel(f, text=txt_eq, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(f, text="✏️", width=34, fg_color="#2563EB", hover_color="#1D4ED8",
                          command=lambda n=eq['name']: self._eq_editar(n)).pack(side="right", padx=3)
            ctk.CTkButton(f, text="🗑️", width=34, fg_color="#DC2626", hover_color="#991B1B",
                          command=lambda n=eq['name']: self._eq_borrar(n)).pack(side="right", padx=3)

    def _eq_editar(self, nombre):
        eq = self.db.get_equipment_by_name(nombre) or {}
        for clave, e in self._eq_entries.items():
            e.delete(0, "end")
            if clave == "eficiencia_pct":
                e.insert(0, format_num(round((eq.get("eficiencia") or 0.75) * 100, 1)))
            elif eq.get(clave) not in (None, ""):
                e.insert(0, format_num(eq.get(clave)))
        extra = self.db.get_equipo_extra(nombre)
        for _, campos_grupo in EQUIPO_EXTRA_GRUPOS:
            for clave, _etq, _u, default, es_texto in campos_grupo:
                e = self._eq_extra_entries[clave]
                e.delete(0, "end")
                valor = extra.get(clave, default)
                e.insert(0, valor if es_texto else format_num(valor))

    def _eq_borrar(self, nombre):
        if mb.askyesno("Eliminar equipo", f"¿Eliminar '{nombre}'?"):
            self.db.delete_equipment(nombre)
            self.cargar_lista_equipos()
            self.combo_equipo.configure(values=self._nombres_equipos())

    def _eq_guardar(self):
        def num(k, d=0.0):
            try:
                v = self._eq_entries[k].get().strip()
                return float(v.replace(",", ".")) if v else d
            except ValueError:
                return d
        nombre = self._eq_entries["name"].get().strip()
        if not nombre:
            mb.showwarning("Atención", "Escribí el nombre del equipo."); return
        self.db.add_equipment(nombre, batch_volume=num("batch_volume", 20),
                              kettle_volume=num("kettle_volume", 30), perdidas_l=num("perdidas_l", 2),
                              evaporacion_l_h=num("evaporacion_l_h", 2),
                              eficiencia=num("eficiencia_pct", 75) / 100.0,
                              temp_macerado=num("temp_macerado", 66),
                              notas=self._eq_entries["notas"].get().strip())
        extra = {}
        for _, campos_grupo in EQUIPO_EXTRA_GRUPOS:
            for clave, _etq, _u, default, es_texto in campos_grupo:
                v = self._eq_extra_entries[clave].get().strip()
                if es_texto:
                    extra[clave] = v or default
                else:
                    try:
                        extra[clave] = float(v.replace(",", ".")) if v else default
                    except ValueError:
                        extra[clave] = default
        self.db.set_equipo_extra(nombre, extra)
        self.cargar_lista_equipos()
        self.combo_equipo.configure(values=self._nombres_equipos())
        mb.showinfo("Equipos", f"Equipo guardado:\n{nombre}")

    # ==========================================
    # CATÁLOGO DE INSUMOS (pestaña, Fase 2)
    # ==========================================
    def setup_tab_insumos(self):
        self.tab_insumos.grid_columnconfigure(0, weight=1)
        self.tab_insumos.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self.tab_insumos, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        card_ing = ctk.CTkFrame(scroll)
        card_ing.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        card_ing.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(card_ing, text="🧪 Catálogo de insumos (editable)",
                     font=ctk.CTkFont(size=16, weight="bold")
                     ).grid(row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(8, 4))
        ctk.CTkLabel(card_ing, text="Tipo:").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        self.combo_ing_tipo = ctk.CTkComboBox(card_ing, values=["Malta", "Lúpulo", "Levadura"], width=130)
        self.combo_ing_tipo.set("Malta")
        self.combo_ing_tipo.grid(row=1, column=1, sticky="w", padx=4, pady=3)
        ctk.CTkLabel(card_ing, text="Nombre:").grid(row=1, column=2, sticky="w", padx=6, pady=3)
        self.e_ing_nombre = ctk.CTkEntry(card_ing, placeholder_text="Ej: Mi Malta Local")
        self.e_ing_nombre.grid(row=1, column=3, columnspan=3, sticky="ew", padx=4, pady=3)
        campos = [("origin", "Origen"), ("supplier", "Proveedor/Lab"), ("category", "Categoría"),
                  ("color", "Color (Lovi)"), ("extract", "Extracto"), ("ppg", "PPG"),
                  ("yield_pct", "Rend. %"), ("diastatic", "Diastático"), ("alpha", "AA %"),
                  ("form", "Formato"), ("attenuation", "Atenuación %"), ("abv_tolerance", "Tol. ABV"),
                  ("temp_range", "Temp (ºC)"), ("notes", "Notas")]
        self._ing_entries = {}
        fila = 2
        for i, (clave, etiqueta) in enumerate(campos):
            col = (i % 3) * 2
            if i > 0 and i % 3 == 0:
                fila += 1
            ctk.CTkLabel(card_ing, text=f"{etiqueta}:").grid(row=fila, column=col, sticky="w", padx=6, pady=3)
            e = ctk.CTkEntry(card_ing, width=90)
            e.grid(row=fila, column=col + 1, sticky="ew", padx=4, pady=3)
            self._ing_entries[clave] = e
        fila += 1
        ctk.CTkButton(card_ing, text="💾 Guardar / Actualizar", command=self._ing_guardar,
                      fg_color="#059669", hover_color="#047857").grid(row=fila, column=0, columnspan=2, padx=6, pady=10, sticky="w")
        ctk.CTkButton(card_ing, text="🧹 Limpiar", command=self._ing_limpiar,
                      fg_color="#6B7280", hover_color="#4B5563").grid(row=fila, column=2, padx=6, pady=10, sticky="w")
        ctk.CTkLabel(card_ing, text="Completá solo los campos que apliquen al tipo elegido.",
                     text_color="#9CA3AF").grid(row=fila, column=3, columnspan=3, sticky="w", padx=6)
        frame_lista = ctk.CTkFrame(scroll)
        frame_lista.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="nsew")
        ctk.CTkLabel(frame_lista, text="Insumos cargados", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=(8, 2))
        self.seg_ing_filtro = ctk.CTkSegmentedButton(
            frame_lista, values=["Todos", "Malta", "Lúpulo", "Levadura"],
            command=lambda _sel=None: self.cargar_lista_insumos())
        self.seg_ing_filtro.set("Todos")
        self.seg_ing_filtro.pack(pady=(0, 8))
        self.lista_insumos_ui = ctk.CTkScrollableFrame(frame_lista, height=220)
        self.lista_insumos_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.cargar_lista_insumos()
        ctk.CTkFrame(scroll, height=2, fg_color="#374151").grid(row=2, column=0, sticky="ew", padx=20, pady=6)
        self.setup_tab_inventario(scroll)

    def cargar_lista_insumos(self):
        for w in self.lista_insumos_ui.winfo_children():
            w.destroy()
        filtro = self.seg_ing_filtro.get() if hasattr(self, "seg_ing_filtro") else "Todos"
        for ing in self.db.get_ingredients():
            if filtro != "Todos" and ing["type"] != filtro:
                continue
            fila = ctk.CTkFrame(self.lista_insumos_ui, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            det = []
            if ing.get("extract"): det.append(f"Ext {format_num(ing['extract'])}")
            if ing.get("color"): det.append(f"Color {format_num(ing['color'])}")
            if ing.get("alpha"): det.append(f"AA {format_num(ing['alpha'])}%")
            if ing.get("form"): det.append(f"{ing['form']}")
            if ing.get("attenuation"): det.append(f"Aten. {format_num(ing['attenuation'])}%")
            if ing.get("abv_tolerance"): det.append(f"ABV {format_num(ing['abv_tolerance'])}%")
            if ing.get("origin"): det.append(f"{ing['origin']}")
            if ing.get("supplier"): det.append(f"{ing['supplier']}")
            texto = f"[{ing['type']}] {ing['name']}" + (f" — {' · '.join(det)}" if det else "")
            ctk.CTkLabel(fila, text=texto, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(fila, text="✏️", width=34, fg_color="#2563EB", hover_color="#1D4ED8",
                          command=lambda t=ing['type'], n=ing['name']: self._ing_editar(t, n)).pack(side="right", padx=3)
            ctk.CTkButton(fila, text="🗑️", width=34, fg_color="#DC2626", hover_color="#991B1B",
                          command=lambda t=ing['type'], n=ing['name']: self._ing_borrar(t, n)).pack(side="right", padx=3)

    def _ing_limpiar(self):
        self.e_ing_nombre.delete(0, "end")
        for e in self._ing_entries.values():
            e.delete(0, "end")

    def _ing_editar(self, tipo, nombre):
        ing = self.db.get_ingredient(tipo, nombre) or {}
        self.combo_ing_tipo.set(tipo)
        self.e_ing_nombre.delete(0, "end"); self.e_ing_nombre.insert(0, nombre)
        for clave, e in self._ing_entries.items():
            e.delete(0, "end")
            v = ing.get(clave)
            if v not in (None, "", 0):
                e.insert(0, format_num(v))

    def _ing_borrar(self, tipo, nombre):
        if mb.askyesno("Eliminar insumo", f"¿Eliminar '{nombre}' ({tipo}) del catálogo?"):
            self.db.delete_ingredient(tipo, nombre)
            self.cargar_lista_insumos()

    def _ing_guardar(self):
        tipo = self.combo_ing_tipo.get()
        nombre = self.e_ing_nombre.get().strip()
        if not nombre:
            mb.showwarning("Atención", "Escribí el nombre del insumo."); return
        def num(clave):
            try:
                v = self._ing_entries[clave].get().strip()
                return float(v) if v else None
            except ValueError:
                return None
        campos = {
            "origin": self._ing_entries["origin"].get().strip(),
            "supplier": self._ing_entries["supplier"].get().strip(),
            "category": self._ing_entries["category"].get().strip(),
            "notes": self._ing_entries["notes"].get().strip(),
            "temp_range": self._ing_entries["temp_range"].get().strip(),
            "form": self._ing_entries["form"].get().strip(),
            "color": num("color"), "extract": num("extract"), "ppg": num("ppg"),
            "yield_pct": num("yield_pct"), "diastatic": num("diastatic"),
            "alpha": num("alpha"), "attenuation": num("attenuation"),
            "abv_tolerance": num("abv_tolerance"),
        }
        campos = {k: v for k, v in campos.items() if v not in (None, "")}
        self.db.add_ingredient(tipo, nombre, **campos)
        self.cargar_lista_insumos()
        mb.showinfo("Catálogo", f"Insumo guardado:\n{tipo} · {nombre}")

    # ==========================================
    # LÓGICA DE INVENTARIO
    # ==========================================
    def agregar_inventario_ui(self):
        tipo = self.combo_tipo_inv.get()
        nombre = self.entry_nombre_inv.get().strip()
        cantidad_str = self.entry_cantidad_inv.get().strip()
        unidad = self.combo_unidad_inv.get()
        if not nombre or not cantidad_str:
            mb.showwarning("Atención", "Rellena el nombre y la cantidad."); return
        try:
            cantidad = float(cantidad_str)
            if cantidad <= 0: raise ValueError
        except ValueError:
            mb.showerror("Error", "La cantidad debe ser un número positivo."); return
        self.db.add_inventory_item(tipo, nombre, cantidad, unidad, motivo="Ingreso manual")
        item = self.db.get_inventory_item_by_name(tipo, nombre)
        if item:
            costo = _flotar(self.entry_costo_inv.get().replace(",", "."), None)
            minimo = _flotar(self.entry_minimo_inv.get().replace(",", "."), None)
            vencimiento = self.entry_vencimiento_inv.get().strip() or None
            if costo is not None or minimo is not None or vencimiento is not None:
                self.db.update_inventory_details(item["id"], costo_unitario=costo,
                                                 minimo=minimo, vencimiento=vencimiento)
        mb.showinfo("Éxito", f"Stock de {nombre} actualizado.")
        for e in (self.entry_nombre_inv, self.entry_cantidad_inv, self.entry_costo_inv,
                 self.entry_minimo_inv, self.entry_vencimiento_inv):
            e.delete(0, "end")
        self.cargar_lista_inventario()
        self.calcular_y_mostrar()

    def abrir_dialogo_consumo_inventario(self):
        """Registra una salida (consumo de cocción) o una merma, dejando constancia en el Kardex."""
        items = self.db.get_all_inventory()
        if not items:
            mb.showinfo("Inventario", "No hay stock cargado todavía."); return
        nombres = [f"{it['type']} · {it['name']} ({format_num(it['amount'])} {it['unit']})" for it in items]
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Registrar Consumo / Merma")
        dialogo.geometry("420x300")
        dialogo.transient(self); dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="Insumo:").pack(anchor="w", padx=15, pady=(15, 2))
        combo_item = ctk.CTkComboBox(dialogo, values=nombres, width=380)
        combo_item.set(nombres[0])
        combo_item.pack(padx=15)
        ctk.CTkLabel(dialogo, text="Cantidad a descontar:").pack(anchor="w", padx=15, pady=(10, 2))
        entry_cant = ctk.CTkEntry(dialogo, width=380, placeholder_text="Ej: 2.5")
        entry_cant.pack(padx=15)
        ctk.CTkLabel(dialogo, text="Motivo:").pack(anchor="w", padx=15, pady=(10, 2))
        combo_tipo_mov = ctk.CTkComboBox(dialogo, values=["Salida (consumo de cocción)", "Merma", "Ajuste"], width=380)
        combo_tipo_mov.set("Salida (consumo de cocción)")
        combo_tipo_mov.pack(padx=15)
        entry_nota = ctk.CTkEntry(dialogo, width=380, placeholder_text="Nota (opcional): ej. Lote #24")
        entry_nota.pack(padx=15, pady=(10, 0))

        def confirmar():
            idx = nombres.index(combo_item.get()) if combo_item.get() in nombres else 0
            item = items[idx]
            try:
                cantidad = float(entry_cant.get().strip().replace(",", "."))
                if cantidad <= 0: raise ValueError
            except ValueError:
                mb.showerror("Error", "Cantidad inválida."); return
            tipo_mov = "Salida" if combo_tipo_mov.get().startswith("Salida") else combo_tipo_mov.get()
            self.db.subtract_inventory_item(item["type"], item["name"], cantidad,
                                            tipo=tipo_mov, motivo=entry_nota.get().strip())
            self.cargar_lista_inventario()
            self.calcular_y_mostrar()
            dialogo.destroy()

        ctk.CTkButton(dialogo, text="✅ Registrar", command=confirmar,
                      fg_color="#059669", hover_color="#047857").pack(pady=15)

    def eliminar_item_inventario(self, item_id):
        self.db.delete_inventory_item(item_id)
        self.cargar_lista_inventario()
        self.calcular_y_mostrar()

    # ------------------------------------------
    # Pegar productos → auto-detección (tipo BrewersFriend: matchea contra catálogo)
    # ------------------------------------------
    def _catalogo_para_matching(self) -> dict[str, tuple[str, str]]:
        return {ing["name"].lower(): (ing["type"], ing["name"]) for ing in self.db.get_ingredients()}

    def abrir_dialogo_pegar_productos(self):
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Pegar productos")
        dialogo.geometry("720x560")
        dialogo.transient(self)
        dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="Pegá el texto con los productos (uno por línea): factura, lista de "
                     "proveedor o planilla. Se detecta nombre, cantidad, unidad y tipo automáticamente.",
                     wraplength=680, justify="left").pack(padx=15, pady=(15, 5), anchor="w")
        txt = ctk.CTkTextbox(dialogo, height=140)
        txt.pack(fill="x", padx=15, pady=5)
        frame_preview = ctk.CTkScrollableFrame(dialogo, label_text="Vista previa (revisá y confirmá)")
        frame_preview.pack(fill="both", expand=True, padx=15, pady=10)
        filas_preview: list[dict] = []

        def analizar():
            for w in frame_preview.winfo_children():
                w.destroy()
            filas_preview.clear()
            productos = parsear_texto_productos(txt.get("1.0", "end"), self._catalogo_para_matching())
            if not productos:
                ctk.CTkLabel(frame_preview, text="No se detectaron productos en el texto.").pack(pady=10)
                return
            for p in productos:
                fila = ctk.CTkFrame(frame_preview, fg_color="transparent")
                fila.pack(fill="x", pady=2)
                var_incluir = ctk.BooleanVar(value=True)
                ctk.CTkCheckBox(fila, text="", variable=var_incluir, width=20).pack(side="left", padx=(2, 6))
                c_tipo = ctk.CTkComboBox(fila, values=TIPOS_INVENTARIO, width=100)
                c_tipo.set(p["tipo"] if p["tipo"] in TIPOS_INVENTARIO else "Otro")
                c_tipo.pack(side="left", padx=3)
                e_nombre = ctk.CTkEntry(fila, width=220)
                e_nombre.insert(0, p["nombre"])
                e_nombre.pack(side="left", padx=3, fill="x", expand=True)
                e_cant = ctk.CTkEntry(fila, width=70)
                e_cant.insert(0, format_num(p["cantidad"]))
                e_cant.pack(side="left", padx=3)
                c_unidad = ctk.CTkComboBox(fila, values=["Kg", "g", "Uds", "L"], width=80)
                c_unidad.set(p["unidad"])
                c_unidad.pack(side="left", padx=3)
                filas_preview.append({"incluir": var_incluir, "tipo": c_tipo, "nombre": e_nombre,
                                       "cantidad": e_cant, "unidad": c_unidad})

        def confirmar():
            agregados = 0
            for f in filas_preview:
                if not f["incluir"].get():
                    continue
                nombre = f["nombre"].get().strip()
                if not nombre:
                    continue
                try:
                    cantidad = float(f["cantidad"].get().replace(",", "."))
                    if cantidad <= 0:
                        continue
                except ValueError:
                    continue
                self.db.add_inventory_item(f["tipo"].get(), nombre, cantidad, f["unidad"].get())
                agregados += 1
            self.cargar_lista_inventario()
            self.calcular_y_mostrar()
            dialogo.destroy()
            mb.showinfo("Inventario", f"{agregados} producto(s) importado(s) al inventario.")

        frame_botones = ctk.CTkFrame(dialogo, fg_color="transparent")
        frame_botones.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkButton(frame_botones, text="🔍 Analizar", command=analizar,
                      fg_color="#2563EB", hover_color="#1D4ED8").pack(side="left")
        ctk.CTkButton(frame_botones, text="✅ Importar seleccionados", command=confirmar,
                      fg_color="#059669", hover_color="#047857").pack(side="right")
        ctk.CTkButton(frame_botones, text="Cancelar", command=dialogo.destroy,
                      fg_color="#6B7280", hover_color="#4B5563").pack(side="right", padx=8)

    def cargar_lista_inventario(self):
        for w in self.lista_inventario_ui.winfo_children():
            w.destroy()
        items = self.db.get_all_inventory()
        valorizacion, bajo_stock = 0.0, 0
        for item in items:
            costo = item["costo_unitario"] or 0
            minimo = item["minimo"] or 0
            valorizacion += (item["amount"] or 0) * costo
            es_bajo = minimo > 0 and item["amount"] <= minimo
            if es_bajo:
                bajo_stock += 1
            fila = ctk.CTkFrame(self.lista_inventario_ui, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            texto = f"[{item['type']}] {item['name']} - {format_num(item['amount'])} {item['unit']}"
            if costo:
                texto += f" · ${format_num(costo)}/u"
            if item["vencimiento"]:
                texto += f" · vence {item['vencimiento']}"
            if es_bajo:
                texto += "  ⚠️ STOCK BAJO"
            ctk.CTkLabel(fila, text=texto, anchor="w",
                         text_color="#F59E0B" if es_bajo else None).pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(fila, text="🗑️", width=30, fg_color="#DC2626", hover_color="#991B1B",
                          command=lambda iid=item['id']: self.eliminar_item_inventario(iid)).pack(side="right", padx=5)
        # ---- KPIs ----
        if hasattr(self, "lbl_kpi_valorizacion"):
            self.lbl_kpi_valorizacion.configure(text=f"💲 Valorización: ${format_num(round(valorizacion, 2))}")
            self.lbl_kpi_total.configure(text=f"📦 Insumos: {len(items)}")
            self.lbl_kpi_bajo.configure(text=f"⚠️ Stock bajo: {bajo_stock}")
        # ---- Kardex (últimos movimientos) ----
        if hasattr(self, "lista_kardex_ui"):
            for w in self.lista_kardex_ui.winfo_children():
                w.destroy()
            movimientos = self.db.get_inventory_movimientos(limit=15)
            if not movimientos:
                ctk.CTkLabel(self.lista_kardex_ui, text="Sin movimientos todavía.",
                             text_color="#9CA3AF").pack(pady=8)
            iconos = {"Entrada": "🟢 +", "Salida": "🔴 -", "Merma": "🟠 -", "Ajuste": "🔵 ~"}
            for m in movimientos:
                f = ctk.CTkFrame(self.lista_kardex_ui, fg_color="transparent")
                f.pack(fill="x", pady=1)
                signo = iconos.get(m["tipo"], "• ")
                texto = f"{signo}{format_num(m['cantidad'])} · {m['item_name']} · {m['fecha']}"
                if m["motivo"]:
                    texto += f" ({m['motivo']})"
                ctk.CTkLabel(f, text=texto, anchor="w", font=ctk.CTkFont(size=11)).pack(side="left", padx=5, fill="x", expand=True)

    def validar_inventario_receta(self, maltas, lupulos):
        alertas = []
        for m in maltas:
            if m['cantidad'] <= 0: continue
            item = self.db.get_inventory_item_by_name('Malta', m['nombre'])
            if item:
                disponible = item['amount']
                if disponible >= m['cantidad']:
                    alertas.append(f"✅ {m['nombre']}: {disponible} Kg (Req: {m['cantidad']} Kg)")
                else:
                    alertas.append(f"❌ {m['nombre']}: Falta {round(m['cantidad'] - disponible, 2)} Kg (Disp: {disponible} Kg)")
            else:
                alertas.append(f"❌ {m['nombre']}: No en inventario (Req: {m['cantidad']} Kg)")
        for l in lupulos:
            if l['cantidad'] <= 0: continue
            item = self.db.get_inventory_item_by_name('Lúpulo', l['nombre'])
            if item:
                disponible = item['amount']
                if disponible >= l['cantidad']:
                    alertas.append(f"✅ {l['nombre']}: {disponible} g (Req: {l['cantidad']} g)")
                else:
                    alertas.append(f"❌ {l['nombre']}: Falta {round(l['cantidad'] - disponible, 2)} g (Disp: {disponible} g)")
            else:
                alertas.append(f"❌ {l['nombre']}: No en inventario (Req: {l['cantidad']} g)")
        return "\n".join(alertas)

    # ==========================================
    # LISTA / SELECCIÓN / NUEVA / GUARDAR
    # ==========================================
    def cargar_lista_recetas(self):
        for w in self.lista_recetas.winfo_children():
            w.destroy()
        for r in self.db.get_all_recipes_summary():
            ctk.CTkButton(self.lista_recetas,
                          text=f"{r['name']} ({r['volume']}L)",
                          fg_color="transparent", border_width=1,
                          text_color=("gray10", "gray90"),
                          hover_color=("gray70", "gray30"), anchor="w",
                          command=lambda r_id=r['id']: self.seleccionar_receta(r_id)
                          ).pack(pady=5, padx=5, fill="x")

    def seleccionar_receta(self, receta_id):
        receta = self.db.get_full_recipe(receta_id)
        if not receta: return
        self.receta_actual_id = receta_id
        self.entry_nombre.delete(0, "end"); self.entry_nombre.insert(0, receta['name'])
        self.volumen_base_receta = float(receta['volume'])
        vol_str = str(int(self.volumen_base_receta))
        self.combo_volumen.set(vol_str if vol_str in VOLUMENES_PRESET else vol_str)
        self.entry_eficiencia.delete(0, "end")
        self.entry_eficiencia.insert(0, str(int(round(float(receta['efficiency']) * 100))))
        self.texto_notas.delete("1.0", "end"); self.texto_notas.insert(1.0, receta.get('notes', ''))
        # Estilo BJCP guardado
        estilo_saved = receta.get('style') or "Auto (Sugerir)"
        self.combo_estilo_bjcp.set(estilo_saved if estilo_saved in get_style_list() else "Auto (Sugerir)")
        # Altitud / levadura / maceración / hervor (paridad móvil)
        alt_nombre = receta.get('altitud_name') or DEF_ALTITUD
        if alt_nombre in ALTITUDES_CORDOBA:
            self.combo_altitud.set(alt_nombre)
        self.entry_so4.delete(0, "end"); self.entry_so4.insert(0, format_num(receta.get('agua_so4', 0) or 0))
        self.entry_cl.delete(0, "end");  self.entry_cl.insert(0, format_num(receta.get('agua_cl', 0) or 0))
        obj_g = receta.get('agua_objetivo') or "Balanceada (genérica)"
        if obj_g in BrewEngine.PERFILES_AGUA_OBJETIVO:
            self.combo_agua_obj.set(obj_g)
        eq_nombre = receta.get('equipo') or ''
        if eq_nombre and eq_nombre in self._nombres_equipos():
            self.combo_equipo.set(eq_nombre)
        self.entry_ratio.delete(0, "end")
        self.entry_ratio.insert(0, format_num(receta.get('ratio_maceracion', 3.0)))
        self.entry_absorcion.delete(0, "end")
        self.entry_absorcion.insert(0, format_num(receta.get('absorcion', 1.0)))
        self.entry_hervor.delete(0, "end")
        self.entry_hervor.insert(0, format_num(receta.get('tiempo_hervor', 60)))
        # Levadura guardada
        levadura_saved = None
        if receta.get('levaduras'):
            levadura_saved = receta['levaduras'][0].get('name')
        if levadura_saved and levadura_saved in LEVADURAS_AR:
            self.combo_levadura.set(levadura_saved)
        # Perfil de agua guardado (Ca/Mg/HCO3/pH)
        ca_s, mg_s, hc_s = (receta.get('agua_ca'), receta.get('agua_mg'), receta.get('agua_hco3'))
        perfil_match = None
        if None not in (ca_s, mg_s, hc_s):
            perfil_match = next((k for k, v in PERFILES_AGUA_CORDOBA.items()
                                 if abs(v.get('ca', 0) - ca_s) < 0.01
                                 and abs(v.get('mg', 0) - mg_s) < 0.01
                                 and abs(v.get('hco3', 0) - hc_s) < 0.01), None)
            if perfil_match:
                self.combo_agua.set(perfil_match)
        self.entry_ca.delete(0, "end");   self.entry_ca.insert(0, format_num(ca_s if ca_s is not None else 50))
        self.entry_mg.delete(0, "end");   self.entry_mg.insert(0, format_num(mg_s if mg_s is not None else 10))
        self.entry_hco3.delete(0, "end"); self.entry_hco3.insert(0, format_num(hc_s if hc_s is not None else 150))
        ph_entrada = receta.get('agua_ph_entrada')
        if ph_entrada is not None:
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(ph_entrada))
        elif perfil_match:
            ph = PERFILES_AGUA_CORDOBA[perfil_match].get('ph', 7.0)
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(ph))
        else:
            self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, "7.0")
        # Ingredientes (maltas con color, lúpulos con formato)
        for w in self.frame_lista_maltas.winfo_children(): w.destroy()
        for w in self.frame_lista_lupulos.winfo_children(): w.destroy()
        for m in receta['maltas']:
            self.add_fila_malta({'nombre': m['name'], 'cantidad': float(m['amount']),
                                 'extracto': float(m.get('extract', 300)),
                                 'color': float(m.get('color', 2))})
        for l in receta['lupulos']:
            self.add_fila_lupulo({'nombre': l['name'], 'cantidad': float(l['amount']),
                                  'aa': float(l['alpha_acids']),
                                  'tiempo': float(l['time']),
                                  'formato': l.get('formato', DEF_FORMATO)})
        self.tabview.set("🛠️ Receta")
        self.calcular_y_mostrar()

    def nueva_receta(self):
        self.receta_actual_id = None
        self.entry_nombre.delete(0, "end")
        self.combo_volumen.set("20")
        self.volumen_base_receta = 20.0
        self.entry_eficiencia.delete(0, "end"); self.entry_eficiencia.insert(0, "75")
        self.combo_altitud.set(DEF_ALTITUD)
        self.combo_levadura.set(DEF_LEVADURA if DEF_LEVADURA in LEVADURAS_AR else sorted(LEVADURAS_AR.keys())[0])
        self.combo_estilo_bjcp.set("Auto (Sugerir)")
        self.entry_ratio.delete(0, "end");     self.entry_ratio.insert(0, "3.0")
        self.entry_absorcion.delete(0, "end"); self.entry_absorcion.insert(0, "1.0")
        self.entry_hervor.delete(0, "end");    self.entry_hervor.insert(0, "60")
        self.combo_agua.set(DEF_PERFIL_AGUA)
        self.entry_so4.delete(0, "end"); self.entry_so4.insert(0, "0")
        self.entry_cl.delete(0, "end");  self.entry_cl.insert(0, "0")
        self.combo_agua_obj.set("Balanceada (genérica)")
        self._on_perfil_agua(None)
        self.texto_notas.delete("1.0", "end")
        self._reset_panel_resultados()
        for w in self.frame_lista_maltas.winfo_children(): w.destroy()
        for w in self.frame_lista_lupulos.winfo_children(): w.destroy()

    def guardar_receta(self):
        nombre = self.entry_nombre.get().strip()
        if not nombre:
            mb.showwarning("Atención", "Escribe un nombre."); return
        maltas, lupulos = self.leer_ingredientes_ui()
        if not maltas and not lupulos:
            mb.showwarning("Atención", "Receta vacía."); return
        resultados = self.calcular_y_mostrar()
        if not resultados: return
        volumen, eficiencia, ratio, absorcion, tiempo_hervor, altitud = self._leer_parametros()
        levadura_nombre, levadura_datos = self._leer_levadura()
        agua_datos = self._leer_agua_ui()
        notas = self.texto_notas.get("1.0", "end-1c").strip()
        r = resultados['r']
        receta_data = {
            'name': nombre, 'style': self.combo_estilo_bjcp.get(),
            'volume': volumen, 'efficiency': eficiencia,
            'og_estimated': r['og'], 'fg_estimated': r['fg'],
            'ibu_estimated': r['ibu'], 'srm_estimated': r['srm'],
            'notes': notas,
            'maltas': maltas, 'lupulos': lupulos,
            'levaduras': [{'nombre': levadura_nombre,
                           'atenuacion': levadura_datos['atenuacion'],
                           'tolerancia': levadura_datos['tolerancia_abv']}],
            'agua_ca': agua_datos['ca'], 'agua_mg': agua_datos['mg'],
            'agua_hco3': agua_datos['hco3'], 'agua_ph_entrada': agua_datos['ph'],
            'agua_so4': agua_datos.get('so4', 0), 'agua_cl': agua_datos.get('cl', 0),
            'agua_objetivo': self.combo_agua_obj.get() or '',
            'equipo': self.combo_equipo.get() or '',
            'tiempo_hervor': tiempo_hervor,
            'ratio_maceracion': ratio, 'absorcion': absorcion,
            'altitud_name': self.combo_altitud.get() or DEF_ALTITUD,
        }
        if self.receta_actual_id:
            if self.db.update_recipe(self.receta_actual_id, receta_data):
                mb.showinfo("Éxito", "Receta actualizada correctamente.")
                self.cargar_lista_recetas()
                self._compartir_si_corresponde(self.receta_actual_id)
            else:
                mb.showerror("Error", f"No se pudo actualizar. ¿Existe otra receta con el nombre '{nombre}'?")
        else:
            nuevo_id = self.db.save_recipe(receta_data)
            if nuevo_id:
                mb.showinfo("Éxito", "Receta guardada.")
                self.cargar_lista_recetas()
                self._compartir_si_corresponde(nuevo_id)
                self.nueva_receta()
            else:
                mb.showerror("Error", "Nombre duplicado. Prueba con otro nombre.")

    def _compartir_si_corresponde(self, recipe_id):
        if getattr(self, "var_compartir_comunidad", None) and self.var_compartir_comunidad.get():
            threading.Thread(target=self.compartir_receta_comunidad, args=(recipe_id,), daemon=True).start()

    def eliminar_receta(self):
        if not self.receta_actual_id:
            mb.showwarning("Atención", "Selecciona una receta de la lista para eliminar."); return
        nombre = self.entry_nombre.get().strip()
        if mb.askyesno("Confirmar Eliminación", f"¿Seguro que quieres eliminar la receta '{nombre}'?"):
            self.db.delete_recipe(self.receta_actual_id)
            mb.showinfo("Eliminada", "La receta ha sido eliminada.")
            self.nueva_receta(); self.cargar_lista_recetas()

    # ==========================================
    # IMPORTACIÓN / EXPORTACIÓN
    # ==========================================
    def cargar_recetas_iniciales(self):
        if len(self.db.get_all_recipes_summary()) > 0: return
        json_path = resource_path('recetas_base.json')
        if not os.path.exists(json_path): return
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                recetas_json = json.load(f)
            for nombre, datos in recetas_json.items():
                self._guardar_desde_json(nombre, datos)
        except Exception as e:
            print(f"Error cargando JSON inicial: {e}")

    def importar_json_ui(self):
        filepath = filedialog.askopenfilename(title="Seleccionar JSON", filetypes=[("JSON", "*.json")])
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                recetas_json = json.load(f)
            importadas, omitidas = 0, 0
            for nombre, datos in recetas_json.items():
                if self._guardar_desde_json(nombre, datos):
                    importadas += 1
                else:
                    omitidas += 1
            self.cargar_lista_recetas()
            mb.showinfo("Éxito", f"Importadas: {importadas}\nOmitidas (duplicadas): {omitidas}")
        except Exception as e:
            mb.showerror("Error", f"No se pudo leer el JSON:\n{e}")

    def _descargar_y_fusionar(self):
        """Descarga el recetario más reciente y lo fusiona. Devuelve (agregadas, omitidas)."""
        with urllib.request.urlopen(RECETARIO_URL, timeout=20) as r:
            recetas_json = json.load(r)
        refrescables = self._recetas_refrescables(recetas_json)
        agregadas, actualizadas, omitidas = 0, 0, 0
        for nombre, datos in recetas_json.items():
            h = _huella(datos)
            if self.db.recipe_exists(nombre):
                # Solo se reescribe si el contenido del recetario cambió desde la última vez
                if (nombre in refrescables and refrescables[nombre] != h
                        and self._guardar_desde_json(nombre, datos, refrescar=True)):
                    actualizadas += 1
                    refrescables[nombre] = h
                else:
                    omitidas += 1
            elif self._guardar_desde_json(nombre, datos):
                agregadas += 1
                refrescables[nombre] = h
        self._guardar_refrescables(refrescables)
        return agregadas, omitidas, actualizadas

    def actualizar_recetas_web(self):
        """Botón manual: busca y fusiona el recetario, mostrando el resultado."""
        try:
            agregadas, omitidas, actualizadas = self._descargar_y_fusionar()
            self.cargar_lista_recetas()
            mb.showinfo("Recetas actualizadas",
                        f"Nuevas recetas agregadas: {agregadas}\n"
                        f"Recetas corregidas (genéricas -> reales): {actualizadas}\n"
                        f"Sin cambios: {omitidas}\n\n"
                        "Listo, sin reinstalar nada.")
        except Exception as e:
            logger.error(f"actualizar_recetas_web: {e}")
            mb.showerror("Error",
                         "No se pudo descargar el recetario.\n\n"
                         "Revisá tu conexión y probá de nuevo.\n"
                         f"Detalle: {e}")

    def _auto_actualizar(self):
        """Al abrir la app: en segundo plano descarga y fusiona el recetario (silencioso)."""
        def tarea():
            try:
                agregadas, omitidas, actualizadas = self._descargar_y_fusionar()
                if agregadas or actualizadas:
                    self.after(0, self._refrescar_tras_auto, agregadas, actualizadas)
            except Exception as e:
                logger.error(f"_auto_actualizar: {e}")
        threading.Thread(target=tarea, daemon=True).start()

    def _refrescar_tras_auto(self, agregadas, actualizadas=0):
        self.cargar_lista_recetas()
        logger.info(f"Recetas auto-actualizadas al iniciar: {agregadas} nuevas, "
                    f"{actualizadas} corregidas.")
        try:
            self.title("Cervecera VGB - By SaintWick (recetas actualizadas)")
        except Exception:
            pass

    # ==========================================
    # COMUNIDAD — compartir/descargar recetas vía GitHub (sin backend propio)
    # ==========================================
    def _leer_token_comunidad(self):
        for var in COMUNIDAD_TOKEN_ENV:
            tok = os.environ.get(var, "").strip()
            if tok:
                return tok
        try:
            with open(COMUNIDAD_TOKEN_FILE, "r", encoding="utf-8") as f:
                tok = f.read().strip()
                if tok:
                    return tok
        except OSError:
            pass
        return None

    def _receta_a_json_recetario(self, recipe_id):
        """Convierte una receta guardada al formato del recetario (mismo formato
        que recetas_base.json / RECETARIO_URL) para compartirla."""
        r = self.db.get_full_recipe(recipe_id)
        if not r:
            return None, None
        datos = {
            "style": r.get("style", ""),
            "agua_vol": r.get("volume"),
            "fg_estimada": r.get("fg_estimated"),
            "notas": r.get("notes", ""),
            "maltas": [{"nombre": m["name"], "cantidad": m["amount"],
                        "extracto": m["extract"], "color": m["color"]} for m in r.get("maltas", [])],
            "lupulos": [{"nombre": l["name"], "cantidad": l["amount"], "aa": l["alpha_acids"],
                         "tiempo": l["time"], "formato": l.get("formato", DEF_FORMATO)}
                        for l in r.get("lupulos", [])],
            "levaduras": [{"nombre": y["name"], "atenuacion": y["attenuation"],
                           "tolerancia": y["tolerance_abv"]} for y in r.get("levaduras", [])],
        }
        return r["name"], datos

    def _slug_archivo(self, nombre):
        s = re.sub(r"[^a-zA-Z0-9]+", "-", nombre.strip().lower()).strip("-")
        return (s or "receta") + ".json"

    def compartir_receta_comunidad(self, recipe_id):
        """Sube (o actualiza) la receta como JSON en recetas_comunidad/ del repo,
        vía la API de contenidos de GitHub (sin clonar el repo). Cualquier usuario
        de la app la baja después con '🌐 Recetas de la Comunidad'. Se ejecuta en
        un hilo aparte (la llama guardar_receta), por eso los avisos van con
        self.after(0, ...) para tocar la UI desde el hilo principal."""
        token = self._leer_token_comunidad()
        if not token:
            self.after(0, lambda: mb.showwarning(
                "Compartir con la comunidad",
                "No hay credenciales de GitHub configuradas para compartir.\n\n"
                "Configuralo una sola vez con alguna de estas opciones:\n"
                f"  · echo TU_TOKEN > {COMUNIDAD_TOKEN_FILE}\n"
                "  · variable de entorno GITHUB_TOKEN\n\n"
                "La receta se guardó localmente igual; sólo no se compartió."))
            return
        nombre, datos = self._receta_a_json_recetario(recipe_id)
        if not nombre:
            return
        archivo = self._slug_archivo(nombre)
        url = COMUNIDAD_ARCHIVO_URL.format(archivo=archivo)
        contenido_b64 = base64.b64encode(
            json.dumps({nombre: datos}, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii")
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json",
                  "User-Agent": "CerveceraVGB"}
        sha = None
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                sha = json.load(r).get("sha")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                logger.error(f"compartir_receta_comunidad (GET): {e}")
        except Exception as e:
            logger.error(f"compartir_receta_comunidad (GET): {e}")
        payload = {"message": f"Comunidad: comparte receta '{nombre}'", "content": contenido_b64}
        if sha:
            payload["sha"] = sha
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                         headers=headers, method="PUT")
            with urllib.request.urlopen(req, timeout=30) as r:
                json.load(r)
            self.db.mark_recipe_compartida(recipe_id)
            self.after(0, lambda: mb.showinfo("Comunidad", f"'{nombre}' se compartió con la comunidad. 🌐"))
        except Exception as e:
            msg = str(e)
            logger.error(f"compartir_receta_comunidad (PUT): {msg}")
            self.after(0, lambda msg=msg: mb.showerror("Comunidad", f"No se pudo compartir la receta.\n{msg}"))

    def descargar_recetas_comunidad(self):
        """Lista y descarga las recetas compartidas por la comunidad (lectura
        pública, sin token) y las fusiona sin pisar las locales."""
        try:
            req = urllib.request.Request(COMUNIDAD_LISTADO_URL, headers={"User-Agent": "CerveceraVGB"})
            with urllib.request.urlopen(req, timeout=20) as r:
                listado = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0, 0  # todavía nadie compartió nada
            raise
        agregadas, omitidas = 0, 0
        for archivo in listado:
            if not archivo.get("name", "").endswith(".json"):
                continue
            try:
                with urllib.request.urlopen(archivo["download_url"], timeout=20) as r:
                    receta_json = json.load(r)
                for nombre, datos in receta_json.items():
                    if self._guardar_desde_json(nombre, datos):
                        agregadas += 1
                    else:
                        omitidas += 1
            except Exception as e:
                logger.error(f"descargar_recetas_comunidad ({archivo.get('name')}): {e}")
        return agregadas, omitidas

    def buscar_recetas_comunidad_ui(self):
        try:
            agregadas, omitidas = self.descargar_recetas_comunidad()
            self.cargar_lista_recetas()
            mb.showinfo("Recetas de la Comunidad",
                        f"Nuevas recetas compartidas: {agregadas}\nYa las tenías: {omitidas}")
        except Exception as e:
            logger.error(f"buscar_recetas_comunidad_ui: {e}")
            mb.showerror("Error", f"No se pudo consultar la comunidad.\n{e}")

    def comprobar_actualizaciones(self):
        """Busca una versión más nueva del PROGRAMA. En Windows la instala en silencio."""
        try:
            req = urllib.request.Request(RELEASE_API_URL,
                                         headers={'User-Agent': 'CerveceraVGB'})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            tag = data.get('tag_name', '')
            version = tag.lstrip('v')
            if version == APP_VERSION:
                mb.showinfo("Actualización", f"Tenés la versión {APP_VERSION}. ¡Estás al día! ✅")
                return
            # elegir el instalador de esta plataforma
            url = None
            for a in data.get('assets', []):
                n = a['name']
                if sys.platform == 'win32' and n.lower().endswith('.exe'):
                    url = a['browser_download_url']; break
                elif sys.platform == 'darwin' and 'macos-arm64' in n:
                    url = a['browser_download_url']; break
                elif sys.platform.startswith('linux') and n.endswith('.AppImage'):
                    url = a['browser_download_url']; break
            if not url:
                mb.showinfo("Actualización", f"Hay una versión nueva: {version}.\nDescargala del release.")
                return
            destino = os.path.join(tempfile.gettempdir(), os.path.basename(url))
            logger.info(f"Descargando actualización {version} -> {destino}")
            with urllib.request.urlopen(url, timeout=180) as r, open(destino, 'wb') as f:
                f.write(r.read())
            if sys.platform == 'win32':
                logger.info("Lanzando instalador en silencio (auto-update).")
                subprocess.Popen([destino, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
                mb.showinfo("Actualización",
                            "Se descargó la versión nueva y se está instalando.\nLa app se cerrará; volvé a abrirla al terminar.")
                self.after(1500, lambda: os._exit(0))
            else:
                if sys.platform == 'darwin':
                    subprocess.Popen(['open', destino])
                else:
                    subprocess.Popen(['xdg-open', destino])
                mb.showinfo("Actualización",
                            f"Se descargó la versión {version}.\n\n{os.path.basename(destino)}\n"
                            "Se abrió para que la instales (en Linux/macOS instalar requiere permisos de administrador).")
        except Exception as e:
            logger.error(f"comprobar_actualizaciones: {e}")
            mb.showerror("Error", f"No se pudo comprobar actualizaciones.\n{e}")

    def _guardar_desde_json(self, nombre, datos, refrescar=False):
        """Adapta una receta del JSON (formato móvil) y la guarda.
        Si ya existe la actualiza SOLO si viene del recetario oficial (refrescar=True);
        así se corrigen las recetas genéricas viejas sin tocar las del usuario."""
        existe = self.db.recipe_exists(nombre)
        if existe and not refrescar:
            return None
        # Levadura: la de la receta importada si la trae; si no, la de por defecto
        levs = datos.get('levaduras') or []
        if levs:
            levadura_nombre = levs[0].get('nombre') or DEF_LEVADURA
            levadura_datos = {"atenuacion": float(levs[0].get('atenuacion') or 81.0),
                              "tolerancia_abv": float(levs[0].get('tolerancia') or 12.0)}
        else:
            levadura_nombre = DEF_LEVADURA
            levadura_datos = LEVADURAS_AR.get(levadura_nombre, {"atenuacion": 81.0, "tolerancia_abv": 12.0})
        receta = {
            'name': nombre, 'style': datos.get('style', 'Estilo Base'),
            'volume': datos.get('agua_vol', 20), 'efficiency': 0.75,
            'og_estimated': None, 'fg_estimated': datos.get('fg_estimada', 1.010),
            'ibu_estimated': None, 'srm_estimated': None,
            'notes': datos.get('notas', ''),
            'maltas': [{'nombre': m['nombre'], 'cantidad': m['cantidad'],
                        'extracto': m.get('extracto', 300), 'color': m.get('color', 2)}
                       for m in datos.get('maltas', [])],
            'lupulos': [{'nombre': l['nombre'], 'cantidad': l['cantidad'],
                         'aa': l.get('aa', 5), 'tiempo': l.get('tiempo', 60),
                         'formato': l.get('formato', DEF_FORMATO)}
                        for l in datos.get('lupulos', [])],
            'levaduras': [{'nombre': levadura_nombre,
                           'atenuacion': levadura_datos['atenuacion'],
                           'tolerancia': levadura_datos['tolerancia_abv']}],
        }
        if existe:
            rid = self._id_receta(nombre)
            return self.db.update_recipe(rid, receta) if rid else None
        return self.db.save_recipe(receta)

    def _id_receta(self, nombre):
        """Id de una receta guardada, buscándola por nombre."""
        try:
            for r in self.db.get_all_recipes_summary():
                if r['name'] == nombre:
                    return r['id']
        except Exception as e:
            logger.error(f"_id_receta({nombre}): {e}")
        return None

    def _recetas_refrescables(self, recetas_json):
        """Nombres que la app puede refrescar desde el recetario.
        La primera vez son los que ya existen y figuran en el recetario: esas son
        justamente las recetas genéricas viejas que hay que corregir."""
        guardado = self.db.get_setting('recetas_refrescables', None)
        if guardado is not None:
            try:
                datos = json.loads(guardado)
                if isinstance(datos, list):        # formato anterior (solo nombres)
                    return {n: None for n in datos}
                return dict(datos)
            except Exception:
                return {}
        try:
            existentes = {r['name'] for r in self.db.get_all_recipes_summary()}
        except Exception:
            existentes = set()
        # Primera vez: los que ya existen y figuran en el recetario son los genéricos viejos
        return {n: None for n in recetas_json if n in existentes}

    def _guardar_refrescables(self, nombres):
        try:
            self.db.set_setting('recetas_refrescables', json.dumps(nombres, ensure_ascii=False))
        except Exception as e:
            logger.error(f"_guardar_refrescables: {e}")

    def _recolectar_datos_exportacion(self):
        resultados = self.calcular_y_mostrar()
        if not resultados: return None
        maltas, lupulos = self.leer_ingredientes_ui()
        volumen, eficiencia, _, _, _, _ = self._leer_parametros()
        r = resultados['r']
        return {
            'name': self.entry_nombre.get().strip() or "Sin Nombre",
            'style': self.combo_estilo_bjcp.get(),
            'volume': volumen,
            'efficiency': eficiencia,
            'og': r['og'], 'fg': r['fg'], 'abv': r['abv'],
            'ibu': r['ibu'], 'srm': r['srm'],
            'ph': r['ph'], 'ph_hervor': r['ph_hervor'], 'ph_final': r['ph_final'],
            'maltas': maltas, 'lupulos': lupulos,
            'notes': self.texto_notas.get("1.0", "end-1c").strip(),
        }

    def exportar_pdf_ui(self):
        data = self._recolectar_datos_exportacion()
        if not data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                filetypes=[("PDF", "*.pdf")],
                                                title="Guardar PDF", initialfile=data['name'])
        if not filepath: return
        if exportar_pdf(data, filepath):
            mb.showinfo("Éxito", f"PDF guardado en:\n{filepath}")
        else:
            mb.showerror("Error", "No se pudo generar el PDF.")

    def exportar_xml_ui(self):
        data = self._recolectar_datos_exportacion()
        if not data: return
        filepath = filedialog.asksaveasfilename(defaultextension=".xml",
                                                filetypes=[("BeerXML", "*.xml")],
                                                title="Guardar BeerXML", initialfile=data['name'])
        if not filepath: return
        if exportar_beerxml(data, filepath):
            mb.showinfo("Éxito", f"BeerXML guardado en:\n{filepath}")
        else:
            mb.showerror("Error", "No se pudo generar el BeerXML.")

    def abrir_menu_acciones(self):
        """Despliega/oculta un dropdown propio bajo el botón Menú (se cierra al elegir
        una opción o al perder el foco; no queda pegado como el tk.Menu nativo)."""
        if self._menu_popup is not None and self._menu_popup.winfo_exists():
            self._cerrar_menu_acciones()
            return
        x = self.btn_menu.winfo_rootx()
        y = self.btn_menu.winfo_rooty() + self.btn_menu.winfo_height() + 2
        popup = ctk.CTkToplevel(self)
        popup.overrideredirect(True)
        popup.geometry(f"+{x}+{y}")
        popup.attributes("-topmost", True)
        frame = ctk.CTkFrame(popup, fg_color="#2c2c2c", corner_radius=6, border_width=1,
                             border_color="#475569")
        frame.pack(fill="both", expand=True)
        opciones = (
            ("📂 Importar JSON", self.importar_json_ui),
            ("🔄 Buscar recetas nuevas", self.actualizar_recetas_web),
            ("🌐 Recetas de la Comunidad", self.buscar_recetas_comunidad_ui),
            ("⬆️ Comprobar actualizaciones", self.comprobar_actualizaciones),
            ("💾 Exportar PDF", self.exportar_pdf_ui),
            ("💾 Exportar BeerXML", self.exportar_xml_ui),
        )
        for texto, accion in opciones:
            ctk.CTkButton(frame, text=texto, anchor="w", fg_color="transparent",
                         hover_color="#374151", height=30,
                         command=lambda a=accion: self._ejecutar_accion_menu(a)
                         ).pack(fill="x", padx=4, pady=2)
        popup.bind("<FocusOut>", lambda e: self._cerrar_menu_acciones())
        self._menu_popup = popup
        popup.after(10, popup.focus_force)

    def _ejecutar_accion_menu(self, accion):
        self._cerrar_menu_acciones()
        accion()

    def _cerrar_menu_acciones(self):
        if self._menu_popup is not None:
            try:
                self._menu_popup.destroy()
            except Exception:
                pass
            self._menu_popup = None

    def toggle_lista_recetas(self):
        """Muestra u oculta la lista de recetas al presionar 'Mis Recetas'."""
        if self._recetas_visibles:
            self.lista_recetas.grid_remove()
            self.btn_toggle_recetas.configure(text="🍺 Mis Recetas  ▸")
        else:
            self.lista_recetas.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
            self.btn_toggle_recetas.configure(text="🍺 Mis Recetas  ▾")
        self._recetas_visibles = not self._recetas_visibles

    def mostrar_ayuda(self):
        AyudaDialog(self)

    def mostrar_log(self):
        """Muestra la ruta del registro y lo abre en el visor por defecto."""
        logp = os.path.join(get_data_dir(), "cervecera_debug.log")
        existe = os.path.exists(logp)
        try:
            if existe:
                if sys.platform == "win32":
                    os.startfile(logp)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", logp])
                else:
                    subprocess.Popen(["xdg-open", logp])
        except Exception as e:
            print(f"No se pudo abrir el log: {e}")
        if existe:
            mb.showinfo("Registro (log)", f"El registro de la app está en:\n\n{logp}\n\nSe abrió en el visor por defecto.")
        else:
            mb.showinfo("Registro (log)", "Todavía no hay registro de errores.\n\nSi la app falla, aparecerá acá.")
