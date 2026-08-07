@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo  AVL-DRIVE Heatmap Tool - Windows EXE build
echo ============================================
echo.

echo [1/4] Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

echo [3/4] Building executable (may take several minutes)...
python -m PyInstaller AVL-DRIVE-Heatmap-Tool.spec --noconfirm --clean

echo [4/4] Verifying output...
if exist "dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe" (
    if exist "dist\AVL-DRIVE-Heatmap-Tool\_internal\python3*.dll" (
        echo.
        echo SUCCESS.
        echo Run: dist\AVL-DRIVE-Heatmap-Tool\AVL-DRIVE-Heatmap-Tool.exe
        echo.
        echo IMPORTANT: Copy the ENTIRE folder dist\AVL-DRIVE-Heatmap-Tool\
        echo            (not just the .exe). The _internal folder is required.
    ) else (
        echo.
        echo WARNING: EXE was created but python310.dll was not found in _internal.
        echo Check the build log above for errors.
    )
) else (
    echo.
    echo BUILD FAILED - check errors above.
)

echo.
pause
endlocal
