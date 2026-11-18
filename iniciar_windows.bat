@echo off
chcp 65001 >nul
echo ==============================================
echo      Cálculo de Tiempo de Arranque - Web
echo ==============================================
where py >nul 2>&1
if %errorlevel% equ 0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
  echo No se pudieron instalar las dependencias. Comprueba tu conexión a internet.
  pause
  exit /b 1
)
%PYTHON% -m streamlit run streamlit_app.py
pause
