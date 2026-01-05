# GitHub Repository Guide

## What to Include

✅ **Include these files:**

1. **Source Code:**
   - `decidim_translation_gui.py` - Main application source code

2. **Build Scripts:**
   - `build_app.sh` - Build script for macOS/Linux
   - `build_app.bat` - Build script for Windows
   - `DecidimTranslationCustomizer.spec` - PyInstaller specification file
   - `requirements.txt` - Python dependencies

3. **Documentation:**
   - `README.md` - Main documentation
   - `BUILD_INSTRUCTIONS.md` - Detailed build instructions
   - `GITHUB_GUIDE.md` - This file

## What NOT to Include

❌ **Exclude these (handled by .gitignore):**

1. **Build Artifacts:**
   - `build/` - PyInstaller build directory
   - `dist/` - Compiled executables (users should build their own)

2. **User Data:**
   - `*.xliff` - Sample/test XLIFF files
   - `*.csv` - Sample/test CSV files
   - `.decidim_translation_customizer.json` - User configuration file

3. **Python Cache:**
   - `__pycache__/` - Python bytecode cache
   - `*.pyc` - Compiled Python files

4. **IDE/Editor Files:**
   - `.vscode/`, `.idea/` - IDE settings
   - `*.swp`, `*.swo` - Editor swap files

## Why Include Build Scripts?

**Yes, include build scripts** because:

1. **Reproducibility**: Users can build the application themselves
2. **Cross-platform**: Different scripts for different platforms
3. **Documentation**: Scripts serve as executable documentation
4. **CI/CD**: Can be used in automated build pipelines
5. **Transparency**: Shows exactly how the app is built

## Why NOT Include Built Executables?

**Don't include `dist/` folder** because:

1. **Size**: Executables are large and bloat the repository
2. **Platform-specific**: Different builds for different OSes
3. **Version control**: Binaries don't diff well in Git
4. **Security**: Users should build from source to verify
5. **Fresh builds**: Ensures users get the latest version

## Recommended Repository Structure

```
DecidimTermCustomizerGUI/
├── .gitignore
├── README.md
├── BUILD_INSTRUCTIONS.md
├── GITHUB_GUIDE.md
├── requirements.txt
├── decidim_translation_gui.py
├── build_app.sh
├── build_app.bat
└── DecidimTranslationCustomizer.spec
```

## GitHub Releases

For distribution, use **GitHub Releases**:

1. Build the executable locally
2. Create a GitHub Release
3. Upload the executable as a release asset
4. Tag the release with a version number

This way:
- Source code stays clean
- Users can download pre-built executables
- Different platforms can have separate assets
- Version history is maintained

## Example Release Workflow

```bash
# Build the application
./build_app.sh  # or build_app.bat on Windows

# Create a release (via GitHub web interface or CLI)
# Upload dist/DecidimTranslationCustomizer as release asset
```

