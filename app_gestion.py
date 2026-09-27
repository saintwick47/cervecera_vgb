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
from tkinter import simpledialog
from tkinter import filedialog, ttk
import hashlib
import csv
import json
import os
import re
import sys
import tempfile
import difflib

from logger import logger
from brew_engine import BrewEngine
from catalogo_ar import get_productores, get_categorias_malta, CATEGORIA_ADJUNTO
from logica_gestion import (
    items_por_id, valores_ficha_inventario, kardex_de_item,
    guardar_ficha_inventario, eliminar_item_inventario as borrar_item_inventario,
    datos_ficha_insumo, guardar_ficha_insumo, clave_fila_insumo, fila_a_insumo,
)

VOLUMENES_PRESET = ["5", "10", "20", "50", "100", "250", "500", "750", "1000", "1200", "1500", "2000", "3000", "5000", "10000"]
TIPOS_INVENTARIO = ["Malta", "Lúpulo", "Levadura", "Misceláneo"]
# Ubicaciones físicas (del diseño de Stitch)
UBICACIONES_INVENTARIO = ["Depósito Principal Seco", "Freezer Lúpulos (-18°C)",
                          "Cámara Levaduras (+4°C)", "Armario de Sales / Lab"]

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
            tipo = "Misceláneo"
        productos.append({"tipo": tipo, "nombre": nombre, "cantidad": cantidad, "unidad": unidad})
    return productos

# Valores por defecto (paridad con beer_vgb_mobile)
DEF_PERFIL_AGUA   = "Córdoba Capital (Agua de Red)"
DEF_LEVADURA      = "Fermentis US-05 (Ale Americana)"
DEF_ALTITUD       = "Córdoba Capital"
DEF_FORMATO       = "pellet"
# Usos de grano (columna "Uso" del diseño de Stitch)
USOS_GRANO       = ["Macerado (Mash)", "Infusión tardía", "Hervor directo", "Tostado", "Adjunto"]
# El catálogo usa nombres cortos: se traducen a las opciones del diseño
USO_A_DISEÑO     = {"Macerado": "Macerado (Mash)", "Infusión / Macerado": "Infusión tardía",
                    "Hervido": "Hervor directo", "Hervido directo": "Hervor directo",
                    "Tostado": "Tostado", "Adjunto": "Adjunto"}
# Momentos de adición del lúpulo (columna "Momento" del diseño)
MOMENTOS_LUPULO  = ["Hervor", "Whirlpool", "Dry hop"]
# Tipo de maceración (sección 3 de la ficha del diseño)
MACERACIONES     = ["Monoinfusión (65-68°C)", "Escalonada (Proteico)", "Decocción tradicional"]
# Campos de la ficha que son listas desplegables (el diseño los muestra con flecha)
CAMPOS_COMBO_INSUMO = {"uso": USOS_GRANO, "maceracion": MACERACIONES}
EVAPORACION_PCT   = 10.0  # evaporación por hora de hervor (%)
APP_VERSION       = "1.4.4"  # versión instalada (para comprobar actualizaciones)
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
        ("temp_grano", "Temp. del Grano", "°C", 20.0, False),
        ("relacion_empaste", "Relación Empaste", "L/Kg", 3.0, False),
        ("perdida_termica", "Pérdida Térmica", "°C", 6.0, False),
        ("temp_lavado", "Temperatura Lavado", "°C", 75.0, False),
        ("tiempo_agua_mash", "Tiempo Agua Mash", "min", 60.0, False),
        ("duracion_lavado", "Duración Lavado", "min", 40.0, False),
        ("precalentamiento_hlt", "Precalentamiento HLT", "°C", 80.0, False),
        ("strike_water", "Strike Water Cal.", "°C", 0.0, False),
        ("tiempo_hervido_eq", "Tiempo de Hervido (min)", "min", 60.0, False),
        ("evaporacion_pct_calc", "Evaporación (%)", "%", 8.0, False),
    ]),
    ("Mermas, Absorción y Pérdidas del Equipo", [
        ("espacio_muerto", "Espacio Muerto (Lts)", "L", 3.0, False),
        ("absorcion_grano", "Absorción del Grano", "L/Kg", 1.0, False),
        ("duracion_prehervor", "Duración Pre-Hervor", "min", 30.0, False),
        ("duracion_enfriado", "Duración Enfriado", "min", 40.0, False),
        ("caudal_enfriador", "Caudal Bomba Salida", "L/min", 3.5, False),
        ("perdida_turb_enfriador", "Pérdida Turb / Enfriador", "L", 4.0, False),
        ("expansion_termica", "Expansión Térmica Mosto", "%", 4.0, False),
    ]),
    ("Control de pH y Fermentación", [
        ("tasa_inoculacion", "Tasa de Inoculación por Defecto", "M/mL/°P", 0.75, False),
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
        frame_contacto = ctk.CTkFrame(self, fg_color="#24242C", corner_radius=8)
        frame_contacto.grid(row=1, column=0, padx=20, pady=(5, 5), sticky="ew")
        ctk.CTkLabel(frame_contacto, text="👨‍💻 Autor: SaintWick", font=ctk.CTkFont(weight="bold", size=13)).pack(side="left", padx=15, pady=10)
        ctk.CTkLabel(frame_contacto, text="📧 nicoweb45@proton.me (Asunto: beer_vgb)", font=ctk.CTkFont(size=13)).pack(side="right", padx=15, pady=10)
        frame_colaboradores = ctk.CTkFrame(self, fg_color="#24242C", corner_radius=8)
        frame_colaboradores.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="ew")
        ctk.CTkLabel(frame_colaboradores, text="🤝 Colaboradores: Stephan",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=15, pady=8)
        btn_cerrar = ctk.CTkButton(self, text="Cerrar Manual", command=self.destroy, fg_color="#2B2B36", hover_color="#3F3F50")
        btn_cerrar.grid(row=3, column=0, padx=20, pady=(10, 20))
        mensaje = """
🍺 MANUAL DE USUARIO - CERVECERA VGB (v18 - Comunidad + Insumos/Inventario unificado)

📝 1. RECETA — organizada en sub-pestañas:
   • Receta: nombre, volumen, eficiencia, ALTITUD (afecta IBU), LEVADURA
     (define FG por atenuación y tolerancia de ABV), estilo BJCP objetivo,
     maltas, lúpulos (escalonables) y notas.
   • Agua: perfil Ca/Mg/HCO3/pH de entrada, sulfato/cloruro y agua objetivo.
   • Macerado: ratio L/kg, absorción L/kg, equipo activo y fórmula de FG.
   • Hervido: tiempo de hervor y fórmula de IBU (Tinseth/Rager).
   • Fermentación: fórmula de ABV (Standard/Alternative).
   • Embotellado: calculadora de PRIMING (azúcar de cebado): volumen a
     embotellar, temperatura máxima de fermentación y CO2 objetivo →
     gramos de azúcar (dextrosa/sacarosa/DME/miel) y g/L.
   RESULTADOS en el panel derecho, en TIEMPO REAL: OG, FG, ABV, IBU, SRM,
   EBC, BU/GU, calorías, pH, más un gráfico de PERFIL SENSORIAL (radar) y
   la CURVA DE GRAVEDAD estimada (OG→FG) — ambos son estimaciones
   ilustrativas, no mediciones. Abajo, los PROCESOS en orden (Macerado →
   Lavado → Hervor → Fermentación).
🎯 AUTO-AMARGOR: botón en el header de Lúpulos. Calcula los gramos de UNA
única adición de amargor @60 min para el IBU objetivo (medio del rango BJCP
del estilo elegido, o cargado a mano), usando la FÓRMULA ACTIVA del combo
"Fórmula IBU" (Tinseth o Rager). El diálogo muestra también el gramaje de
la otra fórmula como referencia. Reemplaza los lúpulos actuales tras confirmar.
Maltas y Lúpulos desde el catálogo argentino (autocompletan Ext/Color y
AA%/formato).

🧪 2. INSUMOS E INVENTARIO (una sola pestaña):
   Arriba, el CATÁLOGO de insumos (editable), con filtro por tipo (Todos/
   Malta/Lúpulo/Levadura). Abajo, el INVENTARIO: alta y suma de stock con
   costo unitario, mínimo de alerta y vencimiento opcionales por ítem.
   KPIs en vivo: valorización total en $ y cantidad con stock bajo.
   "📋 Pegar productos": pegás texto de una factura o planilla y detecta
   solo nombre/cantidad/unidad por línea, matcheando cada nombre contra el
   catálogo automáticamente (revisás y confirmás antes de importar).
   "🔻 Consumo/Merma": descuenta stock a mano (cocción, rotura, ajuste).
   KARDEX: historial de movimientos (entradas/salidas/mermas), se registra
   solo con cada alta o consumo y sobrevive aunque el ítem se agote.
   Al calcular una receta, se valida la disponibilidad contra este inventario.

⚙️ 3. EQUIPOS: perfiles guardables (lote, olla, pérdidas, evaporación,
eficiencia, temp. de macerado) más parámetros extendidos por perfil:
maceración/empaste (temp. de grano, relación de empaste, pérdida térmica,
temp./tiempo de lavado), mermas y pérdidas (espacio muerto, absorción,
duración de pre-hervor/enfriado, caudal, expansión térmica) y pH objetivo
por etapa + tasa de inoculación.

📊 4. COMPARADOR BJCP: estilo objetivo con rangos oficiales (OG, FG, IBU, SRM).

🌐 5. COMUNIDAD: tildá "Compartir con la comunidad al guardar" (pestaña
Receta) para subir tu receta — necesita un token de GitHub configurado una
sola vez (ver mensaje en pantalla si falta). Cualquiera con la app puede
bajar lo que se compartió con "🌐 Recetas de la Comunidad" (menú ☰), sin
necesitar token para eso.

☰ 6. MENÚ (arriba a la izquierda): Importar JSON, Buscar recetas nuevas,
Recetas de la Comunidad, Comprobar actualizaciones, Exportar PDF y
Exportar BeerXML — todo agrupado en un solo desplegable.

📖 7. AGREGAR RECETAS (sin reinstalar):
Al abrir la app, se busca solo el recetario más reciente en la web y se
fusiona automáticamente (sin que hagas nada).
También podés usar "🔄 Buscar recetas nuevas" (manual) o "📂 Importar JSON"
con un archivo descargado. Las recetas nuevas quedan guardadas.
⬆️ 8. ACTUALIZAR LA APP:
Botón "⬆️ Comprobar actualizaciones": si hay una versión nueva, la descarga.
En Windows se instala sola (en silencio); en Linux/macOS la descarga y la abre.
🧾 9. REGISTRO DE ERRORES:
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
Priming/Carbonatación: modelo Zahm & Nagel / Hall (1995) — el mismo que usan
BeerSmith y Brewer's Friend.
Estilos: BJCP 2021 - Brewers Association - Norbrygg - SHBF.
Interoperabilidad: BeerXML (beerxml.com).
Refs: docs.brewfather.app/settings.md - docs.brewfather.app/recipes/calculations.md

📧 10. CONTACTO: nicoweb45@proton.me (Asunto: beer_vgb)
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
                                         text_color="#D97706")
        self.lbl_kpi_bajo.grid(row=0, column=2, padx=10, pady=8)
        self.lbl_kpi_porvencer = ctk.CTkLabel(kpis, text="⏳ Por vencer: 0",
                                              font=ctk.CTkFont(size=13, weight="bold"),
                                              text_color="#DC2626")
        self.lbl_kpi_porvencer.grid(row=0, column=3, padx=10, pady=8, sticky="e")
        kpis.grid_columnconfigure(3, weight=1)

        header = ctk.CTkFrame(cont, fg_color="transparent")
        header.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")
        self.seg_inv_filtro = ctk.CTkSegmentedButton(
            header, values=["Todos"] + TIPOS_INVENTARIO,
            command=lambda _sel=None: self.cargar_lista_inventario())
        self.seg_inv_filtro.set("Todos")
        self.seg_inv_filtro.pack(anchor="w", pady=(0, 8))
        # Filtro por ubicación física (como el diseño)
        self.combo_inv_ubicacion = ctk.CTkComboBox(
            header, values=["Todas las ubicaciones"] + list(UBICACIONES_INVENTARIO), width=250,
            command=lambda _v=None: self.cargar_lista_inventario())
        self.combo_inv_ubicacion.set("Todas las ubicaciones")
        self.combo_inv_ubicacion.pack(anchor="w", pady=(0, 6))
        fila_acciones = ctk.CTkFrame(header, fg_color="transparent")
        fila_acciones.pack(fill="x")
        self.entry_inv_buscar = ctk.CTkEntry(fila_acciones, placeholder_text="🔍 Buscar insumo, cepa, lote...", width=250)
        self.entry_inv_buscar.pack(side="left")
        self.entry_inv_buscar.bind("<KeyRelease>", lambda e: self.cargar_lista_inventario())
        ctk.CTkButton(fila_acciones, text="🛒 Generar Orden de Compra Sugerida", width=250,
                      command=self.generar_orden_compra,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="right", padx=(6, 0))
        ctk.CTkButton(fila_acciones, text="⚖️ Ajuste Físico", width=130,
                      command=self.abrir_dialogo_ajuste_fisico,
                      fg_color="#D97706", hover_color="#B45309").pack(side="right", padx=(6, 0))
        ctk.CTkButton(fila_acciones, text="+ Ingresar Stock", width=130, command=self.abrir_dialogo_ingresar_stock,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="right", padx=(6, 0))
        ctk.CTkButton(fila_acciones, text="📥 Exportar CSV", width=120, command=self.exportar_inventario_csv,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="right", padx=6)
        ctk.CTkButton(fila_acciones, text="🔻 Consumo/Merma", width=130, command=self.abrir_dialogo_consumo_inventario,
                      fg_color="#D97706", hover_color="#B45309").pack(side="right", padx=6)
        ctk.CTkButton(fila_acciones, text="📋 Pegar productos", width=130, command=self.abrir_dialogo_pegar_productos,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="right", padx=6)

        cuerpo = ctk.CTkFrame(cont, fg_color="transparent")
        cuerpo.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="nsew")
        cuerpo.grid_columnconfigure(0, weight=8)
        cuerpo.grid_columnconfigure(1, weight=4)

        frame_lista_inv = ctk.CTkFrame(cuerpo)
        frame_lista_inv.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        # ── Rail derecho: cocciones programadas + distribución de espacio ──
        cuerpo.grid_columnconfigure(2, weight=0, minsize=290)
        rail = ctk.CTkFrame(cuerpo, width=290)
        rail.grid(row=0, column=2, padx=(8, 0), sticky="nsew")
        cab_rail = ctk.CTkFrame(rail, fg_color="transparent")
        cab_rail.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(cab_rail, text="📅 Próximas Cocciones Programadas",
                     font=ctk.CTkFont(size=12, weight="bold"), wraplength=260,
                     justify="left").pack(anchor="w")
        self.lbl_cocciones_estado = ctk.CTkLabel(cab_rail, text="", text_color="#9CA3AF",
                                                 font=ctk.CTkFont(size=11))
        self.lbl_cocciones_estado.pack(anchor="w")
        self.lista_cocciones = ctk.CTkFrame(rail, fg_color="transparent")
        self.lista_cocciones.pack(fill="x", padx=8)
        fila_cocc = ctk.CTkFrame(rail, fg_color="transparent")
        fila_cocc.pack(fill="x", padx=12, pady=(6, 4))
        ctk.CTkButton(fila_cocc, text="➕  Programar cocción", height=26,
                      fg_color="#3A7EBF", hover_color="#1F538D",
                      command=self.abrir_dialogo_programar_coccion).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(fila_cocc, text="Ver todo", height=26, width=70,
                      fg_color="#2B2B36", hover_color="#3F3F50",
                      command=self.mostrar_todas_las_cocciones).pack(side="left", padx=(4, 0))
        ctk.CTkButton(rail, text="🏷️ Etiqueta QR / Lote", height=26,
                      fg_color="#2B2B36", hover_color="#3F3F50",
                      command=self.generar_etiqueta_lote).pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkFrame(rail, height=1, fg_color="#3F3F50").pack(fill="x", padx=12)
        ctk.CTkLabel(rail, text="📦 Distribución de Espacio de Acopio",
                     font=ctk.CTkFont(size=12, weight="bold"), wraplength=260,
                     justify="left").pack(anchor="w", padx=12, pady=(10, 2))
        self.lbl_capacidad = ctk.CTkLabel(rail, text="", text_color="#D97706",
                                          font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_capacidad.pack(anchor="w", padx=12)
        self.lbl_distribucion = ctk.CTkLabel(rail, text="", justify="left", text_color="#9CA3AF",
                                             font=ctk.CTkFont(size=10))
        self.lbl_distribucion.pack(anchor="w", padx=12, pady=(2, 10))
        cab_inv = ctk.CTkFrame(frame_lista_inv, fg_color="transparent")
        cab_inv.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(cab_inv, text="📦 Planilla Operativa de Depósito",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkLabel(cab_inv, text="Ordenado por: Urgencia / Stock Mínimo",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(side="right")
        # Columnas de la "Planilla Operativa de Depósito" del diseño
        cols = ("lote", "tipo", "espec", "fisico", "nivel", "costo", "estado", "acciones")
        self.tree_inventario = ttk.Treeview(frame_lista_inv, columns=cols, show="tree headings",
                                            style="Inventario.Treeview", height=16, selectmode="browse")
        self.tree_inventario.heading("#0", text="Insumo & Cepa / Lote")
        self.tree_inventario.heading("lote", text="Lote / Ubicación")
        self.tree_inventario.heading("tipo", text="Categoría")
        self.tree_inventario.heading("espec", text="Específico (AA% / EBC)")
        self.tree_inventario.heading("fisico", text="Físico")
        self.tree_inventario.heading("nivel", text="Nivel / Mín")
        self.tree_inventario.heading("costo", text="Costo Unit.")
        self.tree_inventario.heading("estado", text="Estado")
        self.tree_inventario.heading("acciones", text="Acciones")
        self.tree_inventario.column("#0", width=170, anchor="w")
        self.tree_inventario.column("lote", width=190, anchor="w")
        self.tree_inventario.column("tipo", width=95, anchor="w")
        self.tree_inventario.column("espec", width=105, anchor="center")
        self.tree_inventario.column("fisico", width=95, anchor="center")
        self.tree_inventario.column("nivel", width=130, anchor="center")
        self.tree_inventario.column("costo", width=85, anchor="w")
        self.tree_inventario.column("estado", width=85, anchor="w")
        self.tree_inventario.column("acciones", width=70, anchor="center")
        self.tree_inventario.tag_configure("bajo", foreground="#D97706")
        self._preparar_filas_alternadas(self.tree_inventario)
        self.tree_inventario.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        pie_inv = ctk.CTkFrame(frame_lista_inv, fg_color="transparent")
        pie_inv.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(pie_inv, text="‹ Anterior", width=90, height=24,
                      command=lambda: self._inv_pagina_mover(-1),
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left")
        ctk.CTkButton(pie_inv, text="Siguiente ›", width=90, height=24,
                      command=lambda: self._inv_pagina_mover(1),
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left", padx=4)
        self.lbl_inv_pagina = ctk.CTkLabel(pie_inv, text="", text_color="#9CA3AF",
                                           font=ctk.CTkFont(size=11))
        self.lbl_inv_pagina.pack(side="left", padx=6)
        self.tree_inventario.bind("<<TreeviewSelect>>", self._inv_on_select)
        # Acciones por fila (como los iconos del diseño): doble clic = historial,
        # clic derecho = menú con historial y ajuste físico.
        self.tree_inventario.bind("<Double-1>", self._inv_ver_historial)
        self.tree_inventario.bind("<Button-3>", self._inv_menu_fila)

        # Ficha de Insumo Activo — metadatos editables + Kardex del ítem seleccionado
        frame_ficha_inv = ctk.CTkFrame(cuerpo)
        frame_ficha_inv.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        frame_ficha_inv.grid_columnconfigure((0, 1), weight=1)
        frame_ficha_inv.grid_rowconfigure(8, weight=1)
        self.lbl_ficha_inv = ctk.CTkLabel(frame_ficha_inv, text="📇 Ficha de Insumo",
                                          font=ctk.CTkFont(size=15, weight="bold"), wraplength=280, justify="left")
        self.lbl_ficha_inv.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 2))
        self.lbl_ficha_inv_sub = ctk.CTkLabel(frame_ficha_inv, text="Elegí un insumo de la lista.",
                                              text_color="#9CA3AF", font=ctk.CTkFont(size=11))
        self.lbl_ficha_inv_sub.grid(row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))
        ctk.CTkLabel(frame_ficha_inv, text="Costo unit. $:").grid(row=2, column=0, sticky="w", padx=(12, 4), pady=3)
        self.entry_ficha_costo = ctk.CTkEntry(frame_ficha_inv, width=110)
        self.entry_ficha_costo.grid(row=2, column=1, sticky="ew", padx=(4, 12), pady=3)
        ctk.CTkLabel(frame_ficha_inv, text="Mínimo (alerta):").grid(row=3, column=0, sticky="w", padx=(12, 4), pady=3)
        self.entry_ficha_minimo = ctk.CTkEntry(frame_ficha_inv, width=110)
        self.entry_ficha_minimo.grid(row=3, column=1, sticky="ew", padx=(4, 12), pady=3)
        ctk.CTkLabel(frame_ficha_inv, text="Vencimiento:").grid(row=4, column=0, sticky="w", padx=(12, 4), pady=3)
        self.entry_ficha_vencimiento = ctk.CTkEntry(frame_ficha_inv, placeholder_text="AAAA-MM-DD", width=110)
        self.entry_ficha_vencimiento.grid(row=4, column=1, sticky="ew", padx=(4, 12), pady=3)
        ctk.CTkLabel(frame_ficha_inv, text="Almacenamiento:").grid(row=5, column=0, sticky="w", padx=(12, 4), pady=3)
        self.combo_ficha_ubicacion = ctk.CTkComboBox(frame_ficha_inv, values=[""] + list(UBICACIONES_INVENTARIO),
                                                     width=200)
        self.combo_ficha_ubicacion.grid(row=5, column=1, columnspan=3, sticky="ew", padx=(4, 12), pady=3)
        ctk.CTkLabel(frame_ficha_inv, text="Lote:").grid(row=6, column=0, sticky="w", padx=(12, 4), pady=3)
        self.entry_ficha_lote = ctk.CTkEntry(frame_ficha_inv, placeholder_text="Ej: CAS-2023-AR", width=140)
        self.entry_ficha_lote.grid(row=6, column=1, sticky="ew", padx=(4, 12), pady=3)
        frame_bot_ficha = ctk.CTkFrame(frame_ficha_inv, fg_color="transparent")
        frame_bot_ficha.grid(row=5, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="ew")
        ctk.CTkButton(frame_bot_ficha, text="💾 Guardar", command=self._inv_guardar_ficha,
                      fg_color="#22C55E", hover_color="#16A34A").pack(side="left")
        ctk.CTkButton(frame_bot_ficha, text="🗑️ Eliminar", command=self._inv_borrar_actual,
                      fg_color="#DC2626", hover_color="#B91C1C").pack(side="left", padx=6)
        ctk.CTkFrame(frame_ficha_inv, height=2, fg_color="#2B2B36").grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=8)
        ctk.CTkLabel(frame_ficha_inv, text="📜 Historial de Movimientos (Kardex)",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(row=7, column=0, columnspan=2, sticky="w", padx=12)
        self.lista_kardex_ui = ctk.CTkScrollableFrame(frame_ficha_inv, height=220)
        self.lista_kardex_ui.grid(row=8, column=0, columnspan=2, sticky="nsew", padx=8, pady=(4, 10))

        self._inv_actual = None
        self._inv_items_por_id = {}
        self.cargar_lista_inventario()

    def setup_tab_equipos(self):
        self.tab_equipos.grid_columnconfigure(0, weight=1)
        self.tab_equipos.grid_rowconfigure(0, weight=1)
        self.tab_equipos.grid_columnconfigure(0, weight=1)
        self.tab_equipos.grid_columnconfigure(1, weight=0, minsize=290)
        contenedor = ctk.CTkFrame(self.tab_equipos, fg_color="transparent")
        contenedor.grid(row=0, column=0, sticky="nsew")
        contenedor.grid_columnconfigure(0, weight=1)
        contenedor.grid_rowconfigure(0, weight=1)

        # 4 sub-pestañas del diseño
        subtabs = ctk.CTkTabview(contenedor, fg_color="#1E1E24")
        subtabs.grid(row=0, column=0, sticky="nsew")
        self.subtabs_equipos = subtabs
        try:
            n_perfiles = len(self.db.get_equipment())
        except Exception:
            n_perfiles = 0
        tab_perfiles = subtabs.add(f"👤 Perfiles de Equipamiento ({n_perfiles})")
        tab_default = subtabs.add("🎛️ Valores por Defecto (Activo)")
        tab_calib = subtabs.add("📏 Calibración de Ollas")
        tab_bexml = subtabs.add("📤 Exportar / Importar BeerXML")
        for t in (tab_perfiles, tab_default, tab_calib, tab_bexml):
            t.grid_columnconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(tab_perfiles, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        c = ctk.CTkFrame(scroll)
        c.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        c.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(c, text="⚙️ Perfiles de equipo", font=ctk.CTkFont(size=16, weight="bold")
                     ).grid(row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(8, 4))
        campos = [("name", "Nombre"), ("batch_volume", "Tamaño Batch (Lts)"),
                  ("kettle_volume", "Olla (L)"), ("perdidas_l", "Pérdidas (L)"),
                  ("evaporacion_l_h", "Evaporación (L/h)"), ("eficiencia_pct", "Eficiencia (%)"),
                  ("temp_macerado", "Temp. Macerado (°C)"), ("notas", "Cervecero / Notas")]
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
        ctk.CTkButton(c, text="💾 Guardar Configuración", command=self._eq_guardar,
                      fg_color="#22C55E", hover_color="#16A34A"
                      ).grid(row=fila, column=0, columnspan=2, padx=6, pady=10, sticky="w")
        ctk.CTkButton(c, text="🧹 Descartar", command=self._eq_limpiar,
                      fg_color="#2B2B36", hover_color="#3F3F50").grid(row=fila, column=2, padx=6, pady=10, sticky="w")
        fl = ctk.CTkFrame(scroll)
        fl.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.lista_equipos_ui = ctk.CTkScrollableFrame(fl, height=220)
        self.lista_equipos_ui.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._eq_acciones(tab_perfiles, tab_default, tab_calib, tab_bexml)
        self.cargar_lista_equipos()
        self._cargar_balance_teorico()

    def _eq_acciones(self, tab_perfiles, tab_default, tab_calib, tab_bexml):
        """Botones y contenido de las sub-pestañas de Equipos (diseño de Stitch)."""
        # Perfiles: acciones del diseño (grid: esta pestaña ya usa grid para el scroll)
        tab_perfiles.grid_rowconfigure(0, weight=1)
        acciones = ctk.CTkFrame(tab_perfiles, fg_color="transparent")
        acciones.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 12))
        ctk.CTkButton(acciones, text="➕ Crear Nuevo Perfil", command=self._eq_limpiar,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="left")
        ctk.CTkButton(acciones, text="➕ Nuevo Equipo", command=self._eq_limpiar,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left", padx=6)
        ctk.CTkButton(acciones, text="⬇️ Importar Brewomatic", command=self._eq_importar_brewomatic,
                      fg_color="#D97706", hover_color="#B45309").pack(side="left")

        # Valores por Defecto
        ctk.CTkLabel(tab_default, text="🎛️ Valores por Defecto", font=ctk.CTkFont(size=16, weight="bold")
                     ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(tab_default, text="El perfil activo define lote, pérdidas, evaporación y macerado.\n"
                                       "Podés guardarlo como valores por defecto de la app.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11), justify="left"
                     ).pack(anchor="w", padx=20)
        ctk.CTkButton(tab_default, text="💾 Guardar Perfil Activo", command=self._eq_guardar,
                      fg_color="#22C55E", hover_color="#16A34A").pack(anchor="w", padx=20, pady=(12, 4))
        ctk.CTkButton(tab_default, text="✏️ Editar Parámetros", command=self._eq_editar_parametros,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkButton(tab_default, text="💾 Guardar como valores por defecto",
                      command=self._eq_guardar_valores_por_defecto,
                      fg_color="#22C55E", hover_color="#16A34A").pack(anchor="w", padx=20, pady=(12, 4))
        ctk.CTkButton(tab_default, text="↩️ Restaurar Brewomatic", command=self._eq_restaurar_brewomatic,
                      fg_color="#D97706", hover_color="#B45309").pack(anchor="w", padx=20, pady=(0, 4))
        fila_strike = ctk.CTkFrame(tab_default, fg_color="transparent")
        fila_strike.pack(anchor="w", padx=20, pady=(4, 0))
        ctk.CTkButton(fila_strike, text="🌡️ Calcular Strike Water", command=self._eq_aplicar_strike,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="left")
        self.lbl_strike_calculado = ctk.CTkLabel(fila_strike, text="Calculado: —",
                                                 text_color="#D97706",
                                                 font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_strike_calculado.pack(side="left", padx=8)
        self.var_visibilidad_comunidad = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tab_default, text="Visibilidad en Comunidad",
                        variable=self.var_visibilidad_comunidad).pack(anchor="w", padx=20, pady=(10, 0))
        self.lbl_default_activo = ctk.CTkLabel(tab_default, text="", text_color="#9CA3AF",
                                               font=ctk.CTkFont(size=11), justify="left")
        self.lbl_default_activo.pack(anchor="w", padx=20, pady=(12, 0))

        # Calibración de Ollas
        ctk.CTkLabel(tab_calib, text="📏 Calibración de Ollas", font=ctk.CTkFont(size=16, weight="bold")
                     ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(tab_calib, text="Medí con agua y corregí la escala de la olla.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        marco = ctk.CTkFrame(tab_calib, fg_color="transparent")
        marco.pack(anchor="w", padx=20, pady=10)
        campos = [("Volumen medido (L)", "20.0"), ("Volumen marcado en la olla (L)", "19.0"),
                  ("Agua de espacio muerto (L)", "1.5")]
        entradas = []
        for i, (etiqueta, valor) in enumerate(campos):
            ctk.CTkLabel(marco, text=f"{etiqueta}:").grid(row=i, column=0, sticky="w", pady=3)
            e = ctk.CTkEntry(marco, width=110)
            e.insert(0, valor)
            e.grid(row=i, column=1, padx=8, pady=3)
            entradas.append(e)
        ctk.CTkButton(tab_calib, text="📐 Calcular y aplicar",
                      command=lambda: self._eq_calibrar_olla(*entradas),
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(anchor="w", padx=20)

        # Exportar / Importar BeerXML
        ctk.CTkLabel(tab_bexml, text="📤 Exportar / Importar BeerXML",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(tab_bexml, text="Compatible con Brewfather, BeerSmith y Brew-o-Matic.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=20)
        ctk.CTkButton(tab_bexml, text="💾 Exportar perfil de equipo", command=self._eq_exportar_beerxml,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(anchor="w", padx=20, pady=(12, 4))
        ctk.CTkButton(tab_bexml, text="📂 Importar equipo desde BeerXML",
                      command=self._eq_importar_beerxml,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(anchor="w", padx=20, pady=4)
        ctk.CTkButton(tab_bexml, text="⬇️ Importar Brewomatic", command=self._eq_importar_brewomatic,
                      fg_color="#D97706", hover_color="#B45309").pack(anchor="w", padx=20, pady=4)

        # ── Rail derecho: Balance Teórico del Lote ──
        rail = ctk.CTkFrame(self.tab_equipos, width=290)
        rail.grid(row=0, column=1, padx=(8, 12), pady=12, sticky="nsew")
        ctk.CTkLabel(rail, text="🧮 Balance Teórico del Lote",
                     font=ctk.CTkFont(size=12, weight="bold"), wraplength=260,
                     justify="left").pack(anchor="w", padx=12, pady=(12, 6))
        self.lbl_balance = ctk.CTkLabel(rail, text="", justify="left", text_color="#C1C7D2",
                                        font=ctk.CTkFont(size=11), anchor="w")
        self.lbl_balance.pack(anchor="w", padx=12)
        ctk.CTkButton(rail, text="🔄 Recalcular", height=26, command=self._cargar_balance_teorico,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(fill="x", padx=12, pady=12)

    def _eq_limpiar(self):
        for e in self._eq_entries.values():
            e.delete(0, "end")
        for e in self._eq_extra_entries.values():
            e.delete(0, "end")

    # ==========================================
    # EQUIPOS: sub-pestañas del diseño + Balance Teórico del Lote
    # ==========================================
    def _eq_valor(self, clave, por_defecto=0.0):
        """Lee un valor numérico del perfil de equipo (campos base o extendidos)."""
        for fuente in (getattr(self, "_eq_entries", {}), getattr(self, "_eq_extra_entries", {})):
            entrada = (fuente or {}).get(clave)
            if entrada is not None:
                try:
                    return float(str(entrada.get()).replace(",", ".") or por_defecto)
                except ValueError:
                    return por_defecto
        return por_defecto

    def _balance_teorico(self):
        """Agua y pérdidas del lote (tarjeta del rail de Equipos del diseño)."""
        lote = self._eq_valor("batch_volume", 20.0)
        evaporacion_l_h = self._eq_valor("evaporacion_l_h", 3.0)
        absorcion_l_kg = self._eq_valor("absorcion_grano", 1.0)
        espacio_muerto = self._eq_valor("espacio_muerto", 3.0)
        turb = self._eq_valor("perdida_turb_enfriador", 4.0)
        ratio = self._eq_valor("relacion_empaste", 3.0)
        horas_hervor = self._eq_valor("tiempo_hervor", 60.0) / 60.0
        evaporacion = evaporacion_l_h * horas_hervor

        granos_kg = 0.0
        try:
            maltas, _ = self.leer_ingredientes_ui()
            granos_kg = sum(float(m.get("cantidad") or 0) for m in maltas)
        except Exception:
            granos_kg = 0.0

        absorcion = granos_kg * absorcion_l_kg
        perdidas = absorcion + evaporacion + turb + espacio_muerto
        agua_total = lote + perdidas
        mash = granos_kg * ratio
        lavado = max(0.0, agua_total - mash)
        return {
            "lote": lote, "granos": granos_kg, "mash": mash, "lavado": lavado,
            "agua_total": agua_total, "perdidas": perdidas, "absorcion": absorcion,
            "evaporacion": evaporacion, "turb": turb, "espacio_muerto": espacio_muerto,
            "pct_mash": (mash / agua_total * 100) if agua_total else 0,
            "pct_lavado": (lavado / agua_total * 100) if agua_total else 0,
            "pct_evap": (evaporacion / agua_total * 100) if agua_total else 0,
        }

    def _cargar_balance_teorico(self):
        """Pinta el rail de Balance Teórico del Lote."""
        if not hasattr(self, "lbl_balance"):
            return
        b = self._balance_teorico()
        if hasattr(self, "lbl_strike_calculado"):
            self.lbl_strike_calculado.configure(
                text=f"Calculado: {format_num(round(self._strike_water(), 1))} °C")
        entrada_evap = getattr(self, "_eq_extra_entries", {}).get("evaporacion_pct_calc")
        if entrada_evap is not None:
            entrada_evap.delete(0, "end")
            entrada_evap.insert(0, f"{b['pct_evap']:.1f}")
        self.lbl_balance.configure(text="\n".join([
            f"💧 Agua total:  {format_num(round(b['agua_total'], 1))} L",
            f"🌾 Mash:  {format_num(round(b['mash'], 1))} L  ({b['pct_mash']:.0f}%)",
            f"🚿 Lavado:  {format_num(round(b['lavado'], 1))} L  ({b['pct_lavado']:.0f}%)",
            "",
            f"📉 Pérdidas acumuladas: {format_num(round(b['perdidas'], 1))} L",
            f"   · granos: {format_num(round(b['absorcion'], 1))} L "
            f"({format_num(b['granos'])} kg)",
            f"   · evaporación: {format_num(round(b['evaporacion'], 1))} L "
            f"({b['pct_evap']:.0f}%)",
            f"   · fondo/turbio: {format_num(round(b['turb'], 1))} L",
            f"   · espacio muerto: {format_num(round(b['espacio_muerto'], 1))} L",
            "",
            f"🎯 Lote final: {format_num(round(b['lote'], 1))} L",
            "",
            f"🌡️ Strike Water Cal.: {format_num(round(self._strike_water(), 1))} °C",
            "" if b["granos"] else "(cargá maltas en la receta para ver el reparto mash/lavado)",
        ]))

    def _strike_water(self):
        """Temperatura del agua de empaste (Strike Water) según Palmer.

        T_agua = (0.41 / ratio) x (T_macerado - T_grano) + T_macerado
        """
        objetivo = self._eq_valor("temp_macerado", 66.0)
        grano = self._eq_valor("temp_grano", 20.0)
        ratio = self._eq_valor("relacion_empaste", 3.0) or 3.0
        perdida = self._eq_valor("perdida_termica", 0.0)
        return (0.41 / ratio) * (objetivo - grano) + objetivo + perdida

    def _eq_aplicar_strike(self):
        """Vuelca el Strike Water calculado en el campo del perfil."""
        entrada = getattr(self, "_eq_extra_entries", {}).get("strike_water")
        if entrada is None:
            return
        entrada.delete(0, "end")
        entrada.insert(0, format_num(round(self._strike_water(), 1)))
        self._cargar_balance_teorico()
        mb.showinfo("Strike Water", f"Temperatura del agua de empaste: "
                                    f"{format_num(round(self._strike_water(), 1))} °C")

    def _eq_editar_parametros(self):
        """Lleva al usuario a la pestaña donde se editan los parámetros del equipo."""
        try:
            self.subtabs_equipos.set(list(self.subtabs_equipos._tab_dict.keys())[0])
        except Exception:
            pass
        mb.showinfo("Editar Parámetros",
                    "Los parámetros del perfil se editan en 'Perfiles de Equipamiento'.\n"
                    "Cambiá los valores y usá 'Guardar Configuración'.")

    def _eq_guardar_valores_por_defecto(self):
        """Guarda el perfil activo como valores por defecto de la app."""
        for clave in ("batch_volume", "perdidas_l", "evaporacion_l_h", "temp_macerado",
                      "relacion_empaste", "absorcion_grano", "espacio_muerto"):
            self.db.set_setting(f"equipo_{clave}", self._eq_valor(clave, 0.0))
        mb.showinfo("Valores por Defecto",
                    "El perfil activo quedó guardado como valores por defecto.")

    def _eq_restaurar_brewomatic(self):
        """Vuelve a los valores típicos de Brew-o-Matic."""
        valores = {"batch_volume": 20.0, "perdidas_l": 4.0, "evaporacion_l_h": 3.2,
                   "temp_macerado": 66.0, "relacion_empaste": 3.0, "absorcion_grano": 1.0,
                   "espacio_muerto": 3.0, "perdida_turb_enfriador": 4.0,
                   "duracion_prehervor": 30.0, "duracion_enfriado": 40.0}
        for clave, valor in valores.items():
            entrada = self._eq_entries.get(clave) or self._eq_extra_entries.get(clave)
            if entrada is not None:
                entrada.delete(0, "end")
                entrada.insert(0, format_num(valor))
        self._cargar_balance_teorico()
        mb.showinfo("Valores por Defecto", "Restaurados los valores típicos de Brew-o-Matic.")

    def _eq_calibrar_olla(self, entrada_medido, entrada_marcado, entrada_muerto):
        """Calibración de ollas: ajusta volumen de olla y espacio muerto medidos."""
        try:
            medido = float(str(entrada_medido.get()).replace(",", "."))
            marcado = float(str(entrada_marcado.get()).replace(",", "."))
            muerto = float(str(entrada_muerto.get()).replace(",", ".") or 0)
        except ValueError:
            mb.showwarning("Calibración", "Completá los tres valores medidos."); return
        if marcado <= 0:
            mb.showwarning("Calibración", "El volumen marcado tiene que ser mayor a 0."); return
        correccion = medido / marcado
        for clave, valor in (("kettle_volume", medido), ("espacio_muerto", muerto)):
            entrada = self._eq_entries.get(clave) or self._eq_extra_entries.get(clave)
            if entrada is not None:
                entrada.delete(0, "end")
                entrada.insert(0, format_num(valor))
        self._cargar_balance_teorico()
        mb.showinfo("Calibración de Ollas",
                    f"Volumen real de la olla: {format_num(medido)} L\n"
                    f"Espacio muerto: {format_num(muerto)} L\n"
                    f"Corrección de la escala: x{correccion:.3f}")

    def _eq_exportar_beerxml(self):
        """Exporta el perfil de equipo activo como BeerXML."""
        from export_engine import ET
        try:
            equipo = self._eq_recolectar() if hasattr(self, "_eq_recolectar") else {
                "name": self._eq_entries["name"].get() or "Equipo",
                "batch_volume": self._eq_valor("batch_volume", 20.0),
                "kettle_volume": self._eq_valor("kettle_volume", 0.0),
                "perdidas_l": self._eq_valor("perdidas_l", 0.0),
                "evaporacion_l_h": self._eq_valor("evaporacion_l_h", 0.0),
                "eficiencia": self._eq_valor("eficiencia_pct", 75.0),
                "temp_macerado": self._eq_valor("temp_macerado", 66.0),
            }
        except Exception as e:
            logger.error(f"_eq_exportar_beerxml: {e}")
            mb.showerror("BeerXML", "No se pudo leer el perfil de equipo."); return
        ruta = filedialog.asksaveasfilename(defaultextension=".xml",
                                            filetypes=[("BeerXML", "*.xml")],
                                            title="Exportar equipo",
                                            initialfile=equipo.get("name", "equipo"))
        if not ruta:
            return
        try:
            raiz = ET.Element("EQUIPMENTS")
            nodo = ET.SubElement(raiz, "EQUIPMENT")
            ET.SubElement(nodo, "NAME").text = str(equipo.get("name", "Equipo"))
            ET.SubElement(nodo, "VERSION").text = "1"
            ET.SubElement(nodo, "BATCH_SIZE").text = str(equipo.get("batch_volume", 20.0))
            ET.SubElement(nodo, "BOIL_SIZE").text = str(equipo.get("kettle_volume", 0.0))
            ET.SubElement(nodo, "EVAP_RATE").text = str(equipo.get("evaporacion_l_h", 0.0))
            ET.SubElement(nodo, "TRUB_CHILLER_LOSS").text = str(equipo.get("perdidas_l", 0.0))
            ET.SubElement(nodo, "EFFICIENCY").text = str(equipo.get("eficiencia", 75.0))
            ET.ElementTree(raiz).write(ruta, encoding="utf-8", xml_declaration=True)
            mb.showinfo("BeerXML", f"Perfil de equipo exportado:\n{ruta}")
        except Exception as e:
            logger.error(f"exportar equipo: {e}")
            mb.showerror("BeerXML", f"No se pudo exportar.\n{e}")

    def _eq_importar_beerxml(self):
        """Trae un perfil de equipo desde un BeerXML."""
        from importador import leer_equipo
        ruta = filedialog.askopenfilename(title="Importar equipo desde BeerXML",
                                          filetypes=[("BeerXML", "*.xml"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            equipo = leer_equipo(ruta)
        except Exception as e:
            logger.error(f"_eq_importar_beerxml: {e}")
            mb.showerror("BeerXML", f"No se pudo leer el archivo.\n{e}"); return
        if not equipo:
            mb.showwarning("BeerXML", "El archivo no tiene un bloque EQUIPMENT."); return
        self._eq_aplicar(equipo)
        mb.showinfo("BeerXML", f"Equipo importado: {equipo.get('name', '')}")

    def _eq_importar_brewomatic(self):
        """Trae los parámetros de equipo de una receta de Brew-o-Matic."""
        entrada = simpledialog.askstring(
            "Importar Brewomatic",
            "Pegá la dirección (o el ID) de la receta de Brew-o-Matic\n"
            "y tomo de ahí los datos del equipo:")
        if not entrada:
            return
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "herramientas"))
            from importar_brewomatic import descargar, _id_de
            datos = descargar(_id_de(entrada))
        except Exception as e:
            logger.error(f"_eq_importar_brewomatic: {e}")
            mb.showerror("Brewomatic", f"No se pudo descargar la receta.\n{e}"); return

        def num(clave, por_defecto=None):
            try:
                return float(datos.get(clave))
            except (TypeError, ValueError):
                return por_defecto

        equipo = {
            "name": f"Brewomatic · {datos.get('NAME', 'receta')[:28]}",
            "batch_volume": num("BATCH_SIZE", 20.0),
            "kettle_volume": num("BOIL_SIZE", 0.0) or 0.0,
            "eficiencia": num("EFFICIENCY", 75.0),
            "evaporacion_l_h": (num("PercentEvap", 0.0) or 0.0) / 100.0 * (num("BATCH_SIZE", 20.0) or 20.0),
            "perdidas_l": num("TrubChillerLosses", 0.0) or 0.0,
            "temp_macerado": 66.0,
        }
        extras = {"absorcion_grano": num("GrainAbsorbtion", None),
                  "relacion_empaste": num("WatertoGrainRatio", None)}
        self._eq_aplicar(equipo, extras)
        detalle = "\n".join(f"· {k}: {format_num(v)}" for k, v in equipo.items() if k != "name")
        mb.showinfo("Importar Brewomatic", f"{equipo['name']}\n\n{detalle}")

    def _eq_aplicar(self, equipo, extras=None):
        """Vuelca un perfil importado en los campos del formulario."""
        equivalencias = {"name": "name", "batch_volume": "batch_volume",
                         "kettle_volume": "kettle_volume", "perdidas_l": "perdidas_l",
                         "evaporacion_l_h": "evaporacion_l_h", "eficiencia": "eficiencia_pct",
                         "temp_macerado": "temp_macerado"}
        for clave_origen, clave_destino in equivalencias.items():
            valor = equipo.get(clave_origen)
            if valor in (None, "", 0) and clave_destino != "name":
                continue
            entrada = self._eq_entries.get(clave_destino)
            if entrada is not None:
                entrada.delete(0, "end")
                entrada.insert(0, valor if clave_destino == "name" else format_num(valor))
        for clave, valor in (extras or {}).items():
            if valor is None:
                continue
            entrada = self._eq_extra_entries.get(clave)
            if entrada is not None:
                entrada.delete(0, "end")
                entrada.insert(0, format_num(valor))
        self._cargar_balance_teorico()

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
            ctk.CTkButton(f, text="✏️", width=34, fg_color="#3A7EBF", hover_color="#1F538D",
                          command=lambda n=eq['name']: self._eq_editar(n)).pack(side="right", padx=3)
            ctk.CTkButton(f, text="🗑️", width=34, fg_color="#DC2626", hover_color="#B91C1C",
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
    def _configurar_estilo_ttk(self):
        if getattr(self, "_ttk_style_listo", False):
            return
        style = ttk.Style()
        style.theme_use("clam")
        for nombre in ("Insumos.Treeview", "Inventario.Treeview"):
            style.configure(nombre, background="#24242C", fieldbackground="#24242C",
                            foreground="#E4E1EA", borderwidth=0, rowheight=34,
                            font=("Segoe UI", 11))
            style.configure(f"{nombre}.Heading", background="#24242C", foreground="#9CA3AF",
                            font=("Segoe UI", 10, "bold"), borderwidth=0, relief="flat")
            style.map(nombre, background=[("selected", "#1F538D")],
                     foreground=[("selected", "#FFFFFF")])
            style.map(f"{nombre}.Heading", background=[("active", "#24242C")])
        style.layout("Insumos.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.layout("Inventario.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        self._ttk_style_listo = True

    def _alternar_filas(self, tabla, indice):
        """Devuelve el tag de fondo alternado del diseño (#24242C / #282834)."""
        return "fila_par" if indice % 2 == 0 else "fila_impar"

    def _preparar_filas_alternadas(self, tabla):
        """Configura los dos fondos alternados (el diseño los usa en sus tablas)."""
        tabla.tag_configure("fila_par", background="#24242C")
        tabla.tag_configure("fila_impar", background="#282834")

    def setup_tab_insumos(self):
        self._configurar_estilo_ttk()
        self.tab_insumos.grid_columnconfigure(0, weight=1)
        self.tab_insumos.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self.tab_insumos, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)

        # ── Header: pestañas por tipo + buscador + acciones ──
        header = ctk.CTkFrame(scroll, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(15, 8), sticky="ew")
        self.seg_ing_filtro = ctk.CTkSegmentedButton(
            header, values=["Todos"] + TIPOS_INVENTARIO,
            command=lambda _sel=None: self.cargar_lista_insumos())
        self.seg_ing_filtro.set("Todos")
        self.seg_ing_filtro.pack(anchor="w", pady=(0, 8))
        # Filtros del diseño: productor/origen y familia de grano
        fila_filtros = ctk.CTkFrame(header, fg_color="transparent")
        fila_filtros.pack(fill="x", pady=(0, 6))
        self.combo_ing_productor = ctk.CTkComboBox(
            fila_filtros, values=["Todos los productores (Uma Malta, Weyermann, Castle, BestMalz...)"]
                                   + get_productores(), width=330,
            command=lambda _v=None: self.cargar_lista_insumos())
        self.combo_ing_productor.set("Todos los productores (Uma Malta, Weyermann, Castle, BestMalz...)")
        self.combo_ing_productor.pack(side="left")
        # Opciones del filtro con el texto exacto del mockup -> categoría real
        self._familias_diseño = {
            "Tipo: Malta Base (Aporte enzimático principal)": "Maltas Base",
            "Tipo: Malta Especial (Sabor y color)": "Maltas Especiales / Caramelo",
            "Tipo: Grano Tostado (Cebada negra, chocolate)": "Granos Tostados",
            "Tipo: Adjunto no malteado (Copos, trigo crudo)": "Adjuntos y Copos"}
        self.combo_ing_familia = ctk.CTkComboBox(
            fila_filtros, values=["Tipo: Todos los granos"] + list(self._familias_diseño), width=330,
            command=lambda _v=None: self.cargar_lista_insumos())
        self.combo_ing_familia.set("Tipo: Todos los granos")
        self.combo_ing_familia.pack(side="left", padx=(8, 0))
        fila_acciones = ctk.CTkFrame(header, fg_color="transparent")
        fila_acciones.pack(fill="x")
        self.entry_ing_buscar = ctk.CTkEntry(fila_acciones, placeholder_text="🔍 Buscar insumo por nombre...", width=280)
        self.entry_ing_buscar.pack(side="left")
        self.entry_ing_buscar.bind("<KeyRelease>", lambda e: self.cargar_lista_insumos())
        ctk.CTkButton(fila_acciones, text="+ Agregar Insumo", width=140, command=self._ing_nuevo,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="right", padx=(6, 0))
        ctk.CTkButton(fila_acciones, text="📥 Exportar CSV", width=130, command=self.exportar_insumos_csv,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="right", padx=6)
        ctk.CTkButton(fila_acciones, text="📂 Importar BeerXML", width=150,
                      command=self.importar_insumos_beerxml,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="right", padx=6)

        # ── Cuerpo: maestro (tabla) + detalle (ficha técnica) ──
        cuerpo = ctk.CTkFrame(scroll, fg_color="transparent")
        cuerpo.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        cuerpo.grid_columnconfigure(0, weight=0, minsize=220)   # rail del diseño (220-260)
        cuerpo.grid_columnconfigure(1, weight=7)                # tabla
        cuerpo.grid_columnconfigure(2, weight=5)                # ficha

        # ── Rail izquierdo: categorías con contador (como el diseño) ──
        rail = ctk.CTkFrame(cuerpo, width=220)
        rail.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        ctk.CTkLabel(rail, text="📚 Biblioteca de Insumos",
                     font=ctk.CTkFont(size=13, weight="bold"), wraplength=170, justify="left"
                     ).pack(anchor="w", padx=12, pady=(12, 8))
        self._rail_insumos = {}
        nombres_rail = {"Malta": "🌾 Maltas / Granos", "Lúpulo": "🌿 Lúpulos",
                        "Levadura": "🧫 Levaduras", "Misceláneo": "⚗️ Misceláneos / Químicos"}
        self._nombres_rail = nombres_rail
        for tipo, icono in (("Malta", "🌾"), ("Lúpulo", "🌿"),
                            ("Levadura", "🧫"), ("Misceláneo", "⚗️")):
            boton = ctk.CTkButton(rail, text=f"{nombres_rail[tipo]}  0", anchor="w", height=30,
                                  fg_color="transparent", hover_color="#2B2B36",
                                  command=lambda t=tipo: self._filtrar_por_rail(t))
            boton.pack(fill="x", padx=8, pady=1)
            self._rail_insumos[tipo] = boton
        ctk.CTkFrame(rail, height=1, fg_color="#3F3F50").pack(fill="x", padx=10, pady=8)
        self.lbl_rail_resumen = ctk.CTkLabel(rail, text="", justify="left",
                                             text_color="#9CA3AF", font=ctk.CTkFont(size=10))
        self.lbl_rail_resumen.pack(anchor="w", padx=12)

        frame_lista = ctk.CTkFrame(cuerpo)
        frame_lista.grid(row=0, column=1, padx=(0, 8), sticky="nsew")
        cab_lista = ctk.CTkFrame(frame_lista, fg_color="transparent")
        cab_lista.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(cab_lista, text="📋 Catálogo de Granos & Maltas",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.lbl_ing_total = ctk.CTkLabel(cab_lista, text="", text_color="#9CA3AF")
        self.lbl_ing_total.pack(side="left", padx=10)
        ctk.CTkLabel(cab_lista, text="·  Sincronizado  ·  Haga clic para editar",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(side="left")
        # Columnas del mockup: Potencial / Color / Uso / % Máx / Recetas
        cols = ("origen", "potencial", "color", "uso", "pct_max", "recetas")
        self.tree_insumos = ttk.Treeview(frame_lista, columns=cols, show="tree headings",
                                         style="Insumos.Treeview", height=16, selectmode="browse")
        self.tree_insumos.heading("#0", text="Insumo / Nombre Comercial")
        self.tree_insumos.heading("origen", text="Origen / Maltería")
        self.tree_insumos.heading("potencial", text="Potencial (SG)")
        self.tree_insumos.heading("color", text="Color SRM")
        self.tree_insumos.heading("uso", text="Uso")
        self.tree_insumos.heading("pct_max", text="% Max")
        self.tree_insumos.heading("recetas", text="Recetas")
        self.tree_insumos.column("#0", width=200, anchor="w")
        self.tree_insumos.column("origen", width=150, anchor="w")
        self.tree_insumos.column("potencial", width=95, anchor="center")
        self.tree_insumos.column("color", width=80, anchor="center")
        self.tree_insumos.column("uso", width=105, anchor="w")
        self.tree_insumos.column("pct_max", width=60, anchor="center")
        self.tree_insumos.column("recetas", width=65, anchor="center")
        self._preparar_filas_alternadas(self.tree_insumos)
        self.tree_insumos.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.tree_insumos.bind("<<TreeviewSelect>>", self._ing_on_select)

        # Pie: "Mostrando X a Y de N" con ‹ › (como el diseño)
        pie = ctk.CTkFrame(frame_lista, fg_color="transparent")
        pie.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(pie, text="‹", width=28, height=24, command=lambda: self._ing_pagina_mover(-1),
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left")
        ctk.CTkButton(pie, text="›", width=28, height=24, command=lambda: self._ing_pagina_mover(1),
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left", padx=4)
        self.lbl_ing_pagina = ctk.CTkLabel(pie, text="", text_color="#9CA3AF",
                                           font=ctk.CTkFont(size=11))
        self.lbl_ing_pagina.pack(side="left", padx=6)

        # Detalle — Ficha Técnica (reusa los mismos campos, ahora en el panel derecho)
        frame_ficha = ctk.CTkFrame(cuerpo)
        frame_ficha.grid(row=0, column=2, padx=(8, 0), sticky="nsew")
        frame_ficha.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.lbl_ficha_ing = ctk.CTkLabel(frame_ficha, text="🧪 Ficha Técnica: nuevo insumo",
                                          font=ctk.CTkFont(size=15, weight="bold"),
                                          wraplength=320, justify="left")
        self.lbl_ficha_ing.grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(10, 8))
        ctk.CTkLabel(frame_ficha, text="1. Información General y Fabricante",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#9CA3AF"
                     ).grid(row=1, column=0, columnspan=4, sticky="w", padx=12, pady=(6, 2))
        ctk.CTkLabel(frame_ficha, text="Clasificación / Tipo:").grid(row=2, column=0, sticky="w", padx=(12, 4), pady=3)
        self.combo_ing_tipo = ctk.CTkComboBox(frame_ficha, values=TIPOS_INVENTARIO, width=110)
        self.combo_ing_tipo.set("Malta")
        self.combo_ing_tipo.grid(row=2, column=1, sticky="ew", padx=4, pady=3)
        ctk.CTkLabel(frame_ficha, text="Nombre Comercial del Insumo:").grid(row=2, column=2, sticky="w", padx=4, pady=3)
        self.e_ing_nombre = ctk.CTkEntry(frame_ficha, placeholder_text="Ej: Mi Malta Local")
        self.e_ing_nombre.grid(row=2, column=3, sticky="ew", padx=(4, 12), pady=3)
        campos = [("origin", "Productor / Maltería"), ("supplier", "País de Origen / Proveedor"),
                  ("category", "Clasificación / Tipo de Grano"), ("color", "Color (SRM)"),
                  ("extract", "Potencial SG"), ("ppg", "PPG"),
                  ("yield_pct", "Rend. %"), ("diastatic", "Poder Diastásico"), ("alpha", "Alpha Ac. %"),
                  ("form", "Modo / Formato"), ("attenuation", "Atenuación %"), ("abv_tolerance", "Tol. ABV"),
                  ("temp_range", "Rango de Temp."),
                  ("dbfg", "DBFG (Base Fina) %"), ("humedad", "Humedad %"),
                  ("proteina", "Proteína Total %"),
                  ("uso", "Uso Recomendado"), ("pct_max", "% Máximo en Grist"),
                  ("maceracion", "Maceración"),
                  ("notes", "Notas de Cata y Perfil Sensorial del Proveedor")]
        self._ing_entries = {}
        self._ing_combos = {}
        # "Clasificación / Tipo de Grano" es una lista con las familias del catálogo
        CAMPOS_COMBO_INSUMO["category"] = get_categorias_malta()
        fila = 3
        for i, (clave, etiqueta) in enumerate(campos):
            col = (i % 2) * 2
            if i > 0 and i % 2 == 0:
                fila += 1
            ctk.CTkLabel(frame_ficha, text=f"{etiqueta}:").grid(row=fila, column=col, sticky="w",
                                                                padx=(12 if col == 0 else 4, 4), pady=3)
            if clave in CAMPOS_COMBO_INSUMO:      # listas del diseño (uso, maceración)
                e = ctk.CTkComboBox(frame_ficha, values=CAMPOS_COMBO_INSUMO[clave], width=100)
                e.set(CAMPOS_COMBO_INSUMO[clave][0])
                self._ing_combos[clave] = e
            else:
                e = ctk.CTkEntry(frame_ficha, width=100)
                self._ing_entries[clave] = e
            e.grid(row=fila, column=col + 1, sticky="ew", padx=(4, 12 if col == 2 else 4), pady=3)
        fila += 1
        ctk.CTkLabel(frame_ficha, text="2. Parámetros Físico-Químicos de Elaboración",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#9CA3AF"
                     ).grid(row=fila, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 2))
        fila += 1
        self.lbl_ing_color_estimado = ctk.CTkLabel(
            frame_ficha, text="Color Estimado: —", text_color="#D97706",
            font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_ing_color_estimado.grid(row=fila, column=0, columnspan=2, sticky="w",
                                         padx=12, pady=(0, 2))
        fila += 1
        ctk.CTkLabel(frame_ficha, text="3. Reglas de Dosificación en Olla",
                     font=ctk.CTkFont(size=11, weight="bold"), text_color="#9CA3AF"
                     ).grid(row=fila, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 2))
        fila += 1
        frame_botones_ficha = ctk.CTkFrame(frame_ficha, fg_color="transparent")
        frame_botones_ficha.grid(row=fila, column=0, columnspan=4, padx=12, pady=(8, 4), sticky="ew")
        ctk.CTkButton(frame_botones_ficha, text="💾 Guardar Cambios", command=self._ing_guardar,
                      fg_color="#22C55E", hover_color="#16A34A").pack(side="left")
        ctk.CTkButton(frame_botones_ficha, text="🗑️ Eliminar", command=self._ing_borrar_actual,
                      fg_color="#DC2626", hover_color="#B91C1C").pack(side="left", padx=6)
        ctk.CTkButton(frame_botones_ficha, text="🧹 Limpiar", command=self._ing_nuevo,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left")
        ctk.CTkButton(frame_botones_ficha, text="📄 Duplicar", command=self._ing_duplicar,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="left", padx=6)
        fila += 1
        ctk.CTkLabel(frame_ficha, text="Completá solo los campos que apliquen al tipo elegido.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)
                     ).grid(row=fila, column=0, columnspan=4, sticky="w", padx=12, pady=(0, 10))

        self._ing_actual = None
        self.cargar_lista_insumos()

    def setup_tab_inventario_tab(self):
        """Pestaña Inventario, separada de Insumos (como en el diseño de Stitch)."""
        self._configurar_estilo_ttk()
        self.tab_inventario.grid_columnconfigure(0, weight=1)
        self.tab_inventario.grid_rowconfigure(0, weight=1)
        scroll = ctk.CTkScrollableFrame(self.tab_inventario, fg_color="transparent")
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        self.setup_tab_inventario(scroll)

    # ── Catálogo: rail de categorías, paginación, ID y duplicar ──
    def _filtrar_por_rail(self, tipo):
        """Al hacer clic en una categoría del rail se filtra la tabla."""
        actual = self.seg_ing_filtro.get()
        self.seg_ing_filtro.set("Todos" if actual == tipo else tipo)
        self._ing_pagina = 0
        self.cargar_lista_insumos()

    def _ing_pagina_mover(self, paso):
        self._ing_pagina = max(0, getattr(self, "_ing_pagina", 0) + paso)
        self.cargar_lista_insumos()

    def _actualizar_color_estimado(self, ing):
        """Muestra el color del insumo en SRM y EBC (sección 2 de la ficha del diseño)."""
        if not hasattr(self, "lbl_ing_color_estimado"):
            return
        color = ing.get("color") or 0
        if not color:
            self.lbl_ing_color_estimado.configure(text="Color Estimado: —")
            return
        try:
            ebc = BrewEngine.srm_a_ebc(color)
        except Exception:
            ebc = color * 1.97
        self.lbl_ing_color_estimado.configure(
            text=f"Color Estimado: {format_num(color)} SRM / {format_num(round(ebc, 1))} EBC")

    def _sku_insumo(self, ing):
        """ID del insumo como en el diseño: INS-MLT-001, INS-ADJ-004, INS-HOP-012…

        El prefijo depende del tipo y, en las maltas, de su familia (los adjuntos
        llevan ADJ). El número es el id de la base: estable y sin repetidos.
        """
        prefijos = {"Malta": "MLT", "Lúpulo": "HOP", "Levadura": "YST", "Misceláneo": "MSC"}
        if ing.get("type") == "Malta" and (ing.get("category") or "") == CATEGORIA_ADJUNTO:
            prefijo = "ADJ"
        else:
            prefijo = prefijos.get(ing.get("type"), "INS")
        return f"INS-{prefijo}-{int(ing.get('id') or 0):03d}"

    def _ing_duplicar(self):
        """Duplica el insumo elegido (como el botón del diseño)."""
        if not self._ing_actual:
            mb.showinfo("Duplicar insumo", "Elegí un insumo de la lista primero."); return
        tipo, nombre = self._ing_actual
        datos = datos_ficha_insumo(self.db, tipo, nombre)
        if not datos:
            return
        copia = f"{nombre} (copia)"
        campos = {k: v for k, v in datos.items()
                  if k not in ("id", "type", "name") and v not in (None, "")}
        self.db.add_ingredient(tipo, copia, **campos)
        self.cargar_lista_insumos()
        self.tree_insumos.selection_set(f"{tipo}|{copia}")
        self._ing_editar(tipo, copia)
        mb.showinfo("Catálogo", f"Insumo duplicado:\n{tipo} · {copia}")

    def _actualizar_rail_insumos(self, totales):
        """Contadores por categoría y resumen del rail (como el diseño)."""
        if not hasattr(self, "_rail_insumos"):
            return
        for tipo, boton in self._rail_insumos.items():
            nombre = getattr(self, "_nombres_rail", {}).get(tipo, tipo)
            boton.configure(text=f"{nombre}  {totales.get(tipo, 0)}")
        if hasattr(self, "lbl_rail_resumen"):
            self.lbl_rail_resumen.configure(
                text=f"Maltas registradas: {totales.get('Malta', 0)}\n"
                     f"Lúpulos: {totales.get('Lúpulo', 0)}\n"
                     f"Levaduras: {totales.get('Levadura', 0)}\n"
                     f"Misceláneos: {totales.get('Misceláneo', 0)}\n"
                     f"Total: {sum(totales.values())} insumos")

    # ==========================================
    # BARRA DE MENÚ (como el diseño: Archivo · Herramientas · Ayuda)
    # ==========================================
    def _crear_barra_menu(self):
        """Barra de menú del diseño de Stitch.

        Reemplaza el desplegable propio por los tres menús que muestra el mockup,
        con las mismas opciones y en el mismo orden.
        """
        import tkinter as tk
        estilo = dict(background="#24242C", foreground="#E4E1EA", activebackground="#3A7EBF",
                      activeforeground="#FFFFFF", bd=0, relief="flat")
        barra = tk.Menu(self, **estilo)

        archivo = tk.Menu(barra, tearoff=0, **estilo)
        archivo.add_command(label="📂  Importar JSON", command=self.importar_json_ui)
        archivo.add_command(label="💾  Exportar PDF", command=self.exportar_pdf_ui)
        archivo.add_command(label="💾  Exportar BeerXML", command=self.exportar_xml_ui)
        archivo.add_separator()
        archivo.add_command(label="🚪  Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=archivo)

        herramientas = tk.Menu(barra, tearoff=0, **estilo)
        herramientas.add_command(label="🔄  Buscar recetas nuevas", command=self.actualizar_recetas_web)
        herramientas.add_command(label="🌐  Recetas de la Comunidad", command=self.buscar_recetas_comunidad_ui)
        herramientas.add_separator()
        herramientas.add_command(label="⬆️  Comprobar actualizaciones", command=self.comprobar_actualizaciones)
        herramientas.add_command(label="🧾  Ver log", command=self.mostrar_log)
        barra.add_cascade(label="Herramientas", menu=herramientas)

        ayuda = tk.Menu(barra, tearoff=0, **estilo)
        ayuda.add_command(label="❓  Manual de Usuario", command=self.mostrar_ayuda)
        ayuda.add_command(label="ℹ️  Acerca de Cervecera VGB", command=self.mostrar_acerca)
        barra.add_cascade(label="Ayuda", menu=ayuda)

        self.configure(menu=barra)
        self._barra_menu = barra

    def mostrar_acerca(self):
        """Ventana "Acerca de Cervecera VGB" (opción del menú Ayuda del diseño)."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Acerca de Cervecera VGB")
        ventana.geometry("460x380")
        ventana.transient(self)
        ctk.CTkLabel(ventana, text="🍺  Cervecera VGB", font=ctk.CTkFont(size=20, weight="bold")
                     ).pack(pady=(20, 2))
        ctk.CTkLabel(ventana, text="Craft Brewing Studio", text_color="#9CA3AF"
                     ).pack()
        ctk.CTkLabel(ventana, text=f"Versión {APP_VERSION}", text_color="#9CA3AF",
                     font=ctk.CTkFont(size=12)).pack(pady=(2, 12))
        texto = (
            "Asistente cervecero para diseñar recetas, calcular y guardar tu inventario.\n"
            "Funciona sin conexión y sin suscripciones.\n\n"
            "Fórmulas: Tinseth y Rager (IBU) · Morey (color) · Palmer y Kai Troester (pH)\n"
            "Estilos: BJCP 2021 · Corrección por altitud (Córdoba)\n\n"
            "Recetas de referencia: Brew-o-Matic (Lautaro Cozzani / Somos Cerveceros)\n\n"
            "By SaintWick · nicoweb45@proton.me"
        )
        ctk.CTkLabel(ventana, text=texto, justify="left", wraplength=400,
                     font=ctk.CTkFont(size=11), text_color="#C1C7D2").pack(padx=20)
        ctk.CTkButton(ventana, text="Cerrar", command=ventana.destroy,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(pady=18)

    def cargar_lista_insumos(self):
        for item in self.tree_insumos.get_children():
            self.tree_insumos.delete(item)
        filtro = self.seg_ing_filtro.get() if hasattr(self, "seg_ing_filtro") else "Todos"
        busqueda = self.entry_ing_buscar.get().strip().lower() if hasattr(self, "entry_ing_buscar") else ""
        SIN_FILTRO = "Todos los productores (Uma Malta, Weyermann, Castle, BestMalz...)"
        productor = (self.combo_ing_productor.get() if hasattr(self, "combo_ing_productor")
                     else SIN_FILTRO)
        familia = (self.combo_ing_familia.get() if hasattr(self, "combo_ing_familia")
                   else "Tipo: Todos los granos")
        recetas_por_insumo = self.db.contar_recetas_por_insumo()
        # Contadores del rail: totales por tipo, sin importar los filtros
        todos = self.db.get_ingredients()
        self._actualizar_rail_insumos({t: sum(1 for i in todos if i["type"] == t)
                                       for t in ("Malta", "Lúpulo", "Levadura", "Misceláneo")})

        # Primero filtramos, después paginamos
        filtrados = []
        for ing in todos:
            if filtro != "Todos" and ing["type"] != filtro:
                continue
            if busqueda and busqueda not in ing["name"].lower():
                continue
            # Vale tanto la etiqueta larga del diseño como la corta ("Todos los productores")
            if not productor.startswith("Todos los productores") and (ing.get("origin") or "") != productor:
                continue
            sin_filtro_familia = (familia.startswith("Tipo: Todos los granos")
                                  or familia.strip() == "Todos los granos")
            # la etiqueta del diseño lleva la descripción: se traduce a la categoría real
            categoria_buscada = getattr(self, "_familias_diseño", {}).get(familia, familia)
            if not sin_filtro_familia and (ing.get("category") or "") != categoria_buscada:
                continue
            filtrados.append(ing)

        total = len(filtrados)
        tamanio = getattr(self, "_ing_por_pagina", 8)
        self._ing_pagina = min(getattr(self, "_ing_pagina", 0),
                               max(0, (total - 1) // tamanio))
        desde = self._ing_pagina * tamanio
        pagina = filtrados[desde:desde + tamanio]

        for indice_fila, ing in enumerate(pagina):
            origen = ing.get("origin") or ing.get("supplier") or "—"
            # Potencial y Color: cambian de significado según el tipo de insumo
            if ing["type"] == "Malta":
                potencial = f"1.{int(ing['extract']):03d}" if ing.get("extract") else "—"
                color = f"{format_num(ing['color'])} SRM" if ing.get("color") else "—"
            elif ing["type"] == "Lúpulo":
                potencial = f"{format_num(ing['alpha'])}% AA" if ing.get("alpha") else "—"
                color = ing.get("form") or "—"
            elif ing["type"] == "Levadura":
                potencial = f"{format_num(ing['attenuation'])}% Aten." if ing.get("attenuation") else "—"
                color = ing.get("temp_range") or "—"
            else:
                potencial = ing.get("category") or "—"
                color = "—"
            pct = f"{format_num(ing['pct_max'])}%" if ing.get("pct_max") else "—"
            usos = recetas_por_insumo.get(ing["name"].lower(), 0)
            self.tree_insumos.insert("", "end", iid=f"{ing['type']}|{ing['name']}",
                                     text=ing["name"],
                                     values=(origen, potencial, color, ing.get("uso") or "—",
                                             pct, f"{usos} receta{'s' if usos != 1 else ''}" if usos else "—"),
                                     tags=(self._alternar_filas(self.tree_insumos, indice_fila),))
        if hasattr(self, "lbl_ing_total"):
            self.lbl_ing_total.configure(text=f"{total} registro{'s' if total != 1 else ''}")
        if hasattr(self, "lbl_ing_pagina"):
            if total:
                nombre = {"Malta": "insumos de maltería", "Lúpulo": "lúpulos",
                          "Levadura": "levaduras", "Misceláneo": "misceláneos"}.get(
                              filtro, "insumos")
                self.lbl_ing_pagina.configure(
                    text=f"Mostrando {desde + 1} a {min(desde + tamanio, total)} de "
                         f"{total} {nombre}  ·  Página {self._ing_pagina + 1} "
                         f"de {max(1, -(-total // tamanio))}")
            else:
                self.lbl_ing_pagina.configure(text="Sin insumos que coincidan")

    def _ing_on_select(self, _evento=None):
        seleccion = self.tree_insumos.selection()
        if not seleccion:
            return
        tipo, nombre = seleccion[0].split("|", 1)
        self._ing_editar(tipo, nombre)

    def _ing_nuevo(self):
        self._ing_actual = None
        self.tree_insumos.selection_remove(self.tree_insumos.selection())
        self.combo_ing_tipo.set(self.seg_ing_filtro.get() if self.seg_ing_filtro.get() != "Todos" else "Malta")
        self.e_ing_nombre.delete(0, "end")
        for e in self._ing_entries.values():
            e.delete(0, "end")
        for clave, combo in getattr(self, "_ing_combos", {}).items():
            combo.set(CAMPOS_COMBO_INSUMO[clave][0])
        self.lbl_ficha_ing.configure(text="🧪 Ficha Técnica: nuevo insumo")

    def _ing_limpiar(self):
        self._ing_nuevo()

    def _ing_editar(self, tipo, nombre):
        ing = datos_ficha_insumo(self.db, tipo, nombre)
        self._ing_actual = (tipo, nombre)
        self.combo_ing_tipo.set(tipo)
        self.e_ing_nombre.delete(0, "end"); self.e_ing_nombre.insert(0, nombre)
        for clave, e in self._ing_entries.items():
            e.delete(0, "end")
            v = ing.get(clave)
            if v not in (None, "", 0):
                e.insert(0, format_num(v))
        for clave, combo in getattr(self, "_ing_combos", {}).items():
            opciones = CAMPOS_COMBO_INSUMO[clave]
            valor_guardado = ing.get(clave) or opciones[0]
            combo.set(valor_guardado if valor_guardado in opciones else opciones[0])
        self._actualizar_color_estimado(ing)
        sku = self._sku_insumo({"type": tipo, "id": ing.get("id"), "category": ing.get("category")})
        self.lbl_ficha_ing.configure(text=f"🧪 Ficha Técnica: {nombre}\n"
                                          f"Activo en Catálogo  ·  ID: {sku}")

    def _ing_borrar_actual(self):
        if not self._ing_actual:
            mb.showinfo("Eliminar insumo", "Elegí un insumo de la lista primero."); return
        self._ing_borrar(*self._ing_actual)

    def _ing_borrar(self, tipo, nombre):
        if mb.askyesno("Eliminar insumo", f"¿Eliminar '{nombre}' ({tipo}) del catálogo?"):
            self.db.delete_ingredient(tipo, nombre)
            self._ing_nuevo()
            self.cargar_lista_insumos()

    def importar_insumos_beerxml(self):
        """Trae insumos desde un archivo BeerXML (Brewfather, BeerSmith, Brew-o-Matic…)."""
        from importador import leer_insumos, guardar_insumos
        ruta = filedialog.askopenfilename(title="Importar insumos desde BeerXML",
                                          filetypes=[("BeerXML", "*.xml"), ("Todos", "*.*")])
        if not ruta:
            return
        try:
            insumos = leer_insumos(ruta)
        except Exception as e:
            logger.error(f"importar_insumos_beerxml: {e}")
            mb.showerror("Importar BeerXML", f"No se pudo leer el archivo.\n{e}")
            return
        if not insumos:
            mb.showwarning("Importar BeerXML",
                           "El archivo no tiene insumos (FERMENTABLE / HOP / YEAST).")
            return
        nuevos, actualizados = guardar_insumos(self.db, insumos)
        self.cargar_lista_insumos()
        mb.showinfo("Importar BeerXML",
                    f"Insumos importados: {nuevos} nuevos, {actualizados} actualizados.\n"
                    f"Total leídos: {len(insumos)}")

    def exportar_insumos_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="insumos_cervecera_vgb.csv")
        if not ruta:
            return
        campos = ["type", "name", "origin", "supplier", "category", "color", "extract", "ppg",
                 "yield_pct", "diastatic", "alpha", "form", "attenuation", "abv_tolerance",
                 "temp_range", "notes"]
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
                w.writeheader()
                for ing in self.db.get_ingredients():
                    w.writerow(ing)
            mb.showinfo("Exportar CSV", f"Catálogo exportado:\n{ruta}")
        except Exception as e:
            mb.showerror("Exportar CSV", f"No se pudo exportar.\n{e}")

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
        def valor(clave):
            """Lee un campo de la ficha, sea entrada de texto o lista desplegable."""
            if clave in getattr(self, "_ing_combos", {}):
                return self._ing_combos[clave].get().strip()
            return self._ing_entries[clave].get().strip()

        campos = {
            "uso": valor("uso"), "maceracion": valor("maceracion"),
            "origin": valor("origin"),
            "supplier": valor("supplier"),
            "category": valor("category"),
            "notes": valor("notes"),
            "temp_range": valor("temp_range"),
            "form": valor("form"),
            "color": num("color"), "extract": num("extract"), "ppg": num("ppg"),
            "yield_pct": num("yield_pct"), "diastatic": num("diastatic"),
            "alpha": num("alpha"), "attenuation": num("attenuation"),
            "abv_tolerance": num("abv_tolerance"),
        }
        # guardar_ficha_insumo limpia los campos vacíos y borra el insumo anterior
        # si le cambiaron el tipo o el nombre (así no quedan huérfanos duplicados).
        ok, tipo, nombre = guardar_ficha_insumo(self.db, tipo, nombre, campos,
                                                anterior=self._ing_actual)
        if not ok:
            mb.showwarning("Atención", "Escribí el nombre del insumo."); return
        self._ing_actual = (tipo, nombre)
        self.cargar_lista_insumos()
        mb.showinfo("Catálogo", f"Insumo guardado:\n{tipo} · {nombre}")

    # ==========================================
    # LÓGICA DE INVENTARIO
    # ==========================================
    def abrir_dialogo_ingresar_stock(self):
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Ingresar Stock")
        dialogo.geometry("420x460")
        dialogo.transient(self); dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="📦 Ingresar Stock", font=ctk.CTkFont(size=16, weight="bold")
                     ).pack(anchor="w", padx=15, pady=(15, 10))
        ctk.CTkLabel(dialogo, text="Tipo:").pack(anchor="w", padx=15)
        combo_tipo = ctk.CTkComboBox(dialogo, values=TIPOS_INVENTARIO, width=380)
        combo_tipo.set("Malta"); combo_tipo.pack(padx=15, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Nombre:").pack(anchor="w", padx=15)
        entry_nombre = ctk.CTkEntry(dialogo, width=380, placeholder_text="Ej: Pale Malt")
        entry_nombre.pack(padx=15, pady=(0, 8))
        fila1 = ctk.CTkFrame(dialogo, fg_color="transparent"); fila1.pack(padx=15, fill="x")
        col1 = ctk.CTkFrame(fila1, fg_color="transparent"); col1.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(col1, text="Cantidad:").pack(anchor="w")
        entry_cantidad = ctk.CTkEntry(col1, placeholder_text="Ej: 5"); entry_cantidad.pack(fill="x", pady=(0, 8))
        col2 = ctk.CTkFrame(fila1, fg_color="transparent"); col2.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(col2, text="Unidad:").pack(anchor="w")
        combo_unidad = ctk.CTkComboBox(col2, values=["Kg", "g", "Uds", "L"])
        combo_unidad.set("Kg"); combo_unidad.pack(fill="x", pady=(0, 8))
        fila2 = ctk.CTkFrame(dialogo, fg_color="transparent"); fila2.pack(padx=15, fill="x")
        col3 = ctk.CTkFrame(fila2, fg_color="transparent"); col3.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(col3, text="Costo unit. $ (opcional):").pack(anchor="w")
        entry_costo = ctk.CTkEntry(col3, placeholder_text="Ej: 1500"); entry_costo.pack(fill="x", pady=(0, 8))
        col4 = ctk.CTkFrame(fila2, fg_color="transparent"); col4.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ctk.CTkLabel(col4, text="Mínimo alerta (opcional):").pack(anchor="w")
        entry_minimo = ctk.CTkEntry(col4, placeholder_text="Ej: 2"); entry_minimo.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Vencimiento (opcional):").pack(anchor="w", padx=15)
        entry_venc = ctk.CTkEntry(dialogo, width=380, placeholder_text="AAAA-MM-DD")
        entry_venc.pack(padx=15, pady=(0, 12))

        def confirmar():
            nombre = entry_nombre.get().strip()
            cant_str = entry_cantidad.get().strip()
            if not nombre or not cant_str:
                mb.showwarning("Atención", "Completá nombre y cantidad."); return
            try:
                cantidad = float(cant_str.replace(",", "."))
                if cantidad <= 0: raise ValueError
            except ValueError:
                mb.showerror("Error", "La cantidad debe ser un número positivo."); return
            tipo = combo_tipo.get()
            self.db.add_inventory_item(tipo, nombre, cantidad, combo_unidad.get(), motivo="Ingreso manual")
            item = self.db.get_inventory_item_by_name(tipo, nombre)
            if item:
                costo = _flotar(entry_costo.get().replace(",", "."), None)
                minimo = _flotar(entry_minimo.get().replace(",", "."), None)
                vencimiento = entry_venc.get().strip() or None
                if costo is not None or minimo is not None or vencimiento is not None:
                    self.db.update_inventory_details(item["id"], costo_unitario=costo,
                                                     minimo=minimo, vencimiento=vencimiento)
            self.cargar_lista_inventario()
            self.calcular_y_mostrar()
            dialogo.destroy()

        ctk.CTkButton(dialogo, text="✅ Ingresar", command=confirmar,
                      fg_color="#22C55E", hover_color="#16A34A").pack(pady=(0, 15))

    def exportar_inventario_csv(self):
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="inventario_cervecera_vgb.csv")
        if not ruta:
            return
        campos = ["type", "name", "amount", "unit", "costo_unitario", "minimo", "vencimiento"]
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
                w.writeheader()
                for item in self.db.get_all_inventory():
                    w.writerow(item)          # ya es dict: la BD devuelve dicts
            mb.showinfo("Exportar CSV", f"Inventario exportado:\n{ruta}")
        except Exception as e:
            mb.showerror("Exportar CSV", f"No se pudo exportar.\n{e}")

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
                      fg_color="#22C55E", hover_color="#16A34A").pack(pady=15)

    def eliminar_item_inventario(self, item_id):
        borrar_item_inventario(self.db, item_id)
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
                c_tipo.set(p["tipo"] if p["tipo"] in TIPOS_INVENTARIO else "Misceláneo")
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
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(side="left")
        ctk.CTkButton(frame_botones, text="✅ Importar seleccionados", command=confirmar,
                      fg_color="#22C55E", hover_color="#16A34A").pack(side="right")
        ctk.CTkButton(frame_botones, text="Cancelar", command=dialogo.destroy,
                      fg_color="#2B2B36", hover_color="#3F3F50").pack(side="right", padx=8)

    # ── Inventario: ubicaciones, vencimientos y columna "Específico" ──
    def _vence_pronto(self, fecha, dias=30):
        """True si el vencimiento cae dentro de los próximos `dias` (KPI 'Por Vencer')."""
        if not fecha:
            return False
        from datetime import datetime, date
        for formato in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                vence = datetime.strptime(str(fecha).strip()[:10], formato).date()
                return 0 <= (vence - date.today()).days <= dias
            except ValueError:
                continue
        return False

    def _especifico_inventario(self, item):
        """Dato técnico de la fila: AA% del lúpulo, color de la malta, atenuación…"""
        nombre = (item.get("name") or "").lower()
        tipo = item.get("type")
        try:
            if tipo == "Lúpulo":
                ing = self.db.get_ingredient("Lúpulo", item["name"])
                if ing and ing.get("alpha"):
                    return f"{format_num(ing['alpha'])}% AA"
            elif tipo == "Malta":
                ing = self.db.get_ingredient("Malta", item["name"])
                if ing and ing.get("color"):
                    return f"{format_num(ing['color'])} EBC"
            elif tipo == "Levadura":
                ing = self.db.get_ingredient("Levadura", item["name"])
                if ing and ing.get("attenuation"):
                    return f"Atenuación {format_num(ing['attenuation'])}%"
        except Exception:
            pass
        return "—"

    # ==========================================
    # COCCIONES PROGRAMADAS (rail del Inventario)
    # ==========================================
    def mostrar_todas_las_cocciones(self):
        """Lista completa de cocciones programadas (enlace 'Ver todo' del diseño)."""
        lotes = self.db.get_lotes()
        if not lotes:
            mb.showinfo("Cocciones", "No hay cocciones programadas todavía."); return
        lineas = []
        for lote in lotes:
            faltantes = self.db.faltantes_de_lote(lote["id"])
            estado = "✅ 100% reservado" if not faltantes else f"⚠️ faltan {len(faltantes)}"
            lineas.append(f"#{lote['id']} · {lote['nombre']} ({format_num(lote['volumen'])} L)\n"
                          f"     {lote['fecha_coccion']} · {estado}")
        mb.showinfo("Cocciones programadas", "\n\n".join(lineas))

    def generar_etiqueta_lote(self):
        """Etiqueta imprimible del lote con código QR (botón del diseño)."""
        lotes = self.db.get_lotes()
        if not lotes:
            mb.showinfo("Etiqueta QR / Lote",
                        "No hay cocciones programadas. Programá una para generar su etiqueta.")
            return
        opciones = [f"#{l['id']} · {l['nombre']} ({format_num(l['volumen'])} L)" for l in lotes]
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Etiqueta QR / Lote")
        dialogo.geometry("460x220")
        dialogo.transient(self); dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="🏷️ Etiqueta QR / Lote",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(dialogo, text="Elegí el lote e imprimí la etiqueta para pegar en el fermentador.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        combo = ctk.CTkComboBox(dialogo, values=opciones, width=420)
        combo.set(opciones[0]); combo.pack(padx=16, pady=10)

        def generar():
            lote = lotes[opciones.index(combo.get())] if combo.get() in opciones else lotes[0]
            dialogo.destroy()
            self._escribir_etiqueta(lote)

        ctk.CTkButton(dialogo, text="Generar etiqueta (PDF)", command=generar,
                      fg_color="#3A7EBF", hover_color="#1F538D").pack(pady=(4, 16))

    def _escribir_etiqueta(self, lote):
        ruta = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                            title="Guardar etiqueta",
                                            initialfile=f"etiqueta_lote_{lote['id']}.pdf")
        if not ruta:
            return
        faltantes = self.db.faltantes_de_lote(lote["id"])
        texto_qr = (f"Lote #{lote['id']} | {lote['nombre']} | {format_num(lote['volumen'])} L | "
                    f"Cocción: {lote['fecha_coccion']} | Receta: {lote['receta_nombre']}")
        ruta_qr = None
        try:
            import qrcode
            ruta_qr = os.path.join(tempfile.gettempdir(), f"qr_lote_{lote['id']}.png")
            qrcode.make(texto_qr).save(ruta_qr)
        except Exception as e:
            logger.warning(f"Sin QR (falta la librería qrcode): {e}")
        try:
            from fpdf import FPDF
            pdf = FPDF(format=(100, 70))
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 7, f"Lote #{lote['id']}", ln=1)
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(0, 5, f"{lote['nombre'][:38]}", ln=1)
            pdf.cell(0, 5, f"Volumen: {format_num(lote['volumen'])} L", ln=1)
            pdf.cell(0, 5, f"Coccion: {lote['fecha_coccion']}", ln=1)
            pdf.cell(0, 5, f"Receta: {lote['receta_nombre'][:30]}", ln=1)
            pdf.cell(0, 5, "Insumos: " + ("OK - 100% reservados" if not faltantes
                                           else f"FALTAN {len(faltantes)}"), ln=1)
            if ruta_qr and os.path.exists(ruta_qr):
                pdf.image(ruta_qr, x=72, y=8, w=26)
            pdf.output(ruta)
            mb.showinfo("Etiqueta QR / Lote",
                        f"Etiqueta generada{' con QR' if ruta_qr else ' (sin QR: falta la librería)'}:\n{ruta}")
        except Exception as e:
            logger.error(f"generar etiqueta: {e}")
            mb.showerror("Etiqueta QR / Lote", f"No se pudo generar la etiqueta.\n{e}")
        finally:
            if ruta_qr and os.path.exists(ruta_qr):
                try:
                    os.remove(ruta_qr)
                except OSError:
                    pass

    def abrir_dialogo_programar_coccion(self):
        """Programa una cocción: elige receta, fecha y equipo; reserva los insumos."""
        recetas = self.db.get_all_recipes_summary()
        if not recetas:
            mb.showinfo("Cocciones", "Primero creá una receta."); return
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Programar cocción")
        dialogo.geometry("430x330")
        dialogo.transient(self); dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="📅 Programar cocción",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(16, 8))
        ctk.CTkLabel(dialogo, text="Receta:").pack(anchor="w", padx=16)
        nombres = [f"{r['name']}" for r in recetas]
        combo_receta = ctk.CTkComboBox(dialogo, values=nombres, width=390)
        combo_receta.set(self.entry_nombre.get().strip() or nombres[0])
        combo_receta.pack(padx=16, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Fecha y hora de cocción (ej: Mañana 08:00):").pack(anchor="w", padx=16)
        entry_fecha = ctk.CTkEntry(dialogo, width=390, placeholder_text="2026-09-28 08:00")
        from datetime import date, timedelta
        entry_fecha.insert(0, f"{(date.today() + timedelta(days=1)).isoformat()} 08:00")
        entry_fecha.pack(padx=16, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Equipo:").pack(anchor="w", padx=16)
        equipos = self._nombres_equipos() or [""]
        combo_equipo = ctk.CTkComboBox(dialogo, values=equipos, width=390)
        combo_equipo.set(equipos[0])
        combo_equipo.pack(padx=16, pady=(0, 12))

        def confirmar():
            nombre_receta = combo_receta.get()
            receta = next((r for r in recetas if r["name"] == nombre_receta), None)
            if not receta:
                mb.showwarning("Cocciones", "Elegí una receta."); return
            lote_id = self.db.planificar_lote(receta["id"], fecha_coccion=entry_fecha.get().strip(),
                                              equipo=combo_equipo.get())
            dialogo.destroy()
            self.cargar_lista_inventario()
            if lote_id:
                faltantes = self.db.faltantes_de_lote(lote_id)
                if faltantes:
                    detalle = "\n".join(f"· {f['nombre']}: se requieren {format_num(f['requerido'])} "
                                        f"{f['unidad']}, hay {format_num(f['disponible'])}"
                                        for f in faltantes)
                    mb.showwarning("Cocción programada con faltantes",
                                   f"'{nombre_receta}' quedó programada, pero falta stock:\n\n{detalle}")
                else:
                    mb.showinfo("Cocción programada",
                                f"'{nombre_receta}' programada.\nInsumos 100% reservados ✓")

        ctk.CTkButton(dialogo, text="Programar y reservar insumos", command=confirmar,
                      fg_color="#22C55E", hover_color="#16A34A").pack(pady=(0, 16))

    def _cargar_rail_cocciones(self):
        """Dibuja las próximas cocciones con su estado (100% reservado o faltantes)."""
        if not hasattr(self, "lista_cocciones"):
            return
        for w in self.lista_cocciones.winfo_children():
            w.destroy()
        lotes = self.db.lotes_para_rail()
        listos = sum(1 for l in lotes if l["listo"])
        if hasattr(self, "lbl_cocciones_estado"):
            self.lbl_cocciones_estado.configure(
                text=(f"{listos} de {len(lotes)} con insumos completos" if lotes
                      else "No hay cocciones programadas"))
        if not lotes:
            ctk.CTkLabel(self.lista_cocciones, text="Programá una cocción para reservar los insumos.",
                         text_color="#9CA3AF", font=ctk.CTkFont(size=10),
                         wraplength=260, justify="left").pack(anchor="w", pady=4)
            return
        for lote in lotes:
            tarjeta = ctk.CTkFrame(self.lista_cocciones, fg_color="#2B2B36", corner_radius=6)
            tarjeta.pack(fill="x", pady=3)
            ctk.CTkLabel(tarjeta, text=f"🍺 {lote['nombre']} ({format_num(lote['volumen'])} L)",
                         font=ctk.CTkFont(size=11, weight="bold"),
                         wraplength=250, justify="left").pack(anchor="w", padx=8, pady=(6, 0))
            if lote["listo"]:
                ctk.CTkLabel(tarjeta, text=f"✅ Insumos 100% reservados · {lote['fecha']}",
                             text_color="#22C55E", font=ctk.CTkFont(size=10),
                             wraplength=250, justify="left").pack(anchor="w", padx=8)
            else:
                texto = " · ".join(f"{f['nombre']} (hay {format_num(f['disponible'])} de "
                                   f"{format_num(f['requerido'])} {f['unidad']})"
                                   for f in lote["faltantes"][:2])
                ctk.CTkLabel(tarjeta, text=f"⚠️ Faltante: {texto}", text_color="#D97706",
                             font=ctk.CTkFont(size=10), wraplength=250,
                             justify="left").pack(anchor="w", padx=8)
                ctk.CTkButton(tarjeta, text="Resolver", height=22, width=90,
                              fg_color="#3A7EBF", hover_color="#1F538D",
                              command=lambda l=lote: self.abrir_resolver_faltantes(l)
                              ).pack(anchor="e", padx=8, pady=(2, 6))
            if lote["listo"]:
                ctk.CTkFrame(tarjeta, height=4, fg_color="transparent").pack()

    def abrir_resolver_faltantes(self, lote):
        """Muestra lo que falta del lote y permite ingresar el stock que llegó."""
        ventana = ctk.CTkToplevel(self)
        ventana.title("Resolver faltantes")
        ventana.geometry("520x380")
        ventana.transient(self); ventana.grab_set()
        ctk.CTkLabel(ventana, text=f"⚠️ Faltantes de “{lote['nombre']}”",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(ventana, text="Ingresá el stock que llegó y volvé a comprobar.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16)
        contenedor = ctk.CTkScrollableFrame(ventana, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=12, pady=8)

        def ingresar(faltante, entrada):
            try:
                cantidad = float(str(entrada.get()).replace(",", "."))
            except ValueError:
                mb.showwarning("Resolver", "Poné una cantidad válida."); return
            item = self.db._stock_de(faltante["tipo"], faltante["nombre"])
            if item:
                self.db.add_inventory_item(faltante["tipo"], item["name"], cantidad, item["unit"])
            else:
                tipo = mb.askyesno("Resolver", f"'{faltante['nombre']}' no está en el inventario.\n"
                                               f"¿Lo agrego como {faltante['tipo']}?")
                if not tipo:
                    return
                self.db.add_inventory_item(faltante["tipo"], faltante["nombre"], cantidad,
                                           faltante["unidad"])
            self.cargar_lista_inventario()
            ventana.destroy()
            mb.showinfo("Resolver", "Stock ingresado. Revisá el estado del lote en el rail.")

        for f in lote["faltantes"]:
            fila = ctk.CTkFrame(contenedor)
            fila.pack(fill="x", pady=3)
            ctk.CTkLabel(fila, text=f"{f['nombre']}", font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").pack(anchor="w", padx=10, pady=(6, 0))
            ctk.CTkLabel(fila, text=f"Se requieren {format_num(f['requerido'])} {f['unidad']} · "
                                    f"hay {format_num(f['disponible'])} · "
                                    f"faltan {format_num(f['faltante'])} {f['unidad']}",
                         text_color="#9CA3AF", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=10)
            abajo = ctk.CTkFrame(fila, fg_color="transparent")
            abajo.pack(fill="x", padx=10, pady=(2, 8))
            entrada = ctk.CTkEntry(abajo, width=110, placeholder_text="cantidad")
            entrada.insert(0, format_num(f["faltante"]))
            entrada.pack(side="left")
            ctk.CTkButton(abajo, text="Ingresar stock", height=26, width=120,
                          fg_color="#22C55E", hover_color="#16A34A",
                          command=lambda f=f, e=entrada: ingresar(f, e)).pack(side="left", padx=6)

    def _cargar_rail_espacio(self):
        """Tarjeta 'Distribución de Espacio de Acopio' del diseño."""
        if not hasattr(self, "lbl_distribucion"):
            return
        distribucion = self.db.distribucion_almacenamiento()
        iconos = {"Malta": "🌾 Granos", "Lúpulo": "🌿 Lúpulos",
                  "Levadura": "🧫 Levaduras", "Misceláneo": "⚗️ Sales"}
        lineas, peso = [], 0.0
        for tipo, unidades in distribucion.items():
            for unidad, total in unidades.items():
                lineas.append(f"{iconos.get(tipo, tipo)} ({format_num(total)} {unidad})")
                if unidad.lower() in ("kg", "kilo", "kilos"):
                    peso += total
        self.lbl_distribucion.configure(text="\n".join(lineas) if lineas else "Sin stock cargado")
        capacidad = float(self.db.get_setting("capacidad_deposito_kg", 500) or 500)
        self.lbl_capacidad.configure(
            text=f"Capacidad estimada: {min(999, round(peso / capacidad * 100))}% "
                 f"({format_num(round(peso))} kg de {format_num(round(capacidad))} kg)")

    # ── Acciones por fila del inventario (diseño de Stitch) ──
    def _inv_ver_historial(self, _evento=None):
        """Doble clic: muestra el Kardex del insumo elegido (ya filtrado en la ficha)."""
        self._inv_on_select()
        item = self._inv_items_por_id.get(self._inv_actual or -1)
        if item:
            mb.showinfo("Historial (Kardex)",
                        f"Los últimos movimientos de “{item['name']}” están en la ficha,\n"
                        f"abajo a la derecha.")

    def _inv_menu_fila(self, evento):
        """Clic derecho: menú con las acciones de la fila."""
        fila = self.tree_inventario.identify_row(evento.y)
        if not fila:
            return
        self.tree_inventario.selection_set(fila)
        self._inv_on_select()
        menu = tk.Menu(self, tearoff=0, background="#24242C", foreground="#E4E1EA",
                       activebackground="#3A7EBF", activeforeground="#FFFFFF", bd=0)
        menu.add_command(label="🧾  Ver historial (Kardex)", command=self._inv_ver_historial)
        menu.add_command(label="⚖️  Ajuste físico…", command=self.abrir_dialogo_ajuste_fisico)
        menu.add_command(label="📥  Ingresar stock…", command=self.abrir_dialogo_ingresar_stock)
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar del inventario",
                         command=lambda: self.eliminar_item_inventario(self._inv_actual))
        try:
            menu.tk_popup(evento.x_root, evento.y_root)
        finally:
            menu.grab_release()

    def generar_orden_compra(self):
        """Orden de compra sugerida con lo que está por debajo del mínimo (diseño de Stitch)."""
        sugerencias = []
        for it in self.db.get_all_inventory():
            minimo = float(it["minimo"] or 0)
            actual = float(it["amount"] or 0)
            if minimo and actual < minimo:
                # Reponer hasta el doble del mínimo (stock de seguridad)
                sugerido = round(minimo * 2 - actual, 2)
                costo = float(it["costo_unitario"] or 0)
                sugerencias.append({
                    "insumo": it["name"], "tipo": it["type"], "actual": actual,
                    "unidad": it["unit"], "minimo": minimo, "sugerido": sugerido,
                    "costo_unitario": costo, "costo_estimado": round(sugerido * costo, 2),
                })
        if not sugerencias:
            mb.showinfo("Orden de compra",
                        "No hay insumos por debajo del mínimo: no hace falta comprar nada ✅")
            return
        total = sum(s["costo_estimado"] for s in sugerencias)
        ruta = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            title="Guardar orden de compra",
                                            initialfile="orden_de_compra.csv")
        if not ruta:
            return
        try:
            with open(ruta, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Insumo", "Categoría", "Stock actual", "Unidad", "Mínimo",
                            "Sugerido", "Costo unitario", "Costo estimado"])
                for s_ in sugerencias:
                    w.writerow([s_["insumo"], s_["tipo"], s_["actual"], s_["unidad"],
                                s_["minimo"], s_["sugerido"], s_["costo_unitario"],
                                s_["costo_estimado"]])
                w.writerow([])
                w.writerow(["", "", "", "", "", "", "TOTAL ESTIMADO", round(total, 2)])
            detalle = "\n".join(f"· {s_['insumo']}: {format_num(s_['sugerido'])} {s_['unidad']}"
                                for s_ in sugerencias[:6])
            mb.showinfo("Orden de compra",
                        f"{len(sugerencias)} insumo(s) para reponer.\n\n{detalle}"
                        f"{'\n…' if len(sugerencias) > 6 else ''}\n\n"
                        f"Costo estimado: ${format_num(round(total, 2))}\nGuardada en:\n{ruta}")
        except Exception as e:
            logger.error(f"generar_orden_compra: {e}")
            mb.showerror("Orden de compra", f"No se pudo guardar.\n{e}")

    def abrir_dialogo_ajuste_fisico(self):
        """Ajuste físico: deja el stock en lo que se contó y lo registra en el Kardex."""
        items = self.db.get_all_inventory()
        if not items:
            mb.showinfo("Ajuste físico", "No hay stock cargado todavía."); return
        dialogo = ctk.CTkToplevel(self)
        dialogo.title("Ajuste Físico")
        dialogo.geometry("440x320")
        dialogo.transient(self); dialogo.grab_set()
        ctk.CTkLabel(dialogo, text="⚖️ Ajuste Físico",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkLabel(dialogo, text="Corregí el stock con lo que contaste en el depósito.\n"
                                   "La diferencia queda registrada en el Kardex.",
                     text_color="#9CA3AF", font=ctk.CTkFont(size=11), justify="left"
                     ).pack(anchor="w", padx=16, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Insumo:").pack(anchor="w", padx=16)
        etiquetas = [f"{it['type']} · {it['name']} ({format_num(it['amount'])} {it['unit']})"
                     for it in items]
        combo = ctk.CTkComboBox(dialogo, values=etiquetas, width=400)
        actual = self._inv_items_por_id.get(self._inv_actual or -1)
        combo.set(f"{actual['type']} · {actual['name']} ({format_num(actual['amount'])} {actual['unit']})"
                  if actual else etiquetas[0])
        combo.pack(padx=16, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Cantidad contada:").pack(anchor="w", padx=16)
        entrada = ctk.CTkEntry(dialogo, width=400, placeholder_text="Ej: 23.4")
        if actual:
            entrada.insert(0, format_num(actual["amount"]))
        entrada.pack(padx=16, pady=(0, 8))
        ctk.CTkLabel(dialogo, text="Motivo:").pack(anchor="w", padx=16)
        motivo = ctk.CTkEntry(dialogo, width=400)
        motivo.insert(0, "Conteo de depósito")
        motivo.pack(padx=16, pady=(0, 12))

        def confirmar():
            indice = etiquetas.index(combo.get()) if combo.get() in etiquetas else 0
            item = items[indice]
            try:
                contada = float(str(entrada.get()).replace(",", "."))
            except ValueError:
                mb.showwarning("Ajuste físico", "Poné una cantidad válida."); return
            diferencia = self.db.ajustar_inventario(item["id"], contada, motivo.get().strip() or "Ajuste físico")
            dialogo.destroy()
            self.cargar_lista_inventario()
            signo = "sobraba" if (diferencia or 0) > 0 else "faltaba"
            mb.showinfo("Ajuste físico",
                        f"{item['name']}: quedó en {format_num(contada)} {item['unit']}.\n"
                        f"{signo.capitalize()} {format_num(abs(diferencia or 0))} {item['unit']} "
                        f"(registrado en el Kardex).")

        ctk.CTkButton(dialogo, text="Aplicar ajuste", command=confirmar,
                      fg_color="#D97706", hover_color="#B45309").pack(pady=(0, 16))

    def _inv_pagina_mover(self, paso):
        """Paginación de la planilla (botones Anterior / Siguiente del diseño)."""
        self._inv_pagina = max(0, getattr(self, "_inv_pagina", 0) + paso)
        self.cargar_lista_inventario()

    def _actualizar_filtro_inventario(self, items):
        """Filtro por categoría con contadores, como el diseño: 'Granos (18)', 'Sales & Químicos (6)'."""
        if not hasattr(self, "seg_inv_filtro"):
            return
        nombres = {"Malta": "Granos", "Lúpulo": "Lúpulos", "Levadura": "Levaduras",
                   "Misceláneo": "Sales & Químicos"}
        etiqueta_todos = f"Todos ({len(items)})"
        mapa = {etiqueta_todos: "Todos"}
        valores = [etiqueta_todos]
        for tipo in TIPOS_INVENTARIO:
            cantidad = sum(1 for i in items if i["type"] == tipo)
            etiqueta = f"{nombres.get(tipo, tipo)} ({cantidad})"
            valores.append(etiqueta)
            mapa[etiqueta] = tipo
        self._mapa_filtro_inv = mapa
        self.seg_inv_filtro.configure(values=valores)
        for etiqueta, tipo in mapa.items():
            if tipo == getattr(self, "_filtro_inv_tipo", "Todos"):
                self.seg_inv_filtro.set(etiqueta)
                break

    def cargar_lista_inventario(self):
        for fila in self.tree_inventario.get_children():
            self.tree_inventario.delete(fila)
        items = self.db.get_all_inventory()
        self._inv_items_por_id = {item["id"]: item for item in items}
        self._actualizar_filtro_inventario(items)
        seleccionado = self.seg_inv_filtro.get() if hasattr(self, "seg_inv_filtro") else "Todos"
        filtro = getattr(self, "_mapa_filtro_inv", {}).get(seleccionado, "Todos")
        self._filtro_inv_tipo = filtro
        busqueda = self.entry_inv_buscar.get().strip().lower() if hasattr(self, "entry_inv_buscar") else ""
        ubicacion = (self.combo_inv_ubicacion.get() if hasattr(self, "combo_inv_ubicacion")
                     else "Todas las ubicaciones")
        valorizacion, bajo_stock, por_vencer = 0.0, 0, 0
        filtrados = []
        for item in items:
            costo = item["costo_unitario"] or 0
            minimo = item["minimo"] or 0
            valorizacion += (item["amount"] or 0) * costo
            es_bajo = minimo > 0 and item["amount"] <= minimo
            if es_bajo:
                bajo_stock += 1
            if self._vence_pronto(item.get("vencimiento")):
                por_vencer += 1
            if filtro != "Todos" and item["type"] != filtro:
                continue
            if busqueda and busqueda not in item["name"].lower():
                continue
            if ubicacion != "Todas las ubicaciones" and (item.get("ubicacion") or "") != ubicacion:
                continue
            filtrados.append(item)

        tam = getattr(self, "_inv_por_pagina", 8)
        self._inv_pagina = min(getattr(self, "_inv_pagina", 0), max(0, (len(filtrados) - 1) // tam))
        desde = self._inv_pagina * tam
        for indice_fila, item in enumerate(filtrados[desde:desde + tam]):
            minimo = item["minimo"] or 0
            costo = item["costo_unitario"] or 0
            es_bajo = minimo > 0 and item["amount"] <= minimo
            fisico = f"{format_num(item['amount'])} {item['unit']}"
            costo_txt = f"${format_num(costo)}/u" if costo else "—"
            # Estado como el diseño: Crítico / Bajo / En Stock según el mínimo
            if minimo > 0:
                nivel = item["amount"] / minimo * 100
                if item["amount"] <= minimo:
                    estado, etiqueta = "🔴 Crítico", "critico"
                elif nivel <= 150:
                    estado, etiqueta = "🟠 Bajo", "bajo"
                else:
                    estado, etiqueta = "🟢 En Stock", "ok"
                nivel_txt = f"{format_num(round(nivel))}% · Min: {format_num(minimo)} {item['unit']}"
            else:
                estado, etiqueta, nivel_txt = "🟢 En Stock", "ok", "—"
            espec = self._especifico_inventario(item)
            ubic = item.get("ubicacion") or "—"
            lote_txt = (f"Lote: {item['lote']} · {ubic}" if item.get("lote")
                        else ubic)
            self.tree_inventario.insert("", "end", iid=str(item["id"]), text=item["name"],
                                        values=(lote_txt, item["type"], espec, fisico,
                                                nivel_txt, costo_txt, estado, "⚖️ 🧾"),
                                        tags=(etiqueta,
                                              self._alternar_filas(self.tree_inventario, indice_fila)))
        if hasattr(self, "lbl_kpi_valorizacion"):
            self.lbl_kpi_valorizacion.configure(text=f"💲 Valorización: ${format_num(round(valorizacion, 2))}")
            self.lbl_kpi_total.configure(text=f"📦 Insumos: {len(items)}")
            activas = len({i["type"] for i in items})
            self.lbl_kpi_total.configure(text=f"📦 Insumos: {len(items)} ítems")
            self.lbl_kpi_bajo.configure(text=f"⚠️ Stock bajo: {bajo_stock}  ·  Reorden sugerido")
            self.lbl_kpi_porvencer.configure(text=f"⏳ Por vencer: {por_vencer}  ·  < 30 días")
        if hasattr(self, "lbl_inv_pagina"):
            if filtrados:
                self.lbl_inv_pagina.configure(
                    text=f"Mostrando {desde + 1} a {min(desde + tam, len(filtrados))} de "
                         f"{len(filtrados)}  ·  Página {self._inv_pagina + 1} de "
                         f"{max(1, -(-len(filtrados) // tam))}")
            else:
                self.lbl_inv_pagina.configure(text="Sin insumos que coincidan")
        self._cargar_rail_cocciones()
        self._cargar_rail_espacio()
        if self._inv_actual not in self._inv_items_por_id:
            self._inv_actual = None
        nombre_seleccionado = self._inv_items_por_id[self._inv_actual]["name"] if self._inv_actual else None
        self._cargar_kardex_ficha(nombre_seleccionado)

    def _inv_on_select(self, _evento=None):
        seleccion = self.tree_inventario.selection()
        if not seleccion:
            return
        item_id = int(seleccion[0])
        item = self._inv_items_por_id.get(item_id)
        if not item:
            return
        ficha = valores_ficha_inventario(item)      # datos: van por la lógica pura
        if not ficha:
            return
        self._inv_actual = item_id
        self.lbl_ficha_inv.configure(text=f"📇 {ficha['titulo']}")
        self.lbl_ficha_inv_sub.configure(
            text=f"{ficha['tipo']} · {format_num(ficha['cantidad'])} {ficha['unidad']}")
        self.entry_ficha_costo.delete(0, "end")
        if ficha["costo_unitario"]:
            self.entry_ficha_costo.insert(0, format_num(ficha["costo_unitario"]))
        self.entry_ficha_minimo.delete(0, "end")
        if ficha["minimo"]:
            self.entry_ficha_minimo.insert(0, format_num(ficha["minimo"]))
        self.entry_ficha_vencimiento.delete(0, "end")
        if ficha["vencimiento"]:
            self.entry_ficha_vencimiento.insert(0, ficha["vencimiento"])
        self.combo_ficha_ubicacion.set(ficha["ubicacion"])
        self.entry_ficha_lote.delete(0, "end")
        if ficha["lote"]:
            self.entry_ficha_lote.insert(0, ficha["lote"])
        self._cargar_kardex_ficha(ficha["titulo"])

    def _inv_guardar_ficha(self):
        if not self._inv_actual:
            mb.showinfo("Ficha de insumo", "Elegí un insumo de la lista primero."); return
        costo = _flotar(self.entry_ficha_costo.get().replace(",", "."), None)
        minimo = _flotar(self.entry_ficha_minimo.get().replace(",", "."), None)
        vencimiento = self.entry_ficha_vencimiento.get().strip()
        guardar_ficha_inventario(self.db, self._inv_actual, costo, minimo, vencimiento,
                                 ubicacion=self.combo_ficha_ubicacion.get(),
                                 lote=self.entry_ficha_lote.get().strip())
        self.cargar_lista_inventario()
        self.calcular_y_mostrar()

    def _inv_borrar_actual(self):
        if not self._inv_actual:
            mb.showinfo("Eliminar", "Elegí un insumo de la lista primero."); return
        item = self._inv_items_por_id.get(self._inv_actual)
        nombre = item["name"] if item else ""
        if mb.askyesno("Eliminar del inventario", f"¿Eliminar '{nombre}' del stock?"):
            self.eliminar_item_inventario(self._inv_actual)
            self._inv_actual = None
            self.lbl_ficha_inv.configure(text="📇 Ficha de Insumo")
            self.lbl_ficha_inv_sub.configure(text="Elegí un insumo de la lista.")
            for e in (self.entry_ficha_costo, self.entry_ficha_minimo, self.entry_ficha_vencimiento):
                e.delete(0, "end")

    def _cargar_kardex_ficha(self, nombre=None):
        if not hasattr(self, "lista_kardex_ui"):
            return
        for w in self.lista_kardex_ui.winfo_children():
            w.destroy()
        movimientos = kardex_de_item(self.db, nombre)
        if not movimientos:
            ctk.CTkLabel(self.lista_kardex_ui, text="Sin movimientos todavía.",
                         text_color="#9CA3AF").pack(pady=8)
            return
        iconos = {"Entrada": "🟢 +", "Salida": "🔴 -", "Merma": "🟠 -", "Ajuste": "🔵 ~"}
        for m in movimientos:
            f = ctk.CTkFrame(self.lista_kardex_ui, fg_color="transparent")
            f.pack(fill="x", pady=1)
            signo = iconos.get(m["tipo"], "• ")
            texto = f"{signo}{format_num(m['cantidad'])}"
            if not nombre:
                texto += f" · {m['item_name']}"
            texto += f" · {m['fecha']}"
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
