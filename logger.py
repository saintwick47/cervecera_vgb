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

# 3. Handler para Archivo: histórico con ROTACIÓN (no crece sin límite).
#    con VGB_TEST=1 (lo usan las pruebas) NO se escribe al log del usuario.
log_file_path = os.path.join(_get_log_dir(), "cervecera_debug.log")
EN_PRUEBAS = os.environ.get("VGB_TEST") == "1"
if EN_PRUEBAS:
    print("[logger] modo prueba: no se escribe el log en disco (VGB_TEST=1)")
else:
    try:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(log_file_path, mode='a', maxBytes=1_000_000,
                                           backupCount=3, encoding='utf-8')
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
def _version_app():
    """Versión de la app, sin importar app_gestion (evita dependencias circulares)."""
    try:
        import re
        fuente = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "app_gestion.py"), encoding="utf-8").read()
        encontrado = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', fuente)
        return encontrado.group(1) if encontrado else "?"
    except Exception:
        return "?"


logger.info("=" * 64)
logger.info(f"🍺 Cervecera VGB v{_version_app()} — inicio de sesión")
logger.info(f"Sistema: {platform.system()} {platform.release()} · Python {sys.version.split()[0]}"
            f" · {platform.machine()}")
logger.info(f"Log: {log_file_path}" + ("  (solo consola: VGB_TEST)" if EN_PRUEBAS else ""))
logger.info("=" * 64)
