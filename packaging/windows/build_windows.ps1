# Cervecera VGB - Build + instalador Windows (ejecutar en runner Windows, repo raíz)
$ErrorActionPreference = "Stop"
$version = (Get-Content "packaging\VERSION").Trim()

Write-Host "== PyInstaller (onedir windowed) =="
python -m PyInstaller --noconfirm --clean --onedir --windowed `
    --name "Cervecera_VGB" `
    --icon "packaging\icons\windows\app_icon.ico" `
    --add-data "recetas_base.json;." `
    --add-data "logo.png;." `
    --add-data "logo.ico;." `
    app.py

Write-Host "== Inno Setup =="
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = Get-ChildItem "C:\Program Files*\Inno Setup*\ISCC.exe" | Select-Object -First 1
}
if (-not $iscc) { throw "ISCC.exe no encontrado (instalá Inno Setup 6 o choco install innosetup -y)" }
& $iscc "packaging\windows\CerveceraVGB.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló" }

New-Item -ItemType Directory -Force -Path "dist_installers" | Out-Null
Get-ChildItem "dist_installers\CerveceraVGB-Setup-*.exe" | ForEach-Object { Write-Host "INSTALADOR LISTO: $($_.FullName)" }
