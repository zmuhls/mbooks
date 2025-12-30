#!/usr/bin/env python3
"""Generate a black wooden table background texture."""

from PIL import Image, ImageDraw, ImageFilter
import random
from pathlib import Path


def generate_black_wood_texture(width=2000, height=2000, output_path=None):
    """Generate a realistic black wooden table texture.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        output_path: Path to save the image (optional)

    Returns:
        PIL Image object
    """
    # Create base image with dark wood color
    # Black wood table - very dark brown/black
    base_color = (20, 18, 15)  # Very dark brown, almost black
    img = Image.new('RGB', (width, height), base_color)

    # Add wood grain texture
    draw = ImageDraw.Draw(img)

    # Create horizontal wood grain lines
    random.seed(42)  # Consistent generation

    for y in range(0, height, 2):
        # Vary the darkness slightly for grain effect
        variation = random.randint(-8, 8)
        color = tuple(max(0, min(255, c + variation)) for c in base_color)

        # Draw slightly wavy horizontal lines for wood grain
        points = []
        for x in range(0, width, 10):
            offset = random.randint(-2, 2)
            points.append((x, y + offset))

        if len(points) > 1:
            draw.line(points, fill=color, width=1)

    # Add some darker knots/grain patterns
    for _ in range(15):
        x = random.randint(100, width - 100)
        y = random.randint(100, height - 100)
        radius = random.randint(30, 80)

        # Draw concentric circles for wood knot
        for r in range(radius, 0, -5):
            darkness = random.randint(-15, -5)
            knot_color = tuple(max(0, c + darkness) for c in base_color)
            draw.ellipse([x - r, y - r, x + r, y + r], outline=knot_color)

    # Apply subtle blur for more realistic wood texture
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    # Add subtle noise for texture
    pixels = img.load()
    for y in range(height):
        for x in range(width):
            if random.random() < 0.3:  # 30% of pixels get noise
                noise = random.randint(-3, 3)
                r, g, b = pixels[x, y]
                pixels[x, y] = (
                    max(0, min(255, r + noise)),
                    max(0, min(255, g + noise)),
                    max(0, min(255, b + noise))
                )

    # Save if path provided
    if output_path:
        img.save(output_path, 'JPEG', quality=95, optimize=True)
        print(f"Generated black wood table texture: {output_path}")

    return img


if __name__ == '__main__':
    # Generate the table background
    project_root = Path(__file__).parent.parent
    output_path = project_root / 'assets' / 'backgrounds' / 'black-wood-table.jpg'

    print("Generating black wooden table background...")
    generate_black_wood_texture(2000, 2000, output_path)
    print(f"Done! Saved to {output_path}")
    print(f"File size: {output_path.stat().st_size / 1024:.1f} KB")
