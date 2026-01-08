"""
Base view class for tab views
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from tkinter.font import Font


class BaseView:
    """Base class for tab views"""
    
    def __init__(self, parent_frame, app):
        """
        Initialize the view
        
        Args:
            parent_frame: The parent frame (tab frame)
            app: Reference to the main application instance
        """
        self.parent_frame = parent_frame
        self.app = app
        self.container = None
    
    def create(self):
        """Create the view UI - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create()")
    
    def update(self):
        """Update the view with current data - to be implemented by subclasses"""
        pass
    
    def destroy(self):
        """Clean up the view"""
        if self.container:
            self.container.destroy()

