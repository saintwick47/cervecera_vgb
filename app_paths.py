# app_paths.py
# Ruta de datos PERSISTENTE Y ESCRIBIBLE para la app (Windows / Linux / macOS).
# FIX: Al instalar en "C:\Program Files\..." (o montar AppImage/DMG) la carpeta de
# la app NO es escribible → se guarda en una carpeta del usuario.

import os
import sys


def get_data_dir():
    """
    Devuelve (y crea) el directorio donde guardar la BD y los logs.

    Prioridad:
      1) Variable de entorno CERVECERA_VGB_DATA o FLET_APP_STORAGE_DATA.
      2) App "empaquetada" (PyInstaller .exe / AppImage / .app):
           - Windows : %LOCALAPPDATA%\\CerveceraVGB
           - macOS   : ~/Library/Application Support/CerveceraVGB
           - Linux   : $XDG_DATA_HOME o ~/.local/share/CerveceraVGB
      3) En desarrollo (no empaquetada): ./data junto al script.
    """
    for env in ("CERVECERA_VGB_DATA", "FLET_APP_STORAGE_DATA"):
        v = os.getenv(env)
        if v:
            os.makedirs(v, exist_ok=True)
            return v

    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
            data_dir = os.path.join(base, "CerveceraVGB")
        elif sys.platform == "darwin":
            data_dir = os.path.join(os.path.expanduser("~/Library/Application Support"),
                                    "CerveceraVGB")
        else:
            xdg = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
            data_dir = os.path.join(xdg, "CerveceraVGB")
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    os.makedirs(data_dir, exist_ok=True)
    return data_dir
