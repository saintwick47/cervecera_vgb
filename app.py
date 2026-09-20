# app.py
# Autor: SaintWick
"""
Interfaz gráfica principal de Cervecera VGB (versión PC / escritorio).
v17 — 🎯 AUTO-AMARGOR (pedido Stephan 15/9): botón que calcula los gramos de
UNA única adición de amargor @60 min para el IBU objetivo (medio del rango
BJCP del estilo elegido, o manual), usando la FÓRMULA ACTIVA del combo
"Fórmula IBU" (Tinseth o Rager) y mostrando como referencia el gramaje de
la otra fórmula. No requiere preguntar al cliente qué cálculo usa.
v16.1 — FIX COSMÉTICO: sin recorte de labels (anchos ajustados, anchor=w,
ventana 1400x900, split 2:1, lista de recetas 300 px).
v16 — LAYOUT BREWOMATIC (pedido Stephan 14/9):
· Inputs a la izquierda, Resultados en panel lateral derecho (tiempo real).
· Procesos de elaboración en orden, como instancias derivadas, abajo.
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
from bjcp_styles import comparar_con_estilo, get_style_list, STYLES
from catalogo_ar import (MALTAS_AR, LUPULOS_AR, LEVADURAS_AR,
                         ALTITUDES_CORDOBA, PERFILES_AGUA_CORDOBA)
import tkinter.messagebox as mb
from tkinter import simpledialog
import tkinter as tk  # Añadido para el manejo de iconos en Linux
import os
import sys
import math
import threading
from logger import logger
from app_paths import get_data_dir
from app_gestion import (GestionMixin, format_num, resource_path, _flotar,
                         VOLUMENES_PRESET, DEF_PERFIL_AGUA, DEF_LEVADURA,
                         DEF_ALTITUD, DEF_FORMATO, EVAPORACION_PCT)

ctk.set_appearance_mode("dark")
try:
    ctk.set_default_color_theme(resource_path("tema_brewtk.json"))
except Exception:
    ctk.set_default_color_theme("blue")


class CerveceraApp(GestionMixin, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Cervecera VGB - By SaintWick")
        self.geometry("1400x900")
        self.minsize(1300, 760)
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
        self._menu_popup = None
        self.btn_menu = ctk.CTkButton(frame_top, text="☰ Menú", command=self.abrir_menu_acciones,
                                      fg_color="#2563EB", hover_color="#1D4ED8", height=32)
        self.btn_menu.pack(side="left", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="❓ Manual de Usuario", command=self.mostrar_ayuda, fg_color="#6B7280", hover_color="#4B5563", height=32).pack(side="right", padx=10, pady=5)
        ctk.CTkButton(frame_top, text="🧾 Ver log", command=self.mostrar_log, fg_color="#475569", hover_color="#334155", height=32).pack(side="right", padx=10, pady=5)
        # --- COLUMNA IZQUIERDA (Recetas) ---
        self.frame_izquierdo = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.frame_izquierdo.grid(row=1, column=0, sticky="nsew")
        self.frame_izquierdo.grid_rowconfigure(1, weight=1)
        self._recetas_visibles = True
        self.btn_toggle_recetas = ctk.CTkButton(self.frame_izquierdo, text="🍺 Mis Recetas  ▾",
                                                fg_color="transparent", hover_color="#2c2c2c",
                                                text_color=("gray10", "gray90"),
                                                font=ctk.CTkFont(size=20, weight="bold"),
                                                command=self.toggle_lista_recetas)
        self.btn_toggle_recetas.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.lista_recetas = ctk.CTkScrollableFrame(self.frame_izquierdo)
        self.lista_recetas.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkButton(self.frame_izquierdo, text="+ Crear Receta Manual", command=self.nueva_receta).grid(row=2, column=0, padx=20, pady=20)
        # --- COLUMNA DERECHA (Tabs: Receta / Inventario) ---
        self.tabview = ctk.CTkTabview(self, corner_radius=0)
        self.tabview.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        self.tab_receta = self.tabview.add("🛠️ Receta")
        self.tab_insumos = self.tabview.add("🧪 Insumos e Inventario")
        self.tab_equipos = self.tabview.add("⚙️ Equipos")
        self.setup_tab_receta()
        self.setup_tab_insumos()
        self.setup_tab_equipos()
        self.cargar_lista_recetas()
        self.nueva_receta()
        # Auto-actualización silenciosa de recetas al abrir la app
        threading.Thread(target=self._auto_actualizar, daemon=True).start()

    # ==========================================
    # CONFIGURACIÓN PESTAÑA RECETA (v16: inputs izq. | resultados der. | procesos abajo)
    # ==========================================
    def setup_tab_receta(self):
        # ── Layout tipo Brewomatic: sub-pestañas izquierda, resultados derecha ──
        self.tab_receta.grid_columnconfigure(0, weight=2)
        self.tab_receta.grid_columnconfigure(1, weight=1)
        self.tab_receta.grid_rowconfigure(0, weight=1)
        # ── COLUMNA IZQUIERDA: sub-pestañas (Receta/Agua/Macerado/Hervido/Fermentación/Embotellado) ──
        self.subtabs_receta = ctk.CTkTabview(self.tab_receta)
        self.subtabs_receta.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        tab_general = self.subtabs_receta.add("📝 Receta")
        tab_agua_sub = self.subtabs_receta.add("💧 Agua")
        tab_mac_sub = self.subtabs_receta.add("🌾 Macerado")
        tab_herv_sub = self.subtabs_receta.add("🌿 Hervido")
        tab_ferm_sub = self.subtabs_receta.add("🧫 Fermentación")
        tab_embot_sub = self.subtabs_receta.add("🍾 Embotellado")

        self.scroll_receta = ctk.CTkScrollableFrame(tab_general, fg_color="transparent")
        self.scroll_receta.pack(fill="both", expand=True)
        self.scroll_receta.grid_columnconfigure(0, weight=1)
        scroll_agua = ctk.CTkScrollableFrame(tab_agua_sub, fg_color="transparent")
        scroll_agua.pack(fill="both", expand=True)
        scroll_mac = ctk.CTkScrollableFrame(tab_mac_sub, fg_color="transparent")
        scroll_mac.pack(fill="both", expand=True)
        scroll_herv = ctk.CTkScrollableFrame(tab_herv_sub, fg_color="transparent")
        scroll_herv.pack(fill="both", expand=True)
        scroll_ferm = ctk.CTkScrollableFrame(tab_ferm_sub, fg_color="transparent")
        scroll_ferm.pack(fill="both", expand=True)
        scroll_embot = ctk.CTkScrollableFrame(tab_embot_sub, fg_color="transparent")
        scroll_embot.pack(fill="both", expand=True)

        # ── 1. Datos Básicos (pestaña "Receta") ───────────────────────────
        frame_datos = ctk.CTkFrame(self.scroll_receta)
        frame_datos.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        frame_datos.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(frame_datos, text="Nombre:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_nombre = ctk.CTkEntry(frame_datos, placeholder_text="Ej: Mi IPA Argenta")
        self.entry_nombre.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(frame_datos, text="Volumen (L):", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.combo_volumen = ctk.CTkComboBox(frame_datos, values=VOLUMENES_PRESET, command=self.escalar_por_volumen, width=90)
        self.combo_volumen.set("20")
        self.combo_volumen.grid(row=1, column=1, padx=5, pady=5)
        ctk.CTkLabel(frame_datos, text="Eficiencia (%):", anchor="w").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.entry_eficiencia = ctk.CTkEntry(frame_datos, placeholder_text="75", width=70)
        self.entry_eficiencia.grid(row=1, column=3, padx=5, pady=5)
        self.entry_eficiencia.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        # Altitud (afecta IBU por punto de ebullición) — paridad móvil
        ctk.CTkLabel(frame_datos, text="Altitud:", anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.combo_altitud = ctk.CTkComboBox(frame_datos, values=list(ALTITUDES_CORDOBA.keys()),
                                             command=lambda e: self.calcular_y_mostrar(), width=150)
        self.combo_altitud.set(DEF_ALTITUD)
        self.combo_altitud.grid(row=2, column=1, padx=5, pady=5)
        # Levadura (define FG por atenuación + tolerancia ABV) — paridad móvil
        ctk.CTkLabel(frame_datos, text="Levadura:", anchor="w").grid(row=2, column=2, padx=5, pady=5, sticky="w")
        _levs = self._opciones_insumo("Levadura")
        self.combo_levadura = ctk.CTkComboBox(frame_datos, values=_levs,
                                              command=lambda e: self.calcular_y_mostrar(), width=200)
        self.combo_levadura.set(DEF_LEVADURA if DEF_LEVADURA in _levs else (_levs[0] if _levs else ""))
        self.combo_levadura.grid(row=2, column=3, padx=5, pady=5)
        # Estilo BJCP
        ctk.CTkLabel(frame_datos, text="Estilo Objetivo:", anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.combo_estilo_bjcp = ctk.CTkComboBox(frame_datos, values=get_style_list(), command=lambda e: self.calcular_y_mostrar())
        self.combo_estilo_bjcp.set("Auto (Sugerir)")
        self.combo_estilo_bjcp.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")
        # ── 4. Maltas ────────────────────────────────────────────────────
        frame_maltas = ctk.CTkFrame(self.scroll_receta)
        frame_maltas.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        header_maltas = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        header_maltas.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_maltas, text="🌾 Maltas y Adjuntos (Kg)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_maltas, text="+ Añadir Malta", width=100, command=lambda: self.add_fila_malta()).pack(side="right")
        # Encabezados de columna (para saber qué es cada valor)
        enc_m = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        enc_m.pack(fill="x", padx=5)
        for etiqueta, ancho in [("Malta", 190), ("Kg", 55), ("Ext", 50), ("Color", 50), ("", 28)]:
            ctk.CTkLabel(enc_m, text=etiqueta, width=ancho, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="#9CA3AF").pack(side="left", padx=2)
        self.frame_lista_maltas = ctk.CTkFrame(frame_maltas, fg_color="transparent")
        self.frame_lista_maltas.pack(fill="x")
        # ── 5. Lúpulos ───────────────────────────────────────────────────
        frame_lupulos = ctk.CTkFrame(self.scroll_receta)
        frame_lupulos.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        header_lupulos = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        header_lupulos.pack(fill="x", padx=5, pady=5)
        ctk.CTkLabel(header_lupulos, text="🌿 Lúpulos (Mezclas y Escalonados)", font=ctk.CTkFont(weight="bold")).pack(side="left")
        ctk.CTkButton(header_lupulos, text="+ Añadir Lúpulo", width=100, command=lambda: self.add_fila_lupulo()).pack(side="right")
        # v17: auto-amargor (usa la fórmula activa Tinseth/Rager)
        ctk.CTkButton(header_lupulos, text="🎯 Auto-amargor", width=110,
                      fg_color="#0D9488", hover_color="#0F766E",
                      command=self.auto_amargor).pack(side="right", padx=(0, 5))
        # Encabezados de columna
        enc_l = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        enc_l.pack(fill="x", padx=5)
        for etiqueta, ancho in [("Lúpulo", 170), ("g", 50), ("AA%", 45), ("Min", 45), ("Formato", 70), ("", 28)]:
            ctk.CTkLabel(enc_l, text=etiqueta, width=ancho, anchor="w",
                         font=ctk.CTkFont(size=11), text_color="#9CA3AF").pack(side="left", padx=2)
        self.frame_lista_lupulos = ctk.CTkFrame(frame_lupulos, fg_color="transparent")
        self.frame_lista_lupulos.pack(fill="x")
        # ── 6. Notas ─────────────────────────────────────────────────────
        frame_notas = ctk.CTkFrame(self.scroll_receta)
        frame_notas.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkLabel(frame_notas, text="📝 Notas del Cocinero", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=5)
        self.texto_notas = ctk.CTkTextbox(frame_notas, height=50, font=ctk.CTkFont(size=12))
        self.texto_notas.pack(fill="x", padx=5, pady=(0, 5))
        # ── 7. Acciones ──────────────────────────────────────────────────
        frame_acciones = ctk.CTkFrame(self.scroll_receta, fg_color="transparent")
        frame_acciones.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        ctk.CTkButton(frame_acciones, text="🔢 Calcular", command=self.calcular_y_mostrar, fg_color="#D97706", hover_color="#B45309").pack(side="left", padx=10)
        ctk.CTkButton(frame_acciones, text="💾 Guardar / Modificar", command=self.guardar_receta, fg_color="#059669", hover_color="#047857").pack(side="left", padx=10)
        ctk.CTkButton(frame_acciones, text="🗑️ Eliminar Receta", command=self.eliminar_receta, fg_color="#DC2626", hover_color="#991B1B").pack(side="left", padx=10)
        self.var_compartir_comunidad = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(frame_acciones, text="🌐 Compartir con la comunidad al guardar",
                        variable=self.var_compartir_comunidad).pack(side="left", padx=15)

        # ── 3. Perfil del Agua (pestaña "Agua") ───────────────────────────
        frame_agua = ctk.CTkFrame(scroll_agua)
        frame_agua.pack(fill="x", padx=20, pady=10)
        frame_agua.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        ctk.CTkLabel(frame_agua, text="💧 Perfil del Agua (ppm)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        self.combo_agua = ctk.CTkComboBox(frame_agua, values=list(PERFILES_AGUA_CORDOBA.keys()),
                                          command=self._on_perfil_agua, width=230)
        self.combo_agua.set(DEF_PERFIL_AGUA)
        self.combo_agua.grid(row=0, column=4, columnspan=4, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(frame_agua, text="Calcio (Ca):", anchor="w").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.entry_ca = ctk.CTkEntry(frame_agua, placeholder_text="50", width=55)
        self.entry_ca.grid(row=1, column=1, padx=2, pady=2)
        self.entry_ca.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_agua, text="Magnesio (Mg):", anchor="w").grid(row=1, column=2, padx=5, pady=2, sticky="w")
        self.entry_mg = ctk.CTkEntry(frame_agua, placeholder_text="10", width=55)
        self.entry_mg.grid(row=1, column=3, padx=2, pady=2)
        self.entry_mg.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_agua, text="Bicarbonato (HCO3):", anchor="w").grid(row=1, column=4, padx=5, pady=2, sticky="w")
        self.entry_hco3 = ctk.CTkEntry(frame_agua, placeholder_text="150", width=55)
        self.entry_hco3.grid(row=1, column=5, padx=2, pady=2)
        self.entry_hco3.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_agua, text="pH Agua:", anchor="w").grid(row=1, column=6, padx=5, pady=2, sticky="w")
        self.entry_ph_agua = ctk.CTkEntry(frame_agua, placeholder_text="7.0", width=50)
        self.entry_ph_agua.grid(row=1, column=7, padx=2, pady=2)
        self.entry_ph_agua.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        # Módulo de agua: sulfato, cloruro y agua objetivo (sales + ósmosis)
        ctk.CTkLabel(frame_agua, text="Sulfato SO4:", anchor="w").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.entry_so4 = ctk.CTkEntry(frame_agua, placeholder_text="0", width=55)
        self.entry_so4.grid(row=2, column=1, padx=2, pady=2)
        self.entry_so4.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_agua, text="Cloruro Cl:", anchor="w").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.entry_cl = ctk.CTkEntry(frame_agua, placeholder_text="0", width=55)
        self.entry_cl.grid(row=2, column=3, padx=2, pady=2)
        self.entry_cl.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_agua, text="🎯 Agua objetivo:", anchor="w").grid(row=2, column=4, padx=5, pady=2, sticky="w")
        self.combo_agua_obj = ctk.CTkComboBox(frame_agua, values=list(BrewEngine.PERFILES_AGUA_OBJETIVO.keys()),
                                              command=lambda e: self.calcular_y_mostrar(), width=180)
        self.combo_agua_obj.set("Balanceada (genérica)")
        self.combo_agua_obj.grid(row=2, column=5, columnspan=3, padx=2, pady=2, sticky="ew")

        # ── Macerado: ratio, absorción, equipo, fórmula FG ───────────────
        frame_mac = ctk.CTkFrame(scroll_mac)
        frame_mac.pack(fill="x", padx=20, pady=10)
        frame_mac.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(frame_mac, text="🌾 Maceración", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ctk.CTkLabel(frame_mac, text="Ratio (L/Kg):", anchor="w").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        self.entry_ratio = ctk.CTkEntry(frame_mac, placeholder_text="3.0", width=70)
        self.entry_ratio.grid(row=1, column=1, padx=2, pady=4, sticky="w")
        self.entry_ratio.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_mac, text="Absorción (L/Kg):", anchor="w").grid(row=1, column=2, padx=5, pady=4, sticky="w")
        self.entry_absorcion = ctk.CTkEntry(frame_mac, placeholder_text="1.0", width=70)
        self.entry_absorcion.grid(row=1, column=3, padx=2, pady=4, sticky="w")
        self.entry_absorcion.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_mac, text="Equipo:", anchor="w").grid(row=2, column=0, padx=5, pady=4, sticky="w")
        self.combo_equipo = ctk.CTkComboBox(frame_mac, values=self._nombres_equipos(),
                                            command=self._on_equipo_change, width=190)
        _eqs = self._nombres_equipos()
        self.combo_equipo.set(_eqs[0] if _eqs else "")
        self.combo_equipo.grid(row=2, column=1, columnspan=2, padx=2, pady=4, sticky="ew")
        ctk.CTkLabel(frame_mac, text="Fórmula FG:", anchor="w").grid(row=3, column=0, padx=5, pady=4, sticky="w")
        self.combo_f_fg = ctk.CTkComboBox(frame_mac, values=["Normal", "Simple"], width=110,
                                          command=self._on_formula_change)
        self.combo_f_fg.set("Simple" if self.db.get_setting("metodo_fg", "normal") == "simple" else "Normal")
        self.combo_f_fg.grid(row=3, column=1, padx=2, pady=4, sticky="w")

        # ── Hervido: tiempo, fórmula IBU ──────────────────────────────────
        frame_herv = ctk.CTkFrame(scroll_herv)
        frame_herv.pack(fill="x", padx=20, pady=10)
        frame_herv.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(frame_herv, text="🌿 Hervor", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ctk.CTkLabel(frame_herv, text="Hervor (min):", anchor="w").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        self.entry_hervor = ctk.CTkEntry(frame_herv, placeholder_text="60", width=70)
        self.entry_hervor.grid(row=1, column=1, padx=2, pady=4, sticky="w")
        self.entry_hervor.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        ctk.CTkLabel(frame_herv, text="Fórmula IBU:", anchor="w").grid(row=1, column=2, padx=5, pady=4, sticky="w")
        self.combo_f_ibu = ctk.CTkComboBox(frame_herv, values=["Tinseth", "Rager"], width=110,
                                           command=self._on_formula_change)
        self.combo_f_ibu.set("Rager" if self.db.get_setting("formula_ibu", "tinseth") == "rager" else "Tinseth")
        self.combo_f_ibu.grid(row=1, column=3, padx=2, pady=4, sticky="w")
        ctk.CTkLabel(frame_herv, text="Los lúpulos y el auto-amargor se cargan en la pestaña Receta.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)
                     ).grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 5))

        # ── Fermentación: levadura activa + fórmula ABV ──────────────────
        frame_ferm = ctk.CTkFrame(scroll_ferm)
        frame_ferm.pack(fill="x", padx=20, pady=10)
        frame_ferm.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(frame_ferm, text="🧫 Fermentación", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ctk.CTkLabel(frame_ferm, text="Fórmula ABV:", anchor="w").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        self.combo_f_abv = ctk.CTkComboBox(frame_ferm, values=["Standard", "Alternative"], width=130,
                                           command=self._on_formula_change)
        self.combo_f_abv.set("Alternative" if self.db.get_setting("formula_abv", "standard") == "alternative" else "Standard")
        self.combo_f_abv.grid(row=1, column=1, padx=2, pady=4, sticky="w")
        ctk.CTkLabel(frame_ferm, text="La levadura se elige en la pestaña Receta (afecta FG y alerta de ABV).",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)
                     ).grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 5))

        # ── Embotellado: calculadora de priming (Hall 1995 / Zahm & Nagel) ──
        self._crear_calculadora_priming(scroll_embot)

        # ── COLUMNA DERECHA: PANEL DE RESULTADOS (tiempo real) ──
        self.panel_resultados = ctk.CTkScrollableFrame(self.tab_receta)
        self.panel_resultados.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.panel_resultados.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(self.panel_resultados, text="📊 Resultados (tiempo real)",
                     font=ctk.CTkFont(size=15, weight="bold")
                     ).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0))
        self.lbl_resumen_receta = ctk.CTkLabel(self.panel_resultados, text="",
                                               font=ctk.CTkFont(size=11), text_color="#9CA3AF")
        self.lbl_resumen_receta.grid(row=1, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 2))
        # Barra de color SRM (color dinámico del mosto)
        self.frame_srm_color = ctk.CTkFrame(self.panel_resultados, height=30,
                                            corner_radius=6, fg_color="#333333")
        self.frame_srm_color.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
        self.frame_srm_color.grid_columnconfigure(0, weight=1)
        self.lbl_srm_hex = ctk.CTkLabel(self.frame_srm_color, text="", font=ctk.CTkFont(size=11))
        self.lbl_srm_hex.grid(row=0, column=0, sticky="ew", padx=6, pady=4)
        # Indicadores clave (tarjetas)
        self.res_labels = {}
        indicadores = [
            ("og", "OG"), ("fg", "FG"),
            ("abv", "ABV"), ("atenuacion", "Atenuación"),
            ("ibu", "IBU"), ("srm", "SRM"),
            ("ebc", "EBC"), ("bugu", "BU/GU"),
            ("calorias", "Calorías /355ml"), ("ph", "pH Macerado"),
        ]
        for i, (clave, titulo) in enumerate(indicadores):
            f = ctk.CTkFrame(self.panel_resultados, fg_color="#2b2b2b", corner_radius=6)
            f.grid(row=3 + i // 2, column=i % 2, padx=4, pady=3, sticky="nsew")
            ctk.CTkLabel(f, text=titulo, font=ctk.CTkFont(size=11),
                         text_color="#9CA3AF").pack(anchor="w", padx=6, pady=(4, 0))
            v = ctk.CTkLabel(f, text="—", font=ctk.CTkFont(size=14, weight="bold"),
                             anchor="w", justify="left")
            v.pack(anchor="w", padx=6, pady=(0, 4))
            self.res_labels[clave] = v
        self.lbl_alerta_lev = ctk.CTkLabel(self.panel_resultados, text="",
                                           font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_alerta_lev.grid(row=8, column=0, columnspan=2, sticky="w", padx=6, pady=4)
        # Perfil sensorial (radar) y curva de gravedad (sparkline)
        ctk.CTkLabel(self.panel_resultados, text="Perfil Sensorial", font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=9, column=0, columnspan=2, sticky="w", padx=6, pady=(6, 0))
        self.canvas_radar = tk.Canvas(self.panel_resultados, width=260, height=200,
                                      bg="#2b2b2b", highlightthickness=0)
        self.canvas_radar.grid(row=10, column=0, columnspan=2, padx=6, pady=4)
        ctk.CTkLabel(self.panel_resultados, text="Curva de Gravedad Estimada", font=ctk.CTkFont(size=12, weight="bold")
                     ).grid(row=11, column=0, columnspan=2, sticky="w", padx=6, pady=(6, 0))
        self.canvas_sparkline = tk.Canvas(self.panel_resultados, width=260, height=70,
                                          bg="#2b2b2b", highlightthickness=0)
        self.canvas_sparkline.grid(row=12, column=0, columnspan=2, padx=6, pady=4)
        # Detalle (agua, química, sales, BJCP, inventario)
        self.texto_resultados = ctk.CTkTextbox(self.panel_resultados, height=280,
                                               font=ctk.CTkFont(size=12))
        self.texto_resultados.grid(row=13, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        # ── FRANJA INFERIOR: PROCESOS EN ORDEN (instancias derivadas) ──
        self.frame_procesos = ctk.CTkFrame(self.tab_receta, corner_radius=8)
        self.frame_procesos.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        ctk.CTkLabel(self.frame_procesos, text="📋 Procesos de elaboración (en orden)",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
        self.proc_labels = {}
        procesos = [("macerado", "1️⃣ Macerado"), ("lavado", "2️⃣ Lavado"),
                    ("hervor", "3️⃣ Hervor"), ("fermentacion", "4️⃣ Fermentación")]
        for i, (clave, titulo) in enumerate(procesos):
            self.frame_procesos.grid_columnconfigure(i, weight=1)
            card = ctk.CTkFrame(self.frame_procesos, fg_color="#2b2b2b", corner_radius=6)
            card.grid(row=1, column=i, padx=4, pady=(0, 6), sticky="nsew")
            ctk.CTkLabel(card, text=titulo, font=ctk.CTkFont(size=12, weight="bold")
                         ).pack(anchor="w", padx=6, pady=(4, 0))
            lbl = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=11), justify="left")
            lbl.pack(anchor="w", padx=6, pady=(0, 6))
            self.proc_labels[clave] = lbl

    # ==========================================
    # EMBOTELLADO: calculadora de priming (Hall 1995 / curva Zahm & Nagel,
    # el mismo modelo que usan BeerSmith/Brewer's Friend). Es una utilidad
    # independiente del motor de cálculo de la receta: no se guarda en la BD.
    # ==========================================
    PRIMING_FACTORES = {
        "Dextrosa (azúcar de maíz)": 4.0,
        "Sacarosa (azúcar de mesa)": 3.8,
        "DME (extracto seco)": 4.6,
        "Miel": 5.0,
    }

    def _crear_calculadora_priming(self, parent):
        f = ctk.CTkFrame(parent)
        f.pack(fill="x", padx=20, pady=10)
        f.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(f, text="🍾 Priming / Carbonatación en Botella",
                     font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ctk.CTkLabel(f, text="Volumen a embotellar (L):", anchor="w").grid(row=1, column=0, padx=5, pady=4, sticky="w")
        self.entry_vol_embotellado = ctk.CTkEntry(f, placeholder_text="20", width=90)
        self.entry_vol_embotellado.grid(row=1, column=1, padx=2, pady=4, sticky="w")
        self.entry_vol_embotellado.bind("<KeyRelease>", lambda e: self._actualizar_priming())
        ctk.CTkLabel(f, text="Temp. máx. de fermentación (°C):", anchor="w").grid(row=1, column=2, padx=5, pady=4, sticky="w")
        self.entry_temp_embotellado = ctk.CTkEntry(f, placeholder_text="20", width=90)
        self.entry_temp_embotellado.grid(row=1, column=3, padx=2, pady=4, sticky="w")
        self.entry_temp_embotellado.bind("<KeyRelease>", lambda e: self._actualizar_priming())
        ctk.CTkLabel(f, text="CO2 objetivo (vol):", anchor="w").grid(row=2, column=0, padx=5, pady=4, sticky="w")
        self.entry_co2_objetivo = ctk.CTkEntry(f, placeholder_text="2.4", width=90)
        self.entry_co2_objetivo.grid(row=2, column=1, padx=2, pady=4, sticky="w")
        self.entry_co2_objetivo.bind("<KeyRelease>", lambda e: self._actualizar_priming())
        ctk.CTkLabel(f, text="Tipo de azúcar:", anchor="w").grid(row=2, column=2, padx=5, pady=4, sticky="w")
        self.combo_azucar_priming = ctk.CTkComboBox(f, values=list(self.PRIMING_FACTORES.keys()), width=200,
                                                     command=lambda e: self._actualizar_priming())
        self.combo_azucar_priming.set("Dextrosa (azúcar de maíz)")
        self.combo_azucar_priming.grid(row=2, column=3, padx=2, pady=4, sticky="w")
        ctk.CTkLabel(f, text="Referencia: Ale ~2.2-2.7 vol · Lager ~2.4-2.8 vol · Trigo ~3.3-4.5 vol · Cask ~1.5-2.0 vol",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)
                     ).grid(row=3, column=0, columnspan=4, sticky="w", padx=5, pady=(8, 4))
        self.lbl_priming_resultado = ctk.CTkLabel(f, text="Completá los datos para calcular.",
                                                  font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_priming_resultado.grid(row=4, column=0, columnspan=4, sticky="w", padx=5, pady=(6, 10))

    def _actualizar_priming(self):
        volumen = _flotar(self.entry_vol_embotellado.get(), None)
        if volumen is None:
            volumen = _flotar(self.combo_volumen.get(), 20) or 20
        temp_c = _flotar(self.entry_temp_embotellado.get(), None)
        co2_obj = _flotar(self.entry_co2_objetivo.get(), None)
        if temp_c is None or co2_obj is None:
            self.lbl_priming_resultado.configure(
                text="Completá temperatura de fermentación y CO2 objetivo para calcular.")
            return
        factor = self.PRIMING_FACTORES.get(self.combo_azucar_priming.get(), 4.0)
        temp_f = temp_c * 9 / 5 + 32
        residual = 3.0378 - 0.050062 * temp_f + 0.00026555 * (temp_f ** 2)
        diferencia = max(0.0, co2_obj - residual)
        gramos = volumen * diferencia * factor
        self.lbl_priming_resultado.configure(
            text=(f"CO2 residual: {residual:.2f} vol  ·  A agregar: {diferencia:.2f} vol\n"
                  f"➜ {gramos:.0f} g de {self.combo_azucar_priming.get().split(' (')[0]} "
                  f"({format_num(round(gramos / volumen, 2)) if volumen else 0} g/L)"))

    # ── Reset del panel de resultados y procesos ────────────────────────
    def _reset_panel_resultados(self):
        for lbl in self.res_labels.values():
            lbl.configure(text="—")
        self.lbl_resumen_receta.configure(text="")
        self.lbl_alerta_lev.configure(text="")
        self.frame_srm_color.configure(fg_color="#333333")
        self.lbl_srm_hex.configure(text="")
        for lbl in self.proc_labels.values():
            lbl.configure(text="—")
        self.texto_resultados.delete("1.0", "end")
        self.canvas_radar.delete("all")
        self.canvas_sparkline.delete("all")

    # ── Perfil sensorial (radar) y curva de gravedad (sparkline) ────────
    # Ambos son estimaciones ilustrativas derivadas de OG/FG/IBU/ABV/SRM,
    # no mediciones de un panel sensorial real ni una cinética de fermentación medida.
    def _dibujar_radar(self, valores):
        c = self.canvas_radar
        c.delete("all")
        cx, cy, radio = 130, 100, 68
        ejes = list(valores.keys())
        n = len(ejes)
        if n < 3:
            return
        angs = [-math.pi / 2 + i * (2 * math.pi / n) for i in range(n)]
        for frac in (0.33, 0.66, 1.0):
            pts = []
            for ang in angs:
                pts += [cx + radio * frac * math.cos(ang), cy + radio * frac * math.sin(ang)]
            c.create_polygon(pts, outline="#3F3F50", fill="", width=1)
        for ang, eje in zip(angs, ejes):
            xe, ye = cx + radio * math.cos(ang), cy + radio * math.sin(ang)
            c.create_line(cx, cy, xe, ye, fill="#3F3F50")
            xl, yl = cx + (radio + 24) * math.cos(ang), cy + (radio + 14) * math.sin(ang)
            c.create_text(xl, yl, text=eje, fill="#9CA3AF", font=("Segoe UI", 8))
        pts_val = []
        for ang, eje in zip(angs, ejes):
            val = max(0.0, min(100.0, valores[eje])) / 100.0
            pts_val += [cx + radio * val * math.cos(ang), cy + radio * val * math.sin(ang)]
        c.create_polygon(pts_val, outline="#3A7EBF", fill="#3A7EBF", width=2, stipple="gray25")
        for i in range(0, len(pts_val), 2):
            c.create_oval(pts_val[i] - 3, pts_val[i + 1] - 3, pts_val[i] + 3, pts_val[i + 1] + 3,
                          fill="#3A7EBF", outline="")

    def _dibujar_sparkline_gravedad(self, og, fg):
        c = self.canvas_sparkline
        c.delete("all")
        w, h, pad = 260, 70, 12
        dias, rango = 12, max(og - fg, 1e-6)
        puntos = []
        for i in range(dias + 1):
            t = i / dias
            g = fg + rango * math.exp(-4.5 * t)
            frac = (g - fg) / rango
            x = pad + (w - 2 * pad) * t
            y = pad + (h - 2 * pad) * (1 - frac)
            puntos += [x, y]
        if len(puntos) >= 4:
            c.create_line(*puntos, fill="#D97706", width=2, smooth=True)
        c.create_text(pad, pad - 4, text=f"OG {og:.3f}", fill="#9CA3AF", anchor="w", font=("Segoe UI", 8))
        c.create_text(w - pad, h - 4, text=f"FG {fg:.3f}", fill="#9CA3AF", anchor="e", font=("Segoe UI", 8))

    # ── Procesos en orden, derivados de la receta (tiempo real) ─────────
    def _actualizar_procesos(self, r, aguas, ratio, tiempo_hervor,
                             levadura_nombre, lupulos, eq):
        temp_mac = eq.get("temp_macerado", 66.0)
        self.proc_labels["macerado"].configure(
            text=f"Agua: {aguas['agua_maceracion']} L (ratio {ratio} L/kg)\n"
                 f"Temp: {format_num(temp_mac)} °C · pH est: {r['ph']:.2f}")
        self.proc_labels["lavado"].configure(
            text=f"Agua: {aguas['agua_lavado']} L\n"
                 f"Pre-hervor: {aguas['volumen_pre_hervor']} L")
        tiempos = sorted({int(l.get('tiempo', 0)) for l in lupulos}, reverse=True)
        esc = " / ".join(f"{t} min" for t in tiempos) if tiempos else "—"
        self.proc_labels["hervor"].configure(
            text=f"{format_num(tiempo_hervor)} min · evap {aguas['evaporacion_L']} L\n"
                 f"Lúpulos: {esc}")
        self.proc_labels["fermentacion"].configure(
            text=f"{levadura_nombre}\n"
                 f"FG {r['fg']:.3f} · ABV {r['abv']}% · aten {r['atenuacion']}%")

    # ── 🎯 AUTO-AMARGOR (v17): gramos de UNA adición @60 min para el IBU objetivo ──
    def auto_amargor(self):
        """Calcula y aplica el lúpulo de amargor (única adición @60 min) necesario
        para el IBU objetivo, con la FÓRMULA ACTIVA (combo Fórmula IBU).
        Muestra como referencia el gramaje de la otra fórmula. (Pedido Stephan 15/9)."""
        volumen, eficiencia, ratio, absorcion, tiempo_hervor, altitud = self._leer_parametros()
        maltas, _ = self.leer_ingredientes_ui()
        if not maltas:
            mb.showwarning("Atención", "Cargá al menos las maltas para conocer la OG.")
            return
        og = BrewEngine.calcular_og(maltas, volumen, eficiencia)
        # IBU objetivo: medio del rango BJCP del estilo elegido, o manual
        inicial = 40.0
        estilo = self.combo_estilo_bjcp.get()
        if estilo and estilo != "Auto (Sugerir)":
            rango = STYLES.get(estilo, {}).get("ibu")
            if rango:
                inicial = (rango[0] + rango[1]) / 2.0
        ibu_obj = simpledialog.askfloat(
            "🎯 Auto-amargor",
            f"IBU objetivo (OG {og:.3f} · {format_num(volumen)} L · alt {altitud} m):",
            parent=self, initialvalue=inicial, minvalue=1, maxvalue=120)
        if not ibu_obj:
            return
        # Lúpulo base: el de la primera fila actual (o EKG por defecto)
        filas = self._filas_de(self.frame_lista_lupulos)
        if filas:
            nombre = filas[0].c_nombre.get() or "East Kent Golding (UK)"
            aa = _flotar(filas[0].e_aa.get(), 5.0) or 5.0
            formato = filas[0].c_formato.get() or DEF_FORMATO
        else:
            nombre, aa, formato = "East Kent Golding (UK)", 5.0, DEF_FORMATO
        formula_act = "rager" if self.combo_f_ibu.get() == "Rager" else "tinseth"
        formula_ref = "tinseth" if formula_act == "rager" else "rager"
        g_act = BrewEngine.calcular_gramos_para_ibu(
            ibu_obj, volumen, og, aa, 60, altitud, formula_act, formato)
        g_ref = BrewEngine.calcular_gramos_para_ibu(
            ibu_obj, volumen, og, aa, 60, altitud, formula_ref, formato)
        nom_act = "Rager" if formula_act == "rager" else "Tinseth"
        nom_ref = "Tinseth" if formula_act == "rager" else "Rager"
        if g_act <= 0:
            mb.showerror("Error", "No se pudo calcular el gramaje (revisá IBU objetivo y AA%).")
            return
        if not mb.askyesno(
            "🎯 Auto-amargor",
            f"Se reemplazarán los lúpulos actuales por UNA adición de amargor @60 min:\n\n"
            f"   {nombre} ({format_num(aa)}% AA, {formato}): {g_act} g   [fórmula {nom_act}]\n"
            f"   (Referencia {nom_ref}: {g_ref} g)\n\n"
            f"IBU objetivo: {format_num(ibu_obj)} · OG {og:.3f} · {format_num(volumen)} L\n"
            f"¿Continuar?"):
            return
        for f in filas:
            f.destroy()
        self.add_fila_lupulo({'nombre': nombre, 'cantidad': g_act, 'aa': aa,
                              'tiempo': 60, 'formato': formato})
        self.calcular_y_mostrar()

    # ── Perfil de agua: al elegir perfil, completar campos ──────────────
    def _on_perfil_agua(self, _=None):
        perfil = PERFILES_AGUA_CORDOBA.get(self.combo_agua.get(), {})
        self.entry_ca.delete(0, "end");    self.entry_ca.insert(0, format_num(perfil.get("ca", 50)))
        self.entry_mg.delete(0, "end");    self.entry_mg.insert(0, format_num(perfil.get("mg", 10)))
        self.entry_hco3.delete(0, "end");  self.entry_hco3.insert(0, format_num(perfil.get("hco3", 150)))
        self.entry_ph_agua.delete(0, "end"); self.entry_ph_agua.insert(0, format_num(perfil.get("ph", 7.0)))
        self.calcular_y_mostrar()

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
        c_nombre = ctk.CTkComboBox(fila, values=combo_valores, width=190)
        if nombre: c_nombre.set(nombre)
        c_nombre.pack(side="left", padx=2)
        c_nombre.bind("<<ComboboxSelected>>", self._on_malta_seleccion(fila))
        e_cant = ctk.CTkEntry(fila, placeholder_text="Kg", width=55)
        e_cant.pack(side="left", padx=2)
        e_cant.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        e_ext = ctk.CTkEntry(fila, placeholder_text="Ext", width=50)
        e_ext.pack(side="left", padx=2)
        e_ext.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        e_color = ctk.CTkEntry(fila, placeholder_text="Col", width=50)
        e_color.pack(side="left", padx=2)
        e_color.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        btn_del = ctk.CTkButton(fila, text="X", width=28, fg_color="#DC2626", hover_color="#991B1B",
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
        c_nombre = ctk.CTkComboBox(fila, values=combo_valores, width=170)
        if nombre: c_nombre.set(nombre)
        c_nombre.pack(side="left", padx=2)
        c_nombre.bind("<<ComboboxSelected>>", self._on_lupulo_seleccion(fila))
        e_cant = ctk.CTkEntry(fila, placeholder_text="g", width=50)
        e_cant.pack(side="left", padx=2)
        e_cant.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        e_aa = ctk.CTkEntry(fila, placeholder_text="AA%", width=45)
        e_aa.pack(side="left", padx=2)
        e_aa.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        e_tiempo = ctk.CTkEntry(fila, placeholder_text="Min", width=45)
        e_tiempo.pack(side="left", padx=2)
        e_tiempo.bind("<KeyRelease>", lambda e: self.calcular_y_mostrar())
        c_formato = ctk.CTkComboBox(fila, values=["pellet", "flor"], width=70)
        formato = datos.get('formato', DEF_FORMATO) if datos else DEF_FORMATO
        c_formato.set(formato if formato in ("pellet", "flor") else DEF_FORMATO)
        c_formato.pack(side="left", padx=2)
        c_formato.bind("<<ComboboxSelected>>", lambda e: self.calcular_y_mostrar())
        btn_del = ctk.CTkButton(fila, text="X", width=28, fg_color="#DC2626", hover_color="#991B1B",
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
            "so4": _flotar(self.entry_so4.get(), 0),
            "cl": _flotar(self.entry_cl.get(), 0),
        }

    def _texto_ajuste_agua(self, agua, volumen_agua):
        """Sales, dilución con ósmosis y relación SO4/Cl para el agua objetivo."""
        objetivo_nombre = self.combo_agua_obj.get() or "Balanceada (genérica)"
        objetivo = BrewEngine.PERFILES_AGUA_OBJETIVO.get(objetivo_nombre, {})
        ratio, desc = BrewEngine.relacion_so4_cl(agua.get("so4", 0), agua.get("cl", 0))
        sa = BrewEngine.calcular_sales(agua, objetivo, volumen_agua)
        lineas = [
            f"\n🎯 AJUSTE DE AGUA (objetivo: {objetivo_nombre})",
            f"SO4/Cl actual: {ratio} ({desc})",
            f"Sales: yeso {sa['yeso_g']} g · CaCl2 {sa['cacl2_g']} g · "
            f"Epsom {sa['epsom_g']} g · bicarbonato {sa['bicarb_g']} g",
        ]
        if sa["ro_pct"] > 0:
            lineas.append(f"HCO3 alto: diluir {sa['ro_pct']:.0f}% con agua de ósmosis")
        lineas.append(f"Resultado: Ca {sa['ca_final']} · Mg {sa['mg_final']} · "
                      f"SO4 {sa['so4_final']} · Cl {sa['cl_final']} · HCO3 {sa['hco3_final']} ppm")
        return "\n".join(lineas)

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
                self._reset_panel_resultados()
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
            self._dibujar_sparkline_gravedad(r['og'], r['fg'])
            self._dibujar_radar({
                "Amargor": min(100.0, (r['ibu'] / 80) * 100),
                "Dulzor": min(100.0, max(0.0, (r['fg'] - 1.000) / 0.020 * 100)),
                "Cuerpo": min(100.0, max(0.0, (r['og'] - 1.030) / 0.060 * 100)),
                "Alcohol": min(100.0, (r['abv'] / 12) * 100),
                "Color": min(100.0, (r['srm'] / 40) * 100),
            })
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
            # ── PANEL DERECHO: indicadores clave (tiempo real) ──
            self.lbl_resumen_receta.configure(
                text=f"Para {format_num(volumen)} L · Altitud {altitud} m · {levadura_nombre}")
            self.res_labels["og"].configure(text=f"{r['og']:.3f}")
            self.res_labels["fg"].configure(text=f"{r['fg']:.3f}")
            self.res_labels["abv"].configure(text=f"{r['abv']}% (alt {r.get('abv_alt', r['abv'])}%)")
            self.res_labels["atenuacion"].configure(text=f"{r['atenuacion']}%")
            self.res_labels["ibu"].configure(text=f"{r['ibu']} ({amargor_desc})")
            self.res_labels["srm"].configure(text=f"{r['srm']} ({color_desc})")
            self.res_labels["ebc"].configure(text=f"{r.get('ebc', 0)}")
            self.res_labels["bugu"].configure(text=f"{r.get('bugu', 0)}")
            self.res_labels["calorias"].configure(text=f"{r['calorias']} kcal")
            self.res_labels["ph"].configure(text=f"{r['ph']:.2f}")
            self.frame_srm_color.configure(fg_color=r.get('srm_hex', '#333333'))
            self.lbl_srm_hex.configure(text=f"Color: SRM {r['srm']} · {color_desc} · EBC {r.get('ebc', 0)}")
            self.lbl_alerta_lev.configure(
                text=alerta_alcohol,
                text_color="#F87171" if r.get('alerta_abv') else "#34D399")
            # ── PANEL DERECHO: detalle (agua, química, sales, BJCP, inventario) ──
            texto = f"""💧 AGUA (evap. {EVAPORACION_PCT}%/h, hervor {tiempo_hervor} min)
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
{self._texto_ajuste_agua(agua_datos, aguas['agua_maceracion'] + aguas['agua_lavado'])}
🏅 ANÁLISIS BJCP ({estilo_elegido})
━━━━━━━━━━━━━━━━━━━━━━━━━━
{analisis_bjcp}
📦 DISPONIBILIDAD EN INVENTARIO
━━━━━━━━━━━━━━━━━━━━━━━━━━
{estado_inventario if estado_inventario else "No hay ingredientes en la receta para validar."}
"""
            self.texto_resultados.delete("1.0", "end")
            self.texto_resultados.insert("1.0", texto)
            # ── FRANJA INFERIOR: procesos en orden ──
            self._actualizar_procesos(r, aguas, ratio, tiempo_hervor,
                                      levadura_nombre, lupulos, eq)
            return {
                'og': r['og'], 'fg': r['fg'], 'abv': r['abv'], 'ibu': r['ibu'],
                'srm': r['srm'], 'ph': r['ph'], 'ph_hervor': r['ph_hervor'],
                'ph_final': r['ph_final'], 'aguas': aguas, 'r': r,
            }
        except Exception as e:
            mb.showerror("Error", f"Revisa los datos:\n{str(e)}")
            return None


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
