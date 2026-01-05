# Building the Decidim Translation Customizer Application

## Prerequisites

1. Python 3.6 or higher installed
2. pip package manager

## Installation Steps

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

### 2. Build the Application

#### On macOS/Linux:
```bash
./build_app.sh
```

#### On Windows:
```cmd
build_app.bat
```

Or manually:
```bash
pyinstaller DecidimTranslationCustomizer.spec
```

## Output

After building, the executable will be in the `dist` folder:

- **macOS/Linux**: `dist/DecidimTranslationCustomizer`
- **Windows**: `dist/DecidimTranslationCustomizer.exe`

## Running the Application

### From source (development):
```bash
python decidim_translation_gui.py
```

### From executable:
Simply double-click the executable file, or run it from the command line:
- macOS/Linux: `./dist/DecidimTranslationCustomizer`
- Windows: `dist\DecidimTranslationCustomizer.exe`

## Troubleshooting

### If PyInstaller is not found:
Make sure Python and pip are in your PATH, or use:
```bash
python -m pip install pyinstaller
python -m PyInstaller DecidimTranslationCustomizer.spec
```

### If the build fails:
- Make sure all dependencies are installed
- Check that tkinter is available (usually included with Python)
- Try building with verbose output: `pyinstaller --log-level=DEBUG DecidimTranslationCustomizer.spec`

### macOS Code Signing:
If you get code signing warnings on macOS, you may need to sign the app:
```bash
codesign --force --deep --sign - dist/DecidimTranslationCustomizer
```

