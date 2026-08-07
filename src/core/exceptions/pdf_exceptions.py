"""
src/core/exceptions/pdf_exceptions.py
Domain-specific exceptions for PDF loading and processing operations.
"""

class PDFProcessingError(Exception):
    """Base exception for all PDF processing errors."""
    pass

class PDFNotFoundError(PDFProcessingError):
    """Raised when the specified PDF file path does not exist on disk."""
    pass

class CorruptedPDFError(PDFProcessingError):
    """Raised when the PDF file is corrupted or unreadable by the engine."""
    pass

class EncryptedPDFError(PDFProcessingError):
    """Raised when the PDF file is password protected or encrypted."""
    pass

class InvalidPageError(PDFProcessingError):
    """Raised when an invalid page index is requested."""
    pass
