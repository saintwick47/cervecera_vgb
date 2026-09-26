# app_gestion.py
# Autor: SaintWick
"""
Módulo de gestión de Cervecera VGB (split de app.py, demasiado grande).
Ruta: app_gestion.py
Versión: v1.4.2 (coincide con APP_VERSION)

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
import hashlib
import json
import os
import re
import sys
import difflib

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
        frame_colaboradores = ctk.CTkFrame(self, fg_color="#2c2c2c", corner_radius=8)
        frame_colaboradores.grid(row=2, column=0, padx=20, pady=(0, 5), sticky="ew")
        ctk.CTkLabel(frame_colaboradores, text="🤝 Colaboradores: Stephan",
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=15, pady=8)
        btn_cerrar = ctk.CTkButton(self, text="Cerrar Manual", command=self.destroy, fg_color="#6B7280", hover_color="#4B5563")
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
