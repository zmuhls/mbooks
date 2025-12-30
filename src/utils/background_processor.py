"""Background blurring for book images."""

import io
from pathlib import Path
from typing import Optional
from PIL import Image, ImageFilter


class BackgroundProcessor:
    """Handle background blurring for book images."""

    def __init__(
        self,
        openrouter_api_key: str = None,
        model: str = "u2net",
        table_background_path: Optional[Path] = None,
        padding_percent: float = 0.125,
        blur_radius: int = 15
    ):
        """Initialize background processor.

        Args:
            openrouter_api_key: Not used (kept for compatibility)
            model: Background removal model (u2net, u2netp, u2net_human_seg, etc.)
            table_background_path: Not used for blur mode (kept for compatibility)
            padding_percent: Not used for blur mode (kept for compatibility)
            blur_radius: Gaussian blur radius for background (default 15)
        """
        self.model = model
        self.blur_radius = blur_radius
        self._rembg_available = False

        # Try to import rembg
        try:
            from rembg import remove
            self._remove_bg = remove
            self._rembg_available = True
            print(f"Background blur mode enabled (radius: {blur_radius}px)")
        except ImportError:
            print("Warning: rembg not installed. Install with: pip install rembg")
            self._remove_bg = None

    def get_subject_mask(self, image_path: Path) -> Optional[Image.Image]:
        """Get mask of the subject (book) using rembg.

        Args:
            image_path: Path to source image

        Returns:
            PIL Image mask (grayscale), or None if failed
        """
        if not self._rembg_available:
            print(f"    rembg not available, skipping background blur")
            return None

        try:
            # Read image
            with open(image_path, 'rb') as f:
                input_data = f.read()

            # Remove background to get subject with alpha channel
            output_data = self._remove_bg(input_data)

            # Convert to PIL Image
            subject_rgba = Image.open(io.BytesIO(output_data))

            # Extract alpha channel as mask
            if subject_rgba.mode == 'RGBA':
                mask = subject_rgba.split()[3]  # Alpha channel
                return mask
            else:
                print(f"    Expected RGBA image, got {subject_rgba.mode}")
                return None

        except Exception as e:
            print(f"    Mask extraction failed: {e}")
            return None

    def blur_background(
        self,
        original_image: Image.Image,
        mask: Image.Image
    ) -> Image.Image:
        """Blur the background while keeping subject sharp.

        Args:
            original_image: Original image (RGB)
            mask: Mask of subject (white=subject, black=background)

        Returns:
            Image with blurred background
        """
        # Create blurred version of entire image
        blurred = original_image.filter(ImageFilter.GaussianBlur(radius=self.blur_radius))

        # Composite: use original where mask is white, blurred where mask is black
        # Convert mask to match image mode if needed
        if original_image.mode == 'RGB':
            result = Image.composite(original_image, blurred, mask)
        else:
            result = Image.composite(original_image.convert('RGB'), blurred, mask)

        return result

    def process_image(self, image_path: Path) -> Optional[Image.Image]:
        """Full pipeline: detect subject → blur background.

        Args:
            image_path: Path to source image

        Returns:
            Processed PIL Image with blurred background, or None if processing failed
        """
        try:
            # Load original image
            original = Image.open(image_path)

            # Convert to RGB if needed
            if original.mode != 'RGB':
                original = original.convert('RGB')

            # Get subject mask
            mask = self.get_subject_mask(image_path)

            if mask is None:
                print(f"    Could not extract mask, skipping blur")
                return None

            # Apply background blur
            result = self.blur_background(original, mask)
            return result

        except Exception as e:
            print(f"    Background blur failed: {e}")
            return None
