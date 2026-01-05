# Decidim Translation Customizer GUI

A graphical user interface for comparing and editing Decidim translation files from Crowdin and Term Customizer.

## Features

1. **File Upload**: Upload Crowdin source files and multiple Term Customizer files
2. **Persistent Configuration**: Crowdin file path is automatically saved and restored on next startup
3. **Diff View**: Visual comparison showing differences between the two sources
4. **Manual Editing**: Edit translation values directly in an editable table
5. **Statistics Overview**: Detailed statistics showing matching keys, mismatches, and keys to be removed
6. **Save Results**: Export edited translations back to CSV format (individual or merged)
7. **Export Deleted Keys**: Separately export keys that will be removed (exist only in Term Customizer)
8. **Helpful Tooltips**: Hover over settings to see detailed explanations

## Requirements

- Python 3.6+
- tkinter (usually included with Python)

## Building the Application

To create a standalone executable:

### macOS/Linux:
```bash
./build_app.sh
```

### Windows:
```cmd
build_app.bat
```

The executable will be created in the `dist` folder. On macOS/Linux, it will be named `DecidimTranslationCustomizer`, and on Windows it will be `DecidimTranslationCustomizer.exe`.

**Note**: You may need to install PyInstaller first:
```bash
pip install pyinstaller
```

## Usage

1. Run the application:
   ```bash
   python decidim_translation_gui.py
   ```

2. **Upload Files**:
   - Click "Upload Crowdin File" to select your Crowdin file:
     - **XLIFF format** (`.xliff`) - Recommended format from Crowdin
     - The Crowdin file path is automatically saved and will be loaded on next startup
     - This is convenient since Crowdin files don't change often
   - Click "Add Term Customizer File(s)" to select one or more Term Customizer CSV files (format: `key;value;locale`)
     - You can add multiple files and they will all be compared
     - Use "Clear Term Customizer Files" to remove all added files
   
   Note: 
   - When loading an XLIFF file, the source and target languages are automatically detected
   - The application validates that Term Customizer locales match the XLIFF languages before comparison
   - Only matching locales are compared (English uses XLIFF source, other languages use XLIFF target)
   - The Crowdin file path is saved in `~/.decidim_translation_customizer.json` for persistence

3. **Configure Settings**:
   - The application automatically detects locales from both files
   - Locales are automatically matched:
     - **English (source language)**: Compares Term Customizer values with XLIFF source text
     - **Other languages (target language)**: Compares Term Customizer values with XLIFF target translations
   - Only matching locales are compared (validation ensures locales match between files)
   
   **Conditional Logic Settings** (configure before each comparison):
   - **Require Term Customizer Value**: Only check entries where Term Customizer has a value (if disabled, will check even if Term Customizer value is empty)
     - *Hover over the checkbox for detailed help text*
   - **Include Empty Values**: Include empty values in comparison (if disabled, empty values are ignored)
     - *Hover over the checkbox for detailed help text*
   - **Case Sensitive**: Perform case-sensitive comparison (if disabled, "Hello" and "hello" are considered the same)
     - *Hover over the checkbox for detailed help text*
   
   **Save Options** (configure before saving):
   - **Save Individual Files**: Saves each Term Customizer file separately with its mismatches
     - *Hover over the option for detailed help text*
   - **Merge All Files**: Combines all mismatches from all files into a single output file
     - *Hover over the option for detailed help text*
   - **Output Suffix**: Optional suffix to add to output filenames (e.g., "_updated")
     - *Hover over the label for detailed help text*

4. **Compare Files**:
   - Click "Compare Files" to analyze differences
   - View the diff in the "Diff View" tab
   - Review and edit entries in the "Edit Translations" tab
   - Check the "Statistics" tab for a detailed overview:
     - Total keys in each file
     - Number of matching vs mismatched keys
     - Keys that will be removed (exist only in Term Customizer)
     - Keys that exist only in Crowdin
     - Per-file statistics (when multiple files are loaded)
     - Match and mismatch percentages

5. **Edit Translations**:
   - Double-click any row in the "Edit Translations" tab to edit the value
   - Make your changes and click "Save"

6. **Save Results**:
   - Configure save options before saving:
     - **Save Individual Files**: Saves each Term Customizer file separately with its mismatches
     - **Merge All Files**: Combines all mismatches into a single file
   - **Output Suffix**: Add a suffix to output filenames (e.g., "_updated" will create "filename_updated.csv")
   - Click "Save Results" to export your edited translations
   - Individual files are saved in the same directory as the source files
   - Merged files require selecting a directory
   - The output format matches the Term Customizer import format: `locale;key;value`

7. **Export Deleted Keys**:
   - Click "Export Deleted Keys" to export keys that exist only in Term Customizer (will be removed)
   - This creates a CSV file with all entries for keys that don't exist in Crowdin
   - Useful for reviewing what will be deleted before saving

## File Formats

### Crowdin File Format

**XLIFF Format (Recommended)**:
- Standard XLIFF 1.2 format exported from Crowdin
- Translation keys are stored in the `resname` attribute of `<trans-unit>` elements
- Source text is in `<source>` elements
- Target translations are in `<target>` elements
- The target language is automatically detected from the `target-language` attribute

**CSV Format (Legacy)**:
Expected columns (semicolon-delimited):
- `ID`
- `key`
- `Source Text`
- `[Target Locale Column]` (e.g., `DE`)
- `Context`

### Term Customizer File Format
Expected columns (semicolon-delimited):
- `key`
- `value`
- `locale`

## Notes

- All CSV files use semicolon (`;`) as the delimiter
- The application automatically detects mismatches between Crowdin and Term Customizer values
- Only mismatched entries are shown in the diff and edit views
- Edited values are preserved when saving

