#!/bin/bash
echo "Compilando Cervecera VGB..."
rm -rf build dist
pyinstaller --noconfirm --onedir --windowed --add-data "recetas_base.json:." --add-data "logo.ico:." --icon="logo.ico" --name "Cervecera_VGB" app.py
echo "Compilacion finalizada! El ejecutable esta en la carpeta 'dist'."
