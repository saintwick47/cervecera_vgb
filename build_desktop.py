#!/usr/bin/env python3
# build_desktop.py — SCRIPT ÚNICO DE BUILD DE ESCRITORIO (Windows/Linux/macOS) v1
# /home/saintwick/Escritorio/beer_vgb/build_desktop.py
# Autor: SaintWick
#
# Compila el instalador de escritorio para el sistema operativo donde se
# ejecuta y lo publica como asset del release de GitHub que corresponde a
# packaging/VERSION (creándolo si no existe).
#
# ⚠️ PyInstaller NO compila cruzado: este script arma el instalador del SO
# donde corre únicamente. Para tener Windows + Linux + macOS en el mismo
# release hay que ejecutarlo una vez en cada sistema (o seguir usando
# GitHub Actions, que ya hace exactamente eso con runners de cada SO).
#
# Reutiliza tal cual lo que ya está en packaging/ — no reinventa el
# empaquetado, solo lo orquesta y sube el resultado:
#   Windows → packaging/windows/build_windows.ps1 (PyInstaller + Inno Setup)
#   Linux   → packaging/linux/build_linux_{appimage,deb,rpm}.sh
#   macOS   → packaging/macos/build_macos.sh [arm64|intel]
#
# NO toca el APK de Android (ver build_apk.py aparte, script separado).
#
# Pipeline:
#   1) Verificar archivos base del repo
#   2) Leer/fijar la versión (packaging/VERSION) y sincronizar CerveceraVGB.iss
#   3) Verificar herramientas del SO detectado
#   4) Compilar (llama a los scripts de packaging/<so>/)
#   5) Publicar en GitHub Releases: crea el release si hace falta, sube los
#      instaladores nuevos y fusiona checksums.txt con el de otras plataformas
#
# Uso:
#   python build_desktop.py                  # compila y publica (SO actual)
#   python build_desktop.py --skip-upload    # solo compila, no publica
#   python build_desktop.py --skip-build     # solo sube lo que ya haya en dist_installers/
#   python build_desktop.py --arch intel     # macOS: build Intel en vez de arm64
#   python build_desktop.py --version 1.5.0  # fuerza una versión (actualiza packaging/VERSION)
#   python build_desktop.py --verbose|--quiet

import argparse
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── CONFIGURACIÓN BASE ────────────────────────────────────────────────────────
PROJECT_DIR = Path(__file__).parent.resolve()
OWNER, REPO = "saintwick47", "cervecera_vgb"
TOKEN_ENV = ("GITHUB_TOKEN", "GH_TOKEN", "GITHUB_PAT")  # mismos nombres que subir_github.py/comitgit.py
TOKEN_FILE = Path.home() / ".config" / "cervecera_vgb" / "token"  # mismo archivo que ya usan esos scripts

ARCHIVOS_REQUERIDOS = ["app.py", "recetas_base.json", "logo.ico", "logo.png", "packaging/VERSION"]

# ── COLORES ANSI (mismo esquema que build_apk.py) ─────────────────────────────
_OK = "\033[92m✅\033[0m"
_ERR = "\033[91m❌\033[0m"
_INFO = "\033[94mℹ️ \033[0m"
_WARN = "\033[93m⚠️ \033[0m"


def parse_args():
    p = argparse.ArgumentParser(
        description="Cervecera VGB — Build instalador de escritorio (Windows/Linux/macOS) y publicación en GitHub Releases",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--skip-build", action="store_true", help="No compila; sube lo que ya haya en dist_installers/")
    p.add_argument("--skip-upload", action="store_true", help="Compila pero no publica en GitHub")
    p.add_argument("--arch", choices=["arm64", "intel"], default="arm64", help="Solo macOS: arquitectura a compilar")
    p.add_argument("--version", default=None, help="Fuerza una versión exacta (en vez de autoincrementar)")
    p.add_argument("--no-bump", action="store_true",
                   help="No autoincrementa: reusa la versión actual de packaging/VERSION tal cual")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--quiet", action="store_true")
    return p.parse_args()


ARGS = parse_args()

# ── LOGGING ───────────────────────────────────────────────────────────────────
LOG_PATH = PROJECT_DIR / "build_desktop.log"
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8")],
)
_log = logging.getLogger(__name__)


def ok(msg):
    _log.info(f"OK  {msg}")
    if not ARGS.quiet: print(f"{_OK}  {msg}")

def err(msg):
    _log.error(msg)
    print(f"{_ERR}  {msg}")

def info(msg):
    _log.info(msg)
    if not ARGS.quiet: print(f"{_INFO} {msg}")

def warn(msg):
    _log.warning(msg)
    if not ARGS.quiet: print(f"{_WARN} {msg}")

def separador(titulo=""):
    line = "─" * 55
    _log.info(f"── {titulo} ──" if titulo else line)
    if not ARGS.quiet:
        print(f"\n{line}")
        if titulo: print(f"  {titulo}")
        print(line)


# ── HELPERS ───────────────────────────────────────────────────────────────────
def run_sub(cmd, cwd=None):
    capture = not ARGS.verbose
    try:
        r = subprocess.run(cmd, cwd=cwd or PROJECT_DIR, capture_output=capture, text=True)
        if capture:
            if r.stdout: _log.debug(r.stdout)
            if r.stderr: _log.debug(r.stderr)
        return r
    except Exception as e:
        _log.error(f"Excepción en subprocess {cmd!r}: {e}")
        raise


def herramienta(nombre):
    return shutil.which(nombre)


# ── PASO 1 — Entorno y archivos ────────────────────────────────────────────
def verificar_entorno():
    separador("PASO 1 — Verificar entorno y archivos")
    in_venv = (hasattr(sys, "real_prefix")
               or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
               or os.environ.get("VIRTUAL_ENV") is not None)
    if not in_venv:
        err("No se detectó entorno virtual activo.")
        raise SystemExit(1)
    ok("Entorno virtual detectado.")

    faltantes = [f for f in ARCHIVOS_REQUERIDOS if not (PROJECT_DIR / f).exists()]
    if faltantes:
        err(f"Faltantes: {', '.join(faltantes)}")
        raise SystemExit(1)
    ok("Archivos base presentes.")


def detectar_so():
    s = platform.system()
    if s == "Windows": return "windows"
    if s == "Darwin": return "macos"
    if s == "Linux": return "linux"
    raise SystemExit(f"{_ERR}  Sistema operativo no soportado: {s}")


# ── PASO 2 — Versión ────────────────────────────────────────────────────────
def incrementar_parche(version):
    partes = version.split(".")
    if len(partes) != 3 or not all(p.isdigit() for p in partes):
        raise SystemExit(f"{_ERR}  No puedo autoincrementar una versión no-semver: {version!r} "
                         f"(usá --version X.Y.Z para fijarla a mano).")
    mayor, menor, parche = partes
    return f"{mayor}.{menor}.{int(parche) + 1}"


def leer_y_fijar_version():
    separador("PASO 2 — Versión")
    version_path = PROJECT_DIR / "packaging" / "VERSION"
    actual = version_path.read_text(encoding="utf-8").strip()

    if ARGS.version:
        version = ARGS.version.strip()
        origen = "forzada con --version"
    elif ARGS.no_bump:
        version = actual
        origen = "--no-bump: se reusa tal cual"
    else:
        # Cada corrida apunta a una versión NUEVA por defecto — nunca se
        # reutiliza la ya publicada, para no pisar un release existente.
        version = incrementar_parche(actual)
        origen = "autoincrementada"

    if version != actual:
        version_path.write_text(version + "\n", encoding="utf-8")
        info(f"packaging/VERSION: {actual} → {version} ({origen})")
    else:
        info(f"Versión ({origen}): {version}")
    ok(f"Versión: {version}")

    # El instalador de Windows repite la versión a mano dentro del .iss
    # (define el nombre del .exe de salida) — la sincronizamos para que
    # nunca quede desactualizada respecto de packaging/VERSION.
    iss = PROJECT_DIR / "packaging" / "windows" / "CerveceraVGB.iss"
    if iss.exists():
        contenido = iss.read_text(encoding="utf-8")
        nuevo = re.sub(r'#define MyAppVersion "[^"]*"',
                       f'#define MyAppVersion "{version}"', contenido)
        if nuevo != contenido:
            iss.write_text(nuevo, encoding="utf-8")
            ok(f"CerveceraVGB.iss sincronizado a {version}.")
        else:
            ok("CerveceraVGB.iss ya estaba sincronizado.")
    return version


# ── PASO 3 — Herramientas por SO ────────────────────────────────────────────
def verificar_herramientas(so):
    separador("PASO 3 — Verificar herramientas")
    if not herramienta("pyinstaller"):
        r = run_sub([sys.executable, "-c", "import PyInstaller"])
        if r.returncode != 0:
            err("PyInstaller no está instalado (pip install pyinstaller).")
            raise SystemExit(1)
    ok("PyInstaller disponible.")

    formatos = []
    if so == "windows":
        candidatos = [Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")]
        candidatos += list(Path("C:/").glob("Program Files*/Inno Setup*/ISCC.exe"))
        if not any(c.exists() for c in candidatos):
            err("No encontré ISCC.exe (instalá Inno Setup 6 o 'choco install innosetup -y').")
            raise SystemExit(1)
        ok("Inno Setup encontrado.")
        formatos = ["exe"]
    elif so == "linux":
        if herramienta("dpkg-deb"):
            formatos.append("deb")
        else:
            warn("dpkg-deb no está instalado: se salta el .deb ('sudo apt install dpkg').")
        if herramienta("rpmbuild"):
            formatos.append("rpm")
        else:
            warn("rpmbuild no está instalado: se salta el .rpm ('sudo apt install rpm').")
        if not herramienta("curl"):
            err("curl no está instalado (lo necesita el AppImage para bajar appimagetool).")
            raise SystemExit(1)
        formatos.append("appimage")
        ok(f"Formatos a compilar: {', '.join(formatos)}")
    elif so == "macos":
        for h in ("sips", "iconutil", "hdiutil"):
            if not herramienta(h):
                err(f"Falta '{h}' (herramienta estándar de macOS).")
                raise SystemExit(1)
        ok("Herramientas de empaquetado de macOS presentes.")
        formatos = ["dmg"]
    return formatos


# ── PASO 4 — Compilar (reutiliza packaging/<so>/build_*.*) ─────────────────
def compilar(so):
    separador(f"PASO 4 — Compilar ({so})")
    if so == "windows":
        r = run_sub(["powershell", "-ExecutionPolicy", "Bypass", "-File",
                     str(PROJECT_DIR / "packaging" / "windows" / "build_windows.ps1")])
        if r.returncode != 0:
            err("build_windows.ps1 falló."); raise SystemExit(1)
    elif so == "linux":
        scripts = [("build_linux_appimage.sh", True),
                  ("build_linux_deb.sh", bool(herramienta("dpkg-deb"))),
                  ("build_linux_rpm.sh", bool(herramienta("rpmbuild")))]
        for nombre, corresponde in scripts:
            if not corresponde:
                continue
            info(f"Ejecutando {nombre}...")
            r = run_sub(["bash", str(PROJECT_DIR / "packaging" / "linux" / nombre)])
            if r.returncode != 0:
                err(f"{nombre} falló."); raise SystemExit(1)
    elif so == "macos":
        r = run_sub(["bash", str(PROJECT_DIR / "packaging" / "macos" / "build_macos.sh"), ARGS.arch])
        if r.returncode != 0:
            err("build_macos.sh falló."); raise SystemExit(1)
    ok("Compilación terminada.")


def rutas_esperadas(so, version, formatos):
    """Nombres exactos que generan los scripts de packaging/ (ver INSTALADOR
    LISTO: de cada uno) — así se sabe qué subir sin adivinar con globs."""
    d = PROJECT_DIR / "dist_installers"
    rutas = []
    if so == "windows":
        rutas.append(d / f"CerveceraVGB-Setup-{version}.exe")
    elif so == "linux":
        if "deb" in formatos: rutas.append(d / f"CerveceraVGB-{version}-x86_64.deb")
        if "rpm" in formatos: rutas.append(d / f"CerveceraVGB-{version}-x86_64.rpm")
        if "appimage" in formatos: rutas.append(d / f"CerveceraVGB-{version}-x86_64.AppImage")
    elif so == "macos":
        rutas.append(d / f"CerveceraVGB-{version}-macos-{ARGS.arch}.dmg")
    return rutas


def _formatos_ya_compilados(so, version):
    """Para --skip-build: en vez de asumir qué se compiló antes, mira qué
    instaladores existen realmente en dist_installers/ para esta versión."""
    if so == "windows" or so == "macos":
        return None  # rutas_esperadas no usa 'formatos' para estos SO
    d = PROJECT_DIR / "dist_installers"
    candidatos = {"deb": f"CerveceraVGB-{version}-x86_64.deb",
                 "rpm": f"CerveceraVGB-{version}-x86_64.rpm",
                 "appimage": f"CerveceraVGB-{version}-x86_64.AppImage"}
    return [f for f, nombre in candidatos.items() if (d / nombre).exists()]


# ── Checksums ────────────────────────────────────────────────────────────────
def calcular_checksums(rutas):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in rutas}

def formatear_checksums(dic):
    return "".join(f"{sha}  {nombre}\n" for nombre, sha in sorted(dic.items()))

def parsear_checksums(texto):
    dic = {}
    for linea in texto.splitlines():
        partes = linea.strip().split(None, 1)
        if len(partes) == 2:
            dic[partes[1].strip()] = partes[0].strip()
    return dic


# ── GitHub Releases API ────────────────────────────────────────────────────
def cargar_token():
    for var in TOKEN_ENV:
        t = os.environ.get(var, "").strip()
        if t: return t
    try:
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t: return t
    except OSError:
        pass
    return None


def api(method, url, token=None, data=None):
    body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else data
    req = urllib.request.Request(url, data=body, method=method)
    if token:
        req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cervecera-vgb-build-desktop")
    if isinstance(data, (dict, list)):
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def obtener_o_crear_release(version, token):
    tag = f"v{version}"
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{tag}"
    try:
        release = api("GET", url, token)
        if release.get("draft"):
            warn(f"El release {tag} existía como BORRADOR (no lo ve nadie más que vos) — lo publico.")
            release = api("PATCH", f"https://api.github.com/repos/{OWNER}/{REPO}/releases/{release['id']}",
                          token, {"draft": False})
        return release, tag
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    info(f"El release {tag} no existe todavía: lo creo.")
    data = {"tag_name": tag, "name": f"Cervecera VGB {tag}", "draft": False, "prerelease": False,
            "body": _cuerpo_release(version)}
    release = api("POST", f"https://api.github.com/repos/{OWNER}/{REPO}/releases", token, data)
    return release, tag


def _cuerpo_release(version):
    """Descripción inicial del release a partir de la plantilla (solo al
    crearlo por primera vez; si ya existe no se toca, por si lo editaste
    a mano). Best-effort: si falta el archivo, el release queda sin cuerpo."""
    plantilla = PROJECT_DIR / "packaging" / "legends" / "RELEASE_NOTES.md"
    try:
        return plantilla.read_text(encoding="utf-8").replace("1.0.0", version)
    except OSError:
        return ""


def borrar_asset_si_existe(release, nombre, token):
    for a in release.get("assets", []):
        if a["name"] == nombre:
            api("DELETE", f"https://api.github.com/repos/{OWNER}/{REPO}/releases/assets/{a['id']}", token)
            return True
    return False


def subir_asset(ruta, release_id, token):
    url = (f"https://uploads.github.com/repos/{OWNER}/{REPO}/releases/{release_id}/assets"
          f"?name={urllib.parse.quote(ruta.name)}")
    req = urllib.request.Request(url, data=ruta.read_bytes(), method="POST")
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cervecera-vgb-build-desktop")
    req.add_header("Content-Type", "application/octet-stream")
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())


# ── PASO 5 — Publicar ───────────────────────────────────────────────────────
def publicar(version, rutas_instaladores):
    separador("PASO 5 — Publicar en GitHub Releases")
    token = cargar_token()
    if not token:
        err("No hay token de GitHub configurado.")
        info(f"Configuralo con: echo TU_TOKEN > {TOKEN_FILE}   (o variable GITHUB_TOKEN)")
        raise SystemExit(1)

    release, tag = obtener_o_crear_release(version, token)
    ok(f"Release {tag}: {release.get('html_url', '(recién creado)')}")

    # El checksums.txt es compartido entre plataformas: si ya hay uno subido
    # (de otro SO), se fusiona en vez de pisarlo.
    checksums_previos = {}
    for a in release.get("assets", []):
        if a["name"] == "checksums.txt":
            try:
                with urllib.request.urlopen(a["browser_download_url"], timeout=30) as r:
                    checksums_previos = parsear_checksums(r.read().decode("utf-8"))
            except Exception as e:
                warn(f"No pude leer el checksums.txt existente: {e}")

    checksums_previos.update(calcular_checksums(rutas_instaladores))
    checksums_path = PROJECT_DIR / "dist_installers" / "checksums.txt"
    checksums_path.write_text(formatear_checksums(checksums_previos), encoding="utf-8")

    subidos = []
    for ruta in list(rutas_instaladores) + [checksums_path]:
        borrar_asset_si_existe(release, ruta.name, token)
        info(f"Subiendo {ruta.name}...")
        subir_asset(ruta, release["id"], token)
        subidos.append(ruta.name)

    verificar_publicacion(tag, subidos, token)
    print(f"\n  📦 {tag}: https://github.com/{OWNER}/{REPO}/releases/tag/{tag}\n")


def verificar_publicacion(tag, nombres_esperados, token):
    """No se confía en la respuesta del POST de subida: se vuelve a pedir el
    release a la API y se confirma que cada asset figura ahí, publicado, con
    su link real de descarga — así una publicación que 'parece' exitosa pero
    no quedó visible (por ejemplo por haber quedado en borrador) se detecta
    acá en vez de reportarse como éxito."""
    url = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/tags/{tag}"
    release = api("GET", url, token)
    if release.get("draft"):
        err(f"El release {tag} sigue marcado como BORRADOR después de publicar — revisalo a mano.")
        raise SystemExit(1)
    presentes = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    faltan = [n for n in nombres_esperados if n not in presentes]
    if faltan:
        err(f"GitHub no lista todavía estos assets (la subida no quedó confirmada): {', '.join(faltan)}")
        raise SystemExit(1)
    for n in nombres_esperados:
        ok(f"Confirmado en GitHub: {presentes[n]}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now()
    print("\n" + "═" * 55)
    print("  🍺  CERVECERA VGB — Build Escritorio (Windows/Linux/macOS)")
    print("  By SaintWick | nicoweb45@proton.me")
    print("═" * 55)

    try:
        verificar_entorno()
        so = detectar_so()
        info(f"Sistema operativo detectado: {so}")
        version = leer_y_fijar_version()

        if not ARGS.skip_build:
            formatos = verificar_herramientas(so)
            compilar(so)
        else:
            warn("--skip-build: uso lo que ya haya en dist_installers/.")
            formatos = _formatos_ya_compilados(so, version)
            if formatos == []:
                err(f"No hay ningún instalador de la versión {version} en dist_installers/.")
                raise SystemExit(1)

        rutas = rutas_esperadas(so, version, formatos)
        faltantes = [str(r) for r in rutas if not r.exists()]
        if faltantes:
            err(f"No están generados: {', '.join(faltantes)}")
            raise SystemExit(1)

        if not ARGS.skip_upload:
            publicar(version, rutas)
        else:
            warn("--skip-upload: no publico en GitHub.")

        elapsed = int((datetime.now() - start).total_seconds())
        separador("BUILD COMPLETADO")
        for r in rutas: print(f"  · {r}")
        print(f"\n  Tiempo total: {elapsed // 60}m {elapsed % 60}s\n")
    except SystemExit:
        sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n{_WARN} Cancelado.\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
