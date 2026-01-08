"""
Grammar Check & Tone Adjustment View for Decidim Translation Assistant
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.font import Font
from .base_view import BaseView
from constants import (
    TAG_HEADER, TAG_SUBHEADER, TAG_NUMBER, TAG_WARNING, TAG_ERROR,
    TAG_ORIGINAL, TAG_CORRECTED,
    COLOR_ORIGINAL_BG, COLOR_CORRECTED_BG,
    FONT_COURIER, FONT_ARIAL, FONT_ARIAL_BOLD, FONT_ARIAL_HEADER,
    DEFAULT_API_ENDPOINT, DEFAULT_API_MODEL, DEFAULT_BATCH_SIZE, DEFAULT_TEMPERATURE
)


class GrammarCheckView(BaseView):
    """View for the Grammar Check & Tone Adjustment tab"""
    
    def create(self):
        """Create the Grammar Check & Tone Adjustment tab UI"""
        self.container = ttk.Frame(self.parent_frame, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # File Selection & Processing Settings box
        settings_box = ttk.LabelFrame(self.container, text="File Selection & Processing Settings", padding="10")
        settings_box.pack(fill=tk.X, pady=5)
        
        # API Configuration
        api_frame = ttk.Frame(settings_box)
        api_frame.pack(fill=tk.X, pady=5)
        
        # API Endpoint
        endpoint_frame = ttk.Frame(api_frame)
        endpoint_frame.pack(fill=tk.X, pady=2)
        ttk.Label(endpoint_frame, text="API Endpoint:").pack(side=tk.LEFT, padx=5)
        self.gc_api_endpoint_var = tk.StringVar(value=getattr(self.app, 'api_endpoint', DEFAULT_API_ENDPOINT))
        endpoint_entry = ttk.Entry(endpoint_frame, textvariable=self.gc_api_endpoint_var, width=50)
        endpoint_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # API Key
        key_frame = ttk.Frame(api_frame)
        key_frame.pack(fill=tk.X, pady=2)
        ttk.Label(key_frame, text="API Key:").pack(side=tk.LEFT, padx=5)
        self.gc_api_key_var = tk.StringVar(value=getattr(self.app, 'api_key', ''))
        key_entry = ttk.Entry(key_frame, textvariable=self.gc_api_key_var, width=50, show="*")
        key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Model
        model_frame = ttk.Frame(api_frame)
        model_frame.pack(fill=tk.X, pady=2)
        ttk.Label(model_frame, text="Model:").pack(side=tk.LEFT, padx=5)
        model_value = getattr(self.app, 'api_model', DEFAULT_API_MODEL)
        self.gc_model_var = tk.StringVar(value=model_value)
        model_entry = ttk.Entry(model_frame, textvariable=self.gc_model_var, width=50)
        model_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # API settings buttons
        api_buttons_frame = ttk.Frame(api_frame)
        api_buttons_frame.pack(pady=5)
        ttk.Button(api_buttons_frame, text="Save API Settings", 
                  command=self.app.save_api_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(api_buttons_frame, text="Test Connection", 
                  command=self.app.test_llm_connection).pack(side=tk.LEFT, padx=5)
        
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
        self.gc_batch_size_var = tk.IntVar(value=DEFAULT_BATCH_SIZE)
        batch_spin = ttk.Spinbox(batch_frame, from_=1, to=50, textvariable=self.gc_batch_size_var, width=10)
        batch_spin.pack(side=tk.LEFT, padx=5)
        
        # Temperature
        temp_frame = ttk.Frame(options_row)
        temp_frame.pack(side=tk.LEFT, padx=5)
        ttk.Label(temp_frame, text="Temperature:").pack(side=tk.LEFT, padx=5)
        self.gc_temperature_var = tk.DoubleVar(value=DEFAULT_TEMPERATURE)
        temp_spin = ttk.Spinbox(temp_frame, from_=0.0, to=0.2, increment=0.1, 
                               textvariable=self.gc_temperature_var, width=10, format="%.1f")
        temp_spin.pack(side=tk.LEFT, padx=5)
        
        # Tone adjustment section
        tone_section = ttk.LabelFrame(self.container, text="Tone Adjustments", padding="10")
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
        button_frame = ttk.Frame(self.container)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Initialize check and adjustments", 
                  command=self.app.initialize_check_and_adjustments).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save", 
                  command=self.app.save_grammar_corrections).pack(side=tk.LEFT, padx=5)
        
        # Paned window for preview and statistics
        paned = ttk.PanedWindow(self.container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left pane: Preview
        preview_container = ttk.LabelFrame(paned, text="Preview", padding="5")
        paned.add(preview_container, weight=1)
        
        self.grammar_preview_text = scrolledtext.ScrolledText(preview_container, wrap=tk.WORD, 
                                                             font=FONT_COURIER)
        self.grammar_preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure preview text tags
        self.grammar_preview_text.tag_config(TAG_ORIGINAL, background=COLOR_ORIGINAL_BG, foreground="black")
        self.grammar_preview_text.tag_config(TAG_CORRECTED, background=COLOR_CORRECTED_BG, foreground="black")
        self.grammar_preview_text.tag_config(TAG_HEADER, font=Font(weight="bold"), foreground="navy")
        self.grammar_preview_text.tag_config(TAG_ERROR, foreground="red")
        
        # Right pane: Statistics
        stats_container = ttk.LabelFrame(paned, text="Statistics", padding="5")
        paned.add(stats_container, weight=1)
        
        self.gc_stats_text = scrolledtext.ScrolledText(stats_container, wrap=tk.WORD, 
                                                       font=FONT_ARIAL)
        self.gc_stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for statistics highlighting
        self.gc_stats_text.tag_config(TAG_HEADER, font=FONT_ARIAL_HEADER, foreground="navy")
        self.gc_stats_text.tag_config(TAG_SUBHEADER, font=FONT_ARIAL_BOLD, foreground="darkblue")
        self.gc_stats_text.tag_config(TAG_NUMBER, font=FONT_ARIAL_BOLD, foreground="darkgreen")
        self.gc_stats_text.tag_config(TAG_WARNING, foreground="orange")
        self.gc_stats_text.tag_config(TAG_ERROR, foreground="red")
        self.gc_stats_text.config(state=tk.DISABLED)
        
        # Store references in app
        self.app.gc_api_endpoint_var = self.gc_api_endpoint_var
        self.app.gc_api_key_var = self.gc_api_key_var
        self.app.gc_model_var = self.gc_model_var
        self.app.gc_crowdin_file_vars = self.gc_crowdin_file_vars
        self.app.gc_term_file_vars = self.gc_term_file_vars
        self.app.gc_crowdin_checkboxes_frame = self.gc_crowdin_checkboxes_frame
        self.app.gc_term_checkboxes_frame = self.gc_term_checkboxes_frame
        self.app.gc_language_var = self.gc_language_var
        self.app.gc_language_combo = self.gc_language_combo
        self.app.gc_batch_size_var = self.gc_batch_size_var
        self.app.gc_temperature_var = self.gc_temperature_var
        self.app.gc_tone_var = self.gc_tone_var
        self.app.grammar_preview_text = self.grammar_preview_text
        self.app.gc_stats_text = self.gc_stats_text
        
        # Initialize grammar check and tone adjustment data
        self.app.grammar_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.app.tone_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.app._gc_language_update_scheduled = None  # For debouncing language updates
        
        # Cache for language lists to avoid repeated expensive operations
        self.app._gc_languages_cache = None
        self.app._gc_languages_cache_valid = False
        self.app.gc_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for grammar check
        
        # Initialize file selection lazily (only when tab is accessed)
        self.app.root.after_idle(self.app.update_gc_file_selection)

