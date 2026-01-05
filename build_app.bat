@echo off
REM Build script for Decidim Translation Customizer GUI (Windows)

echo Building Decidim Translation Customizer GUI...

REM Install PyInstaller if not already installed
where pyinstaller >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Build the application using the spec file
pyinstaller DecidimTranslationCustomizer.spec

echo.
echo Build complete! The executable is in the 'dist' folder.
echo You can run it with: dist\DecidimTranslationCustomizer.exe
pause

