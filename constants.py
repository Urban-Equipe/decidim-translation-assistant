"""
Constants for Decidim Translation Assistant
"""

# Default API settings
DEFAULT_API_ENDPOINT = 'https://api.openai.com/v1/chat/completions'
DEFAULT_API_MODEL = 'gpt-4o-mini'
DEFAULT_BATCH_SIZE = 10
DEFAULT_TEMPERATURE = 0.1

# UI Strings
APP_TITLE = "Decidim Translation Assistant"
DEFAULT_WINDOW_SIZE = "1400x900"

# File types
XLIFF_EXTENSIONS = [("XLIFF files", "*.xliff"), ("All files", "*.*")]
CSV_EXTENSIONS = [("CSV files", "*.csv"), ("All files", "*.*")]

# Text formatting tags
TAG_HEADER = "header"
TAG_SUBHEADER = "subheader"
TAG_NUMBER = "number"
TAG_WARNING = "warning"
TAG_ERROR = "error"
TAG_ADDED = "added"
TAG_REMOVED = "removed"
TAG_ORIGINAL = "original"
TAG_CORRECTED = "corrected"
TAG_MATCH = "match"
TAG_REPLACEMENT = "replacement"

# Colors
COLOR_ADDED_BG = "#e6ffe6"
COLOR_REMOVED_BG = "#ffe6e6"
COLOR_ORIGINAL_BG = "#ffe6e6"
COLOR_CORRECTED_BG = "#e6ffe6"
COLOR_MATCH_BG = "#ffff99"
COLOR_REPLACEMENT_BG = "#99ff99"

# Fonts
FONT_COURIER = ("Courier", 10)
FONT_ARIAL = ("Arial", 11)
FONT_ARIAL_BOLD = ("Arial", 11, "bold")
FONT_ARIAL_HEADER = ("Arial", 12, "bold")

