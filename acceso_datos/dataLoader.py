import json
from typing import Optional, Tuple

class DataLoader: 
    """
    Handles loading and parsing JSON data from file streams.
    
    Responsibilities:
    - Read JSON from streams (Flask uploads)
    - Validate JSON structure
    - Expose raw parsed data to orchestrators
    """
    
    def __init__(self):
        """Initialize the DataLoader."""
        self.raw_data = None
    
    def load_from_stream(self, stream) -> Tuple[bool, Optional[str]]:
        """
        Load and parse JSON content from an open file-like stream.

        Args:
            stream: Readable stream that provides JSON content.

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message).
        """
        try:
            if hasattr(stream, "seek"):
                stream.seek(0)
            self.raw_data = json.load(stream)
            return True, None
        except json.JSONDecodeError as e:
            return False, f"JSON inválido: {e}"
        except Exception as e:
            return False, f"Error leyendo archivo: {e}"
        
    def get_raw_data(self) -> Optional[dict]:
        """
        Get the raw loaded JSON data.
        
        Returns:
            dict: Raw JSON data, or None if not loaded.
        """
        return self.raw_data