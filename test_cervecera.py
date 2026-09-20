# test_cervecera.py
# 2024-05-17 (v2 - calibración Dry Irish Stout + auto-amargor)
# Autor: SaintWick
"""
Suite de tests integrados para Cervecera VGB.
Incluye tests de Motor, BD (CRUD e Inventario), Comparador BJCP,
calibración contra ficha Dry Irish Stout y round-trip del Auto-amargor.
Para ejecutar: python -m unittest test_cervecera.py -v
"""
import unittest
import os
import json
from brew_engine import BrewEngine
from database import DatabaseManager
from bjcp_styles import comparar_con_estilo, get_style_list
from app_gestion import parsear_texto_productos


class TestBrewEngine(unittest.TestCase):
    """Tests para el motor de cálculos cerveceros"""
    def setUp(self):
        """Datos de prueba basados en una IPA estándar de 20L"""
        self.receta_ipa = {
            "agua_vol": 20.0,
            "fg_estimada": 1.012,
            "maltas": [
                {'nombre': 'Pale Malt', 'cantidad': 4.0, 'extracto': 300},
                {'nombre': 'Crystal 20L', 'cantidad': 0.5, 'extracto': 250}
            ],
            "lupulos": [
                {'nombre': 'Cascade', 'cantidad': 30, 'aa': 6.0, 'tiempo': 60},
                {'nombre': 'Citra', 'cantidad': 20, 'aa': 12.0, 'tiempo': 5}
            ],
            "agua": {'ca': 50, 'mg': 10, 'hco3': 100}
        }
        self.eficiencia = 0.75

    def test_calcular_og(self):
        og = BrewEngine.calcular_og(self.receta_ipa['maltas'], self.receta_ipa['agua_vol'], self.eficiencia)
        self.assertAlmostEqual(og, 1.050, places=3)

    def test_calcular_ibu(self):
        og = BrewEngine.calcular_og(self.receta_ipa['maltas'], self.receta_ipa['agua_vol'], self.eficiencia)
        ibu = BrewEngine.calcular_ibu(self.receta_ipa['lupulos'], self.receta_ipa['agua_vol'], og)
        self.assertGreater(ibu, 20)
        self.assertLess(ibu, 40)

    def test_calcular_abv(self):
        abv = BrewEngine.calcular_abv(1.065, 1.015)
        self.assertAlmostEqual(abv, 6.56, places=2)

    def test_calcular_aguas(self):
        # Motor paridad móvil: incluye evaporación 10%/60min → lavado 13.0 L
        aguas = BrewEngine.calcular_aguas(4.5, 20.0, ratio_maceracion=3.0)
        self.assertEqual(aguas['agua_maceracion'], 13.5)
        self.assertEqual(aguas['agua_lavado'], 13.0)

    def test_estimar_ph(self):
        ph_blanda = BrewEngine.estimar_ph_maceracion(50, 10, 20, srm=10)
        self.assertLess(ph_blanda, 5.6)

    def test_ph_con_malta_oscura(self):
        ph_rubia = BrewEngine.estimar_ph_maceracion(50, 10, 150, srm=5)
        ph_stout = BrewEngine.estimar_ph_maceracion(50, 10, 150, srm=35)
        self.assertLess(ph_stout, ph_rubia)

    def test_calcular_receta_completa(self):
        resultados = BrewEngine.calcular_receta_completa(self.receta_ipa, self.eficiencia)
        self.assertIn('og', resultados)
        self.assertIn('ibu', resultados)
        self.assertIn('abv', resultados)
        self.assertIn('aguas', resultados)
        self.assertIn('ph', resultados)
        self.assertAlmostEqual(resultados['og'], 1.050, places=3)
        self.assertGreater(resultados['ibu'], 0)
        self.assertIsInstance(resultados['ph'], float)


class TestAutoAmargor(unittest.TestCase):
    """Round-trip de la inversa IBU -> gramos (botón 🎯 Auto-amargor, v17)."""
    OG = 1.047
    V = 20.0
    AA = 5.0

    def test_inversa_tinseth_roundtrip(self):
        g = BrewEngine.calcular_gramos_para_ibu(40.0, self.V, self.OG, self.AA, 60, 400,
                                                "tinseth", "pellet")
        self.assertAlmostEqual(g, 64.7, delta=0.6)
        ibu = BrewEngine.calcular_ibu([{'cantidad': g, 'aa': self.AA, 'tiempo': 60,
                                        'formato': 'pellet'}],
                                      self.V, self.OG, 400, "tinseth")
        self.assertAlmostEqual(ibu, 40.0, delta=0.5)

    def test_inversa_rager_roundtrip(self):
        g = BrewEngine.calcular_gramos_para_ibu(40.0, self.V, self.OG, self.AA, 60, 400,
                                                "rager", "pellet")
        self.assertAlmostEqual(g, 49.8, delta=0.6)
        ibu = BrewEngine.calcular_ibu([{'cantidad': g, 'aa': self.AA, 'tiempo': 60,
                                        'formato': 'pellet'}],
                                      self.V, self.OG, 400, "rager")
        self.assertAlmostEqual(ibu, 40.0, delta=0.5)

    def test_guardas_entrada_invalida(self):
        self.assertEqual(BrewEngine.calcular_gramos_para_ibu(0, 20, 1.05, 5), 0.0)
        self.assertEqual(BrewEngine.calcular_gramos_para_ibu(40, 0, 1.05, 5), 0.0)
        self.assertEqual(BrewEngine.calcular_gramos_para_ibu(40, 20, 1.05, 0), 0.0)


class TestCalibracionDryIrishStout(unittest.TestCase):
    """Calibración contra ficha externa Dry Irish Stout (20 L, ef 72%)."""
    def setUp(self):
        self.datos = {
            'maltas': [
                {'nombre': 'Pale Ale', 'cantidad': 3.54, 'extracto': 300, 'color': 3},
                {'nombre': 'Trigo Flaked (Flaked Wheat)', 'cantidad': 0.44, 'extracto': 290, 'color': 2},
                {'nombre': 'Cebada Tostada (Roasted Barley)', 'cantidad': 0.44, 'extracto': 250, 'color': 500},
            ],
            'lupulos': [],
            'agua_vol': 20.0,
            'agua': {'ca': 60, 'mg': 10, 'hco3': 140, 'ph': 7.0},
            'tiempo_hervor': 60,
            'ratio_maceracion': 3.0,
            'absorcion': 1.0,
            'atenuacion_levadura': 80.0,
            'tolerancia_abv': 12.0,
            'metodo_fg': 'normal',
            'temp_macerado': 65.0,
            'formula_ibu': 'tinseth',
            'perdidas_l': 2.0,
            'evaporacion_l_h': 2.0,
        }
        self.r = BrewEngine.calcular_receta_completa(self.datos, 0.72, 400)

    def test_og(self):
        self.assertAlmostEqual(self.r['og'], 1.047, places=3)

    def test_srm(self):
        self.assertGreaterEqual(self.r['srm'], 32)
        self.assertLessEqual(self.r['srm'], 35)

    def test_aguas(self):
        self.assertAlmostEqual(self.r['aguas']['agua_maceracion'], 13.26, places=1)
        self.assertAlmostEqual(self.r['aguas']['volumen_pre_hervor'], 24.0, places=0)

    def test_ph_calibrado(self):
        # Ficha: pH 5.4-5.5 con HCO3 100-180; tolerancia de modelo ±0.1
        self.assertGreaterEqual(self.r['ph'], 5.3)
        self.assertLessEqual(self.r['ph'], 5.6)

    def test_ibu_con_auto_amargor(self):
        g = BrewEngine.calcular_gramos_para_ibu(40.0, 20.0, self.r['og'], 5.0, 60, 400,
                                                "tinseth", "pellet")
        ibu = BrewEngine.calcular_ibu([{'cantidad': g, 'aa': 5.0, 'tiempo': 60,
                                        'formato': 'pellet'}],
                                      20.0, self.r['og'], 400, "tinseth")
        self.assertAlmostEqual(ibu, 40.0, delta=0.5)


class TestDatabase(unittest.TestCase):
    """Tests para la base de datos SQLite (Recetas e Inventario)"""
    def setUp(self):
        self.db = DatabaseManager(db_name="test_vgb.db")

    def tearDown(self):
        self.db.close()
        if os.path.exists(self.db.db_path):
            os.remove(self.db.db_path)

    def test_crear_receta_con_ingredientes(self):
        receta = {
            'name': 'Test IPA', 'volume': 20.0, 'efficiency': 0.75,
            'notes': 'Agregar dry hop', 'maltas': [{'nombre': 'Pale', 'cantidad': 4.0, 'extracto': 300}],
            'lupulos': [{'nombre': 'Cascade', 'cantidad': 30, 'aa': 6.0, 'tiempo': 60}]
        }
        recipe_id = self.db.save_recipe(receta)
        self.assertIsNotNone(recipe_id)
        receta_db = self.db.get_full_recipe(recipe_id)
        self.assertEqual(receta_db['name'], 'Test IPA')
        self.assertEqual(len(receta_db['maltas']), 1)
        self.assertEqual(receta_db['notes'], 'Agregar dry hop')

    def test_no_duplicados(self):
        receta = {'name': 'Receta Unica', 'volume': 10.0, 'efficiency': 0.70, 'notes': '', 'maltas': [], 'lupulos': []}
        id1 = self.db.save_recipe(receta)
        id2 = self.db.save_recipe(receta)
        self.assertIsNotNone(id1)
        self.assertIsNone(id2)

    def test_actualizar_receta(self):
        receta = {'name': 'Vieja IPA', 'volume': 20.0, 'efficiency': 0.75, 'notes': '', 'maltas': [{'nombre': 'Pale', 'cantidad': 4.0, 'extracto': 300}], 'lupulos': []}
        recipe_id = self.db.save_recipe(receta)
        # Actualizar nombre y añadir lúpulo
        receta_update = {'name': 'Nueva IPA', 'volume': 25.0, 'efficiency': 0.80, 'notes': 'Modificada', 'maltas': [], 'lupulos': [{'nombre': 'Citra', 'cantidad': 20, 'aa': 12.0, 'tiempo': 5}]}
        success = self.db.update_recipe(recipe_id, receta_update)
        self.assertTrue(success)
        receta_db = self.db.get_full_recipe(recipe_id)
        self.assertEqual(receta_db['name'], 'Nueva IPA')
        self.assertEqual(receta_db['volume'], 25.0)
        self.assertEqual(len(receta_db['maltas']), 0)  # Borramos maltas
        self.assertEqual(len(receta_db['lupulos']), 1)  # Añadimos 1 lúpulo

    def test_eliminar_receta(self):
        receta = {'name': 'A Borrar', 'volume': 10.0, 'efficiency': 0.70, 'notes': '', 'maltas': [{'nombre': 'Pale', 'cantidad': 2.0, 'extracto': 300}], 'lupulos': []}
        recipe_id = self.db.save_recipe(receta)
        self.assertIsNotNone(recipe_id)
        self.db.delete_recipe(recipe_id)
        receta_db = self.db.get_full_recipe(recipe_id)
        self.assertIsNone(receta_db)  # Debe devolver None si se borró

    def test_inventario_agregar_y_sumar(self):
        # Añadir stock inicial
        self.db.add_inventory_item('Malta', 'Pale Ale', 5.0, 'Kg')
        item = self.db.get_inventory_item_by_name('Malta', 'Pale Ale')
        self.assertIsNotNone(item)
        self.assertEqual(item['amount'], 5.0)
        # Sumar stock existente
        self.db.add_inventory_item('Malta', 'Pale Ale', 2.5, 'Kg')
        item_actualizado = self.db.get_inventory_item_by_name('Malta', 'Pale Ale')
        self.assertEqual(item_actualizado['amount'], 7.5)

    def test_inventario_restar_y_eliminar(self):
        self.db.add_inventory_item('Lúpulo', 'Cascade', 100.0, 'g')
        self.db.subtract_inventory_item('Lúpulo', 'Cascade', 40.0)
        item = self.db.get_inventory_item_by_name('Lúpulo', 'Cascade')
        self.assertEqual(item['amount'], 60.0)
        # Restar todo y verificar que desaparece de la BD (nuestro método borra si <= 0)
        self.db.subtract_inventory_item('Lúpulo', 'Cascade', 60.0)
        item_vacio = self.db.get_inventory_item_by_name('Lúpulo', 'Cascade')
        self.assertIsNone(item_vacio)

    def test_cargar_json_50_recetas(self):
        json_path = os.path.join(os.path.dirname(__file__), 'recetas_base.json')
        if not os.path.exists(json_path):
            self.skipTest("recetas_base.json no encontrado. Saltando test.")
        with open(json_path, 'r', encoding='utf-8') as f:
            recetas_json = json.load(f)
        importadas = 0
        for nombre, datos in recetas_json.items():
            receta_adaptada = {
                'name': nombre, 'volume': datos.get('agua_vol', 20),
                'fg_estimated': datos.get('fg_estimada', 1.010), 'efficiency': 0.75, 'notes': '',
                'maltas': datos.get('maltas', []), 'lupulos': datos.get('lupulos', [])
            }
            if self.db.save_recipe(receta_adaptada): importadas += 1
        self.assertEqual(importadas, len(recetas_json))

    def test_receta_marcar_compartida(self):
        receta = {'name': 'Receta Comunidad', 'volume': 20.0, 'efficiency': 0.75,
                  'notes': '', 'maltas': [], 'lupulos': []}
        recipe_id = self.db.save_recipe(receta)
        self.assertEqual(self.db.get_full_recipe(recipe_id).get('compartida'), 0)
        self.db.mark_recipe_compartida(recipe_id)
        self.assertEqual(self.db.get_full_recipe(recipe_id).get('compartida'), 1)

    def test_equipo_extra_params_roundtrip(self):
        self.db.add_equipment('Equipo Test Extra', batch_volume=20)
        self.assertEqual(self.db.get_equipo_extra('Equipo Test Extra'), {})
        self.db.set_equipo_extra('Equipo Test Extra', {'temp_grano': 22.0, 'ph_mash': 5.3})
        extra = self.db.get_equipo_extra('Equipo Test Extra')
        self.assertEqual(extra['temp_grano'], 22.0)
        self.assertEqual(extra['ph_mash'], 5.3)

    def test_inventario_costo_minimo_vencimiento(self):
        self.db.add_inventory_item('Malta', 'Pilsen', 10.0, 'Kg')
        item = self.db.get_inventory_item_by_name('Malta', 'Pilsen')
        self.db.update_inventory_details(item['id'], costo_unitario=1500.0,
                                         minimo=5.0, vencimiento='2026-12-01')
        item = self.db.get_inventory_item_by_name('Malta', 'Pilsen')
        self.assertEqual(item['costo_unitario'], 1500.0)
        self.assertEqual(item['minimo'], 5.0)
        self.assertEqual(item['vencimiento'], '2026-12-01')

    def test_inventario_kardex_registra_movimientos(self):
        self.db.add_inventory_item('Lúpulo', 'Citra', 100.0, 'g', motivo='Compra inicial')
        self.db.subtract_inventory_item('Lúpulo', 'Citra', 30.0, tipo='Salida', motivo='Cocción #1')
        movimientos = self.db.get_inventory_movimientos(limit=5)
        tipos = [m['tipo'] for m in movimientos if m['item_name'] == 'Citra']
        self.assertIn('Entrada', tipos)
        self.assertIn('Salida', tipos)

    def test_inventario_kardex_sobrevive_a_item_borrado(self):
        # Al vaciar el stock el ítem se borra de `inventory`, pero el Kardex
        # debe conservar el historial (no usa FK con ON DELETE CASCADE).
        self.db.add_inventory_item('Lúpulo', 'Mosaic', 20.0, 'g')
        self.db.subtract_inventory_item('Lúpulo', 'Mosaic', 20.0, tipo='Salida', motivo='Consumo total')
        self.assertIsNone(self.db.get_inventory_item_by_name('Lúpulo', 'Mosaic'))
        movimientos = self.db.get_inventory_movimientos(limit=10)
        nombres = [m['item_name'] for m in movimientos]
        self.assertIn('Mosaic', nombres)


class TestBJCP(unittest.TestCase):
    """Tests para el motor de comparación BJCP"""
    def test_estilo_en_rango(self):
        # American IPA: OG 1.056-1.070, IBU 40-70, SRM 5-10
        resultado = comparar_con_estilo("American IPA", 1.060, 1.012, 50, 7)
        # Si todo está en rango, no debe haber ningún ❌
        self.assertNotIn("❌", resultado)
        self.assertIn("✅", resultado)

    def test_estilo_fuera_de_rango(self):
        # American IPA: OG 1.056-1.070. Vamos a pasarle una OG de Stout (1.090)
        resultado = comparar_con_estilo("American IPA", 1.090, 1.012, 50, 7)
        # Debe detectar que la OG está fuera y mostrar ❌
        self.assertIn("❌ OG", resultado)
        # El IBU y SRM deberían estar correctos
        self.assertIn("✅ IBU", resultado)

    def test_lista_estilos_disponible(self):
        lista = get_style_list()
        self.assertIsInstance(lista, list)
        self.assertGreater(len(lista), 80)  # Tenemos +80 estilos
        self.assertEqual(lista[0], "Auto (Sugerir)")  # El primer elemento debe ser Auto


class TestParserPegarProductos(unittest.TestCase):
    """Tests del parser de 'Pegar productos' (Insumos/Inventario, app_gestion.py)."""
    def setUp(self):
        # Catálogo mínimo de matching: {nombre_lower: (tipo, nombre_original)}
        self.catalogo = {
            "cascade argentino": ("Lúpulo", "Cascade Argentino"),
            "mosaic (usa)": ("Lúpulo", "Mosaic (USA)"),
            "pale ale (ba-malt)": ("Malta", "Pale Ale (Ba-Malt)"),
        }

    def test_formato_combinado_nombre_cantidad_unidad(self):
        productos = parsear_texto_productos("Pale Ale (Ba-Malt) 25 kg", self.catalogo)
        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['tipo'], 'Malta')
        self.assertEqual(p['nombre'], 'Pale Ale (Ba-Malt)')
        self.assertEqual(p['cantidad'], 25.0)
        self.assertEqual(p['unidad'], 'Kg')

    def test_formato_csv_con_unidad_en_columna_separada(self):
        # Regresión: cantidad y unidad en columnas separadas (factura/planilla)
        productos = parsear_texto_productos("Mosaic;200;g", self.catalogo)
        self.assertEqual(len(productos), 1)
        p = productos[0]
        self.assertEqual(p['tipo'], 'Lúpulo')
        self.assertEqual(p['nombre'], 'Mosaic (USA)')
        self.assertEqual(p['cantidad'], 200.0)
        self.assertEqual(p['unidad'], 'g')

    def test_sin_match_en_catalogo_tipo_otro(self):
        productos = parsear_texto_productos("Ingrediente Desconocido XYZ 3 kg", self.catalogo)
        self.assertEqual(productos[0]['tipo'], 'Otro')

    def test_multiples_lineas(self):
        texto = "Pale Ale (Ba-Malt) 25 kg\nCascade Argentino 500g\n"
        productos = parsear_texto_productos(texto, self.catalogo)
        self.assertEqual(len(productos), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
