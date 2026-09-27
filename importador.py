# importador.py
# Autor: SaintWick
"""
Lectura de archivos BeerXML (insumos y equipo) para Cervecera VGB.

BeerXML es el formato estándar que exportan Brewfather, BeerSmith, Brew-o-Matic y
nuestra propia app, así que sirve para traer catálogos y perfiles de equipo.

Es lógica pura (no toca la interfaz): recibe una ruta o un texto XML y devuelve
diccionarios listos para guardar. Los tests corren sin pantalla.
"""
import xml.etree.ElementTree as ET

# Equivalencias de tipos de BeerXML a nuestro catálogo
CATEGORIA_POR_TIPO = {
    "grain": "Maltas Base", "base": "Maltas Base", "specialty": "Maltas Especiales / Caramelo",
    "caramel": "Maltas Especiales / Caramelo", "crystal": "Maltas Especiales / Caramelo",
    "roasted": "Granos Tostados", "black": "Granos Tostados", "smoked": "Granos Tostados",
    "adjunct": "Adjuntos y Copos", "sugar": "Adjuntos y Copos", "extract": "Adjuntos y Copos",
    "dry extract": "Adjuntos y Copos",
}


def _texto(nodo, etiqueta, por_defecto=""):
    hijo = nodo.find(etiqueta)
    return hijo.text.strip() if (hijo is not None and hijo.text) else por_defecto


def _numero(nodo, etiqueta, por_defecto=0.0):
    try:
        return float(_texto(nodo, etiqueta, str(por_defecto)).replace(",", "."))
    except ValueError:
        return por_defecto


def _raiz(fuente):
    """Acepta una ruta de archivo o el texto XML."""
    if isinstance(fuente, (str, bytes)) and len(str(fuente)) < 500 and "<" not in str(fuente):
        return ET.parse(fuente).getroot()
    return ET.fromstring(fuente)


def _iterar_todos(raiz, etiqueta):
    """Devuelve los nodos con esa etiqueta, estén en la raíz o dentro de un contenedor."""
    return raiz.iter(etiqueta)


def leer_insumos(fuente):
    """Insumos de un BeerXML: [{tipo, nombre, campos…}] listos para add_ingredient."""
    raiz = _raiz(fuente)
    insumos = []

    for nodo in _iterar_todos(raiz, "FERMENTABLE"):
        nombre = _texto(nodo, "NAME")
        if not nombre:
            continue
        tipo_xml = _texto(nodo, "TYPE", "Grain").lower()
        # BeerXML da el rendimiento en %; nuestro extracto va en puntos L°/kg (x3.8)
        rendimiento = _numero(nodo, "YIELD", 75.0)
        campos = {
            "tipo": "Malta",
            "nombre": nombre,
            "origin": _texto(nodo, "ORIGIN"),
            "supplier": _texto(nodo, "SUPPLIER"),
            "category": CATEGORIA_POR_TIPO.get(tipo_xml, "Maltas Base"),
            "color": _numero(nodo, "COLOR", 2.0),
            "extract": round(rendimiento * 3.8) if rendimiento else 300,
            "ppg": round(rendimiento * 0.46, 1) if rendimiento else 0,
            "uso": "Macerado" if tipo_xml not in ("sugar", "extract") else "Hervido",
        }
        insumos.append(campos)

    for nodo in _iterar_todos(raiz, "HOP"):
        nombre = _texto(nodo, "NAME")
        if not nombre:
            continue
        forma = _texto(nodo, "FORM", "Pellet").strip().lower()
        uso_xml = _texto(nodo, "USE", "Boil").strip().lower()
        uso = {"boil": "Amargor", "aroma": "Aroma", "dry hop": "Aroma",
               "first wort": "Amargor", "mash": "Amargor"}.get(uso_xml, "Doble propósito")
        insumos.append({
            "tipo": "Lúpulo",
            "nombre": nombre,
            "origin": _texto(nodo, "ORIGIN"),
            "supplier": _texto(nodo, "SUPPLIER"),
            "alpha": _numero(nodo, "ALPHA", 5.0),
            "form": "flor" if "leaf" in forma or "whole" in forma else "pellet",
            "uso": uso,
        })

    for nodo in _iterar_todos(raiz, "YEAST"):
        nombre = _texto(nodo, "NAME")
        if not nombre:
            continue
        laboratorio = _texto(nodo, "LABORATORY")
        producto = _texto(nodo, "PRODUCT_ID")
        # Origen: la marca; el código de producto sólo si no está ya en el nombre
        origen = laboratorio
        if producto and producto.lower() not in nombre.lower():
            origen = " ".join(x for x in (laboratorio, producto) if x).strip()
        insumos.append({
            "tipo": "Levadura",
            "nombre": nombre,
            "origin": origen,
            "attenuation": _numero(nodo, "ATTENUATION", 75.0),
            "abv_tolerance": _numero(nodo, "MAX_ABV", 12.0) or 12.0,
            "temp_range": _texto(nodo, "TEMPERATURE_RANGE") or _rango_temperatura(nodo),
            "form": "seca" if "dry" in _texto(nodo, "FORM", "Dry").lower() else "líquida",
        })
    return insumos


def _rango_temperatura(nodo):
    minimo = _numero(nodo, "MIN_TEMPERATURE", 0.0)
    maximo = _numero(nodo, "MAX_TEMPERATURE", 0.0)
    if minimo or maximo:
        return f"{minimo:.0f}-{maximo:.0f} °C"
    return ""


def leer_equipo(fuente):
    """Perfil de equipo de un BeerXML (bloque EQUIPMENT), si existe."""
    raiz = _raiz(fuente)
    nodo = raiz.find("EQUIPMENT") if raiz.tag != "EQUIPMENT" else raiz
    if nodo is None:
        nodo = next(iter(_iterar_todos(raiz, "EQUIPMENT")), None)
    if nodo is None:
        return {}
    return {
        "name": _texto(nodo, "NAME", "Equipo importado"),
        "batch_volume": _numero(nodo, "BATCH_SIZE", 20.0),
        "kettle_volume": _numero(nodo, "BOIL_SIZE", 0.0) or _numero(nodo, "KETTLE_VOLUME", 0.0),
        "perdidas_l": _numero(nodo, "TRUB_CHILLER_LOSS", 0.0),
        "evaporacion_l_h": _numero(nodo, "EVAP_RATE", 0.0),
        "eficiencia": _numero(nodo, "EFFICIENCY", 75.0),
        "temp_macerado": _numero(nodo, "MASH_TEMP", 66.0),
        "notas": "Importado de BeerXML",
    }


def leer_receta(fuente):
    """Datos básicos de una receta BeerXML: {nombre, volumen, eficiencia, insumos…}."""
    raiz = _raiz(fuente)
    receta = raiz.find("RECIPE") if raiz.tag != "RECIPE" else raiz
    if receta is None:
        receta = raiz
    maltas, lupulos, levaduras = [], [], []
    for nodo in _iterar_todos(receta, "FERMENTABLE"):
        rendimiento = _numero(nodo, "YIELD", 75.0)
        maltas.append({"nombre": _texto(nodo, "NAME"),
                       "cantidad": _numero(nodo, "AMOUNT", 0.0),
                       "extracto": round(rendimiento * 3.8) if rendimiento else 300,
                       "color": _numero(nodo, "COLOR", 2.0)})
    for nodo in _iterar_todos(receta, "HOP"):
        lupulos.append({"nombre": _texto(nodo, "NAME"),
                        "cantidad": _numero(nodo, "AMOUNT", 0.0) * 1000,   # kg -> g
                        "aa": _numero(nodo, "ALPHA", 5.0),
                        "tiempo": _numero(nodo, "TIME", 60.0),
                        "formato": "flor" if "leaf" in _texto(nodo, "FORM", "").lower() else "pellet"})
    for nodo in _iterar_todos(receta, "YEAST"):
        levaduras.append({"nombre": _texto(nodo, "NAME"),
                          "atenuacion": _numero(nodo, "ATTENUATION", 75.0),
                          "tolerancia": _numero(nodo, "MAX_ABV", 12.0) or 12.0})
    return {
        "nombre": _texto(receta, "NAME", "Receta importada"),
        "agua_vol": _numero(receta, "BATCH_SIZE", 20.0),
        "eficiencia": _numero(receta, "EFFICIENCY", 75.0) / 100.0,
        "fg_estimada": _numero(receta, "FG", 1.010) or 1.010,
        "style": "",
        "maltas": [m for m in maltas if m["nombre"]],
        "lupulos": [l for l in lupulos if l["nombre"]],
        "levaduras": [y for y in levaduras if y["nombre"]],
    }


def guardar_insumos(db, insumos):
    """Guarda los insumos en el catálogo. Devuelve (nuevos, actualizados)."""
    nuevos = actualizados = 0
    for datos in insumos:
        tipo, nombre = datos.pop("tipo"), datos.pop("nombre")
        campos = {k: v for k, v in datos.items() if v not in (None, "")}
        existe = db.get_ingredient(tipo, nombre)
        db.add_ingredient(tipo, nombre, **campos)
        if existe:
            actualizados += 1
        else:
            nuevos += 1
    return nuevos, actualizados
