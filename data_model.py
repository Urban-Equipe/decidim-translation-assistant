"""
Data Model for Decidim Translation Assistant

Manages application state and data structures.
"""


class DataModel:
    """Manages application data state"""
    
    def __init__(self):
        # File paths
        self.crowdin_files = []  # List of XLIFF file paths
        self.term_customizer_files = []  # List of file paths
        
        # File data
        self.crowdin_file_data = {}  # Data per XLIFF file: {file_path: {key: {'source': value, 'target': value}}}
        self.crowdin_languages = {}  # Languages per XLIFF file: {file_path: {'source': 'en', 'target': 'de'}}
        self.term_customizer_data = {}  # Combined data from all files
        self.term_customizer_file_data = {}  # Data per file: {file_path: {key: {locale: value}}}
        
        # Comparison results
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}  # {file_path: {key: entry}}
        self.term_customizer_locales = set()
        self.keys_to_delete = []  # Keys that exist only in Term Customizer
        
        # Grammar check and tone adjustment data
        self.grammar_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.tone_corrections = {}  # {file_path: {key: {locale: {'original': value, 'corrected': value}}}}
        self.gc_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for grammar check
        
        # Search & Replace data
        self.sr_direct_files = {}  # {file_path: {key: {locale: value}}} - Files loaded directly for search/replace
        self.replacement_preview = {}  # {file_path: {key: {locale: {'old': value, 'new': value}}}}
        self.last_sr_output_files = []  # List of most recently created output files
    
    def clear_term_customizer_files(self):
        """Clear all Term Customizer files and related data"""
        self.term_customizer_files = []
        self.term_customizer_data = {}
        self.term_customizer_file_data = {}
        self.term_customizer_locales = set()
    
    def clear_crowdin_file(self, file_path):
        """Remove a Crowdin file and its data"""
        if file_path in self.crowdin_files:
            self.crowdin_files.remove(file_path)
        if file_path in self.crowdin_file_data:
            del self.crowdin_file_data[file_path]
        if file_path in self.crowdin_languages:
            del self.crowdin_languages[file_path]
    
    def clear_comparison_results(self):
        """Clear comparison results"""
        self.mismatched_entries = {}
        self.mismatched_entries_per_file = {}
        self.keys_to_delete = []
    
    def clear_grammar_results(self):
        """Clear grammar check and tone adjustment results"""
        self.grammar_corrections = {}
        self.tone_corrections = {}

