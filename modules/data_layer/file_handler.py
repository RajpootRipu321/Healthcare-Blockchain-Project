"""File Handler for medical image processing."""

import os
import uuid
import hashlib
from typing import Tuple, Optional
from werkzeug.utils import secure_filename
from PIL import Image


class FileHandler:
    """
    Handler for medical file operations.

    Supports:
    - Medical image formats (PNG, JPG, DICOM)
    - Secure file naming
    - File validation
    - Metadata extraction
    """

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'dcm', 'dicom', 'bmp'}
    MAX_FILE_SIZE = 16 * 1024 * 1024  # 16 MB

    def __init__(self, upload_folder: str, download_folder: str):
        """
        Initialize file handler.

        Args:
            upload_folder: Directory for uploads
            download_folder: Directory for downloads
        """
        self.upload_folder = upload_folder
        self.download_folder = download_folder

        # Ensure directories exist
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(download_folder, exist_ok=True)

    def save_upload(self, file, patient_id: str = None) -> Tuple[str, str]:
        """
        Save an uploaded file securely.

        Args:
            file: Werkzeug FileStorage object
            patient_id: Optional patient identifier

        Returns:
            Tuple of (file_path, original_filename)
        """
        if not file or file.filename == '':
            raise ValueError("No file provided")

        if not self.is_allowed_file(file.filename):
            raise ValueError(f"File type not allowed. Allowed: {self.ALLOWED_EXTENSIONS}")

        # Generate secure filename
        original_filename = secure_filename(file.filename)
        ext = self.get_extension(original_filename)

        # Create unique filename with patient ID if provided
        unique_id = str(uuid.uuid4())[:8]
        if patient_id:
            new_filename = f"{patient_id}_{unique_id}.{ext}"
        else:
            new_filename = f"{unique_id}.{ext}"

        file_path = os.path.join(self.upload_folder, new_filename)
        file.save(file_path)

        return file_path, original_filename

    def is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and self.get_extension(filename) in self.ALLOWED_EXTENSIONS

    @staticmethod
    def get_extension(filename: str) -> str:
        """Get lowercase file extension."""
        return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex digest of file hash
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def get_image_metadata(self, file_path: str) -> dict:
        """
        Extract metadata from an image file.

        Args:
            file_path: Path to image

        Returns:
            Dictionary with image metadata
        """
        try:
            with Image.open(file_path) as img:
                return {
                    'format': img.format,
                    'mode': img.mode,
                    'size': img.size,
                    'width': img.width,
                    'height': img.height,
                    'file_size': os.path.getsize(file_path)
                }
        except Exception as e:
            return {
                'error': str(e),
                'file_size': os.path.getsize(file_path)
            }

    def prepare_for_ai(self, file_path: str, target_size: Tuple[int, int] = (224, 224)) -> str:
        """
        Prepare image for AI model processing.

        Args:
            file_path: Path to original image
            target_size: Target dimensions (width, height)

        Returns:
            Path to processed image
        """
        with Image.open(file_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Resize while maintaining aspect ratio
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Create new image with target size (padding if needed)
            new_img = Image.new('RGB', target_size, (0, 0, 0))
            paste_x = (target_size[0] - img.width) // 2
            paste_y = (target_size[1] - img.height) // 2
            new_img.paste(img, (paste_x, paste_y))

            # Save processed image
            processed_path = file_path.rsplit('.', 1)[0] + '_processed.png'
            new_img.save(processed_path, 'PNG')

            return processed_path

    def cleanup_temp_files(self, file_paths: list):
        """Remove temporary files."""
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    def get_download_path(self, filename: str) -> str:
        """Get full path for a download file."""
        return os.path.join(self.download_folder, secure_filename(filename))
