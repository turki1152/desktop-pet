@echo off
REM ===========================================================================
REM  Build Desktop Pet into ONE standalone Windows .exe using PyInstaller.
REM  Produces a single portable file:  dist\DesktopPet.exe
REM
REM  The characters and assets are bundled inside the .exe. On first run the app
REM  copies them out next to the .exe (as characters\ and assets\ folders) so you
REM  can edit them and add your own characters. settings.json / reminders.json
REM  are saved there too.
REM ===========================================================================
cd /d "%~dp0"

echo Installing build dependency (PyInstaller)...
pip install pyinstaller >nul 2>&1

echo Building single-file executable...
pyinstaller --noconfirm --clean --onefile --windowed ^
    --name DesktopPet ^
    --icon assets\icon.ico ^
    --add-data "characters;characters" ^
    --add-data "assets;assets" ^
    main.py
if errorlevel 1 (
    echo.
    echo Build FAILED. See the messages above.
    pause
    exit /b 1
)

echo.
echo ===========================================================================
echo  Done!  Your single-file app is here:
echo     dist\DesktopPet.exe
echo.
echo  Move dist\DesktopPet.exe anywhere you like and double-click it to run your
echo  pet -- no Python needed. (It creates characters\ and assets\ folders beside
echo  itself on first run so you can customise and add characters.)
echo ===========================================================================
pause
