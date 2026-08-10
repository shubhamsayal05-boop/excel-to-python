@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  AVL-DRIVE Heatmap Tool V5.1 - Windows EXE
echo ============================================
echo.
echo Build folder: %CD%
echo Python: 
python --version
where python
echo.

echo [1/6] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul

echo [2/6] Exporting operation_modes.json...
python export_operation_modes.py
if errorlevel 1 (
    echo EXPORT FAILED
    pause
    exit /b 1
)

echo [3/6] Verifying config and JSON...
python -c "import json; d=json.load(open('operation_modes.json')); assert 10090100 in d['HEATMAP_OPERATION_CODES']; assert 10090200 in d['HEATMAP_OPERATION_CODES']; print('OK:', d['BUILD_STAMP'])"
if errorlevel 1 (
    echo.
    echo CONFIG CHECK FAILED - Upshift/Downshift codes missing
    pause
    exit /b 1
)

echo [4/6] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [5/6] Building executable (may take several minutes)...
python -m PyInstaller AVL-DRIVE-Heatmap-Tool.spec --noconfirm --clean
if errorlevel 1 (
    echo BUILD FAILED
    pause
    exit /b 1
)

echo [6/6] Verifying output...
set "OUT=dist\AVL-DRIVE-Heatmap-Tool"
set "INT=%OUT%\_internal"
set "FAIL=0"
for /f %%i in ('python -c "import sys; print(f'python{sys.version_info.major}{sys.version_info.minor}.dll')"') do set "PYDLL=%%i"

if not exist "%OUT%\AVL-DRIVE-Heatmap-Tool.exe" (
    echo ERROR: EXE not found.
    set "FAIL=1"
)

if not exist "%INT%\%PYDLL%" (
    echo ERROR: %INT%\%PYDLL% is MISSING.
    echo        The EXE will show "Failed to load Python DLL".
    set "FAIL=1"
) else (
    echo OK: %PYDLL% found
)

if not exist "%INT%\vcruntime140.dll" (
    echo ERROR: %INT%\vcruntime140.dll is MISSING.
    echo        Install VC++ Redistributable OR rebuild with python.org Python.
    set "FAIL=1"
) else (
    echo OK: vcruntime140.dll found
)

findstr /C:"10090100" "%INT%\operation_modes.json" >nul
if errorlevel 1 (
    echo ERROR: operation_modes.json missing 10090100
    set "FAIL=1"
) else (
    echo OK: operation_modes.json contains Upshift 10090100
)

if not exist "%INT%\_tcl_data" (
    echo WARNING: _tcl_data missing - Tcl error possible at startup
) else (
    echo OK: _tcl_data bundled
)

echo.
if "%FAIL%"=="1" (
    echo BUILD VERIFICATION FAILED - do not distribute this EXE.
    pause
    exit /b 1
)

echo SUCCESS.
echo.
echo Run: %OUT%\AVL-DRIVE-Heatmap-Tool.exe
echo.
echo IMPORTANT:
echo  - Copy the ENTIRE folder "%OUT%" (exe + _internal folder together)
echo  - Do not run from a double-nested zip path; use e.g. C:\Tools\AVL-DRIVE-Heatmap-Tool\
echo  - If startup still fails, install VC++ Redistributable x64:
echo    https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist
echo.
pause
endlocal
