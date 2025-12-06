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

