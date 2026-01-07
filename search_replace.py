"""
Search & Replace functionality for Decidim Translation Customizer

Handles search and replace operations across files.
"""

import re


class SearchReplaceHandler:
    """Handles search and replace operations"""
    
    @staticmethod
    def should_replace(text, search_term, case_sensitive, whole_word):
        """Check if text should be replaced based on options"""
        if not text:
            return False
        
        if not case_sensitive:
            text_lower = text.lower()
            search_lower = search_term.lower()
        else:
            text_lower = text
            search_lower = search_term
        
        if whole_word:
            # Use word boundaries for whole word matching
            pattern = r'\b' + re.escape(search_lower) + r'\b'
            if not case_sensitive:
                return bool(re.search(pattern, text_lower, re.IGNORECASE))
            else:
                return bool(re.search(pattern, text_lower))
        else:
            return search_lower in text_lower
    
    @staticmethod
    def replace_text(text, search_term, replace_term, case_sensitive, whole_word):
        """Replace text based on options"""
        if whole_word:
            if case_sensitive:
                pattern = r'\b' + re.escape(search_term) + r'\b'
                return re.sub(pattern, replace_term, text)
            else:
                pattern = r'(?i)\b' + re.escape(search_term) + r'\b'
                return re.sub(pattern, replace_term, text, flags=re.IGNORECASE)
        else:
            if case_sensitive:
                return text.replace(search_term, replace_term)
            else:
                # Case-insensitive replace
                return re.sub(re.escape(search_term), replace_term, text, flags=re.IGNORECASE)


