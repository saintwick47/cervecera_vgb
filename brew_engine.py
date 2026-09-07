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
    def calcular_fg(og, atenuacion_levadura=75.0):
        """FG = 1 + (OG - 1) * (1 - %Atenuacion/100)"""
        if og <= 1.000 or atenuacion_levadura <= 0: return 1.000
        fg = 1.0 + ((og - 1.0) * (1.0 - (atenuacion_levadura / 100.0)))
        return round(fg, 4)

    @staticmethod
    def calcular_abv(og, fg):
        if og <= fg: return 0.0
        return round(((og - fg) * 131.25), 2)

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
    def calcular_ibu(lupulos, volumen_lote, og, altitud=400):
        if volumen_lote <= 0: return 0.0
        ibu_total = 0.0
        temp_eb = 100 - (altitud / 300.0)
        fc_temp = math.exp(-0.04 * (100 - temp_eb)) if temp_eb < 100 else 1.0
        for lupulo in lupulos:
            cantidad_g = lupulo.get('cantidad', 0)
            aa = lupulo.get('aa', 0) / 100.0
            tiempo = lupulo.get('tiempo', 0)
            formato = lupulo.get('formato', 'pellet').lower()
            if aa <= 0 or cantidad_g <= 0: continue
            factor_og = 1.65 * math.pow(0.000125, og - 1)
            utilizacion = 0.0
            if tiempo > 0:
                factor_tiempo = (1 - math.exp(-0.04 * tiempo)) / 4.15
                utilizacion = factor_og * factor_tiempo
            elif tiempo == 0:
                # Whirlpool / flameout: isomerización parcial (~10% de la máx).
                # Nota: un lúpulo en seco (dry-hop) NO aporta IBU; no se debe
                # usar tiempo 0 para dry-hop.
                utilizacion = factor_og * 0.10
            factor_formato = 1.10 if formato == 'pellet' else 1.0
            ibu_lupulo = (cantidad_g * utilizacion * aa * 1000) / volumen_lote
            ibu_lupulo *= fc_temp * factor_formato
            ibu_total += ibu_lupulo
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
        if mcu_total <= 7:
            srm = mcu_total
        else:
            srm = 1.4922 * math.pow(mcu_total, 0.6859)
        return max(0, round(srm, 1))

    # ==========================================
    # MÓDULO AGUAS Y pH
    # ==========================================
    @staticmethod
    def calcular_aguas(granos_kg, volumen_final, ratio_maceracion=3.0,
                       absorcion_grano=1.0, evaporacion_pct=10.0, tiempo_hervor_min=60):
        """
        Calcula agua de maceración y lavado.
        v3: Incorpora evaporación durante el hervor (típicamente 8-12% por hora).
        V_lavado = V_antes_hervir - V_empaste + M_total (fórmula Informe §2.B)
        """
        if granos_kg <= 0: return {'agua_maceracion': 0.0, 'agua_lavado': 0.0,
                                   'volumen_pre_hervor': 0.0, 'evaporacion_L': 0.0}
        evaporacion_h = (evaporacion_pct / 100.0) * (tiempo_hervor_min / 60.0)
        volumen_pre_hervor = volumen_final * (1 + evaporacion_h)
        agua_maceracion = granos_kg * ratio_maceracion
        volumen_retenido = granos_kg * absorcion_grano
        agua_lavado = volumen_pre_hervor - agua_maceracion + volumen_retenido
        evaporacion_L = volumen_pre_hervor - volumen_final
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

        og = BrewEngine.calcular_og(maltas, volumen, eficiencia)
        fg = BrewEngine.calcular_fg(og, atenuacion_levadura)
        abv = BrewEngine.calcular_abv(og, fg)
        atenuacion_real = BrewEngine.calcular_atenuacion(og, fg)
        calorias = BrewEngine.calcular_calorias(og, fg, abv)
        alerta_abv = abv > tolerancia_abv

        ibu = BrewEngine.calcular_ibu(lupulos, volumen, og, altitud)
        srm = BrewEngine.calcular_srm(maltas, volumen)

        granos_kg = sum(m.get('cantidad', 0) for m in maltas)
        tiempo_hervor = datos_receta.get('tiempo_hervor', 60)
        aguas = BrewEngine.calcular_aguas(granos_kg, volumen, ratio_mac,
                                          absorcion, evaporacion_pct, tiempo_hervor)

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
        }
