#!/usr/bin/env python3
"""
Pasa las recetas reales validadas (recetario_real.json) al recetario de Cervecera VGB,
reemplazando las recetas genéricas.

- Mantiene los nombres del catálogo (IPA 3 - American IPA, etc.) para que el usuario
  encuentre lo mismo de siempre, pero con los ingredientes y pasos reales.
- Guarda el origen en "notas" y en "origen".
- Hace copia de seguridad del recetario anterior.

Uso:  python herramientas/aplicar_recetario_real.py
"""
import json, os, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BASE = os.path.join(RAIZ, "recetas_base.json")                 # lo que viene dentro de la app
PUBLICO = os.path.join(RAIZ, "recetas_cervecera_vgb.json")     # recetario que se publica en GitHub
REALES = os.path.join(AQUI, "recetario_real.json")


def main():
    if not os.path.exists(REALES):
        print(f"No existe {REALES}: corré primero reemplazar_genericas.py")
        return 1
    base = json.load(open(BASE, encoding="utf-8"))
    reales = json.load(open(REALES, encoding="utf-8"))

    if not os.path.exists(BASE.replace(".json", "_genericas.json")):
        shutil.copy(BASE, BASE.replace(".json", "_genericas.json"))
        print("Copia de seguridad -> recetas_base_genericas.json")

    nuevo, cambiadas, sin_datos = {}, [], []
    for nombre, datos in base.items():
        if nombre in reales:
            r = dict(reales[nombre])
            r.setdefault("notas", "")
            nuevo[nombre] = r
            cambiadas.append(nombre)
        else:
            nuevo[nombre] = datos          # se queda la vieja si no hubo reemplazo
            sin_datos.append(nombre)

    # Recetas reales que no correspondían a ninguna genérica (se agregan igual)
    extra = {n: d for n, d in reales.items() if n not in base}
    nuevo.update(extra)                      # recetas que no existen en el catálogo

    for destino in (BASE, PUBLICO):
        with open(destino, "w", encoding="utf-8") as f:
            json.dump(nuevo, f, ensure_ascii=False, indent=1)
        print(f"Escrito {os.path.basename(destino)}: {len(nuevo)} recetas")

    print(f"\nReemplazadas: {len(cambiadas)} | Nuevas: {len(extra)}")
    if sin_datos:
        print(f"Sin reemplazo ({len(sin_datos)}): " + ", ".join(sin_datos))
    if extra:
        print("Extra: " + ", ".join(extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
