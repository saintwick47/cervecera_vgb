#!/usr/bin/env python3
# subir_github.py — Sube archivos modificados usando token desde config
import os, sys, json, base64, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

OWNER, REPO = "saintwick47", "cervecera_vgb"
BRANCH = "main"
TOKEN_FILE = Path.home() / ".config" / "cervecera_vgb" / "token"
README = "README.md"
MARCADOR = "## 📝 Historial de cambios (CHANGELOG)"


def cargar_token():
    # 1) Variable de entorno
    for var in ("GITHUB_TOKEN", "GH_TOKEN"):
        t = os.environ.get(var, "").strip()
        if t: return t
    # 2) Archivo seguro (~/.config/cervecera_vgb/token)
    try:
        t = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if t: return t
    except OSError: pass
    # 3) Pedir una vez y guardar
    t = input("Pegá tu token de GitHub (ghp_...): ").strip()
    if not t:
        sys.exit("❌ Sin token. Generá uno en https://github.com/settings/tokens/new")
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(t, encoding="utf-8")
    try: os.chmod(TOKEN_FILE, 0o600)
    except OSError: pass
    print(f"✅ Token guardado en {TOKEN_FILE}")
    return t


def api(method, path, token, data=None):
    url = f"https://api.github.com/repos/{OWNER}/{REPO}{path}"
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "cervecera-vgb-uploader")
    if body: req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        det = e.read().decode("utf-8", errors="replace")
        sys.exit(f"❌ {method} {path} → {e.code}: {det}")


def sha_actual(token, ruta):
    try:
        info = api("GET", f"/contents/{ruta}?ref={BRANCH}", token)
        return info.get("sha")
    except SystemExit:
        return None


def archivos_modificados():
    import subprocess
    out = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
    items = []
    for linea in out.splitlines():
        if len(linea) < 4: continue
        code, path = linea[:2], linea[3:].strip()
        if code.strip() in ("M", "A", "??", "MM", "AM"):
            items.append(path)
    return items


def editar_readme(mensaje, archivos):
    p = Path(README)
    contenido = p.read_text(encoding="utf-8") if p.exists() else f"# Cervecera VGB\n\n{MARCADOR}\n"
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    lineas = mensaje.strip().splitlines() or ["Cambios varios."]
    entrada = [f"\n### {fecha} — {lineas[0]}\n"]
    entrada += [f"- {l}" for l in lineas[1:]]
    entrada.append(f"- Archivos: {', '.join(archivos)}\n")
    bloque = "\n".join(entrada)
    if MARCADOR in contenido:
        idx = contenido.find(MARCADOR) + len(MARCADOR)
        nuevo = contenido[:idx] + "\n" + bloque + contenido[idx:]
    else:
        nuevo = contenido.rstrip("\n") + f"\n\n{MARCADOR}\n{bloque}"
    p.write_text(nuevo, encoding="utf-8")


def subir_archivo(ruta, token, mensaje_commit, sha=None):
    with open(ruta, "rb") as f:
        content = base64.b64encode(f.read()).decode("ascii")
    data = {"message": mensaje_commit, "content": content, "branch": BRANCH}
    if sha: data["sha"] = sha
    api("PUT", f"/contents/{ruta}", token, data)
    print(f"  ✅ {ruta}")


def main():
    mensaje = " ".join(sys.argv[1:]).strip()
    if not mensaje:
        mensaje = input("Mensaje del commit: ").strip()
    if not mensaje:
        sys.exit("❌ Sin mensaje.")

    token = cargar_token()

    # Archivos que SÍ o SÍ subimos
    archivos_fijos = ["app.py", "brew_engine.py", "catalogo_ar.py", "test_cervecera.py", "database.py"]
    faltantes = [a for a in archivos_fijos if not Path(a).exists()]
    if faltantes:
        sys.exit(f"❌ Faltan archivos: {', '.join(faltantes)}")

    # + cualquier otro modificado detectado por git
    mods_extra = [a for a in archivos_modificados() if a not in archivos_fijos]
    mods = archivos_fijos + mods_extra

    print(f"📤 Subiendo {len(mods)} archivo(s) a GitHub:")
    for m in mods: print(f"  · {m}")

    editar_readme(mensaje, mods)
    if README not in mods: mods.append(README)

    print("\n🚀 Enviando vía API REST...")
    for ruta in mods:
        if not Path(ruta).exists(): continue
        sha = sha_actual(token, ruta)
        subir_archivo(ruta, token, mensaje, sha)

    print(f"\n✅ Listo. Ver: https://github.com/{OWNER}/{REPO}/commits/{BRANCH}")


if __name__ == "__main__":
    main()
