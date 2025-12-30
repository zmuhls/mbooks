"""Utility for generating image URLs for GitHub Pages."""

from typing import Dict


class ImageURLBuilder:
    """Build image URLs for GitHub Pages hosting."""

    def __init__(self, base_url: str = "https://zmuhls.github.io/mbooks"):
        self.base_url = base_url
        self.listings_path = "listings"

    def build_urls(self, listing_dir: str, images_data: Dict) -> str:
        """Build pipe-delimited image URLs for eBay.

        Args:
            listing_dir: Directory name (e.g., 'first_blood_david_morrell')
            images_data: Dict with 'files' and 'primary_image' keys

        Returns:
            Pipe-delimited URLs with primary image first
        """
        image_files = images_data.get('files', [])
        primary_image = images_data.get('primary_image', '')

        # Order images with primary first
        if primary_image and primary_image in image_files:
            ordered = [primary_image] + [img for img in image_files if img != primary_image]
        else:
            ordered = image_files

        # Build full URLs
        urls = [f"{self.base_url}/{self.listings_path}/{listing_dir}/{img}"
               for img in ordered]

        return '|'.join(urls)
