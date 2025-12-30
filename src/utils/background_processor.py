"""Background removal and compositing for book images."""

import io
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


class BackgroundProcessor:
    """Handle background removal and table compositing for book images."""

    def __init__(
        self,
        openrouter_api_key: str = None,
        model: str = "u2net",
        table_background_path: Optional[Path] = None,
        padding_percent: float = 0.125
    ):
        """Initialize background processor.

        Args:
            openrouter_api_key: Not used (kept for compatibility)
            model: Background removal model (u2net, u2netp, u2net_human_seg, etc.)
            table_background_path: Path to black wood table image
            padding_percent: Padding as fraction (0.125 = 12.5%)
        """
        self.model = model
        self.table_background_path = table_background_path
        self.padding_percent = padding_percent
        self.table_background = None
        self._rembg_available = False

        # Try to import rembg
        try:
            from rembg import remove
            self._remove_bg = remove
            self._rembg_available = True
        except ImportError:
            print("Warning: rembg not installed. Install with: pip install rembg")
            self._remove_bg = None

        # Load and cache table background
        if table_background_path and table_background_path.exists():
            try:
                self.table_background = Image.open(table_background_path)
                print(f"Loaded table background: {table_background_path.name}")
            except Exception as e:
                print(f"Warning: Could not load table background: {e}")
                self.table_background = None

    def remove_background(self, image_path: Path) -> Optional[Image.Image]:
        """Remove background using rembg library.

        Args:
            image_path: Path to source image

        Returns:
            PIL Image with transparent background, or None if failed
        """
        if not self._rembg_available:
            print(f"    rembg not available, skipping background removal")
            return None

        try:
            # Read image
            with open(image_path, 'rb') as f:
                input_data = f.read()

            # Remove background
            output_data = self._remove_bg(input_data)

            # Convert to PIL Image
            output_image = Image.open(io.BytesIO(output_data))

            return output_image

        except Exception as e:
            print(f"    Background removal failed: {e}")
            return None

    def composite_on_table(
        self,
        cutout_image: Image.Image,
        output_size: Tuple[int, int] = None
    ) -> Image.Image:
        """Composite cutout book onto black wooden table background.

        Args:
            cutout_image: Book with transparent background
            output_size: Target dimensions for final image (uses table bg size if None)

        Returns:
            Composited image with black table background
        """
        if self.table_background is None:
            raise ValueError("Table background not loaded")

        # Use table background size if output size not specified
        if output_size is None:
            output_size = self.table_background.size

        # Create a copy of table background at target size
        table = self.table_background.copy()
        if table.size != output_size:
            table = table.resize(output_size, Image.Resampling.LANCZOS)

        # Calculate available space with padding
        padding_px = int(min(output_size) * self.padding_percent)
        available_w = output_size[0] - (2 * padding_px)
        available_h = output_size[1] - (2 * padding_px)

        # Scale book to fit available space (maintain aspect ratio)
        book_aspect = cutout_image.width / cutout_image.height

        if cutout_image.width / available_w > cutout_image.height / available_h:
            # Width is limiting factor
            new_w = available_w
            new_h = int(new_w / book_aspect)
        else:
            # Height is limiting factor
            new_h = available_h
            new_w = int(new_h * book_aspect)

        # Resize book
        scaled_book = cutout_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Calculate center position
        x = (output_size[0] - new_w) // 2
        y = (output_size[1] - new_h) // 2

        # Composite using alpha channel if present
        if scaled_book.mode == 'RGBA':
            table.paste(scaled_book, (x, y), scaled_book)
        else:
            table.paste(scaled_book, (x, y))

        return table

    def process_image(self, image_path: Path) -> Optional[Image.Image]:
        """Full pipeline: remove background → composite on table.

        Args:
            image_path: Path to source image

        Returns:
            Processed PIL Image, or None if processing failed
        """
        # Step 1: Remove background
        cutout = self.remove_background(image_path)

        if cutout is None:
            # Fallback: use original image and composite directly
            # This provides a degraded but functional result
            try:
                original = Image.open(image_path)
                # Convert to RGBA for consistency
                if original.mode != 'RGBA':
                    original = original.convert('RGBA')
                return self.composite_on_table(original)
            except Exception as e:
                print(f"    Compositing failed: {e}")
                return None

        # Step 2: Composite on table
        try:
            result = self.composite_on_table(cutout)
            return result
        except Exception as e:
            print(f"    Compositing failed: {e}")
            return None
