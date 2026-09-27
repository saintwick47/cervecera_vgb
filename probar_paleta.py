"""Comprueba que la app use solo la paleta del sistema de diseño (DESIGN.md).

Evita que se cuelen colores nuevos: el mockup define una paleta cerrada y la
coherencia visual depende de respetarla.

Uso:  python probar_paleta.py
"""
import collections
import os

os.environ["VGB_TEST"] = "1"   # las pruebas no escriben el log del usuario
import re
import sys

ARCHIVOS = ("app.py", "app_gestion.py", "app_recetas.py")

# Paleta del DESIGN.md: la del texto (CTk) + los tokens del encabezado YAML
PALETA = {
    "#1E1E24": "canvas", "#24242C": "panel / barra", "#2B2B36": "módulo / inputs",
    "#32323E": "input", "#343442": "input hundido", "#34343B": "superficie alta",
    "#3F3F50": "borde", "#3A3A4A": "borde hairline", "#282834": "fila alternada",
    "#3A7EBF": "azul CTk (acción primaria)", "#1F538D": "azul hover",
    "#9ECAFF": "surface-tint", "#D97706": "ámbar / cobre", "#B45309": "ámbar oscuro",
    "#22C55E": "verde operativo", "#16A34A": "verde hover",
    "#DC2626": "rojo destructivo", "#B91C1C": "rojo hover",
    "#FFFFFF": "blanco", "#E4E1EA": "on-surface", "#C1C7D2": "on-surface-variant",
    "#9CA3AF": "texto suave",
}


def revisar_tema(aqui):
    """Comprueba que el tema propio se CARGA y trae los colores del diseño.

    Este chequeo existe porque el archivo puede llamarse distinto y la app caía
    en silencio al tema por defecto (azul/gris), sin que nadie lo notara.
    """
    import glob
    candidatos = []
    for nombre in ("tema_brewtk.json", "Tema brewtk.json"):
        ruta = os.path.join(aqui, nombre)
        if os.path.exists(ruta):
            candidatos.append(ruta)
    if not candidatos:
        print("  ✗ no se encontró el archivo del tema")
        return 1
    import json
    tema = json.load(open(candidatos[0], encoding="utf-8"))
    problemas = []
    esperado = {
        ("CTk", "fg_color"): "#1E1E24",
        ("CTkEntry", "fg_color"): "#2B2B36",
        ("CTkEntry", "border_color"): "#3F3F50",
        ("CTkButton", "fg_color"): "#3A7EBF",
        ("CTkSegmentedButton", "selected_color"): "#3A7EBF",
    }
    for (seccion, clave), color in esperado.items():
        valor = tema.get(seccion, {}).get(clave)
        valor = valor[-1] if isinstance(valor, list) else valor
        if valor != color:
            problemas.append(f"{seccion}.{clave} = {valor} (debería ser {color})")
    fuente = tema.get("CTkFont", {}).get("Linux", {}).get("family")
    print(f"  tema: {os.path.basename(candidatos[0])} · tipografía: {fuente}")
    for problema in problemas:
        print(f"  ✗ {problema}")
    return 1 if problemas else 0


def main():
    aqui = os.path.dirname(os.path.abspath(__file__))
    usados = collections.Counter()
    for archivo in ARCHIVOS:
        ruta = os.path.join(aqui, archivo)
        if not os.path.exists(ruta):
            continue
        for hexa in re.findall(r'"#([0-9A-Fa-f]{6})"', open(ruta, encoding="utf-8").read()):
            usados["#" + hexa.upper()] += 1
    fuera = {c: n for c, n in usados.items() if c not in PALETA}
    print(f"Colores distintos en uso: {len(usados)}")
    print(f"Dentro de la paleta del diseño: {sum(n for c, n in usados.items() if c in PALETA)} usos")
    if fuera:
        print("\nFuera de la paleta:")
        for color, n in sorted(fuera.items(), key=lambda x: -x[1]):
            print(f"  ✗ {color}  x{n}")
        print(f"\nPALETA: {len(fuera)} color(es) fuera del diseño ✗")
        return 1
    print("\nTodos los colores pertenecen a la paleta del diseño ✓")
    print("Tema propio:")
    if revisar_tema(aqui):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
