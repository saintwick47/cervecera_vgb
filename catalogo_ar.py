# catalogo_ar.py
# 2024-05-17 (v4 - datos de ficha técnica: productor, categoría, uso y % máx)
# Autor: SaintWick
"""
Catálogo de Insumos y Perfiles Geográficos de Argentina (mercado cervecero).

v4: se limpiaron los espacios al final de las claves (antes "Uma Malta Pilsen "
    no coincidía con el nombre que escribía la interfaz) y se agregaron los datos
    que muestra la ficha técnica del diseño: productor/origen, categoría, uso y
    porcentaje máximo recomendado.

Los valores técnicos son los estándar de cada maltería (extracto en puntos
L°/kg, color en °Lovibond/SRM, AA en %, atenuación en %).
"""

# ==========================================
# 1. PERFILES GEOGRÁFICOS DE CÓRDOBA
# ==========================================
# La altitud reduce la presión atmosférica y el punto de ebullición.
ALTITUDES_CORDOBA = {
    "Córdoba Capital": 400,
    "La Cumbre": 1100,
    "Villa Carlos Paz": 550,
    "Alta Gracia": 450,
    "Villa General Belgrano": 700,
    "San Francisco": 130,
    "Río Cuarto": 200,
    "Cruz del Eje": 500,
    "Mina Clavero": 750,
    "Personalizado": 0,
}

# Perfiles de agua estimados de la provincia (promedios generales).
# 'ph' = pH típico del agua de entrada (se usa para estimar el pH de maceración).
PERFILES_AGUA_CORDOBA = {
    "Córdoba Capital (Agua de Red)": {"ca": 25.0, "mg": 5.0, "hco3": 80.0, "ph": 7.3},
    "La Cumbre (Agua de Sierra)": {"ca": 10.0, "mg": 2.0, "hco3": 30.0, "ph": 6.8},
    "Villa Carlos Paz (Agua de Red)": {"ca": 30.0, "mg": 8.0, "hco3": 90.0, "ph": 7.2},
    "Río Cuarto (Agua de Red)": {"ca": 45.0, "mg": 12.0, "hco3": 150.0, "ph": 7.5},
    "Agua Destilada / Ósmosis": {"ca": 0.0, "mg": 0.0, "hco3": 0.0, "ph": 7.0},
}

# ==========================================
# 2. MALTA Y FERMENTABLES
# ==========================================
# Campos: extracto (puntos L°/kg), color (°L), origen (productor),
# categoria (familia para los filtros), uso, pct_max (% máx. del grist),
# ppg (potencial en PPG) y diastatic (poder diastásico relativo).
CATEGORIA_BASE = "Maltas Base"
CATEGORIA_ESPECIAL = "Maltas Especiales / Caramelo"
CATEGORIA_TOSTADA = "Granos Tostados"
CATEGORIA_ADJUNTO = "Adjuntos y Copos"

MALTAS_AR = {
    # --- Nacionales: Uma Malta (Argentina) ---
    "Malta Pale Ale (Uma Malta)": {
        "extracto": 309, "color": 3.8, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 100},
    "Pilsen Criolla (Uma Malta)": {
        "extracto": 308, "color": 2.2, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 105},
    "Malta Munich (Uma Malta)": {
        "extracto": 305, "color": 9.0, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 80,
        "ppg": 36, "diastatic": 80},
    "Uma Malta Base": {
        "extracto": 298, "color": 2.5, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 36, "diastatic": 100},
    "Uma Malta Caramel 150": {
        "extracto": 288, "color": 75.0, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 20,
        "ppg": 34, "diastatic": 0},
    "Uma Malta Negra": {
        "extracto": 280, "color": 500.0, "origen": "Uma Malta (Argentina)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Macerado", "pct_max": 10,
        "ppg": 33, "diastatic": 0},
    # --- Nacionales: MaltAr / Cargill ---
    "MaltAr / Cargill Pilsen": {
        "extracto": 305, "color": 2.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 105},
    "MaltAr / Cargill Malta Base": {
        "extracto": 305, "color": 2.5, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 100},
    "MaltAr / Cargill Munich": {
        "extracto": 302, "color": 8.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 80,
        "ppg": 36, "diastatic": 80},
    "MaltAr / Cargill Caramel 40": {
        "extracto": 292, "color": 20.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 20,
        "ppg": 35, "diastatic": 0},
    "MaltAr / Cargill Caramel 120": {
        "extracto": 285, "color": 60.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 15,
        "ppg": 34, "diastatic": 0},
    "MaltAr / Cargill Chocolate": {
        "extracto": 280, "color": 350.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Macerado", "pct_max": 10,
        "ppg": 33, "diastatic": 0},
    "MaltAr / Cargill Black (Carafa)": {
        "extracto": 278, "color": 500.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Macerado", "pct_max": 10,
        "ppg": 33, "diastatic": 0},
    # --- Importados: Weyermann Malting (Alemania) ---
    "Weyermann Pilsner": {
        "extracto": 309, "color": 2.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 110},
    "Weyermann Munich I": {
        "extracto": 305, "color": 7.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 80,
        "ppg": 37, "diastatic": 85},
    "Weyermann Munich II": {
        "extracto": 303, "color": 9.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 80,
        "ppg": 36, "diastatic": 75},
    "Caramelo 60L (CaraAroma)": {
        "extracto": 292, "color": 35.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 20,
        "ppg": 35, "diastatic": 0},
    "Weyermann Caramunich I": {
        "extracto": 294, "color": 25.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 20,
        "ppg": 35, "diastatic": 0},
    "Weyermann Caramunich III": {
        "extracto": 288, "color": 55.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 15,
        "ppg": 34, "diastatic": 0},
    "Melanoidina (Weyermann)": {
        "extracto": 307, "color": 28.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Macerado", "pct_max": 20,
        "ppg": 37, "diastatic": 0},
    "Weyermann Carafa Special I": {
        "extracto": 290, "color": 350.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Macerado", "pct_max": 10,
        "ppg": 35, "diastatic": 0},
    "Weyermann Carafa Special III": {
        "extracto": 288, "color": 500.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Macerado", "pct_max": 10,
        "ppg": 34, "diastatic": 0},
    "Weyermann Smoked Malt (Ahumada)": {
        "extracto": 305, "color": 3.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Macerado", "pct_max": 60,
        "ppg": 37, "diastatic": 90},
    "Roasted Barley": {
        "extracto": 250, "color": 500.0, "origen": "Weyermann Malting (Alemania)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Tostado", "pct_max": 10,
        "ppg": 30, "diastatic": 0},
    "Cebada Tostada (Roasted Barley)": {
        "extracto": 250, "color": 500.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_TOSTADA, "uso": "Tostado", "pct_max": 10,
        "ppg": 30, "diastatic": 0},
    # --- Importados: Castle Malting (Bélgica) ---
    "Special B (Castle Malting)": {
        "extracto": 288, "color": 150.0, "origen": "Castle Malting (Bélgica)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Macerado", "pct_max": 10,
        "ppg": 34, "diastatic": 0},
    "Castle Malting Pilsen": {
        "extracto": 307, "color": 1.8, "origen": "Castle Malting (Bélgica)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 105},
    "Castle Malting Pale Ale": {
        "extracto": 306, "color": 3.5, "origen": "Castle Malting (Bélgica)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 100},
    "Castle Malting Biscuit": {
        "extracto": 296, "color": 23.0, "origen": "Castle Malting (Bélgica)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Macerado", "pct_max": 15,
        "ppg": 35, "diastatic": 0},
    # --- Importados: BestMalz (Alemania) ---
    "Trigo Malteado (BestMalz)": {
        "extracto": 310, "color": 2.5, "origen": "BestMalz (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 70,
        "ppg": 38, "diastatic": 95},
    "BestMalz Vienna": {
        "extracto": 304, "color": 3.5, "origen": "BestMalz (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 36, "diastatic": 90},
    "BestMalz Dark Munich": {
        "extracto": 302, "color": 12.0, "origen": "BestMalz (Alemania)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 80,
        "ppg": 36, "diastatic": 75},
    # --- Importados: Dingemans (Bélgica) ---
    "Dingemans Pilsen": {
        "extracto": 307, "color": 1.6, "origen": "Dingemans (Bélgica)",
        "categoria": CATEGORIA_BASE, "uso": "Macerado", "pct_max": 100,
        "ppg": 37, "diastatic": 105},
    "Dingemans Cara 20": {
        "extracto": 294, "color": 20.0, "origen": "Dingemans (Bélgica)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Infusión / Macerado", "pct_max": 20,
        "ppg": 35, "diastatic": 0},
    "Dingemans Special B": {
        "extracto": 286, "color": 145.0, "origen": "Dingemans (Bélgica)",
        "categoria": CATEGORIA_ESPECIAL, "uso": "Macerado", "pct_max": 10,
        "ppg": 34, "diastatic": 0},
    # --- Adjuntos y copos ---
    "Copos de Avena (Flaked Oats)": {
        "extracto": 278, "color": 1.4, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Adjunto", "pct_max": 30,
        "ppg": 33, "diastatic": 0},
    "Avena Arrollada (Flaked Oats)": {
        "extracto": 278, "color": 2.0, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Adjunto", "pct_max": 30,
        "ppg": 33, "diastatic": 0},
    "Maíz Flaked (Flaked Corn)": {
        "extracto": 292, "color": 1.0, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Adjunto", "pct_max": 30,
        "ppg": 35, "diastatic": 0},
    "Trigo Flaked (Flaked Wheat)": {
        "extracto": 290, "color": 2.0, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Adjunto", "pct_max": 40,
        "ppg": 35, "diastatic": 0},
    "Cebada Cruda (Flaked Barley)": {
        "extracto": 280, "color": 2.0, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Adjunto", "pct_max": 20,
        "ppg": 33, "diastatic": 0},
    "Azúcar Candi (Candy Sugar)": {
        "extracto": 380, "color": 10.0, "origen": "Dingemans (Bélgica)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Hervido", "pct_max": 20,
        "ppg": 46, "diastatic": 0},
    "Miel de Caña": {
        "extracto": 300, "color": 8.0, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Hervido", "pct_max": 15,
        "ppg": 36, "diastatic": 0},
    "Extracto de Malta Seco (DME)": {
        "extracto": 350, "color": 4.0, "origen": "MaltAr / Cargill (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Hervido", "pct_max": 100,
        "ppg": 43, "diastatic": 0},
    "Lactosa (Azúcar de Leche)": {
        "extracto": 350, "color": 0.5, "origen": "AgroCereal (Argentina)",
        "categoria": CATEGORIA_ADJUNTO, "uso": "Hervido", "pct_max": 10,
        "ppg": 42, "diastatic": 0},
}

# ==========================================
# 3. LÚPULOS
# ==========================================
# Campos: aa (% alfa ácido de referencia), formato (pellet/flor),
# origen (país o productor), uso (Amargor / Aroma / Doble propósito).
LUPULOS_AR = {
    # --- Nacionales (Patagónicos) ---
    "Cascade Argentino": {"aa": 6.0, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Doble propósito"},
    "Mapuche": {"aa": 8.0, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Doble propósito"},
    "Victoria": {"aa": 7.0, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Aroma"},
    "Brewer's Gold Argentino": {"aa": 7.5, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Amargor"},
    "Spalter Argentino": {"aa": 4.5, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Aroma"},
    "Nugget Argentino": {"aa": 12.0, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Amargor"},
    "Traful": {"aa": 9.5, "formato": "pellet", "origen": "Patagonia (Argentina)", "uso": "Doble propósito"},
    # --- Estados Unidos ---
    "Cascade US": {"aa": 5.5, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Aroma"},
    "Citra (USA)": {"aa": 12.5, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    "Mosaic (USA)": {"aa": 11.5, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    "Amarillo (USA)": {"aa": 9.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Aroma"},
    "Centennial (USA)": {"aa": 10.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    "Columbus / CTZ (USA)": {"aa": 15.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Amargor"},
    "Simcoe (USA)": {"aa": 13.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    "Chinook (USA)": {"aa": 12.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    "Apollo (USA)": {"aa": 18.5, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Amargor"},
    "Sabro (USA)": {"aa": 14.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Aroma"},
    "El Dorado (USA)": {"aa": 14.0, "formato": "pellet", "origen": "Yakima Chief (EE.UU.)", "uso": "Doble propósito"},
    # --- Alemania ---
    "Hallertau Mittelfrüh (DE)": {"aa": 4.0, "formato": "pellet", "origen": "Hallertau (Alemania)", "uso": "Aroma"},
    "Tettnanger (DE)": {"aa": 4.5, "formato": "pellet", "origen": "Hallertau (Alemania)", "uso": "Aroma"},
    "Spalter Select (DE)": {"aa": 4.5, "formato": "pellet", "origen": "Hallertau (Alemania)", "uso": "Aroma"},
    "Magnum (DE)": {"aa": 13.5, "formato": "pellet", "origen": "Hallertau (Alemania)", "uso": "Amargor"},
    "Perle (DE)": {"aa": 7.5, "formato": "pellet", "origen": "Hallertau (Alemania)", "uso": "Doble propósito"},
    # --- República Checa / Reino Unido ---
    "Saaz (CZ)": {"aa": 3.5, "formato": "pellet", "origen": "Žatec (Rep. Checa)", "uso": "Aroma"},
    "East Kent Golding (UK)": {"aa": 5.0, "formato": "pellet", "origen": "Reino Unido", "uso": "Aroma"},
    "Fuggles (UK)": {"aa": 4.5, "formato": "pellet", "origen": "Reino Unido", "uso": "Aroma"},
    "Target (UK)": {"aa": 11.0, "formato": "pellet", "origen": "Reino Unido", "uso": "Amargor"},
    # --- Australia / Nueva Zelanda ---
    "Galaxy (AU)": {"aa": 14.0, "formato": "pellet", "origen": "Australia", "uso": "Aroma"},
    "Nelson Sauvin (NZ)": {"aa": 12.0, "formato": "pellet", "origen": "Nueva Zelanda", "uso": "Aroma"},
}

# ==========================================
# 4. LEVADURAS
# ==========================================
# Campos: atenuacion (%), tolerancia_abv (%), temp_range, formato, origen (marca).
LEVADURAS_AR = {
    # --- Fermentis ---
    "Fermentis US-05 (Ale Americana)": {
        "atenuacion": 81.0, "tolerancia_abv": 12.0, "temp_range": "12-25 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis S-04 (Ale Inglesa)": {
        "atenuacion": 75.0, "tolerancia_abv": 11.0, "temp_range": "12-25 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis W-34/70 (Lager)": {
        "atenuacion": 80.0, "tolerancia_abv": 10.5, "temp_range": "9-22 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis K-97 (Ale Alemana)": {
        "atenuacion": 80.0, "tolerancia_abv": 12.0, "temp_range": "15-25 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis T-58 (Belga)": {
        "atenuacion": 75.0, "tolerancia_abv": 12.5, "temp_range": "15-25 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis BE-134 (Saison)": {
        "atenuacion": 85.0, "tolerancia_abv": 14.0, "temp_range": "18-28 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis M-31 (Belga Tripel)": {
        "atenuacion": 82.0, "tolerancia_abv": 14.0, "temp_range": "17-25 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    "Fermentis S-23 (Lager)": {
        "atenuacion": 80.0, "tolerancia_abv": 11.0, "temp_range": "9-22 °C",
        "formato": "seca", "origen": "Fermentis (Francia)"},
    # --- Mangrove Jack's ---
    "Mangrove Jack's M44 (US West Coast)": {
        "atenuacion": 80.0, "tolerancia_abv": 14.0, "temp_range": "15-23 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    "Mangrove Jack's M15 (Empire Ale)": {
        "atenuacion": 76.0, "tolerancia_abv": 13.0, "temp_range": "17-22 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    "Mangrove Jack's M27 (Californian Lager)": {
        "atenuacion": 78.0, "tolerancia_abv": 11.0, "temp_range": "10-20 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    "Mangrove Jack's M29 (German Lager)": {
        "atenuacion": 80.0, "tolerancia_abv": 11.0, "temp_range": "10-22 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    "Mangrove Jack's M47 (Belgian Abbey)": {
        "atenuacion": 83.0, "tolerancia_abv": 14.0, "temp_range": "18-25 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    "Mangrove Jack's M21 (Belgian Wit)": {
        "atenuacion": 76.0, "tolerancia_abv": 12.0, "temp_range": "18-25 °C",
        "formato": "seca", "origen": "Mangrove Jack's (NZ)"},
    # --- Lallemand ---
    "Lallemand Nottingham (Ale Inglesa)": {
        "atenuacion": 80.0, "tolerancia_abv": 12.0, "temp_range": "10-22 °C",
        "formato": "seca", "origen": "Lallemand (Canadá)"},
    "Lallemand Bry-97 (West Coast)": {
        "atenuacion": 78.0, "tolerancia_abv": 12.0, "temp_range": "15-22 °C",
        "formato": "seca", "origen": "Lallemand (Canadá)"},
    "Lallemand Diamond (Lager)": {
        "atenuacion": 81.0, "tolerancia_abv": 12.0, "temp_range": "10-20 °C",
        "formato": "seca", "origen": "Lallemand (Canadá)"},
    "Lallemand Voss Kveik": {
        "atenuacion": 80.0, "tolerancia_abv": 14.0, "temp_range": "25-40 °C",
        "formato": "seca", "origen": "Lallemand (Canadá)"},
}

# ==========================================
# 5. MISCELÁNEOS / QUÍMICOS (4ª categoría del diseño)
# ==========================================
# Campos: origen (proveedor), categoria (familia), uso, notas.
MISCELANEOS_AR = {
    "Sulfato de Calcio (CaSO4 / Yeso)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Sales de agua",
        "uso": "Ajuste de agua", "notes": "Resalta el amargor (SO4). Pureza > 98%"},
    "Cloruro de Calcio (CaCl2)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Sales de agua",
        "uso": "Ajuste de agua", "notes": "Redondea el sabor (Cl)"},
    "Sulfato de Magnesio (Epsom)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Sales de agua",
        "uso": "Ajuste de agua", "notes": "Aporta Mg y SO4"},
    "Cloruro de Sodio (Sal de Mesa)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Sales de agua",
        "uso": "Ajuste de agua", "notes": "Usar sin yodo ni antiaglomerantes"},
    "Bicarbonato de Sodio (NaHCO3)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Sales de agua",
        "uso": "Ajuste de agua", "notes": "Sube el pH / aporta alcalinidad"},
    "Ácido Láctico 88%": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Ácidos",
        "uso": "Corrección de pH", "notes": "Para macerado y agua de lavado"},
    "Ácido Fosfórico": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Ácidos",
        "uso": "Corrección de pH", "notes": "Alternativa al láctico"},
    "Irish Moss (Musgo de Irlanda)": {
        "origen": "Proveedor cervecero", "categoria": "Clarificantes",
        "uso": "Hervido (15 min)", "notes": "Coagula proteínas"},
    "Whirlfloc / Clarificante": {
        "origen": "Proveedor cervecero", "categoria": "Clarificantes",
        "uso": "Hervido (10-15 min)", "notes": "Tableta o polvo"},
    "Gelatina sin sabor": {
        "origen": "Proveedor cervecero", "categoria": "Clarificantes",
        "uso": "Cold crash", "notes": "Clarificación en frío"},
    "Nutriente de Levadura": {
        "origen": "Proveedor cervecero", "categoria": "Nutrientes",
        "uso": "Hervido (10 min)", "notes": "Recomendado en fermentaciones fuertes"},
    "Corrector de pH 5.2": {
        "origen": "Proveedor cervecero", "categoria": "Ácidos",
        "uso": "Macerado", "notes": "Buffer que estabiliza el pH"},
    "Taninos / Polvo de cáscara": {
        "origen": "Proveedor cervecero", "categoria": "Clarificantes",
        "uso": "Macerado / Hervido", "notes": "Mejora el prensado del grano"},
    "Cáscara de Naranja Dulce": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido (5-10 min)", "notes": "Witbier: 20-30 g / 20 L"},
    "Cáscara de Naranja Amarga": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido (5-10 min)", "notes": "Witbier: 15-25 g / 20 L"},
    "Coriandro en grano": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido (5-10 min)", "notes": "Witbier: 10-20 g / 20 L"},
    "Semillas de Cilantro": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido", "notes": "Perfil cítrico-especiado"},
    "Anís / Hinojo": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido", "notes": "Estilos belgas y saison"},
    "Canela en rama": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Hervido / Secundario", "notes": "Navideñas y pumpkin ale"},
    "Vainilla (chaucha)": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Secundario", "notes": "1-2 chauchas / 20 L"},
    "Cacao nibs": {
        "origen": "Dietética", "categoria": "Especias y adjuntos",
        "uso": "Secundario / maduración", "notes": "Stout y porter"},
    "Café en grano": {
        "origen": "Cafetería", "categoria": "Especias y adjuntos",
        "uso": "Cold brew al embotellar", "notes": "Imperial stout"},
    "Priming (Dextrosa)": {
        "origen": "Proveedor cervecero", "categoria": "Carbonatación",
        "uso": "Embotellado", "notes": "7 g/L aprox. para 2.4 vol CO2"},
    "Priming (Azúcar de mesa)": {
        "origen": "Dietética", "categoria": "Carbonatación",
        "uso": "Embotellado", "notes": "Ajustar por calculadora de priming"},
    "Ácido Ascórbico (Antioxidante)": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Antioxidantes",
        "uso": "Embotellado", "notes": "Evita oxidación en el envasado"},
    "Metabisulfito de Potasio": {
        "origen": "Laboratorio (grado alimentario)", "categoria": "Antioxidantes",
        "uso": "Embotellado / sanitizado", "notes": "Dosis muy baja"},
}


# ==========================================
# HELPERS PARA LA UI
# ==========================================
def get_maltas_list():
    return sorted(MALTAS_AR.keys())


def get_lupulos_list():
    return sorted(LUPULOS_AR.keys())


def get_levaduras_list():
    return sorted(LEVADURAS_AR.keys())


def get_miscelaneos_list():
    return sorted(MISCELANEOS_AR.keys())


def get_altitudes_list():
    return list(ALTITUDES_CORDOBA.keys())


def get_aguas_list():
    return list(PERFILES_AGUA_CORDOBA.keys())


def get_productores():
    """Productores/orígenes presentes en el catálogo (para el filtro del diseño)."""
    productores = set()
    for coleccion in (MALTAS_AR, LUPULOS_AR, LEVADURAS_AR, MISCELANEOS_AR):
        for datos in coleccion.values():
            origen = (datos.get("origen") or "").strip()
            if origen:
                productores.add(origen)
    return sorted(productores)


def get_categorias_malta():
    """Familias de grano, en el orden que muestra el diseño."""
    orden = [CATEGORIA_BASE, CATEGORIA_ESPECIAL, CATEGORIA_TOSTADA, CATEGORIA_ADJUNTO]
    vistas = {d.get("categoria") for d in MALTAS_AR.values()}
    return [c for c in orden if c in vistas] + sorted(vistas - set(orden) - {None})
