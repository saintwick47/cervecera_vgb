# bjcp_styles.py
# /home/saintwick/Escritorio/beer_vgb/bjcp_styles.py
# 2024-05-17
# Autor: SaintWick

"""
Base de datos completa de estilos BJCP 2021 y motor de comparación.
Cubre más de 80 estilos oficiales para validación en tiempo real.
"""

# Rangos oficiales basados en BJCP 2021 Guidelines
STYLES = {
    # --- LAGER AMERICANA ---
    "American Light Lager": {"og": [1.028, 1.040], "fg": [1.004, 1.010], "ibu": [8, 12], "srm": [2, 3]},
    "American Lager": {"og": [1.040, 1.050], "fg": [1.004, 1.010], "ibu": [8, 15], "srm": [2, 4]},
    "Premium American Lager": {"og": [1.046, 1.056], "fg": [1.008, 1.012], "ibu": [15, 25], "srm": [2, 6]},
    "American Ice Lager": {"og": [1.050, 1.060], "fg": [1.008, 1.012], "ibu": [12, 22], "srm": [2, 5]},
    "Malt Liquor": {"og": [1.060, 1.080], "fg": [1.010, 1.020], "ibu": [12, 25], "srm": [2, 6]},

    # --- LAGER INTERNACIONAL ---
    "International Pale Lager": {"og": [1.042, 1.050], "fg": [1.008, 1.012], "ibu": [18, 25], "srm": [2, 4]},
    "International Amber Lager": {"og": [1.042, 1.050], "fg": [1.010, 1.014], "ibu": [18, 25], "srm": [8, 15]},
    "International Dark Lager": {"og": [1.044, 1.056], "fg": [1.008, 1.014], "ibu": [18, 25], "srm": [14, 25]},

    # --- LAGER CHECA ---
    "Czech Pale Lager": {"og": [1.044, 1.056], "fg": [1.013, 1.017], "ibu": [30, 45], "srm": [3, 7]},
    "Czech Premium Pale Lager": {"og": [1.044, 1.060], "fg": [1.014, 1.016], "ibu": [35, 45], "srm": [3, 7]},
    "Czech Amber Lager": {"og": [1.044, 1.060], "fg": [1.014, 1.018], "ibu": [25, 40], "srm": [10, 18]},
    "Czech Dark Lager": {"og": [1.044, 1.056], "fg": [1.014, 1.018], "ibu": [20, 35], "srm": [20, 35]},

    # --- LAGER EUROPEA PALIDA ---
    "Munich Helles": {"og": [1.045, 1.051], "fg": [1.008, 1.012], "ibu": [16, 22], "srm": [3, 5]},
    "Festbier": {"og": [1.054, 1.057], "fg": [1.010, 1.012], "ibu": [18, 25], "srm": [4, 7]},
    "Helles Bock": {"og": [1.064, 1.072], "fg": [1.011, 1.018], "ibu": [23, 35], "srm": [6, 11]},

    # --- CERVEZA EUROPEA PALIDA AMARGA ---
    "German Pils": {"og": [1.044, 1.050], "fg": [1.008, 1.013], "ibu": [22, 40], "srm": [2, 5]},

    # --- LAGER EUROPEA AMBAR ---
    "Vienna Lager": {"og": [1.046, 1.052], "fg": [1.010, 1.014], "ibu": [18, 30], "srm": [10, 16]},
    "Altbier": {"og": [1.044, 1.052], "fg": [1.010, 1.015], "ibu": [25, 50], "srm": [11, 17]},
    "California Common": {"og": [1.048, 1.054], "fg": [1.011, 1.014], "ibu": [30, 45], "srm": [8, 14]},
    "Düssel Alt": {"og": [1.046, 1.054], "fg": [1.010, 1.014], "ibu": [35, 50], "srm": [11, 17]},

    # --- LAGER EUROPEA OSCURA ---
    "Schwarzbier": {"og": [1.046, 1.052], "fg": [1.010, 1.014], "ibu": [22, 32], "srm": [17, 30]},

    # --- LAGER EUROPEA AMBAR MALTA ---
    "Märzen": {"og": [1.054, 1.060], "fg": [1.012, 1.016], "ibu": [20, 28], "srm": [8, 14]},

    # --- LAGER EUROPEA OSCURA MALTA ---
    "Dunkles Bock": {"og": [1.064, 1.072], "fg": [1.013, 1.019], "ibu": [20, 30], "srm": [14, 22]},
    "Doppelbock": {"og": [1.072, 1.092], "fg": [1.016, 1.024], "ibu": [16, 26], "srm": [6, 25]},
    "Eisbock": {"og": [1.078, 1.120], "fg": [1.020, 1.035], "ibu": [25, 35], "srm": [12, 30]},

    # --- CERVEZA DE TRIGO ALEMANA ---
    "Weissbier": {"og": [1.044, 1.052], "fg": [1.008, 1.014], "ibu": [8, 15], "srm": [2, 8]},
    "Dunkles Weissbier": {"og": [1.044, 1.052], "fg": [1.008, 1.014], "ibu": [10, 18], "srm": [10, 18]},
    "Weizenbock": {"og": [1.064, 1.080], "fg": [1.013, 1.019], "ibu": [15, 30], "srm": [6, 25]},
    "Roggenbier": {"og": [1.046, 1.056], "fg": [1.010, 1.014], "ibu": [10, 20], "srm": [10, 18]},

    # --- CERVEZA AMARGA BRITANICA ---
    "Ordinary Bitter": {"og": [1.032, 1.040], "fg": [1.004, 1.008], "ibu": [25, 35], "srm": [4, 12]},
    "Best Bitter": {"og": [1.040, 1.048], "fg": [1.008, 1.012], "ibu": [25, 40], "srm": [5, 16]},
    "Strong Bitter": {"og": [1.048, 1.060], "fg": [1.010, 1.016], "ibu": [30, 50], "srm": [6, 18]},

    # --- CERVEZA PALIDA DE LA COMMONWEALTH ---
    "Australian Sparkling Ale": {"og": [1.038, 1.050], "fg": [1.004, 1.006], "ibu": [20, 30], "srm": [3, 7]},
    "Australian Pale Ale": {"og": [1.040, 1.050], "fg": [1.008, 1.012], "ibu": [25, 40], "srm": [4, 10]},

    # --- CERVEZA MARRON BRITANICA ---
    "English Brown Ale": {"og": [1.040, 1.052], "fg": [1.008, 1.014], "ibu": [20, 30], "srm": [12, 22]},
    "English Dark Mild": {"og": [1.030, 1.038], "fg": [1.008, 1.013], "ibu": [10, 25], "srm": [12, 25]},

    # --- CERVEZA ESCOCESA ---
    "Scottish Light": {"og": [1.030, 1.035], "fg": [1.010, 1.014], "ibu": [8, 20], "srm": [9, 17]},
    "Scottish Heavy": {"og": [1.035, 1.040], "fg": [1.010, 1.015], "ibu": [10, 25], "srm": [9, 17]},
    "Scottish Export": {"og": [1.040, 1.054], "fg": [1.010, 1.016], "ibu": [15, 30], "srm": [9, 17]},
    "Wee Heavy": {"og": [1.070, 1.100], "fg": [1.018, 1.040], "ibu": [17, 35], "srm": [14, 25]},

    # --- CERVEZA IRLANDESA ---
    "Irish Red Ale": {"og": [1.044, 1.060], "fg": [1.010, 1.014], "ibu": [17, 28], "srm": [9, 18]},
    "Irish Stout": {"og": [1.036, 1.044], "fg": [1.007, 1.011], "ibu": [30, 45], "srm": [25, 40]},
    "Irish Extra Stout": {"og": [1.052, 1.062], "fg": [1.010, 1.014], "ibu": [35, 50], "srm": [30, 40]},

    # --- CERVEZA OSCURA BRITANICA ---
    "Sweet Stout": {"og": [1.044, 1.060], "fg": [1.012, 1.024], "ibu": [20, 40], "srm": [25, 40]},
    "Oatmeal Stout": {"og": [1.048, 1.065], "fg": [1.010, 1.018], "ibu": [25, 40], "srm": [22, 40]},
    "Tropical Stout": {"og": [1.056, 1.075], "fg": [1.010, 1.018], "ibu": [30, 50], "srm": [30, 40]},
    "Foreign Extra Stout": {"og": [1.056, 1.075], "fg": [1.010, 1.018], "ibu": [30, 70], "srm": [30, 40]},
    "British Brown Porter": {"og": [1.040, 1.052], "fg": [1.008, 1.014], "ibu": [25, 35], "srm": [20, 30]},
    "Robust Porter": {"og": [1.050, 1.065], "fg": [1.012, 1.016], "ibu": [25, 50], "srm": [22, 35]},

    # --- CERVEZA FUERTE BRITANICA ---
    "British Strong Ale": {"og": [1.055, 1.070], "fg": [1.010, 1.018], "ibu": [35, 55], "srm": [8, 22]},
    "Old Ale": {"og": [1.060, 1.090], "fg": [1.015, 1.025], "ibu": [30, 60], "srm": [12, 25]},
    "English Barleywine": {"og": [1.080, 1.120], "fg": [1.018, 1.030], "ibu": [35, 70], "srm": [8, 22]},

    # --- CERVEZA DE TRIGO AMERICANA ---
    "American Wheat Beer": {"og": [1.040, 1.055], "fg": [1.008, 1.013], "ibu": [15, 30], "srm": [3, 6]},

    # --- CERVEZA AMBAR AMERICANA ---
    "American Amber Ale": {"og": [1.045, 1.060], "fg": [1.010, 1.015], "ibu": [25, 40], "srm": [10, 17]},

    # --- CERVEZA MARRON AMERICANA ---
    "American Brown Ale": {"og": [1.045, 1.060], "fg": [1.010, 1.016], "ibu": [20, 30], "srm": [18, 26]},

    # --- PALE ALE AMERICANA ---
    "American Pale Ale": {"og": [1.045, 1.060], "fg": [1.010, 1.015], "ibu": [30, 50], "srm": [5, 10]},
    "American Blonde Ale": {"og": [1.038, 1.054], "fg": [1.008, 1.013], "ibu": [15, 28], "srm": [3, 6]},

    # --- CERVEZA FUERTE AMERICANA ---
    "American Strong Ale": {"og": [1.060, 1.090], "fg": [1.012, 1.020], "ibu": [50, 80], "srm": [8, 20]},
    "American Barleywine": {"og": [1.080, 1.120], "fg": [1.016, 1.030], "ibu": [50, 100], "srm": [10, 19]},
    "Wheatwine": {"og": [1.080, 1.120], "fg": [1.015, 1.025], "ibu": [30, 60], "srm": [6, 14]},

    # --- IPA AMERICANA ---
    "English IPA": {"og": [1.050, 1.075], "fg": [1.010, 1.018], "ibu": [40, 60], "srm": [6, 14]},
    "American IPA": {"og": [1.056, 1.070], "fg": [1.008, 1.014], "ibu": [40, 70], "srm": [5, 10]},
    "Imperial IPA": {"og": [1.070, 1.090], "fg": [1.012, 1.020], "ibu": [60, 100], "srm": [6, 14]},
    "Belgian IPA": {"og": [1.056, 1.070], "fg": [1.008, 1.016], "ibu": [40, 70], "srm": [5, 12]},
    "Black IPA": {"og": [1.056, 1.075], "fg": [1.010, 1.016], "ibu": [50, 70], "srm": [25, 40]},

    # --- ALE BELGA Y FRANCESA ---
    "Witbier": {"og": [1.044, 1.052], "fg": [1.008, 1.012], "ibu": [10, 20], "srm": [2, 4]},
    "Belgian Pale Ale": {"og": [1.048, 1.054], "fg": [1.010, 1.014], "ibu": [20, 30], "srm": [6, 13]},
    "Bière de Garde": {"og": [1.060, 1.080], "fg": [1.008, 1.016], "ibu": [18, 28], "srm": [6, 19]},
    "Belgian Blonde Ale": {"og": [1.062, 1.075], "fg": [1.008, 1.014], "ibu": [15, 30], "srm": [4, 7]},
    "Saison": {"og": [1.048, 1.065], "fg": [1.002, 1.012], "ibu": [20, 35], "srm": [4, 14]},
    "Berliner Weisse": {"og": [1.028, 1.032], "fg": [1.003, 1.006], "ibu": [3, 8], "srm": [2, 3]},
    "Flanders Red Ale": {"og": [1.048, 1.057], "fg": [1.002, 1.012], "ibu": [10, 25], "srm": [10, 16]},
    "Oud Bruin": {"og": [1.040, 1.054], "fg": [1.008, 1.012], "ibu": [15, 25], "srm": [12, 18]},
    "Lambic": {"og": [1.040, 1.054], "fg": [1.001, 1.010], "ibu": [0, 10], "srm": [3, 7]},
    "Gueuze": {"og": [1.040, 1.060], "fg": [1.000, 1.006], "ibu": [0, 10], "srm": [3, 7]},
    "Fruit Lambic": {"og": [1.040, 1.060], "fg": [1.000, 1.010], "ibu": [0, 10], "srm": [3, 12]},

    # --- ALE FUERTE BELGA ---
    "Belgian Single": {"og": [1.044, 1.054], "fg": [1.004, 1.010], "ibu": [15, 25], "srm": [3, 6]},
    "Dubbel": {"og": [1.062, 1.075], "fg": [1.008, 1.018], "ibu": [15, 25], "srm": [10, 17]},
    "Tripel": {"og": [1.075, 1.085], "fg": [1.008, 1.014], "ibu": [20, 40], "srm": [4, 7]},
    "Belgian Golden Strong Ale": {"og": [1.070, 1.095], "fg": [1.005, 1.016], "ibu": [22, 35], "srm": [3, 6]},
    "Belgian Dark Strong Ale": {"og": [1.075, 1.110], "fg": [1.010, 1.024], "ibu": [20, 35], "srm": [12, 22]},

    # --- STOUT AMERICANA ---
    "American Stout": {"og": [1.050, 1.075], "fg": [1.010, 1.022], "ibu": [35, 60], "srm": [30, 40]},
    "Imperial Stout": {"og": [1.075, 1.115], "fg": [1.018, 1.030], "ibu": [50, 80], "srm": [30, 50]},

    # --- PORTER AMERICANA ---
    "Baltic Porter": {"og": [1.060, 1.090], "fg": [1.014, 1.024], "ibu": [20, 40], "srm": [17, 30]},

    # --- HISTORICAS Y OTRAS ---
    "Gose": {"og": [1.036, 1.040], "fg": [1.004, 1.008], "ibu": [5, 12], "srm": [2, 5]},
    "Kentucky Common": {"og": [1.040, 1.055], "fg": [1.008, 1.012], "ibu": [15, 30], "srm": [8, 18]},
    "Lichtenhainer": {"og": [1.040, 1.052], "fg": [1.006, 1.010], "ibu": [5, 15], "srm": [3, 6]},
    "Sahti": {"og": [1.056, 1.080], "fg": [1.010, 1.020], "ibu": [5, 15], "srm": [4, 12]},
    "Braggot": {"og": [1.060, 1.100], "fg": [1.010, 1.020], "ibu": [15, 50], "srm": [5, 25]}
}

def comparar_con_estilo(style_name, og, fg, ibu, srm):
    """Compara los parámetros calculados con el estilo BJCP seleccionado"""
    if style_name not in STYLES:
        return f"⚠️ Estilo '{style_name}' no encontrado en la base BJCP local."

    ranges = STYLES[style_name]
    resultados = []

    def evaluar(param_name, value, rango, is_gravity=False):
        low, high = rango
        if low <= value <= high:
            return f"✅ {param_name}: {value:.3f} (Rango: {low:.3f}-{high:.3f})" if is_gravity else f"✅ {param_name}: {value:.1f} (Rango: {low:.0f}-{high:.0f})"
        else:
            diferencia = value - high if value > high else value - low
            diff_str = f"{diferencia:+.3f}" if is_gravity else f"{diferencia:+.1f}"
            return f"❌ {param_name}: {value:.3f} (Rango: {low:.3f}-{high:.3f} | Diff: {diff_str})" if is_gravity else f"❌ {param_name}: {value:.1f} (Rango: {low:.0f}-{high:.0f} | Diff: {diff_str})"

    resultados.append(evaluar("OG ", og, ranges["og"], is_gravity=True))
    resultados.append(evaluar("FG ", fg, ranges["fg"], is_gravity=True))
    resultados.append(evaluar("IBU", ibu, ranges["ibu"]))
    resultados.append(evaluar("SRM", srm, ranges["srm"]))

    return "\n".join(resultados)

def get_style_list():
    """Devuelve la lista de estilos para el ComboBox de la UI"""
    return ["Auto (Sugerir)"] + list(STYLES.keys())
