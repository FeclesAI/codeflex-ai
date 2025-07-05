"""
Data processing and validation utilities
"""
import json
import csv
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from loguru import logger

import pandas as pd
from cerberus import Validator


class DataProcessor:
    """
    Data processing, cleaning, and validation utilities
    """
    
    def __init__(self):
        self.seen_hashes = set()
        self.duplicate_count = 0
    
    def get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text data"""
        if not isinstance(text, str):
            return str(text) if text is not None else ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        # Normalize quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        
        return text
    
    def clean_url(self, url: str) -> str:
        """Clean and normalize URL"""
        if not url:
            return ""
        
        # Remove fragments and unnecessary parameters
        url = url.split('#')[0]
        
        # Normalize protocol
        if url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def extract_numbers(self, text: str) -> List[float]:
        """Extract numbers from text"""
        if not text:
            return []
        
        # Find all numbers (including decimals)
        numbers = re.findall(r'-?\d+\.?\d*', text)
        return [float(num) for num in numbers if num]
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        if not text:
            return []
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return re.findall(email_pattern, text)
    
    def extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        if not text:
            return []
        
        # Various phone number patterns
        patterns = [
            r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',
            r'\+?([0-9]{1,3})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})[-.\s]?([0-9]{3,4})'
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, tuple):
                    phone = ''.join(match)
                else:
                    phone = match
                phones.append(phone)
        
        return phones
    
    def calculate_hash(self, data: Union[str, Dict, List]) -> str:
        """Calculate hash for duplicate detection"""
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def is_duplicate(self, data: Union[str, Dict, List]) -> bool:
        """Check if data is duplicate"""
        data_hash = self.calculate_hash(data)
        
        if data_hash in self.seen_hashes:
            self.duplicate_count += 1
            return True
        
        self.seen_hashes.add(data_hash)
        return False
    
    def validate_data(self, data: Dict, schema: Dict) -> Dict[str, Any]:
        """Validate data against schema"""
        validator = Validator(schema)
        
        if validator.validate(data):
            return {'valid': True, 'data': data}
        else:
            return {
                'valid': False,
                'errors': validator.errors,
                'data': data
            }
    
    def save_to_json(self, data: List[Dict], filepath: Union[str, Path], indent: int = 2):
        """Save data to JSON file"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            
            logger.info(f"Saved {len(data)} records to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
    
    def save_to_csv(self, data: List[Dict], filepath: Union[str, Path]):
        """Save data to CSV file"""
        if not data:
            logger.warning("No data to save to CSV")
            return
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Flatten nested dictionaries
            flattened_data = []
            for item in data:
                flattened_item = self._flatten_dict(item)
                flattened_data.append(flattened_item)
            
            # Get all unique keys
            all_keys = set()
            for item in flattened_data:
                all_keys.update(item.keys())
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
                writer.writeheader()
                writer.writerows(flattened_data)
            
            logger.info(f"Saved {len(data)} records to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
    
    def save_to_excel(self, data: List[Dict], filepath: Union[str, Path]):
        """Save data to Excel file"""
        if not data:
            logger.warning("No data to save to Excel")
            return
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Flatten nested dictionaries
            flattened_data = []
            for item in data:
                flattened_item = self._flatten_dict(item)
                flattened_data.append(flattened_item)
            
            df = pd.DataFrame(flattened_data)
            df.to_excel(filepath, index=False)
            
            logger.info(f"Saved {len(data)} records to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving to Excel: {e}")
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary"""
        items = []
        
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert list to string representation
                items.append((new_key, json.dumps(v) if v else ''))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def get_duplicate_stats(self) -> Dict[str, int]:
        """Get duplicate detection statistics"""
        return {
            'total_processed': len(self.seen_hashes) + self.duplicate_count,
            'unique_items': len(self.seen_hashes),
            'duplicates_found': self.duplicate_count,
            'duplicate_rate': (
                self.duplicate_count / (len(self.seen_hashes) + self.duplicate_count)
                if (len(self.seen_hashes) + self.duplicate_count) > 0 else 0
            )
        }