"""
Configuration Management for Decidim Translation Customizer

Handles loading and saving of user configuration.
"""

import os
import json


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config_file = os.path.join(os.path.expanduser("~"), ".decidim_translation_customizer.json")
        self.crowdin_file_paths = []  # List of file paths (backward compatible with single file)
        self.api_endpoint = 'https://api.openai.com/v1/chat/completions'
        self.api_key = ''
        self.api_model = 'gpt-4o-mini'
    
    def load(self):
        """Load saved configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Support both old format (single file) and new format (multiple files)
                    if 'crowdin_file_paths' in config:
                        # New format: multiple files
                        self.crowdin_file_paths = [
                            path for path in config['crowdin_file_paths']
                            if os.path.exists(path)
                        ]
                    elif 'crowdin_file_path' in config:
                        # Old format: single file (backward compatibility)
                        if os.path.exists(config['crowdin_file_path']):
                            self.crowdin_file_paths = [config['crowdin_file_path']]
                    # Load API settings
                    self.api_endpoint = config.get('api_endpoint', 'https://api.openai.com/v1/chat/completions')
                    self.api_key = config.get('api_key', '')
                    self.api_model = config.get('api_model', 'gpt-4o-mini')
        except Exception as e:
            # If config file is corrupted, just ignore it
            self.crowdin_file_paths = []
            self.api_endpoint = 'https://api.openai.com/v1/chat/completions'
            self.api_key = ''
            self.api_model = 'gpt-4o-mini'
    
    def save(self):
        """Save configuration"""
        try:
            config = {
                'crowdin_file_paths': self.crowdin_file_paths,
                'api_endpoint': self.api_endpoint,
                'api_key': self.api_key,
                'api_model': self.api_model
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            # Silently fail if we can't save config
            pass

