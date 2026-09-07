# export_engine.py
# /home/saintwick/Escritorio/beer_vgb/export_engine.py
# 2024-05-17
# Autor: SaintWick

"""
Motor de exportación a PDF y BeerXML profesional.
"""

from fpdf import FPDF
import xml.etree.ElementTree as ET
from datetime import datetime

class PDFReceta(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, 'Cervecera VGB - By SaintWick', 0, 1, 'R')
        self.line(10, 15, 200, 15)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Pagina {self.page_no()}/{{nb}} | nicoweb45@proton.me', 0, 0, 'C')

def exportar_pdf(receta_data, filepath):
    """Genera un PDF profesional con la receta"""
    pdf = PDFReceta()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Título
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 15, receta_data.get('name', 'Sin Nombre'), 0, 1, 'C')

    # Info General
    pdf.set_font('Helvetica', '', 12)
    pdf.set_text_color(60, 60, 60)
    estilo = receta_data.get('style', 'N/A')
    volumen = receta_data.get('volume', 20)
    eficiencia = receta_data.get('efficiency', 0.75) * 100
    fecha = datetime.now().strftime("%d/%m/%Y")

    pdf.cell(0, 8, f"Estilo: {estilo} | Volumen: {volumen}L | Eficiencia: {eficiencia:.0f}% | Fecha: {fecha}", 0, 1, 'C')
    pdf.ln(5)

    # Parámetros Calculados
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, 'Parametros Calculados', 0, 1, 'L', True)

    pdf.set_font('Helvetica', '', 11)
    pdf.cell(95, 8, f"OG: {receta_data.get('og', 0):.4f}", 1, 0, 'C')
    pdf.cell(95, 8, f"FG: {receta_data.get('fg', 0):.4f}", 1, 1, 'C')
    pdf.cell(95, 8, f"ABV: {receta_data.get('abv', 0)}%", 1, 0, 'C')
    pdf.cell(95, 8, f"IBU: {receta_data.get('ibu', 0)}", 1, 1, 'C')
    pdf.cell(95, 8, f"SRM: {receta_data.get('srm', 0)}", 1, 0, 'C')
    pdf.cell(95, 8, f"pH Maceración: {receta_data.get('ph', 0)}", 1, 1, 'C')
    pdf.cell(95, 8, f"pH Post-Hervor: {receta_data.get('ph_hervor', '-')}", 1, 0, 'C')
    pdf.cell(95, 8, f"pH Final (lúpulo): {receta_data.get('ph_final', '-')}", 1, 1, 'C')
    pdf.ln(5)

    # Ingredientes - Maltas
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Maltas y Adjuntos', 0, 1, 'L', True)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(80, 8, 'Nombre', 1, 0, 'C')
    pdf.cell(40, 8, 'Cantidad (Kg)', 1, 0, 'C')
    pdf.cell(40, 8, 'Extracto (PPG)', 1, 0, 'C')
    pdf.cell(30, 8, 'Color (SRM)', 1, 1, 'C')

    pdf.set_font('Helvetica', '', 10)
    for m in receta_data.get('maltas', []):
        pdf.cell(80, 8, m.get('nombre', ''), 1, 0, 'L')
        pdf.cell(40, 8, str(m.get('cantidad', 0)), 1, 0, 'C')
        pdf.cell(40, 8, str(m.get('extracto', 300)), 1, 0, 'C')
        pdf.cell(30, 8, str(m.get('color', 2)), 1, 1, 'C')
    pdf.ln(5)

    # Ingredientes - Lúpulos
    pdf.set_font('Helvetica', 'B', 14)
    pdf.cell(0, 10, 'Lupulos', 0, 1, 'L', True)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.cell(70, 8, 'Nombre', 1, 0, 'C')
    pdf.cell(35, 8, 'Cantidad (g)', 1, 0, 'C')
    pdf.cell(35, 8, 'Alfa Acidos %', 1, 0, 'C')
    pdf.cell(50, 8, 'Tiempo (min)', 1, 1, 'C')

    pdf.set_font('Helvetica', '', 10)
    for l in receta_data.get('lupulos', []):
        pdf.cell(70, 8, l.get('nombre', ''), 1, 0, 'L')
        pdf.cell(35, 8, str(l.get('cantidad', 0)), 1, 0, 'C')
        pdf.cell(35, 8, str(l.get('aa', 0)), 1, 0, 'C')
        pdf.cell(50, 8, str(l.get('tiempo', 0)), 1, 1, 'C')
    pdf.ln(5)

    # Notas
    if receta_data.get('notes'):
        pdf.set_font('Helvetica', 'B', 14)
        pdf.cell(0, 10, 'Notas del Cocinero', 0, 1, 'L', True)
        pdf.set_font('Helvetica', '', 11)
        pdf.multi_cell(0, 8, receta_data['notes'])

    try:
        pdf.output(filepath)
        return True
    except Exception as e:
        print(f"Error PDF: {e}")
        return False

def exportar_beerxml(receta_data, filepath):
    """Genera un archivo BeerXML estándar para importar en otros softwares"""
    recipe = ET.Element("RECIPE")

    ET.SubElement(recipe, "NAME").text = receta_data.get('name', '')
    ET.SubElement(recipe, "VERSION").text = "1"
    ET.SubElement(recipe, "TYPE").text = "All Grain"
    ET.SubElement(recipe, "BATCH_SIZE").text = str(receta_data.get('volume', 20.0))
    ET.SubElement(recipe, "EFFICIENCY").text = str(receta_data.get('efficiency', 0.75) * 100)
    ET.SubElement(recipe, "OG").text = str(receta_data.get('og', 1.0))
    ET.SubElement(recipe, "FG").text = str(receta_data.get('fg', 1.0))

    # Maltas
    ferm_element = ET.SubElement(recipe, "FERMENTABLES")
    for m in receta_data.get('maltas', []):
        f = ET.SubElement(ferm_element, "FERMENTABLE")
        ET.SubElement(f, "NAME").text = m.get('nombre', '')
        ET.SubElement(f, "VERSION").text = "1"
        ET.SubElement(f, "TYPE").text = "Grain"
        ET.SubElement(f, "AMOUNT").text = str(m.get('cantidad', 0.0))
        ET.SubElement(f, "YIELD").text = str(m.get('extracto', 300) / 3.8) # Aproximación a porcentaje
        ET.SubElement(f, "COLOR").text = str(m.get('color', 2))

    # Lúpulos
    hops_element = ET.SubElement(recipe, "HOPS")
    for l in receta_data.get('lupulos', []):
        h = ET.SubElement(hops_element, "HOP")
        ET.SubElement(h, "NAME").text = l.get('nombre', '')
        ET.SubElement(h, "VERSION").text = "1"
        ET.SubElement(h, "ALPHA").text = str(l.get('aa', 0.0))
        ET.SubElement(h, "AMOUNT").text = str(l.get('cantidad', 0.0) / 1000.0) # BeerXML usa Kg
        ET.SubElement(h, "USE").text = "Boil"
        ET.SubElement(h, "TIME").text = str(l.get('tiempo', 60))

    # Notas
    ET.SubElement(recipe, "NOTES").text = receta_data.get('notes', '')

    tree = ET.ElementTree(recipe)
    try:
        ET.indent(tree, space="  ", level=0) # Python 3.9+ para formato bonito
        tree.write(filepath, encoding="utf-8", xml_declaration=True)
        return True
    except Exception as e:
        print(f"Error XML: {e}")
        return False
