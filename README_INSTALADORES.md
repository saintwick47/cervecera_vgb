# Cervecera VGB — Instaladores de escritorio (Windows / Linux / macOS)

El código de la versión PC vive en la raíz de este repositorio. Con un
clic en **Actions** se generan los **4 instaladores** en la nube
(GitHub) y se adjuntan solos al release indicado:

| Sistema | Archivo que se genera |
|---|---|
| Windows | `CerveceraVGB-Setup-1.0.0.exe` (instalador con logo en el escritorio) |
| Linux x86_64 | `CerveceraVGB-1.0.0-x86_64.AppImage` |
| macOS Intel | `CerveceraVGB-1.0.0-macos-intel.dmg` |
| macOS Apple Silicon | `CerveceraVGB-1.0.0-macos-arm64.dmg` |
| Todos | `checksums.txt` (SHA-256 de cada instalador) |

## Pasos para publicar

1. **Subir el código** (repositorio `saintwick47/cervecera_vgb`):
   ```bash
   cd /home/saintwick/Escritorio/beer_vgb
   git init
   git add .
   git commit -m "App de escritorio v1.0.0 + empaquetado multiplataforma"
   git branch -M main
   git remote add origin https://github.com/saintwick47/cervecera_vgb.git
   git push -u origin main
   ```
2. **Disparar la compilación** en GitHub: pestaña **Actions** →
   *Build instaladores (Windows/Linux/macOS)* → **Run workflow** →
   tag `v1.0.0` → Run.
3. Esperar ~10–15 min. Al terminar, los instaladores y el
   `checksums.txt` aparecen adjuntos en
   https://github.com/saintwick47/cervecera_vgb/releases/tag/v1.0.0
4. (Opcional) Editá el release y pegá la descripción que está en
   `packaging/legends/RELEASE_NOTES.md`.

> Tip: si publicás un **release nuevo** (ej. tag `v1.1.0`) con sus
> notas, el workflow se dispara solo y adjunta todo a ese release.

## Si querés compilar en tu máquina (sin GitHub Actions)

- Windows: instalá Python 3.12 + Inno Setup 6 y ejecutá
  `packaging/windows/build_windows.ps1`.
- Linux: `bash packaging/linux/build_linux_appimage.sh`
  (requiere python3-tk).
- macOS: `bash packaging/macos/build_macos.sh intel|arm64`.
- Luego subí los archivos de `dist_installers/` con el botón
  *"Editar release"* → *arrastrar archivos* en GitHub.

## Notas
- El ícono de escritorio usa el logo oficial (`logo.png`/`app_icon.ico`,
  generados desde el logo cuadrado de la app).
- En la primera instalación, macOS pedirá confirmar la app descargada
  (clic derecho → Abrir). En Linux: `chmod +x` al AppImage.
