#!/usr/bin/env python3
"""
Importa recetas desde Brew-o-Matic (brew-o-matic.com.ar) al formato de Cervecera VGB.

Uso:
  python herramientas/importar_brewomatic.py <ID_o_URL> [<ID_o_URL> ...] [-o salida.json]

Ejemplo:
  python herramientas/importar_brewomatic.py https://www.brew-o-matic.com.ar/#/recipe/clone/RBK... -o recetas_brewomatic.json

El JSON generado se importa en la app con "📂 Importar JSON" (o "🔄 Buscar recetas nuevas").
"""
import json, os, re, sys, urllib.request

BASE = "https://www.brew-o-matic.com.ar/recipe/"


def _id_de(valor: str) -> str:
    """Acepta una URL de Brew-o-Matic o directamente el ID."""
    valor = valor.strip()
    m = re.search(r"/recipe/(?:clone/)?([^/?#]+)", valor)
    return m.group(1) if m else valor


def descargar(rid: str) -> dict:
    url = BASE + rid
    req = urllib.request.Request(url, headers={"User-Agent": "CerveceraVGB"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def convertir(d: dict) -> dict:
    """Brew-o-Matic (BeerXML/JSON) -> formato Cervecera VGB."""
    maltas = []
    for f in (d.get("FERMENTABLES", {}) or {}).get("FERMENTABLE", []) or []:
        pot = float(f.get("POTENTIAL") or 1.030)
        try:
            pot = float(pot)
        except (TypeError, ValueError):
            pot = 1.030
        # potential (PPG, ej 1.037) -> extracto en L°/kg (x 8.345)
        extracto = round((pot - 1.0) * 1000 * 8.345) if pot < 2 else round(pot)
        maltas.append({
            "nombre": f.get("NAME", "Malta"),
            "cantidad": round(float(f.get("AMOUNT") or 0), 2),
            "extracto": extracto or 300,
            "color": round(float(f.get("COLOR") or 2), 1),
        })
    lupulos = []
    for h in (d.get("HOPS", {}) or {}).get("HOP", []) or []:
        lupulos.append({
            "nombre": h.get("NAME", "Lúpulo"),
            "cantidad": round(float(h.get("AMOUNT") or 0) * 1000, 1),   # kg -> g
            "aa": round(float(h.get("ALPHA") or 5), 1),
            "tiempo": int(float(h.get("TIME") or 60)),
            "formato": "pellet" if str(h.get("FORM", "pellet")).lower().startswith("pel") else "flor",
        })
    levaduras = []
    for y in (d.get("YEASTS", {}) or {}).get("YEAST", []) or []:
        levaduras.append({
            "nombre": y.get("NAME", "Levadura"),
            "atenuacion": float(y.get("ATTENUATION") or 75),
            "tolerancia": 12.0,
        })
    estilo = (d.get("STYLE") or {}).get("NAME") or "Estilo Base"
    return {
        "style": estilo,
        "notas": (f"Receta original: {d.get('NAME')} · {estilo} · "
                  f"fuente Brew-o-Matic (brew-o-matic.com.ar)"),
        "agua_vol": float(d.get("BATCH_SIZE") or 20),
        "fg_estimada": float(d.get("FG") or 1.010),
        "granos_base": round(sum(m["cantidad"] for m in maltas), 2),
        "granos_especiales": 0.0,
        "maltas": maltas,
        "lupulos": lupulos,
        "levaduras": levaduras,
        "ph_macerado_objetivo": "",
        # referencia de Brew-o-Matic para validar
        "_bom": {"og": d.get("OG"), "fg": d.get("FG"),
                 "eficiencia": d.get("EFFICIENCY"), "estilo": (d.get("STYLE") or {}).get("NAME")},
    }


def validar(recetas):
    """Compara el OG/FG que calcula Cervecera VGB con los que publica Brew-o-Matic."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from brew_engine import BrewEngine as B
    except ImportError as e:
        print(f"\n(No se pudo validar: {e})")
        return
    filas, dentro, total = [], 0, 0
    for nombre, r in recetas.items():
        bom = r.get("_bom") or {}
        if bom.get("og") is None:
            continue
        datos = {"maltas": r["maltas"], "lupulos": r["lupulos"], "agua_vol": r["agua_vol"],
                 "agua": {"ca": 25, "mg": 5, "hco3": 80, "ph": 7.3}, "tiempo_hervor": 60,
                 "atenuacion_levadura": (r["levaduras"][0]["atenuacion"] if r.get("levaduras") else 75.0),
                 "tolerancia_abv": 12, "metodo_fg": "simple", "temp_macerado": 66}
        res = B.calcular_receta_completa(datos, (bom.get("eficiencia") or 75) / 100.0, 400)
        dog = round(res["og"] - float(bom["og"]), 4)
        dfg = round(res["fg"] - float(bom["fg"]), 4) if bom.get("fg") else None
        ok = abs(dog) <= 0.002 and (dfg is None or abs(dfg) <= 0.002)
        total += 1; dentro += 1 if ok else 0
        filas.append((nombre, float(bom["og"]), res["og"], dog,
                      (float(bom["fg"]) if bom.get("fg") else None), res["fg"], dfg,
                      res["ibu"], res["srm"], res["abv"], ok))
    if not filas:
        return
    print("\n=== VALIDACIÓN: Cervecera VGB vs Brew-o-Matic ===")
    print(f"{'Receta':<38}{'OG BOM':>8}{'OG VGB':>8}{'Δ':>8}{'FG BOM':>8}{'FG VGB':>8}{'Δ':>8}   IBU   SRM   ABV")
    for (n, o1, o2, d1, f1, f2, d2, ibu, srm, abv, ok) in filas:
        marca = "OK " if ok else "!! "
        print(f"{marca}{n[:35]:<35}{o1:>8.4f}{o2:>8.4f}{d1:>+8.4f}"
              f"{(f'{f1:.4f}' if f1 else '-'):>8}{(f2 if f2 else 0):>8.4f}"
              f"{(f'{d2:+.4f}' if d2 is not None else '-'):>8}{ibu:>6.1f}{srm:>6.1f}{abv:>6.2f}")
    print(f"\nCoinciden (Δ ≤ 0,002): {dentro}/{total} recetas")
    with open("validacion_brewomatic.csv", "w", encoding="utf-8") as f:
        f.write("receta;og_bom;og_vgb;delta_og;fg_bom;fg_vgb;delta_fg;ibu;color;abv;coincide\n")
        for (n, o1, o2, d1, f1, f2, d2, ibu, srm, abv, ok) in filas:
            f.write(f"{n};{o1};{o2};{d1:+.4f};{f1 or ''};{f2};"
                    f"{(f'{d2:+.4f}' if d2 is not None else '')};{ibu};{srm};{abv};{'si' if ok else 'no'}\n")
    print("Detalle guardado en validacion_brewomatic.csv")


def main():
    argv = sys.argv[1:]
    # Permite pasar un archivo .txt con una URL/ID por línea
    expandido = []
    for a in argv:
        if not a.startswith("-") and os.path.exists(a) and a.lower().endswith((".txt", ".list")):
            with open(a, encoding="utf-8") as fh:
                expandido += [ln.strip() for ln in fh
                              if ln.strip() and not ln.strip().startswith("#")]
        else:
            expandido.append(a)
    argv = expandido
    salida = "recetas_brewomatic.json"
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == "-o":
            salida = argv[i + 1]; i += 2; continue
        args.append(argv[i]); i += 1
    if not args:
        print(__doc__); return
    recetas = {}
    for valor in args:
        rid = _id_de(valor)
        try:
            d = descargar(rid)
            nombre = d.get("NAME") or rid
            recetas[nombre] = convertir(d)
            print(f"✓ {nombre}  (OG {d.get('OG')} / FG {d.get('FG')})")
        except Exception as e:
            print(f"✗ {valor}: {e}")
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(recetas, f, ensure_ascii=False, indent=1)
    print(f"\n-> {len(recetas)} recetas guardadas en {salida}")
    validar(recetas)


if __name__ == "__main__":
    main()
