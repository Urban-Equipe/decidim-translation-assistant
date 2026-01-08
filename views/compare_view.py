"""
Compare View for Decidim Translation Assistant
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.font import Font
from .base_view import BaseView
from constants import (
    TAG_HEADER, TAG_SUBHEADER, TAG_NUMBER, TAG_WARNING, TAG_ERROR,
    TAG_ADDED, TAG_REMOVED, COLOR_ADDED_BG, COLOR_REMOVED_BG,
    FONT_COURIER, FONT_ARIAL, FONT_ARIAL_BOLD, FONT_ARIAL_HEADER
)


class CompareView(BaseView):
    """View for the Compare tab"""
    
    def create(self):
        """Create the Compare tab UI"""
        # Main container
        self.container = ttk.Frame(self.parent_frame, padding="10")
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Settings section
        settings_frame = ttk.LabelFrame(self.container, text="Comparison Settings", padding="10")
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
                  command=self.app.compare_files).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_row, text="Save Results", 
                  command=self.app.save_results).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_row, text="Export Deleted Keys", 
                  command=self.app.export_deleted_keys).pack(side=tk.LEFT, padx=5)
        
        # Paned window for diff view and statistics
        paned = ttk.PanedWindow(self.container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left pane: Diff View
        diff_container = ttk.LabelFrame(paned, text="Diff View", padding="5")
        paned.add(diff_container, weight=1)
        
        self.diff_text = scrolledtext.ScrolledText(diff_container, wrap=tk.NONE, 
                                                   font=FONT_COURIER)
        self.diff_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for diff highlighting
        self.diff_text.tag_config(TAG_ADDED, foreground="green", background=COLOR_ADDED_BG)
        self.diff_text.tag_config(TAG_REMOVED, foreground="red", background=COLOR_REMOVED_BG)
        self.diff_text.tag_config(TAG_HEADER, foreground="blue", font=Font(family="Courier", size=10, weight="bold"))
        self.diff_text.config(state=tk.DISABLED)
        
        # Right pane: Statistics
        stats_container = ttk.LabelFrame(paned, text="Statistics", padding="5")
        paned.add(stats_container, weight=1)
        
        self.stats_text = scrolledtext.ScrolledText(stats_container, wrap=tk.WORD, 
                                                    font=FONT_ARIAL)
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for statistics highlighting
        self.stats_text.tag_config(TAG_HEADER, font=FONT_ARIAL_HEADER, foreground="navy")
        self.stats_text.tag_config(TAG_SUBHEADER, font=FONT_ARIAL_BOLD, foreground="darkblue")
        self.stats_text.tag_config(TAG_NUMBER, font=FONT_ARIAL_BOLD, foreground="darkgreen")
        self.stats_text.tag_config(TAG_WARNING, foreground="orange")
        self.stats_text.tag_config(TAG_ERROR, foreground="red")
        self.stats_text.config(state=tk.DISABLED)
        
        # Store references in app for access from main class
        self.app.locale_info_label = self.locale_info_label
        self.app.require_term_value_var = self.require_term_value_var
        self.app.include_empty_var = self.include_empty_var
        self.app.case_sensitive_var = self.case_sensitive_var
        self.app.save_mode_var = self.save_mode_var
        self.app.output_suffix_var = self.output_suffix_var
        self.app.diff_text = self.diff_text
        self.app.stats_text = self.stats_text

