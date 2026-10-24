@echo off
setlocal
cd /d "%~dp0"

echo [EzZapret] Checking virtual environment...
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Python 3 was not found. Install Python 3.10+ and make sure the py launcher is available.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

if not exist "assets\EzZapret.ico" (
    echo [ERROR] assets\EzZapret.ico was not found.
    pause
    exit /b 1
)

for /f "delims=" %%I in ('python -c "import os, customtkinter; print(os.path.dirname(customtkinter.__file__))"') do set "CTK_DIR=%%I"
if not defined CTK_DIR (
    echo [ERROR] Could not locate CustomTkinter package data.
    pause
    exit /b 1
)

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "EzZapret.spec" del /q "EzZapret.spec"

echo [EzZapret] Building EzZapret.exe...
pyinstaller --noconfirm --clean --onefile --windowed --uac-admin --name EzZapret --icon "%~dp0assets\EzZapret.ico" --add-data "%CTK_DIR%;customtkinter" --add-data "%~dp0assets\EzZapret.ico;assets" main.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo.
echo [OK] dist\EzZapret.exe created.
echo [OK] Custom EzZapret icon embedded.
echo [OK] Run the EXE from a writable folder, for example C:\EzZapret.
endlocal
