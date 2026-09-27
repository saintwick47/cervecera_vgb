# database.py
# 2024-05-17 (Actualizado v4)
# Autor: SaintWick
"""
Gestor de Base de Datos SQLite relacional y portátil.
Guarda todo en una carpeta local './data/' para garantizar la portabilidad.
Incluye CRUD completo, Sistema de Inventario, Levaduras y Migraciones.
v3 FIX: Acepta data_dir inyectable para compatibilidad con Flet mobile (Android).
v4 FIX: Silencia IntegrityError en save_recipe (logger.debug) — los duplicados
        son comportamiento esperado al re-sembrar el catálogo o importar recetas.
"""
import sqlite3
import json
import os
import sys
from logger import logger
from app_paths import get_data_dir


# Marcador para "vaciar este campo" en los updates: None significa "no tocar".
VACIO = object()


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
            ('agua_so4',       'REAL DEFAULT 0'),
            ('agua_cl',        'REAL DEFAULT 0'),
            ('agua_objetivo',  "TEXT DEFAULT ''"),
            ('equipo',         "TEXT DEFAULT ''"),
            ('tiempo_hervor',  'REAL DEFAULT 60'),
            ('ratio_maceracion','REAL DEFAULT 3.0'),
            ('absorcion',      'REAL DEFAULT 1.0'),
            ('altitud_name',   "TEXT DEFAULT 'Córdoba Capital'"),
            ('compartida',     'INTEGER DEFAULT 0'),
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
        if 'momento' not in hop_cols:
            try:
                cursor.execute("ALTER TABLE recipe_hops ADD COLUMN momento TEXT DEFAULT 'Hervor'")
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
        cursor.execute("PRAGMA table_info(inventory)")
        inv_columns = [col[1] for col in cursor.fetchall()]
        for col, definition in [('costo_unitario', 'REAL DEFAULT 0'),
                                ('minimo',         'REAL DEFAULT 0'),
                                ('vencimiento',    "TEXT DEFAULT ''"),
                                ('ubicacion',      "TEXT DEFAULT ''"),
                                ('lote',           "TEXT DEFAULT ''")]:
            if col not in inv_columns:
                cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col} {definition}")
        # Kardex de movimientos de inventario (entradas/salidas/mermas/ajustes).
        # Se denormaliza nombre/tipo del insumo para que el historial sobreviva
        # aunque el ítem se borre o se agote del todo.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                receta_id INTEGER,
                receta_nombre TEXT DEFAULT '',
                fecha_coccion TEXT DEFAULT '',
                volumen REAL DEFAULT 0,
                equipo TEXT DEFAULT '',
                estado TEXT DEFAULT 'planificada',
                notas TEXT DEFAULT '',
                creado TEXT DEFAULT (datetime('now','localtime'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lote_insumos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lote_id INTEGER NOT NULL,
                tipo TEXT DEFAULT '',
                nombre TEXT NOT NULL,
                cantidad REAL DEFAULT 0,
                unidad TEXT DEFAULT '',
                disponible REAL DEFAULT 0,
                reservado INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                item_name TEXT NOT NULL,
                item_type TEXT NOT NULL,
                fecha TEXT NOT NULL,
                tipo TEXT NOT NULL,
                cantidad REAL NOT NULL,
                motivo TEXT DEFAULT ''
            )
        ''')
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON inventory_movimientos(id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fermentables_recipe ON recipe_fermentables(recipe_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hops_recipe ON recipe_hops(recipe_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_yeasts_recipe ON recipe_yeasts(recipe_id)")
        # Preferencias globales (fórmulas de cálculo — como Brewfather Settings > Formulas)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        # Perfiles de EQUIPO (Fase 4)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                batch_volume REAL DEFAULT 20,
                kettle_volume REAL DEFAULT 30,
                perdidas_l REAL DEFAULT 2,
                evaporacion_l_h REAL DEFAULT 2,
                eficiencia REAL DEFAULT 0.75,
                temp_macerado REAL DEFAULT 66,
                notas TEXT DEFAULT ''
            )
        ''')
        cursor.execute("PRAGMA table_info(equipment)")
        eq_columns = [col[1] for col in cursor.fetchall()]
        if 'extra_params' not in eq_columns:
            cursor.execute("ALTER TABLE equipment ADD COLUMN extra_params TEXT DEFAULT '{}'")
        # Catálogo de INSUMOS editable (Fase 2): maltas, lúpulos y levaduras
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,             -- 'Malta' | 'Lúpulo' | 'Levadura'
                name TEXT NOT NULL,
                origin TEXT DEFAULT '',
                supplier TEXT DEFAULT '',
                category TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                color REAL DEFAULT 0,           -- color (Lovi) / EBC informativo
                extract REAL DEFAULT 0,         -- extracto (puntos, base 300)
                ppg REAL DEFAULT 0,
                yield_pct REAL DEFAULT 0,
                diastatic REAL DEFAULT 0,
                alpha REAL DEFAULT 0,           -- %AA (lúpulo)
                form TEXT DEFAULT '',           -- pellet / flor (lúpulo)
                attenuation REAL DEFAULT 0,     -- % atenuación (levadura)
                abv_tolerance REAL DEFAULT 0,   -- tolerancia ABV (levadura)
                temp_range TEXT DEFAULT '',
                uso TEXT DEFAULT '',            -- Macerado / Hervido / Ajuste de agua…
                pct_max REAL DEFAULT 0,         -- % máximo recomendado en la receta
                dbfg REAL DEFAULT 0,            -- extracto fino base (Base Fina, %)
                humedad REAL DEFAULT 0,         -- humedad (%)
                proteina REAL DEFAULT 0,        -- proteína total (%)
                maceracion TEXT DEFAULT '',     -- Monoinfusión / Escalonada / Decocción
                UNIQUE(type, name)
            )
        ''')
        self.conn.commit()
        self._migrar_columnas_faltantes()

    # ==========================================
    # MÉTODOS DE RECETAS
    # ==========================================
    # ==========================================
    # MIGRACIONES DEL ESQUEMA
    # ==========================================
    def _migrar_columnas_faltantes(self):
        """Agrega a las tablas que YA EXISTEN las columnas nuevas del esquema.

        `CREATE TABLE IF NOT EXISTS` no toca una tabla que ya está creada, así que
        una base de datos vieja se quedaba sin las columnas nuevas y guardar
        fallaba (p. ej. "table ingredients has no column named uso").
        Las definiciones se leen del propio archivo: una sola fuente de verdad.
        """
        import re
        try:
            with open(__file__, encoding="utf-8") as f:
                fuente = f.read()
        except OSError:
            return
        fin_sql = "'''"
        patron = r"CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\)\s*" + fin_sql
        bloques = re.findall(patron, fuente, re.S)
        cursor = self.conn.cursor()
        agregadas = []
        for tabla, definicion in bloques:
            cursor.execute(f"PRAGMA table_info({tabla})")
            existentes = {fila[1] for fila in cursor.fetchall()}
            if not existentes:
                continue            # la tabla no existe: la crea el CREATE TABLE
            for linea in definicion.splitlines():
                limpia = linea.split("--")[0].strip().rstrip(",")
                if not limpia:
                    continue
                if limpia.upper().startswith(("PRIMARY KEY", "FOREIGN KEY",
                                              "UNIQUE", "CHECK", "CONSTRAINT")):
                    continue
                columna = limpia.split()[0]
                if columna in existentes:
                    continue
                try:
                    cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {limpia}")
                    agregadas.append(f"{tabla}.{columna}")
                except Exception as e:
                    logger.error(f"No se pudo agregar {tabla}.{columna}: {e}")
        if agregadas:
            self.conn.commit()
            logger.info(f"Migración de esquema: {len(agregadas)} columnas agregadas -> "
                        f"{', '.join(agregadas)}")

    def refrescar_catalogo_insumos(self, maltas, lupulos, levaduras, miscelaneos=None):
        """Completa el catálogo en instalaciones que ya existen.

        - Agrega los insumos que falten (el catálogo creció).
        - Rellena los datos técnicos que estén VACÍOS (productor, categoría, uso,
          % máx, PPG…): lo que ahora muestran los filtros del catálogo.
        - **Nunca** pisa un valor que el usuario haya cargado ni borra insumos.
        Devuelve (agregados, completados).
        """
        existentes = {(i["type"], i["name"].strip().lower()): i for i in self.get_ingredients()}

        def comunes(d):
            return {"origin": d.get("origen", ""), "supplier": d.get("supplier", ""),
                    "category": d.get("categoria", ""), "notes": d.get("notes", ""),
                    "uso": d.get("uso", ""), "pct_max": d.get("pct_max", 0)}

        por_tipo = [
            ("Malta", maltas, lambda d: {"extract": d.get("extracto", 300), "color": d.get("color", 2),
                                         "ppg": d.get("ppg", 0), "diastatic": d.get("diastatic", 0)}),
            ("Lúpulo", lupulos, lambda d: {"alpha": d.get("aa", 5), "form": d.get("formato", "pellet")}),
            ("Levadura", levaduras, lambda d: {"attenuation": d.get("atenuacion", 75),
                                               "abv_tolerance": d.get("tolerancia_abv", 12),
                                               "temp_range": d.get("temp_range", ""),
                                               "form": d.get("formato", "seca")}),
            ("Misceláneo", miscelaneos, lambda d: {}),
        ]
        agregados = completados = 0
        for tipo, coleccion, extra in por_tipo:
            for nombre, d in (coleccion or {}).items():
                campos = dict(extra(d)); campos.update(comunes(d))
                actual = existentes.get((tipo, nombre.strip().lower()))
                if not actual:
                    self.add_ingredient(tipo, nombre, **campos)
                    agregados += 1
                    continue
                # completar SOLO lo que está vacío
                faltantes = {}
                for clave, valor in campos.items():
                    if valor in (None, "", 0):
                        continue
                    guardado = actual.get(clave)
                    if guardado in (None, "", 0):
                        faltantes[clave] = valor
                if faltantes:
                    self.update_ingredient(tipo, actual["name"], **faltantes)
                    completados += 1
        return agregados, completados

    def contar_recetas_por_insumo(self):
        """{nombre en minúsculas: nº de recetas que lo usan} — columna "Recetas" del catálogo."""
        cursor = self.conn.cursor()
        conteo = {}
        for tabla in ("recipe_fermentables", "recipe_hops", "recipe_yeasts"):
            try:
                cursor.execute(f"SELECT LOWER(name), COUNT(DISTINCT recipe_id) "
                               f"FROM {tabla} GROUP BY LOWER(name)")
                for nombre, n in cursor.fetchall():
                    if nombre:
                        conteo[nombre] = conteo.get(nombre, 0) + n
            except Exception as e:
                logger.error(f"contar_recetas_por_insumo ({tabla}): {e}")
        return conteo

    # ==========================================
    # COCCIONES PROGRAMADAS (lotes) — del diseño de Stitch
    # Al planificar un lote se RESERVAN sus insumos y se avisa lo que falta.
    # ==========================================
    def necesidades_de_receta(self, receta_id):
        """Insumos que pide una receta: [{tipo, nombre, cantidad, unidad}]."""
        receta = self.get_full_recipe(receta_id)
        if not receta:
            return []
        necesidades = []
        for m in receta.get("maltas", []):
            necesidades.append({"tipo": "Malta", "nombre": m["name"],
                                "cantidad": float(m.get("amount") or 0), "unidad": "kg"})
        for h in receta.get("lupulos", []):
            necesidades.append({"tipo": "Lúpulo", "nombre": h["name"],
                                "cantidad": float(h.get("amount") or 0), "unidad": "g"})
        for y in receta.get("levaduras", []):
            necesidades.append({"tipo": "Levadura", "nombre": y["name"],
                                "cantidad": 1.0, "unidad": "u"})
        return necesidades

    def _stock_de(self, tipo, nombre):
        """Stock disponible para un insumo de la receta.

        Primero busca el nombre exacto; si no está, busca por parecido (los nombres
        de la receta y del inventario no siempre coinciden).
        """
        items = [i for i in self.get_all_inventory() if i["type"] == tipo]
        buscado = (nombre or "").strip().lower()
        for it in items:
            if it["name"].strip().lower() == buscado:
                return it
        for it in items:                       # por parecido
            guardado = it["name"].strip().lower()
            if buscado and (buscado in guardado or guardado in buscado):
                return it
        return None

    def _reservado_por_otros(self, tipo, nombre, excluir_lote=None):
        """Cantidad ya comprometida por otros lotes planificados."""
        cursor = self.conn.cursor()
        cursor.execute("""SELECT COALESCE(SUM(li.cantidad), 0) FROM lote_insumos li
                          JOIN lotes l ON l.id = li.lote_id
                          WHERE l.estado = 'planificada' AND li.tipo = ?
                            AND LOWER(li.nombre) = LOWER(?) AND li.lote_id != ?""",
                       (tipo, nombre, excluir_lote or -1))
        return float(cursor.fetchone()[0] or 0)

    def planificar_lote(self, receta_id, fecha_coccion="", volumen=None, equipo="", nombre=None):
        """Programa una cocción y reserva sus insumos. Devuelve el id del lote."""
        receta = self.get_full_recipe(receta_id)
        if not receta:
            return None
        nombre = nombre or f"Lote de {receta['name']}"
        cursor = self.conn.cursor()
        cursor.execute("""INSERT INTO lotes (nombre, receta_id, receta_nombre, fecha_coccion,
                                             volumen, equipo, estado)
                          VALUES (?, ?, ?, ?, ?, ?, 'planificada')""",
                       (nombre, receta_id, receta["name"], fecha_coccion,
                        float(volumen or receta.get("volume") or 0), equipo or ""))
        lote_id = cursor.lastrowid
        for n in self.necesidades_de_receta(receta_id):
            item = self._stock_de(n["tipo"], n["nombre"])
            disponible = float(item["amount"]) if item else 0.0
            disponible -= self._reservado_por_otros(n["tipo"], n["nombre"], lote_id)
            cursor.execute("""INSERT INTO lote_insumos (lote_id, tipo, nombre, cantidad,
                                                        unidad, disponible, reservado)
                              VALUES (?, ?, ?, ?, ?, ?, 1)""",
                           (lote_id, n["tipo"], n["nombre"], n["cantidad"],
                            n["unidad"], max(0.0, disponible)))
        self.conn.commit()
        return lote_id

    def get_lotes(self, estado=None):
        cursor = self.conn.cursor()
        if estado:
            cursor.execute("SELECT * FROM lotes WHERE estado=? ORDER BY fecha_coccion, id", (estado,))
        else:
            cursor.execute("SELECT * FROM lotes ORDER BY fecha_coccion, id")
        return [dict(r) for r in cursor.fetchall()]

    def faltantes_de_lote(self, lote_id):
        """Lo que falta para cocinar: [{nombre, tipo, requerido, disponible}].

        El stock se mira EN VIVO (no el que había al planificar): así, cuando llega
        el pedido y se ingresa, el lote pasa solo a "insumos completos".
        """
        cursor = self.conn.cursor()
        cursor.execute("""SELECT tipo, nombre, cantidad, unidad FROM lote_insumos
                          WHERE lote_id=? ORDER BY tipo, nombre""", (lote_id,))
        faltantes = []
        for tipo, nombre, cantidad, unidad in cursor.fetchall():
            item = self._stock_de(tipo, nombre)
            actual = float(item["amount"]) if item else 0.0
            actual -= self._reservado_por_otros(tipo, nombre, lote_id)
            actual = max(0.0, actual)
            requerido = float(cantidad or 0)
            if actual < requerido:
                faltantes.append({"tipo": tipo, "nombre": nombre, "unidad": unidad,
                                  "requerido": requerido, "disponible": actual,
                                  "faltante": requerido - actual})
        return faltantes

    def lotes_para_rail(self, limite=3):
        """Datos del rail 'Próximas Cocciones Programadas' del diseño."""
        salida = []
        for lote in self.get_lotes("planificada")[:limite]:
            faltantes = self.faltantes_de_lote(lote["id"])
            salida.append({"id": lote["id"], "nombre": lote["nombre"],
                           "volumen": lote["volumen"], "fecha": lote["fecha_coccion"],
                           "estado": lote["estado"], "listo": not faltantes,
                           "faltantes": faltantes})
        return salida

    def update_lote_estado(self, lote_id, estado):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE lotes SET estado=? WHERE id=?", (estado, lote_id))
        self.conn.commit()

    def delete_lote(self, lote_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM lote_insumos WHERE lote_id=?", (lote_id,))
        cursor.execute("DELETE FROM lotes WHERE id=?", (lote_id,))
        self.conn.commit()

    def distribucion_almacenamiento(self):
        """Ocupación por categoría (tarjeta 'Distribución de Espacio de Acopio')."""
        totales = {}
        for it in self.get_all_inventory():
            clave = it["type"]
            unidad = it["unit"] or "u"
            acumulado = totales.setdefault(clave, {})
            acumulado[unidad] = acumulado.get(unidad, 0.0) + float(it["amount"] or 0)
        return totales

    def ajustar_inventario(self, item_id, cantidad_contada, motivo="Ajuste físico"):
        """Ajuste físico: deja el stock en la cantidad contada y lo registra en el Kardex.

        Devuelve la diferencia aplicada (positiva si sobraba, negativa si faltaba).
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, type, amount, unit FROM inventory WHERE id=?", (item_id,))
        fila = cursor.fetchone()
        if not fila:
            return None
        nombre, tipo, actual, unidad = fila[0], fila[1], float(fila[2] or 0), fila[3]
        contada = float(cantidad_contada)
        diferencia = contada - actual
        cursor.execute("UPDATE inventory SET amount=? WHERE id=?", (contada, item_id))
        cursor.execute("""INSERT INTO inventory_movimientos
                          (item_id, item_name, item_type, fecha, tipo, cantidad, motivo)
                          VALUES (?, ?, ?, datetime('now','localtime'), 'Ajuste', ?, ?)""",
                       (item_id, nombre, tipo, diferencia, motivo))
        self.conn.commit()
        return diferencia

    def save_recipe(self, recipe_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO recipes (name, style, volume, efficiency, og_estimated, fg_estimated,
                    ibu_estimated, srm_estimated, notes, agua_ca, agua_mg, agua_hco3,
                    agua_ph_entrada, agua_so4, agua_cl, agua_objetivo, equipo,
                    tiempo_hervor, ratio_maceracion, absorcion, altitud_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                recipe_data['name'], recipe_data.get('style', ''), recipe_data['volume'],
                recipe_data.get('efficiency', 0.75),
                recipe_data.get('og_estimated'), recipe_data.get('fg_estimated'),
                recipe_data.get('ibu_estimated'), recipe_data.get('srm_estimated'),
                recipe_data.get('notes', ''),
                recipe_data.get('agua_ca', 50), recipe_data.get('agua_mg', 10),
                recipe_data.get('agua_hco3', 150), recipe_data.get('agua_ph_entrada'),
                recipe_data.get('agua_so4', 0), recipe_data.get('agua_cl', 0),
                recipe_data.get('agua_objetivo', ''), recipe_data.get('equipo', ''),
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
                cursor.execute('INSERT INTO recipe_hops (recipe_id, name, amount, alpha_acids, time, formato, momento) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (recipe_id, hop['nombre'], hop['cantidad'], hop.get('aa', 5), hop.get('tiempo', 60),
                 hop.get('formato', 'pellet'), hop.get('momento', 'Hervor')))
            for yeast in recipe_data.get('levaduras', []):
                cursor.execute('INSERT INTO recipe_yeasts (recipe_id, name, attenuation, tolerance_abv) VALUES (?, ?, ?, ?)',
                (recipe_id, yeast['nombre'], yeast.get('atenuacion', 75), yeast.get('tolerancia', 12)))
            self.conn.commit()
            return recipe_id
        except sqlite3.IntegrityError as e:
            # v4: silencio — los duplicados son comportamiento esperado
            # (re-sembrado del catálogo, re-importación del mismo JSON, etc.)
            logger.debug(f"Receta duplicada (no guardada): {recipe_data.get('name', '?')}")
            return None
        except Exception as e:
            logger.error(f"Error guardando receta: {e}")
            return None

    def update_recipe(self, recipe_id, recipe_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''UPDATE recipes SET name=?, style=?, volume=?, efficiency=?,
                og_estimated=?, fg_estimated=?, ibu_estimated=?, srm_estimated=?, notes=?,
                agua_ca=?, agua_mg=?, agua_hco3=?, agua_ph_entrada=?, agua_so4=?, agua_cl=?, agua_objetivo=?, equipo=?, tiempo_hervor=?,
                ratio_maceracion=?, absorcion=?, altitud_name=?
                WHERE id=?''',
            (recipe_data['name'], recipe_data.get('style', ''), recipe_data['volume'],
             recipe_data.get('efficiency', 0.75), recipe_data.get('og_estimated'),
             recipe_data.get('fg_estimated'), recipe_data.get('ibu_estimated'),
             recipe_data.get('srm_estimated'), recipe_data.get('notes', ''),
             recipe_data.get('agua_ca', 50), recipe_data.get('agua_mg', 10),
             recipe_data.get('agua_hco3', 150), recipe_data.get('agua_ph_entrada'),
             recipe_data.get('agua_so4', 0), recipe_data.get('agua_cl', 0),
             recipe_data.get('agua_objetivo', ''), recipe_data.get('equipo', ''),
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
                cursor.execute('INSERT INTO recipe_hops (recipe_id, name, amount, alpha_acids, time, formato, momento) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (recipe_id, hop['nombre'], hop['cantidad'], hop.get('aa', 5), hop.get('tiempo', 60),
                 hop.get('formato', 'pellet'), hop.get('momento', 'Hervor')))
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
        return [dict(r) for r in cursor.fetchall()]

    def recipe_exists(self, name):
        """Devuelve True si ya existe una receta con ese nombre."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM recipes WHERE name = ?", (name,))
        return cursor.fetchone() is not None

    def mark_recipe_compartida(self, recipe_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE recipes SET compartida=1 WHERE id=?", (recipe_id,))
        self.conn.commit()

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
    # PREFERENCIAS (settings) — fórmulas globales
    # ==========================================
    def get_setting(self, key, default=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cursor.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    # ==========================================
    # PERFILES DE EQUIPO (Fase 4)
    # ==========================================
    def get_equipment(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM equipment ORDER BY name")
        return [dict(r) for r in cursor.fetchall()]

    def get_equipment_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM equipment WHERE name=?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def add_equipment(self, name, **campos):
        cursor = self.conn.cursor()
        vals = (name, campos.get("batch_volume", 20), campos.get("kettle_volume", 30),
                campos.get("perdidas_l", 2), campos.get("evaporacion_l_h", 2),
                campos.get("eficiencia", 0.75), campos.get("temp_macerado", 66),
                campos.get("notas", ""))
        try:
            cursor.execute("""INSERT INTO equipment
                (name, batch_volume, kettle_volume, perdidas_l, evaporacion_l_h,
                 eficiencia, temp_macerado, notas) VALUES (?,?,?,?,?,?,?,?)""", vals)
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            cursor.execute("""UPDATE equipment SET batch_volume=?, kettle_volume=?, perdidas_l=?,
                evaporacion_l_h=?, eficiencia=?, temp_macerado=?, notas=? WHERE name=?""",
                (vals[1], vals[2], vals[3], vals[4], vals[5], vals[6], vals[7], name))
            self.conn.commit()
            return True

    def delete_equipment(self, name):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM equipment WHERE name=?", (name,))
        self.conn.commit()

    def get_equipo_extra(self, name):
        """Parámetros extendidos del equipo (maceración, mermas, pH) guardados como JSON."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT extra_params FROM equipment WHERE name=?", (name,))
        row = cursor.fetchone()
        if not row or not row["extra_params"]:
            return {}
        try:
            return json.loads(row["extra_params"])
        except Exception:
            return {}

    def set_equipo_extra(self, name, datos: dict):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE equipment SET extra_params=? WHERE name=?",
                       (json.dumps(datos, ensure_ascii=False), name))
        self.conn.commit()

    def seed_equipment(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM equipment")
        if cursor.fetchone()[0] == 0:
            self.add_equipment("Equipo por defecto (20 L)", batch_volume=20, kettle_volume=30,
                               perdidas_l=2, evaporacion_l_h=2, eficiencia=0.75, temp_macerado=66)

    # ==========================================
    # CATÁLOGO DE INSUMOS (editable) — Fase 2
    # ==========================================
    CAMPOS_INSUMO = ("origin", "supplier", "category", "notes", "color", "extract",
                     "ppg", "yield_pct", "diastatic", "alpha", "form",
                     "attenuation", "abv_tolerance", "temp_range",
                     "uso", "pct_max", "dbfg", "humedad", "proteina", "maceracion")

    def get_ingredients(self, tipo=None):
        """Lista de insumos (dicts), opcionalmente filtrada por tipo."""
        cursor = self.conn.cursor()
        if tipo:
            cursor.execute("SELECT * FROM ingredients WHERE type=? ORDER BY name", (tipo,))
        else:
            cursor.execute("SELECT * FROM ingredients ORDER BY type, name")
        return [dict(r) for r in cursor.fetchall()]

    def get_ingredient(self, tipo, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ingredients WHERE type=? AND name=?", (tipo, name))
        row = cursor.fetchone()
        return dict(row) if row else None

    def ingredient_names(self, tipo):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM ingredients WHERE type=? ORDER BY name", (tipo,))
        return [r["name"] for r in cursor.fetchall()]

    def add_ingredient(self, tipo, name, **campos):
        """Agrega un insumo. Si ya existe (mismo tipo+nombre), lo actualiza."""
        datos = {c: campos.get(c) for c in self.CAMPOS_INSUMO}
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO ingredients (type, name, origin, supplier, category, notes,
                       color, extract, ppg, yield_pct, diastatic, alpha, form,
                       attenuation, abv_tolerance, temp_range, uso, pct_max,
                       dbfg, humedad, proteina, maceracion)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tipo, name, datos["origin"] or "", datos["supplier"] or "",
                 datos["category"] or "", datos["notes"] or "",
                 datos["color"] or 0, datos["extract"] or 0, datos["ppg"] or 0,
                 datos["yield_pct"] or 0, datos["diastatic"] or 0,
                 datos["alpha"] or 0, datos["form"] or "",
                 datos["attenuation"] or 0, datos["abv_tolerance"] or 0,
                 datos["temp_range"] or "", datos["uso"] or "",
                 datos["pct_max"] or 0, datos["dbfg"] or 0,
                 datos["humedad"] or 0, datos["proteina"] or 0,
                 datos["maceracion"] or ""))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return self.update_ingredient(tipo, name, **campos)

    def update_ingredient(self, tipo, name, **campos):
        sets, vals = [], []
        for c in self.CAMPOS_INSUMO:
            if c in campos and campos[c] is not None:
                sets.append(f"{c}=?")
                vals.append(campos[c])
        if not sets:
            return True
        vals += [tipo, name]
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE ingredients SET {', '.join(sets)} WHERE type=? AND name=?", vals)
        self.conn.commit()
        return True

    def delete_ingredient(self, tipo, name):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ingredients WHERE type=? AND name=?", (tipo, name))
        self.conn.commit()

    def seed_ingredients(self, maltas, lupulos, levaduras, miscelaneos=None):
        """Carga el catálogo base en la BD la primera vez (luego es editable).

        Copia la ficha técnica completa (productor, categoría, uso, % máximo…),
        que es lo que muestran los filtros y la tabla del catálogo.
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ingredients")
        if cursor.fetchone()[0] > 0:
            return 0

        def comunes(d):
            return {"origin": d.get("origen", ""), "supplier": d.get("supplier", ""),
                    "category": d.get("categoria", ""), "notes": d.get("notes", ""),
                    "uso": d.get("uso", ""), "pct_max": d.get("pct_max", 0)}

        n = 0
        for nombre, d in (maltas or {}).items():
            self.add_ingredient("Malta", nombre, extract=d.get("extracto", 300),
                                color=d.get("color", 2), ppg=d.get("ppg", 0),
                                diastatic=d.get("diastatic", 0), **comunes(d)); n += 1
        for nombre, d in (lupulos or {}).items():
            self.add_ingredient("Lúpulo", nombre, alpha=d.get("aa", 5),
                                form=d.get("formato", "pellet"), **comunes(d)); n += 1
        for nombre, d in (levaduras or {}).items():
            self.add_ingredient("Levadura", nombre, attenuation=d.get("atenuacion", 75),
                                abv_tolerance=d.get("tolerancia_abv", 12),
                                temp_range=d.get("temp_range", ""),
                                form=d.get("formato", "seca"), **comunes(d)); n += 1
        for nombre, d in (miscelaneos or {}).items():
            self.add_ingredient("Misceláneo", nombre, **comunes(d)); n += 1
        return n

    # ==========================================
    # MÉTODOS DE INVENTARIO
    # ==========================================
    def add_inventory_item(self, item_type, name, amount, unit, motivo="Ingreso"):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''INSERT INTO inventory (type, name, amount, unit) VALUES (?, ?, ?, ?)''',
                           (item_type, name, amount, unit))
            self.conn.commit()
            self.add_inventory_movimiento(cursor.lastrowid, name, item_type, "Entrada", amount, motivo)
            return True
        except sqlite3.IntegrityError:
            cursor.execute('''UPDATE inventory SET amount = amount + ? WHERE type=? AND name=?''',
                           (amount, item_type, name))
            self.conn.commit()
            cursor.execute("SELECT id FROM inventory WHERE type=? AND name=?", (item_type, name))
            row = cursor.fetchone()
            self.add_inventory_movimiento(row["id"] if row else None, name, item_type,
                                          "Entrada", amount, motivo)
            return True
        except Exception as e:
            logger.error(f"Error añadiendo inventario: {e}")
            return False

    def subtract_inventory_item(self, item_type, name, amount, tipo="Salida", motivo=""):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id, amount FROM inventory WHERE type=? AND LOWER(name)=?", (item_type, name.lower()))
            row = cursor.fetchone()
            if not row:
                return False
            item_id, current_amount = row["id"], row["amount"]
            new_amount = current_amount - amount
            if new_amount <= 0:
                cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
            else:
                cursor.execute("UPDATE inventory SET amount = ? WHERE id=?", (new_amount, item_id))
            self.conn.commit()
            self.add_inventory_movimiento(item_id, name, item_type, tipo, amount, motivo)
            return True
        except Exception as e:
            logger.error(f"Error restando inventario: {e}")
            return False

    def update_inventory_details(self, item_id, costo_unitario=None, minimo=None,
                                 vencimiento=None, ubicacion=None, lote=None):
        """Actualiza la ficha del ítem.

        None = no tocar ese campo · VACIO (importado de este módulo) = dejarlo vacío.
        """
        sets, vals = [], []
        for columna, valor in (("costo_unitario", costo_unitario),
                               ("minimo", minimo),
                               ("vencimiento", vencimiento),
                               ("ubicacion", ubicacion),
                               ("lote", lote)):
            if valor is VACIO:
                sets.append(f"{columna}=NULL")
            elif valor is not None:
                sets.append(f"{columna}=?"); vals.append(valor)
        if not sets:
            return
        vals.append(item_id)
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE inventory SET {', '.join(sets)} WHERE id=?", vals)
        self.conn.commit()

    def add_inventory_movimiento(self, item_id, item_name, item_type, tipo, cantidad, motivo=""):
        cursor = self.conn.cursor()
        cursor.execute("""INSERT INTO inventory_movimientos
                           (item_id, item_name, item_type, fecha, tipo, cantidad, motivo)
                           VALUES (?, ?, ?, datetime('now','localtime'), ?, ?, ?)""",
                       (item_id, item_name, item_type, tipo, cantidad, motivo))
        self.conn.commit()

    def get_inventory_movimientos(self, limit=15):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory_movimientos ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in cursor.fetchall()]

    def delete_inventory_item(self, item_id):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM inventory WHERE id=?", (item_id,))
        self.conn.commit()

    def get_all_inventory(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory ORDER BY type, name")
        return [dict(r) for r in cursor.fetchall()]

    def get_inventory_item_by_name(self, item_type, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM inventory WHERE type=? AND LOWER(name)=?", (item_type, name.lower()))
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        if self.conn:
            self.conn.close()
