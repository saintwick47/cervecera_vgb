# logger.py
import logging
import sys
import platform
import os

def _get_log_dir():
    """Obtiene el directorio de datos persistente (compatible con Flet Mobile/Android)."""
    d = os.getenv("FLET_APP_STORAGE_DATA") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(d, exist_ok=True)
    return d

# ── CONFIGURACIÓN DE LOGGING MEJORADA ──────────────────────────────────────
# 1. Formato detallado para el ARCHIVO
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 2. Formato limpio para la CONSOLA
console_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)

# Crear el logger específico de la app
logger = logging.getLogger("CerveceraVGB_Mobile")
logger.setLevel(logging.DEBUG)

# 3. Handler para Archivo (Guarda en carpeta con permisos de escritura)
log_file_path = os.path.join(_get_log_dir(), "cervecera_debug.log")
file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)

# 4. Handler para Consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)

# Añadir handlers al logger
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# ── INICIALIZACIÓN ────────────────────────────────────────────────────────
logger.info("=" * 50)
logger.info("🍺 Logger inicializado - Cervecera VGB Mobile")
logger.info(f"Sistema Operativo: {platform.system()} {platform.release()}")
logger.info(f"Versión de Python: {sys.version.split()[0]}")
logger.info(f"Arquitectura: {platform.machine()}")
logger.info(f"📝 Ruta de Logs: {log_file_path}")
logger.info("=" * 50)
