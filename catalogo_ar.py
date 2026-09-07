# catalogo_ar.py
# /home/saintwick/Escritorio/beer_vgb/catalogo_ar.py
# 2024-05-17 (Actualizado v2)
# Autor: SaintWick

"""
Catálogo de Insumos y Perfiles Geográficos de Argentina (Mercado Cerveceros).
Cumple con la Sección 4 del Informe Técnico de BrewApp Córdoba.
"""

# ==========================================
# 1. PERFILES GEOGRÁFICOS DE CÓRDOBA (§3.A y §5 - Pantalla 1)
# ==========================================
# La altitud reduce la presión atmosférica y el punto de ebullición.
# Altitudes extraídas de datos geográficos oficiales.

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
    "Personalizado": 0  # El usuario ingresa el valor manualmente
}

# Perfiles de agua estimados de la provincia (Promedios generales)
# 'ph' = pH típico del agua de entrada (se usa en la estimación de pH de maceración)
PERFILES_AGUA_CORDOBA = {
    "Córdoba Capital (Agua de Red)": {"ca": 25.0, "mg": 5.0, "hco3": 80.0, "ph": 7.3},
    "La Cumbre (Agua de Sierra)": {"ca": 10.0, "mg": 2.0, "hco3": 30.0, "ph": 6.8},
    "Villa Carlos Paz (Agua de Red)": {"ca": 30.0, "mg": 8.0, "hco3": 90.0, "ph": 7.2},
    "Río Cuarto (Agua de Red)": {"ca": 45.0, "mg": 12.0, "hco3": 150.0, "ph": 7.5},
    "Agua Destilada / Ósmosis": {"ca": 0.0, "mg": 0.0, "hco3": 0.0, "ph": 7.0}
}

# ==========================================
# 2. MALTA Y FERMENTABLES (§4 - MaltAr, Cargill, Weyermann)
# ==========================================
# Valores técnicos estándar (Extracto PPG x1000, Color en °Lovibond)

MALTAS_AR = {
    # --- Nacionales (MaltAr / Cargill / Uma Malta) ---
    "MaltAr / Cargill Pilsen": {"extracto": 300, "color": 2.0},
    "MaltAr / Cargill Malta Base": {"extracto": 300, "color": 2.5},
    "MaltAr / Cargill Munich": {"extracto": 295, "color": 8.0},
    "MaltAr / Cargill Caramel 40": {"extracto": 280, "color": 20.0},
    "MaltAr / Cargill Caramel 120": {"extracto": 275, "color": 60.0},
    "MaltAr / Cargill Chocolate": {"extracto": 270, "color": 350.0},
    "MaltAr / Cargill Black (Carafa)": {"extracto": 270, "color": 500.0},

    "Uma Malta Pilsen": {"extracto": 298, "color": 2.2},
    "Uma Malta Base": {"extracto": 298, "color": 2.5},
    "Uma Malta Munich": {"extracto": 293, "color": 9.0},
    "Uma Malta Caramel 150": {"extracto": 275, "color": 75.0},
    "Uma Malta Negra": {"extracto": 270, "color": 500.0},

    # --- Importados (Weyermann - Líder en distribuidoras AR) ---
    "Weyermann Pilsner": {"extracto": 305, "color": 2.0},
    "Weyermann Munich I": {"extracto": 300, "color": 7.0},
    "Weyermann Munich II": {"extracto": 300, "color": 9.0},
    "Weyermann Caramunich I": {"extracto": 285, "color": 25.0},
    "Weyermann Caramunich III": {"extracto": 280, "color": 55.0},
    "Weyermann Caraaroma": {"extracto": 282, "color": 35.0},
    "Weyermann Carafa Special I": {"extracto": 280, "color": 350.0},
    "Weyermann Carafa Special III": {"extracto": 280, "color": 500.0},
    "Weyermann Smoked Malt (Ahumada)": {"extracto": 300, "color": 3.0},

    # --- Adjuntos Comunes ---
    "Avena Arrollada (Flaked Oats)": {"extracto": 280, "color": 2.0},
    "Maíz Flaked (Flaked Corn)": {"extracto": 290, "color": 1.0},
    "Trigo Flaked (Flaked Wheat)": {"extracto": 290, "color": 2.0},
    "Cebada Cruda (Flaked Barley)": {"extracto": 280, "color": 2.0},
}

# ==========================================
# 3. LÚPULOS (§4 - Patagónicos e Importados)
# ==========================================
# Se ingresan con un %AA promedio de referencia.
# La UI debe permitir editar el %AA real del lote impreso en el empaque.

LUPULOS_AR = {
    # --- Nacionales (Patagónicos) ---
    "Cascade Argentino": {"aa": 6.0, "formato": "pellet"},
    "Mapuche": {"aa": 8.0, "formato": "pellet"},
    "Victoria": {"aa": 7.0, "formato": "pellet"},
    "Brewer's Gold Argentino": {"aa": 7.5, "formato": "pellet"},
    "Spalter Argentino": {"aa": 4.5, "formato": "pellet"},

    # --- Importados (Comunes en Cibart / Demon) ---
    "Citra (USA)": {"aa": 12.5, "formato": "pellet"},
    "Mosaic (USA)": {"aa": 11.5, "formato": "pellet"},
    "Amarillo (USA)": {"aa": 9.0, "formato": "pellet"},
    "Centennial (USA)": {"aa": 10.0, "formato": "pellet"},
    "Columbus / CTZ (USA)": {"aa": 15.0, "formato": "pellet"},
    "Simcoe (USA)": {"aa": 13.0, "formato": "pellet"},
    "Chinook (USA)": {"aa": 12.0, "formato": "pellet"},

    "Hallertau Mittelfrüh (DE)": {"aa": 4.0, "formato": "pellet"},
    "Tettnanger (DE)": {"aa": 4.5, "formato": "pellet"},
    "Spalter Select (DE)": {"aa": 4.5, "formato": "pellet"},
    "Saaz (CZ)": {"aa": 3.5, "formato": "pellet"},

    "East Kent Golding (UK)": {"aa": 5.0, "formato": "pellet"},
    "Fuggles (UK)": {"aa": 4.5, "formato": "pellet"},
    "Target (UK)": {"aa": 11.0, "formato": "pellet"},
}

# ==========================================
# 4. LEVADURAS (§4 - Fermentis y Mangrove Jack's)
# ==========================================
# Atenuación promedio (%) y Tolerancia de Alcohol (% ABV) para alertas dinámicas.

LEVADURAS_AR = {
    # --- Fermentis (Estándar de Mercado) ---
    "Fermentis US-05 (Ale Americana)": {"atenuacion": 81.0, "tolerancia_abv": 12.0},
    "Fermentis S-04 (Ale Inglesa)": {"atenuacion": 75.0, "tolerancia_abv": 11.0},
    "Fermentis W-34/70 (Lager)": {"atenuacion": 80.0, "tolerancia_abv": 10.5},
    "Fermentis K-97 (Ale Alemana)": {"atenuacion": 80.0, "tolerancia_abv": 12.0},
    "Fermentis T-58 (Belga)": {"atenuacion": 75.0, "tolerancia_abv": 12.5},
    "Fermentis BE-134 (Saison)": {"atenuacion": 85.0, "tolerancia_abv": 14.0},
    "Fermentis M-31 (Belga Tripsel)": {"atenuacion": 82.0, "tolerancia_abv": 14.0},

    # --- Mangrove Jack's (Muy popular en Argentina) ---
    "Mangrove Jack's M44 (US West Coast)": {"atenuacion": 80.0, "tolerancia_abv": 14.0},
    "Mangrove Jack's M15 (Empire Ale)": {"atenuacion": 76.0, "tolerancia_abv": 13.0},
    "Mangrove Jack's M27 (Californian Lager)": {"atenuacion": 78.0, "tolerancia_abv": 11.0},
    "Mangrove Jack's M29 (German Lager)": {"atenuacion": 80.0, "tolerancia_abv": 11.0},
    "Mangrove Jack's M47 (Belgian Abbey)": {"atenuacion": 83.0, "tolerancia_abv": 14.0},
}

# ==========================================
# HELPERS PARA LA UI
# ==========================================

def get_maltas_list():
    return sorted(list(MALTAS_AR.keys()))

def get_lupulos_list():
    return sorted(list(LUPULOS_AR.keys()))

def get_levaduras_list():
    return sorted(list(LEVADURAS_AR.keys()))

def get_altitudes_list():
    return list(ALTITUDES_CORDOBA.keys())

def get_aguas_list():
    return list(PERFILES_AGUA_CORDOBA.keys())
