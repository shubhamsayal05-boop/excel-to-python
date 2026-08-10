@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  AVL-DRIVE Heatmap Tool - Windows EXE build
echo ============================================
echo.

echo [1/5] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
del /s /q *.pyc 2>nul

echo [2/5] Verifying config before build...
python -c "import config; assert 10090100 in config.HEATMAP_OPERATION_CODES; assert 10090200 in config.HEATMAP_OPERATION_CODES; print('OK:', config.BUILD_STAMP)"
if errorlevel 1 (
    echo.
    echo CONFIG CHECK FAILED - Upshift/Downshift codes missing in config.py
    echo Make sure you are on branch cursor/add-gearshift-sub-operations-1720
    pause
    exit /b 1
)
echo [3/5] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [4/5] Building executable (may take several minutes)...
python -m PyInstaller AVL-DRIVE-Heatmap-Tool.spec --noconfirm --clean

echo [5/5] Verifying output...
if exist "dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe" (
    if exist "dist\AVL-DRIVE-Heatmap-Tool\_internal\python3*.dll" (
        findstr /C:"10090100" "dist\AVL-DRIVE-Heatmap-Tool\_internal\config.py" >nul
        if errorlevel 1 (
            echo.
            echo WARNING: Built config.py does NOT contain 10090100.
            echo The EXE bundle is stale — delete build and dist and rebuild.
        ) else (
            echo.
            echo SUCCESS - config.py in bundle contains 10090100 Upshift.
        )
        echo.
        echo Run: dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe
        echo.
        echo IMPORTANT: Copy the ENTIRE folder dist\AVL-DRIVE-Heatmap-Tool\
        echo            (not just the .exe). The _internal folder is required.
        echo.
        echo In Help page, bundle stamp should be: gearshift-10090100-10090200-filebundle
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
