# database.py
# /home/saintwick/Escritorio/beer_vgb/database.py
# 2024-05-17 (Actualizado v3)
# Autor: SaintWick
"""
Gestor de Base de Datos SQLite relacional y portátil.
Guarda todo en una carpeta local './data/' para garantizar la portabilidad.
Incluye CRUD completo, Sistema de Inventario, Levaduras y Migraciones.

v3 FIX: Acepta data_dir inyectable para compatibilidad con Flet mobile (Android).
"""
import sqlite3
import os
import sys
from logger import logger
from app_paths import get_data_dir

class DatabaseManager:
    def __init__(self, db_name="cervecera_vgb.db", data_dir=None):
        # FIX CRÍTICO (WinError 5): si no se pasa data_dir, usar una carpeta del
        # USUARIO y escribible (nunca Program Files ni la carpeta de la app).
        # Si se pasa data_dir (desde Flet mobile), usarlo directamente.
        if data_dir:
            self.data_dir = data_dir
        else:
            self.data_dir = get_data_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.db_path = os.path.join(self.data_dir, db_name)
        self.conn = None
        self.connect()
        self.init_database()

    def connect(self):
        """Establece conexión persistente con la BD y activa Foreign Keys"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def init_database(self):
        """Crea las tablas si no existen y aplica migraciones"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                style TEXT DEFAULT '',
                volume REAL NOT NULL,
                efficiency REAL DEFAULT 0.75,
                og_estimated REAL,
                fg_estimated REAL,
                ibu_estimated REAL,
                srm_estimated REAL,
                notes TEXT
            )
        ''')
        cursor.execute("PRAGMA table_info(recipes)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'style' not in columns:
            cursor.execute("ALTER TABLE recipes ADD COLUMN style TEXT DEFAULT ''")
        for col, definition in [
            ('agua_ca',        'REAL DEFAULT 50'),
            ('agua_mg',        'REAL DEFAULT 10'),
            ('agua_hco3',      'REAL DEFAULT 150'),
            ('agua_ph_entrada','REAL DEFAULT NULL'),
            ('tiempo_hervor',  'REAL DEFAULT 60'),
            ('ratio_maceracion','REAL DEFAULT 3.0'),
            ('absorcion',      'REAL DEFAULT 1.0'),
            ('altitud_name',   "TEXT DEFAULT 'Córdoba Capital'"),
        ]:
            if col not in columns:
                try:
                    cursor.execute(f"ALTER TABLE recipes ADD COLUMN {col} {definition}")
                except sqlite3.OperationalError:
                    pass
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_fermentables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                extract REAL DEFAULT 300,
                color REAL DEFAULT 2,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_hops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                alpha_acids REAL NOT NULL,
                time REAL NOT NULL,
                formato TEXT DEFAULT 'pellet',
                FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute("PRAGMA table_info(recipe_hops)")
        hop_cols = [col[1] for col in cursor.fetchall()]
        if 'formato' not in hop_cols:
            try:
                cursor.execute("ALTER TABLE recipe_hops ADD COLUMN formato TEXT DEFAULT 'pellet'")
            except sqlite3.OperationalError:
                pass
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recipe_yeasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recipe_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                attenuation REAL DEFAULT 75.0,
                tolerance_abv REAL DEFAULT 12.0,
                FOREIGN KEY (recipe_id) REFERENCES recipes (id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                unit TEXT NOT NULL,
                UNIQUE(type, name)
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fermentables_recipe ON recipe_fermentables(recipe_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hops_recipe ON recipe_hops(recipe_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_yeasts_recipe ON recipe_yeasts(recipe_id)")
        self.conn.commit()

    # ==========================================
    # MÉTODOS DE RECETAS
    # ==========================================
    def save_recipe(self, recipe_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO recipes (name, style, volume, efficiency, og_estimated, fg_estimated,
                    ibu_estimated, srm_estimated, notes, agua_ca, agua_mg, agua_hco3,
                    agua_ph_entrada, tiempo_hervor, ratio_maceracion, absorcion, altitud_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_data['name'], recipe_data.get('style', ''), recipe_data['volume'],
                recipe_data.get('efficiency', 0.75),
                recipe_data.get('og_estimated'), recipe_data.get('fg_estimated'),
                recipe_data.get('ibu_estimated'), recipe_data.get('srm_estimated'),
                recipe_data.get('notes', ''),
                recipe_data.get('agua_ca', 50), recipe_data.get('agua_mg', 10),
                recipe_data.get('agua_hco3', 150), recipe_data.get('agua_ph_entrada'),
                recipe_data.get('tiempo_hervor', 60),
                recipe_data.get('ratio_maceracion', 3.0),
                recipe_data.get('absorcion', 1.0),
                recipe_data.get('altitud_name', 'Córdoba Capital'),
            ))
            recipe_id = cursor.lastrowid
            for malt in recipe_data.get('maltas', []):
                cursor.execute('INSERT INTO recipe_fermentables (recipe_id, name, amount, extract, color) VALUES (?, ?, ?, ?, ?)',
                (recipe_id, malt['nombre'], malt['cantidad'], malt.get('extracto', 300), malt.get('color', 2)))
            for hop in recipe_data.get('lupulos', []):
                cursor.execute('INSERT INTO recipe_hops (recipe_id, name, amount, alpha_acids, time, formato) VALUES (?, ?, ?, ?, ?, ?)',
                (recipe_id, hop['nombre'], hop['cantidad'], hop.get('aa', 5), hop.get('tiempo', 60), hop.get('formato', 'pellet')))
            for yeast in recipe_data.get('levaduras', []):
                cursor.execute('INSERT INTO recipe_yeasts (recipe_id, name, attenuation, tolerance_abv) VALUES (?, ?, ?, ?)',
                (recipe_id, yeast['nombre'], yeast.get('atenuacion', 75), yeast.get('tolerancia', 12)))
            self.conn.commit()
            return recipe_id
        except sqlite3.IntegrityError as e:
            logger.warning(f"IntegrityError guardando receta: {e}")
            return None
        except Exception as e:
            logger.error(f"Error guardando receta: {e}")
            return None

    def update_recipe(self, recipe_id, recipe_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''UPDATE recipes SET name=?, style=?, volume=?, efficiency=?,
                og_estimated=?, fg_estimated=?, ibu_estimated=?, srm_estimated=?, notes=?,
                agua_ca=?, agua_mg=?, agua_hco3=?, agua_ph_entrada=?, tiempo_hervor=?,
                ratio_maceracion=?, absorcion=?, altitud_name=?
                WHERE id=?''',
            (recipe_data['name'], recipe_data.get('style', ''), recipe_data['volume'],
             recipe_data.get('efficiency', 0.75), recipe_data.get('og_estimated'),
             recipe_data.get('fg_estimated'), recipe_data.get('ibu_estimated'),
             recipe_data.get('srm_estimated'), recipe_data.get('notes', ''),
             recipe_data.get('agua_ca', 50), recipe_data.get('agua_mg', 10),
             recipe_data.get('agua_hco3', 150), recipe_data.get('agua_ph_entrada'),
             recipe_data.get('tiempo_hervor', 60),
             recipe_data.get('ratio_maceracion', 3.0),
             recipe_data.get('absorcion', 1.0),
             recipe_data.get('altitud_name', 'Córdoba Capital'), recipe_id))
            cursor.execute("DELETE FROM recipe_fermentables WHERE recipe_id=?", (recipe_id,))
            cursor.execute("DELETE FROM recipe_hops WHERE recipe_id=?", (recipe_id,))
            cursor.execute("DELETE FROM recipe_yeasts WHERE recipe_id=?", (recipe_id,))
            for malt in recipe_data.get('maltas', []):
                cursor.execute('INSERT INTO recipe_fermentables (recipe_id, name, amount, extract, color) VALUES (?, ?, ?, ?, ?)',
                (recipe_id, malt['nombre'], malt['cantidad'], malt.get('extracto', 300), malt.get('color', 2)))
            for hop in recipe_data.get('lupulos', []):
                cursor.execute('INSERT INTO recipe_hops (recipe_id, name, amount, alpha_acids, time, formato) VALUES (?, ?, ?, ?, ?, ?)',
                (recipe_id, hop['nombre'], hop['cantidad'], hop.get('aa', 5), hop.get('tiempo', 60), hop.get('formato', 'pellet')))
            for yeast in recipe_data.get('levaduras', []):
                cursor.execute('INSERT INTO recipe_yeasts (recipe_id, name, attenuation, tolerance_abv) VALUES (?, ?, ?, ?)',
                (recipe_id, yeast['nombre'], yeast.get('atenuacion', 75), yeast.get('tolerancia', 12)))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            logger.error(f"Error actualizando receta: {e}")
            return False

    def delete_recipe(self, recipe_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM recipes WHERE id=?", (recipe_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error eliminando receta: {e}")

    def get_all_recipes_summary(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, volume FROM recipes ORDER BY name")
        return cursor.fetchall()

    def get_full_recipe(self, recipe_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        recipe_row = cursor.fetchone()
        if not recipe_row: return None
        recipe = dict(recipe_row)
        cursor.execute("SELECT * FROM recipe_fermentables WHERE recipe_id = ?", (recipe_id,))
        recipe['maltas'] = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM recipe_hops WHERE recipe_id = ?", (recipe_id,))
        recipe['lupulos'] = [dict(row) for row in cursor.fetchall()]
        cursor.execute("SELECT * FROM recipe_yeasts WHERE recipe_id = ?", (recipe_id,))
        recipe['levaduras'] = [dict(row) for row in cursor.fetchall()]
        return recipe

    # ==========================================
    # MÉTODOS DE INVENTARIO
    # ==========================================
    def add_inventory_item(self, item_type, name, amount, unit):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT INTO inventory (type, name, amount, unit) VALUES (?, ?, ?, ?)''',
                           (item_type, name, amount, unit))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            cursor.execute('''UPDATE inventory SET amount = amount + ? WHERE type=? AND name=?''',
                           (amount, item_type, name))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error añadiendo inventario: {e}")
            return False

    def subtract_inventory_item(self, item_type, name, amount):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT amount FROM inventory WHERE type=? AND LOWER(name)=?", (item_type, name.lower()))
            row = cursor.fetchone()
            if not row:
                return False
            current_amount = row["amount"]
            new_amount = current_amount - amount
            if new_amount <= 0:
                cursor.execute("DELETE FROM inventory WHERE type=? AND LOWER(name)=?", (item_type, name.lower()))
            else:
                cursor.execute("UPDATE inventory SET amount = ? WHERE type=? AND LOWER(name)=?",
                               (new_amount, item_type, name.lower()))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error restando inventario: {e}")
            return False

    def delete_inventory_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        self.conn.commit()

    def get_all_inventory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory ORDER BY type, name")
        return cursor.fetchall()

    def get_inventory_item_by_name(self, item_type, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE type=? AND LOWER(name)=?", (item_type, name.lower()))
        return cursor.fetchone()

    def close(self):
        if self.conn:
            self.conn.close()
