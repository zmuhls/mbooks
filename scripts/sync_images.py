#!/usr/bin/env python3
"""Sync and optimize images from listings/ to docs/listings/."""

import shutil
from pathlib import Path
import sys


def optimize_image(image_path: Path, max_size: int = 1600, quality: int = 85, bg_processor=None) -> None:
    """Optimize image for web hosting with optional background replacement.

    Args:
        image_path: Path to image file
        max_size: Maximum dimension (width or height)
        quality: JPEG quality (1-100)
        bg_processor: BackgroundProcessor instance (optional)
    """
    try:
        from PIL import Image

        # Step 1: Apply background processing if enabled
        if bg_processor:
            print(f"  Processing background: {image_path.name}")
            processed_img = bg_processor.process_image(image_path)

            if processed_img:
                img = processed_img
                print(f"  ✓ Background applied: {image_path.name}")
            else:
                print(f"  ✗ Background processing failed, using original: {image_path.name}")
                img = Image.open(image_path)
        else:
            img = Image.open(image_path)

        # Step 2: Resize if larger than max_size
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"  Resized: {image_path.name} ({img.size[0]}x{img.size[1]})")

        # Step 3: Save with optimization (convert to RGB if needed)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        img.save(image_path, 'JPEG', optimize=True, quality=quality)

    except ImportError:
        print("Warning: PIL/Pillow not installed. Skipping optimization.")
        print("Install with: pip install Pillow")
    except Exception as e:
        print(f"Warning: Could not optimize {image_path.name}: {e}")


def sync_images(source_dir: Path, target_dir: Path, optimize: bool = True, dry_run: bool = False,
                apply_background: bool = False, padding_percent: float = 0.125) -> None:
    """Sync image files and metadata from source to target.

    Args:
        source_dir: Source listings directory
        target_dir: Target docs/listings directory
        optimize: Whether to optimize images during sync
        dry_run: Show what would be synced without copying
        apply_background: Apply black wooden table background
        padding_percent: Padding as fraction (default 0.125 = 12.5%)
    """
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)

    target_dir.mkdir(parents=True, exist_ok=True)

    # Initialize background processor if enabled
    bg_processor = None
    if apply_background:
        try:
            import os
            import sys

            # Add project root to Python path for imports
            project_root = Path(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.utils.background_processor import BackgroundProcessor

            # API key not required for rembg, but keep for compatibility
            api_key = os.getenv("OPENROUTER_API_KEY", "")

            table_bg_path = project_root / "assets" / "backgrounds" / "black-wood-table.jpg"

            if not table_bg_path.exists():
                print(f"Warning: Table background not found at {table_bg_path}")
                print("Skipping background processing.")
            else:
                bg_processor = BackgroundProcessor(
                    openrouter_api_key=api_key,
                    table_background_path=table_bg_path,
                    padding_percent=padding_percent
                )
                print(f"Background processing enabled (padding: {padding_percent*100:.1f}%)")
        except Exception as e:
            print(f"Warning: Could not initialize background processor: {e}")
            bg_processor = None

    synced_count = 0
    optimized_count = 0
    skipped_count = 0

    # Iterate through each book directory
    for book_dir in source_dir.iterdir():
        if not book_dir.is_dir() or book_dir.name.startswith('.'):
            continue

        target_book_dir = target_dir / book_dir.name
        target_book_dir.mkdir(exist_ok=True)

        # Sync images and metadata
        for file in book_dir.iterdir():
            if file.suffix.lower() in ['.jpg', '.jpeg', '.png'] or file.name == 'metadata.json':
                target_file = target_book_dir / file.name

                # Check if file needs updating
                needs_update = (
                    not target_file.exists() or
                    file.stat().st_mtime > target_file.stat().st_mtime
                )

                if needs_update:
                    if dry_run:
                        print(f"Would copy: {file.relative_to(source_dir)}")
                    else:
                        shutil.copy2(file, target_file)
                        print(f"Synced: {file.relative_to(source_dir)}")

                        # Optimize images (not metadata.json)
                        if optimize and file.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                            optimize_image(target_file, bg_processor=bg_processor)
                            optimized_count += 1

                    synced_count += 1
                else:
                    skipped_count += 1

    print(f"\nSync complete:")
    print(f"  {synced_count} files synced")
    if optimize and optimized_count > 0:
        print(f"  {optimized_count} images optimized")
    print(f"  {skipped_count} files unchanged")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Sync images to docs/listings/')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be synced without copying')
    parser.add_argument('--no-optimize', action='store_true',
                       help='Skip image optimization')
    parser.add_argument('--apply-background', action='store_true',
                       help='Apply black wooden table background to images')
    parser.add_argument('--padding', type=float, default=0.125,
                       help='Padding percentage (default: 0.125 = 12.5%%)')
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    source = project_root / 'listings'
    target = project_root / 'docs' / 'listings'

    sync_images(source, target, optimize=not args.no_optimize, dry_run=args.dry_run,
                apply_background=args.apply_background, padding_percent=args.padding)
