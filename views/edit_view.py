"""
Edit View for Decidim Translation Assistant
"""

import tkinter as tk
from tkinter import ttk
from .base_view import BaseView


class EditView(BaseView):
    """View for the Edit Translations tab"""
    
    def create(self):
        """Create the Edit tab UI"""
        self.container = ttk.Frame(self.parent_frame)
        self.container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Treeview with scrollbars
        tree_frame = ttk.Frame(self.container)
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
        self.edit_tree.bind("<Double-1>", self.app.on_item_double_click)
        
        # Store reference in app
        self.app.edit_tree = self.edit_tree
        self.app.editable_values = {}

