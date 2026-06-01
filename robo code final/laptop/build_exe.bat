@echo off
REM Build frontend.py into a single executable using PyInstaller
REM Prefer the project's virtualenv Python if present, otherwise fall back to system python
set "VENV_PY=.\.venv\Scripts\python.exe"
if exist "%VENV_PY%" (
	set "PYTHON_EXE=%VENV_PY%"
) else (
	set "PYTHON_EXE=python"
)

echo Using Python: %PYTHON_EXE%
echo Installing dependencies with %PYTHON_EXE%...
%PYTHON_EXE% -m pip install --upgrade pip
%PYTHON_EXE% -m pip install -r requirements.txt

echo Running PyInstaller (windowed)...
%PYTHON_EXE% -m PyInstaller --onefile --noconsole --add-data "templates;templates" frontend.py

if %ERRORLEVEL% neq 0 (
	echo PyInstaller failed with exit code %ERRORLEVEL%.
	exit /b %ERRORLEVEL%
)

echo Build finished. The executable will be in the dist folder.
