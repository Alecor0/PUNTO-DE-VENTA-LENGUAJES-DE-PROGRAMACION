@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
    py -3 tienda.py
) else (
    python tienda.py
)
if errorlevel 1 (
    echo.
    echo Revisa que Python 3.10 o posterior y Tkinter esten instalados.
    pause
)
