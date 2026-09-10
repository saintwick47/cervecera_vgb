#!/usr/bin/env python3
"""
Genera el catálogo descargable de recetas públicas de Brew-o-Matic.

Las recetas NO se meten en la app: se publican como archivo descargable
(JSON + CSV) para que la gente las consulte y, si quiere, las importe.

Uso:
    python herramientas/catalogo_brewomatic.py [carpeta_salida]
"""
import csv, datetime, json, os, sys, urllib.request

URL = "https://www.brew-o-matic.com.ar/recipe/public?google_id=undefined"
WEB_RECETA = "https://www.brew-o-matic.com.ar/#/recipe/clone/"


def descargar():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def fecha(valor):
    """publishDate viene en milisegundos o como texto."""
    if isinstance(valor, (int, float)) and valor > 0:
        try:
            # algunos vienen en segundos, otros en milisegundos
            seg = valor / 1000 if valor > 1e11 else valor
            return datetime.datetime.utcfromtimestamp(seg).strftime("%Y-%m-%d")
        except Exception:
            return ""
    return str(valor or "")[:10]


def limpiar(r):
    return {
        "nombre": (r.get("NAME") or "").strip(),
        "estilo": ((r.get("STYLE") or {}).get("NAME") or "").strip(),
        "og": r.get("OG"),
        "abv": r.get("ABV"),
        "ibu": r.get("CALCIBU"),
        "color_srm": r.get("CALCCOLOUR"),
        "litros": r.get("BATCH_SIZE"),
        "publicada": fecha(r.get("publishDate")),
        "autor": ((r.get("owner") or {}).get("name") or r.get("BREWER") or "").strip()
        if isinstance(r.get("owner"), dict) else (r.get("BREWER") or "").strip(),
        "url": WEB_RECETA + str(r.get("_id", "")),
    }


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(salida, exist_ok=True)
    crudas = descargar()
    recetas = [limpiar(r) for r in crudas]
    recetas = [r for r in recetas if r["nombre"] and r["estilo"]]
    recetas.sort(key=lambda r: (r["estilo"], r["nombre"]))

    datos = {
        "fuente": "Brew-o-Matic — https://www.brew-o-matic.com.ar",
        "creditos": ("Recetas publicadas por la comunidad de Brew-o-Matic "
                     "(Lautaro Cozzani / Somos Cerveceros, licencia MIT)."),
        "descargado": datetime.date.today().isoformat(),
        "total": len(recetas),
        "aviso": ("Cada receta incluye el enlace a su ficha original. Los valores de "
                  "OG/ABV/IBU/color son los publicados por Brew-o-Matic."),
        "recetas": recetas,
    }
    j = os.path.join(salida, "recetas_brewomatic_catalogo.json")
    with open(j, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)

    c = os.path.join(salida, "recetas_brewomatic_catalogo.csv")
    with open(c, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(recetas[0].keys()), delimiter=";")
        w.writeheader()
        w.writerows(recetas)

    print(f"{len(recetas)} recetas -> {j} ({os.path.getsize(j)/1048576:.1f} MB)")
    print(f"{len(recetas)} recetas -> {c} ({os.path.getsize(c)/1048576:.1f} MB)")
    estilos = {}
    for r in recetas:
        estilos[r["estilo"]] = estilos.get(r["estilo"], 0) + 1
    print(f"Estilos distintos: {len(estilos)}")


if __name__ == "__main__":
    main()
