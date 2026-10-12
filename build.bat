@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Сборка ZapretCloud

where python >nul 2>&1 || (echo Python не найден. Установите Python 3.11+ с python.org, отметив "Add python.exe to PATH". & pause & exit /b 1)

echo [1/4] Установка зависимостей...
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt pyinstaller || (echo Не удалось установить зависимости. & pause & exit /b 1)

echo [2/4] Сборка программы (PyInstaller)...
if exist build rmdir /s /q build
if exist dist\ZapretCloud rmdir /s /q dist\ZapretCloud
python -m PyInstaller --noconfirm --clean --onedir --windowed --uac-admin ^
  --name ZapretCloud --icon assets\icon.ico --add-data "assets;assets" ^
  --exclude-module tkinter main.py
if not exist dist\ZapretCloud\ZapretCloud.exe (echo Сборка не удалась, смотрите сообщения выше. & pause & exit /b 1)

echo [3/4] Копирование движка zapret...
robocopy engine dist\ZapretCloud\engine /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo Не удалось скопировать папку engine. & pause & exit /b 1)
if exist dist\ZapretCloud\engine\lists\zc_custom rmdir /s /q dist\ZapretCloud\engine\lists\zc_custom

echo [4/4] Сборка установщика (Inno Setup)...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo.
  echo Inno Setup 6 не найден - установщик не собран.
  echo Скачайте его с https://jrsoftware.org/isdl.php , установите и запустите build.bat ещё раз.
  echo Готовая программа без установщика: dist\ZapretCloud\ZapretCloud.exe
  pause
  exit /b 0
)
"%ISCC%" /Q installer\ZapretCloud.iss || (echo Ошибка сборки установщика. & pause & exit /b 1)

echo.
echo Готово!
echo   Установщик: installer\Output\ZapretCloud_Setup_2.2.13.exe
echo   Программа:  dist\ZapretCloud\ZapretCloud.exe
explorer installer\Output
pause
