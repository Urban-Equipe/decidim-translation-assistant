"""
Comparison Logic for Decidim Translation Customizer

Handles file comparison and statistics calculation.
"""

import os


class ComparisonLogic:
    """Handles comparison logic and statistics"""
    
    @staticmethod
    def normalize_value(value, case_sensitive):
        """Normalize value based on case sensitivity setting"""
        if not case_sensitive:
            return value.strip().lower() if value else ''
        return value.strip() if value else ''
    
    @staticmethod
    def values_differ(val1, val2, include_empty, case_sensitive):
        """Compare two values based on settings"""
        # If include_empty is False, skip comparison if either value is empty
        if not include_empty:
            if not val1 or not val2:
                return False
        # Compare normalized values
        return ComparisonLogic.normalize_value(val1, case_sensitive) != ComparisonLogic.normalize_value(val2, case_sensitive)
    
    @staticmethod
    def should_check_value(term_value, require_value):
        """Determine if we should check this value based on require_term_value setting"""
        if require_value:
            # Only check if term customizer value exists
            return bool(term_value)
        else:
            # Check regardless of whether term customizer value exists
            return True
    
    @staticmethod
    def calculate_statistics(crowdin_data, term_customizer_file_data, mismatched_entries, 
                           mismatched_entries_per_file, term_customizer_files, xliff_source_language, 
                           xliff_target_language, term_customizer_locales):
        """Calculate comparison statistics"""
        stats = {
            'total_crowdin_keys': len(crowdin_data),
            'total_term_customizer_keys': 0,
            'keys_in_both': 0,
            'keys_only_in_crowdin': 0,
            'keys_only_in_term_customizer': 0,
            'mismatched_keys': len(mismatched_entries),
            'matching_keys': 0,
            'total_locales_compared': len(term_customizer_locales),
            'per_file_stats': {}
        }
        
        # Get all unique keys from term customizer
        all_term_keys = set()
        for file_path, file_data in term_customizer_file_data.items():
            all_term_keys.update(file_data.keys())
        
        stats['total_term_customizer_keys'] = len(all_term_keys)
        
        # Calculate keys in both
        crowdin_keys = set(crowdin_data.keys())
        stats['keys_in_both'] = len(crowdin_keys & all_term_keys)
        stats['keys_only_in_crowdin'] = len(crowdin_keys - all_term_keys)
        keys_only_in_term = all_term_keys - crowdin_keys
        stats['keys_only_in_term_customizer'] = len(keys_only_in_term)
        
        # Calculate matching keys (in both but no mismatches)
        keys_in_both = set(crowdin_data.keys()) & all_term_keys
        stats['matching_keys'] = max(0, len(keys_in_both) - stats['mismatched_keys'])
        
        # Per-file statistics
        for file_path in term_customizer_files:
            file_data = term_customizer_file_data.get(file_path, {})
            file_mismatches = mismatched_entries_per_file.get(file_path, {})
            file_keys = set(file_data.keys())
            
            keys_in_crowdin = len(file_keys & set(crowdin_data.keys()))
            file_stats = {
                'total_keys': len(file_keys),
                'keys_in_crowdin': keys_in_crowdin,
                'keys_only_in_file': len(file_keys - set(crowdin_data.keys())),
                'mismatched_keys': len(file_mismatches),
                'matching_keys': max(0, keys_in_crowdin - len(file_mismatches))
            }
            stats['per_file_stats'][os.path.basename(file_path)] = file_stats
        
        return stats

