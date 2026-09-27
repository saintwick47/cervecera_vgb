#!/usr/bin/env python3
"""
Corre TODAS las verificaciones del proyecto y muestra un resumen corto.

Uso:
    python verificar.py            # todo (tests + paridad + pruebas de interfaz)
    python verificar.py rapido     # sin las pruebas que abren ventanas

Cada verificación imprime una línea. Sale con código 1 si algo falla.
"""
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
PY_PRUEBAS = os.path.join(RAIZ, ".venv-test", "bin", "python")
if not os.path.exists(PY_PRUEBAS):
    PY_PRUEBAS = sys.executable

VERIFICACIONES = [
    ("tests del motor, la BD y la lógica",
     [PY_PRUEBAS, "-m", "unittest", "test_cervecera"], RAIZ, "ventana"),
    ("paleta de colores del sistema de diseño",
     [sys.executable, "probar_paleta.py"], RAIZ, None),
    ("paridad PC ↔ Android",
     [sys.executable, os.path.join(RAIZ, "herramientas", "paridad.py")], RAIZ, None),
    ("maestro-detalle de Insumos/Inventario (abre la app)",
     [sys.executable, "probar_maestro_detalle_ui.py"], RAIZ, "ventana"),
    ("catálogo de Insumos: filtros, rail, paginación, ID y duplicar (abre la app)",
     [sys.executable, "probar_catalogo_insumos.py"], RAIZ, "ventana"),
    ("barra de menú del diseño (Archivo · Herramientas · Ayuda)",
     [sys.executable, "probar_menu.py"], RAIZ, "ventana"),
    ("Inventario: KPIs, ubicaciones, estados y niveles (abre la app)",
     [sys.executable, "probar_inventario_ui.py"], RAIZ, "ventana"),
    ("rail de cocciones programadas y distribución de espacio (abre la app)",
     [sys.executable, "probar_cocciones_ui.py"], RAIZ, "ventana"),
    ("Equipos: 4 sub-pestañas, importación y Balance Teórico (abre la app)",
     [sys.executable, "probar_equipos_ui.py"], RAIZ, "ventana"),
    ("Recetas: columnas del diseño (% Total, Uso, g/L, IBU Aporte) (abre la app)",
     [sys.executable, "probar_receta_columnas.py"], RAIZ, "ventana"),
    ("arranque y uso completo de la app, sin errores en el log (abre la app)",
     [sys.executable, "probar_arranque.py"], RAIZ, "ventana"),
]


def main():
    rapido = "rapido" in sys.argv
    resultados = []
    for nombre, comando, carpeta, necesita in VERIFICACIONES:
        if rapido and necesita == "ventana":
            resultados.append((nombre, None, "salteada"))
            continue
        entorno = dict(os.environ)
        entorno["PYTHONPATH"] = carpeta + os.pathsep + entorno.get("PYTHONPATH", "")
        entorno["VGB_TEST"] = "1"      # las pruebas no escriben el log del usuario
        r = subprocess.run(comando, cwd=carpeta, env=entorno,
                           capture_output=True, text=True, timeout=600)
        salida = (r.stdout + r.stderr)
        # Buscamos el veredicto dentro de la salida de cada prueba
        if r.returncode != 0:
            estado = "FALLA"
        elif "FAILED" in salida or "diferencia(s)" in salida or "Traceback" in salida:
            estado = "FALLA"
        else:
            estado = "OK"
        detalle = ""
        for linea in salida.splitlines():
            if any(m in linea for m in ("Ran ", "RESULTADO:", "TODO OK", "OK ✓",
                                        "diferencia(s)", "FAILED")):
                detalle = linea.strip()
        resultados.append((nombre, estado, detalle))

    print("=" * 72)
    print("  VERIFICACIÓN DE CERVECERA VGB")
    print("=" * 72)
    for nombre, estado, detalle in resultados:
        if estado is None:
            icono = "·"
        else:
            icono = {"OK": "✅", "FALLA": "❌"}.get(estado, "·")
        print(f"  {icono} {nombre}")
        if detalle:
            print(f"      {detalle}")
    fallas = [n for n, e, _ in resultados if e == "FALLA"]
    print("-" * 72)
    if fallas:
        print(f"  ❌ {len(fallas)} verificación(es) con problemas: {', '.join(fallas)}")
        return 1
    print("  ✅ TODO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
