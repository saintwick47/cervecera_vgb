#!/usr/bin/env python3
"""
Verifica que las versiones de PC y Android de Cervecera VGB estén a la par.

No compara los archivos de interfaz (son distintos a propósito: uno es
customtkinter y el otro Flet), sino lo que tiene que coincidir siempre:
los módulos compartidos, el recetario, el esquema de la base de datos,
la versión y que cada función exista en LAS DOS versiones.

Uso:
    python herramientas/paridad.py            # verificar
    python herramientas/paridad.py --sync     # copiar los compartidos de PC a Android
    python herramientas/paridad.py --sync --desde android
"""
import json, os, re, shutil, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)                      # proyecto donde vive el script
ESPACIO = os.path.dirname(RAIZ)                   # carpeta que contiene los dos proyectos

# Archivos que deben ser byte a byte iguales en las dos versiones
COMPARTIDOS = [
    "brew_engine.py", "catalogo_ar.py", "bjcp_styles.py", "export_engine.py",
    "recetas_base.json", "recetas_cervecera_vgb.json",
    "herramientas/importar_brewomatic.py", "herramientas/reemplazar_genericas.py",
    "herramientas/aplicar_recetario_real.py", "herramientas/catalogo_brewomatic.py",
    "herramientas/paridad.py", "herramientas/LEEME_paridad.md",
    "herramientas/LEEME_importar_brewomatic.md",
]

# Funciones que deben existir en las dos apps (aunque se llamen distinto)
MARCAS = {
    "Refresco del recetario sin tocar las recetas del usuario":
        {"app.py": ["recetas_refrescables", "refrescar=True"],
         "main.py": ["recetas_refrescables", "_fusionar_recetario"]},
    "Levadura de la receta al importar (no forzar US-05)":
        {"app.py": ["datos.get('levaduras')"], "main.py": ["_levaduras_de"]},
    "Origen de la receta guardado en las notas":
        {"app.py": ["datos.get('notas'"], "main.py": ['d.get("notas"']},
    "Módulo de agua: perfiles objetivo y sales":
        {"app.py": ["calcular_sales", "PERFILES_AGUA_OBJETIVO"],
         "main.py": ["calcular_sales", "PERFILES_AGUA_OBJETIVO"]},
    "Fórmulas elegibles (IBU / FG / ABV)":
        {"app.py": ["formula_ibu", "metodo_fg", "formula_abv"],
         "main.py": ["formula_ibu", "metodo_fg", "formula_abv"]},
    "Perfiles de equipo":
        {"app.py": ["seed_equipment"], "main.py": ["seed_equipment"]},
    "Catálogo de insumos editable":
        {"app.py": ["seed_ingredients"], "main.py": ["seed_ingredients"]},
}


def localizar():
    """Devuelve (proyecto_pc, proyecto_android)."""
    pc = android = None
    candidatos = [RAIZ] + [os.path.join(ESPACIO, n) for n in ("beer_vgb", "beer_vgb_mobile")]
    for c in candidatos:
        if not os.path.isdir(c):
            continue
        if os.path.exists(os.path.join(c, "app.py")) and pc is None:
            pc = c
        if os.path.exists(os.path.join(c, "main.py")) and android is None:
            android = c
    return pc, android


def tablas_de(ruta_database):
    """Esquema: {tabla: [columnas]} leyendo las sentencias CREATE TABLE."""
    s = open(ruta_database, encoding="utf-8").read()
    bruto = dict(re.findall(r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\)\s*'''", s, re.S))
    esquema = {}
    for tabla, cuerpo in bruto.items():
        columnas = []
        for linea in cuerpo.splitlines():
            sin_comentario = linea.split("--")[0].strip().rstrip(",")
            if sin_comentario:
                columnas.append(re.sub(r"\s+", " ", sin_comentario))
        esquema[tabla] = columnas
    return esquema


def version_de(ruta, patron):
    s = open(ruta, encoding="utf-8").read()
    m = re.search(patron, s)
    return m.group(1) if m else "?"


def main():
    solo_compartidos = "--solo-compartidos" in sys.argv
    sincronizar = "--sync" in sys.argv
    desde = "pc"
    if "--desde" in sys.argv:
        desde = sys.argv[sys.argv.index("--desde") + 1].lower()

    pc, android = localizar()
    if not pc or not android:
        print(f"No encontré los dos proyectos (PC={pc}, Android={android})")
        return 1
    print(f"PC      : {pc}\nAndroid : {android}\n")

    fallos = []

    # ── 1) Archivos compartidos ──────────────────────────────────────────────
    print("── Archivos que deben ser idénticos ──")
    if sincronizar:
        origen, destino = (pc, android) if desde == "pc" else (android, pc)
        for rel in COMPARTIDOS:
            o, d = os.path.join(origen, rel), os.path.join(destino, rel)
            if os.path.exists(o):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(o, d)
        print(f"  (copiados desde {os.path.basename(origen)} hacia {os.path.basename(destino)})")

    for rel in COMPARTIDOS:
        a, b = os.path.join(pc, rel), os.path.join(android, rel)
        if not os.path.exists(a) or not os.path.exists(b):
            print(f"  ✗ {rel}  (falta en {'PC' if not os.path.exists(a) else 'Android'})")
            fallos.append(rel)
            continue
        if open(a, "rb").read() == open(b, "rb").read():
            print(f"  ✓ {rel}")
        else:
            print(f"  ✗ {rel}  DIFIERE")
            fallos.append(rel)

    if solo_compartidos:
        # Modo estricto (lo usa la build del APK): solo importan los archivos
        # que tienen que ser iguales sí o sí.
        if fallos:
            print(f"\nRESULTADO: {len(fallos)} archivo(s) compartido(s) distinto(s): {', '.join(fallos)}")
            return 1
        print("\nRESULTADO: archivos compartidos a la par ✓")
        return 0

    # ── 2) Versión ───────────────────────────────────────────────────────────
    print("\n── Versión ──")
    v_pc = version_de(os.path.join(pc, "app.py"), r'APP_VERSION\s*=\s*"([^"]+)"')
    v_and = version_de(os.path.join(android, "main.py"), r'APP_VERSION\s*=\s*"([^"]+)"')
    if v_pc == v_and:
        print(f"  ✓ PC y Android en la versión {v_pc}")
    else:
        print(f"  ✗ PC {v_pc} · Android {v_and}  (tienen que coincidir)")
        fallos.append(f"versión {v_pc} != {v_and}")

    # ── 3) Recetarios ────────────────────────────────────────────────────────
    print("\n── Recetario ──")
    for rel in ("recetas_base.json", "recetas_cervecera_vgb.json"):
        a, b = os.path.join(pc, rel), os.path.join(android, rel)
        if not (os.path.exists(a) and os.path.exists(b)):
            continue
        na = len(json.load(open(a, encoding="utf-8")))
        nb = len(json.load(open(b, encoding="utf-8")))
        if na == nb:
            print(f"  ✓ {rel}: {na} recetas en las dos")
        else:
            print(f"  ✗ {rel}: PC {na} · Android {nb}")
            fallos.append(f"{rel} {na} != {nb}")

    # ── 4) Esquema de la base de datos ───────────────────────────────────────
    print("\n── Base de datos (mismas tablas y columnas) ──")
    if os.path.exists(os.path.join(pc, "database.py")) and os.path.exists(os.path.join(android, "database.py")):
        ea = tablas_de(os.path.join(pc, "database.py"))
        eb = tablas_de(os.path.join(android, "database.py"))
        for tabla in sorted(set(ea) | set(eb)):
            if ea.get(tabla) == eb.get(tabla):
                print(f"  ✓ {tabla} ({len(ea.get(tabla, []))} columnas)")
            else:
                print(f"  ✗ {tabla}  PC={ea.get(tabla)}\n        Android={eb.get(tabla)}")
                fallos.append(f"tabla {tabla}")

    # ── 5) Funciones presentes en las dos apps ───────────────────────────────
    print("\n── Funciones que deben estar en las dos versiones ──")
    for descripcion, por_archivo in MARCAS.items():
        faltan = []
        for archivo, claves in por_archivo.items():
            ruta = os.path.join(pc if archivo == "app.py" else android, archivo)
            if not os.path.exists(ruta):
                faltan.append(f"{archivo} (no existe)")
                continue
            contenido = open(ruta, encoding="utf-8").read()
            faltan += [f"{archivo}: {k}" for k in claves if k not in contenido]
        if faltan:
            print(f"  ✗ {descripcion}  -> falta {', '.join(faltan)}")
            fallos.append(descripcion)
        else:
            print(f"  ✓ {descripcion}")

    # ── Resultado ────────────────────────────────────────────────────────────
    print()
    if fallos:
        print(f"RESULTADO: {len(fallos)} diferencia(s). Hay que ponerlas a la par:")
        for f in fallos:
            print(f"  · {f}")
        print("\nTip: python herramientas/paridad.py --sync   (copia los compartidos de PC a Android)")
        return 1
    print("RESULTADO: las dos versiones están a la par ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
