# test_cervecera.py
# /home/saintwick/Escritorio/beer_vgb/test_cervecera.py
# 2024-05-17
# Autor: SaintWick

"""
Suite de tests integrados para Cervecera VGB.
Incluye tests de Motor, BD (CRUD e Inventario) y Comparador BJCP.
Para ejecutar: python -m unittest test_cervecera.py -v
"""

import unittest
import os
import json
from brew_engine import BrewEngine
from database import DatabaseManager
from bjcp_styles import comparar_con_estilo, get_style_list

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
        self.assertEqual(len(receta_db['maltas']), 0) # Borramos maltas
        self.assertEqual(len(receta_db['lupulos']), 1) # Añadimos 1 lúpulo

    def test_eliminar_receta(self):
        receta = {'name': 'A Borrar', 'volume': 10.0, 'efficiency': 0.70, 'notes': '', 'maltas': [{'nombre': 'Pale', 'cantidad': 2.0, 'extracto': 300}], 'lupulos': []}
        recipe_id = self.db.save_recipe(receta)
        self.assertIsNotNone(recipe_id)

        self.db.delete_recipe(recipe_id)
        receta_db = self.db.get_full_recipe(recipe_id)
        self.assertIsNone(receta_db) # Debe devolver None si se borró

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
        self.assertGreater(len(lista), 80) # Tenemos +80 estilos
        self.assertEqual(lista[0], "Auto (Sugerir)") # El primer elemento debe ser Auto

if __name__ == '__main__':
    unittest.main(verbosity=2)
