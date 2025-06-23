"""Security utilities for the research system."""
import os
from pathlib import Path
from typing import Optional
import re
import html
import secrets
import string

class SecurityConfig:
    """Security configuration and utilities."""
    
    # Allowed file extensions for various operations
    ALLOWED_EXPORT_EXTENSIONS = {'.json', '.md', '.txt'}
    ALLOWED_READ_EXTENSIONS = {'.json', '.md', '.txt', '.yaml', '.yml', '.log', '.jsonl'}
    
    # Path constraints
    MAX_PATH_LENGTH = 255
    MAX_FILENAME_LENGTH = 100
    
    @staticmethod
    def validate_path(path: Path, base_dir: Optional[Path] = None, 
                     create_parent: bool = False) -> Path:
        """
        Validate and sanitize a file path to prevent path traversal attacks.
        
        Args:
            path: The path to validate
            base_dir: Optional base directory to ensure path is within
            create_parent: Whether to create parent directories if they don't exist
            
        Returns:
            Validated Path object
            
        Raises:
            ValueError: If path is invalid or outside allowed directory
        """
        # Convert to Path object if string
        if isinstance(path, str):
            path = Path(path)
        
        # Resolve to absolute path and remove any '..' components
        try:
            path = path.resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")
        
        # Check path length
        if len(str(path)) > SecurityConfig.MAX_PATH_LENGTH:
            raise ValueError(f"Path too long: {len(str(path))} > {SecurityConfig.MAX_PATH_LENGTH}")
        
        # Check filename length
        if len(path.name) > SecurityConfig.MAX_FILENAME_LENGTH:
            raise ValueError(f"Filename too long: {len(path.name)} > {SecurityConfig.MAX_FILENAME_LENGTH}")
        
        # If base_dir is provided, ensure path is within it
        if base_dir:
            base_dir = Path(base_dir).resolve()
            try:
                # Check if path is relative to base_dir
                path.relative_to(base_dir)
            except ValueError:
                raise ValueError(f"Path '{path}' is outside allowed directory '{base_dir}'")
        
        # Create parent directory if requested and it doesn't exist
        if create_parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        
        return path
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 100) -> str:
        """
        Sanitize a filename to remove potentially dangerous characters.
        
        Args:
            filename: The filename to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized filename
        """
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Replace dangerous characters with underscores
        # Allow only alphanumeric, dash, underscore, and dot
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Remove multiple consecutive dots to prevent extension spoofing
        filename = re.sub(r'\.{2,}', '.', filename)
        
        # Ensure it doesn't start with a dot (hidden file)
        if filename.startswith('.'):
            filename = '_' + filename[1:]
        
        # Truncate if too long
        if len(filename) > max_length:
            name, ext = os.path.splitext(filename)
            # Keep extension if possible
            if len(ext) < max_length:
                name = name[:max_length - len(ext)]
                filename = name + ext
            else:
                filename = filename[:max_length]
        
        return filename
    
    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 10000) -> str:
        """
        Sanitize user input to prevent injection attacks.
        
        Args:
            text: User input text
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Escape HTML entities
        text = html.escape(text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text 
                      if char in '\n\t' or not char.isspace() or char == ' ')
        
        return text
    
    @staticmethod
    def generate_session_id(length: int = 8) -> str:
        """
        Generate a secure random session ID.
        
        Args:
            length: Length of the session ID
            
        Returns:
            Secure random string
        """
        # Use secrets module for cryptographically secure random generation
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate that a URL is properly formatted and uses allowed schemes.
        
        Args:
            url: URL to validate
            
        Returns:
            True if valid, False otherwise
        """
        allowed_schemes = {'http', 'https'}
        
        # Basic URL pattern
        url_pattern = re.compile(
            r'^(https?://)' # http:// or https://
            r'([a-zA-Z0-9.-]+)' # domain
            r'(:[0-9]+)?' # optional port
            r'(/.*)?$' # optional path
        )
        
        if not url_pattern.match(url):
            return False
        
        # Check scheme
        scheme = url.split('://')[0].lower()
        return scheme in allowed_schemes
    
    @staticmethod
    def redact_sensitive_data(text: str) -> str:
        """
        Redact potentially sensitive data from text.
        
        Args:
            text: Text to redact
            
        Returns:
            Text with sensitive data redacted
        """
        # Redact API keys (common patterns)
        text = re.sub(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\\s]+)', r'\1[REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact AWS keys
        text = re.sub(r'(AKIA[0-9A-Z]{16})', '[AWS_KEY_REDACTED]', text)
        text = re.sub(r'(aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\\s]+)', 
                     r'\1[REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact bearer tokens
        text = re.sub(r'(bearer\s+)([a-zA-Z0-9\-._~+/]+)', r'\1[TOKEN_REDACTED]', text, flags=re.IGNORECASE)
        
        # Redact email addresses
        text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL_REDACTED]', text)
        
        return text

# Global security config instance
security = SecurityConfig()