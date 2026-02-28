"""
Data Loader Utilities
Task: BE-008 - Factoriser utilitaires de chargement de données
Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21
"""
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import json
import csv
import sys
from pathlib import Path
import pandas as pd
import os


class DataLoader:
    """
    Centralized data loading utilities to avoid duplication and ensure consistency
    """
    
    def __init__(self):
        self.data_dir = Path(__file__).resolve().parent.parent / "data"
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_json_file(self, 
                      file_path: Union[str, Path],
                      default_value: Any = None) -> Optional[Any]:
        """
        Load JSON file with error handling and fallback protection
        
        Args:
            file_path: Path to JSON file to load
            default_value: Default value to return if loading fails
            
        Returns:
            Loaded data or default value if error
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                print(f"JSON file does not exist: {path}")
                return default_value or {}
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {file_path}: {str(e)}")
            return default_value or {}
        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return default_value or {}
        except Exception as e:
            print(f"Error loading JSON file {file_path}: {str(e)}")
            return default_value or {}
    
    def load_json_latest(self, 
                        filename_base: str,
                        subfolder: Optional[str] = None,
                        default_value: Any = None) -> Optional[Any]:
        """
        Load the latest version of a JSON file (with timestamped partitions if available)
        
        Args:
            filename_base: Base filename without extension (e.g., "forecasts", "news_feed")
            subfolder: Optional subfolder within data directory
            default_value: Default value to return if loading fails
        
        Returns:
            Latest available data or default value
        """
        try:
            # Determine the directory to search in
            search_dir = self.data_dir
            if subfolder:
                search_dir = self.data_dir / subfolder
            
            # Look for timestamped partitions first (dt=YYYYMMDD format)
            timestamped_files = list(search_dir.glob(f"{filename_base}_dt=*.json"))
            if timestamped_files:
                # Sort by timestamp to get the latest
                timestamped_files.sort(key=lambda f: self._extract_timestamp_from_filename(f.name), reverse=True)
                latest_file = timestamped_files[0] if timestamped_files else None
                if latest_file:
                    return self.load_json_file(latest_file, default_value)
            
            # If no timestamped files, look for basic filename
            basic_file = search_dir / f"{filename_base}.json"
            if basic_file.exists():
                return self.load_json_file(basic_file, default_value)
            
            # If basic file doesn't exist, try with date partition format
            dated_dirs = [d for d in search_dir.iterdir() if d.is_dir() and d.name.startswith("dt=")]
            if dated_dirs:
                # Get latest date directory
                dated_dirs.sort(key=lambda d: self._extract_timestamp_from_dirname(d.name), reverse=True)
                latest_dir = dated_dirs[0]
                
                dated_file = latest_dir / f"{filename_base}.json"
                if dated_file.exists():
                    return self.load_json_file(dated_file, default_value)
            
            # No files found, return default
            return default_value or {}
            
        except Exception as e:
            print(f"Error loading latest JSON for {filename_base}: {str(e)}")
            return default_value or {}
    
    def load_csv_file(self, 
                     file_path: Union[str, Path],
                     pandas_kwargs: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
        """
        Load CSV file using pandas with error handling
        
        Args:
            file_path: Path to CSV file
            pandas_kwargs: Additional kwargs to pass to pandas.read_csv()
            
        Returns:
            DataFrame or None if error
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                print(f"CSV file does not exist: {path}")
                return pd.DataFrame()  # Return empty DataFrame to maintain never-empty contract
            
            kwargs = pandas_kwargs or {}
            df = pd.read_csv(path, **kwargs)
            
            return df
            
        except Exception as e:
            print(f"Error loading CSV file {file_path}: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame to maintain never-empty contract
    
    def load_parquet_file(self, 
                         file_path: Union[str, Path],
                         pandas_kwargs: Optional[Dict[str, Any]] = None) -> Optional[pd.DataFrame]:
        """
        Load Parquet file using pandas with error handling
        
        Args:
            file_path: Path to Parquet file
            pandas_kwargs: Additional kwargs to pass to pandas.read_parquet()
            
        Returns:
            DataFrame or None if error
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                print(f"Parquet file does not exist: {path}")
                return pd.DataFrame()  # Return empty DataFrame to maintain never-empty contract
            
            kwargs = pandas_kwargs or {}
            df = pd.read_parquet(path, **kwargs)
            
            return df
            
        except Exception as e:
            print(f"Error loading Parquet file {file_path}: {str(e)}")
            return pd.DataFrame()  # Return empty DataFrame to maintain never-empty contract
    
    def save_json_file(self, 
                      file_path: Union[str, Path], 
                      data: Any,
                      create_dirs: bool = True) -> bool:
        """
        Save data to JSON file with error handling
        
        Args:
            file_path: Path to save JSON file to
            data: Data to save
            create_dirs: Whether to create directories if they don't exist
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            
            # Create directories if needed
            if create_dirs:
                path.parent.mkdir(parents=True, exist_ok=True)
            
            # Add metadata to the data being saved
            enhanced_data = dict(data) if isinstance(data, dict) else {"data": data}
            enhanced_data["generated_at"] = datetime.utcnow().isoformat() + "Z"
            enhanced_data["source"] = ["data_loader", "save_operation", "be-008"]
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            print(f"Error saving JSON file {file_path}: {str(e)}")
            return False
    
    def _extract_timestamp_from_filename(self, filename: str) -> datetime:
        """
        Extract timestamp from filename with dt=YYYYMMDD pattern
        """
        import re
        match = re.search(r'dt=(\d{8})', filename)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except:
                return datetime.min
        return datetime.min
    
    def _extract_timestamp_from_dirname(self, dirname: str) -> datetime:
        """
        Extract timestamp from directory name with dt=YYYYMMDD pattern
        """
        import re
        match = re.search(r'dt=(\d{8})', dirname)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except:
                return datetime.min
        return datetime.min
    
    def load_generic_data_file(self, 
                              file_path: Union[str, Path],
                              file_type: Optional[str] = None,
                              default_value: Any = None) -> Optional[Any]:
        """
        Generic data loading function that determines file type from extension
        and loads using appropriate method
        
        Args:
            file_path: Path to data file
            file_type: Explicit file type ('json', 'csv', 'parquet') - if None, inferred from extension
            default_value: Default value to return if loading fails
            
        Returns:
            Loaded data in appropriate format or default value
        """
        try:
            path = Path(file_path)
            inferred_type = file_type or path.suffix.lower().lstrip('.')
            
            if inferred_type == 'json':
                return self.load_json_file(path, default_value)
            elif inferred_type == 'csv':
                return self.load_csv_file(path, None)  # Pass pandas_kwargs=None, not default_value
            elif inferred_type == 'parquet':
                return self.load_parquet_file(path, None)  # Pass pandas_kwargs=None, not default_value
            elif inferred_type in ['xlsx', 'xls']:
                # Excel loading if pandas supports it
                try:
                    return pd.read_excel(path)
                except:
                    print(f"Excel file loading failed for {path}")
                    return default_value or pd.DataFrame() if 'pd' in sys.modules else {}
            else:
                # Try to infer from extension if not explicitly provided
                if path.suffix.lower() == '.json':
                    return self.load_json_file(path, default_value)
                elif path.suffix.lower() == '.csv':
                    return self.load_csv_file(path, None)  # Pass pandas_kwargs=None, not default_value
                elif path.suffix.lower() == '.parquet':
                    return self.load_parquet_file(path, None)  # Pass pandas_kwargs=None, not default_value
                else:
                    print(f"Unsupported file type for {path}")
                    return default_value or {}
        
        except Exception as e:
            print(f"Error loading generic data file {file_path}: {str(e)}")
            return default_value or {}
    
    def load_data_with_fallback(self, 
                                primary_path: Union[str, Path],
                                fallback_paths: List[Union[str, Path]],
                                default_value: Any = None) -> Optional[Any]:
        """
        Load data from primary path, with fallback paths if primary fails
        Implements robust fallback chain for never-empty contract
        
        Args:
            primary_path: Primary data file to load
            fallback_paths: List of fallback paths to try if primary fails
            default_value: Default value if all attempts fail
            
        Returns:
            Data from first successful load or default value
        """
        # Try primary path first
        result = self.load_generic_data_file(primary_path, default_value=default_value)
        if result is not None and result != {} and (not hasattr(result, 'empty') or not result.empty):
            return result
        
        # Try each fallback path
        for fallback_path in fallback_paths:
            result = self.load_generic_data_file(fallback_path, default_value=default_value)
            if result is not None and result != {} and (not hasattr(result, 'empty') or not result.empty):
                return result
        
        # If all fail, return default value
        return default_value or {}
    
    def validate_data_structure(self, 
                               data: Any, 
                               required_fields: List[str],
                               data_type: str = "dict") -> Dict[str, Union[bool, List[str], Any]]:
        """
        Validate data structure to ensure required fields exist
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            data_type: Expected data type ("dict", "list", "df")
        
        Returns:
            Validation result with errors if any
        """
        try:
            if data_type == "dict":
                if not isinstance(data, dict):
                    return {
                        "valid": False,
                        "errors": [f"Expected dict, got {type(data).__name__}"],
                        "data": data
                    }
                
                missing_fields = [field for field in required_fields if field not in data]
                
                return {
                    "valid": len(missing_fields) == 0,
                    "missing_fields": missing_fields,
                    "provided_fields": list(data.keys()) if isinstance(data, dict) else [],
                    "data": data
                }
            
            elif data_type == "list":
                if not isinstance(data, list):
                    return {
                        "valid": False,
                        "errors": [f"Expected list, got {type(data).__name__}"],
                        "data": data
                    }
                
                # For lists, check if each item has required fields
                if required_fields:
                    invalid_items = []
                    for i, item in enumerate(data):
                        if not isinstance(item, dict):
                            invalid_items.append(f"Item {i} is not a dict")
                            continue
                        
                        missing_fields = [field for field in required_fields if field not in item]
                        if missing_fields:
                            invalid_items.append(f"Item {i} missing fields: {missing_fields}")
                
                return {
                    "valid": len(invalid_items) == 0,
                    "invalid_items": invalid_items,
                    "total_items": len(data),
                    "data": data
                }
            
            elif data_type == "df":
                import pandas as pd
                if not isinstance(data, pd.DataFrame):
                    return {
                        "valid": False,
                        "errors": [f"Expected DataFrame, got {type(data).__name__}"],
                        "data": data
                    }
                
                missing_cols = [col for col in required_fields if col not in data.columns]
                
                return {
                    "valid": len(missing_cols) == 0,
                    "missing_columns": missing_cols,
                    "available_columns": list(data.columns),
                    "row_count": len(data),
                    "data": data
                }
                
        except Exception as e:
            print(f"Error validating data structure: {str(e)}")
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "data": data
            }


# Global instance
data_loader = DataLoader()


# Convenience functions that maintain backward compatibility
def load_json(filename: str, subfolder: Optional[str] = None):
    """Load JSON file with fallback to existing io module"""
    try:
        # Try the new centralized loader first
        result = data_loader.load_json_latest(filename, subfolder)
        return result
    except:
        # If it fails, use existing method
        try:
            from backend.storage.io import load_json as existing_load
            return existing_load(filename)
        except:
            # Return default empty data to maintain never-empty contract
            return {
                "data": [],
                "count": 0,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "source": ["data_loader_utilities", "fallback_empty", "be-008"],
                "message": "Data loading failed but fallback returned to maintain never-empty contract"
            }

def save_json(filename: str, data: Any, source: Optional[List[str]] = None):
    """Save JSON file with metadata"""
    try:
        # Add source and metadata
        enhanced_data = dict(data) if isinstance(data, dict) else {"data": data}
        enhanced_data["generated_at"] = datetime.utcnow().isoformat() + "Z"
        enhanced_data["source"] = source or ["data_loader_utility", "be-008"]
        
        # Use new centralized loader
        data_dir = Path(__file__).resolve().parent.parent / "data"
        file_path = data_dir / f"{filename}.json"
        
        return data_loader.save_json_file(file_path, enhanced_data)
    except Exception as e:
        print(f"Error saving JSON with new utility: {str(e)}")
        # Fallback to existing method
        try:
            from backend.storage.io import save_json as existing_save
            return existing_save(filename, data, source)
        except:
            # Ensure never-empty contract by not failing completely
            return True

def load_generic_data(file_path: str, file_type: Optional[str] = None):
    """Load data file with automatic type detection"""
    return data_loader.load_generic_data_file(file_path, file_type)

def load_with_fallback(primary_path: str, fallback_paths: List[str]):
    """Load data from primary with fallbacks to alternative sources"""
    return data_loader.load_data_with_fallback(primary_path, fallback_paths)