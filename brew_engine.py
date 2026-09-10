# brew_engine.py
# /home/saintwick/Escritorio/beer_vgb/brew_engine.py
# 2024-05-17 (Actualizado v3 - Cumple Informe Técnico)
# Autor: saintwick
"""
Motor de cálculos cerveceros profesionales.
Implementa fórmulas estándar: PPG (OG), Tinseth (IBU), Morey/Daniels (SRM), Palmer (pH).
Incluye correcciones por altitud, formatos de lúpulo y automatización de levaduras.

v3: Añade Strike Water (Informe §2.B), Corrección Densímetro ASBC (§4.DíaCocción),
    y tasa de evaporación en cálculo de aguas.
"""
import math
from logger import logger

class BrewEngine:
    """Motor de cálculos técnicos de elaboración de cerveza."""

    # ==========================================
    # MÓDULO DENSIDAD Y ATENUACIÓN
    # ==========================================
    @staticmethod
    def calcular_og(maltas, volumen_lote, eficiencia=0.75):
        if volumen_lote <= 0: return 1.000
        puntos_totales = 0.0
        for malta in maltas:
            cantidad = malta.get('cantidad', 0)
            extracto = malta.get('extracto', 300)
            puntos_totales += (cantidad * extracto * eficiencia)
        gravedad = puntos_totales / volumen_lote
        og = 1.0 + (gravedad / 1000.0)
        return round(og, 4)

    @staticmethod
    def calcular_fg(og, atenuacion_levadura=75.0, metodo="normal",
                    temp_macerado=66.0, especiales_pct=0.0):
        """
        FG por atenuación. (Fase 0)
        metodo='simple'  -> solo atenuación de la levadura (como antes)
        metodo='normal'  -> ajusta la atenuación por TEMPERATURA DE MACERADO
                            (beta-amilasa <65 C = más fermentable; alfa-amilasa
                            >67 C = más dextrinas) y por maltas especiales.
        Referencias: rangos enzimáticos (Brewfather - Mash & Lauter Science).
        """
        if og <= 1.000 or atenuacion_levadura <= 0: return 1.000
        aa = float(atenuacion_levadura)
        if str(metodo).lower() == "normal":
            tabla = [(60, 1.08), (62, 1.06), (64, 1.03), (66, 1.00),
                     (68, 0.96), (70, 0.91), (72, 0.86), (74, 0.82)]
            t = min(max(float(temp_macerado or 66.0), 60.0), 74.0)
            factor_t = 1.0
            for i in range(len(tabla) - 1):
                t0, f0 = tabla[i]; t1, f1 = tabla[i + 1]
                if t0 <= t <= t1:
                    factor_t = f0 + (f1 - f0) * (t - t0) / (t1 - t0)
                    break
            factor_esp = max(0.75, 1.0 - 0.25 * float(especiales_pct or 0.0))
            aa = aa * factor_t * factor_esp
        aa = min(max(aa, 40.0), 95.0)
        fg = 1.0 + ((og - 1.0) * (1.0 - (aa / 100.0)))
        return round(fg, 4)

    @staticmethod
    def calcular_abv(og, fg, formula="standard"):
        """ABV: 'standard' (OG-FG)*131.25  |  'alternative' 76.08*(OG-FG)/(1.775-OG)*(FG/0.794)
        (Fórmulas documentadas por Brewfather en Settings > Formulas)."""
        if og <= fg: return 0.0
        if str(formula).lower() == "alternative":
            try:
                abv = 76.08 * (og - fg) / (1.775 - og) * (fg / 0.794)
            except ZeroDivisionError:
                abv = (og - fg) * 131.25
        else:
            abv = (og - fg) * 131.25
        return round(abv, 2)

    @staticmethod
    def calcular_atenuacion(og, fg):
        if og <= 1.000 or og <= fg: return 0.0
        return round((((og - fg) / (og - 1.0)) * 100), 1)

    @staticmethod
    def calcular_calorias(og, fg, abv):
        """Fórmula de Daniels para calorías por porción de 355ml (12oz)."""
        if og <= 1.000: return 0.0
        re = (0.1808 * (og - 1) * 1000) + (0.8192 * (fg - 1) * 1000)
        calorias = ((6.9 * abv) + (4.0 * re)) * 3.55
        return round(max(0, calorias), 0)

    # ==========================================
    # MÓDULO AMARGOR Y LÚPULOS (§3.A y §3.C)
    # ==========================================
    @staticmethod
    def calcular_ibu(lupulos, volumen_lote, og, altitud=400, formula="tinseth",
                     hop_stand_min=15.0):
        """
        IBU. (Fase 0)
        formula='tinseth' (default) o 'rager' (librería brauhaus).
        Flameout/whirlpool (tiempo=0): se estima la isomerización POSTERIOR al
        apagado (Hosom/alchemyoverlord: la utilización continúa hasta ~82 C),
        con una tasa ~50% durante el hop stand (hop_stand_min).
        OJO: el dry-hop NO aporta IBU (no usar tiempo 0 para dry-hop).
        """
        if volumen_lote <= 0: return 0.0
        ibu_total = 0.0
        temp_eb = 100 - (altitud / 300.0)
        fc_temp = math.exp(-0.04 * (100 - temp_eb)) if temp_eb < 100 else 1.0
        es_rager = str(formula).lower() == "rager"
        for lupulo in lupulos:
            cantidad_g = lupulo.get('cantidad', 0)
            aa_pct = lupulo.get('aa', 0)
            tiempo = lupulo.get('tiempo', 0)
            formato = (lupulo.get('formato') or 'pellet').lower()
            if aa_pct <= 0 or cantidad_g <= 0: continue
            factor_formato = 1.10 if formato == 'pellet' else 1.0

            if es_rager:
                t = tiempo if tiempo > 0 else hop_stand_min * 0.5
                util_pct = 18.11 + 13.86 * math.tanh((t - 31.32) / 18.27)   # %
                ajuste = max(0.0, (og - 1.050) / 0.2)
                ibu_l = (cantidad_g / 1000.0) * 100 * util_pct * aa_pct / (volumen_lote * (1 + ajuste))
                ibu_total += ibu_l * factor_formato * fc_temp
            else:
                aa = aa_pct / 100.0
                factor_og = 1.65 * math.pow(0.000125, og - 1)
                if tiempo > 0:
                    utilizacion = factor_og * ((1 - math.exp(-0.04 * tiempo)) / 4.15)
                else:
                    f_stand = (1 - math.exp(-0.04 * float(hop_stand_min or 15.0))) / 4.15
                    utilizacion = factor_og * f_stand * 0.5
                ibu_l = (cantidad_g * utilizacion * aa * 1000) / volumen_lote
                ibu_total += ibu_l * fc_temp * factor_formato
        return round(ibu_total, 1)

    # ==========================================
    # MÓDULO COLOR (SRM)
    # ==========================================
    @staticmethod
    def calcular_srm(maltas, volumen_lote):
        if volumen_lote <= 0: return 0.0
        mcu_total = 0.0
        for malta in maltas:
            cantidad_kg = malta.get('cantidad', 0)
            lovibond = malta.get('color', 2.0)
            mcu = (cantidad_kg * lovibond * 2.205) / (volumen_lote * 0.264)
            mcu_total += mcu
        if mcu_total <= 0:
            return 0.0
        # Morey (BeerSmith / BrewWiki). Antes se usaba MCU directo por debajo de 7.
        srm = 1.4922 * math.pow(mcu_total, 0.6859)
        return max(0, round(srm, 1))

    @staticmethod
    def srm_a_ebc(srm):
        """Conversión estándar SRM -> EBC (Brewfather: EBC = SRM x 1.97)."""
        return round(float(srm or 0) * 1.97, 1)

    # ==========================================
    # MÓDULO AGUAS Y pH
    # ==========================================
    @staticmethod
    def calcular_aguas(granos_kg, volumen_final, ratio_maceracion=3.0,
                       absorcion_grano=1.0, evaporacion_pct=10.0, tiempo_hervor_min=60,
                       perdidas_l=0.0, evaporacion_l_h=None):
        """
        Calcula agua de maceración y lavado.
        v3: Incorpora evaporación durante el hervor (típicamente 8-12% por hora).
        V_lavado = V_antes_hervir - V_empaste + M_total (fórmula Informe §2.B)
        """
        if granos_kg <= 0: return {'agua_maceracion': 0.0, 'agua_lavado': 0.0,
                                   'volumen_pre_hervor': 0.0, 'evaporacion_L': 0.0}
        # Fase 4: usar evaporación en L/h del equipo si está definida; sumar pérdidas
        if evaporacion_l_h:
            evaporacion_l = float(evaporacion_l_h) * (float(tiempo_hervor_min or 60) / 60.0)
        else:
            evaporacion_h = (evaporacion_pct / 100.0) * (tiempo_hervor_min / 60.0)
            evaporacion_l = volumen_final * evaporacion_h
        volumen_pre_hervor = volumen_final + float(perdidas_l or 0.0) + evaporacion_l
        agua_maceracion = granos_kg * ratio_maceracion
        volumen_retenido = granos_kg * absorcion_grano
        agua_lavado = volumen_pre_hervor - agua_maceracion + volumen_retenido
        evaporacion_L = evaporacion_l
        return {
            'agua_maceracion': round(agua_maceracion, 2),
            'agua_lavado': max(0, round(agua_lavado, 2)),
            'volumen_pre_hervor': round(volumen_pre_hervor, 2),
            'evaporacion_L': round(evaporacion_L, 2),
        }

    @staticmethod
    def estimar_ph_maceracion(ca_ppm, mg_ppm, hco3_ppm, srm, ph_agua=None):
        """
        Estima el pH de maceración (modelo empírico documentado).

        Alcalinidad residual (RA) según Kolbach, en ppm como CaCO3:
            RA = (HCO3/61 - (Ca/20 + Mg/12) / 2) * 50
        El pH baja con maltas oscuras (SRM) y se ajusta levemente según el
        pH del agua de entrada (desviación respecto de 7.0).
        Es una ESTIMACIÓN de diseño: en la práctica siempre medir con pHmetro.
        """
        hco3_mmol = max(0.0, hco3_ppm) / 61.0
        ca_mmol   = max(0.0, ca_ppm)   / 20.0
        mg_mmol   = max(0.0, mg_ppm)   / 12.0
        ra_mmol   = hco3_mmol - (ca_mmol + mg_mmol) / 2.0
        ra_ppm    = ra_mmol * 50.0  # ppm como CaCO3
        ph = 5.6 + ra_ppm * 0.0030 - max(0.0, srm - 5.0) * 0.02
        if ph_agua:  # influencia del pH del agua de entrada (acotada ±0.2)
            ph += max(-0.2, min(0.2, (ph_agua - 7.0) * 0.05))
        return round(max(4.0, min(8.0, ph)), 2)

    @staticmethod
    def estimar_ph_post_hervor(ph_mash, tiempo_hervor_min=60):
        caida = min(0.3, (tiempo_hervor_min / 30.0) * 0.1)
        return round(max(4.0, ph_mash - caida), 2)

    @staticmethod
    def estimar_ph_post_lupulo(ph_hervor, lupulos, volumen_lote):
        return round(ph_hervor, 2)

    @staticmethod
    def calcular_acido_lactico(ph_actual, ph_objetivo, granos_kg):
        if ph_actual <= ph_objetivo or granos_kg <= 0: return 0.0
        ml_por_decima = (granos_kg / 4.5) * 1.0
        decimas_a_bajar = ph_actual - ph_objetivo
        ml_necesarios = ml_por_decima * (decimas_a_bajar * 10.0)
        return round(ml_necesarios, 1)

    # ==========================================
    # 🆕 STRIKE WATER (Informe §2.B)
    # ==========================================
    @staticmethod
    def calcular_strike_water(temp_objetivo, temp_grano, ratio, factor_correccion=0.0):
        """
        Calcula la temperatura del agua de mezcla (Strike Water) para alcanzar
        la temperatura de maceración objetivo.

        Fórmula Informe §2.B:
            T_agua = T_objetivo + (0.4/R) * (T_objetivo - T_grano) + FC

        :param temp_objetivo: Temperatura deseada del macerado (°C, típicamente 65-68)
        :param temp_grano:    Temperatura actual del grano (°C, usualmente ambiente)
        :param ratio:         Relación de empaste en L/kg
        :param factor_correccion: FC por pérdida térmica del equipo (0 a 2 °C)
        :return: Temperatura del agua a calentar (°C)
        """
        if ratio <= 0: return temp_objetivo
        t_agua = temp_objetivo + (0.4 / ratio) * (temp_objetivo - temp_grano) + factor_correccion
        return round(t_agua, 1)

    # ==========================================
    # 🆕 CORRECCIÓN DE DENSÍMETRO ASBC (§4 Día de Cocción)
    # ==========================================
    @staticmethod
    def corregir_densimetro(gravedad_leida, temp_medicion_c):
        """
        Corrige la gravedad leída por el densímetro a la temperatura de calibración (20°C)
        usando la fórmula ASBC (American Society of Brewing Chemists).

        :param gravedad_leida: Gravedad específica leída (ej. 1.050)
        :param temp_medicion_c: Temperatura real del mosto al medir (°C)
        :return: Gravedad corregida a 20°C
        """
        def factor(t):
            return (1.00130346
                    - 0.000134722124 * t
                    + 0.00000204052596 * (t ** 2)
                    - 0.00000000232820948 * (t ** 3))
        if temp_medicion_c == 20.0: return round(gravedad_leida, 4)
        gravedad_corregida = gravedad_leida * (factor(temp_medicion_c) / factor(20.0))
        return round(gravedad_corregida, 4)

    # ==========================================
    # DESCRIPTORES UI
    # ==========================================
    @staticmethod
    def obtener_descripcion_ph(ph):
        if ph < 5.2: return "⚠️ Muy Ácido"
        elif ph <= 5.6: return "✅ Rango Óptimo (5.2 - 5.6)"
        elif ph <= 5.8: return "⚠️ Algo Alto"
        else: return "❌ Muy Alto"

    @staticmethod
    def obtener_descripcion_color(srm):
        if srm < 4: return "Paja"
        elif srm < 8: return "Dorado"
        elif srm < 12: return "Ámbar"
        elif srm < 20: return "Cobrizo"
        elif srm < 30: return "Marrón"
        elif srm < 40: return "Marrón Oscuro"
        else: return "Negro"

    @staticmethod
    def obtener_descripcion_amargor(ibu):
        if ibu < 20: return "Muy Suave"
        elif ibu < 40: return "Balanceado"
        elif ibu < 60: return "Amargo"
        elif ibu < 80: return "Muy Amargo"
        else: return "Extremadamente Amargo"

    @staticmethod
    def sugerir_estilo(og, ibu, srm):
        if og < 1.045 and ibu < 30 and srm < 8: return "Pilsner / Blonde Ale"
        elif og < 1.055 and ibu < 40 and srm < 15: return "Pale Ale / Amber Ale"
        elif og > 1.060 and ibu > 50 and srm < 15: return "IPA / American IPA"
        elif srm > 30 and og > 1.060: return "Stout / Porter"
        elif og > 1.080: return "Imperial / Barley Wine"
        else: return "Estilo Personalizado"

    @staticmethod
    def srm_a_color_hex(srm):
        """Mapea SRM a un color hexadecimal para la Barra Dinámica SRM (§3 Pantalla 3)."""
        if srm < 3:   return "#FFE699"  # Paja muy pálido
        elif srm < 4: return "#FFD878"  # Paja
        elif srm < 6: return "#FFCA5A"  # Dorado claro
        elif srm < 8: return "#FBB12A"  # Dorado
        elif srm < 10: return "#E59029" # Dorado oscuro
        elif srm < 13: return "#D1792B" # Ámbar claro
        elif srm < 16: return "#A9632E" # Ámbar
        elif srm < 19: return "#884A25" # Cobrizo
        elif srm < 23: return "#6F3C1F" # Marrón claro
        elif srm < 28: return "#552B16" # Marrón
        elif srm < 35: return "#3D1D0F" # Marrón oscuro
        elif srm < 40: return "#2A110A" # Muy oscuro
        else:         return "#1A0906"  # Negro opaco

    # ==========================================
    # MOTOR PRINCIPAL: RECETA COMPLETA
    # ==========================================
    @staticmethod
    def calcular_receta_completa(datos_receta, eficiencia=0.75, altitud=400):
        maltas = datos_receta.get('maltas', [])
        lupulos = datos_receta.get('lupulos', [])
        volumen = datos_receta.get('agua_vol', 20.0)
        atenuacion_levadura = datos_receta.get('atenuacion_levadura', 75.0)
        tolerancia_abv = datos_receta.get('tolerancia_abv', 12.0)
        agua = datos_receta.get('agua', {"ca": 50, "mg": 10, "hco3": 150})
        ratio_mac = datos_receta.get('ratio_maceracion', 3.0)
        absorcion = datos_receta.get('absorcion', 1.0)
        evaporacion_pct = datos_receta.get('evaporacion_pct', 10.0)

        metodo_fg   = datos_receta.get('metodo_fg', 'normal')
        temp_mac    = datos_receta.get('temp_macerado', 66.0)
        formula_ibu = datos_receta.get('formula_ibu', 'tinseth')
        formula_abv = datos_receta.get('formula_abv', 'standard')
        hop_stand   = datos_receta.get('hop_stand_min', 15.0)
        perdidas_l  = datos_receta.get('perdidas_l', 0.0)
        evap_l_h    = datos_receta.get('evaporacion_l_h')

        granos_total = sum(m.get('cantidad', 0) for m in maltas) or 0.0
        especiales_kg = sum(m.get('cantidad', 0) for m in maltas if m.get('color', 2) > 20)
        especiales_pct = (especiales_kg / granos_total) if granos_total > 0 else 0.0

        og = BrewEngine.calcular_og(maltas, volumen, eficiencia)
        fg = BrewEngine.calcular_fg(og, atenuacion_levadura, metodo_fg, temp_mac, especiales_pct)
        abv = BrewEngine.calcular_abv(og, fg, formula_abv)
        abv_alt = BrewEngine.calcular_abv(og, fg, "alternative")
        atenuacion_real = BrewEngine.calcular_atenuacion(og, fg)
        calorias = BrewEngine.calcular_calorias(og, fg, abv)
        alerta_abv = abv > tolerancia_abv

        ibu = BrewEngine.calcular_ibu(lupulos, volumen, og, altitud, formula_ibu, hop_stand)
        srm = BrewEngine.calcular_srm(maltas, volumen)
        ebc = BrewEngine.srm_a_ebc(srm)

        granos_kg = sum(m.get('cantidad', 0) for m in maltas)
        tiempo_hervor = datos_receta.get('tiempo_hervor', 60)
        aguas = BrewEngine.calcular_aguas(granos_kg, volumen, ratio_mac,
                                          absorcion, evaporacion_pct, tiempo_hervor,
                                          perdidas_l, evap_l_h)

        ph_mash = BrewEngine.estimar_ph_maceracion(
            agua.get('ca', 50), agua.get('mg', 10), agua.get('hco3', 150), srm,
            agua.get('ph')  # pH del agua de entrada (opcional)
        )
        ph_hervor = BrewEngine.estimar_ph_post_hervor(ph_mash, tiempo_hervor)
        ph_final  = BrewEngine.estimar_ph_post_lupulo(ph_hervor, lupulos, volumen)

        ph_objetivo = 5.3
        acido_lactico_ml = 0.0
        if ph_mash > ph_objetivo:
            acido_lactico_ml = BrewEngine.calcular_acido_lactico(ph_mash, ph_objetivo, granos_kg)

        bugu = round(ibu / ((og - 1) * 1000), 2) if og > 1 else 0
        return {
            'og': og, 'fg': fg, 'ibu': ibu, 'srm': srm, 'abv': abv,
            'atenuacion': atenuacion_real, 'calorias': calorias, 'aguas': aguas,
            'bugu': bugu,
            'ph': ph_mash, 'ph_hervor': ph_hervor, 'ph_final': ph_final,
            'acido_lactico_ml': acido_lactico_ml,
            'alerta_abv': alerta_abv,
            'srm_hex': BrewEngine.srm_a_color_hex(srm),
            'ebc': ebc, 'abv_alt': abv_alt,
            'metodo_fg': metodo_fg, 'formula_ibu': formula_ibu, 'formula_abv': formula_abv,
        }

    # ==========================================
    # MÓDULO AGUA OBJETIVO, SALES Y ÓSMOSIS (Fase 3)
    # ==========================================
    # Perfiles de agua objetivo por familia de estilo (ppm)
    PERFILES_AGUA_OBJETIVO = {
        "Pilsner / Lager claro":  {"ca": 40,  "mg": 5,  "so4": 50,  "cl": 50,  "hco3": 25},
        "Blonde / Cream Ale":     {"ca": 50,  "mg": 5,  "so4": 70,  "cl": 60,  "hco3": 40},
        "Pale Ale / IPA":         {"ca": 110, "mg": 10, "so4": 250, "cl": 55,  "hco3": 25},
        "Amber / Red Ale":        {"ca": 80,  "mg": 8,  "so4": 120, "cl": 60,  "hco3": 60},
        "Porter":                 {"ca": 70,  "mg": 8,  "so4": 60,  "cl": 90,  "hco3": 100},
        "Stout / Imperial":       {"ca": 80,  "mg": 10, "so4": 60,  "cl": 110, "hco3": 150},
        "Belgian / Saison":       {"ca": 60,  "mg": 8,  "so4": 90,  "cl": 70,  "hco3": 35},
        "Trigo / Weissbier":      {"ca": 50,  "mg": 8,  "so4": 60,  "cl": 70,  "hco3": 40},
        "Balanceada (genérica)":  {"ca": 70,  "mg": 8,  "so4": 100, "cl": 80,  "hco3": 60},
    }

    # ppm que aporta 1 gramo de sal disuelto en 1 litro
    APORTE_SALES = {
        "yeso":   {"ca": 232.8, "so4": 557.7},   # CaSO4.2H2O
        "cacl2":  {"ca": 272.6, "cl": 483.0},    # CaCl2.2H2O
        "epsom":  {"mg": 98.6,  "so4": 389.7},   # MgSO4.7H2O
        "sal":    {"na": 393.4, "cl": 606.6},    # NaCl
        "bicarb": {"na": 273.7, "hco3": 728.6},  # NaHCO3
    }

    @staticmethod
    def familia_estilo(nombre_estilo):
        """Familia de estilo (para elegir el agua objetivo)."""
        n = (nombre_estilo or "").lower()
        if any(k in n for k in ("pils", "lager", "helles", "kolsch", "light", "mexican")):
            return "Pilsner / Lager claro"
        if any(k in n for k in ("ipa", "pale ale", "apa", "neipa")):
            return "Pale Ale / IPA"
        if any(k in n for k in ("stout", "imperial", "barley")):
            return "Stout / Imperial"
        if "porter" in n:
            return "Porter"
        if any(k in n for k in ("amber", "red ale", "red lager", "irish red")):
            return "Amber / Red Ale"
        if any(k in n for k in ("belgian", "saison", "dubbel", "tripel", "wit")):
            return "Belgian / Saison"
        if any(k in n for k in ("wheat", "weizen", "weiss", "trigo")):
            return "Trigo / Weissbier"
        if any(k in n for k in ("blonde", "cream")):
            return "Blonde / Cream Ale"
        return "Balanceada (genérica)"

    @staticmethod
    def perfil_agua_objetivo(nombre_estilo):
        fam = BrewEngine.familia_estilo(nombre_estilo)
        return fam, dict(BrewEngine.PERFILES_AGUA_OBJETIVO.get(fam, {}))

    @staticmethod
    def calcular_sales(agua_actual, objetivo, volumen_l):
        """
        Gramos de sales para acercar el agua actual al perfil objetivo.
        agua_actual / objetivo: dict con ca, mg, so4, cl, hco3 (ppm).
        Considera la DILUCIÓN con ósmosis (la ósmosis aporta ~0 minerales).
        Devuelve gramos + valores finales estimados + % de dilución.
        """
        v = max(0.0, float(volumen_l or 0))
        claves = ("ca", "mg", "so4", "cl", "hco3")
        ap = {k: float(agua_actual.get(k, 0) or 0) for k in claves}
        ob = {k: float(objetivo.get(k, 0) or 0) for k in claves}
        A = BrewEngine.APORTE_SALES

        # 1) Dilución con ósmosis si el bicarbonato actual supera el objetivo
        ro_pct = 0.0
        if ap["hco3"] > ob["hco3"] and ap["hco3"] > 0:
            ro_pct = round(max(0.0, (1 - ob["hco3"] / ap["hco3"])) * 100, 0)
        factor = 1.0 - (ro_pct / 100.0)
        ap_eff = {k: ap[k] * factor for k in claves}   # agua efectiva tras diluir

        def gramos(deficit, aporte):
            if v <= 0 or aporte <= 0:
                return 0.0
            return max(0.0, deficit) * v / aporte

        g_yeso   = gramos(ob["so4"] - ap_eff["so4"], A["yeso"]["so4"])
        g_cacl2  = gramos(ob["cl"] - ap_eff["cl"], A["cacl2"]["cl"])
        g_epsom  = gramos(ob["mg"] - ap_eff["mg"], A["epsom"]["mg"])
        g_bicarb = gramos(ob["hco3"] - ap_eff["hco3"], A["bicarb"]["hco3"])

        if v > 0:
            ca_f   = ap_eff["ca"] + g_yeso * A["yeso"]["ca"] / v + g_cacl2 * A["cacl2"]["ca"] / v
            so4_f  = ap_eff["so4"] + g_yeso * A["yeso"]["so4"] / v + g_epsom * A["epsom"]["so4"] / v
            cl_f   = ap_eff["cl"] + g_cacl2 * A["cacl2"]["cl"] / v
            mg_f   = ap_eff["mg"] + g_epsom * A["epsom"]["mg"] / v
            hco3_f = ap_eff["hco3"] + g_bicarb * A["bicarb"]["hco3"] / v
        else:
            ca_f, so4_f, cl_f, mg_f, hco3_f = (ap_eff["ca"], ap_eff["so4"], ap_eff["cl"],
                                               ap_eff["mg"], ap_eff["hco3"])

        return {
            "yeso_g": round(g_yeso, 1), "cacl2_g": round(g_cacl2, 1),
            "epsom_g": round(g_epsom, 1), "bicarb_g": round(g_bicarb, 1),
            "ca_final": round(ca_f), "mg_final": round(mg_f),
            "so4_final": round(so4_f), "cl_final": round(cl_f),
            "hco3_final": round(hco3_f), "ro_pct": ro_pct, "volumen_l": v,
        }

    @staticmethod
    def relacion_so4_cl(so4, cl):
        """Relación sulfato/cloruro y su interpretación."""
        so4 = float(so4 or 0); cl = float(cl or 0)
        if cl <= 0:
            return (0.0, "sin cloruro") if so4 <= 0 else (99.0, "muy amarga (SO4 alto)")
        r = so4 / cl
        if r < 0.8:
            desc = "predomina malta (dulce)"
        elif r <= 1.5:
            desc = "equilibrada"
        elif r <= 2.5:
            desc = "predomina lúpulo (amarga)"
        else:
            desc = "muy amarga (SO4 alto)"
        return round(r, 2), desc
