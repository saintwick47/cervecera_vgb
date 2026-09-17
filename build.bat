@echo off
echo Compilando Cervecera VGB...
rmdir /s /q build dist
pyinstaller --noconfirm --onedir --windowed --add-data "recetas_base.json;." --add-data "logo.ico;." --icon "logo.ico" --name "Cervecera_VGB" app.py
echo.
echo Compilacion finalizada! El ejecutable esta en la carpeta 'dist'.
pause
