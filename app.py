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
- Descargá el archivo "recetario" (JSON) desde la sección Recetas de la web
  https://saintwick47.github.io
- En la app: botón "📂 Importar JSON" → elegí el archivo descargado.
- O usá el botón "🔄 Buscar recetas nuevas": descarga el recetario más reciente
  del release y lo fusiona automáticamente (sin reinstalar ni perder nada).
- Las recetas nuevas se agregan a tu recetario y quedan guardadas.

🧾 6. REGISTRO DE ERRORES:
- Si algo falla, usá el botón "🧾 Ver log" (arriba) para ver la ruta del archivo
  de registro. Windows: %LOCALAPPDATA%\\Cervecera VGB\\cervecera_debug.log

📧 7. CONTACTO: nicoweb45@proton.me (Asunto: beer_vgb)
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

        self.volumen_base_receta = 20.0

        self.cargar_recetas_iniciales()

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- BARRA SUPERIOR ---
        frame_top = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color="#2c2c2c")
        frame_top.grid(row=0, column=0, columnspan=2, sticky="ew")
        ctk.CTkButton(frame_top, text="📂 Importar JSON", command=self.importar_json_ui, fg_color="#2563EB", hover_color="#1D4ED8", height=32).pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="🔄 Buscar recetas nuevas", command=self.actualizar_recetas_web, fg_color="#0D9488", hover_color="#0F766E", height=32).pack(side="left", padx=10, pady=5)
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

        self.setup_tab_receta()
        self.setup_tab_inventario()

        self.cargar_lista_recetas()
        self.nueva_receta()

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
        self.combo_levadura = ctk.CTkComboBox(frame_datos, values=sorted(LEVADURAS_AR.keys()),
                                              command=lambda e: self.calcular_y_mostrar(), width=230)
        self.combo_levadura.set(DEF_LEVADURA if DEF_LEVADURA in LEVADURAS_AR else sorted(LEVADURAS_AR.keys())[0])
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
        self.frame_lista_maltas = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        self.frame_lista_maltas.pack(fill="x")

        # ── 5. Lúpulos ───────────────────────────────────────────────────
        frame_lupulos = ctk.CTkFrame(self.scroll_receta)
        frame_lupulos.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        header_lupulos = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        header_lupulos.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_lupulos, text="🌿 Lúpulos (Mezclas y Escalonados)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_lupulos, text="+ Añadir Lúpulo", width=100, command=lambda: self.add_fila_lupulo()).pack(side="right")
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

    def add_fila_malta(self, datos=None):
        fila = ctk.CTkFrame(self.frame_lista_maltas, fg_color="transparent")
        fila.pack(fill="x", pady=2)

        lista_maltas = sorted(MALTAS_AR.keys())
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
            if nombre in MALTAS_AR:
                fila.e_extracto.delete(0, "end"); fila.e_extracto.insert(0, str(MALTAS_AR[nombre]["extracto"]))
                fila.e_color.delete(0, "end");    fila.e_color.insert(0, str(MALTAS_AR[nombre]["color"]))
            self.calcular_y_mostrar()
        return cb

    def add_fila_lupulo(self, datos=None):
        fila = ctk.CTkFrame(self.frame_lista_lupulos, fg_color="transparent")
        fila.pack(fill="x", pady=2)

        lista_lupulos = sorted(LUPULOS_AR.keys())
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
            if nombre in LUPULOS_AR:
                fila.e_aa.delete(0, "end"); fila.e_aa.insert(0, str(LUPULOS_AR[nombre]["aa"]))
                fila.c_formato.set(LUPULOS_AR[nombre].get("formato", DEF_FORMATO))
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
        levadura_datos = LEVADURAS_AR.get(self.combo_levadura.get(),
                                          {"atenuacion": 75.0, "tolerancia_abv": 12.0})
        return self.combo_levadura.get(), levadura_datos

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

            datos_calculo = {
                'maltas': maltas, 'lupulos': lupulos, 'agua_vol': volumen,
                'agua': agua_datos, 'tiempo_hervor': tiempo_hervor,
                'ratio_maceracion': ratio, 'absorcion': absorcion,
                'evaporacion_pct': EVAPORACION_PCT,
                'atenuacion_levadura': levadura_datos['atenuacion'],
                'tolerancia_abv': levadura_datos['tolerancia_abv'],
            }
            r = BrewEngine.calcular_receta_completa(datos_calculo, eficiencia, altitud)

            granos_kg = sum(m.get('cantidad', 0) for m in maltas)
            aguas = BrewEngine.calcular_aguas(granos_kg, volumen, ratio, absorcion,
                                              EVAPORACION_PCT, tiempo_hervor)

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
OG : {r['og']:.4f}   FG : {r['fg']:.4f}   (Auto. Levadura: {levadura_nombre})
ABV: {r['abv']}%   Atenuación: {r['atenuacion']}%
IBU: {r['ibu']} ({amargor_desc})   SRM: {r['srm']} ({color_desc})
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

    def actualizar_recetas_web(self):
        """Descarga el recetario más reciente del release y lo fusiona (sin reinstalar)."""
        url = ("https://github.com/saintwick47/cervecera_vgb/"
               "releases/latest/download/recetas_cervecera_vgb.json")
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                recetas_json = json.load(r)
        except Exception as e:
            logger.error(f"actualizar_recetas_web: no se pudo descargar: {e}")
            mb.showerror("Error",
                         "No se pudo descargar el recetario.\n\n"
                         "Revisá tu conexión y probá de nuevo.\n"
                         f"Detalle: {e}")
            return
        agregadas, omitidas = 0, 0
        for nombre, datos in recetas_json.items():
            if self._guardar_desde_json(nombre, datos):
                agregadas += 1
            else:
                omitidas += 1
        self.cargar_lista_recetas()
        mb.showinfo("Recetas actualizadas",
                    f"Nuevas recetas agregadas: {agregadas}\n"
                    f"Ya existían (se omitieron): {omitidas}\n\n"
                    "Listo, sin reinstalar nada.")

    def _guardar_desde_json(self, nombre, datos):
        """Adapta una receta del JSON (formato móvil) y la guarda."""
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
