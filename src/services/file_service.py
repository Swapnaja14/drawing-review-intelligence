"""
src/services/file_service.py
Service handling file validation, size limits, SHA-256 hashing, and temp directory management.
"""

import hashlib
from pathlib import Path
from typing import Optional
import tempfile
import shutil

from src.core.dtos.workflow_dtos import FileValidationResultDTO
from src.core.exceptions.workflow_exceptions import (
    FileHandlingError,
    InvalidFileExtensionError,
    FileTooLargeError
)
from src.infrastructure.logging.logger import get_logger

logger = get_logger("FileService")

MAX_FILE_SIZE_MB = 500.0  # 500 MB maximum limit for engineering PDFs


class FileService:
    """
    Application Service responsible for file handling, validation, hashing,
    and temporary workspace directory management.
    """

    def __init__(self, max_size_mb: float = MAX_FILE_SIZE_MB) -> None:
        self.max_size_mb = max_size_mb
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)

    def validate_pdf_file(self, file_path: str | Path) -> FileValidationResultDTO:
        """
        Validates an uploaded PDF drawing file path.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            FileValidationResultDTO: Validation result container.
        """
        path = Path(file_path).resolve()
        logger.info(f"Validating PDF file: {path}")

        if not path.exists() or not path.is_file():
            logger.error(f"File not found: {path}")
            return FileValidationResultDTO(
                file_path=path,
                is_valid=False,
                file_name=path.name,
                file_size_mb=0.0,
                file_hash_sha256="",
                error_message=f"File does not exist: {path.name}"
            )

        if path.suffix.lower() != ".pdf":
            logger.error(f"Invalid file extension: {path.suffix}")
            return FileValidationResultDTO(
                file_path=path,
                is_valid=False,
                file_name=path.name,
                file_size_mb=round(path.stat().st_size / (1024 * 1024), 2),
                file_hash_sha256="",
                error_message=f"Invalid file format '{path.suffix}'. Only .pdf drawings are supported."
            )

        file_size = path.stat().st_size
        if file_size == 0:
            logger.error(f"Empty PDF file: {path}")
            return FileValidationResultDTO(
                file_path=path,
                is_valid=False,
                file_name=path.name,
                file_size_mb=0.0,
                file_hash_sha256="",
                error_message="Uploaded PDF file is 0 bytes (empty)."
            )

        if file_size > self.max_size_bytes:
            size_mb = round(file_size / (1024 * 1024), 2)
            logger.error(f"File exceeds size limit ({size_mb} MB > {self.max_size_mb} MB)")
            return FileValidationResultDTO(
                file_path=path,
                is_valid=False,
                file_name=path.name,
                file_size_mb=size_mb,
                file_hash_sha256="",
                error_message=f"File size ({size_mb} MB) exceeds maximum allowed limit ({self.max_size_mb} MB)."
            )

        # Compute SHA-256 hash
        file_hash = self.compute_sha256(path)
        size_mb = round(file_size / (1024 * 1024), 2)

        logger.info(f"File '{path.name}' is valid ({size_mb} MB, SHA-256: {file_hash[:8]})")
        return FileValidationResultDTO(
            file_path=path,
            is_valid=True,
            file_name=path.name,
            file_size_mb=size_mb,
            file_hash_sha256=file_hash
        )

    def compute_sha256(self, file_path: Path) -> str:
        """Computes SHA-256 digest of file content in chunks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_app_temp_dir(self) -> Path:
        """Creates and returns the application temp workspace directory."""
        temp_dir = Path(tempfile.gettempdir()) / "UCCAnalyzer" / "cache"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir
