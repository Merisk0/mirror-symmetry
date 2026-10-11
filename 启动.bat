@echo off
setlocal
cd /d "%~dp0"

set "EXE=%~dp0dist\MirrorSymmetry.exe"
if exist "%EXE%" (
  start "" "%EXE%" %*
  exit /b 0
)

set "PY=python"
where py >nul 2>nul && set "PY=py"

%PY% --version >nul 2>nul
if errorlevel 1 (
  echo [!] Python not found. Please install Python 3.8+ first: https://www.python.org/downloads/
  echo     ^(remember to tick "Add python.exe to PATH"^)
  pause
  exit /b 1
)

%PY% -c "import PIL" >nul 2>nul
if errorlevel 1 (
  echo [*] Installing dependency: Pillow ...
  %PY% -m pip install --user pillow
  %PY% -c "import PIL" >nul 2>nul
  if errorlevel 1 (
    echo [!] Pillow install failed. Please run manually:  pip install pillow
    pause
    exit /b 1
  )
)

where pythonw >nul 2>nul
if errorlevel 1 (
  %PY% -m mirror_symmetry %*
  if errorlevel 1 pause
) else (
  set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
  start "" pythonw "%~dp0mirror_symmetry.py" %*
)
exit /b 0
