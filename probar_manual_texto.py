#!/usr/bin/env python3
"""Verifica el texto del Manual de Usuario de la app de PC.

Se lee el manual directo del código (no abre ventana), así que corre rápido en
cualquier entorno. Comprueba que estén todas las secciones y que no queden
textos obsoletos de versiones anteriores.

Uso:  python probar_manual_texto.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
FUENTE = os.path.join(RAIZ, "app_gestion.py")

# Secciones que el manual debe mencionar siempre
SECCIONES = (
    "CÓMO ESTÁ ORGANIZADA LA VENTANA",
    "RECETA",
    "INSUMOS E INVENTARIO",
    "COCCIONES PROGRAMADAS",
    "EQUIPOS",
    "COMPARADOR BJCP",
    "COMUNIDAD",
    "MENÚ",
    "AGREGAR RECETAS",
    "ACTUALIZAR LA APP",
    "REGISTRO DE ERRORES",
    "FUENTES DE LAS FÓRMULAS",
    "CONTACTO",
)
# Funciones nuevas que el manual tiene que explicar
FUNCIONES = (
    "Auto-amargor", "Ajuste Físico", "Kardex", "Orden de Compra", "Etiqueta QR",
    "BeerXML", "Brewomatic", "gauge", "Altitud", "Priming",
)
# Textos que ya no deben aparecer
OBSOLETOS = ("v18", "v1.4.3", "50 recetas base")


def leer_manual():
    with open(FUENTE, "r", encoding="utf-8") as f:
        codigo = f.read()
    m = re.search(r'mensaje = """(.*?)"""', codigo, re.S)
    if not m:
        raise AssertionError("no se encontró el texto del manual en app_gestion.py")
    return m.group(1)


def main():
    texto = leer_manual()
    faltan = [s for s in SECCIONES if s not in texto]
    if faltan:
        print(f"❌ Faltan secciones en el manual: {faltan}")
        return 1
    sin_explicar = [f for f in FUNCIONES if f.lower() not in texto.lower()]
    if sin_explicar:
        print(f"❌ El manual no explica: {sin_explicar}")
        return 1
    viejos = [o for o in OBSOLETOS if o in texto]
    if viejos:
        print(f"❌ El manual todavía dice: {viejos}")
        return 1

    # El encabezado debe declarar la versión publicada
    version = re.search(r'APP_VERSION = "([^"]+)"', open(
        os.path.join(RAIZ, "app_gestion.py"), encoding="utf-8").read())
    if version and f"v{version.group(1)}" not in texto:
        print(f"❌ El manual no declara la versión v{version.group(1)}")
        return 1

    lineas = texto.strip().splitlines()
    print(f"   -> manual: {len(lineas)} líneas, {len(texto)} caracteres")
    print(f"   -> secciones: {len(SECCIONES)} | funciones explicadas: {len(FUNCIONES)}")
    print("MANUAL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
