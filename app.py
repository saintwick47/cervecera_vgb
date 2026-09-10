# app.py
# Autor: SaintWick

"""
Interfaz gráfica principal de Cervecera VGB (versión PC / escritorio).
v15 — PARIDAD FUNCIONAL con beer_vgb_mobile (Android):
  · Mismo motor (brew_engine.py móvil): FG por atenuación de levadura,
    IBU con altitud/formato/whirlpool, ácido láctico, pH post-hervor y final,
    aguas con evaporación, calorías, etc.
  · Mismo catálogo argentino (catalogo_ar.py): maltas, lúpulos, levaduras,
    altitudes y perfiles de agua con pH.
  · Misma persistencia: levadura, formato de lúpulo, color de malta, altitud,
    ratio L/kg, absorción, tiempo de hervor y perfil de agua (Ca/Mg/HCO3/pH).
  · Adaptado a customtkinter (la diferencia es solo el medio de uso).
"""

import customtkinter as ctk
from database import DatabaseManager
from brew_engine import BrewEngine
from bjcp_styles import comparar_con_estilo, get_style_list
from export_engine import exportar_pdf, exportar_beerxml
from catalogo_ar import (MALTAS_AR, LUPULOS_AR, LEVADURAS_AR,
                         ALTITUDES_CORDOBA, PERFILES_AGUA_CORDOBA)
import tkinter.messagebox as mb
from tkinter import filedialog
import tkinter as tk  # Añadido para el manejo de iconos en Linux
import json
import os
import sys
import subprocess
import threading
import tempfile
import urllib.request
from logger import logger
from app_paths import get_data_dir

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

VOLUMENES_PRESET = ["5", "10", "20", "50", "100", "250", "500", "750", "1000", "1200", "1500", "2000", "3000", "5000", "10000"]
TIPOS_INVENTARIO = ["Malta", "Lúpulo", "Levadura", "Otro"]

# Valores por defecto (paridad con beer_vgb_mobile)
DEF_PERFIL_AGUA   = "Córdoba Capital (Agua de Red)"
DEF_LEVADURA      = "Fermentis US-05 (Ale Americana)"
DEF_ALTITUD       = "Córdoba Capital"
DEF_FORMATO       = "pellet"
EVAPORACION_PCT   = 10.0  # evaporación por hora de hervor (%)
APP_VERSION       = "1.3.0"  # versión instalada (para comprobar actualizaciones)
RECETARIO_URL     = ("https://github.com/saintwick47/cervecera_vgb/"
                     "releases/latest/download/recetas_cervecera_vgb.json")
RELEASE_API_URL   = "https://api.github.com/repos/saintwick47/cervecera_vgb/releases/latest"


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
🍺 MANUAL DE USUARIO - CERVECERA VGB (v15 - paridad con móvil)

📝 1. RECETA:
- Nombre, volumen, eficiencia, ALTITUD (afecta IBU) y LEVADURA
  (define FG por atenuación y tolerancia de ABV).
- Maceración: ratio L/kg, absorción L/kg y tiempo de hervor (min)
  → calcula agua de maceración, lavado y evaporación.
- 💧 Perfil del Agua: elegí un perfil de Córdoba o cargá Ca/Mg/HCO3/pH.
  El pH del agua de entrada participa en el pH estimado de maceración.
- Maltas y Lúpulos desde el catálogo argentino (autocompletan Ext/Color y
  AA%/formato). Podés escalonar lúpulos (varias líneas).
- Resultados: OG, FG (auto por levadura), ABV, atenuación, IBU, SRM,
  BU/GU, calorías, aguas, pH (entrada/maceración/post-hervor/final),
  ácido láctico recomendado para fijar pH 5.3 y alerta de levadura.

📊 2. COMPARADOR BJCP: estilo objetivo con rangos oficiales (OG, FG, IBU, SRM).

📦 3. INVENTARIO: carga tu stock real; al calcular, valida disponibilidad.

💾 4. EXPORTACIÓN: PDF profesional y BeerXML (Brewfather/Grainfather…).

📖 5. AGREGAR RECETAS (sin reinstalar):
- Al abrir la app, se busca solo el recetario más reciente en la web y se
  fusiona automáticamente (sin que hagas nada).
- También podés usar "🔄 Buscar recetas nuevas" (manual) o "📂 Importar JSON"
  con un archivo descargado. Las recetas nuevas quedan guardadas.

⬆️ 6. ACTUALIZAR LA APP:
- Botón "⬆️ Comprobar actualizaciones": si hay una versión nueva, la descarga.
  En Windows se instala sola (en silencio); en Linux/macOS la descarga y la abre.

🧾 7. REGISTRO DE ERRORES:
- Si algo falla, usá el botón "🧾 Ver log" (arriba) para ver la ruta del archivo
  de registro. Windows: %LOCALAPPDATA%\\Cervecera VGB\\cervecera_debug.log

📧 8. CONTACTO: nicoweb45@proton.me (Asunto: beer_vgb)
"""
        self.texto_ayuda.insert("1.0", mensaje)
        self.texto_ayuda.configure(state="disabled")

        # Forzar el foco para que la ventana se abra siempre en primer plano en Windows
        self.after(200, lambda: self.focus_force())


class CerveceraApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cervecera VGB - By SaintWick")
        self.geometry("1220x860")
        self.minsize(1050, 640)

        # 📌 ASIGNAR ICONO A LA VENTANA (Multiplataforma)
        try:
            icon_path_ico = resource_path("logo.ico")
            icon_path_png = resource_path("logo.png")

            if sys.platform == "win32" and os.path.exists(icon_path_ico):
                # Windows usa .ico
                self.iconbitmap(icon_path_ico)
            elif os.path.exists(icon_path_png):
                # Linux/Mac usa .png mediante iconphoto
                self._icon_img = tk.PhotoImage(file=icon_path_png)
                self.iconphoto(True, self._icon_img)
        except Exception as e:
            print(f"No se pudo cargar el icono de la ventana: {e}")

        self.db = DatabaseManager()
        self.receta_actual_id = None
        # Fase 2: cargar el catálogo de insumos en la BD la primera vez (luego es editable)
        try:
            self.db.seed_ingredients(MALTAS_AR, LUPULOS_AR, LEVADURAS_AR)
            self.db.seed_equipment()
        except Exception as e:
            logger.warning(f"No se pudo sembrar el catálogo de insumos: {e}")

        self.volumen_base_receta = 20.0

        self.cargar_recetas_iniciales()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- BARRA SUPERIOR ---
        frame_top = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#2c2c2c")
        frame_top.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkButton(frame_top, text="📂 Importar JSON", command=self.importar_json_ui, fg_color="#2563EB", hover_color="#1D4ED8", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="🔄 Buscar recetas nuevas", command=self.actualizar_recetas_web, fg_color="#0D9488", hover_color="#0F766E", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="⬆️ Comprobar actualizaciones", command=self.comprobar_actualizaciones, fg_color="#7C3AED", hover_color="#6D28D9", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="💾 Exportar PDF", command=self.exportar_pdf_ui, fg_color="#D97706", hover_color="#B45309", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="💾 Exportar BeerXML", command=self.exportar_xml_ui, fg_color="#7C3AED", hover_color="#6D28D9", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="❓ Manual de Usuario", command=self.mostrar_ayuda, fg_color="#6B7280", hover_color="#4B5563", height=32).pack(side="right", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="🧾 Ver log", command=self.mostrar_log, fg_color="#475569", hover_color="#334155", height=32).pack(side="right", padx=10, pady=5)

        # --- COLUMNA IZQUIERDA (Recetas) ---
        self.frame_izquierdo = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.frame_izquierdo.grid(row=1, column=0, sticky="nsew")
        self.frame_izquierdo.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.frame_izquierdo, text="🍺 Mis Recetas", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        self.lista_recetas = ctk.CTkScrollableFrame(self.frame_izquierdo)
        self.lista_recetas.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(self.frame_izquierdo, text="+ Crear Receta Manual", command=self.nueva_receta).grid(row=2, column=0, padx=20, pady=20)

        # --- COLUMNA DERECHA (Tabs: Receta / Inventario) ---
        self.tabview = ctk.CTkTabview(self, corner_radius=0)
        self.tabview.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

        self.tab_receta = self.tabview.add("🛠️ Receta")
        self.tab_inventario = self.tabview.add("📦 Inventario")
        self.tab_insumos = self.tabview.add("🧪 Insumos")
        self.tab_equipos = self.tabview.add("⚙️ Equipos")

        self.setup_tab_receta()
        self.setup_tab_inventario()
        self.setup_tab_insumos()
        self.setup_tab_equipos()

        self.cargar_lista_recetas()
        self.nueva_receta()
        # Auto-actualización silenciosa de recetas al abrir la app
        threading.Thread(target=self._auto_actualizar, daemon=True).start()

    # ==========================================
    # CONFIGURACIÓN PESTAÑA RECETA (CON SCROLL)
    # ==========================================
    def setup_tab_receta(self):
        self.scroll_receta = ctk.CTkScrollableFrame(self.tab_receta)
        self.scroll_receta.pack(fill="both", expand=True)
        self.scroll_receta.grid_columnconfigure(0, weight=1)

        # ── 1. Datos Básicos ─────────────────────────────────────────────
        frame_datos = ctk.CTkFrame(self.scroll_receta)
        frame_datos.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        frame_datos.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(frame_datos, text="Nombre:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_nombre = ctk.CTkEntry(frame_datos, placeholder_text="Ej: Mi IPA Argenta")
        self.entry_nombre.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(frame_datos, text="Volumen (L):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.combo_volumen = ctk.CTkComboBox(frame_datos, values=VOLUMENES_PRESET, command=self.escalar_por_volumen)
        self.combo_volumen.set("20")
        self.combo_volumen.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(frame_datos, text="Eficiencia (%):").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_eficiencia = ctk.CTkEntry(frame_datos, placeholder_text="75")
        self.entry_eficiencia.grid(row=1, column=3, padx=5, pady=5)
        self.entry_eficiencia.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        # Altitud (afecta IBU por punto de ebullición) — paridad móvil
        ctk.CTkLabel(frame_datos, text="Altitud:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.combo_altitud = ctk.CTkComboBox(frame_datos, values=list(ALTITUDES_CORDOBA.keys()),
                                             command=lambda e: self.calcular_y_mostrar(), width=180)
        self.combo_altitud.set(DEF_ALTITUD)
        self.combo_altitud.grid(row=2, column=1, padx=5, pady=5)

        # Levadura (define FG por atenuación + tolerancia ABV) — paridad móvil
        ctk.CTkLabel(frame_datos, text="Levadura:").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        _levs = self._opciones_insumo("Levadura")
        self.combo_levadura = ctk.CTkComboBox(frame_datos, values=_levs,
                                              command=lambda e: self.calcular_y_mostrar(), width=230)
        self.combo_levadura.set(DEF_LEVADURA if DEF_LEVADURA in _levs else (_levs[0] if _levs else ""))
        self.combo_levadura.grid(row=2, column=3, padx=5, pady=5)

        # Estilo BJCP
        ctk.CTkLabel(frame_datos, text="Estilo Objetivo:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.combo_estilo_bjcp = ctk.CTkComboBox(frame_datos, values=get_style_list(), command=lambda e: self.calcular_y_mostrar())
        self.combo_estilo_bjcp.set("Auto (Sugerir)")
        self.combo_estilo_bjcp.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # ── 2. Maceración y Hervor ───────────────────────────────────────
        frame_mac = ctk.CTkFrame(self.scroll_receta)
        frame_mac.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        frame_mac.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        ctk.CTkLabel(frame_mac, text="🪣 Maceración y Hervor", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=6, sticky="w", padx=5, pady=5)

        ctk.CTkLabel(frame_mac, text="Ratio (L/Kg):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.entry_ratio = ctk.CTkEntry(frame_mac, placeholder_text="3.0", width=70)
        self.entry_ratio.grid(row=1, column=1, padx=2, pady=2)
        self.entry_ratio.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        ctk.CTkLabel(frame_mac, text="Absorción (L/Kg):").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.entry_absorcion = ctk.CTkEntry(frame_mac, placeholder_text="1.0", width=70)
        self.entry_absorcion.grid(row=1, column=3, padx=2, pady=2)
        self.entry_absorcion.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        ctk.CTkLabel(frame_mac, text="Hervor (min):").grid(row=1, column=4, padx=5, pady=2, sticky="w")
        self.entry_hervor = ctk.CTkEntry(frame_mac, placeholder_text="60", width=70)
        self.entry_hervor.grid(row=1, column=5, padx=2, pady=2)
        self.entry_hervor.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        # Fase 4: equipo + fórmulas (Fase 0)
        ctk.CTkLabel(frame_mac, text="Equipo:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.combo_equipo = ctk.CTkComboBox(frame_mac, values=self._nombres_equipos(),
                                            command=self._on_equipo_change, width=210)
        _eqs = self._nombres_equipos()
        self.combo_equipo.set(_eqs[0] if _eqs else "")
        self.combo_equipo.grid(row=2, column=1, columnspan=2, padx=2, pady=2, sticky="ew")

        ctk.CTkLabel(frame_mac, text="Fórmula IBU:").grid(row=2, column=3, padx=5, pady=2, sticky="w")
        self.combo_f_ibu = ctk.CTkComboBox(frame_mac, values=["Tinseth", "Rager"], width=110,
                                           command=self._on_formula_change)
        self.combo_f_ibu.set("Rager" if self.db.get_setting("formula_ibu", "tinseth") == "rager" else "Tinseth")
        self.combo_f_ibu.grid(row=2, column=4, padx=2, pady=2, sticky="w")

        ctk.CTkLabel(frame_mac, text="FG:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.combo_f_fg = ctk.CTkComboBox(frame_mac, values=["Normal", "Simple"], width=110,
                                          command=self._on_formula_change)
        self.combo_f_fg.set("Simple" if self.db.get_setting("metodo_fg", "normal") == "simple" else "Normal")
        self.combo_f_fg.grid(row=3, column=1, padx=2, pady=2, sticky="w")

        ctk.CTkLabel(frame_mac, text="ABV:").grid(row=3, column=3, padx=5, pady=2, sticky="w")
        self.combo_f_abv = ctk.CTkComboBox(frame_mac, values=["Standard", "Alternative"], width=130,
                                           command=self._on_formula_change)
        self.combo_f_abv.set("Alternative" if self.db.get_setting("formula_abv", "standard") == "alternative" else "Standard")
        self.combo_f_abv.grid(row=3, column=4, padx=2, pady=2, sticky="w")

        # ── 3. Perfil del Agua ───────────────────────────────────────────
        frame_agua = ctk.CTkFrame(self.scroll_receta)
        frame_agua.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        frame_agua.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        ctk.CTkLabel(frame_agua, text="💧 Perfil del Agua (ppm)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)

        self.combo_agua = ctk.CTkComboBox(frame_agua, values=list(PERFILES_AGUA_CORDOBA.keys()),
                                          command=self._on_perfil_agua, width=260)
        self.combo_agua.set(DEF_PERFIL_AGUA)
        self.combo_agua.grid(row=0, column=4, columnspan=4, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(frame_agua, text="Calcio (Ca):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.entry_ca = ctk.CTkEntry(frame_agua, placeholder_text="50", width=60)
        self.entry_ca.grid(row=1, column=1, padx=2, pady=2)
        self.entry_ca.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        ctk.CTkLabel(frame_agua, text="Magnesio (Mg):").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.entry_mg = ctk.CTkEntry(frame_agua, placeholder_text="10", width=60)
        self.entry_mg.grid(row=1, column=3, padx=2, pady=2)
        self.entry_mg.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        ctk.CTkLabel(frame_agua, text="Bicarbonato (HCO3):").grid(row=1, column=4, padx=5, pady=2, sticky="w")
        self.entry_hco3 = ctk.CTkEntry(frame_agua, placeholder_text="150", width=60)
        self.entry_hco3.grid(row=1, column=5, padx=2, pady=2)
        self.entry_hco3.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        ctk.CTkLabel(frame_agua, text="pH Agua:").grid(row=1, column=6, padx=5, pady=2, sticky="w")
        self.entry_ph_agua = ctk.CTkEntry(frame_agua, placeholder_text="7.0", width=55)
        self.entry_ph_agua.grid(row=1, column=7, padx=2, pady=2)
        self.entry_ph_agua.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        # ── 4. Maltas ────────────────────────────────────────────────────
        frame_maltas = ctk.CTkFrame(self.scroll_receta)
        frame_maltas.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        header_maltas = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        header_maltas.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_maltas, text="🌾 Maltas y Adjuntos (Kg)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_maltas, text="+ Añadir Malta", width=100, command=lambda: self.add_fila_malta()).pack(side="right")
        # Encabezados de columna (para saber qué es cada valor)
        enc_m = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        enc_m.pack(fill="x", padx=5)
        for etiqueta, ancho in [("Malta", 210), ("Kg", 60), ("Ext", 55), ("Color", 55), ("", 30)]:
            ctk.CTkLabel(enc_m, text=etiqueta, width=ancho, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="#9CA3AF").pack(side="left", padx=2)
        self.frame_lista_maltas = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        self.frame_lista_maltas.pack(fill="x")

        # ── 5. Lúpulos ───────────────────────────────────────────────────
        frame_lupulos = ctk.CTkFrame(self.scroll_receta)
        frame_lupulos.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        header_lupulos = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        header_lupulos.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_lupulos, text="🌿 Lúpulos (Mezclas y Escalonados)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_lupulos, text="+ Añadir Lúpulo", width=100, command=lambda: self.add_fila_lupulo()).pack(side="right")
        # Encabezados de columna
        enc_l = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        enc_l.pack(fill="x", padx=5)
        for etiqueta, ancho in [("Lúpulo", 185), ("g", 55), ("AA%", 50), ("Min", 50), ("Formato", 75), ("", 30)]:
            ctk.CTkLabel(enc_l, text=etiqueta, width=ancho, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="#9CA3AF").pack(side="left", padx=2)
        self.frame_lista_lupulos = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        self.frame_lista_lupulos.pack(fill="x")

        # ── 6. Notas ─────────────────────────────────────────────────────
        frame_notas = ctk.CTkFrame(self.scroll_receta)
        frame_notas.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(frame_notas, text="📝 Notas del Cocinero", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)
        self.texto_notas = ctk.CTkTextbox(frame_notas, height=50, font=ctk.CTkFont(size=12))
        self.texto_notas.pack(fill="x", padx=5, pady=(0, 5))

        # ── 7. Acciones ──────────────────────────────────────────────────
        frame_acciones = ctk.CTkFrame(self.scroll_receta, fg_color="transparent")
        frame_acciones.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(frame_acciones, text="🔢 Calcular", command=self.calcular_y_mostrar, fg_color="#D97706", hover_color="#B45309").pack(side="left", padx=10)
        ctk.CTkButton(frame_acciones, text="💾 Guardar / Modificar", command=self.guardar_receta, fg_color="#059669", hover_color="#047857").pack(side="left", padx=10)
        ctk.CTkButton(frame_acciones, text="🗑️ Eliminar Receta", command=self.eliminar_receta, fg_color="#DC2626", hover_color="#991B1B").pack(side="left", padx=10)

        # ── 8. Resultados ────────────────────────────────────────────────
        frame_resultados = ctk.CTkFrame(self.scroll_receta)
        frame_resultados.grid(row=7, column=0, padx=20, pady=10, sticky="nsew")
        self.texto_resultados = ctk.CTkTextbox(frame_resultados, height=320, font=ctk.CTkFont(size=13))
        self.texto_resultados.pack(fill="both", expand=True, padx=10, pady=10)

    # ── Perfil de agua: al elegir perfil, completar campos ──────────────
    def _on_perfil_agua(self, _=None):
        perfil = PERFILES_AGUA_CORDOBA.get(self.combo_agua.get(), {})
        self.entry_ca.delete(0, "end");    self.entry_ca.insert(0, format_num(perfil.get("ca", 50)))
        self.entry_mg.delete(0, "end");    self.entry_mg.insert(0, format_num(perfil.get("mg", 10)))
        self.entry_hco3.delete(0, "end");  self.entry_hco3.insert(0, format_num(perfil.get("hco3", 150)))
        self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(perfil.get("ph", 7.0)))
        self.calcular_y_mostrar()

    # ==========================================
    # CONFIGURACIÓN PESTAÑA INVENTARIO
    # ==========================================
    def setup_tab_inventario(self):
        self.tab_inventario.grid_columnconfigure(0, weight=1)

        frame_add = ctk.CTkFrame(self.tab_inventario)
        frame_add.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        ctk.CTkLabel(frame_add, text="➕ Añadir / Sumar Stock", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, pady=10, padx=10, sticky="w")

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

        ctk.CTkButton(frame_add, text="Añadir al Inventario", command=self.agregar_inventario_ui, fg_color="#059669", hover_color="#047857").grid(row=3, column=0, columnspan=4, pady=15)

        frame_lista_inv = ctk.CTkFrame(self.tab_inventario)
        frame_lista_inv.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        ctk.CTkLabel(frame_lista_inv, text="📦 Stock Disponible", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.lista_inventario_ui = ctk.CTkScrollableFrame(frame_lista_inv)
        self.lista_inventario_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.cargar_lista_inventario()


    # ==========================================
    # PERFILES DE EQUIPO (pestaña, Fase 4)
    # ==========================================
    def _nombres_equipos(self):
        try:
            return [e["name"] for e in self.db.get_equipment()]
        except Exception:
            return []

    def _on_equipo_change(self, _=None):
        """Al elegir equipo: aplicar volumen, eficiencia y temperatura de macerado."""
        eq = self.db.get_equipment_by_name(self.combo_equipo.get())
        if eq:
            self.combo_volumen.set(format_num(eq.get("batch_volume") or 20))
            self.volumen_base_receta = float(eq.get("batch_volume") or 20)
            self.entry_eficiencia.delete(0, "end")
            self.entry_eficiencia.insert(0, format_num(round((eq.get("eficiencia") or 0.75) * 100, 1)))
        self.calcular_y_mostrar()

    def _on_formula_change(self, _=None):
        """Guarda las fórmulas elegidas (preferencia global, como Brewfather)."""
        try:
            self.db.set_setting("formula_ibu", "rager" if self.combo_f_ibu.get() == "Rager" else "tinseth")
            self.db.set_setting("metodo_fg", "simple" if self.combo_f_fg.get() == "Simple" else "normal")
            self.db.set_setting("formula_abv", "alternative" if self.combo_f_abv.get() == "Alternative" else "standard")
        except Exception as e:
            logger.warning(f"No se pudo guardar la preferencia de fórmula: {e}")
        self.calcular_y_mostrar()

    def setup_tab_equipos(self):
        self.tab_equipos.grid_columnconfigure(0, weight=1)
        c = ctk.CTkFrame(self.tab_equipos)
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
        ctk.CTkButton(c, text="💾 Guardar / Actualizar", command=self._eq_guardar,
                      fg_color="#059669", hover_color="#047857"
                      ).grid(row=fila, column=0, columnspan=2, padx=6, pady=10, sticky="w")
        ctk.CTkButton(c, text="🧹 Limpiar", command=lambda: [e.delete(0, "end") for e in self._eq_entries.values()],
                      fg_color="#6B7280", hover_color="#4B5563").grid(row=fila, column=2, padx=6, pady=10, sticky="w")

        fl = ctk.CTkFrame(self.tab_equipos)
        fl.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.lista_equipos_ui = ctk.CTkScrollableFrame(fl)
        self.lista_equipos_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.cargar_lista_equipos()

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
        self.cargar_lista_equipos()
        self.combo_equipo.configure(values=self._nombres_equipos())
        mb.showinfo("Equipos", f"Equipo guardado:\n{nombre}")

    # ==========================================
    # CATÁLOGO DE INSUMOS (pestaña, Fase 2)
    # ==========================================
    def setup_tab_insumos(self):
        self.tab_insumos.grid_columnconfigure(0, weight=1)
        card_ing = ctk.CTkFrame(self.tab_insumos)
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

        frame_lista = ctk.CTkFrame(self.tab_insumos)
        frame_lista.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        ctk.CTkLabel(frame_lista, text="Insumos cargados", font=ctk.CTkFont(size=15, weight="bold")).pack(pady=8)
        self.lista_insumos_ui = ctk.CTkScrollableFrame(frame_lista)
        self.lista_insumos_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.cargar_lista_insumos()

    def cargar_lista_insumos(self):
        for w in self.lista_insumos_ui.winfo_children():
            w.destroy()
        for ing in self.db.get_ingredients():
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

        self.db.add_inventory_item(tipo, nombre, cantidad, unidad)
        mb.showinfo("Éxito", f"Stock de {nombre} actualizado.")
        self.entry_nombre_inv.delete(0, "end"); self.entry_cantidad_inv.delete(0, "end")
        self.cargar_lista_inventario()
        self.calcular_y_mostrar()

    def eliminar_item_inventario(self, item_id):
        self.db.delete_inventory_item(item_id)
        self.cargar_lista_inventario()
        self.calcular_y_mostrar()

    def cargar_lista_inventario(self):
        for w in self.lista_inventario_ui.winfo_children():
            w.destroy()
        items = self.db.get_all_inventory()
        for item in items:
            fila = ctk.CTkFrame(self.lista_inventario_ui, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            texto = f"[{item['type']}] {item['name']} - {item['amount']} {item['unit']}"
            ctk.CTkLabel(fila, text=texto, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(fila, text="🗑️", width=30, fg_color="#DC2626", hover_color="#991B1B",
                          command=lambda iid=item['id']: self.eliminar_item_inventario(iid)).pack(side="right", padx=5)

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
    # FILAS DE INGREDIENTES (catálogo + campos)
    # ==========================================
    def _set_combo_valor(self, combo, valor, lista_catalogo):
        """Configura un combo manteniendo valores heredados que no están en el catálogo."""
        try:
            combo.set(valor)
        except Exception:
            pass
        if valor and valor not in combo.cget("values"):
            try:
                combo.configure(values=[valor] + list(combo.cget("values")))
                combo.set(valor)
            except Exception:
                pass

    # ── Catálogo de insumos desde la BD (Fase 2) ────────────────────────────
    def _opciones_insumo(self, tipo):
        """Nombres de insumos: los de la BD (editables) + los del catálogo base."""
        nombres = set()
        try:
            nombres |= set(self.db.ingredient_names(tipo))
        except Exception:
            pass
        base = {"Malta": MALTAS_AR, "Lúpulo": LUPULOS_AR, "Levadura": LEVADURAS_AR}.get(tipo, {})
        nombres |= set(base.keys())
        return sorted(nombres)

    def _datos_insumo(self, tipo, nombre):
        """Devuelve los datos del insumo (primero la BD editable, luego el catálogo)."""
        try:
            ing = self.db.get_ingredient(tipo, nombre)
        except Exception:
            ing = None
        if ing:
            if tipo == "Malta":
                return {"extracto": ing.get("extract") or 300, "color": ing.get("color") or 2}
            if tipo == "Lúpulo":
                return {"aa": ing.get("alpha") or 5, "formato": ing.get("form") or DEF_FORMATO}
            if tipo == "Levadura":
                return {"atenuacion": ing.get("attenuation") or 75.0,
                        "tolerancia_abv": ing.get("abv_tolerance") or 12.0}
        base = {"Malta": MALTAS_AR, "Lúpulo": LUPULOS_AR, "Levadura": LEVADURAS_AR}.get(tipo, {})
        d = base.get(nombre)
        if not d:
            return None
        if tipo == "Malta":
            return {"extracto": d.get("extracto", 300), "color": d.get("color", 2)}
        if tipo == "Lúpulo":
            return {"aa": d.get("aa", 5), "formato": d.get("formato", DEF_FORMATO)}
        return {"atenuacion": d.get("atenuacion", 75.0), "tolerancia_abv": d.get("tolerancia_abv", 12.0)}

    def add_fila_malta(self, datos=None):
        fila = ctk.CTkFrame(self.frame_lista_maltas, fg_color="transparent")
        fila.pack(fill="x", pady=2)

        lista_maltas = self._opciones_insumo("Malta")
        nombre = datos.get('nombre', '') if datos else ''
        combo_valores = ([nombre] + lista_maltas) if (nombre and nombre not in lista_maltas) else lista_maltas
        c_nombre = ctk.CTkComboBox(fila, values=combo_valores, width=210)
        if nombre: c_nombre.set(nombre)
        c_nombre.pack(side="left", padx=2)
        c_nombre.bind("<<ComboboxSelected>>", self._on_malta_seleccion(fila))

        e_cant = ctk.CTkEntry(fila, placeholder_text="Kg", width=60)
        e_cant.pack(side="left", padx=2)
        e_cant.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        e_ext = ctk.CTkEntry(fila, placeholder_text="Ext", width=55)
        e_ext.pack(side="left", padx=2)
        e_ext.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        e_color = ctk.CTkEntry(fila, placeholder_text="Col", width=55)
        e_color.pack(side="left", padx=2)
        e_color.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        btn_del = ctk.CTkButton(fila, text="X", width=30, fg_color="#DC2626", hover_color="#991B1B",
                                command=lambda: self._borrar_fila(fila))
        btn_del.pack(side="left", padx=5)

        fila.c_nombre, fila.e_cantidad, fila.e_extracto, fila.e_color = c_nombre, e_cant, e_ext, e_color

        if datos:
            e_cant.insert(0, format_num(datos.get('cantidad', '')))
            e_ext.insert(0, format_num(datos.get('extracto', 300)))
            e_color.insert(0, format_num(datos.get('color', 2)))
        else:
            e_ext.insert(0, "300"); e_color.insert(0, "2")
        return fila

    def _on_malta_seleccion(self, fila):
        def cb(_=None):
            nombre = fila.c_nombre.get()
            d = self._datos_insumo("Malta", nombre)
            if d:
                fila.e_extracto.delete(0, "end"); fila.e_extracto.insert(0, format_num(d["extracto"]))
                fila.e_color.delete(0, "end");    fila.e_color.insert(0, format_num(d["color"]))
            self.calcular_y_mostrar()
        return cb

    def add_fila_lupulo(self, datos=None):
        fila = ctk.CTkFrame(self.frame_lista_lupulos, fg_color="transparent")
        fila.pack(fill="x", pady=2)

        lista_lupulos = self._opciones_insumo("Lúpulo")
        nombre = datos.get('nombre', '') if datos else ''
        combo_valores = ([nombre] + lista_lupulos) if (nombre and nombre not in lista_lupulos) else lista_lupulos
        c_nombre = ctk.CTkComboBox(fila, values=combo_valores, width=185)
        if nombre: c_nombre.set(nombre)
        c_nombre.pack(side="left", padx=2)
        c_nombre.bind("<<ComboboxSelected>>", self._on_lupulo_seleccion(fila))

        e_cant = ctk.CTkEntry(fila, placeholder_text="g", width=55)
        e_cant.pack(side="left", padx=2)
        e_cant.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        e_aa = ctk.CTkEntry(fila, placeholder_text="AA%", width=50)
        e_aa.pack(side="left", padx=2)
        e_aa.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        e_tiempo = ctk.CTkEntry(fila, placeholder_text="Min", width=50)
        e_tiempo.pack(side="left", padx=2)
        e_tiempo.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())

        c_formato = ctk.CTkComboBox(fila, values=["pellet", "flor"], width=75)
        formato = datos.get('formato', DEF_FORMATO) if datos else DEF_FORMATO
        c_formato.set(formato if formato in ("pellet", "flor") else DEF_FORMATO)
        c_formato.pack(side="left", padx=2)
        c_formato.bind("<<ComboboxSelected>>", lambda e: self.calcular_y_mostrar())

        btn_del = ctk.CTkButton(fila, text="X", width=30, fg_color="#DC2626", hover_color="#991B1B",
                                command=lambda: self._borrar_fila(fila))
        btn_del.pack(side="left", padx=5)

        fila.c_nombre, fila.e_cantidad, fila.e_aa, fila.e_tiempo, fila.c_formato = c_nombre, e_cant, e_aa, e_tiempo, c_formato

        if datos:
            e_cant.insert(0, format_num(datos.get('cantidad', '')))
            e_aa.insert(0, format_num(datos.get('aa', 5)))
            e_tiempo.insert(0, format_num(datos.get('tiempo', 60)))
        else:
            e_aa.insert(0, "5"); e_tiempo.insert(0, "60")
        return fila

    def _on_lupulo_seleccion(self, fila):
        def cb(_=None):
            nombre = fila.c_nombre.get()
            d = self._datos_insumo("Lúpulo", nombre)
            if d:
                fila.e_aa.delete(0, "end"); fila.e_aa.insert(0, format_num(d["aa"]))
                fila.c_formato.set(d.get("formato") or DEF_FORMATO)
            self.calcular_y_mostrar()
        return cb

    def _borrar_fila(self, fila):
        fila.destroy()
        self.calcular_y_mostrar()

    def _filas_de(self, parent_frame):
        return [w for w in parent_frame.winfo_children()
                if isinstance(w, ctk.CTkFrame) and hasattr(w, "c_nombre")]

    def leer_ingredientes_ui(self):
        maltas, lupulos = [], []
        for fila in self._filas_de(self.frame_lista_maltas):
            try:
                maltas.append({
                    'nombre': fila.c_nombre.get() or "Malta",
                    'cantidad': _flotar(fila.e_cantidad.get(), 0),
                    'extracto': int(_flotar(fila.e_extracto.get(), 300)),
                    'color': _flotar(fila.e_color.get(), 2),
                })
            except Exception:
                pass
        for fila in self._filas_de(self.frame_lista_lupulos):
            try:
                lupulos.append({
                    'nombre': fila.c_nombre.get() or "Lúpulo",
                    'cantidad': _flotar(fila.e_cantidad.get(), 0),
                    'aa': _flotar(fila.e_aa.get(), 5),
                    'tiempo': int(_flotar(fila.e_tiempo.get(), 60)),
                    'formato': fila.c_formato.get() or DEF_FORMATO,
                })
            except Exception:
                pass
        return maltas, lupulos

    # ==========================================
    # LÓGICA DE ESCALADO Y RECETAS
    # ==========================================
    def escalar_por_volumen(self, nuevo_volumen_str):
        """Escala proporcional las cantidades al cambiar el volumen (como el móvil)."""
        try:
            nuevo_volumen = float(nuevo_volumen_str)
            if nuevo_volumen <= 0 or self.volumen_base_receta <= 0: return
            factor = nuevo_volumen / self.volumen_base_receta
            for fila in self._filas_de(self.frame_lista_maltas):
                actual = _flotar(fila.e_cantidad.get(), 0)
                fila.e_cantidad.delete(0, "end")
                fila.e_cantidad.insert(0, format_num(round(actual * factor, 2)))
            for fila in self._filas_de(self.frame_lista_lupulos):
                actual = _flotar(fila.e_cantidad.get(), 0)
                fila.e_cantidad.delete(0, "end")
                fila.e_cantidad.insert(0, format_num(round(actual * factor, 2)))
            self.volumen_base_receta = nuevo_volumen
        except ValueError:
            return
        self.calcular_y_mostrar()

    def _leer_levadura(self):
        nombre = self.combo_levadura.get()
        levadura_datos = self._datos_insumo("Levadura", nombre) or {"atenuacion": 75.0, "tolerancia_abv": 12.0}
        return nombre, levadura_datos

    def _leer_agua_ui(self):
        return {
            "ca": _flotar(self.entry_ca.get(), 50),
            "mg": _flotar(self.entry_mg.get(), 10),
            "hco3": _flotar(self.entry_hco3.get(), 150),
            "ph": _flotar(self.entry_ph_agua.get(), 7.0),
        }


    def _leer_parametros(self):
        volumen = _flotar(self.combo_volumen.get(), 20) or 20
        eficiencia = (_flotar(self.entry_eficiencia.get(), 75) or 75) / 100
        ratio = _flotar(self.entry_ratio.get(), 3.0) or 3.0
        absorcion = _flotar(self.entry_absorcion.get(), 1.0) or 1.0
        tiempo_hervor = _flotar(self.entry_hervor.get(), 60) or 60
        altitud = ALTITUDES_CORDOBA.get(self.combo_altitud.get(), 400)
        return volumen, eficiencia, ratio, absorcion, tiempo_hervor, altitud

    # ==========================================
    # LÓGICA DE RECETAS Y CÁLCULOS
    # ==========================================
    def calcular_y_mostrar(self):
        try:
            volumen, eficiencia, ratio, absorcion, tiempo_hervor, altitud = self._leer_parametros()
            maltas, lupulos = self.leer_ingredientes_ui()
            levadura_nombre, levadura_datos = self._leer_levadura()
            agua_datos = self._leer_agua_ui()

            if not maltas and not lupulos:
                self.texto_resultados.delete("1.0", "end")
                self.texto_resultados.insert(
                    "1.0", "\n\n   👉 Añade maltas y lúpulos o selecciona una receta de la izquierda.")
                return None

            eq = self.db.get_equipment_by_name(self.combo_equipo.get()) or {}
            datos_calculo = {
                'maltas': maltas, 'lupulos': lupulos, 'agua_vol': volumen,
                'agua': agua_datos, 'tiempo_hervor': tiempo_hervor,
                'ratio_maceracion': ratio, 'absorcion': absorcion,
                'evaporacion_pct': EVAPORACION_PCT,
                'atenuacion_levadura': levadura_datos['atenuacion'],
                'tolerancia_abv': levadura_datos['tolerancia_abv'],
                # Fase 0: fórmulas seleccionables
                'metodo_fg': "simple" if self.combo_f_fg.get() == "Simple" else "normal",
                'temp_macerado': eq.get("temp_macerado", 66.0),
                'formula_ibu': "rager" if self.combo_f_ibu.get() == "Rager" else "tinseth",
                'formula_abv': "alternative" if self.combo_f_abv.get() == "Alternative" else "standard",
                # Fase 4: equipo
                'perdidas_l': eq.get("perdidas_l", 0.0),
                'evaporacion_l_h': eq.get("evaporacion_l_h"),
            }
            r = BrewEngine.calcular_receta_completa(datos_calculo, eficiencia, altitud)

            granos_kg = sum(m.get('cantidad', 0) for m in maltas)
            aguas = BrewEngine.calcular_aguas(granos_kg, volumen, ratio, absorcion,
                                              EVAPORACION_PCT, tiempo_hervor,
                                              eq.get("perdidas_l", 0.0), eq.get("evaporacion_l_h"))

            alerta_alcohol = ("🚨 ¡ALERTA! Saturación de levadura (ABV > Tolerancia)"
                              if r.get('alerta_abv') else "✅ Levadura apta para este ABV")

            color_desc = BrewEngine.obtener_descripcion_color(r['srm'])
            amargor_desc = BrewEngine.obtener_descripcion_amargor(r['ibu'])
            estilo_sugerido = BrewEngine.sugerir_estilo(r['og'], r['ibu'], r['srm'])
            ph_desc = BrewEngine.obtener_descripcion_ph(r['ph'])

            estado_inventario = self.validar_inventario_receta(maltas, lupulos)
            estilo_elegido = self.combo_estilo_bjcp.get()
            if estilo_elegido and estilo_elegido != "Auto (Sugerir)":
                analisis_bjcp = comparar_con_estilo(estilo_elegido, r['og'], r['fg'], r['ibu'], r['srm'])
            else:
                analisis_bjcp = (f"ℹ️ Estilo sugerido por parámetros: {estilo_sugerido}\n"
                                 "(Selecciona un estilo específico arriba para ver la comparación BJCP)")

            self.texto_resultados.delete("1.0", "end")
            texto = f"""
🧪 PARÁMETROS CALCULADOS (Para {volumen} L | Altitud: {altitud}m)
━━━━━━━━━━━━━━━━━━━━━━━━━━
OG : {r['og']:.3f}   FG : {r['fg']:.3f}   (Auto. Levadura: {levadura_nombre})   [1.000 = agua destilada]
ABV: {r['abv']}% (alt. {r.get('abv_alt', r['abv'])}%)   Atenuación: {r['atenuacion']}%
IBU: {r['ibu']} ({amargor_desc})   SRM: {r['srm']} ({color_desc})   EBC: {r.get('ebc', 0)}
BU/GU: {r.get('bugu', 0)}   Calorías: {r['calorias']} kcal/355ml

💧 AGUA (evap. {EVAPORACION_PCT}%/h, hervor {tiempo_hervor} min)
━━━━━━━━━━━━━━━━━━━━━━━━━━
Maceración : {aguas['agua_maceracion']} L  (ratio {ratio} L/kg)
Lavado     : {aguas['agua_lavado']} L
Pre-hervor : {aguas['volumen_pre_hervor']} L  (evapora {aguas['evaporacion_L']} L)

🧪 QUÍMICA (pH)
━━━━━━━━━━━━━━━━━━━━━━━━━━
pH Entrada (agua): {agua_datos.get('ph', 7.0)}
Maceración       : {r['ph']:.2f} {ph_desc}
Post-hervor      : {r['ph_hervor']:.2f}
Final (lúpulo)   : {r['ph_final']:.2f}
Para fijar pH en 5.3 añadir: {r['acido_lactico_ml']} ml de Ácido Láctico (88%)

⚠️ {alerta_alcohol}

🏅 ANÁLISIS BJCP ({estilo_elegido})
━━━━━━━━━━━━━━━━━━━━━━━━━━
{analisis_bjcp}

📦 DISPONIBILIDAD EN INVENTARIO
━━━━━━━━━━━━━━━━━━━━━━━━━━
{estado_inventario if estado_inventario else "No hay ingredientes en la receta para validar."}
"""
            self.texto_resultados.insert("1.0", texto)
            return {
                'og': r['og'], 'fg': r['fg'], 'abv': r['abv'], 'ibu': r['ibu'],
                'srm': r['srm'], 'ph': r['ph'], 'ph_hervor': r['ph_hervor'],
                'ph_final': r['ph_final'], 'aguas': aguas, 'r': r,
            }
        except Exception as e:
            mb.showerror("Error", f"Revisa los datos:\n{str(e)}")
            return None

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
        self.texto_notas.delete("1.0", "end"); self.texto_notas.insert("1.0", receta.get('notes', ''))

        # Estilo BJCP guardado
        estilo_saved = receta.get('style') or "Auto (Sugerir)"
        self.combo_estilo_bjcp.set(estilo_saved if estilo_saved in get_style_list() else "Auto (Sugerir)")

        # Altitud / levadura / maceración / hervor (paridad móvil)
        alt_nombre = receta.get('altitud_name') or DEF_ALTITUD
        if alt_nombre in ALTITUDES_CORDOBA:
            self.combo_altitud.set(alt_nombre)
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
        self._on_perfil_agua(None)
        self.texto_notas.delete("1.0", "end")
        self.texto_resultados.delete("1.0", "end")
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
            'tiempo_hervor': tiempo_hervor,
            'ratio_maceracion': ratio, 'absorcion': absorcion,
            'altitud_name': self.combo_altitud.get() or DEF_ALTITUD,
        }

        if self.receta_actual_id:
            if self.db.update_recipe(self.receta_actual_id, receta_data):
                mb.showinfo("Éxito", "Receta actualizada correctamente.")
                self.cargar_lista_recetas()
            else:
                mb.showerror("Error", f"No se pudo actualizar. ¿Existe otra receta con el nombre '{nombre}'?")
        else:
            nuevo_id = self.db.save_recipe(receta_data)
            if nuevo_id:
                mb.showinfo("Éxito", "Receta guardada.")
                self.cargar_lista_recetas()
                self.nueva_receta()
            else:
                mb.showerror("Error", "Nombre duplicado. Prueba con otro nombre.")

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
        agregadas, omitidas = 0, 0
        for nombre, datos in recetas_json.items():
            if self._guardar_desde_json(nombre, datos):
                agregadas += 1
            else:
                omitidas += 1
        return agregadas, omitidas

    def actualizar_recetas_web(self):
        """Botón manual: busca y fusiona el recetario, mostrando el resultado."""
        try:
            agregadas, omitidas = self._descargar_y_fusionar()
            self.cargar_lista_recetas()
            mb.showinfo("Recetas actualizadas",
                        f"Nuevas recetas agregadas: {agregadas}\n"
                        f"Ya existían (se omitieron): {omitidas}\n\n"
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
                agregadas, omitidas = self._descargar_y_fusionar()
                if agregadas:
                    self.after(0, self._refrescar_tras_auto, agregadas)
            except Exception as e:
                logger.error(f"_auto_actualizar: {e}")
        threading.Thread(target=tarea, daemon=True).start()

    def _refrescar_tras_auto(self, agregadas):
        self.cargar_lista_recetas()
        logger.info(f"Recetas auto-actualizadas al iniciar: {agregadas} nuevas.")
        try:
            self.title("Cervecera VGB - By SaintWick (recetas actualizadas)")
        except Exception:
            pass

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

    def _guardar_desde_json(self, nombre, datos):
        """Adapta una receta del JSON (formato móvil) y la guarda.
        Si ya existe, no la intenta guardar (evita el 'IntegrityError' en el log)."""
        if self.db.recipe_exists(nombre):
            return None
        levadura_nombre = DEF_LEVADURA
        levadura_datos = LEVADURAS_AR.get(levadura_nombre, {"atenuacion": 81.0, "tolerancia_abv": 12.0})
        receta = {
            'name': nombre, 'style': datos.get('style', 'Estilo Base'),
            'volume': datos.get('agua_vol', 20), 'efficiency': 0.75,
            'og_estimated': None, 'fg_estimated': datos.get('fg_estimada', 1.010),
            'ibu_estimated': None, 'srm_estimated': None,
            'notes': '',
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
        return self.db.save_recipe(receta)

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


if __name__ == "__main__":
    try:
        app = CerveceraApp()
        app.mainloop()
    except Exception as e:
        try:
            logger.exception("Error fatal al iniciar Cervecera VGB")
        except Exception:
            pass
        try:
            import traceback as _tb
            _tb.print_exc()
            mb.showerror("Cervecera VGB",
                         "Ocurrió un error al iniciar la app.\n\n"
                         "Revisá el registro:\n"
                         + os.path.join(get_data_dir(), "cervecera_debug.log"))
        except Exception:
            pass
        raise
