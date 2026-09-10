# 🔬 ANÁLISIS DE FÓRMULAS — Brewfather / BeerSmith
### Extraído de la documentación oficial y fuentes citadas por ellos
> Objetivo: usar la misma lógica y tener **cálculos reales**. Documento de análisis (no es función de la app).

---

## 1. BREWFATHER (docs oficiales)

### 1.1 Color del mosto (3 pasos)
```
MCU = (Color del grano [Lovibond] × Peso [lb]) / Volumen [gal]
SRM = 1.49 × MCU^0.69            ← ecuación de Morey (versión Brewfather)
EBC = SRM × 1.97
```
Brewfather la describe como "el método de una sola ecuación más preciso".

### 1.2 Alcohol (Settings → Formulas)
| Opción | Fórmula |
|---|---|
| **Standard** | `ABV = (OG − FG) × 131.25` (buena hasta ~8%) |
| **Alternative** | `ABV = 76.08 × (OG − FG) / (1.775 − OG) × (FG / 0.794)` (mejor en cervezas fuertes) |

### 1.3 Final Gravity (FG) — 3 métodos
| Opción | Qué considera |
|---|---|
| **Simple** | Solo la **atenuación de la levadura** aplicada a la OG (no considera macerado ni granos) |
| **Normal** *(recomendado)* | Atenuación + **tipo de fermentables** + **temperatura de macerado** + aporte **no fermentable** de maltas especiales |
| **Advanced** | Separa por grano la parte **fermentable / no fermentable**, + atenuación + temperatura de macerado |

### 1.4 IBU — 4 fórmulas seleccionables
| Fórmula | Característica |
|---|---|
| **Tinseth** (default) | Curvas empíricas de utilización según **tiempo de hervor y densidad**. La más usada |
| **Rager** | Factor de ajuste de densidad cuando OG > 1.050 y curva de utilización con `tanh`. Suele dar **más IBU** que Tinseth |
| **Noonan** | **Tabla** de utilización por tiempo y densidad (no es curva continua; escalona) |
| **Garetz** | La más compleja: densidad del hervor, **altitud** y **floculación de la levadura**. Suele dar **menos IBU** |

### 1.5 Balance amargo/malto
- **BU:GU** clásico = `IBU / ((OG − 1) × 1000)`
- **RBR (Relative Bitterness Ratio)** — Mad Alchemist: mejora el BU:GU incorporando la **atenuación**
  (más atenuación ⇒ menos dulzor residual ⇒ se percibe más amargo con los mismos IBU).

### 1.6 Otras fórmulas que Brewfather cita en "Acerca de"
| Tema | Fuente |
|---|---|
| Frescura del lúpulo / IBU avanzados | **John-Paul Hosom** — alchemyoverlord.wordpress.com (modelo **SMPH**) |
| FG con refractómetro | **Petr Novotný** — diversity-pivo.blogspot.com |
| Calculadora de agua | **DM Riffe** — homebrewingphysics.blogspot.com + **Kai Troester** — braukaiser.com |
| Calculadora de levadura | **Kai Troester** + **Chris White** |
| Guías de estilo | BJCP · Brewers Association · Norbrygg · SHBF |

🔗 Fórmulas: https://docs.brewfather.app/settings.md · Cálculos: https://docs.brewfather.app/recipes/calculations.md

**Dato clave:** Tinseth clásico **predice 0 IBU en flameout/whirlpool** — por eso el modelo SMPH de Hosom.

---

## 2. BEERSMITH

- **Color**: usa la ecuación de **Morey** por defecto (`SRM = 1.4922 × MCU^0.6859`, BrewWiki),
  y permite alternativas (MCU directo para colores < 10.5 SRM; Daniels / Mosher).
- **IBU**: ofrece **Tinseth, Rager, Garetz y Mosher** (seleccionable).
- **OG**: a partir del **potencial de extracto (PPG / L°)** de cada grano × **eficiencia** (brewhouse/mash),
  con corrección por **volumen y contracción** del mosto.
- **FG**: **atenuación de la levadura** + **fermentabilidad** propia de cada grano (apparent attenuation).
- **Agua**: herramienta propia con **alcalinidad residual** y estimación de **pH de macerado**.
- **Perfil de equipo**: volumen de olla/fermentador, pérdidas, evaporación, eficiencia → define volúmenes reales.

🔗 BrewWiki (Morey): https://forum.beersmith.com/index.php?title=Estimating_Color&oldid=2284

---

## 3. COMPARACIÓN con Cervecera VGB (estado actual del motor)

| Cálculo | Cervecera VGB hoy | Brewfather / BeerSmith | Acción propuesta |
|---|---|---|---|
| **Color (SRM)** | `MCU = kg×L×2.205/(vol×0.264)`; si MCU>7 → `1.4922×MCU^0.6859`, si no `SRM=MCU` | `1.49×MCU^0.69` (Brewfather) / `1.4922×MCU^0.6859` (BeerSmith) | ✅ Alinear a Morey puro + mostrar **EBC** |
| **OG** | `GU = Σ(kg × extracto × eficiencia) / volumen` | Potencial (PPG) × eficiencia + **contracción** + volumen real del equipo | ⚠️ Revisar eficiencia/volumen + **Fase 4 equipo** |
| **FG** | **Solo atenuación** (equivale a *Simple*) | **Normal** (atenuación + macerado + especiales) / Advanced | 🔴 **Implementar "Normal"** y selector |
| **ABV** | `(OG−FG)×131.25` (Standard) | Standard / **Alternative** (76.08…) | ⚠️ Agregar opción Alternative |
| **IBU** | **Tinseth** + factor fijo 10% en whirlpool | Tinseth / Rager / Noonan / Garetz + modelo SMPH | 🔴 **Selector de fórmulas** + whirlpool real |
| **Balance** | BU:GU | BU:GU **y RBR** | ⚠️ Agregar RBR |
| **pH macerado** | RA simplificada + corrección por color | RA + acidez del grano (Riffe/Troester) | ⏸️ Documentado (agua NO va como función) |
| **Densímetro** | Corrección ASBC ✅ | Similar | ✅ Ya está |
| **Refractómetro → FG** | ❌ | Fórmula de Novotný | ⚠️ Agregar herramienta |
| **Equipo** | ❌ | Perfil de equipo (volúmenes, pérdidas, eficiencia) | 🔴 **Fase 4** |

---

## 4. PLAN DE CORRECCIÓN DE CÁLCULOS (Fase 0) — propuesto

1. **FG "Normal"**: `FG = 1 + (OG−1) × (1 − AA_efectiva/100)`, donde
   `AA_efectiva = AA_levadura × factor_macerado × factor_especiales`
   - `factor_macerado`: 63 °C ≈ 1.05 · 65 °C ≈ 1.00 · 67 °C ≈ 0.95 · 70 °C ≈ 0.88
   - `factor_especiales`: descuenta el aporte no fermentable de crystal/roasted (aprox. por % del grano bill)
   - Selector: **Simple / Normal / Advanced**.
2. **IBU seleccionable**: Tinseth (actual), **Rager**, **Garetz**, **Noonan**; y corregir whirlpool/flameout
   (en vez del 10% fijo: utilización decreciente en el tiempo de hop stand, modelo tipo SMPH).
3. **ABV seleccionable**: Standard / Alternative.
4. **Color**: Morey puro (1.4922 × MCU^0.6859), sin umbral; mostrar **EBC**.
5. **Balance**: agregar **RBR** (con atenuación).
6. **Herramientas**: refractómetro→FG (Novotný), carbohidratos/calorías (ya está), carbonatación (opcional).
7. **Fase 4 — Perfil de equipo**: volumen de olla/fermentador, pérdidas por trub/mangueras,
   evaporación L/h, eficiencia, contracción del mosto → **volúmenes y OG reales**.

### Cómo validar (lo que propuso Stephan)
Hacer **la misma receta** en Cervecera VGB, Brewfather, Brew-o-matic y BeerSmith y comparar
OG · FG · ABV · IBU · SRM. Ajustar hasta coincidir dentro de ±1–2% (IBU ±10%).

---

## 5. Fuentes
- Brewfather: https://docs.brewfather.app/settings.md · https://docs.brewfather.app/recipes/calculations.md
- RBR (Mad Alchemist): https://docs.brewfather.app/recipes/designer/relative-bitterness-ratio.md
- BeerSmith / BrewWiki (Morey): https://forum.beersmith.com/index.php?title=Estimating_Color&oldid=2284
- IBU / SMPH: https://alchemyoverlord.wordpress.com/
- Agua: https://www.homebrewingphysics.blogspot.com/ · https://braukaiser.com/
- BeerXML (interoperabilidad): http://www.beerxml.com/
