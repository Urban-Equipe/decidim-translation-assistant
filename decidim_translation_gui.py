"""
Decidim Translation Assistant

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
import os
import json
import re
from datetime import datetime
import urllib.request
import urllib.error

# Import modules (lazy import for heavy modules)
from config_manager import ConfigManager
from file_handlers import FileHandler
from comparison_logic import ComparisonLogic
from search_replace import SearchReplaceHandler

# Lazy import for grammar_tone (only when needed)
_grammar_tone_handler = None

def get_grammar_tone_handler():
    """Lazy load grammar_tone module"""
    global _grammar_tone_handler
    if _grammar_tone_handler is None:
        from grammar_tone import GrammarToneHandler
        _grammar_tone_handler = GrammarToneHandler
    return _grammar_tone_handler


class DecidimTranslationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Decidim Translation Assistant")
        self.root.geometry("1400x900")
        
        # Data storage
        self.crowdin_files = []  # List of XLIFF file paths
        self.term_customizer_files = []  # List of file paths
        self.crowdin_file_data = {}  # Data per XLIFF file: {file_path: {key: {'source': value, 'target': value}}}
        self.crowdin_languages = {}  # Languages per XLIFF file: {file_path: {'source': 'en', 'target': 'de'}}
        self.term_customizer_data = {}  # Combined data from all files
        self.term_customizer_file_data = {}  # Data per file: {file_path: {key: {locale: value}}}
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}  # {file_path: {key: entry}}
        self.term_customizer_locales = set()
        self.keys_to_delete = []  # Keys that exist only in Term Customizer
        
        # Initialize config manager
        self.config_manager = ConfigManager()
        
        # Initialize handlers
        self.file_handler = FileHandler()
        self.comparison_logic = ComparisonLogic()
        self.search_replace_handler = SearchReplaceHandler()
        
        # API settings (will be loaded from config)
        self.api_endpoint = 'https://api.openai.com/v1/chat/completions'
        self.api_key = ''
        self.api_model = 'gpt-4o-mini'
        
        # Grammar check and tone adjustment data
        self.grammar_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.tone_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.gc_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for grammar check
        
        # Cache for language lists to avoid repeated expensive operations
        self._sr_languages_cache = None
        self._sr_languages_cache_valid = False
        self._gc_languages_cache = None
        self._gc_languages_cache_valid = False
        
        # Load saved configuration
        self.config_manager.load()
        self.crowdin_files = self.config_manager.crowdin_file_paths.copy()
        self.api_endpoint = self.config_manager.api_endpoint
        self.api_key = self.config_manager.api_key
        self.api_model = self.config_manager.api_model
        
        # Create UI
        self.create_widgets()
        
        # Auto-load Crowdin files if available
        for file_path in self.crowdin_files:
            if os.path.exists(file_path):
                self.load_crowdin_file(file_path)
        
    def create_widgets(self):
        # File upload section at the top (always visible)
        upload_frame = ttk.LabelFrame(self.root, text="Load Files to Compare", padding="10")
        upload_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Buttons row
        buttons_row = ttk.Frame(upload_frame)
        buttons_row.pack(fill=tk.X, pady=5)
        
        ttk.Button(buttons_row, text="Add Crowdin/XLIFF File(s)", 
                  command=self.upload_crowdin_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row, text="Remove Selected XLIFF", 
                  command=self.remove_selected_crowdin_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row, text="Add Term Customizer File(s)", 
                  command=self.add_term_customizer_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_row, text="Clear Term Customizer Files", 
                  command=self.clear_term_customizer_files).pack(side=tk.LEFT, padx=5)
        
        # Files display row
        files_row = ttk.Frame(upload_frame)
        files_row.pack(fill=tk.X, pady=5)
        
        # XLIFF files listbox
        xliff_files_frame = ttk.Frame(files_row)
        xliff_files_frame.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        ttk.Label(xliff_files_frame, text="Crowdin/XLIFF Files:").pack(anchor=tk.W)
        xliff_listbox_frame = ttk.Frame(xliff_files_frame)
        xliff_listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.crowdin_listbox = tk.Listbox(xliff_listbox_frame, height=3)
        self.crowdin_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        xliff_scrollbar = ttk.Scrollbar(xliff_listbox_frame, orient=tk.VERTICAL, command=self.crowdin_listbox.yview)
        xliff_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.crowdin_listbox.config(yscrollcommand=xliff_scrollbar.set)
        
        # Term Customizer files listbox
        term_files_frame = ttk.Frame(files_row)
        term_files_frame.pack(side=tk.LEFT, padx=10, fill=tk.BOTH, expand=True)
        ttk.Label(term_files_frame, text="Term Customizer Files:").pack(anchor=tk.W)
        term_listbox_frame = ttk.Frame(term_files_frame)
        term_listbox_frame.pack(fill=tk.BOTH, expand=True)
        self.term_customizer_listbox = tk.Listbox(term_listbox_frame, height=3)
        self.term_customizer_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        term_scrollbar = ttk.Scrollbar(term_listbox_frame, orient=tk.VERTICAL, command=self.term_customizer_listbox.yview)
        term_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.term_customizer_listbox.config(yscrollcommand=term_scrollbar.set)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Track which tabs have been initialized (lazy loading)
        self.tabs_initialized = {
            'compare': False,
            'edit': False,
            'search_replace': False,
            'grammar': False
        }
        
        # Bind tab change event for lazy initialization
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # Compare Tab (main tab with file loading, settings, diff, and statistics)
        self.compare_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.compare_frame, text="Compare")
        self.create_compare_view()
        self.tabs_initialized['compare'] = True
        
        # Edit View Tab
        self.edit_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.edit_frame, text="Edit Translations")
        self.create_edit_view()
        self.tabs_initialized['edit'] = True
        
        # Search & Replace Tab (lazy load)
        self.search_replace_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.search_replace_frame, text="Search & Replace")
        # Don't create view yet - will be created on first access
        
        # Grammar Check & Tone Adjustments Tab (lazy load)
        self.grammar_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.grammar_frame, text="Grammar check & tone adjustments")
        # Don't create view yet - will be created on first access
    
    def create_compare_view(self):
        """Create the Compare tab with settings, diff view, and statistics"""
        # Main container with scrolling
        main_container = ttk.Frame(self.compare_frame, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Settings section
        settings_frame = ttk.LabelFrame(main_container, text="Comparison Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Info display row
        info_row = ttk.Frame(settings_frame)
        info_row.pack(fill=tk.X, pady=2)
        
        self.locale_info_label = ttk.Label(info_row, text="Load files to see detected locales", 
                                           foreground="gray")
        self.locale_info_label.pack(side=tk.LEFT, padx=5)
        
        # Conditional logic settings row
        logic_row = ttk.Frame(settings_frame)
        logic_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(logic_row, text="Comparison Logic:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        
        # Require term customizer value to exist
        self.require_term_value_var = tk.BooleanVar(value=True)
        require_check = ttk.Checkbutton(logic_row, text="Require Term Customizer Value", 
                       variable=self.require_term_value_var)
        require_check.pack(side=tk.LEFT, padx=5)
        
        # Include empty values in comparison
        self.include_empty_var = tk.BooleanVar(value=False)
        include_check = ttk.Checkbutton(logic_row, text="Include Empty Values", 
                       variable=self.include_empty_var)
        include_check.pack(side=tk.LEFT, padx=5)
        
        # Case sensitive comparison
        self.case_sensitive_var = tk.BooleanVar(value=True)
        case_check = ttk.Checkbutton(logic_row, text="Case Sensitive", 
                       variable=self.case_sensitive_var)
        case_check.pack(side=tk.LEFT, padx=5)
        
        # Save settings row
        save_row = ttk.Frame(settings_frame)
        save_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(save_row, text="Save Options:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        
        self.save_mode_var = tk.StringVar(value="individual")
        individual_radio = ttk.Radiobutton(save_row, text="Save Individual Files", 
                       variable=self.save_mode_var, value="individual")
        individual_radio.pack(side=tk.LEFT, padx=5)
        
        merge_radio = ttk.Radiobutton(save_row, text="Merge All Files", 
                       variable=self.save_mode_var, value="merge")
        merge_radio.pack(side=tk.LEFT, padx=5)
        
        suffix_label = ttk.Label(save_row, text="Output Suffix:")
        suffix_label.pack(side=tk.LEFT, padx=(20, 5))
        
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
        
        # Paned window for diff view and statistics
        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left pane: Diff View
        diff_container = ttk.LabelFrame(paned, text="Diff View", padding="5")
        paned.add(diff_container, weight=1)
        
        self.diff_text = scrolledtext.ScrolledText(diff_container, wrap=tk.NONE, 
                                                   font=Font(family="Courier", size=10))
        self.diff_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for diff highlighting
        self.diff_text.tag_config("added", foreground="green", background="#e6ffe6")
        self.diff_text.tag_config("removed", foreground="red", background="#ffe6e6")
        self.diff_text.tag_config("header", foreground="blue", font=Font(family="Courier", size=10, weight="bold"))
        self.diff_text.config(state=tk.DISABLED)
        
        # Right pane: Statistics
        stats_container = ttk.LabelFrame(paned, text="Statistics", padding="5")
        paned.add(stats_container, weight=1)
        
        self.stats_text = scrolledtext.ScrolledText(stats_container, wrap=tk.WORD, 
                                                    font=Font(family="Arial", size=11))
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for statistics highlighting
        self.stats_text.tag_config("header", font=Font(family="Arial", size=12, weight="bold"), foreground="navy")
        self.stats_text.tag_config("subheader", font=Font(family="Arial", size=11, weight="bold"), foreground="darkblue")
        self.stats_text.tag_config("number", font=Font(family="Arial", size=11, weight="bold"), foreground="darkgreen")
        self.stats_text.tag_config("warning", foreground="orange")
        self.stats_text.tag_config("error", foreground="red")
        self.stats_text.config(state=tk.DISABLED)
    
    def on_tab_changed(self, event=None):
        """Handle tab change event for lazy loading"""
        try:
            selected_tab = self.notebook.index(self.notebook.select())
            tab_names = ['compare', 'edit', 'search_replace', 'grammar']
            
            if selected_tab < len(tab_names):
                tab_name = tab_names[selected_tab]
                
                # Lazy initialize Search & Replace tab
                if tab_name == 'search_replace' and not self.tabs_initialized['search_replace']:
                    self.create_search_replace_view()
                    self.tabs_initialized['search_replace'] = True
                
                # Lazy initialize Grammar Check tab
                elif tab_name == 'grammar' and not self.tabs_initialized['grammar']:
                    self.create_grammar_check_view()
                    self.tabs_initialized['grammar'] = True
        except:
            pass  # Ignore errors during tab switching
        
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
        
    def calculate_statistics(self):
        """Calculate comparison statistics"""
        # Build combined Crowdin data from all XLIFF files
        combined_crowdin_data = {}
        all_xliff_sources = set()
        all_xliff_targets = set()
        for file_path, file_data in self.crowdin_file_data.items():
            langs = self.crowdin_languages[file_path]
            if langs['source']:
                all_xliff_sources.add(langs['source'])
            if langs['target']:
                all_xliff_targets.add(langs['target'])
            for key, entry in file_data.items():
                if key not in combined_crowdin_data:
                    combined_crowdin_data[key] = {
                        'source': entry.get('source', '') or '',
                        'target': entry.get('target', '') or ''
                    }
                # Merge values (prefer non-empty values)
                if entry.get('source') and not combined_crowdin_data[key]['source']:
                    combined_crowdin_data[key]['source'] = entry.get('source', '') or ''
                if entry.get('target') and not combined_crowdin_data[key]['target']:
                    combined_crowdin_data[key]['target'] = entry.get('target', '') or ''
        
        # Use first source/target for compatibility (or combine them)
        xliff_source = ', '.join(sorted(all_xliff_sources)) if all_xliff_sources else ''
        xliff_target = ', '.join(sorted(all_xliff_targets)) if all_xliff_targets else ''
        
        stats = self.comparison_logic.calculate_statistics(
            combined_crowdin_data, self.term_customizer_file_data, self.mismatched_entries,
            self.mismatched_entries_per_file, self.term_customizer_files,
            xliff_source, xliff_target, self.term_customizer_locales
        )
        # Store keys to delete (keys only in Term Customizer)
        all_term_keys = set()
        for file_path, file_data in self.term_customizer_file_data.items():
            all_term_keys.update(file_data.keys())
        crowdin_keys = set(combined_crowdin_data.keys())
        keys_only_in_term = all_term_keys - crowdin_keys
        self.keys_to_delete = sorted(list(keys_only_in_term))
        return stats
    
    def update_statistics_view(self):
        """Update the statistics display"""
        # Disable updates for better performance
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        
        if not self.crowdin_files or not self.term_customizer_data:
            self.stats_text.insert(tk.END, "Please load and compare files to see statistics.\n")
            self.stats_text.config(state=tk.DISABLED)
            return
        
        stats = self.calculate_statistics()
        
        # Build content in memory first
        content_parts = []
        
        # Overall statistics
        content_parts.append(("OVERALL STATISTICS\n", "header"))
        content_parts.append(("=" * 80 + "\n\n", None))
        
        content_parts.append(("Crowdin (XLIFF) File:\n", "subheader"))
        content_parts.append((f"  Total keys: {stats['total_crowdin_keys']}\n", None))
        content_parts.append((f"  Source language: {self.xliff_source_language}\n", None))
        content_parts.append((f"  Target language: {self.xliff_target_language}\n\n", None))
        
        content_parts.append(("Term Customizer Files:\n", "subheader"))
        content_parts.append((f"  Total files: {len(self.term_customizer_files)}\n", None))
        content_parts.append((f"  Total unique keys: {stats['total_term_customizer_keys']}\n", None))
        content_parts.append((f"  Locales compared: {', '.join(sorted(self.term_customizer_locales))}\n\n", None))
        
        content_parts.append(("Comparison Results:\n", "subheader"))
        content_parts.append((f"  Keys in both files: ", "subheader"))
        content_parts.append((f"{stats['keys_in_both']}\n", "number"))
        
        content_parts.append((f"  ✓ Matching (no changes needed): ", "subheader"))
        content_parts.append((f"{stats['matching_keys']}\n", "number"))
        
        content_parts.append((f"  ✗ Mismatched (need review): ", "subheader"))
        content_parts.append((f"{stats['mismatched_keys']}\n", "number"))
        
        content_parts.append((f"  ⚠ Keys only in Crowdin: ", "subheader"))
        content_parts.append((f"{stats['keys_only_in_crowdin']}\n", "warning"))
        content_parts.append(("    (These keys exist in Crowdin but not in Term Customizer)\n", None))
        
        content_parts.append((f"  ⚠ Keys only in Term Customizer: ", "subheader"))
        content_parts.append((f"{stats['keys_only_in_term_customizer']}\n", "warning"))
        if stats['keys_only_in_term_customizer'] > 0:
            content_parts.append(("    ⚠ These keys exist in Term Customizer but not in Crowdin.\n", "warning"))
            content_parts.append(("    They will be removed from the output files.\n\n", "warning"))
        else:
            content_parts.append(("    (No keys to remove)\n\n", None))
        
        # Per-file statistics
        if len(self.term_customizer_files) > 1:
            content_parts.append(("PER-FILE STATISTICS\n", "header"))
            content_parts.append(("=" * 80 + "\n\n", None))
            
            for filename, file_stats in stats['per_file_stats'].items():
                content_parts.append((f"File: {filename}\n", "subheader"))
                content_parts.append((f"  Total keys: {file_stats['total_keys']}\n", None))
                content_parts.append((f"  Keys in Crowdin: {file_stats['keys_in_crowdin']}\n", None))
                content_parts.append((f"  Keys only in this file: {file_stats['keys_only_in_file']}\n", None))
                content_parts.append((f"  Matching: {file_stats['matching_keys']}\n", None))
                content_parts.append((f"  Mismatched: {file_stats['mismatched_keys']}\n\n", None))
        
        # Summary
        content_parts.append(("SUMMARY\n", "header"))
        content_parts.append(("=" * 80 + "\n\n", None))
        
        total_entries = stats['mismatched_keys'] + stats['matching_keys']
        if total_entries > 0:
            match_percentage = (stats['matching_keys'] / total_entries) * 100
            mismatch_percentage = (stats['mismatched_keys'] / total_entries) * 100
            
            content_parts.append((f"Match rate: {match_percentage:.1f}% ({stats['matching_keys']} of {total_entries} keys)\n", None))
            content_parts.append((f"Mismatch rate: {mismatch_percentage:.1f}% ({stats['mismatched_keys']} of {total_entries} keys)\n", None))
        
        if stats['keys_only_in_term_customizer'] > 0:
            content_parts.append((f"\n⚠ Warning: {stats['keys_only_in_term_customizer']} keys will be removed as they don't exist in Crowdin.\n", "warning"))
        
        # Insert all content at once
        for text, tag in content_parts:
            if tag:
                self.stats_text.insert(tk.END, text, tag)
            else:
                self.stats_text.insert(tk.END, text)
        
        self.stats_text.config(state=tk.DISABLED)
    
    def create_search_replace_view(self):
        """Create the search and replace tab"""
        container = ttk.Frame(self.search_replace_frame)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section: File selection and search/replace inputs
        top_section = ttk.LabelFrame(container, text="Search & Replace Configuration", padding="10")
        top_section.pack(fill=tk.X, pady=5)
        
        # File selection frame
        file_selection_frame = ttk.Frame(top_section)
        file_selection_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_selection_frame, text="Select Files:", font=Font(weight="bold")).pack(anchor=tk.W)
        
        file_checkboxes_frame = ttk.Frame(file_selection_frame)
        file_checkboxes_frame.pack(fill=tk.X, pady=5)
        
        # XLIFF files checkboxes (will be populated dynamically)
        ttk.Label(file_checkboxes_frame, text="XLIFF Files:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        self.sr_crowdin_file_vars = {}  # {file_path: BooleanVar}
        self.sr_crowdin_checkboxes_frame = ttk.Frame(file_checkboxes_frame)
        self.sr_crowdin_checkboxes_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Term Customizer files checkboxes (will be populated dynamically)
        ttk.Label(file_checkboxes_frame, text="Term Customizer Files:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        self.sr_term_file_vars = {}  # {file_path: BooleanVar}
        self.sr_term_checkboxes_frame = ttk.Frame(file_checkboxes_frame)
        self.sr_term_checkboxes_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Search and Replace inputs
        search_replace_inputs = ttk.Frame(top_section)
        search_replace_inputs.pack(fill=tk.X, pady=10)
        
        ttk.Label(search_replace_inputs, text="Search for:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.search_term_var = tk.StringVar(value="")
        search_entry = ttk.Entry(search_replace_inputs, textvariable=self.search_term_var, width=40)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        ttk.Label(search_replace_inputs, text="Replace with:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.replace_term_var = tk.StringVar(value="")
        replace_entry = ttk.Entry(search_replace_inputs, textvariable=self.replace_term_var, width=40)
        replace_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        
        search_replace_inputs.columnconfigure(1, weight=1)
        
        # Language selection
        language_frame = ttk.Frame(top_section)
        language_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(language_frame, text="Language:").pack(side=tk.LEFT, padx=5)
        self.sr_language_var = tk.StringVar(value="")
        self.sr_language_combo = ttk.Combobox(language_frame, textvariable=self.sr_language_var, 
                                             state="readonly", width=20)
        self.sr_language_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(language_frame, text="(Auto-detected from selected files)").pack(side=tk.LEFT, padx=5)
        
        # Options
        options_frame = ttk.Frame(top_section)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.sr_case_sensitive_var = tk.BooleanVar(value=False)
        case_check = ttk.Checkbutton(options_frame, text="Case Sensitive", 
                                   variable=self.sr_case_sensitive_var)
        case_check.pack(side=tk.LEFT, padx=5)
        
        self.sr_whole_word_var = tk.BooleanVar(value=False)
        whole_word_check = ttk.Checkbutton(options_frame, text="Whole Word Only", 
                                          variable=self.sr_whole_word_var)
        whole_word_check.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(top_section)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Preview Replacements", 
                  command=self.preview_replacements).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply Replacements", 
                  command=self.apply_replacements).pack(side=tk.LEFT, padx=5)
        
        # Preview section
        preview_section = ttk.LabelFrame(container, text="Preview", padding="10")
        preview_section.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_text = scrolledtext.ScrolledText(preview_section, wrap=tk.WORD, 
                                                      font=Font(family="Courier", size=10),
                                                      height=15)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure preview text tags
        self.preview_text.tag_config("match", background="#ffff99", foreground="black")
        self.preview_text.tag_config("replacement", background="#99ff99", foreground="black")
        self.preview_text.tag_config("header", font=Font(weight="bold"), foreground="navy")
        
        # Initialize replacement data storage
        self.replacement_preview = {}  # {file_path: {key: {locale: {'old': value, 'new': value}}}}
        self._sr_update_scheduled = None  # For debouncing language updates
        self.sr_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for search/replace
        self.last_sr_output_files = []  # List of most recently created output files for easy reloading
        
        # Cache for language lists to avoid repeated expensive operations
        self._sr_languages_cache = None
        self._sr_languages_cache_valid = False
        
        # Initialize file selection lazily (only when tab is accessed)
        # Don't call update functions here - they'll be called when needed
        self.root.after_idle(self.update_sr_file_selection)
        
    def update_sr_file_selection(self):
        """Update the file selection checkboxes for XLIFF and Term Customizer files"""
        # Only update if frames exist
        if not hasattr(self, 'sr_crowdin_checkboxes_frame') or not hasattr(self, 'sr_term_checkboxes_frame'):
            return
        
        # Clear existing XLIFF checkboxes
        for widget in list(self.sr_crowdin_checkboxes_frame.winfo_children()):
            widget.destroy()
        self.sr_crowdin_file_vars = {}
        
        # Add checkboxes for each XLIFF file
        for file_path in self.crowdin_files:
            var = tk.BooleanVar(value=False)
            self.sr_crowdin_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_sr_xliff_check_callback(fp):
                def callback():
                    self._sr_languages_cache_valid = False  # Invalidate cache
                    self.update_sr_languages()
                return callback
            check = ttk.Checkbutton(self.sr_crowdin_checkboxes_frame, text=filename, variable=var,
                                   command=make_sr_xliff_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
        
        # Clear existing Term Customizer checkboxes
        for widget in list(self.sr_term_checkboxes_frame.winfo_children()):
            widget.destroy()
        self.sr_term_file_vars = {}
        
        # Add checkboxes for each Term Customizer file
        for file_path in self.term_customizer_files:
            var = tk.BooleanVar(value=False)
            self.sr_term_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_sr_check_callback(fp):
                def callback():
                    self._sr_languages_cache_valid = False  # Invalidate cache
                    self.update_sr_languages()
                return callback
            check = ttk.Checkbutton(self.sr_term_checkboxes_frame, text=filename, variable=var,
                                   command=make_sr_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
        
        # Add checkboxes for directly loaded files (for search/replace only)
        for file_path in self.sr_direct_files.keys():
            var = tk.BooleanVar(value=False)
            self.sr_term_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_sr_direct_check_callback(fp):
                def callback():
                    self._sr_languages_cache_valid = False  # Invalidate cache
                    self.update_sr_languages()
                return callback
            check = ttk.Checkbutton(self.sr_term_checkboxes_frame, text=f"{filename} (direct)", variable=var,
                                   command=make_sr_direct_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
        
        self.update_sr_languages()
    
    def update_sr_languages(self):
        """Update available languages based on selected files - optimized with debouncing"""
        if not hasattr(self, 'sr_language_combo'):
            return
        
        # Cancel any pending update
        if self._sr_update_scheduled:
            try:
                self.root.after_cancel(self._sr_update_scheduled)
            except:
                pass
        
        # Schedule update with small delay to debounce rapid checkbox clicks
        self._sr_update_scheduled = self.root.after(50, self._do_update_sr_languages)
    
    def _do_update_sr_languages(self):
        """Actually perform the language update - optimized with caching"""
        self._sr_update_scheduled = None
        
        if not hasattr(self, 'sr_language_combo'):
            return
        
        # Use cache if available and valid
        if self._sr_languages_cache_valid and self._sr_languages_cache is not None:
            sorted_languages = self._sr_languages_cache
        else:
            languages = set()
            
            # Check XLIFF files
            for file_path, var in self.sr_crowdin_file_vars.items():
                if var.get() and file_path in self.crowdin_languages:
                    langs = self.crowdin_languages[file_path]
                    if langs['source']:
                        languages.add(langs['source'])
                    if langs['target']:
                        languages.add(langs['target'])
            
            # Check Term Customizer files (only if selected)
            selected_files = set()
            for file_path, var in self.sr_term_file_vars.items():
                if var.get():
                    selected_files.add(file_path)
            
            # Only check selected files to speed things up
            files_to_check = selected_files if selected_files else (set(self.term_customizer_file_data.keys()) | set(self.sr_direct_files.keys()))
            
            for file_path in files_to_check:
                file_data = self.term_customizer_file_data.get(file_path) or self.sr_direct_files.get(file_path)
                if file_data:
                    # More efficient: collect locales in one pass
                    for key_data in file_data.values():
                        if isinstance(key_data, dict):
                            languages.update(key_data.keys())
            
            sorted_languages = sorted(languages)
            # Cache the result
            self._sr_languages_cache = sorted_languages
            self._sr_languages_cache_valid = True
        
        # Only update if values changed
        current_values = self.sr_language_combo['values']
        if tuple(sorted_languages) != tuple(current_values):
            self.sr_language_combo['values'] = sorted_languages
            # Only set default if current value is not in new list
            if sorted_languages:
                current_val = self.sr_language_var.get()
                if not current_val or current_val not in sorted_languages:
                    self.sr_language_var.set(sorted_languages[0])
        
    def preview_replacements(self):
        """Preview what will be replaced"""
        search_term = self.search_term_var.get().strip()
        replace_term = self.replace_term_var.get().strip()
        language = self.sr_language_var.get()
        
        if not search_term:
            messagebox.showwarning("Warning", "Please enter a search term.")
            return
        
        if not language:
            messagebox.showwarning("Warning", "Please select a language.")
            return
        
        self.replacement_preview = {}
        total_replacements = 0
        
        # Clear preview
        self.preview_text.delete(1.0, tk.END)
        
        # Process XLIFF files
        for file_path, var in self.sr_crowdin_file_vars.items():
            if var.get() and file_path in self.crowdin_file_data:
                file_data = self.crowdin_file_data[file_path]
                langs = self.crowdin_languages[file_path]
                xliff_replacements = {}
                
                for key, entry in file_data.items():
                    # Determine which value to check based on language
                    value = None
                    if language.lower() == langs['source'].lower():
                        value = entry.get('source', '') or ''
                    elif language.lower() == langs['target'].lower():
                        value = entry.get('target', '') or ''
                    else:
                        continue
                    
                    if value and self._should_replace(value, search_term):
                        new_value = self._replace_text(value, search_term, replace_term)
                        if new_value != value:
                            xliff_replacements[key] = {
                                language: {'old': value, 'new': new_value}
                            }
                            total_replacements += 1
                
                if xliff_replacements:
                    self.replacement_preview[file_path] = xliff_replacements
        
        # Process Term Customizer files
        for file_path, var in self.sr_term_file_vars.items():
            if var.get():
                # Check if it's a directly loaded file or a regular Term Customizer file
                file_data = self.sr_direct_files.get(file_path) or self.term_customizer_file_data.get(file_path, {})
                file_replacements = {}
                
                for key, locales in file_data.items():
                    if language in locales:
                        value = locales[language]
                        if value and self._should_replace(value, search_term):
                            new_value = self._replace_text(value, search_term, replace_term)
                            if new_value != value:
                                if key not in file_replacements:
                                    file_replacements[key] = {}
                                file_replacements[key][language] = {'old': value, 'new': new_value}
                                total_replacements += 1
                
                if file_replacements:
                    self.replacement_preview[file_path] = file_replacements
        
        # Display preview
        if not self.replacement_preview:
            self.preview_text.insert(tk.END, "No replacements found.\n")
            return
        
        self.preview_text.insert(tk.END, f"Found {total_replacements} replacement(s) in {len(self.replacement_preview)} file(s)\n\n", "header")
        
        for file_path, replacements in self.replacement_preview.items():
            filename = os.path.basename(file_path)
            self.preview_text.insert(tk.END, f"File: {filename}\n", "header")
            self.preview_text.insert(tk.END, "=" * 80 + "\n\n")
            
            for key, locales in sorted(replacements.items()):
                self.preview_text.insert(tk.END, f"Key: {key}\n")
                for loc, changes in locales.items():
                    self.preview_text.insert(tk.END, f"  [{loc}] ", "header")
                    self.preview_text.insert(tk.END, "Old: ", "header")
                    self.preview_text.insert(tk.END, f"{changes['old']}\n", "match")
                    self.preview_text.insert(tk.END, f"      New: ", "header")
                    self.preview_text.insert(tk.END, f"{changes['new']}\n", "replacement")
                self.preview_text.insert(tk.END, "\n")
    
    def _should_replace(self, text, search_term):
        """Check if text should be replaced based on options"""
        case_sensitive = self.sr_case_sensitive_var.get()
        whole_word = self.sr_whole_word_var.get()
        return self.search_replace_handler.should_replace(text, search_term, case_sensitive, whole_word)
    
    def _replace_text(self, text, search_term, replace_term):
        """Replace text based on options"""
        case_sensitive = self.sr_case_sensitive_var.get()
        whole_word = self.sr_whole_word_var.get()
        return self.search_replace_handler.replace_text(text, search_term, replace_term, case_sensitive, whole_word)
    
    def apply_replacements(self):
        """Apply the replacements and save to new files"""
        if not self.replacement_preview:
            messagebox.showwarning("Warning", "Please preview replacements first.")
            return
        
        # Confirm action
        total_replacements = sum(len(locales) for replacements in self.replacement_preview.values() 
                                for locales in replacements.values())
        if not messagebox.askyesno("Confirm", 
                                  f"Save {total_replacements} replacement(s) to new file(s)?\n\n"
                                  "This will create new output files. Original files will not be modified."):
            return
        
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Save XLIFF file replacements (as CSV)
            for file_path in self.crowdin_files:
                if file_path in self.replacement_preview:
                    directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    output_filename = f"{base_name}_replaced_{timestamp}.csv"
                    output_path = os.path.join(directory, output_filename)
                    
                    # Ensure unique filename
                    counter = 1
                    original_path = output_path
                    while os.path.exists(output_path):
                        base, ext = os.path.splitext(original_path)
                        output_path = f"{base}_{counter}{ext}"
                        counter += 1
                    
                    output_rows = []
                    for key, locales in self.replacement_preview[file_path].items():
                        for locale, changes in locales.items():
                            output_rows.append({
                                'locale': locale,
                                'key': key,
                                'value': changes['new']
                            })
                    
                    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
                        fieldnames = ['locale', 'key', 'value']
                        writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
                        writer.writeheader()
                        writer.writerows(output_rows)
                    
                    saved_files.append(output_path)
            
            # Save Term Customizer file replacements
            for file_path, replacements in self.replacement_preview.items():
                if file_path in self.crowdin_files:
                    continue
                
                directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_filename = f"{base_name}_replaced_{timestamp}.csv"
                output_path = os.path.join(directory, output_filename)
                
                # Ensure unique filename
                counter = 1
                original_path = output_path
                while os.path.exists(output_path):
                    base, ext = os.path.splitext(original_path)
                    output_path = f"{base}_{counter}{ext}"
                    counter += 1
                
                output_rows = []
                for key, locales in replacements.items():
                    for locale, changes in locales.items():
                        output_rows.append({
                            'locale': locale,
                            'key': key,
                            'value': changes['new']
                        })
                
                with open(output_path, mode='w', newline='', encoding='utf-8') as file:
                    fieldnames = ['locale', 'key', 'value']
                    writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
                    writer.writeheader()
                    writer.writerows(output_rows)
                
                saved_files.append(output_path)
                # Track for easy reloading
                self.last_sr_output_files.append(output_path)
                # Keep only last 10 files
                if len(self.last_sr_output_files) > 10:
                    self.last_sr_output_files.pop(0)
            
            if saved_files:
                files_list = '\n'.join([os.path.basename(f) for f in saved_files])
                messagebox.showinfo("Success", 
                                  f"Saved {len(saved_files)} file(s) with replacements:\n\n{files_list}\n\n"
                                  "Original files were not modified.\n\n"
                                  "Tip: Use 'Load File for Search & Replace' to load these files for further operations.")
            else:
                messagebox.showinfo("Info", "No files were saved.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error saving replacement files: {str(e)}")
        
        # Clear preview
        self.replacement_preview = {}
        self.preview_text.delete(1.0, tk.END)
    
    def create_grammar_check_view(self):
        """Create the grammar check and tone adjustment tab"""
        container = ttk.Frame(self.grammar_frame, padding="10")
        container.pack(fill=tk.BOTH, expand=True)
        
        # File Selection & Processing Settings box
        settings_box = ttk.LabelFrame(container, text="File Selection & Processing Settings", padding="10")
        settings_box.pack(fill=tk.X, pady=5)
        
        # API Configuration
        api_frame = ttk.Frame(settings_box)
        api_frame.pack(fill=tk.X, pady=5)
        
        # API Endpoint
        endpoint_frame = ttk.Frame(api_frame)
        endpoint_frame.pack(fill=tk.X, pady=2)
        ttk.Label(endpoint_frame, text="API Endpoint:").pack(side=tk.LEFT, padx=5)
        self.gc_api_endpoint_var = tk.StringVar(value=getattr(self, 'api_endpoint', 'https://api.openai.com/v1/chat/completions'))
        endpoint_entry = ttk.Entry(endpoint_frame, textvariable=self.gc_api_endpoint_var, width=50)
        endpoint_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # API Key
        key_frame = ttk.Frame(api_frame)
        key_frame.pack(fill=tk.X, pady=2)
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT, padx=5)
        self.gc_api_key_var = tk.StringVar(value=getattr(self, 'api_key', ''))
        key_entry = ttk.Entry(key_frame, textvariable=self.gc_api_key_var, width=50, show="*")
        key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Model
        model_frame = ttk.Frame(api_frame)
        model_frame.pack(fill=tk.X, pady=2)
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT, padx=5)
        model_value = getattr(self, 'api_model', 'gpt-4o-mini')
        self.gc_model_var = tk.StringVar(value=model_value)
        model_entry = ttk.Entry(model_frame, textvariable=self.gc_model_var, width=50)
        model_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # API settings buttons
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(pady=5)
        ttk.Button(api_buttons_frame, text="Save API Settings", 
                  command=self.save_api_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons_frame, text="Test Connection", 
                  command=self.test_llm_connection).pack(side=tk.LEFT, padx=5)
        
        # File selection
        file_selection_frame = ttk.Frame(settings_box)
        file_selection_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_selection_frame, text="Select Files:", font=Font(weight="bold")).pack(anchor=tk.W)
        
        file_checkboxes_frame = ttk.Frame(file_selection_frame)
        file_checkboxes_frame.pack(fill=tk.X, pady=5)
        
        # XLIFF files checkboxes (will be populated dynamically)
        ttk.Label(file_checkboxes_frame, text="XLIFF Files:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        self.gc_crowdin_file_vars = {}  # {file_path: BooleanVar}
        self.gc_crowdin_checkboxes_frame = ttk.Frame(file_checkboxes_frame)
        self.gc_crowdin_checkboxes_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Term Customizer files checkboxes (will be populated dynamically)
        ttk.Label(file_checkboxes_frame, text="Term Customizer Files:", font=Font(weight="bold")).pack(side=tk.LEFT, padx=5)
        self.gc_term_file_vars = {}  # {file_path: BooleanVar}
        self.gc_term_checkboxes_frame = ttk.Frame(file_checkboxes_frame)
        self.gc_term_checkboxes_frame.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Language and processing options
        options_row = ttk.Frame(settings_box)
        options_row.pack(fill=tk.X, pady=5)
        
        # Language selection
        language_frame = ttk.Frame(options_row)
        language_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(language_frame, text="Language:").pack(side=tk.LEFT, padx=5)
        self.gc_language_var = tk.StringVar(value="")
        self.gc_language_combo = ttk.Combobox(language_frame, textvariable=self.gc_language_var, 
                                             state="readonly", width=20)
        self.gc_language_combo.pack(side=tk.LEFT, padx=5)
        
        # Batch Size
        batch_frame = ttk.Frame(options_row)
        batch_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(batch_frame, text="Batch Size:").pack(side=tk.LEFT, padx=5)
        self.gc_batch_size_var = tk.IntVar(value=10)
        batch_spin = ttk.Spinbox(batch_frame, from_=1, to=50, textvariable=self.gc_batch_size_var, width=10)
        batch_spin.pack(side=tk.LEFT, padx=5)
        
        # Temperature
        temp_frame = ttk.Frame(options_row)
        temp_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT, padx=5)
        self.gc_temperature_var = tk.DoubleVar(value=0.1)
        temp_spin = ttk.Spinbox(temp_frame, from_=0.0, to=0.2, increment=0.1, 
                               textvariable=self.gc_temperature_var, width=10, format="%.1f")
        temp_spin.pack(side=tk.LEFT, padx=5)
        
        # Tone adjustment section
        tone_section = ttk.LabelFrame(container, text="Tone Adjustments", padding="10")
        tone_section.pack(fill=tk.X, pady=5)
        
        self.gc_tone_var = tk.StringVar(value="keep")
        tone_frame = ttk.Frame(tone_section)
        tone_frame.pack(fill=tk.X, pady=5)
        
        keep_radio = ttk.Radiobutton(tone_frame, text="Keep original tone", 
                                    variable=self.gc_tone_var, value="keep")
        keep_radio.pack(side=tk.LEFT, padx=10)
        
        formal_radio = ttk.Radiobutton(tone_frame, text="Switch to formal (Sie-Form)", 
                                      variable=self.gc_tone_var, value="formal")
        formal_radio.pack(side=tk.LEFT, padx=10)
        
        informal_radio = ttk.Radiobutton(tone_frame, text="Switch to informal (Du-Form)", 
                                        variable=self.gc_tone_var, value="informal")
        informal_radio.pack(side=tk.LEFT, padx=10)
        
        # Action buttons
        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Initialize check and adjustments", 
                  command=self.initialize_check_and_adjustments).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", 
                  command=self.save_grammar_corrections).pack(side=tk.LEFT, padx=5)
        
        # Paned window for preview and statistics
        paned = ttk.PanedWindow(container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left pane: Preview
        preview_container = ttk.LabelFrame(paned, text="Preview", padding="5")
        paned.add(preview_container, weight=1)
        
        self.grammar_preview_text = scrolledtext.ScrolledText(preview_container, wrap=tk.WORD, 
                                                             font=Font(family="Courier", size=10))
        self.grammar_preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure preview text tags
        self.grammar_preview_text.tag_config("original", background="#ffe6e6", foreground="black")
        self.grammar_preview_text.tag_config("corrected", background="#e6ffe6", foreground="black")
        self.grammar_preview_text.tag_config("header", font=Font(weight="bold"), foreground="navy")
        self.grammar_preview_text.tag_config("error", foreground="red")
        
        # Right pane: Statistics
        stats_container = ttk.LabelFrame(paned, text="Statistics", padding="5")
        paned.add(stats_container, weight=1)
        
        self.gc_stats_text = scrolledtext.ScrolledText(stats_container, wrap=tk.WORD, 
                                                       font=Font(family="Arial", size=11))
        self.gc_stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for statistics highlighting
        self.gc_stats_text.tag_config("header", font=Font(family="Arial", size=12, weight="bold"), foreground="navy")
        self.gc_stats_text.tag_config("subheader", font=Font(family="Arial", size=11, weight="bold"), foreground="darkblue")
        self.gc_stats_text.tag_config("number", font=Font(family="Arial", size=11, weight="bold"), foreground="darkgreen")
        self.gc_stats_text.tag_config("warning", foreground="orange")
        self.gc_stats_text.tag_config("error", foreground="red")
        self.gc_stats_text.config(state=tk.DISABLED)
        
        # Initialize grammar check and tone adjustment data
        self.grammar_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.tone_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self._gc_language_update_scheduled = None  # For debouncing language updates
        
        # Cache for language lists to avoid repeated expensive operations
        self._gc_languages_cache = None
        self._gc_languages_cache_valid = False
        
        # Initialize file selection lazily (only when tab is accessed)
        self.root.after_idle(self.update_gc_file_selection)
    
    def update_gc_file_selection(self):
        """Update the file selection checkboxes for XLIFF and Term Customizer files in grammar check"""
        if not hasattr(self, 'gc_crowdin_checkboxes_frame') or not hasattr(self, 'gc_term_checkboxes_frame'):
            return
        
        # Clear existing XLIFF checkboxes
        for widget in list(self.gc_crowdin_checkboxes_frame.winfo_children()):
            widget.destroy()
        self.gc_crowdin_file_vars = {}
        
        # Add checkboxes for each XLIFF file
        for file_path in self.crowdin_files:
            var = tk.BooleanVar(value=False)
            self.gc_crowdin_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_gc_xliff_check_callback(fp):
                def callback():
                    self._gc_languages_cache_valid = False  # Invalidate cache
                    self.update_gc_languages()
                return callback
            check = ttk.Checkbutton(self.gc_crowdin_checkboxes_frame, text=filename, variable=var,
                                   command=make_gc_xliff_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
        
        # Clear existing Term Customizer checkboxes
        for widget in list(self.gc_term_checkboxes_frame.winfo_children()):
            widget.destroy()
        self.gc_term_file_vars = {}
        
        # Add checkboxes for each Term Customizer file
        for file_path in self.term_customizer_files:
            var = tk.BooleanVar(value=False)
            self.gc_term_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_gc_check_callback(fp):
                def callback():
                    self._gc_languages_cache_valid = False  # Invalidate cache
                    self.update_gc_languages()
                return callback
            check = ttk.Checkbutton(self.gc_term_checkboxes_frame, text=filename, variable=var,
                                   command=make_gc_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
        
        # Add checkboxes for directly loaded files (for grammar check only)
        for file_path in self.gc_direct_files.keys():
            var = tk.BooleanVar(value=False)
            self.gc_term_file_vars[file_path] = var
            filename = os.path.basename(file_path)
            def make_gc_direct_check_callback(fp):
                def callback():
                    self._gc_languages_cache_valid = False  # Invalidate cache
                    self.update_gc_languages()
                return callback
            check = ttk.Checkbutton(self.gc_term_checkboxes_frame, text=f"{filename} (direct)", variable=var,
                                   command=make_gc_direct_check_callback(file_path))
            check.pack(side=tk.LEFT, padx=5)
    
    def load_file_for_grammar_check(self):
        """Load a CSV file directly for grammar checking"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File for Grammar Check",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Load the file
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
            
            # Store in direct files dictionary
            self.gc_direct_files[file_path] = file_data
            
            # Invalidate cache when new file is loaded
            self._gc_languages_cache_valid = False
            
            # Update file selection checkboxes (only if tab is initialized)
            if self.tabs_initialized.get('grammar', False):
                self.update_gc_file_selection()
                # Update languages
                self.update_gc_languages()
            
            messagebox.showinfo("Success", 
                              f"Loaded {len(file_data)} keys from {os.path.basename(file_path)}\n"
                              f"Locales: {', '.join(sorted(file_locales))}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def load_file_for_search_replace(self):
        """Load a CSV file directly for search and replace operations"""
        file_path = filedialog.askopenfilename(
            title="Select CSV File for Search & Replace",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Load the file
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
            
            # Store in direct files dictionary
            self.sr_direct_files[file_path] = file_data
            
            # Invalidate cache when new file is loaded
            self._sr_languages_cache_valid = False
            
            # Update file selection checkboxes (only if tab is initialized)
            if self.tabs_initialized.get('search_replace', False):
                self.update_sr_file_selection()
                # Update languages
                self.update_sr_languages()
            
            messagebox.showinfo("Success", 
                              f"Loaded {len(file_data)} keys from {os.path.basename(file_path)}\n"
                              f"Locales: {', '.join(sorted(file_locales))}\n\n"
                              "You can now use this file for search & replace operations.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
    
    def save_api_settings(self):
        """Save API settings to config"""
        self.api_endpoint = self.gc_api_endpoint_var.get().strip()
        self.api_key = self.gc_api_key_var.get().strip()
        self.api_model = self.gc_model_var.get().strip() or 'gpt-4o-mini'
        self.save_config()
        messagebox.showinfo("Success", "API settings saved successfully.")
    
    def test_llm_connection(self):
        """Test the LLM API connection with a simple request"""
        api_key = self.gc_api_key_var.get().strip()
        api_endpoint = self.gc_api_endpoint_var.get().strip()
        model = self.gc_model_var.get().strip() or 'gpt-4o-mini'
        
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key first.")
            return
        
        if not api_endpoint:
            messagebox.showerror("Error", "Please enter an API endpoint first.")
            return
        
        # Show testing message
        test_window = tk.Toplevel(self.root)
        test_window.title("Testing Connection")
        test_window.geometry("400x150")
        test_window.transient(self.root)
        test_window.grab_set()
        
        status_label = ttk.Label(test_window, text="Testing connection to LLM API...", font=Font(weight="bold"))
        status_label.pack(pady=20)
        
        result_text = scrolledtext.ScrolledText(test_window, height=4, wrap=tk.WORD, width=50)
        result_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        result_text.config(state=tk.DISABLED)
        
        def run_test():
            try:
                # Prepare a simple test request
                data = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": "Say 'Connection successful' if you can read this."}
                    ],
                    "temperature": 0.1,
                    "max_tokens": 20
                }
                
                req = urllib.request.Request(
                    api_endpoint,
                    data=json.dumps(data).encode('utf-8'),
                    headers={
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {api_key}'
                    }
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    
                    if 'choices' not in result or not result['choices']:
                        result_text.config(state=tk.NORMAL)
                        result_text.insert(tk.END, f"ERROR: Invalid API response\nResponse: {json.dumps(result, indent=2)}", "error")
                        result_text.config(state=tk.DISABLED)
                        status_label.config(text="Connection Failed", foreground="red")
                    else:
                        response_text = result['choices'][0]['message']['content'].strip()
                        result_text.config(state=tk.NORMAL)
                        result_text.insert(tk.END, f"SUCCESS: Connection working!\n\n")
                        result_text.insert(tk.END, f"Model: {model}\n")
                        result_text.insert(tk.END, f"Endpoint: {api_endpoint}\n")
                        result_text.insert(tk.END, f"Response: {response_text}")
                        result_text.config(state=tk.DISABLED)
                        status_label.config(text="Connection Successful!", foreground="green")
                        
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8')
                try:
                    error_json = json.loads(error_body)
                    error_obj = error_json.get('error', {})
                    
                    # Try different error formats
                    # OpenAI format: {"error": {"message": "...", "type": "...", "code": "..."}}
                    # Alternative format: {"result": "error", "error": {"code": "...", "description": "..."}}
                    error_message = (
                        error_obj.get('message') or 
                        error_obj.get('description') or 
                        error_obj.get('error') or
                        error_body
                    )
                    error_type = error_obj.get('type', 'API Error')
                    error_code = error_obj.get('code', str(e.code))
                    
                    # If error_code is still the HTTP code, try to get a more specific code
                    if error_code == str(e.code) and 'code' in error_obj:
                        error_code = error_obj['code']
                    
                except:
                    error_message = error_body
                    error_type = "HTTP Error"
                    error_code = str(e.code)
                
                result_text.config(state=tk.NORMAL)
                result_text.insert(tk.END, f"ERROR: {error_type} (Code: {error_code})\n\n", "error")
                result_text.insert(tk.END, f"Message: {error_message}\n\n", "error")
                result_text.insert(tk.END, f"Full response:\n{error_body}", "error")
                result_text.config(state=tk.DISABLED)
                status_label.config(text="Connection Failed", foreground="red")
                
            except urllib.error.URLError as e:
                result_text.config(state=tk.NORMAL)
                result_text.insert(tk.END, f"ERROR: Network error\n\n", "error")
                result_text.insert(tk.END, f"Details: {str(e)}\n\n", "error")
                result_text.insert(tk.END, "Please check:\n- Your internet connection\n- The API endpoint URL\n- Firewall/proxy settings", "error")
                result_text.config(state=tk.DISABLED)
                status_label.config(text="Connection Failed", foreground="red")
                
            except json.JSONDecodeError as e:
                result_text.config(state=tk.NORMAL)
                result_text.insert(tk.END, f"ERROR: Invalid JSON response\n\n", "error")
                result_text.insert(tk.END, f"Details: {str(e)}", "error")
                result_text.config(state=tk.DISABLED)
                status_label.config(text="Connection Failed", foreground="red")
                
            except Exception as e:
                result_text.config(state=tk.NORMAL)
                result_text.insert(tk.END, f"ERROR: Unexpected error\n\n", "error")
                result_text.insert(tk.END, f"Details: {str(e)}", "error")
                result_text.config(state=tk.DISABLED)
                status_label.config(text="Connection Failed", foreground="red")
            
            # Configure error tag
            result_text.tag_config("error", foreground="red")
            
            # Add close button
            close_btn = ttk.Button(test_window, text="Close", command=test_window.destroy)
            close_btn.pack(pady=5)
        
        # Run test in a separate thread-like operation (using after to avoid blocking)
        test_window.after(100, run_test)
    
    def update_gc_languages(self):
        """Update available languages for grammar checking - optimized with debouncing"""
        if not hasattr(self, 'gc_language_combo'):
            return
        
        # Cancel any pending update
        if self._gc_language_update_scheduled:
            try:
                self.root.after_cancel(self._gc_language_update_scheduled)
            except:
                pass
        
        # Schedule update with small delay to debounce rapid checkbox clicks
        self._gc_language_update_scheduled = self.root.after(100, self._do_update_gc_languages)
    
    def _do_update_gc_languages(self):
        """Actually perform the language update - optimized with caching"""
        self._gc_language_update_scheduled = None
        
        if not hasattr(self, 'gc_language_combo'):
            return
        
        # Use cache if available and valid (when no files are selected, use cached all-languages list)
        selected_files = set()
        if hasattr(self, 'gc_term_file_vars'):
            for file_path, var in self.gc_term_file_vars.items():
                if var.get():
                    selected_files.add(file_path)
        
        # If files are selected, we need to recalculate. Otherwise use cache if available
        if not selected_files and self._gc_languages_cache_valid and self._gc_languages_cache is not None:
            sorted_languages = self._gc_languages_cache
        else:
            languages = set()
            
            # Check XLIFF files
            for file_path, langs in self.crowdin_languages.items():
                if langs['source']:
                    languages.add(langs['source'])
                if langs['target']:
                    languages.add(langs['target'])
            
            # Check Term Customizer files (only if selected, or all if none selected for initial population)
            files_to_check = selected_files if selected_files else set(self.term_customizer_file_data.keys())
            
            for file_path in files_to_check:
                file_data = self.term_customizer_file_data.get(file_path)
                if file_data:
                    # More efficient: collect locales in one pass
                    for key_data in file_data.values():
                        if isinstance(key_data, dict):
                            languages.update(key_data.keys())
            
            # Check directly loaded files for grammar check (only if selected or for initial population)
            for file_path in self.gc_direct_files.keys():
                if not selected_files or file_path in selected_files:
                    file_data = self.gc_direct_files[file_path]
                    for key_data in file_data.values():
                        if isinstance(key_data, dict):
                            languages.update(key_data.keys())
            
            sorted_languages = sorted(languages)
            
            # Cache the result if no files are selected (for initial population)
            if not selected_files:
                self._gc_languages_cache = sorted_languages
                self._gc_languages_cache_valid = True
        
        # Only update if values changed
        current_values = self.gc_language_combo['values']
        if tuple(sorted_languages) != tuple(current_values):
            self.gc_language_combo['values'] = sorted_languages
            # Only set default if current value is not in new list
            if sorted_languages:
                current_val = self.gc_language_var.get()
                if not current_val or current_val not in sorted_languages:
                    self.gc_language_var.set(sorted_languages[0])
    
    def extract_placeholders(self, text):
        """Extract all placeholders from text"""
        handler = get_grammar_tone_handler()
        return handler.extract_placeholders(text)
    
    def validate_placeholders(self, original, corrected):
        """Validate that placeholders are preserved"""
        handler = get_grammar_tone_handler()
        return handler.validate_placeholders(original, corrected)
    
    def call_llm_grammar_check(self, entries, language):
        """Call LLM API to check grammar for a batch of entries"""
        handler = get_grammar_tone_handler()
        api_key = self.gc_api_key_var.get().strip()
        api_endpoint = self.gc_api_endpoint_var.get().strip()
        model = self.gc_model_var.get().strip() or 'gpt-4o-mini'
        temperature = self.gc_temperature_var.get()
        
        if not api_key:
            raise Exception("API key not set. Please configure API settings.")
        
        # Build prompt using module
        system_prompt, user_prompt = handler.build_grammar_prompt(language, entries)
        
        # Make API call using module
        response_text = handler.call_llm_api(
            api_endpoint, api_key, model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature
        )
        
        # Parse response using module
        return handler.parse_llm_response(response_text, len(entries))
    
    def initialize_check_and_adjustments(self):
        """Combined method that performs grammar check and tone adjustment (if tone != 'keep')"""
        language = self.gc_language_var.get()
        if not language:
            messagebox.showwarning("Warning", "Please select a language.")
            return
        
        api_key = self.gc_api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please configure API settings first.")
            return
        
        tone_mode = self.gc_tone_var.get()
        
        # Clear previous corrections
        self.grammar_corrections = {}
        self.tone_corrections = {}
        self.grammar_preview_text.delete(1.0, tk.END)
        
        # Step 1: Always do grammar check first
        self.grammar_preview_text.insert(tk.END, "Step 1: Checking grammar...\n\n", "header")
        self.grammar_preview_text.update()
        
        # Call grammar check (this is synchronous, so it will complete before continuing)
        try:
            # Collect entries to check (same logic as check_grammar)
            entries_to_check = {}  # {file_path: [(key, locale, value), ...]}
            
            # Check XLIFF files
            for file_path, var in self.gc_crowdin_file_vars.items():
                if var.get() and file_path in self.crowdin_file_data:
                    file_data = self.crowdin_file_data[file_path]
                    langs = self.crowdin_languages[file_path]
                    xliff_entries = []
                    
                    for key, entry in file_data.items():
                        value = None
                        if language.lower() == langs['source'].lower():
                            value = entry.get('source', '') or ''
                        elif language.lower() == langs['target'].lower():
                            value = entry.get('target', '') or ''
                        else:
                            continue
                        
                        if value and value.strip():
                            xliff_entries.append((key, language, value))
                    
                    if xliff_entries:
                        entries_to_check[file_path] = xliff_entries
            
            # Check Term Customizer files
            for file_path, var in self.gc_term_file_vars.items():
                if var.get():
                    file_data = self.gc_direct_files.get(file_path) or self.term_customizer_file_data.get(file_path, {})
                    file_entries = []
                    
                    for key, locales in file_data.items():
                        if language in locales:
                            value = locales[language]
                            if value and value.strip():
                                file_entries.append((key, language, value))
                    
                    if file_entries:
                        entries_to_check[file_path] = file_entries
            
            if not entries_to_check:
                messagebox.showinfo("Info", "No entries found to check for the selected language.")
                return
            
            # Process grammar check
            total_entries = sum(len(entries) for entries in entries_to_check.values())
            self.grammar_preview_text.insert(tk.END, f"Checking grammar for {total_entries} entries in {len(entries_to_check)} file(s)...\n\n", "header")
            self.grammar_preview_text.update()
            
            batch_size = self.gc_batch_size_var.get()
            
            # Process each file for grammar
            for file_path, entries in entries_to_check.items():
                filename = os.path.basename(file_path)
                self.grammar_preview_text.insert(tk.END, f"Processing {filename}...\n", "header")
                self.grammar_preview_text.update()
                
                file_corrections = {}
                
                # Process in batches
                for i in range(0, len(entries), batch_size):
                    batch = entries[i:i+batch_size]
                    batch_keys = [e[0] for e in batch]
                    batch_values = [e[2] for e in batch]
                    
                    try:
                        corrected_values = self.call_llm_grammar_check(
                            list(zip(batch_keys, batch_values)), language
                        )
                        
                        for (key, locale, original), corrected in zip(batch, corrected_values):
                            is_valid, error_msg = self.validate_placeholders(original, corrected)
                            
                            if not is_valid:
                                self.grammar_preview_text.insert(tk.END, 
                                    f"Warning: Placeholder mismatch for key '{key}'. Keeping original.\n", "error")
                                corrected = original
                            
                            if corrected != original:
                                if key not in file_corrections:
                                    file_corrections[key] = {}
                                file_corrections[key][locale] = {
                                    'original': original,
                                    'corrected': corrected
                                }
                    except Exception as e:
                        error_msg = str(e)
                        self.grammar_preview_text.insert(tk.END, 
                            f"\n❌ ERROR processing batch {i//batch_size + 1}:\n", "error")
                        self.grammar_preview_text.insert(tk.END, 
                            f"   {error_msg}\n\n", "error")
                        self.grammar_preview_text.update()
                        continue
                
                if file_corrections:
                    self.grammar_corrections[file_path] = file_corrections
            
            # Step 2: Do tone adjustment if needed
            if tone_mode != "keep":
                # Only apply tone adjustment to German languages
                if language.lower() not in ['de', 'de-ch']:
                    self.grammar_preview_text.insert(tk.END, 
                        f"\n⚠ Tone adjustment skipped: Only available for German (de/de-CH) languages.\n", "warning")
                else:
                    self.grammar_preview_text.insert(tk.END, f"\nStep 2: Adjusting tone ({tone_mode})...\n\n", "header")
                    self.grammar_preview_text.update()
                    
                    # Collect entries to adjust (use grammar-corrected if available, otherwise original)
                    entries_to_adjust = {}
                    
                    if self.grammar_corrections:
                        # Use grammar-corrected values as source
                        for file_path, corrections in self.grammar_corrections.items():
                            file_entries = []
                            for key, locales in corrections.items():
                                if language in locales:
                                    value = locales[language]['corrected']
                                    if value and value.strip():
                                        file_entries.append((key, language, value))
                            if file_entries:
                                entries_to_adjust[file_path] = file_entries
                    else:
                        # Use original file data
                        entries_to_adjust = entries_to_check
                    
                    if entries_to_adjust:
                        # Process tone adjustment
                        for file_path, entries in entries_to_adjust.items():
                            filename = os.path.basename(file_path)
                            self.grammar_preview_text.insert(tk.END, f"Processing {filename}...\n", "header")
                            self.grammar_preview_text.update()
                            
                            file_corrections = {}
                            
                            # Process in batches
                            for i in range(0, len(entries), batch_size):
                                batch = entries[i:i+batch_size]
                                batch_keys = [e[0] for e in batch]
                                batch_values = [e[2] for e in batch]
                                
                                try:
                                    adjusted_values = self.call_llm_tone_adjustment(
                                        list(zip(batch_keys, batch_values)), language, tone_mode
                                    )
                                    
                                    for (key, locale, original), adjusted in zip(batch, adjusted_values):
                                        is_valid, error_msg = self.validate_placeholders(original, adjusted)
                                        
                                        if not is_valid:
                                            self.grammar_preview_text.insert(tk.END, 
                                                f"Warning: Placeholder mismatch for key '{key}'. Keeping original.\n", "error")
                                            adjusted = original
                                        
                                        if adjusted != original:
                                            if key not in file_corrections:
                                                file_corrections[key] = {}
                                            file_corrections[key][locale] = {
                                                'original': original,
                                                'corrected': adjusted
                                            }
                                except Exception as e:
                                    error_msg = str(e)
                                    self.grammar_preview_text.insert(tk.END, 
                                        f"\n❌ ERROR processing batch {i//batch_size + 1}:\n", "error")
                                    self.grammar_preview_text.insert(tk.END, 
                                        f"   {error_msg}\n\n", "error")
                                    self.grammar_preview_text.update()
                                    continue
                            
                            if file_corrections:
                                self.tone_corrections[file_path] = file_corrections
            
            # Display results
            self.display_grammar_results()
            self.update_gc_statistics()
            
            # Show summary message
            total_grammar = sum(
                len(locales) for file_corr in self.grammar_corrections.values()
                for locales in file_corr.values()
            ) if self.grammar_corrections else 0
            total_tone = sum(
                len(locales) for file_corr in self.tone_corrections.values()
                for locales in file_corr.values()
            ) if self.tone_corrections else 0
            
            if total_grammar > 0 or total_tone > 0:
                messagebox.showinfo("Check and Adjustments Complete", 
                                  f"Grammar corrections: {total_grammar}\n"
                                  f"Tone adjustments: {total_tone}\n\n"
                                  "Review the corrections in the preview below.")
            else:
                messagebox.showinfo("Check and Adjustments Complete", 
                                  "No corrections found. All entries appear to be correct.\n\n"
                                  "Note: If you expected corrections, please check:\n"
                                  "- The LLM connection (use 'Test Connection' button)\n"
                                  "- That the selected language matches your file content\n"
                                  "- Error messages in the preview area")
        
        except Exception as e:
            error_msg = str(e)
            self.grammar_preview_text.insert(tk.END, 
                f"\n❌ FATAL ERROR:\n\n", "error")
            self.grammar_preview_text.insert(tk.END, 
                f"{error_msg}\n\n", "error")
            messagebox.showerror("Error", 
                               f"Error during check and adjustments:\n\n{error_msg}\n\n"
                               "Check the preview area for more details.")
    
    def check_grammar(self):
        """Check grammar for selected files and language"""
        language = self.gc_language_var.get()
        if not language:
            messagebox.showwarning("Warning", "Please select a language.")
            return
        
        api_key = self.gc_api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please configure API settings first.")
            return
        
        # Collect entries to check
        entries_to_check = {}  # {file_path: [(key, locale, value), ...]}
        
        # Check XLIFF files
        for file_path, var in self.gc_crowdin_file_vars.items():
            if var.get() and file_path in self.crowdin_file_data:
                file_data = self.crowdin_file_data[file_path]
                langs = self.crowdin_languages[file_path]
                xliff_entries = []
                
                for key, entry in file_data.items():
                    value = None
                    if language.lower() == langs['source'].lower():
                        value = entry.get('source', '') or ''
                    elif language.lower() == langs['target'].lower():
                        value = entry.get('target', '') or ''
                    else:
                        continue
                    
                    if value and value.strip():
                        xliff_entries.append((key, language, value))
                
                if xliff_entries:
                    entries_to_check[file_path] = xliff_entries
        
        # Check Term Customizer files
        for file_path, var in self.gc_term_file_vars.items():
            if var.get():
                # Check if it's a directly loaded file or a regular Term Customizer file
                file_data = self.gc_direct_files.get(file_path) or self.term_customizer_file_data.get(file_path, {})
                file_entries = []
                
                for key, locales in file_data.items():
                    if language in locales:
                        value = locales[language]
                        if value and value.strip():
                            file_entries.append((key, language, value))
                
                if file_entries:
                    entries_to_check[file_path] = file_entries
        
        if not entries_to_check:
            messagebox.showinfo("Info", "No entries found to check for the selected language.")
            return
        
        # Clear previous corrections
        self.grammar_corrections = {}
        self.grammar_preview_text.delete(1.0, tk.END)
        
        # Show progress
        total_entries = sum(len(entries) for entries in entries_to_check.values())
        self.grammar_preview_text.insert(tk.END, f"Checking grammar for {total_entries} entries in {len(entries_to_check)} file(s)...\n\n", "header")
        self.grammar_preview_text.update()
        
        batch_size = self.gc_batch_size_var.get()
        
        try:
            # Process each file
            for file_path, entries in entries_to_check.items():
                filename = os.path.basename(file_path)
                self.grammar_preview_text.insert(tk.END, f"Processing {filename}...\n", "header")
                self.grammar_preview_text.update()
                
                file_corrections = {}
                
                # Process in batches
                for i in range(0, len(entries), batch_size):
                    batch = entries[i:i+batch_size]
                    batch_keys = [e[0] for e in batch]
                    batch_values = [e[2] for e in batch]
                    
                    # Call LLM
                    try:
                        corrected_values = self.call_llm_grammar_check(
                            list(zip(batch_keys, batch_values)), language
                        )
                        
                        # Validate and store corrections
                        for (key, locale, original), corrected in zip(batch, corrected_values):
                            # Validate placeholders
                            is_valid, error_msg = self.validate_placeholders(original, corrected)
                            
                            if not is_valid:
                                # If placeholders don't match, keep original
                                self.grammar_preview_text.insert(tk.END, 
                                    f"Warning: Placeholder mismatch for key '{key}'. Keeping original.\n", "error")
                                corrected = original
                            
                            if corrected != original:
                                if key not in file_corrections:
                                    file_corrections[key] = {}
                                file_corrections[key][locale] = {
                                    'original': original,
                                    'corrected': corrected
                                }
                        
                    except Exception as e:
                        error_msg = str(e)
                        # Show detailed error information
                        self.grammar_preview_text.insert(tk.END, 
                            f"\n❌ ERROR processing batch {i//batch_size + 1}:\n", "error")
                        self.grammar_preview_text.insert(tk.END, 
                            f"   {error_msg}\n\n", "error")
                        self.grammar_preview_text.update()
                        # Continue with next batch
                        continue
                
                if file_corrections:
                    self.grammar_corrections[file_path] = file_corrections
            
            # Display results
            self.display_grammar_results()
            self.update_gc_statistics()
            
            # Show summary message
            if self.grammar_corrections:
                total_corrections = sum(
                    len(locales) for file_corr in self.grammar_corrections.values()
                    for locales in file_corr.values()
                )
                messagebox.showinfo("Grammar Check Complete", 
                                  f"Found {total_corrections} correction(s) in {len(self.grammar_corrections)} file(s).\n\n"
                                  "Review the corrections in the preview below.")
            else:
                messagebox.showinfo("Grammar Check Complete", 
                                  "No corrections found. All entries appear to be grammatically correct.\n\n"
                                  "Note: If you expected corrections, please check:\n"
                                  "- The LLM connection (use 'Test Connection' button)\n"
                                  "- That the selected language matches your file content\n"
                                  "- Error messages in the preview area")
            
        except Exception as e:
            error_msg = str(e)
            # Show detailed error in preview
            self.grammar_preview_text.insert(tk.END, 
                f"\n❌ FATAL ERROR during grammar check:\n\n", "error")
            self.grammar_preview_text.insert(tk.END, 
                f"{error_msg}\n\n", "error")
            self.grammar_preview_text.insert(tk.END, 
                "Please check:\n"
                "- Your API settings (use 'Test Connection' button)\n"
                "- Your internet connection\n"
                "- The error details above\n", "error")
            messagebox.showerror("Error", 
                               f"Error during grammar check:\n\n{error_msg}\n\n"
                               "Check the preview area for more details.")
    
    def adjust_tone(self):
        """Adjust tone for selected files and language"""
        tone_mode = self.gc_tone_var.get()
        if tone_mode == "keep":
            messagebox.showinfo("Info", "Tone adjustment is set to 'keep'. No changes will be made.")
            return
        
        language = self.gc_language_var.get()
        if not language:
            messagebox.showwarning("Warning", "Please select a language.")
            return
        
        # Only apply tone adjustment to German languages
        if language.lower() not in ['de', 'de-ch']:
            messagebox.showwarning("Warning", 
                                 f"Tone adjustment is only available for German (de/de-CH) languages.\n"
                                 f"Selected language: {language}")
            return
        
        api_key = self.gc_api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("Warning", "Please configure API settings first.")
            return
        
        # Collect entries to adjust
        entries_to_adjust = {}  # {file_path: [(key, locale, value), ...]}
        
        # Use grammar corrections if available, otherwise use original files
        if self.grammar_corrections:
            # Use grammar-corrected values as source
            for file_path, corrections in self.grammar_corrections.items():
                file_entries = []
                for key, locales in corrections.items():
                    if language in locales:
                        # Use the corrected value from grammar check
                        value = locales[language]['corrected']
                        if value and value.strip():
                            file_entries.append((key, language, value))
                if file_entries:
                    entries_to_adjust[file_path] = file_entries
        else:
            # Use original file data
            # Check XLIFF files
            for file_path, var in self.gc_crowdin_file_vars.items():
                if var.get() and file_path in self.crowdin_file_data:
                    file_data = self.crowdin_file_data[file_path]
                    langs = self.crowdin_languages[file_path]
                    xliff_entries = []
                    
                    for key, entry in file_data.items():
                        value = None
                        if language.lower() == langs['source'].lower():
                            value = entry.get('source', '') or ''
                        elif language.lower() == langs['target'].lower():
                            value = entry.get('target', '') or ''
                        else:
                            continue
                        
                        if value and value.strip():
                            xliff_entries.append((key, language, value))
                    
                    if xliff_entries:
                        entries_to_adjust[file_path] = xliff_entries
            
            # Check Term Customizer files
            for file_path, var in self.gc_term_file_vars.items():
                if var.get():
                    file_data = self.gc_direct_files.get(file_path) or self.term_customizer_file_data.get(file_path, {})
                    file_entries = []
                    
                    for key, locales in file_data.items():
                        if language in locales:
                            value = locales[language]
                            if value and value.strip():
                                file_entries.append((key, language, value))
                    
                    if file_entries:
                        entries_to_adjust[file_path] = file_entries
        
        if not entries_to_adjust:
            messagebox.showinfo("Info", "No entries found to adjust for the selected language.")
            return
        
        # Clear previous tone corrections
        self.tone_corrections = {}
        self.grammar_preview_text.delete(1.0, tk.END)
        
        # Show progress
        total_entries = sum(len(entries) for entries in entries_to_adjust.values())
        self.grammar_preview_text.insert(tk.END, f"Adjusting tone ({tone_mode}) for {total_entries} entries in {len(entries_to_adjust)} file(s)...\n\n", "header")
        self.grammar_preview_text.update()
        
        batch_size = self.gc_batch_size_var.get()
        
        try:
            # Process each file
            for file_path, entries in entries_to_adjust.items():
                filename = os.path.basename(file_path)
                self.grammar_preview_text.insert(tk.END, f"Processing {filename}...\n", "header")
                self.grammar_preview_text.update()
                
                file_corrections = {}
                
                # Process in batches
                for i in range(0, len(entries), batch_size):
                    batch = entries[i:i+batch_size]
                    batch_keys = [e[0] for e in batch]
                    batch_values = [e[2] for e in batch]
                    
                    # Call LLM
                    try:
                        adjusted_values = self.call_llm_tone_adjustment(
                            list(zip(batch_keys, batch_values)), language, tone_mode
                        )
                        
                        # Validate and store corrections
                        for (key, locale, original), adjusted in zip(batch, adjusted_values):
                            # Validate placeholders
                            is_valid, error_msg = self.validate_placeholders(original, adjusted)
                            
                            if not is_valid:
                                # If placeholders don't match, keep original
                                self.grammar_preview_text.insert(tk.END, 
                                    f"Warning: Placeholder mismatch for key '{key}'. Keeping original.\n", "error")
                                adjusted = original
                            
                            if adjusted != original:
                                if key not in file_corrections:
                                    file_corrections[key] = {}
                                file_corrections[key][locale] = {
                                    'original': original,
                                    'corrected': adjusted
                                }
                        
                    except Exception as e:
                        error_msg = str(e)
                        # Show detailed error information
                        self.grammar_preview_text.insert(tk.END, 
                            f"\n❌ ERROR processing batch {i//batch_size + 1}:\n", "error")
                        self.grammar_preview_text.insert(tk.END, 
                            f"   {error_msg}\n\n", "error")
                        self.grammar_preview_text.update()
                        # Continue with next batch
                        continue
                
                if file_corrections:
                    self.tone_corrections[file_path] = file_corrections
            
            # Display results
            self.display_grammar_results()
            
            # Show summary message
            if self.tone_corrections:
                total_corrections = sum(
                    len(locales) for file_corr in self.tone_corrections.values()
                    for locales in file_corr.values()
                )
                messagebox.showinfo("Tone Adjustment Complete", 
                                  f"Found {total_corrections} adjustment(s) in {len(self.tone_corrections)} file(s).\n\n"
                                  "Review the adjustments in the preview below.")
            else:
                messagebox.showinfo("Tone Adjustment Complete", 
                                  "No adjustments found. All entries already have the desired tone.\n\n"
                                  "Note: If you expected adjustments, please check:\n"
                                  "- The LLM connection (use 'Test Connection' button)\n"
                                  "- That the selected language is German (de/de-CH)\n"
                                  "- Error messages in the preview area")
            
        except Exception as e:
            error_msg = str(e)
            # Show detailed error in preview
            self.grammar_preview_text.insert(tk.END, 
                f"\n❌ FATAL ERROR during tone adjustment:\n\n", "error")
            self.grammar_preview_text.insert(tk.END, 
                f"{error_msg}\n\n", "error")
            self.grammar_preview_text.insert(tk.END, 
                "Please check:\n"
                "- Your API settings (use 'Test Connection' button)\n"
                "- Your internet connection\n"
                "- The error details above\n", "error")
            messagebox.showerror("Error", 
                               f"Error during tone adjustment:\n\n{error_msg}\n\n"
                               "Check the preview area for more details.")
    
    def call_llm_tone_adjustment(self, entries, language, tone_mode):
        """Call LLM API to adjust tone for a batch of entries"""
        handler = get_grammar_tone_handler()
        api_key = self.gc_api_key_var.get().strip()
        api_endpoint = self.gc_api_endpoint_var.get().strip()
        model = self.gc_model_var.get().strip() or 'gpt-4o-mini'
        temperature = self.gc_temperature_var.get()
        
        if not api_key:
            raise Exception("API key not set. Please configure API settings.")
        
        # Build prompt using module
        system_prompt, user_prompt = handler.build_tone_prompt(language, tone_mode, entries)
        
        # Make API call using module
        response_text = handler.call_llm_api(
            api_endpoint, api_key, model,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature
        )
        
        # Parse response using module
        return handler.parse_llm_response(response_text, len(entries))
    
    def display_grammar_results(self):
        """Display grammar check and tone adjustment results in preview"""
        self.grammar_preview_text.delete(1.0, tk.END)
        
        # Combine grammar and tone corrections for display
        all_corrections = {}
        for file_path, corrections in self.grammar_corrections.items():
            if file_path not in all_corrections:
                all_corrections[file_path] = {}
            for key, locales in corrections.items():
                if key not in all_corrections[file_path]:
                    all_corrections[file_path][key] = {}
                for locale, changes in locales.items():
                    all_corrections[file_path][key][locale] = changes
        
        # Merge tone corrections (tone corrections override grammar corrections for same key/locale)
        for file_path, corrections in self.tone_corrections.items():
            if file_path not in all_corrections:
                all_corrections[file_path] = {}
            for key, locales in corrections.items():
                if key not in all_corrections[file_path]:
                    all_corrections[file_path][key] = {}
                for locale, changes in locales.items():
                    # If this key/locale already has grammar corrections, use the grammar-corrected as original
                    if locale in all_corrections[file_path].get(key, {}):
                        all_corrections[file_path][key][locale] = {
                            'original': all_corrections[file_path][key][locale]['original'],
                            'corrected': changes['corrected']
                        }
                    else:
                        all_corrections[file_path][key][locale] = changes
        
        if not all_corrections:
            self.grammar_preview_text.insert(tk.END, "No corrections found. All entries are correct.\n")
            return
        
        total_grammar = sum(
            len(locales) for file_corr in self.grammar_corrections.values()
            for locales in file_corr.values()
        )
        total_tone = sum(
            len(locales) for file_corr in self.tone_corrections.values()
            for locales in file_corr.values()
        )
        total_corrections = sum(
            len(locales) for file_corr in all_corrections.values()
            for locales in file_corr.values()
        )
        
        self.grammar_preview_text.insert(tk.END, 
            f"Found {total_corrections} correction(s) in {len(all_corrections)} file(s)\n", "header")
        if total_grammar > 0:
            self.grammar_preview_text.insert(tk.END, f"  - Grammar: {total_grammar}\n", "header")
        if total_tone > 0:
            self.grammar_preview_text.insert(tk.END, f"  - Tone: {total_tone}\n", "header")
        self.grammar_preview_text.insert(tk.END, "\n")
        
        for file_path, corrections in all_corrections.items():
            filename = os.path.basename(file_path)
            self.grammar_preview_text.insert(tk.END, f"File: {filename}\n", "header")
            self.grammar_preview_text.insert(tk.END, "=" * 80 + "\n\n")
            
            for key, locales in sorted(corrections.items()):
                self.grammar_preview_text.insert(tk.END, f"Key: {key}\n")
                for locale, changes in locales.items():
                    self.grammar_preview_text.insert(tk.END, f"  [{locale}] ", "header")
                    self.grammar_preview_text.insert(tk.END, "Original: ", "header")
                    self.grammar_preview_text.insert(tk.END, f"{changes['original']}\n", "original")
                    self.grammar_preview_text.insert(tk.END, f"           Corrected: ", "header")
                    self.grammar_preview_text.insert(tk.END, f"{changes['corrected']}\n", "corrected")
                self.grammar_preview_text.insert(tk.END, "\n")
    
    def update_gc_statistics(self):
        """Update the statistics view for grammar check and tone adjustments"""
        self.gc_stats_text.config(state=tk.NORMAL)
        self.gc_stats_text.delete(1.0, tk.END)
        
        # Build content in memory first
        content_parts = []
        
        # Overall statistics
        content_parts.append(("GRAMMAR CHECK & TONE ADJUSTMENT STATISTICS\n", "header"))
        content_parts.append(("=" * 80 + "\n\n", None))
        
        # Count corrections
        total_grammar = sum(
            len(locales) for file_corr in self.grammar_corrections.values()
            for locales in file_corr.values()
        ) if self.grammar_corrections else 0
        
        total_tone = sum(
            len(locales) for file_corr in self.tone_corrections.values()
            for locales in file_corr.values()
        ) if self.tone_corrections else 0
        
        total_files = len(set(list(self.grammar_corrections.keys()) + list(self.tone_corrections.keys())))
        
        content_parts.append(("Overall Results:\n", "subheader"))
        content_parts.append((f"  Files processed: {total_files}\n", None))
        content_parts.append((f"  ✓ Grammar corrections: ", "subheader"))
        content_parts.append((f"{total_grammar}\n", "number"))
        content_parts.append((f"  ✓ Tone adjustments: ", "subheader"))
        content_parts.append((f"{total_tone}\n", "number"))
        content_parts.append((f"  Total changes: ", "subheader"))
        content_parts.append((f"{total_grammar + total_tone}\n\n", "number"))
        
        # Per-file statistics
        if total_files > 0:
            content_parts.append(("Per-File Statistics:\n", "header"))
            content_parts.append(("=" * 80 + "\n\n", None))
            
            all_files = set(list(self.grammar_corrections.keys()) + list(self.tone_corrections.keys()))
            for file_path in sorted(all_files):
                filename = os.path.basename(file_path)
                content_parts.append((f"File: {filename}\n", "subheader"))
                
                grammar_count = sum(
                    len(locales) for locales in self.grammar_corrections.get(file_path, {}).values()
                ) if file_path in self.grammar_corrections else 0
                
                tone_count = sum(
                    len(locales) for locales in self.tone_corrections.get(file_path, {}).values()
                ) if file_path in self.tone_corrections else 0
                
                content_parts.append((f"  Grammar corrections: ", "subheader"))
                content_parts.append((f"{grammar_count}\n", "number"))
                content_parts.append((f"  Tone adjustments: ", "subheader"))
                content_parts.append((f"{tone_count}\n", "number"))
                content_parts.append((f"  Total: ", "subheader"))
                content_parts.append((f"{grammar_count + tone_count}\n\n", "number"))
        
        if total_grammar == 0 and total_tone == 0:
            content_parts.append(("No corrections found. All entries are correct.\n", None))
        
        # Insert all content at once
        for text, tag in content_parts:
            if tag:
                self.gc_stats_text.insert(tk.END, text, tag)
            else:
                self.gc_stats_text.insert(tk.END, text)
        
        self.gc_stats_text.config(state=tk.DISABLED)
    
    def save_grammar_corrections(self):
        """Save grammar-corrected and tone-adjusted entries to new files"""
        # Combine grammar and tone corrections
        all_corrections = {}
        for file_path, corrections in self.grammar_corrections.items():
            if file_path not in all_corrections:
                all_corrections[file_path] = {}
            for key, locales in corrections.items():
                if key not in all_corrections[file_path]:
                    all_corrections[file_path][key] = {}
                for locale, changes in locales.items():
                    all_corrections[file_path][key][locale] = changes['corrected']
        
        # Merge tone corrections (tone corrections override grammar corrections for same key/locale)
        for file_path, corrections in self.tone_corrections.items():
            if file_path not in all_corrections:
                all_corrections[file_path] = {}
            for key, locales in corrections.items():
                if key not in all_corrections[file_path]:
                    all_corrections[file_path][key] = {}
                for locale, changes in locales.items():
                    all_corrections[file_path][key][locale] = changes['corrected']
        
        if not all_corrections:
            messagebox.showwarning("Warning", "No corrections to save. Please run grammar check or tone adjustment first.")
            return
        
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            for file_path, corrections in all_corrections.items():
                directory = os.path.dirname(file_path) if os.path.dirname(file_path) else os.getcwd()
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Determine suffix based on what was done
                has_grammar = file_path in self.grammar_corrections
                has_tone = file_path in self.tone_corrections
                if has_grammar and has_tone:
                    suffix = "grammar_tone_checked"
                elif has_grammar:
                    suffix = "grammar_checked"
                elif has_tone:
                    suffix = "tone_adjusted"
                else:
                    suffix = "corrected"
                
                output_filename = f"{base_name}_{suffix}_{timestamp}.csv"
                output_path = os.path.join(directory, output_filename)
                
                # Ensure unique filename
                counter = 1
                original_path = output_path
                while os.path.exists(output_path):
                    base, ext = os.path.splitext(original_path)
                    output_path = f"{base}_{counter}{ext}"
                    counter += 1
                
                # Prepare output rows
                output_rows = []
                for key, locales in corrections.items():
                    for locale, value in locales.items():
                        output_rows.append({
                            'locale': locale,
                            'key': key,
                            'value': value
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
                messagebox.showinfo("Success", 
                                  f"Saved {len(saved_files)} file(s) with corrections:\n\n{files_list}\n\n"
                                  "Original files were not modified.")
            else:
                messagebox.showinfo("Info", "No files were saved.")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error saving corrections: {str(e)}")
        
    def save_config(self):
        """Save configuration"""
        self.config_manager.crowdin_file_paths = self.crowdin_files.copy()
        self.config_manager.api_endpoint = self.api_endpoint
        self.config_manager.api_key = self.api_key
        self.config_manager.api_model = self.api_model
        self.config_manager.save()
    
    def upload_crowdin_files(self):
        """Upload one or more XLIFF files"""
        file_paths = filedialog.askopenfilenames(
            title="Select Crowdin/XLIFF File(s)",
            filetypes=[("XLIFF files", "*.xliff"), ("All files", "*.*")]
        )
        if file_paths:
            loaded_count = 0
            for file_path in file_paths:
                if file_path not in self.crowdin_files:
                    if self.load_crowdin_file(file_path):
                        self.crowdin_files.append(file_path)
                        self.crowdin_listbox.insert(tk.END, os.path.basename(file_path))
                        loaded_count += 1
                else:
                    messagebox.showinfo("Info", f"File {os.path.basename(file_path)} is already loaded")
            
            if loaded_count > 0:
                self.update_locale_info()
                # Invalidate caches when files change
                self._sr_languages_cache_valid = False
                self._gc_languages_cache_valid = False
                
                # Update search & replace languages (only if tab is initialized)
                if hasattr(self, 'sr_language_combo') and self.tabs_initialized.get('search_replace', False):
                    self.update_sr_languages()
                # Update grammar check languages (only if tab is initialized)
                if hasattr(self, 'gc_language_combo') and self.tabs_initialized.get('grammar', False):
                    self.update_gc_languages()
                # Update search & replace file selection (only if tab is initialized)
                if hasattr(self, 'sr_crowdin_var') and self.tabs_initialized.get('search_replace', False):
                    self.update_sr_file_selection()
                # Update grammar check file selection (only if tab is initialized)
                if hasattr(self, 'gc_crowdin_var') and self.tabs_initialized.get('grammar', False):
                    self.update_gc_file_selection()
                
                # Save config after loading
                self.save_config()
                messagebox.showinfo("Success", f"Loaded {loaded_count} XLIFF file(s)")
    
    def remove_selected_crowdin_file(self):
        """Remove the selected XLIFF file from the list"""
        selection = self.crowdin_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file to remove")
            return
        
        index = selection[0]
        file_path = self.crowdin_files[index]
        
        # Remove from lists
        self.crowdin_files.pop(index)
        self.crowdin_listbox.delete(index)
        
        # Remove from data structures
        if file_path in self.crowdin_file_data:
            del self.crowdin_file_data[file_path]
        if file_path in self.crowdin_languages:
            del self.crowdin_languages[file_path]
        
        # Update UI
        self.update_locale_info()
        # Invalidate caches when files change
        self._sr_languages_cache_valid = False
        self._gc_languages_cache_valid = False
        
        # Update search & replace languages (only if tab is initialized)
        if hasattr(self, 'sr_language_combo') and self.tabs_initialized.get('search_replace', False):
            self.update_sr_languages()
        # Update grammar check languages (only if tab is initialized)
        if hasattr(self, 'gc_language_combo') and self.tabs_initialized.get('grammar', False):
            self.update_gc_languages()
        # Update search & replace file selection (only if tab is initialized)
        if hasattr(self, 'sr_crowdin_var') and self.tabs_initialized.get('search_replace', False):
            self.update_sr_file_selection()
        # Update grammar check file selection (only if tab is initialized)
        if hasattr(self, 'gc_crowdin_var') and self.tabs_initialized.get('grammar', False):
            self.update_gc_file_selection()
        
        # Save config
        self.save_config()
        messagebox.showinfo("Removed", f"Removed {os.path.basename(file_path)}")
            
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
            # Invalidate caches when files change
            self._sr_languages_cache_valid = False
            self._gc_languages_cache_valid = False
            
            # Update search & replace file selection (only if tab is initialized)
            if hasattr(self, 'sr_term_file_vars') and self.tabs_initialized.get('search_replace', False):
                self.update_sr_file_selection()
            # Update grammar check file selection and languages (only if tab is initialized)
            if hasattr(self, 'gc_term_file_vars') and self.tabs_initialized.get('grammar', False):
                self.update_gc_file_selection()
                if hasattr(self, 'gc_language_combo'):
                    self.update_gc_languages()
    
    def clear_term_customizer_files(self):
        self.term_customizer_files = []
        self.term_customizer_data = {}
        self.term_customizer_file_data = {}
        self.term_customizer_locales = set()
        self.term_customizer_listbox.delete(0, tk.END)
        self.update_locale_info()
        # Invalidate caches when files change
        self._sr_languages_cache_valid = False
        self._gc_languages_cache_valid = False
        
        # Update search & replace file selection (only if tab is initialized)
        if hasattr(self, 'sr_term_file_vars') and self.tabs_initialized.get('search_replace', False):
            self.update_sr_file_selection()
        # Update grammar check file selection and languages (only if tab is initialized)
        if hasattr(self, 'gc_term_file_vars') and self.tabs_initialized.get('grammar', False):
            self.update_gc_file_selection()
            if hasattr(self, 'gc_language_combo'):
                self.update_gc_languages()
        messagebox.showinfo("Cleared", "All Term Customizer files have been cleared")
            
    def load_crowdin_file(self, file_path):
        """Load a single XLIFF file and store its data"""
        if not file_path:
            return False
            
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.xliff':
                # Load XLIFF file
                data, count, source_lang, target_lang = self.file_handler.load_xliff_file(file_path)
                
                # Store per-file data
                self.crowdin_file_data[file_path] = data
                self.crowdin_languages[file_path] = {
                    'source': source_lang,
                    'target': target_lang
                }
                
                return True
            else:
                messagebox.showerror("Error", "Only XLIFF files are supported for Crowdin files")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Error loading XLIFF file {os.path.basename(file_path)}: {str(e)}")
            return False
            
    def load_term_customizer_file(self, file_path):
        """Load a single Term Customizer file"""
        try:
            file_data, file_locales = self.file_handler.load_csv_file(file_path)
            
            # Also add to combined data
            for key, locales in file_data.items():
                if key not in self.term_customizer_data:
                    self.term_customizer_data[key] = {}
                for locale, value in locales.items():
                    self.term_customizer_data[key][locale] = value
                    self.term_customizer_locales.add(locale)
            
            # Store per-file data
            self.term_customizer_file_data[file_path] = file_data
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading Term Customizer file {os.path.basename(file_path)}: {str(e)}")
    
    def update_locale_info(self):
        """Update the locale info label"""
        info_parts = []
        
        # Collect all XLIFF languages
        xliff_sources = set()
        xliff_targets = set()
        for file_path, langs in self.crowdin_languages.items():
            if langs['source']:
                xliff_sources.add(langs['source'])
            if langs['target']:
                xliff_targets.add(langs['target'])
        
        if xliff_sources or xliff_targets:
            xliff_info = f"XLIFF: {len(self.crowdin_files)} file(s)"
            if xliff_sources:
                xliff_info += f", source={', '.join(sorted(xliff_sources))}"
            if xliff_targets:
                xliff_info += f", target={', '.join(sorted(xliff_targets))}"
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
        
        if not self.term_customizer_files:
            messagebox.showwarning("Warning", "Please add at least one Term Customizer file first")
            return
            
        if not self.crowdin_files:
            messagebox.showwarning("Warning", "Please upload at least one Crowdin/XLIFF file first")
            return
        
        # Collect all XLIFF languages for validation
        all_xliff_sources = set()
        all_xliff_targets = set()
        for file_path, langs in self.crowdin_languages.items():
            if langs['source']:
                all_xliff_sources.add(langs['source'].lower())
            if langs['target']:
                all_xliff_targets.add(langs['target'].lower())
        
        # Validate locale matching
        unmatched_locales = []
        for locale in self.term_customizer_locales:
            locale_lower = locale.lower()
            if locale_lower not in all_xliff_sources and locale_lower not in all_xliff_targets:
                unmatched_locales.append(locale)
        
        if unmatched_locales:
            messagebox.showerror("Error", 
                f"Locale mismatch detected!\n\n"
                f"Term Customizer locales: {', '.join(sorted(self.term_customizer_locales))}\n"
                f"XLIFF source languages: {', '.join(sorted([l for l in all_xliff_sources]))}\n"
                f"XLIFF target languages: {', '.join(sorted([l for l in all_xliff_targets]))}\n\n"
                f"The following locales don't match: {', '.join(unmatched_locales)}\n"
                f"Only matching locales can be compared.")
            return
        
        # Build combined Crowdin data from all XLIFF files
        # A key exists if it exists in ANY XLIFF file
        combined_crowdin_data = {}  # {key: {'source': value, 'target': value, 'files': [file_paths]}}
        for file_path, file_data in self.crowdin_file_data.items():
            langs = self.crowdin_languages[file_path]
            for key, entry in file_data.items():
                if key not in combined_crowdin_data:
                    combined_crowdin_data[key] = {
                        'source': entry.get('source', '') or '',
                        'target': entry.get('target', '') or '',
                        'files': []
                    }
                # Merge values (prefer non-empty values)
                if entry.get('source') and not combined_crowdin_data[key]['source']:
                    combined_crowdin_data[key]['source'] = entry.get('source', '') or ''
                if entry.get('target') and not combined_crowdin_data[key]['target']:
                    combined_crowdin_data[key]['target'] = entry.get('target', '') or ''
                if file_path not in combined_crowdin_data[key]['files']:
                    combined_crowdin_data[key]['files'].append(file_path)
            
        # Find mismatches using configured conditional logic
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}
        
        # Calculate keys to delete (keys only in Term Customizer, not in any Crowdin file)
        all_term_keys = set()
        for file_path, file_data in self.term_customizer_file_data.items():
            all_term_keys.update(file_data.keys())
        crowdin_keys = set(combined_crowdin_data.keys())
        keys_only_in_term = all_term_keys - crowdin_keys
        self.keys_to_delete = sorted(list(keys_only_in_term))
        
        # Use comparison logic helper methods
        values_differ = lambda v1, v2: self.comparison_logic.values_differ(v1, v2, include_empty, case_sensitive)
        should_check_value = lambda tv, rv: self.comparison_logic.should_check_value(tv, rv)
        
        # Compare for each Term Customizer file separately
        for term_file_path in self.term_customizer_files:
            term_file_data = self.term_customizer_file_data.get(term_file_path, {})
            file_mismatches = {}
            
            # Compare for each matching locale
            for key, term_data in term_file_data.items():
                if key not in combined_crowdin_data:
                    continue
                
                crowdin_entry = combined_crowdin_data[key]
                entry_mismatches = {}
                
                # Check each locale in this Term Customizer file
                for locale in term_data.keys():
                    locale_lower = locale.lower()
                    term_value = term_data.get(locale, '') or ''
                    
                    # Find matching XLIFF file for this locale
                    xliff_value = None
                    matching_xliff_file = None
                    
                    # Try to find a matching XLIFF file for this locale
                    for xliff_file_path, xliff_data in self.crowdin_file_data.items():
                        langs = self.crowdin_languages[xliff_file_path]
                        if key in xliff_data:
                            if locale_lower == langs['source'].lower():
                                # Source language: use XLIFF source
                                xliff_value = xliff_data[key].get('source', '') or ''
                                matching_xliff_file = xliff_file_path
                                break
                            elif locale_lower == langs['target'].lower():
                                # Target language: use XLIFF target
                                xliff_value = xliff_data[key].get('target', '') or ''
                                matching_xliff_file = xliff_file_path
                                break
                    
                    # If no specific match found, use combined data
                    if xliff_value is None:
                        if locale_lower in all_xliff_sources:
                            xliff_value = crowdin_entry['source']
                        elif locale_lower in all_xliff_targets:
                            xliff_value = crowdin_entry['target']
                        else:
                            continue
                    
                    # Check for mismatch
                    if should_check_value(term_value, require_term_value):
                        if values_differ(term_value, xliff_value):
                            entry_mismatches[locale] = {
                                'term_value': term_value,
                                'xliff_value': xliff_value,
                                'xliff_file': matching_xliff_file or 'multiple'
                            }
                
                # Add to mismatched entries if any locale has a mismatch
                if entry_mismatches:
                    if key not in file_mismatches:
                        file_mismatches[key] = {
                            'crowdin_source': crowdin_entry['source'],
                            'crowdin_target': crowdin_entry['target'],
                            'term_values': {}
                        }
                    # Store mismatches for each locale
                    for locale, mismatch_data in entry_mismatches.items():
                        file_mismatches[key]['term_values'][locale] = mismatch_data['term_value']
                    
                    # Also add to combined mismatches
                    if key not in self.mismatched_entries:
                        self.mismatched_entries[key] = {
                            'crowdin_source': crowdin_entry['source'],
                            'crowdin_target': crowdin_entry['target'],
                            'term_values': {}
                        }
                    for locale, mismatch_data in entry_mismatches.items():
                        self.mismatched_entries[key]['term_values'][locale] = mismatch_data['term_value']
            
            # Store per-file mismatches
            self.mismatched_entries_per_file[term_file_path] = file_mismatches
                    
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
        self.diff_text.config(state=tk.NORMAL)
        self.diff_text.delete(1.0, tk.END)
        
        if not self.mismatched_entries:
            self.diff_text.insert(tk.END, "No mismatches found. Files are in sync.\n")
            self.diff_text.config(state=tk.DISABLED)
            return
        
        # Build content in memory first for better performance
        content_parts = []
        for key, entry in sorted(self.mismatched_entries.items()):
            # Header
            content_parts.append(("\n" + "="*80 + "\n", "header"))
            content_parts.append((f"Key: {key}\n", "header"))
            content_parts.append(("="*80 + "\n\n", "header"))
            
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
                
                content_parts.append((f"Locale ({locale}):\n", None))
                content_parts.append((f"  {xliff_label}:  {xliff_value}\n", "removed"))
                content_parts.append((f"  Customizer:     {term_value}\n", "added"))
                content_parts.append(("\n", None))
        
        # Insert all content at once
        for text, tag in content_parts:
            if tag:
                self.diff_text.insert(tk.END, text, tag)
            else:
                self.diff_text.insert(tk.END, text)
        
        # Reset to read-only state
        self.diff_text.config(state=tk.DISABLED)
                
    def update_edit_view(self):
        # Clear existing items efficiently
        children = self.edit_tree.get_children()
        if children:
            self.edit_tree.delete(*children)
        
        self.editable_values = {}
        
        # Prepare all items first
        items_to_insert = []
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
                items_to_insert.append((item_id, (
                    key,
                    locale,
                    xliff_value,
                    term_value,
                    term_value  # Start with term customizer value
                )))
                self.editable_values[item_id] = term_value
        
        # Insert all items at once (batch insert for better performance)
        for item_id, values in items_to_insert:
            self.edit_tree.insert("", tk.END, iid=item_id, values=values)
                
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
                    
                    # Create output filename with timestamp to ensure uniqueness
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    if suffix:
                        output_filename = f"{base_name}{suffix}_{timestamp}.csv"
                    else:
                        output_filename = f"{base_name}_updated_{timestamp}.csv"
                    output_path = os.path.join(directory, output_filename)
                    
                    # Ensure unique filename (shouldn't happen with timestamp, but just in case)
                    counter = 1
                    original_path = output_path
                    while os.path.exists(output_path):
                        base, ext = os.path.splitext(original_path)
                        output_path = f"{base}_{counter}{ext}"
                        counter += 1
                    
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
                
                # Create output filename with timestamp to ensure uniqueness
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if suffix:
                    output_filename = f"merged{suffix}_{timestamp}.csv"
                else:
                    output_filename = f"merged_{timestamp}.csv"
                output_path = os.path.join(directory, output_filename)
                
                # Ensure unique filename
                counter = 1
                original_path = output_path
                while os.path.exists(output_path):
                    base, ext = os.path.splitext(original_path)
                    output_path = f"{base}_{counter}{ext}"
                    counter += 1
                
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
        
        # Generate unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"deleted_keys_{timestamp}.csv"
        
        file_path = filedialog.asksaveasfilename(
            title="Export Deleted Keys",
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        # Ensure unique filename if file exists
        if os.path.exists(file_path):
            base, ext = os.path.splitext(file_path)
            counter = 1
            while os.path.exists(file_path):
                file_path = f"{base}_{counter}{ext}"
                counter += 1
        
        try:
            # Collect all entries for keys to delete
            output_rows = []
            for key in self.keys_to_delete:
                # Get all locales for this key from all files
                for term_file_path, file_data in self.term_customizer_file_data.items():
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

