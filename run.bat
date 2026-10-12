@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>&1 || (echo Python не найден. Установите Python 3.11+ с python.org, отметив "Add python.exe to PATH". & pause & exit /b 1)
python -m pip install -q -r requirements.txt
start "" pythonw main.py
