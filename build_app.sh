#!/bin/bash

# Build script for Decidim Translation Assistant

echo "Building Decidim Translation Assistant..."

# Install PyInstaller if not already installed
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip install pyinstaller
fi

# Build the application using the spec file
pyinstaller DecidimTranslationCustomizer.spec

echo ""
echo "Build complete! The executable is in the 'dist' folder."
echo "You can run it with: ./dist/DecidimTranslationAssistant"

