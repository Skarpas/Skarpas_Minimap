@echo off
echo Creando entorno virtual...
python -m venv .venv
echo Instalando dependencias...
.venv\Scripts\pip install -r requirements.txt
echo.
echo Listo. Ejecuta run.bat para iniciar el programa.
pause
