@echo off
chcp 65001 >nul
title Instalar Moderador LIVE
cd /d "%~dp0"

echo.
echo  === Instalando Moderador LIVE ===
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo  [X] No encontre Python.
  echo      Instalalo desde https://www.python.org/downloads/
  echo      y MARCA la casilla "Add Python to PATH". Luego vuelve a abrir este archivo.
  echo.
  pause
  exit /b
)

echo  [1/2] Instalando librerias...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo  [X] Fallo la instalacion de librerias. Revisa tu internet y prueba otra vez.
  pause
  exit /b
)

echo  [2/2] Creando acceso directo en el Escritorio...
for /f "delims=" %%i in ('python -c "import sys,os;print(os.path.join(os.path.dirname(sys.executable),'pythonw.exe'))"') do set PYW=%%i
powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Moderador LIVE.lnk');" ^
  "$s.TargetPath='%PYW%';" ^
  "$s.Arguments='\"%~dp0Moderador.pyw\"';" ^
  "$s.WorkingDirectory='%~dp0';" ^
  "$s.IconLocation='%SystemRoot%\System32\shell32.dll,22';" ^
  "$s.Save()"

echo.
echo  Listo! Ya tienes "Moderador LIVE" en el Escritorio.
echo  Abrelo con doble clic cuando vayan a hacer live.
echo.
pause
