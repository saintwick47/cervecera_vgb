# 💧 INFORMACIÓN SOBRE AGUA PARA CERVECEROS
### Documento de referencia (extraído de fuentes públicas de la web)
> Este archivo es material de estudio/consulta. **No es una función de la app.**

---

## 1. Fuente principal: curso de agua (gratuito)
**"Tratamiento de agua para cerveceros"** — Olavarría Cerveza (Thinkific)
🔗 https://olavarriacerveza.thinkific.com/courses/tratamiento-de-agua-para-cerveceros

**Temario (capítulos y temas):**
1. **Bienvenidos** — Introducción.
2. **Aprendamos sobre agua** — Composición del agua de elaboración · Análisis de ejemplo · Evaluación.
3. **Kit de tratamiento de agua** — Cuidados del medidor de pH · Almacenamiento de sales · Cómo medir el pH · Evaluación.
4. **Ajustando la química del agua** — Principales tratamientos del agua · Filtrado y decloración ·
   Preparación del agua de macerado · Preparación del agua de lavado · Relación sulfato/cloruro · Evaluación.
5. **Ajustando la química del macerado** — Principales tratamientos para ajustar el pH de macerado ·
   Elección de un perfil de agua · Selección de maltas · **Dilución con agua de ósmosis** ·
   **Adiciones de sales** · **Adiciones de ácidos** · Cambios en la relación de empaste · Evaluación.
6. **Herramientas** — Calculadoras y utilidades.

> Nota: el curso es gratis; conviene inscribirse para ver el detalle de cada tema.

---

## 2. Conceptos clave (conocimiento público de química del agua cervecera)

### Iones que importan (ppm = mg/L)
| Ion | Efecto principal |
|---|---|
| **Ca** (calcio) | Baja el pH, ayuda a la clarificación y a la levadura. 50–150 ppm típico |
| **Mg** (magnesio) | Nutriente de levadura; amargo áspero en exceso (>40 ppm). Típico 5–20 |
| **Na** (sodio) | Realza sabor; >150 ppm da sabor salado/metálico |
| **HCO₃** (bicarbonato) | **Alcalinidad**: sube el pH del macerado. El enemigo en cervezas claras |
| **SO₄** (sulfato) | Realza el amargor del lúpulo (seco) |
| **Cl** (cloruro) | Realza la maltosidad/plenitud |
| **pH** | Mide acidez; en macerado el objetivo es **5.2–5.6 (ideal 5.3–5.4)** |

### Alcalinidad residual (RA)
```
RA (ppm como CaCO3) ≈ Alcalinidad (ppm CaCO3) − [ (Ca ppm / 3.5) + (Mg ppm / 7) ]
```
- **RA alta** → sube el pH del macerado (problema en cervezas claras).
- **RA baja/negativa** → baja el pH (bien para cervezas claras, mal para oscuras sin ajuste).

### Sales de ajuste (aporte por **1 g en 1 L**)
| Sal | Aporte |
|---|---|
| Yeso (CaSO₄·2H₂O) | Ca **+232.8** ppm · SO₄ **+557.7** ppm |
| Cloruro de calcio (CaCl₂·2H₂O) | Ca **+272.6** ppm · Cl **+483.0** ppm |
| Epsom (MgSO₄·7H₂O) | Mg **+98.6** ppm · SO₄ **+389.7** ppm |
| Sal de mesa (NaCl) | Na **+393.4** ppm · Cl **+606.6** ppm |
| Bicarbonato de sodio (NaHCO₃) | Na **+273.7** ppm · HCO₃ **+728.6** ppm |

### Ácidos
- **Láctico 88%**: ~1 mL por kg de grano baja ~0.1 pH (depende del poder buffer del grano).
- **Fosfórico**: alternativa, más neutro en sabor.
- Siempre medir con pHmetro; nunca calcular a ciegas.

### Dilución con ósmosis (RO)
Mezclar con agua de ósmosis (≈0 minerales) baja **proporcionalmente todos los iones**:
```
%RO necesario ≈ (1 − objetivo / actual) × 100     (para el ion limitante, normalmente HCO3)
```
Ej.: HCO₃ actual 150 ppm y objetivo 30 ppm → RO ≈ 80%.

### Relación sulfato/cloruro (SO₄/Cl)
| Relación | Percepción |
|---|---|
| < 0.8 | Predomina malta (dulce, pleno) |
| 0.8 – 1.5 | Equilibrada |
| 1.5 – 2.5 | Predomina lúpulo (amarga) |
| > 2.5 | Muy amarga/seca (IPA, West Coast) |

### Decloración (imprescindible si hay cloro/cloramina)
- Filtro de carbón activado, o **metabisulfito de potasio/sodio** (~1 tableta o 0.02 g por 20 L).
- El cloro produce **clorofenoles** (sabor medicinal) — muy difícil de corregir después.

### pH de macerado: cómo ajustarlo (orden práctico)
1. **Partir del análisis de tu agua** (Ca, Mg, Na, HCO₃, SO₄, Cl, pH).
2. Elegir el **perfil objetivo del estilo**.
3. Si el HCO₃ está muy alto → **diluir con ósmosis** hasta el objetivo.
4. Agregar **sales** para llegar a Ca/SO₄/Cl objetivo.
5. Ajustar el **pH con ácido** (láctico/fosfórico) hasta 5.2–5.6.
6. Medir el pH **15 min después de empastar** y corregir si hace falta.
7. El agua de **lavado** no debería superar ~pH 6 ni tener alcalinidad alta (riesgo de taninos).

---

## 3. Herramientas y referencias recomendadas
- **Brewfather – Water Calculator**: https://docs.brewfather.app/recipes/water-calculator
  (fórmulas basadas en **DM Riffe – homebrewingphysics.blogspot.com** y **Kai Troester – braukaiser.com**)
- **Bru'n Water** (planilla de referencia en química de agua).
- **EZ Water Calculator**.
- **Kai Troester** – braukaiser.com (macerado, pH, atenuación).
- **DM Riffe** – homebrewingphysics.blogspot.com (química del agua).
- **John Palmer** – "How to Brew" (capítulo de agua).

---

*Documento generado como referencia interna del proyecto Cervecera VGB.*
