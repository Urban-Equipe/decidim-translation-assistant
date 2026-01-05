"""
Decidim Translation Customizer GUI

Copyright (C) 2024 Urban-Equipe

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter.font import Font
import xml.etree.ElementTree as ET
import os
import json


class ToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, 'bbox') else (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.tipwindow = tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"), wraplength=300)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


def create_tooltip(widget, text):
    """Helper function to create a tooltip"""
    return ToolTip(widget, text)


class DecidimTranslationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Decidim Translation Customizer")
        self.root.geometry("1400x900")
        
        # Data storage
        self.crowdin_file_path = None
        self.term_customizer_files = []  # List of file paths
        self.crowdin_data = {}
        self.term_customizer_data = {}  # Combined data from all files
        self.term_customizer_file_data = {}  # Data per file: {file_path: {key: {locale: value}}}
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}  # {file_path: {key: entry}}
        self.xliff_source_language = 'en'
        self.xliff_target_language = ''
        self.term_customizer_locales = set()
        self.keys_to_delete = []  # Keys that exist only in Term Customizer
        
        # Config file path
        self.config_file = os.path.join(os.path.expanduser("~"), ".decidim_translation_customizer.json")
        
        # Load saved configuration
        self.load_config()
        
        # Create UI
        self.create_widgets()
        
        # Auto-load Crowdin file if available
        if self.crowdin_file_path and os.path.exists(self.crowdin_file_path):
            self.crowdin_label.config(text=f"Loaded: {os.path.basename(self.crowdin_file_path)}")
            self.load_crowdin_file()
        
    def create_widgets(self):
        # Top frame for file uploads and settings
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        # File upload section
        upload_frame = ttk.LabelFrame(top_frame, text="File Upload", padding="10")
        upload_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(upload_frame, text="Upload Crowdin File", 
                  command=self.upload_crowdin_file).pack(side=tk.LEFT, padx=5)
        self.crowdin_label = ttk.Label(upload_frame, text="No file selected")
        self.crowdin_label.pack(side=tk.LEFT, padx=10)
        
        ttk.Button(upload_frame, text="Add Term Customizer File(s)", 
                  command=self.add_term_customizer_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(upload_frame, text="Clear Term Customizer Files", 
                  command=self.clear_term_customizer_files).pack(side=tk.LEFT, padx=5)
        
        # Listbox for term customizer files
        term_files_frame = ttk.Frame(upload_frame)
        term_files_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        ttk.Label(term_files_frame, text="Term Customizer Files:").pack(anchor=tk.W)
        self.term_customizer_listbox = tk.Listbox(term_files_frame, height=3)
        self.term_customizer_listbox.pack(fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(term_files_frame, orient=tk.VERTICAL, command=self.term_customizer_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.term_customizer_listbox.config(yscrollcommand=scrollbar.set)
        
        # Settings section
        settings_frame = ttk.LabelFrame(top_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Info display row
        info_row = ttk.Frame(settings_frame)
        info_row.pack(fill=tk.X, pady=2)
        
        self.locale_info_label = ttk.Label(info_row, text="Load files to see detected locales", 
                                           foreground="gray")
        self.locale_info_label.pack(side=tk.LEFT, padx=5)
        create_tooltip(self.locale_info_label, "Shows the detected languages from the XLIFF file (source and target) and the locales found in Term Customizer files. Only matching locales will be compared.")
        
        # Conditional logic settings row
        logic_row = ttk.Frame(settings_frame)
        logic_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(logic_row, text="Comparison Logic:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        
        # Require term customizer value to exist
        self.require_term_value_var = tk.BooleanVar(value=True)
        require_check = ttk.Checkbutton(logic_row, text="Require Term Customizer Value", 
                       variable=self.require_term_value_var)
        require_check.pack(side=tk.LEFT, padx=5)
        create_tooltip(require_check, "If enabled, only entries where Term Customizer has a value will be checked. If disabled, entries with empty values will also be compared.")
        
        # Include empty values in comparison
        self.include_empty_var = tk.BooleanVar(value=False)
        include_check = ttk.Checkbutton(logic_row, text="Include Empty Values", 
                       variable=self.include_empty_var)
        include_check.pack(side=tk.LEFT, padx=5)
        create_tooltip(include_check, "If enabled, empty values will be included in comparisons. If disabled, empty values are ignored and won't trigger mismatches.")
        
        # Case sensitive comparison
        self.case_sensitive_var = tk.BooleanVar(value=True)
        case_check = ttk.Checkbutton(logic_row, text="Case Sensitive", 
                       variable=self.case_sensitive_var)
        case_check.pack(side=tk.LEFT, padx=5)
        create_tooltip(case_check, "If enabled, comparisons are case-sensitive (e.g., 'Hello' ≠ 'hello'). If disabled, case differences are ignored.")
        
        # Save settings row
        save_row = ttk.Frame(settings_frame)
        save_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(save_row, text="Save Options:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        
        self.save_mode_var = tk.StringVar(value="individual")
        individual_radio = ttk.Radiobutton(save_row, text="Save Individual Files", 
                       variable=self.save_mode_var, value="individual")
        individual_radio.pack(side=tk.LEFT, padx=5)
        create_tooltip(individual_radio, "Save each Term Customizer file separately with its mismatches. Output files are saved in the same directory as source files.")
        
        merge_radio = ttk.Radiobutton(save_row, text="Merge All Files", 
                       variable=self.save_mode_var, value="merge")
        merge_radio.pack(side=tk.LEFT, padx=5)
        create_tooltip(merge_radio, "Combine all mismatches from all files into a single output file. You'll be asked to select a directory for the merged file.")
        
        suffix_label = ttk.Label(save_row, text="Output Suffix:")
        suffix_label.pack(side=tk.LEFT, padx=(20, 5))
        create_tooltip(suffix_label, "Optional suffix to add to output filenames. An underscore will be added automatically if not present. Example: '_updated' creates 'filename_updated.csv'")
        
        self.output_suffix_var = tk.StringVar(value="")
        suffix_entry = ttk.Entry(save_row, textvariable=self.output_suffix_var, width=20)
        suffix_entry.pack(side=tk.LEFT, padx=5)
        
        # Action buttons row
        button_row = ttk.Frame(settings_frame)
        button_row.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_row, text="Compare Files", 
                  command=self.compare_files).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_row, text="Save Results", 
                  command=self.save_results).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_row, text="Export Deleted Keys", 
                  command=self.export_deleted_keys).pack(side=tk.LEFT, padx=5)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Diff View Tab
        self.diff_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.diff_frame, text="Diff View")
        self.create_diff_view()
        
        # Edit View Tab
        self.edit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.edit_frame, text="Edit Translations")
        self.create_edit_view()
        
        # Statistics Tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistics")
        self.create_statistics_view()
        
    def create_diff_view(self):
        # Create a scrolled text widget for diff display
        diff_container = ttk.Frame(self.diff_frame)
        diff_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.diff_text = scrolledtext.ScrolledText(diff_container, wrap=tk.NONE, 
                                                   font=Font(family="Courier", size=10))
        self.diff_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for diff highlighting
        self.diff_text.tag_config("added", foreground="green", background="#e6ffe6")
        self.diff_text.tag_config("removed", foreground="red", background="#ffe6e6")
        self.diff_text.tag_config("header", foreground="blue", font=Font(family="Courier", size=10, weight="bold"))
        
    def create_edit_view(self):
        # Create a frame with treeview for editing
        edit_container = ttk.Frame(self.edit_frame)
        edit_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(edit_container)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        
        # Treeview
        columns = ("key", "locale", "crowdin_value", "term_customizer_value", "current_value")
        self.edit_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                                     yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.edit_tree.yview)
        hsb.config(command=self.edit_tree.xview)
        
        # Configure columns
        self.edit_tree.heading("key", text="Key")
        self.edit_tree.heading("locale", text="Locale")
        self.edit_tree.heading("crowdin_value", text="Crowdin Value")
        self.edit_tree.heading("term_customizer_value", text="Term Customizer Value")
        self.edit_tree.heading("current_value", text="Current Value (Editable)")
        
        self.edit_tree.column("key", width=200)
        self.edit_tree.column("locale", width=80)
        self.edit_tree.column("crowdin_value", width=300)
        self.edit_tree.column("term_customizer_value", width=300)
        self.edit_tree.column("current_value", width=300)
        
        # Grid layout
        self.edit_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click to edit
        self.edit_tree.bind("<Double-1>", self.on_item_double_click)
        
        # Store editable values
        self.editable_values = {}
        
    def create_statistics_view(self):
        """Create the statistics overview tab"""
        stats_container = ttk.Frame(self.stats_frame)
        stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a scrolled text widget for statistics display
        self.stats_text = scrolledtext.ScrolledText(stats_container, wrap=tk.WORD, 
                                                    font=Font(family="Arial", size=11))
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for statistics highlighting
        self.stats_text.tag_config("header", font=Font(family="Arial", size=12, weight="bold"), foreground="navy")
        self.stats_text.tag_config("subheader", font=Font(family="Arial", size=11, weight="bold"), foreground="darkblue")
        self.stats_text.tag_config("number", font=Font(family="Arial", size=11, weight="bold"), foreground="darkgreen")
        self.stats_text.tag_config("warning", foreground="orange")
        self.stats_text.tag_config("error", foreground="red")
        
    def calculate_statistics(self):
        """Calculate comparison statistics"""
        stats = {
            'total_crowdin_keys': len(self.crowdin_data),
            'total_term_customizer_keys': 0,
            'keys_in_both': 0,
            'keys_only_in_crowdin': 0,
            'keys_only_in_term_customizer': 0,
            'mismatched_keys': len(self.mismatched_entries),
            'matching_keys': 0,
            'total_locales_compared': len(self.term_customizer_locales),
            'per_file_stats': {}
        }
        
        # Get all unique keys from term customizer
        all_term_keys = set()
        for file_path, file_data in self.term_customizer_file_data.items():
            all_term_keys.update(file_data.keys())
        
        stats['total_term_customizer_keys'] = len(all_term_keys)
        
        # Calculate keys in both
        crowdin_keys = set(self.crowdin_data.keys())
        stats['keys_in_both'] = len(crowdin_keys & all_term_keys)
        stats['keys_only_in_crowdin'] = len(crowdin_keys - all_term_keys)
        keys_only_in_term = all_term_keys - crowdin_keys
        stats['keys_only_in_term_customizer'] = len(keys_only_in_term)
        
        # Store keys to delete (keys only in Term Customizer)
        self.keys_to_delete = sorted(list(keys_only_in_term))
        
        # Calculate matching keys (in both but no mismatches)
        keys_in_both = set(self.crowdin_data.keys()) & all_term_keys
        stats['matching_keys'] = max(0, len(keys_in_both) - stats['mismatched_keys'])
        
        # Per-file statistics
        for file_path in self.term_customizer_files:
            file_data = self.term_customizer_file_data.get(file_path, {})
            file_mismatches = self.mismatched_entries_per_file.get(file_path, {})
            file_keys = set(file_data.keys())
            
            keys_in_crowdin = len(file_keys & set(self.crowdin_data.keys()))
            file_stats = {
                'total_keys': len(file_keys),
                'keys_in_crowdin': keys_in_crowdin,
                'keys_only_in_file': len(file_keys - set(self.crowdin_data.keys())),
                'mismatched_keys': len(file_mismatches),
                'matching_keys': max(0, keys_in_crowdin - len(file_mismatches))
            }
            stats['per_file_stats'][os.path.basename(file_path)] = file_stats
        
        return stats
    
    def update_statistics_view(self):
        """Update the statistics display"""
        self.stats_text.delete(1.0, tk.END)
        
        if not self.crowdin_data or not self.term_customizer_data:
            self.stats_text.insert(tk.END, "Please load and compare files to see statistics.\n")
            return
        
        stats = self.calculate_statistics()
        
        # Overall statistics
        self.stats_text.insert(tk.END, "OVERALL STATISTICS\n", "header")
        self.stats_text.insert(tk.END, "=" * 80 + "\n\n")
        
        self.stats_text.insert(tk.END, "Crowdin (XLIFF) File:\n", "subheader")
        self.stats_text.insert(tk.END, f"  Total keys: {stats['total_crowdin_keys']}\n")
        self.stats_text.insert(tk.END, f"  Source language: {self.xliff_source_language}\n")
        self.stats_text.insert(tk.END, f"  Target language: {self.xliff_target_language}\n\n")
        
        self.stats_text.insert(tk.END, "Term Customizer Files:\n", "subheader")
        self.stats_text.insert(tk.END, f"  Total files: {len(self.term_customizer_files)}\n")
        self.stats_text.insert(tk.END, f"  Total unique keys: {stats['total_term_customizer_keys']}\n")
        self.stats_text.insert(tk.END, f"  Locales compared: {', '.join(sorted(self.term_customizer_locales))}\n\n")
        
        self.stats_text.insert(tk.END, "Comparison Results:\n", "subheader")
        self.stats_text.insert(tk.END, f"  Keys in both files: ", "subheader")
        self.stats_text.insert(tk.END, f"{stats['keys_in_both']}\n", "number")
        
        self.stats_text.insert(tk.END, f"  ✓ Matching (no changes needed): ", "subheader")
        self.stats_text.insert(tk.END, f"{stats['matching_keys']}\n", "number")
        
        self.stats_text.insert(tk.END, f"  ✗ Mismatched (need review): ", "subheader")
        self.stats_text.insert(tk.END, f"{stats['mismatched_keys']}\n", "number")
        
        self.stats_text.insert(tk.END, f"  ⚠ Keys only in Crowdin: ", "subheader")
        self.stats_text.insert(tk.END, f"{stats['keys_only_in_crowdin']}\n", "warning")
        self.stats_text.insert(tk.END, "    (These keys exist in Crowdin but not in Term Customizer)\n")
        
        self.stats_text.insert(tk.END, f"  ⚠ Keys only in Term Customizer: ", "subheader")
        self.stats_text.insert(tk.END, f"{stats['keys_only_in_term_customizer']}\n", "warning")
        if stats['keys_only_in_term_customizer'] > 0:
            self.stats_text.insert(tk.END, "    ⚠ These keys exist in Term Customizer but not in Crowdin.\n", "warning")
            self.stats_text.insert(tk.END, "    They will be removed from the output files.\n\n", "warning")
        else:
            self.stats_text.insert(tk.END, "    (No keys to remove)\n\n")
        
        # Per-file statistics
        if len(self.term_customizer_files) > 1:
            self.stats_text.insert(tk.END, "PER-FILE STATISTICS\n", "header")
            self.stats_text.insert(tk.END, "=" * 80 + "\n\n")
            
            for filename, file_stats in stats['per_file_stats'].items():
                self.stats_text.insert(tk.END, f"File: {filename}\n", "subheader")
                self.stats_text.insert(tk.END, f"  Total keys: {file_stats['total_keys']}\n")
                self.stats_text.insert(tk.END, f"  Keys in Crowdin: {file_stats['keys_in_crowdin']}\n")
                self.stats_text.insert(tk.END, f"  Keys only in this file: {file_stats['keys_only_in_file']}\n")
                self.stats_text.insert(tk.END, f"  Matching: {file_stats['matching_keys']}\n")
                self.stats_text.insert(tk.END, f"  Mismatched: {file_stats['mismatched_keys']}\n\n")
        
        # Summary
        self.stats_text.insert(tk.END, "SUMMARY\n", "header")
        self.stats_text.insert(tk.END, "=" * 80 + "\n\n")
        
        total_entries = stats['mismatched_keys'] + stats['matching_keys']
        if total_entries > 0:
            match_percentage = (stats['matching_keys'] / total_entries) * 100
            mismatch_percentage = (stats['mismatched_keys'] / total_entries) * 100
            
            self.stats_text.insert(tk.END, f"Match rate: {match_percentage:.1f}% ({stats['matching_keys']} of {total_entries} keys)\n")
            self.stats_text.insert(tk.END, f"Mismatch rate: {mismatch_percentage:.1f}% ({stats['mismatched_keys']} of {total_entries} keys)\n")
        
        if stats['keys_only_in_term_customizer'] > 0:
            self.stats_text.insert(tk.END, f"\n⚠ Warning: {stats['keys_only_in_term_customizer']} keys will be removed as they don't exist in Crowdin.\n", "warning")
        
    def load_config(self):
        """Load saved configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'crowdin_file_path' in config and os.path.exists(config['crowdin_file_path']):
                        self.crowdin_file_path = config['crowdin_file_path']
        except Exception as e:
            # If config file is corrupted, just ignore it
            pass
    
    def save_config(self):
        """Save configuration"""
        try:
            config = {
                'crowdin_file_path': self.crowdin_file_path
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            # Silently fail if we can't save config
            pass
    
    def upload_crowdin_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Crowdin File (CSV or XLIFF)",
            filetypes=[("XLIFF files", "*.xliff"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.crowdin_file_path = file_path
            self.crowdin_label.config(text=f"Loaded: {file_path.split('/')[-1]}")
            self.load_crowdin_file()
            # Save config after loading
            self.save_config()
            
    def add_term_customizer_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Term Customizer CSV File(s)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_paths:
            for file_path in file_paths:
                if file_path not in self.term_customizer_files:
                    self.term_customizer_files.append(file_path)
                    self.term_customizer_listbox.insert(tk.END, os.path.basename(file_path))
                    self.load_term_customizer_file(file_path)
            self.update_locale_info()
    
    def clear_term_customizer_files(self):
        self.term_customizer_files = []
        self.term_customizer_data = {}
        self.term_customizer_file_data = {}
        self.term_customizer_locales = set()
        self.term_customizer_listbox.delete(0, tk.END)
        self.update_locale_info()
        messagebox.showinfo("Cleared", "All Term Customizer files have been cleared")
            
    def load_xliff_file(self, file_path):
        """Parse XLIFF file and extract translation data"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Get namespace from root element (XLIFF uses default namespace)
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'
            
            # Helper function to create namespaced tag
            def ns_tag(tag):
                return f'{namespace}{tag}' if namespace else tag
            
            # Get source and target languages from file element
            file_elem = root.find(f'.//{ns_tag("file")}')
            
            source_lang = 'en'
            target_lang = ''
            
            if file_elem is not None:
                source_lang = file_elem.get('source-language', 'en').lower()
                target_lang = file_elem.get('target-language', '').lower()
            
            # Store language info
            self.xliff_source_language = source_lang
            self.xliff_target_language = target_lang
            
            data = {}
            
            # Find all trans-unit elements
            trans_units = root.findall(f'.//{ns_tag("trans-unit")}')
            
            for trans_unit in trans_units:
                # Get the key from resname attribute
                key = trans_unit.get('resname', '')
                if not key:
                    continue
                
                # Get source text
                source_elem = trans_unit.find(ns_tag('source'))
                source_text = source_elem.text if source_elem is not None and source_elem.text else ''
                
                # Get target text
                target_elem = trans_unit.find(ns_tag('target'))
                target_text = target_elem.text if target_elem is not None and target_elem.text else ''
                
                data[key] = {
                    'target': target_text,
                    'source': source_text
                }
            
            return data, len(data)
            
        except ET.ParseError as e:
            raise Exception(f"XML parsing error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing XLIFF file: {str(e)}")
    
    def load_crowdin_file(self):
        if not self.crowdin_file_path:
            return
            
        try:
            self.crowdin_data = {}
            file_ext = os.path.splitext(self.crowdin_file_path)[1].lower()
            
            if file_ext == '.xliff':
                # Load XLIFF file
                self.crowdin_data, count = self.load_xliff_file(self.crowdin_file_path)
                info_text = f"XLIFF: {count} entries (source: {self.xliff_source_language}, target: {self.xliff_target_language})"
                self.update_locale_info()
                messagebox.showinfo("Success", f"Loaded {count} entries from XLIFF file\nSource: {self.xliff_source_language}, Target: {self.xliff_target_language}")
            else:
                messagebox.showerror("Error", "Only XLIFF files are supported for Crowdin files")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading Crowdin file: {str(e)}")
            
    def load_term_customizer_file(self, file_path):
        """Load a single Term Customizer file"""
        try:
            file_data = {}
            file_locales = set()
            
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';')
                for row in reader:
                    key = row.get('key', '')
                    value = row.get('value', '')
                    locale = row.get('locale', '').lower()
                    if key and locale:
                        if key not in file_data:
                            file_data[key] = {}
                        file_data[key][locale] = value
                        file_locales.add(locale)
                        # Also add to combined data
                        if key not in self.term_customizer_data:
                            self.term_customizer_data[key] = {}
                        self.term_customizer_data[key][locale] = value
                        self.term_customizer_locales.add(locale)
            
            # Store per-file data
            self.term_customizer_file_data[file_path] = file_data
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading Term Customizer file {os.path.basename(file_path)}: {str(e)}")
    
    def update_locale_info(self):
        """Update the locale info label"""
        info_parts = []
        
        if self.xliff_source_language or self.xliff_target_language:
            xliff_info = f"XLIFF: source={self.xliff_source_language}"
            if self.xliff_target_language:
                xliff_info += f", target={self.xliff_target_language}"
            info_parts.append(xliff_info)
        
        if self.term_customizer_locales:
            locales_str = ', '.join(sorted(self.term_customizer_locales))
            info_parts.append(f"Term Customizer locales: {locales_str}")
        
        if info_parts:
            self.locale_info_label.config(text=" | ".join(info_parts), foreground="black")
        else:
            self.locale_info_label.config(text="Load files to see detected locales", foreground="gray")
            
    def compare_files(self):
        # Get conditional logic settings
        require_term_value = self.require_term_value_var.get()
        include_empty = self.include_empty_var.get()
        case_sensitive = self.case_sensitive_var.get()
        
        # Reload files if needed
        if not self.crowdin_data and self.crowdin_file_path:
            self.load_crowdin_file()
        
        if not self.term_customizer_files:
            messagebox.showwarning("Warning", "Please add at least one Term Customizer file first")
            return
            
        if not self.crowdin_data:
            messagebox.showwarning("Warning", "Please upload Crowdin file first")
            return
        
        # Validate locale matching
        unmatched_locales = []
        for locale in self.term_customizer_locales:
            locale_lower = locale.lower()
            if locale_lower != self.xliff_source_language.lower() and locale_lower != self.xliff_target_language.lower():
                unmatched_locales.append(locale)
        
        if unmatched_locales:
            messagebox.showerror("Error", 
                f"Locale mismatch detected!\n\n"
                f"Term Customizer locales: {', '.join(sorted(self.term_customizer_locales))}\n"
                f"XLIFF source language: {self.xliff_source_language}\n"
                f"XLIFF target language: {self.xliff_target_language}\n\n"
                f"The following locales don't match: {', '.join(unmatched_locales)}\n"
                f"Only matching locales can be compared.")
            return
            
        # Find mismatches using configured conditional logic
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}
        
        # Calculate keys to delete (keys only in Term Customizer, not in Crowdin)
        all_term_keys = set()
        for file_path, file_data in self.term_customizer_file_data.items():
            all_term_keys.update(file_data.keys())
        crowdin_keys = set(self.crowdin_data.keys())
        keys_only_in_term = all_term_keys - crowdin_keys
        self.keys_to_delete = sorted(list(keys_only_in_term))
        
        def normalize_value(value):
            """Normalize value based on case sensitivity setting"""
            if not case_sensitive:
                return value.strip().lower() if value else ''
            return value.strip() if value else ''
        
        def values_differ(val1, val2):
            """Compare two values based on settings"""
            # If include_empty is False, skip comparison if either value is empty
            if not include_empty:
                if not val1 or not val2:
                    return False
            # Compare normalized values
            return normalize_value(val1) != normalize_value(val2)
        
        def should_check_value(term_value, require_value):
            """Determine if we should check this value based on require_term_value setting"""
            if require_value:
                # Only check if term customizer value exists
                return bool(term_value)
            else:
                # Check regardless of whether term customizer value exists
                return True
        
        # Compare for each file separately
        for file_path in self.term_customizer_files:
            file_data = self.term_customizer_file_data.get(file_path, {})
            file_mismatches = {}
            
            # Compare for each matching locale
            for key, term_data in file_data.items():
                if key not in self.crowdin_data:
                    continue
                
                crowdin_entry = self.crowdin_data[key]
                entry_mismatches = {}
                
                # Check each locale in this file
                for locale in term_data.keys():
                    locale_lower = locale.lower()
                    term_value = term_data.get(locale, '') or ''
                    
                    # Determine which XLIFF value to compare with
                    if locale_lower == self.xliff_source_language.lower():
                        # English (or source language): use XLIFF source
                        xliff_value = crowdin_entry['source'] or ''
                    elif locale_lower == self.xliff_target_language.lower():
                        # Target language: use XLIFF target
                        xliff_value = crowdin_entry['target'] or ''
                    else:
                        # Should not happen due to validation above, but skip just in case
                        continue
                    
                    # Check for mismatch
                    if should_check_value(term_value, require_term_value):
                        if values_differ(term_value, xliff_value):
                            entry_mismatches[locale] = {
                                'term_value': term_value,
                                'xliff_value': xliff_value
                            }
                
                # Add to mismatched entries if any locale has a mismatch
                if entry_mismatches:
                    if key not in file_mismatches:
                        file_mismatches[key] = {
                            'crowdin_source': crowdin_entry['source'] or '',
                            'crowdin_target': crowdin_entry['target'] or '',
                            'term_values': {}
                        }
                    # Store mismatches for each locale
                    for locale, mismatch_data in entry_mismatches.items():
                        file_mismatches[key]['term_values'][locale] = mismatch_data['term_value']
                    
                    # Also add to combined mismatches
                    if key not in self.mismatched_entries:
                        self.mismatched_entries[key] = {
                            'crowdin_source': crowdin_entry['source'] or '',
                            'crowdin_target': crowdin_entry['target'] or '',
                            'term_values': {}
                        }
                    for locale, mismatch_data in entry_mismatches.items():
                        self.mismatched_entries[key]['term_values'][locale] = mismatch_data['term_value']
            
            # Store per-file mismatches
            self.mismatched_entries_per_file[file_path] = file_mismatches
                    
        # Update diff view
        self.update_diff_view()
        
        # Update edit view
        self.update_edit_view()
        
        # Update statistics view
        self.update_statistics_view()
        
        total_mismatches = sum(len(m) for m in self.mismatched_entries_per_file.values())
        stats = self.calculate_statistics()
        messagebox.showinfo("Comparison Complete", 
                          f"Found {total_mismatches} mismatched entries across {len(self.term_customizer_files)} file(s)\n\n"
                          f"Statistics:\n"
                          f"  Matching: {stats['matching_keys']}\n"
                          f"  Mismatched: {stats['mismatched_keys']}\n"
                          f"  Keys only in Term Customizer: {stats['keys_only_in_term_customizer']}")
        
    def update_diff_view(self):
        self.diff_text.delete(1.0, tk.END)
        
        if not self.mismatched_entries:
            self.diff_text.insert(tk.END, "No mismatches found. Files are in sync.\n")
            return
            
        for key, entry in sorted(self.mismatched_entries.items()):
            # Header
            self.diff_text.insert(tk.END, f"\n{'='*80}\n", "header")
            self.diff_text.insert(tk.END, f"Key: {key}\n", "header")
            self.diff_text.insert(tk.END, f"{'='*80}\n\n", "header")
            
            # Show diff for each locale with mismatch
            for locale in sorted(entry['term_values'].keys()):
                locale_lower = locale.lower()
                term_value = entry['term_values'][locale]
                
                # Determine which XLIFF value to show
                if locale_lower == self.xliff_source_language.lower():
                    xliff_value = entry['crowdin_source']
                    xliff_label = "XLIFF (source)"
                elif locale_lower == self.xliff_target_language.lower():
                    xliff_value = entry['crowdin_target']
                    xliff_label = "XLIFF (target)"
                else:
                    continue
                
                self.diff_text.insert(tk.END, f"Locale ({locale}):\n")
                self.diff_text.insert(tk.END, f"  {xliff_label}:  {xliff_value}\n", "removed")
                self.diff_text.insert(tk.END, f"  Customizer:     {term_value}\n", "added")
                self.diff_text.insert(tk.END, "\n")
                
    def update_edit_view(self):
        # Clear existing items
        for item in self.edit_tree.get_children():
            self.edit_tree.delete(item)
            
        self.editable_values = {}
        
        # Add mismatched entries
        for key, entry in sorted(self.mismatched_entries.items()):
            # Add row for each locale with mismatch
            for locale in sorted(entry['term_values'].keys()):
                locale_lower = locale.lower()
                term_value = entry['term_values'][locale]
                
                # Determine which XLIFF value to show
                if locale_lower == self.xliff_source_language.lower():
                    xliff_value = entry['crowdin_source']
                elif locale_lower == self.xliff_target_language.lower():
                    xliff_value = entry['crowdin_target']
                else:
                    continue
                
                item_id = f"{key}_{locale}"
                self.edit_tree.insert("", tk.END, iid=item_id, values=(
                    key,
                    locale,
                    xliff_value,
                    term_value,
                    term_value  # Start with term customizer value
                ))
                self.editable_values[item_id] = term_value
                
    def on_item_double_click(self, event):
        item = self.edit_tree.selection()[0] if self.edit_tree.selection() else None
        if not item:
            return
            
        # Get current value
        current_values = self.edit_tree.item(item, "values")
        current_value = current_values[4] if len(current_values) > 4 else ""
        
        # Create edit dialog
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("Edit Translation")
        edit_dialog.geometry("600x300")
        
        ttk.Label(edit_dialog, text=f"Key: {current_values[0]}", font=Font(weight="bold")).pack(pady=5)
        ttk.Label(edit_dialog, text=f"Locale: {current_values[1]}").pack()
        
        ttk.Label(edit_dialog, text="Current Value:").pack(anchor=tk.W, padx=20, pady=(10, 5))
        text_widget = scrolledtext.ScrolledText(edit_dialog, height=8, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        text_widget.insert(1.0, current_value)
        text_widget.focus()
        
        def save_edit():
            new_value = text_widget.get(1.0, tk.END).strip()
            # Update tree
            values = list(current_values)
            values[4] = new_value
            self.edit_tree.item(item, values=values)
            # Update stored value
            self.editable_values[item] = new_value
            edit_dialog.destroy()
            
        ttk.Button(edit_dialog, text="Save", command=save_edit).pack(pady=10)
        ttk.Button(edit_dialog, text="Cancel", command=edit_dialog.destroy).pack()
        
    def save_results(self):
        if not self.mismatched_entries_per_file:
            messagebox.showwarning("Warning", "No data to save. Please compare files first.")
            return
        
        save_mode = self.save_mode_var.get()
        suffix = self.output_suffix_var.get().strip()
        if suffix and not suffix.startswith('_'):
            suffix = '_' + suffix
        
        try:
            if save_mode == "individual":
                # Save each file individually
                saved_files = []
                for file_path in self.term_customizer_files:
                    file_mismatches = self.mismatched_entries_per_file.get(file_path, {})
                    if not file_mismatches:
                        continue
                    
                    # Get base name and directory
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
                    
                    # Create output filename
                    output_filename = f"{base_name}{suffix}.csv"
                    output_path = os.path.join(directory, output_filename)
                    
                    # Get edited values for this file
                    output_rows = []
                    for key, entry in file_mismatches.items():
                        for locale in entry['term_values'].keys():
                            item_id = f"{key}_{locale}"
                            # Get edited value if available, otherwise use original
                            edited_value = self.editable_values.get(item_id, entry['term_values'][locale])
                            output_rows.append({
                                'locale': locale,
                                'key': key,
                                'value': edited_value
                            })
                    
                    # Write to file
                    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
                        fieldnames = ['locale', 'key', 'value']
                        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
                        writer.writeheader()
                        writer.writerows(output_rows)
                    
                    saved_files.append(output_path)
                
                if saved_files:
                    files_list = '\n'.join([os.path.basename(f) for f in saved_files])
                    messagebox.showinfo("Success", f"Saved {len(saved_files)} file(s):\n{files_list}")
                else:
                    messagebox.showinfo("Info", "No mismatches found to save.")
                    
            else:  # merge
                # Merge all files into one
                directory = filedialog.askdirectory(title="Select directory to save merged file")
                if not directory:
                    return
                
                # Get all edited values
                all_output_rows = []
                seen_keys = set()
                
                for file_path in self.term_customizer_files:
                    file_mismatches = self.mismatched_entries_per_file.get(file_path, {})
                    for key, entry in file_mismatches.items():
                        for locale in entry['term_values'].keys():
                            item_key = (key, locale)
                            if item_key not in seen_keys:
                                item_id = f"{key}_{locale}"
                                edited_value = self.editable_values.get(item_id, entry['term_values'][locale])
                                all_output_rows.append({
                                    'locale': locale,
                                    'key': key,
                                    'value': edited_value
                                })
                                seen_keys.add(item_key)
                
                # Create output filename
                output_filename = f"merged{suffix}.csv"
                output_path = os.path.join(directory, output_filename)
                
                # Write to file
                with open(output_path, mode='w', newline='', encoding='utf-8') as file:
                    fieldnames = ['locale', 'key', 'value']
                    writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
                    writer.writeheader()
                    writer.writerows(all_output_rows)
                
                messagebox.showinfo("Success", f"Merged results saved to:\n{output_path}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Error saving file: {str(e)}")
    
    def export_deleted_keys(self):
        """Export keys that will be deleted (exist only in Term Customizer)"""
        if not self.keys_to_delete:
            messagebox.showinfo("Info", "No keys to delete. All keys in Term Customizer files exist in Crowdin.")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Deleted Keys",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Collect all entries for keys to delete
            output_rows = []
            for key in self.keys_to_delete:
                # Get all locales for this key from all files
                for file_path, file_data in self.term_customizer_file_data.items():
                    if key in file_data:
                        for locale, value in file_data[key].items():
                            output_rows.append({
                                'key': key,
                                'locale': locale,
                                'value': value
                            })
            
            # Write to file
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                fieldnames = ['key', 'locale', 'value']
                writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                writer.writerows(output_rows)
            
            messagebox.showinfo("Success", 
                              f"Exported {len(self.keys_to_delete)} keys to delete\n"
                              f"Total entries: {len(output_rows)}\n"
                              f"Saved to: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error exporting deleted keys: {str(e)}")


def main():
    root = tk.Tk()
    app = DecidimTranslationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

