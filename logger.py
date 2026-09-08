# logger.py
# Logger robusto de Cervecera VGB: captura arranque + errores de uso,
# escribe el historial en la carpeta del usuario y registra las
# excepciones no controladas (sys.excepthook).
import logging
import sys
import platform
import os
import traceback
from app_paths import get_data_dir

def _get_log_dir():
    """Directorio de datos persistente Y ESCRIBIBLE (FIX WinError 5 en Program Files)."""
    return get_data_dir()

# ── CONFIGURACIÓN DE LOGGING MEJORADA ──────────────────────────────────────
file_formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("CerveceraVGB")
logger.setLevel(logging.DEBUG)

# 3. Handler para Archivo: histórico (append) para no perder errores previos
log_file_path = os.path.join(_get_log_dir(), "cervecera_debug.log")
try:
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    # Si no se puede crear el archivo, al menos mantener consola
    print(f"[logger] No se pudo crear el log en {log_file_path}: {e}")

# 4. Handler para Consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)
if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
           for h in logger.handlers):
    logger.addHandler(console_handler)

# 5. Capturar TODAS las excepciones no controladas (crash de uso/arranque)
def _excepthook(exc_type, exc_value, exc_tb):
    try:
        logger.error("⚠️ Excepción NO controlada:", exc_info=(exc_type, exc_value, exc_tb))
    except Exception:
        pass
    traceback.print_exception(exc_type, exc_value, exc_tb)

sys.excepthook = _excepthook

# ── INICIALIZACIÓN ────────────────────────────────────────────────────────
logger.info("=" * 50)
logger.info("🍺 Logger inicializado - Cervecera VGB")
logger.info(f"Sistema Operativo: {platform.system()} {platform.release()}")
logger.info(f"Versión de Python: {sys.version.split()[0]}")
logger.info(f"Arquitectura: {platform.machine()}")
logger.info(f"📝 Ruta de Logs: {log_file_path}")
logger.info("=" * 50)
