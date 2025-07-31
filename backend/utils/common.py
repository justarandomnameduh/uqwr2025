#!/usr/bin/env python3

import os
import logging
from PIL import Image
from typing import Tuple

logger = logging.getLogger(__name__)

def preprocess_image(image_path: str, max_image_size: Tuple[int, int] = (1024, 1024)) -> str:
    """Preprocess image to reduce memory usage (legacy function - kept for backward compatibility)"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize image if it's too large
            if img.size[0] > max_image_size[0] or img.size[1] > max_image_size[1]:
                img.thumbnail(max_image_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {image_path} to {img.size}")
            
            # Save processed image temporarily - properly handle the file extension
            dir_path, filename = os.path.split(image_path)
            name, ext = os.path.splitext(filename)
            processed_filename = f"{name}_processed{ext}"
            processed_path = os.path.join(dir_path, processed_filename)
            
            img.save(processed_path, quality=85, optimize=True)
            return processed_path
    except Exception as e:
        logger.warning(f"Failed to preprocess image {image_path}: {e}")
        return image_path

def preprocess_image_in_memory(image_path: str, max_image_size: Tuple[int, int] = (1024, 1024)) -> Image.Image:
    """Preprocess image in memory to avoid disk I/O"""
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize image if it's too large
            if img.size[0] > max_image_size[0] or img.size[1] > max_image_size[1]:
                # Create a copy since we're returning it
                img = img.copy()
                img.thumbnail(max_image_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image from {image_path} to {img.size}")
                return img
            else:
                # Return a copy to ensure the original file handle is closed
                return img.copy()
    except Exception as e:
        logger.warning(f"Failed to preprocess image {image_path}: {e}")
        raise