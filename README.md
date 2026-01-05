# Decidim Translation Assistant

A graphical user interface for comparing and editing Decidim translation files from Crowdin and Term Customizer.

## License

This project is licensed under the GNU Affero General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Features

1. **File Upload**: Upload Crowdin source files and multiple Term Customizer files
2. **Persistent Configuration**: Crowdin file path is automatically saved and restored on next startup
3. **Diff View**: Visual comparison showing differences between the two sources
4. **Manual Editing**: Edit translation values directly in an editable table
5. **Statistics Overview**: Detailed statistics showing matching keys, mismatches, and keys to be removed
6. **Save Results**: Export edited translations back to CSV format (individual or merged) - always creates new files
7. **Export Deleted Keys**: Separately export keys that will be removed (exist only in Term Customizer)
8. **Search & Replace**: Find and replace terms across multiple files with language-aware replacement
9. **Grammar Check & Tone Adjustment**: Use LLM to check grammar and adjust tone (formal/informal) for German translations
10. **Safe File Operations**: Original files are never modified - all outputs are saved to new timestamped files

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

The executable will be created in the `dist` folder. On macOS/Linux, it will be named `DecidimTranslationAssistant`, and on Windows it will be `DecidimTranslationAssistant.exe`.

**Note**: You may need to install PyInstaller first:
```bash
pip install pyinstaller
```

## Usage

1. Run the application:
   ```bash
   python decidim_translation_gui.py
   ```

2. **Load Files** (Top Section - Always Visible):
   - The file upload section is always visible at the top of the window, regardless of which tab is active
   - Click "Upload Crowdin File" to select your Crowdin file:
     - **XLIFF format** (`.xliff`) - Recommended format from Crowdin
     - The Crowdin file path is automatically saved and will be loaded on next startup
     - This is convenient since Crowdin files don't change often
   - Click "Add Term Customizer File(s)" to select one or more Term Customizer CSV files (format: `key;value;locale`)
     - You can add multiple files and they will all be compared
     - Use "Clear Term Customizer Files" to remove all added files
   - All loaded files are shown in the listbox
   
   Note: 
   - When loading an XLIFF file, the source and target languages are automatically detected
   - The application validates that Term Customizer locales match the XLIFF languages before comparison
   - Only matching locales are compared (English uses XLIFF source, other languages use XLIFF target)
   - The Crowdin file path is saved in `~/.decidim_translation_customizer.json` for persistence

3. **Compare Tab**:
   - **Comparison Settings**:
     - The application automatically detects locales from both files
     - Locales are automatically matched:
       - **English (source language)**: Compares Term Customizer values with XLIFF source text
       - **Other languages (target language)**: Compares Term Customizer values with XLIFF target translations
     - Only matching locales are compared (validation ensures locales match between files)
     
     **Conditional Logic Settings** (configure before each comparison):
     - **Require Term Customizer Value**: Only check entries where Term Customizer has a value (if disabled, will check even if Term Customizer value is empty)
     - **Include Empty Values**: Include empty values in comparison (if disabled, empty values are ignored)
     - **Case Sensitive**: Perform case-sensitive comparison (if disabled, "Hello" and "hello" are considered the same)
     
     **Save Options** (configure before saving):
     - **Save Individual Files**: Saves each Term Customizer file separately with its mismatches
     - **Merge All Files**: Combines all mismatches from all files into a single output file
     - **Output Suffix**: Optional suffix to add to output filenames (e.g., "_updated")
   
   - **Compare Files**:
     - Click "Compare Files" to analyze differences
     - View results in the split pane:
       - **Left pane (Diff View)**: Visual comparison showing differences between files
       - **Right pane (Statistics)**: Detailed statistics showing:
         - Total keys in each file
         - Number of matching vs mismatched keys
         - Keys that will be removed (exist only in Term Customizer)
         - Keys that exist only in Crowdin
         - Per-file statistics (when multiple files are loaded)
         - Match and mismatch percentages
   
   - **Save Results**:
     - Configure save options before saving
     - Click "Save Results" to export your edited translations
     - **Important**: All output files are created with timestamps to ensure uniqueness - original files are never modified
     - Individual files are saved in the same directory as the source files
     - Merged files require selecting a directory
     - The output format matches the Term Customizer import format: `locale;key;value`
   
   - **Export Deleted Keys**:
     - Click "Export Deleted Keys" to export keys that exist only in Term Customizer (will be removed)
     - This creates a CSV file with all entries for keys that don't exist in Crowdin
     - Useful for reviewing what will be deleted before saving
     - Output files include timestamps to ensure uniqueness

4. **Edit Translations Tab**:
   - Double-click any row to edit the value
   - Make your changes and click "Save"

5. **Search & Replace Tab**:
   - Select files (Crowdin and/or Term Customizer files) to search in
   - Enter search term and replacement term
   - Select the language for replacement (only terms in that language will be replaced)
   - Configure options: Case Sensitive, Whole Word Only
   - Click "Preview Replacements" to see what will be changed
   - Click "Apply Replacements" to save changes to new files
   - **Important**: Original files are never modified - all replacements are saved to new timestamped files
   - You can chain multiple search & replace operations by loading output files from previous operations

6. **Grammar Check & Tone Adjustments Tab**:
   - **File Selection & Processing Settings**:
     - Configure API settings (endpoint, key, model) - settings are saved automatically
     - Use "Test Connection" to verify API connectivity
     - Select files (Crowdin and/or Term Customizer files) to check
     - Select language to check
     - Configure batch size and temperature for LLM processing
   
   - **Tone Adjustments**:
     - Choose tone adjustment: Keep original, Switch to formal (Sie-Form), or Switch to informal (Du-Form)
     - Tone adjustment is only available for German languages (de/de-CH)
   
   - **Process**:
     - Click "Initialize check and adjustments" to:
       - First perform grammar check on all selected entries
       - Then perform tone adjustment (if tone setting is not "keep")
     - Review results in the split pane:
       - **Left pane (Preview)**: Shows original and corrected text side-by-side
       - **Right pane (Statistics)**: Shows statistics about corrections:
         - Files processed
         - Grammar corrections count
         - Tone adjustments count
         - Per-file statistics
   
   - **Save**:
     - Click "Save" to save corrected entries to new timestamped files
     - **Important**: Original files are never modified - all corrections are saved to new timestamped files

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

