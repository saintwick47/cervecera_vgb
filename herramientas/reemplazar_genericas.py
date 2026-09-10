#!/usr/bin/env python3
"""
Reemplaza las recetas genéricas de Cervecera VGB por recetas REALES de Brew-o-Matic.

Para cada receta genérica busca, en el listado público de Brew-o-Matic, una receta
del estilo correspondiente; la descarga completa, la convierte y la VALIDA con
nuestro motor (el OG/FG nuestro debe coincidir con el que publica Brew-o-Matic).
Solo se aceptan recetas que pasan la validación.

Uso:
    python herramientas/reemplazar_genericas.py            # todas
    python herramientas/reemplazar_genericas.py --solo 3  # probar con las primeras 3
    python herramientas/reemplazar_genericas.py --idioma   # solo probar descarga
"""
import json, os, re, sys, time, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.dirname(AQUI))
import importar_brewomatic as IB  # noqa: E402

LISTADO = os.path.join(AQUI, "bom_publicos.json")     # caché del listado público
SALIDA = os.path.join(AQUI, "recetario_real.json")    # recetas reales encontradas
INFORME = os.path.join(AQUI, "reemplazo_informe.txt")

# Nuestra receta genérica -> términos que debe contener el estilo de Brew-o-Matic
MAPA = {
    "Argentina 1 - Strong Scotch Ale":       ["17C", "Scotch Ale", "Wee Heavy"],
    "Argentina 2 - IPA Argenta":             ["IPA Argenta", "Argenta"],
    "Argentina 3 - Honey Light Lager":       ["1A", "Light Lager"],
    "IPA 1 - West Coast IPA":                ["West Coast", "21A"],
    "IPA 2 - Hazy IPA":                      ["21C", "Hazy", "NEIPA", "New England"],
    "IPA 3 - American IPA":                  ["21A"],
    "Negra 1 - American Stout":              ["20B", "American Stout"],
    "Negra 2 - Dry Stout":                   ["15B", "Irish Stout", "Dry Stout"],
    "Negra 3 - Sweet Stout":                 ["16A", "Sweet Stout", "Milk Stout"],
    "Red Lager 1 - International Amber Lager": ["2B"],
    "Red Lager 2 - American Red Lager":      ["2B", "Red Lager", "Amber Lager"],
    "Red Lager 3 - Red Cream Lager":         ["1C", "Cream Ale"],
    "Rubia 1 - Blonde Ale Básica":           ["18A"],
    "Rubia 2 - Honey Blonde Ale":            ["18A", "Honey"],
    "Rubia 3 - American Blonde":             ["18A", "Blonde"],
    "Wheat 1 - Hefeweizen":                  ["10A", "Hefeweizen"],
    "Wheat 2 - Dunkelweizen":                ["10B", "Dunkelweizen"],
    "Wheat 3 - American Wheat":              ["1D", "American Wheat"],
    "Porter 1 - Robust Porter":              ["20A", "Robust Porter"],
    "Porter 2 - Brown Porter":               ["13C", "Brown Porter"],
    "Porter 3 - Baltic Porter":              ["9C", "Baltic Porter"],
    "Pale Ale 1 - American Pale Ale":        ["18B"],
    "Pale Ale 2 - English Pale Ale":         ["11A", "11B", "11C", "English Pale", "Bitter"],
    "Pale Ale 3 - Aussie Sparkling Ale":     ["12B", "Australian Sparkling"],
    "Belgian 1 - Dubbel":                    ["26B", "Dubbel"],
    "Belgian 2 - Tripel":                    ["26C", "Tripel"],
    "Belgian 3 - Golden Strong":             ["25C", "Golden Strong"],
    "Saison 1 - Farmhouse Ale":              ["25B", "Saison"],
    "Saison 2 - Dark Saison":                ["25B", "Saison"],
    "Saison 3 - Super Saison":               ["25B", "Saison"],
    "Lager 1 - Munich Helles":               ["4A", "Helles"],
    "Lager 2 - Schwarzbier":                 ["8B", "Schwarzbier"],
    "Lager 3 - Vienna Lager":                ["7A", "Vienna"],
    "Barleywine 1 - English Barleywine":     ["17D", "English Barleywine"],
    "Barleywine 2 - American Barleywine":    ["22C", "American Barleywine"],
    "Pilsner 1 - German Pilsner":            ["5D", "German Pils"],
    "Pilsner 2 - Czech Pilsner":             ["3B", "Czech", "Bohemian"],
    "Pilsner 3 - Italian Pilsner":           ["5D", "Italian Pils", "Pilsner"],
    "Amber Ale 1 - American Amber":          ["19A", "American Amber"],
    "Amber Ale 2 - Irish Red Ale":           ["15A", "Irish Red"],
    "Amber Ale 3 - Belgian Amber":           ["26A", "Belgian Amber"],
    "Kölsch 1 - Traditional Kölsch":         ["5B", "Kölsch", "Kolsch"],
    "Kölsch 2 - Hoppy Kölsch":               ["5B", "Kölsch", "Kolsch"],
    "Scottish Ale 1 - 60 Shilling":          ["14A", "Scottish Light"],
    "Scottish Ale 2 - 80 Shilling":          ["14B", "Scottish Heavy"],
    "Cream Ale 1 - Standard Cream Ale":      ["1C", "Cream Ale"],
    "Cream Ale 2 - Vanilla Cream Ale":       ["1C", "Cream Ale"],
    "Witbier 1 - Traditional Witbier":       ["24A", "Witbier", "Wit"],
    "Witbier 2 - Orange Coriander Wit":      ["24A", "Witbier", "Wit"],
    "Witbier 3 - Black Wit":                 ["24A", "Witbier", "Wit"],
    "Marca - Sierra Nevada Pale Ale (Clon)": ["18B", "American Pale Ale"],
    "Marca - Guinness Draught (Clon)":       ["15B", "Irish Stout", "Dry Stout"],
    "Marca - Pilsner Urquell (Clon)":        ["3B", "Czech", "Bohemian"],
    "Marca - Heineken (Clon)":               ["5D", "German Pils"],
    "Marca - Stella Artois (Clon)":          ["5D", "Pilsner"],
    "Marca - Weihenstephaner Hefeweizen (Clon)": ["10A", "Hefeweizen"],
    "Marca - Duvel (Clon)":                  ["25C", "Golden Strong"],
    "Marca - Stone IPA (Clon)":              ["21A", "American IPA"],
    "Marca - Brooklyn Lager (Clon)":         ["2B", "Vienna", "Amber Lager"],
    "Marca - Anchor Liberty Ale (Clon)":     ["18B", "American Pale Ale"],
    "Marca - Paulaner Salvator (Clon)":      ["9B", "Doppelbock"],
    "Marca - Corona Extra (Clon)":           ["1A", "Light Lager", "Mexican"],
    "Nueva - NEIPA Tropical Haze":           ["21C", "NEIPA", "Hazy", "New England"],
    "Nueva - Gose de Frutos Rojos":          ["Gose", "23G", "27"],
    "Nueva - Imperial Stout Café":           ["20C", "Imperial Stout"],
    "Nueva - Oktoberfest Festbier":          ["4B", "6A", "Festbier", "Oktoberfest", "Märzen", "Marzen"],
}


def bajar_listado(usar_cache=True):
    if usar_cache and os.path.exists(LISTADO) and time.time() - os.path.getmtime(LISTADO) < 86400:
        with open(LISTADO, encoding="utf-8") as f:
            return json.load(f)
    url = "https://www.brew-o-matic.com.ar/recipe/public?google_id=undefined"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        datos = json.load(r)
    with open(LISTADO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)
    return datos


def estilo_de(r):
    return ((r.get("STYLE") or {}).get("NAME") or "")


CODIGO = re.compile(r"^\s*0*(\d{1,2})\s*([A-D])?\b")


def codigo_estilo(estilo):
    """'21A - American IPA' -> '21A' ; '01C - Cream Ale' -> '1C'."""
    m = CODIGO.match(estilo or "")
    return f"{int(m.group(1))}{m.group(2) or ''}".upper() if m else None


def candidatos(publicos, terminos, usados):
    """Recetas publicadas que encajan con los términos, con datos y sin repetir.

    Los códigos BJCP (1A, 21A, 15B...) se comparan EXACTOS: antes '1A' coincidía
    dentro de '21A' y elegía recetas de otro estilo.
    """
    codigos = {t.upper() for t in terminos if re.fullmatch(r"\d{1,2}[A-D]?", t)}
    palabras = [t.lower() for t in terminos if not re.fullmatch(r"\d{1,2}[A-D]?", t)]
    out = []
    for r in publicos:
        if r.get("_id") in usados:
            continue
        est = estilo_de(r)
        por_codigo = codigo_estilo(est) in codigos if codigos else False
        if not (por_codigo or any(w in est.lower() for w in palabras)):
            continue
        if not r.get("OG") or not r.get("BATCH_SIZE"):
            continue
        nombre = (r.get("NAME") or "").strip()
        # fuera las recetas sin nombre real (vacías, "2_", "asdf", etc.)
        if len(nombre) < 4 or not any(ch.isalpha() for ch in nombre):
            continue
        out.append(r)
    # Primero coincidencia exacta de código BJCP, después las que tienen más datos
    out.sort(key=lambda r: (0 if (codigos and codigo_estilo(estilo_de(r)) in codigos) else 1,
                            r.get("ABV") is None))
    return out


def validar_uno(rec):
    """(coincide, delta_og, delta_fg) comparando nuestro cálculo con Brew-o-Matic."""
    from brew_engine import BrewEngine as B
    bom = rec.get("_bom") or {}
    if not bom.get("og"):
        return False, None, None
    datos = {"maltas": rec["maltas"], "lupulos": rec["lupulos"], "agua_vol": rec["agua_vol"],
             "agua": {"ca": 25, "mg": 5, "hco3": 80, "ph": 7.3}, "tiempo_hervor": 60,
             "atenuacion_levadura": (rec["levaduras"][0]["atenuacion"] if rec.get("levaduras") else 75.0),
             "tolerancia_abv": 12, "metodo_fg": "simple", "temp_macerado": 66}
    res = B.calcular_receta_completa(datos, (bom.get("eficiencia") or 75) / 100.0, 400)
    dog = round(res["og"] - float(bom["og"]), 4)
    dfg = round(res["fg"] - float(bom["fg"]), 4) if bom.get("fg") else None
    ok = abs(dog) <= 0.002 and (dfg is None or abs(dfg) <= 0.002)
    return ok, dog, dfg


def main():
    solo = None
    if "--solo" in sys.argv:
        solo = int(sys.argv[sys.argv.index("--solo") + 1])
    publicos = bajar_listado()
    print(f"Listado público: {len(publicos)} recetas\n")

    reales, usados, informe = {}, set(), []
    pendientes = list(MAPA.items())
    if solo:
        pendientes = pendientes[:solo]

    for slot, terminos in pendientes:
        cands = candidatos(publicos, terminos, usados)
        elegido = None
        probados = 0
        for c in cands[:12]:
            probados += 1
            try:
                d = IB.descargar(c["_id"])
            except Exception as e:
                informe.append(f"[descarga] {slot}: {e}")
                continue
            if not (d.get("FERMENTABLES") or {}).get("FERMENTABLE"):
                continue
            rec = IB.convertir(d)
            ok, dog, dfg = validar_uno(rec)
            if ok:
                real_nombre = d.get("NAME") or c.get("NAME") or slot
                rec["origen"] = {
                    "receta": real_nombre,
                    "estilo": (d.get("STYLE") or {}).get("NAME"),
                    "url": f"https://www.brew-o-matic.com.ar/#/recipe/clone/{c['_id']}",
                    "fuente": "Brew-o-Matic (brew-o-matic.com.ar)",
                }
                reales[slot] = rec
                usados.add(c["_id"])
                elegido = (real_nombre, dog, dfg, c)
                break
        if elegido:
            n, dog, dfg, c = elegido
            linea = (f"OK   {slot:<44} <- {n[:38]:<38} "
                     f"ΔOG {dog:+.4f} ΔFG {(f'{dfg:+.4f}' if dfg is not None else '  -    ')}")
            print(linea, flush=True)
            informe.append(linea)
        else:
            linea = f"FALLA {slot:<44} (probé {probados} candidatos / {len(cands)} disponibles)"
            print(linea, flush=True)
            informe.append(linea)

        with open(SALIDA, "w", encoding="utf-8") as f:
            json.dump(reales, f, ensure_ascii=False, indent=1)
        with open(INFORME, "w", encoding="utf-8") as f:
            f.write("\n".join(informe) + "\n")

    print(f"\nReemplazos conseguidos: {len(reales)}/{len(pendientes)}")
    print(f"-> {SALIDA}")


if __name__ == "__main__":
    main()
