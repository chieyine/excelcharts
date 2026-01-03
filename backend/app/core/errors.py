"""
Error message constants and utilities for user-friendly error handling.
"""
from typing import Dict, Optional

# Error codes
class ErrorCodes:
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_EMPTY = "FILE_EMPTY"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    PARSE_ERROR = "PARSE_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

# User-friendly error messages - friendly, helpful, and empathetic
ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    ErrorCodes.FILE_TOO_LARGE: {
        "message": "Oops! Your file is a bit too large",
        "detail": f"We love that you have lots of data! However, your file exceeds our size limit to keep things fast for everyone.",
        "suggestion": "💡 Try splitting your file into smaller parts, or export just the columns you need. Most insights can be found with a sample of your data!"
    },
    ErrorCodes.FILE_EMPTY: {
        "message": "Hmm, your file looks empty",
        "detail": "We couldn't find any data in the file you uploaded. This might happen if the file wasn't saved properly.",
        "suggestion": "💡 Make sure your file has data in it, save it again, and try uploading once more. If you're copying from Excel, make sure all rows are included!"
    },
    ErrorCodes.INVALID_FILE_TYPE: {
        "message": "We need a CSV or Excel file",
        "detail": "We work best with CSV or Excel files (.csv, .xlsx, .xls). Your file type isn't something we can read yet.",
        "suggestion": "💡 No worries! If you're using Google Sheets or another tool, just export it as CSV or Excel. Most tools have a 'Download as CSV' option in the File menu."
    },
    ErrorCodes.PARSE_ERROR: {
        "message": "We're having trouble reading your file",
        "detail": "Something's not quite right with the file format. It might be corrupted, have special characters, or be in an unexpected format.",
        "suggestion": "💡 Try saving your file again as a fresh CSV or Excel file. Make sure there are no unusual characters in your column names. If you're using Excel, try 'Save As' and choose CSV format."
    },
    ErrorCodes.PROCESSING_ERROR: {
        "message": "Something went wrong while processing",
        "detail": "We hit a snag while analyzing your data. This could be due to unusual data formats, missing values, or file structure issues.",
        "suggestion": "💡 Check that your file has headers in the first row, and that your data is organized in columns. Try removing any completely empty rows or columns, then upload again."
    },
    ErrorCodes.RATE_LIMIT_EXCEEDED: {
        "message": "Whoa there! Slow down a bit",
        "detail": "You're uploading files faster than we can keep up! We limit requests to keep the service fast for everyone.",
        "suggestion": "💡 Take a quick break - grab a coffee ☕ - and try again in about a minute. Your data will still be there!"
    },
    ErrorCodes.TIMEOUT: {
        "message": "This is taking longer than expected",
        "detail": "Your file is taking a while to process. This usually happens with very large files or complex data structures.",
        "suggestion": "💡 Try uploading a smaller sample of your data (first 1000 rows works great for most insights!), or split your file into smaller chunks. You can always analyze different parts separately."
    },
    ErrorCodes.UNKNOWN_ERROR: {
        "message": "Hmm, something unexpected happened",
        "detail": "We encountered an issue we weren't expecting. Don't worry - it's not your fault!",
        "suggestion": "💡 Give it another try in a moment. If the problem keeps happening, try a different file or check that your internet connection is stable. We're here to help!"
    }
}

def get_error_response(error_code: str, additional_detail: Optional[str] = None) -> Dict[str, str]:
    """
    Get user-friendly error response for an error code.
    
    Args:
        error_code: One of the ErrorCodes constants
        additional_detail: Optional additional detail to append
        
    Returns:
        Dictionary with message, detail, and suggestion
    """
    error_info = ERROR_MESSAGES.get(error_code, ERROR_MESSAGES[ErrorCodes.UNKNOWN_ERROR])
    
    response = {
        "code": error_code,
        "message": error_info["message"],
        "detail": error_info["detail"],
        "suggestion": error_info["suggestion"]
    }
    
    if additional_detail:
        response["detail"] = f"{response['detail']} {additional_detail}"
    
    return response

