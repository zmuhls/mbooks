.PHONY: sync-images sync-images-bg build-csv build-csv-bg deploy all help

# Sync images from listings/ to docs/listings/ with optimization
sync-images:
	@echo "Syncing and optimizing images..."
	@python scripts/sync_images.py
	@echo "Sync complete."

# Sync images with black wooden table background
sync-images-bg:
	@echo "Syncing images with black table background..."
	@python scripts/sync_images.py --apply-background
	@echo "Sync complete."

# Build eBay CSV export with full image URLs
build-csv: sync-images
	@echo "Building eBay CSV export..."
	@python src/ebay/exporter.py listings
	@echo "Export complete. Check exports/ directory."

# Build eBay CSV with background-processed images
build-csv-bg: sync-images-bg
	@echo "Building eBay CSV export..."
	@python src/ebay/exporter.py listings
	@echo "Export complete. Check exports/ directory."

# Deploy to GitHub Pages (commit and push docs/)
deploy: sync-images
	@echo "Deploying to GitHub Pages..."
	@git add docs/
	@git commit -m "sync images to github pages" || true
	@git push origin main
	@echo "Deployed. Site will update in 1-2 minutes."

# Combined workflow: sync, export CSV, and deploy
all: sync-images build-csv deploy
	@echo "Complete workflow finished!"

# Show available commands
help:
	@echo "Available commands:"
	@echo "  make sync-images     - Sync and optimize images from listings/ to docs/"
	@echo "  make sync-images-bg  - Sync with black wooden table backgrounds"
	@echo "  make build-csv       - Build eBay CSV with full image URLs (auto-syncs first)"
	@echo "  make build-csv-bg    - Build eBay CSV with background-processed images"
	@echo "  make deploy          - Deploy images to GitHub Pages"
	@echo "  make all             - Run complete workflow (sync + export + deploy)"
	@echo ""
	@echo "Example workflow:"
	@echo "  1. Add images to listings/book_name/"
	@echo "  2. make build-csv"
	@echo "  3. make deploy"
	@echo "  4. Upload CSV to eBay"
	@echo ""
	@echo "Background processing workflow:"
	@echo "  1. pip install rembg  (first time only)"
	@echo "  2. make build-csv-bg"
	@echo "  3. make deploy"
