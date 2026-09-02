"""Image Preprocessor for AI model input."""

import numpy as np
from PIL import Image
from typing import Tuple, Optional
import os


class ImagePreprocessor:
    """
    Preprocessor for medical images.

    Handles:
    - Resizing to model input size
    - Normalization
    - Color space conversion
    - Data augmentation (optional)
    """

    def __init__(self, target_size: Tuple[int, int] = (224, 224)):
        """
        Initialize preprocessor.

        Args:
            target_size: Target dimensions (width, height)
        """
        self.target_size = target_size

    def load_image(self, image_path: str) -> Image.Image:
        """
        Load an image from path.

        Args:
            image_path: Path to image file

        Returns:
            PIL Image object
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        return Image.open(image_path)

    def preprocess(self, image_path: str) -> np.ndarray:
        """
        Preprocess image for model input.

        Args:
            image_path: Path to image

        Returns:
            Preprocessed numpy array ready for model
        """
        img = self.load_image(image_path)
        return self.preprocess_pil(img)

    def preprocess_pil(self, img: Image.Image) -> np.ndarray:
        """
        Preprocess PIL Image for model input.

        Args:
            img: PIL Image object

        Returns:
            Preprocessed numpy array
        """
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')

        # Resize to target size
        img = img.resize(self.target_size, Image.Resampling.LANCZOS)

        # Convert to numpy array
        img_array = np.array(img, dtype=np.float32)

        # Normalize to [0, 1]
        img_array = img_array / 255.0

        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)

        return img_array

    def preprocess_for_mobilenet(self, image_path: str) -> np.ndarray:
        """
        Preprocess specifically for MobileNet.

        Uses MobileNet's preprocessing (scale to [-1, 1])

        Args:
            image_path: Path to image

        Returns:
            Preprocessed numpy array
        """
        img = self.load_image(image_path)

        if img.mode != 'RGB':
            img = img.convert('RGB')

        img = img.resize(self.target_size, Image.Resampling.LANCZOS)
        img_array = np.array(img, dtype=np.float32)

        # MobileNet preprocessing: scale to [-1, 1]
        img_array = (img_array / 127.5) - 1.0

        return np.expand_dims(img_array, axis=0)

    def preprocess_batch(self, image_paths: list) -> np.ndarray:
        """
        Preprocess multiple images.

        Args:
            image_paths: List of image paths

        Returns:
            Batch of preprocessed images
        """
        batch = []
        for path in image_paths:
            img_array = self.preprocess(path)
            batch.append(img_array[0])  # Remove batch dim temporarily

        return np.array(batch)

    @staticmethod
    def get_image_info(image_path: str) -> dict:
        """
        Get basic image information.

        Args:
            image_path: Path to image

        Returns:
            Dictionary with image info
        """
        with Image.open(image_path) as img:
            return {
                'format': img.format,
                'mode': img.mode,
                'size': img.size,
                'width': img.width,
                'height': img.height
            }
