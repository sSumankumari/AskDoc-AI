import re
import validators
from urllib.parse import urlparse
from typing import List, Optional
from werkzeug.datastructures import FileStorage


def validate_url(url: str) -> bool:
    """
    Validate URL format and accessibility
    """
    if not url or not isinstance(url, str):
        return False

    # Check URL length
    if len(url) > 2048:
        return False

    # Use validators library for basic validation
    if not validators.url(url):
        return False

    # Additional checks
    try:
        parsed = urlparse(url)

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False

        # Must be http or https
        if parsed.scheme not in ['http', 'https']:
            return False

        # Basic domain validation
        if '.' not in parsed.netloc:
            return False

        return True

    except Exception:
        return False


def validate_file(file: FileStorage, allowed_extensions: List[str]) -> bool:
    """
    Validate uploaded file
    """
    if not file or not file.filename:
        return False

    # Check if file has an extension
    if '.' not in file.filename:
        return False

    # Get file extension
    extension = file.filename.rsplit('.', 1)[1].lower()

    # Check if extension is allowed
    if extension not in [ext.lower() for ext in allowed_extensions]:
        return False

    # Check file size (basic check, more detailed in processor)
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning

    # Max 16MB
    if file_size > 16 * 1024 * 1024:
        return False

    return True


def validate_question(question: str) -> bool:
    """
    Validate question format and content
    """
    if not question or not isinstance(question, str):
        return False

    # Remove whitespace and check length
    question = question.strip()

    # Must be between 3 and 1000 characters
    if len(question) < 3 or len(question) > 1000:
        return False

    # Must contain at least one letter
    if not re.search(r'[a-zA-Z]', question):
        return False

    # Check for potentially harmful content (basic)
    harmful_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
    ]

    for pattern in harmful_patterns:
        if re.search(pattern, question, re.IGNORECASE | re.DOTALL):
            return False

    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage
    """
    if not filename:
        return "untitled"

    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255 - len(ext) - 1] + '.' + ext if ext else name[:255]

    return filename or "untitled"


def validate_json_data(data: dict, required_fields: List[str]) -> tuple[bool, Optional[str]]:
    """
    Validate JSON data structure
    """
    if not isinstance(data, dict):
        return False, "Data must be a JSON object"

    # Check required fields
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"

        if not data[field] or (isinstance(data[field], str) and not data[field].strip()):
            return False, f"Field '{field}' cannot be empty"

    return True, None


def is_safe_content(content: str) -> bool:
    """
    Basic content safety check
    """
    if not content or not isinstance(content, str):
        return False

    # Check for extremely long content that might cause issues
    if len(content) > 10 * 1024 * 1024:  # 10MB text limit
        return False

    # Basic XSS prevention (simple check)
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>.*?</iframe>',
        r'<object[^>]*>.*?</object>',
        r'<embed[^>]*>.*?</embed>',
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
            return False

    return True