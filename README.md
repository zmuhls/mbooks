# Muhlbauer Books - Collectible Book Management System

A complete system for managing, cataloging, and listing collectible books with LLM-powered metadata extraction and eBay integration.

## Quick Start

### View the Catalog Website

```bash
python books.py serve
```

Then open: **http://localhost:8000**

### List All Books

```bash
python books.py list
```

### Export to eBay CSV

```bash
python books.py export
```

Output: `exports/ebay_upload_YYYYMMDD.csv`

## Directory Structure

```
photo_parsing/
├── books.py              # Main CLI tool
├── config.yaml           # System configuration
├── listings/             # Book catalog (8 books)
│   ├── first_blood_david_morrell/
│   │   ├── metadata.json
│   │   └── *.jpg
│   └── ...
├── site/                 # Website files
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── exports/              # eBay CSV exports
└── src/                  # Python modules
    ├── core/             # Config, models, schema
    ├── vision/           # LLM extraction
    └── ebay/             # eBay exporter
```

## Features

### Website
- **Minimalist design** - Clean, professional aesthetic
- **Search & filter** - Find books by title, author, or attributes
- **Image gallery** - Browse multiple photos per book
- **Responsive** - Works on desktop and mobile
- **Bonham's link** - Featured auction reference

### eBay Integration
- **Bulk CSV export** - Ready for eBay File Exchange
- **Standard fields** - Category 377 (Antiquarian & Collectible)
- **Auto-generated titles** - 80-char optimized with SIGNED/Limited tags
- **HTML descriptions** - Formatted with edition details

### LLM Extraction (Optional)
Extract metadata from book images using Claude vision:

```bash
# Set API key first
export ANTHROPIC_API_KEY=your_key_here

# Extract from a listing folder
python books.py extract first_blood_david_morrell
```

## Current Catalog

**8 Books Total:**
- 6 Signed editions
- 6 Limited editions
- 3 With slipcases

**Listings:**
1. Dark Delicacies - Signed #16/1250
2. Fearie Tales - Signed with slipcase
3. First Blood - Signed lettered edition PP/52
4. In Laymon's Terms - Signed #226/400
5. October Dreams - Halloween anthology
6. The Handyman - Signed #402/500
7. The Stand - Limited edition with slipcase
8. Zodiac - Signed #118/500

## Adding New Books

### Manual Entry

1. Create a new directory in `listings/`:
   ```bash
   mkdir listings/new_book_title
   ```

2. Add images to the directory

3. Create `metadata.json` following the schema in `config/schema.json`

4. Or copy an existing metadata.json and edit it

### With LLM Extraction

1. Create directory and add images:
   ```bash
   mkdir listings/new_book
   cp /path/to/images/*.jpg listings/new_book/
   ```

2. Extract metadata:
   ```bash
   export ANTHROPIC_API_KEY=your_key
   python books.py extract new_book
   ```

3. Edit the extracted data and save as `metadata.json`

## eBay Listing Workflow

### Quick Start

```bash
# 1. Add images and metadata to a listing
cp images/*.jpg listings/book_name/
nano listings/book_name/metadata.json

# 2. Generate eBay CSV with optimized images
make build-csv

# 3. Deploy images to GitHub Pages
make deploy

# 4. Upload CSV to eBay Seller Hub
```

### Generated CSV Format

The CSV will contain full GitHub Pages URLs in the `PicURL` field:

```
https://zmuhls.github.io/mbooks/listings/first_blood_david_morrell/IMG_5531.jpg|https://zmuhls.github.io/mbooks/listings/first_blood_david_morrell/IMG_5532.jpg
```

Primary images (specified in metadata.json) appear first.

### Image Optimization

Images are automatically:
- Resized to 1600px maximum dimension
- Compressed to 85% JPEG quality
- Optimized for web delivery

Original images in `listings/` remain unchanged.

### Background Blur (Optional)

Apply professional background blur to make books stand out:

**Setup:**

1. Install background removal library:
   ```bash
   pip install rembg
   ```

**Usage:**

```bash
# Apply background blur with default settings (15px radius)
python scripts/sync_images.py --apply-background

# Adjust blur intensity
python scripts/sync_images.py --apply-background --padding 0.20  # 20px blur
python scripts/sync_images.py --apply-background --padding 0.10  # 10px blur

# Preview without making changes
python scripts/sync_images.py --apply-background --dry-run
```

**How it works:**
- Detects book/subject using AI segmentation
- Applies Gaussian blur to background only
- Keeps book perfectly sharp and in focus
- Falls back to original image if processing fails
- Uses local `rembg` library (no API key required)

**Note:** Background processing adds ~2-5 seconds per image. Original images in `listings/` remain unchanged.

### Available Make Commands

```bash
make sync-images  # Sync and optimize images from listings/ to docs/
make build-csv    # Build eBay CSV with full image URLs (auto-syncs first)
make deploy       # Deploy images to GitHub Pages
make all          # Run complete workflow (sync + export + deploy)
```

### Manual Workflow (without Make)

```bash
# 1. Sync images to docs/
python scripts/sync_images.py

# 2. Generate CSV
python src/ebay/exporter.py listings

# 3. Deploy to GitHub Pages
git add docs/
git commit -m "sync images to github pages"
git push origin main
```

## Configuration

Edit `config.yaml` to customize:
- Website colors and branding
- eBay category and defaults
- LLM model selection
- Directory paths

## Website Customization

**Colors** - Edit `site/styles.css` variables:
```css
:root {
    --bg-dark: #1a1a1a;
    --accent: #c49a6c;
    /* ... */
}
```

**Content** - Edit `site/index.html`:
- Business name
- Tagline
- Contact email
- Bonham's link

## eBay Export Format

CSV includes all standard fields:
- Title, Description, Category
- Author, Publisher, Format
- Condition, Special Attributes
- Images (full GitHub Pages URLs - automatically hosted)
- Pricing (user fills in)
- Shipping & Returns

## Tech Stack

- **Frontend**: Vanilla JavaScript, CSS, HTML
- **Backend**: Python 3.8+
- **LLM**: Anthropic Claude (optional)
- **Data**: JSON metadata files
- **Export**: CSV for eBay

## Requirements

```bash
pip install -r requirements.txt
```

**Core:**
- PyYAML
- Python 3.8+

**Optional (for LLM extraction):**
- anthropic

## Support

For questions about the system, check:
- `config/schema.json` - Metadata structure
- `src/` modules - Implementation details
- `books.py --help` - CLI commands

## Contact

**Muhlbauer Books LLC**
Email: zmuhlbauer1@gmail.com

Recent Auction: [Highlights from the Medical Library of J Muhlbauer](https://www.bonhams.com/auction/31643/highlights-from-the-medical-library-of-j-muhlbauer/)
