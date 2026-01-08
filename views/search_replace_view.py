"""
Search & Replace View for Decidim Translation Assistant
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.font import Font
from .base_view import BaseView
from constants import (
    TAG_MATCH, TAG_REPLACEMENT, TAG_HEADER,
    COLOR_MATCH_BG, COLOR_REPLACEMENT_BG, FONT_COURIER
)


class SearchReplaceView(BaseView):
    """View for the Search & Replace tab"""
    
    def create(self):
        """Create the Search & Replace tab UI"""
        self.container = ttk.Frame(self.parent_frame)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top section: File selection and search/replace inputs
        top_section = ttk.LabelFrame(self.container, text="Search & Replace Configuration", padding="10")
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
                  command=self.app.preview_replacements).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Apply Replacements", 
                  command=self.app.apply_replacements).pack(side=tk.LEFT, padx=5)
        
        # Preview section
        preview_section = ttk.LabelFrame(self.container, text="Preview", padding="10")
        preview_section.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_text = scrolledtext.ScrolledText(preview_section, wrap=tk.WORD, 
                                                      font=FONT_COURIER,
                                                      height=15)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure preview text tags
        self.preview_text.tag_config(TAG_MATCH, background=COLOR_MATCH_BG, foreground="black")
        self.preview_text.tag_config(TAG_REPLACEMENT, background=COLOR_REPLACEMENT_BG, foreground="black")
        self.preview_text.tag_config(TAG_HEADER, font=Font(weight="bold"), foreground="navy")
        
        # Store references in app
        self.app.sr_crowdin_file_vars = self.sr_crowdin_file_vars
        self.app.sr_term_file_vars = self.sr_term_file_vars
        self.app.sr_crowdin_checkboxes_frame = self.sr_crowdin_checkboxes_frame
        self.app.sr_term_checkboxes_frame = self.sr_term_checkboxes_frame
        self.app.search_term_var = self.search_term_var
        self.app.replace_term_var = self.replace_term_var
        self.app.sr_language_var = self.sr_language_var
        self.app.sr_language_combo = self.sr_language_combo
        self.app.sr_case_sensitive_var = self.sr_case_sensitive_var
        self.app.sr_whole_word_var = self.sr_whole_word_var
        self.app.preview_text = self.preview_text
        
        # Initialize replacement data storage
        self.app.replacement_preview = {}  # {file_path: {key: {locale: {'old': value, 'new': value}}}}
        self.app._sr_update_scheduled = None  # For debouncing language updates
        self.app.sr_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for search/replace
        self.app.last_sr_output_files = []  # List of most recently created output files for easy reloading
        
        # Cache for language lists to avoid repeated expensive operations
        self.app._sr_languages_cache = None
        self.app._sr_languages_cache_valid = False
        
        # Initialize file selection lazily (only when tab is accessed)
        # Don't call update functions here - they'll be called when needed
        self.app.root.after_idle(self.app.update_sr_file_selection)

