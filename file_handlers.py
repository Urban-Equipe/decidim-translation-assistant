"""
File Handlers for Decidim Translation Customizer

Handles XLIFF and CSV file loading and saving operations.
"""

import csv
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from tkinter import messagebox


class FileHandler:
    """Handles file operations for XLIFF and CSV files"""
    
    @staticmethod
    def load_xliff_file(file_path):
        """Parse XLIFF file and extract translation data"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Get namespace from root element (XLIFF uses default namespace)
            namespace = ''
            if root.tag.startswith('{'):
                namespace = root.tag.split('}')[0] + '}'
            
            # Helper function to create namespaced tag
            def ns_tag(tag):
                return f'{namespace}{tag}' if namespace else tag
            
            # Get source and target languages from file element
            file_elem = root.find(f'.//{ns_tag("file")}')
            
            source_lang = 'en'
            target_lang = ''
            
            if file_elem is not None:
                source_lang = file_elem.get('source-language', 'en').lower()
                target_lang = file_elem.get('target-language', '').lower()
            
            data = {}
            
            # Find all trans-unit elements
            trans_units = root.findall(f'.//{ns_tag("trans-unit")}')
            
            for trans_unit in trans_units:
                # Get the key from resname attribute
                key = trans_unit.get('resname', '')
                if not key:
                    continue
                
                # Get source text
                source_elem = trans_unit.find(ns_tag('source'))
                source_text = source_elem.text if source_elem is not None and source_elem.text else ''
                
                # Get target text
                target_elem = trans_unit.find(ns_tag('target'))
                target_text = target_elem.text if target_elem is not None and target_elem.text else ''
                
                data[key] = {
                    'target': target_text,
                    'source': source_text
                }
            
            return data, len(data), source_lang, target_lang
            
        except ET.ParseError as e:
            raise Exception(f"XML parsing error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error parsing XLIFF file: {str(e)}")
    
    @staticmethod
    def load_csv_file(file_path):
        """Load a CSV file and return data structure"""
        try:
            file_data = {}
            file_locales = set()
            
            with open(file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';')
                for row in reader:
                    key = row.get('key', '')
                    value = row.get('value', '')
                    locale = row.get('locale', '').lower()
                    if key and locale:
                        if key not in file_data:
                            file_data[key] = {}
                        file_data[key][locale] = value
                        file_locales.add(locale)
            
            return file_data, file_locales
            
        except Exception as e:
            raise Exception(f"Error loading CSV file: {str(e)}")
    
    @staticmethod
    def save_csv_file(output_path, output_rows, fieldnames=None):
        """Save data to a CSV file"""
        if fieldnames is None:
            fieldnames = ['locale', 'key', 'value']
        
        # Ensure unique filename
        counter = 1
        original_path = output_path
        while os.path.exists(output_path):
            base, ext = os.path.splitext(original_path)
            output_path = f"{base}_{counter}{ext}"
            counter += 1
        
        with open(output_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(output_rows)
        
        return output_path
    
    @staticmethod
    def generate_timestamped_filename(base_name, suffix, extension='.csv'):
        """Generate a timestamped filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            if not suffix.startswith('_'):
                suffix = '_' + suffix
            filename = f"{base_name}{suffix}_{timestamp}{extension}"
        else:
            filename = f"{base_name}_{timestamp}{extension}"
        return filename



