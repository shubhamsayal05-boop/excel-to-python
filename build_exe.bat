@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  AVL-DRIVE Heatmap Tool - Windows EXE build
echo ============================================
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
    echo CONFIG CHECK FAILED - Upshift/Downshift codes missing in config.py
    echo Make sure you are on branch cursor/add-gearshift-sub-operations-1720
    pause
    exit /b 1
)
echo [4/6] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [5/6] Building executable (may take several minutes)...
python -m PyInstaller AVL-DRIVE-Heatmap-Tool.spec --noconfirm --clean

echo [6/6] Verifying output...
if exist "dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe" (
    if exist "dist\AVL-DRIVE-Heatmap-Tool\_internal\python3*.dll" (
        findstr /C:"10090100" "dist\AVL-DRIVE-Heatmap-Tool\_internal\operation_modes.json" >nul
        if errorlevel 1 (
            echo.
            echo WARNING: operation_modes.json in bundle does NOT contain 10090100.
            echo Delete build and dist folders and rebuild.
        ) else (
            echo.
            echo SUCCESS - operation_modes.json contains 10090100 Upshift.
        )
        if exist "dist\AVL-DRIVE-Heatmap-Tool\_internal\_tcl_data" (
            echo Tcl/Tk data bundled for matplotlib/PyInstaller.
        ) else (
            echo WARNING: _tcl_data folder missing — EXE may fail with Tcl error on startup.
        )
        echo.
        echo Run: dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe
        echo.
        echo IMPORTANT: Copy the ENTIRE folder dist\AVL-DRIVE-Heatmap-Tool\
        echo            (not just the .exe). The _internal folder is required.
        echo.
        echo In Help page, bundle stamp should be: gearshift-json-v3
    ) else (
        echo.
        echo WARNING: EXE was created but python DLL was not found in _internal.
        echo Check the build log above for errors.
    )
) else (
    echo.
    echo BUILD FAILED - check errors above.
)

echo.
pause
endlocal
