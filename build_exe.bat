@echo off
REM ===========================================================================
REM  Desktop Pet — build script
REM  Produces:  dist\DesktopPet.exe   (single portable file)
REM ===========================================================================
cd /d "%~dp0"

echo [1/3] Checking PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo     Installing PyInstaller...
    pip install pyinstaller
    if errorlevel 1 ( echo FAILED to install PyInstaller & pause & exit /b 1 )
)

echo [2/3] Building DesktopPet.exe...
pyinstaller --noconfirm --clean DesktopPet.spec
if errorlevel 1 (
    echo.
    echo *** BUILD FAILED — see messages above ***
    pause
    exit /b 1
)

echo [3/3] Copying to project root for easy access...
if exist "dist\DesktopPet.exe" (
    copy /Y "dist\DesktopPet.exe" "DesktopPet.exe" >nul
)

echo.
echo ===========================================================================
echo  SUCCESS!
echo.
echo  Distributable:   dist\DesktopPet.exe
echo  Quick copy:      DesktopPet.exe  (same folder as this bat)
echo.
echo  Share DesktopPet.exe on your website. Users just double-click it —
echo  no Python, no installer needed. On first run the pet automatically
echo  adds itself to Windows startup.
echo ===========================================================================
pause
