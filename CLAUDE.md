# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Collectible book management system with LLM-powered metadata extraction and eBay integration. Books are cataloged with images in `listings/`, exported to eBay CSV with full GitHub Pages URLs, and displayed on a static website.

## Key Commands

### CLI Operations (books.py)
```bash
python books.py list                    # Show inventory
python books.py export                  # Generate eBay CSV
python books.py serve [port]            # Start local server (default: 8000)
python books.py extract <folder_name>   # Extract metadata from images (requires ANTHROPIC_API_KEY)
```

### eBay Workflow (Makefile)
```bash
make build-csv      # Sync images to docs/, optimize, generate CSV
make sync-images    # Sync and optimize images from listings/ to docs/
make deploy         # Commit and push docs/ to GitHub Pages
make all            # Complete workflow (sync + CSV + deploy)
```

### Image Sync Script
```bash
python scripts/sync_images.py                      # Sync with optimization
python scripts/sync_images.py --dry-run            # Preview changes
python scripts/sync_images.py --no-optimize        # Skip image optimization
python scripts/sync_images.py --apply-background   # Apply black table background
python scripts/sync_images.py --apply-background --padding 0.15  # 15% padding
```

### Testing
```bash
pytest                                  # Run all tests
pytest tests/test_image_urls.py        # Test URL generation
```

## Architecture

### Dual Directory Structure
**Critical:** Two parallel directories must stay in sync:
- `listings/` - Source of truth (working directory)
- `docs/listings/` - Deployed to GitHub Pages (public hosting)

Changes to `listings/` must be synced to `docs/` before images are accessible online. Use `make sync-images` or the sync script.

### Image Hosting Strategy
GitHub Pages (`https://zmuhls.github.io/mbooks/`) hosts all images for eBay listings:
1. Images live in `docs/listings/{book_slug}/{image_file}.jpg`
2. eBay CSV contains full URLs, not local paths
3. ImageURLBuilder (`src/utils/image_urls.py`) generates URLs
4. Primary image (from `metadata.json`) always appears first

**eBay Requirements:**
- HTTPS URLs (GitHub Pages provides this)
- Static URLs (no expiration/tokens)
- Publicly accessible
- Max 1600px recommended, <12 MB per image

### Data Flow

```
Book Images → listings/{book}/
                ├── metadata.json (canonical data)
                └── *.jpg

            ↓ (make sync-images)

docs/listings/{book}/
    ├── metadata.json (copy)
    └── *.jpg (optimized: 1600px, 85% quality)

            ↓ (make build-csv)

exports/ebay_upload_YYYYMMDD.csv
    ├── PicURL: https://zmuhls.github.io/mbooks/listings/{book}/image.jpg
    └── Full listing data

            ↓ (make deploy)

GitHub Pages → Live image hosting
```

### Metadata Schema

Each `listings/{book}/metadata.json` has this structure:
```json
{
  "basic_info": {
    "title": "...",
    "author": "..." | ["..."],
    "editor": "..." | ["..."]
  },
  "edition_details": {
    "is_signed": bool,
    "is_limited_edition": bool,
    "edition_description": "..."
  },
  "images": {
    "files": ["IMG_001.jpg", "IMG_002.jpg"],
    "primary_image": "IMG_001.jpg",
    "image_notes": {}
  },
  "condition": {
    "overall_grade": "NEW|LIKE_NEW|VERY_GOOD|GOOD|ACCEPTABLE"
  }
}
```

**Important:** `images.primary_image` determines first image in eBay CSV (eBay displays first image as main photo).

## Code Modules

### src/ebay/exporter.py
Main eBay CSV generator. Key patterns:
- Uses `ImageURLBuilder` for URL generation
- `listing_to_row()` maps metadata → eBay CSV fields
- Handles relative imports for direct execution (`python src/ebay/exporter.py`)
- Generates 80-char max titles with SIGNED/Limited tags

### src/utils/image_urls.py
Centralizes image URL generation:
- Configurable base URL (currently GitHub Pages)
- Ensures primary image is first
- Returns pipe-delimited URLs for eBay

**Design:** Easy to migrate to different hosting (Cloudinary, S3) by modifying this one file.

### src/vision/extractor.py
LLM-powered metadata extraction from book images:
- Uses Claude's vision API (multimodal)
- Encodes images to base64
- Extracts title, author, edition info, condition
- Requires `ANTHROPIC_API_KEY` environment variable

### scripts/sync_images.py
Syncs and optimizes images from `listings/` to `docs/`:
- Smart sync (only updates changed files based on mtime)
- Optimization: resize to 1600px max, compress to 85% JPEG quality
- Uses Pillow (PIL) for image processing
- Non-destructive (originals in `listings/` unchanged)

## Important Patterns

### Adding a New Book
1. Create directory: `mkdir listings/new_book_slug`
2. Add images: `cp *.jpg listings/new_book_slug/`
3. Create `metadata.json` (copy from existing book as template)
4. Sync to docs: `make sync-images`
5. Generate CSV: `make build-csv`
6. Deploy: `make deploy`

### eBay CSV Format
Two exporters exist (both generate full URLs):
1. `src/ebay/exporter.py` - Standard format (23 fields)
2. `create_ebay_bulk_upload.py` - Extended format (45+ fields)
3. `scripts/populate_ebay_draft.py` - eBay draft template format

All use the same pattern: load metadata.json → build URLs → generate rows.

### Image URL Construction
Pattern used across all exporters:
```python
from src.utils.image_urls import ImageURLBuilder

url_builder = ImageURLBuilder()
pic_urls = url_builder.build_urls(listing_dir_name, images_dict)
# Returns: "https://zmuhls.github.io/mbooks/listings/book/img1.jpg|img2.jpg"
```

### GitHub Pages Deployment
1. Images must be in `/docs` directory (configured in repo settings)
2. Push to `main` branch triggers auto-deployment
3. Site updates within 1-2 minutes
4. URL pattern: `https://zmuhls.github.io/mbooks/listings/{book_slug}/{filename}.jpg`

## Configuration

### config.yaml
Central configuration for:
- Vision extraction prompts (Claude model, max images)
- eBay defaults (category 377, FixedPrice, GTC duration)
- Website theme and colors
- Validation rules (required fields, condition grades)

### Environment Variables
```bash
ANTHROPIC_API_KEY    # Required for LLM extraction
EBAY_CLIENT_ID       # For eBay API (future)
EBAY_CLIENT_SECRET   # For eBay API (future)
```

## Common Workflows

### Update Existing Book Images
```bash
# 1. Replace images in listings/
cp new_images/*.jpg listings/book_name/

# 2. Update metadata.json if needed
nano listings/book_name/metadata.json

# 3. Sync and deploy
make sync-images
make deploy
```

### Generate eBay Listing
```bash
# 1. Ensure images are synced and deployed
make build-csv

# 2. CSV appears in exports/ebay_upload_YYYYMMDD.csv
# 3. Fill in Price column (left blank)
# 4. Upload to eBay Seller Hub
```

### Test Image URLs
```bash
# 1. Generate CSV
make build-csv

# 2. Extract URL from CSV
grep "zmuhls.github.io" exports/ebay_upload_*.csv | head -1

# 3. Test in browser or curl
curl -I "https://zmuhls.github.io/mbooks/listings/book_name/image.jpg"
# Should return: HTTP/2 200, content-type: image/jpeg
```

## Critical Constraints

### GitHub Pages Limitations
- 100 GB/month bandwidth (current usage: ~2-3 GB/month)
- 1 GB repository size limit
- Images are publicly accessible (required for eBay anyway)

### eBay CSV Requirements
- Action field: "Add" or "Draft"
- Category: 377 (Antiquarian & Collectible Books)
- Title max: 80 characters
- Image URLs: Pipe-delimited, HTTPS, static
- Primary image must be first in pipe-delimited list

### Image Optimization
- Max dimension: 1600px (maintains aspect ratio)
- Quality: 85% JPEG compression
- Format: Always convert to RGB JPEG (handles RGBA/P modes)
- eBay recommendation: <12 MB per image

## File Organization

```
listings/{book_slug}/          # Source data
├── metadata.json              # Canonical metadata
└── *.jpg                      # Original images

docs/listings/{book_slug}/     # GitHub Pages deployment
├── metadata.json              # Synced copy
└── *.jpg                      # Optimized images

exports/                       # eBay CSV outputs
scripts/                       # Automation scripts
src/
├── core/                      # Listing models, config
├── ebay/                      # CSV exporters
├── utils/                     # ImageURLBuilder
└── vision/                    # LLM extraction
```

## Modifying Exporters

When changing CSV format or adding fields:
1. Update both `src/ebay/exporter.py` AND `create_ebay_bulk_upload.py`
2. Ensure `ImageURLBuilder` is used for URLs (not hardcoded)
3. Test with: `make build-csv && head -2 exports/ebay_upload_*.csv`
4. Verify pipe delimiters: `grep "PicURL" exports/ebay_upload_*.csv`

## Troubleshooting

### "ImportError: No module named src.utils"
- Run scripts from project root: `python src/ebay/exporter.py` (not from src/)
- Or use Makefile: `make build-csv`

### Images not showing on GitHub Pages
- Check if synced: `ls docs/listings/book_name/`
- Verify deployment: Wait 1-2 minutes after `git push`
- Test URL directly in browser
- Check Actions tab in GitHub repo for deployment status

### CSV has local filenames instead of URLs
- Verify `ImageURLBuilder` is imported and used
- Check `url_builder.build_urls()` is called (not manual path construction)
- Rebuild: `make build-csv`

### Optimization fails with "PIL/Pillow not installed"
- Install: `pip install Pillow`
- Or skip optimization: `python scripts/sync_images.py --no-optimize`
