# GitHub Pages Setup

## Enable GitHub Pages

1. Go to your repository: https://github.com/zmuhls/mbooks

2. Click **Settings** (top right)

3. In the left sidebar, click **Pages**

4. Under "Build and deployment":
   - **Source**: Deploy from a branch
   - **Branch**: main
   - **Folder**: /docs
   - Click **Save**

5. Wait 1-2 minutes for deployment

6. Your site will be live at: **https://zmuhls.github.io/mbooks/**

## What's Deployed

The `docs/` directory contains:
- `index.html` - Main catalog page
- `app.js` - JavaScript (uses relative paths)
- `styles.css` - Minimalist theme
- `listings/` - All 8 book catalogs with images

## Image Hosting for eBay Listings

GitHub Pages serves as the image host for eBay bulk upload CSVs.

### Image URLs

All images are publicly accessible at:
```
https://zmuhls.github.io/mbooks/listings/{book_name}/{image_file}.jpg
```

Example:
```
https://zmuhls.github.io/mbooks/listings/first_blood_david_morrell/IMG_5531.jpg
```

### Complete Workflow

When adding new books or updating images:

```bash
# 1. Add images to listings directory
cp *.jpg listings/new_book/

# 2. Sync and build CSV (with optimization)
make build-csv

# 3. Deploy to GitHub Pages
make deploy

# 4. Wait 1-2 minutes for deployment, then upload CSV to eBay
```

### Image Optimization

Images are automatically optimized during sync:
- Resized to max 1600px (maintains aspect ratio)
- Compressed to 85% JPEG quality
- Reduces bandwidth and loads faster on eBay

To skip optimization:
```bash
python scripts/sync_images.py --no-optimize
```

### Bandwidth Considerations

- Current: 22 images, ~46 MB total (will be ~25-30 MB after optimization)
- GitHub Pages limit: 100 GB/month
- Estimated usage: 2-3 GB/month with moderate traffic
- Well within free tier limits

## Updates

To update the live site:

```bash
# Make changes to docs/ directory
# Or update listings/ and copy to docs/

git add docs/
git commit -m "update catalog"
git push
```

Site updates automatically within 1-2 minutes.

## Local Testing

Test the docs site locally before pushing:

```bash
cd docs
python3 -m http.server 8000
```

Open http://localhost:8000

## Custom Domain (Optional)

To use a custom domain:

1. Add a `CNAME` file to `docs/`:
   ```bash
   echo "books.yourdomain.com" > docs/CNAME
   ```

2. Configure DNS with your domain provider:
   - Add CNAME record pointing to `zmuhls.github.io`

3. In GitHub Pages settings, enter your custom domain

