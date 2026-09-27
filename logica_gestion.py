# logica_gestion.py
# Autor: SaintWick
"""
Lógica del maestro-detalle de Insumos e Inventario, **separada de los widgets**.

Estas funciones reciben la base de datos y valores simples, y devuelven datos.
`app_gestion.py` las usa para mostrar: así el flujo maestro-detalle (elegir fila →
ficha → editar → guardar → borrar) se puede testear **sin pantalla** (sirve para CI,
donde no hay display).

Convención: devuelven datos; nunca tocan la interfaz ni muestran mensajes.
"""
from database import VACIO


# ══════════════════════════════════════════════════════════════════════════════
#  INVENTARIO
# ══════════════════════════════════════════════════════════════════════════════

def items_por_id(items):
    """Ítems de inventario indexados por id (lo que usa el Treeview para seleccionar)."""
    return {it["id"]: it for it in (items or [])}


def valores_ficha_inventario(item):
    """Valores que muestra la Ficha de Insumo Activo. None si no hay ítem.

    La interfaz solo formatea: los datos salen de acá.
    """
    if not item:
        return None
    return {
        "id": item.get("id"),
        "titulo": item.get("name", ""),
        "tipo": item.get("type", ""),
        "cantidad": item.get("amount"),
        "unidad": item.get("unit", ""),
        "costo_unitario": item.get("costo_unitario"),
        "minimo": item.get("minimo"),
        "vencimiento": item.get("vencimiento") or "",
        "ubicacion": item.get("ubicacion") or "",
        "lote": item.get("lote") or "",
    }


def kardex_de_item(db, nombre=None, limite=15, escaneo=200):
    """Movimientos del Kardex. Con `nombre`, solo los de ese ítem (no la lista global)."""
    movimientos = db.get_inventory_movimientos(limit=escaneo)
    if nombre:
        movimientos = [m for m in movimientos if m.get("item_name") == nombre]
    return movimientos[:limite]


def guardar_ficha_inventario(db, item_id, costo, minimo, vencimiento, ubicacion=None, lote=None):
    """Guarda costo / mínimo / vencimiento de la ficha.

    Un campo vacío (None o "") **limpia** el dato en la base, que es lo que espera
    cualquiera que borre el contenido de la casilla. Devuelve True si guardó.
    """
    if not item_id:
        return False

    def valor(v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return VACIO
        return v

    datos = {"costo_unitario": valor(costo), "minimo": valor(minimo),
             "vencimiento": valor(vencimiento)}
    if ubicacion is not None:
        datos["ubicacion"] = ubicacion or VACIO
    if lote is not None:
        datos["lote"] = lote or VACIO
    db.update_inventory_details(item_id, **datos)
    return True


def eliminar_item_inventario(db, item_id):
    """Borra un ítem del inventario (desde la ficha). Devuelve True si borró."""
    if not item_id:
        return False
    db.delete_inventory_item(item_id)
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  INSUMOS
# ══════════════════════════════════════════════════════════════════════════════

CLAVE_TEXTO = ("origin", "supplier", "category", "notes", "temp_range", "form")
CLAVE_NUMERO = ("color", "extract", "ppg", "yield_pct", "diastatic",
                "alpha", "attenuation", "abv_tolerance")


def clave_fila_insumo(tipo, nombre):
    """Clave con la que el Treeview identifica una fila de insumo."""
    return f"{tipo}|{nombre}"


def fila_a_insumo(clave):
    """Vuelve de la clave del Treeview a (tipo, nombre)."""
    tipo, _, nombre = (clave or "").partition("|")
    return tipo, nombre


def datos_ficha_insumo(db, tipo, nombre):
    """Insumo para la ficha técnica (dict vacío si no existe)."""
    return db.get_ingredient(tipo, nombre) or {}


def limpiar_campos_insumo(campos):
    """Descarta los campos vacíos: en la BD solo se guarda lo que tiene valor."""
    return {k: v for k, v in (campos or {}).items() if v not in (None, "")}


def guardar_ficha_insumo(db, tipo, nombre, campos, anterior=None):
    """Guarda un insumo desde la ficha técnica.

    Si mientras editaba le cambiaron el tipo o el nombre, el insumo anterior queda
    huérfano: se borra para no duplicar.
    Devuelve (ok, tipo, nombre) — los datos con los que quedó guardado.
    """
    nombre = (nombre or "").strip()
    if not nombre:
        return (False, tipo, nombre)
    campos = limpiar_campos_insumo(campos)
    if anterior and tuple(anterior) != (tipo, nombre):
        db.delete_ingredient(*anterior)
    db.add_ingredient(tipo, nombre, **campos)
    return (True, tipo, nombre)


def nombre_insumo_nuevo(ing_actual, tipo, nombre):
    """True si lo que se está guardando reemplaza a otro insumo (cambió tipo o nombre)."""
    return bool(ing_actual) and tuple(ing_actual) != (tipo, (nombre or "").strip())
