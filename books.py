#!/usr/bin/env python3
"""
Muhlbauer Books CLI - Manage book listings, export to eBay, and serve website.

Usage:
    python books.py list              - List all books
    python books.py export            - Export eBay CSV
    python books.py serve             - Start local web server
    python books.py extract <folder>  - Extract metadata from images (requires API key)
"""

import sys
import json
import http.server
import socketserver
from pathlib import Path

BASE_DIR = Path(__file__).parent
LISTINGS_DIR = BASE_DIR / 'listings'
EXPORTS_DIR = BASE_DIR / 'exports'
SITE_DIR = BASE_DIR / 'site'


def list_books():
    """List all book listings with summary info."""
    print("\n  MUHLBAUER BOOKS INVENTORY\n" + "=" * 50)

    count = 0
    for item in sorted(LISTINGS_DIR.iterdir()):
        if item.is_dir():
            meta_file = item / 'metadata.json'
            if meta_file.exists():
                with open(meta_file) as f:
                    data = json.load(f)
                basic = data.get('basic_info', {})
                edition = data.get('edition_details', {})
                images = data.get('images', {})

                title = basic.get('title', 'Unknown')
                creator = basic.get('author') or basic.get('editor') or ''
                signed = 'SIGNED' if edition.get('is_signed') else ''
                limited = 'LIMITED' if edition.get('is_limited_edition') else ''
                img_count = len(images.get('files', []))

                tags = ' '.join(filter(None, [signed, limited]))
                print(f"\n  [{item.name}]")
                print(f"  {title}")
                if creator:
                    print(f"  by {creator}")
                if tags:
                    print(f"  {tags}")
                print(f"  {img_count} images")
                count += 1

    print(f"\n{'=' * 50}")
    print(f"  Total: {count} books\n")


def export_ebay():
    """Export listings to eBay bulk upload CSV."""
    sys.path.insert(0, str(BASE_DIR / 'src'))
    from ebay.exporter import EbayExporter

    EXPORTS_DIR.mkdir(exist_ok=True)
    exporter = EbayExporter(LISTINGS_DIR)
    output = exporter.export_csv()

    print(f"\n  eBay CSV exported to: {output}")
    print(f"  Listings exported: {len(exporter.load_listings())}\n")


def serve_website(port=8000):
    """Start local web server to view the catalog."""
    import os

    # Serve from project root so both site/ and listings/ are accessible
    os.chdir(BASE_DIR)

    # Custom handler to serve index.html from site/ directory
    class CustomHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            # Redirect root to site/index.html
            if self.path == '/':
                self.path = '/site/index.html'
            # Serve site assets from site/
            elif self.path.startswith('/styles.css') or self.path.startswith('/app.js'):
                self.path = '/site' + self.path
            return http.server.SimpleHTTPRequestHandler.do_GET(self)

    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        print(f"\n  Serving Muhlbauer Books catalog at:")
        print(f"  http://localhost:{port}")
        print(f"\n  Press Ctrl+C to stop.\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n  Server stopped.\n")


def extract_metadata(folder_name: str):
    """Extract metadata from book images using LLM vision."""
    folder_path = LISTINGS_DIR / folder_name
    if not folder_path.exists():
        print(f"  Error: Folder '{folder_name}' not found in listings/")
        return

    # Check for API key
    import os
    if not os.getenv('ANTHROPIC_API_KEY'):
        print("\n  Error: ANTHROPIC_API_KEY environment variable not set.")
        print("  Set it with: export ANTHROPIC_API_KEY=your_key_here\n")
        return

    sys.path.insert(0, str(BASE_DIR / 'src'))
    from vision.extractor import VisionExtractor

    # Find images
    images = list(folder_path.glob('*.jpg')) + list(folder_path.glob('*.jpeg')) + list(folder_path.glob('*.png'))
    if not images:
        print(f"  No images found in {folder_name}/")
        return

    print(f"\n  Extracting metadata from {len(images)} images...")

    extractor = VisionExtractor()
    result = extractor.extract_metadata(images[:5])  # Limit to 5 images

    if result.success:
        print("\n  Extracted metadata:")
        print(json.dumps(result.data, indent=2))
        print(f"\n  Tokens used: {result.tokens_used}")
    else:
        print(f"\n  Extraction failed: {result.error}")


def show_help():
    """Show help message."""
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == 'list':
        list_books()
    elif command == 'export':
        export_ebay()
    elif command == 'serve':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
        serve_website(port)
    elif command == 'extract':
        if len(sys.argv) < 3:
            print("  Usage: python books.py extract <folder_name>")
            return
        extract_metadata(sys.argv[2])
    else:
        show_help()


if __name__ == '__main__':
    main()
