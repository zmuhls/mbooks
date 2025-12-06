# Muhlbauer Books LLC - Collectible Books Gallery Website

A modern, interactive web gallery for showcasing your collectible book listings with images and detailed metadata.

## Quick Start

### Open the Website

Simply double-click `index.html` in this folder to open it in your default web browser. No server or installation required!

**Or** navigate to the folder and:
```bash
open index.html
```

## Features

### 📚 Browse Your Collection
- View all 8 collectible books in a responsive grid layout
- See primary image and key information at a glance
- Hover effects show visual feedback

### 🔍 Search & Filter
- **Search Box**: Find books by title, author, or editor
- **Filter Buttons**:
  - All: Show all books
  - Signed: Only signed editions
  - Limited Edition: Only limited edition books

### 📖 Detailed View
Click any book card to open the detailed modal with:

1. **Overview Tab**
   - Full creator information (author/editor/illustrator)
   - Edition details (limited edition info, copy numbers)
   - Signature information
   - Notes and special details

2. **Details Tab**
   - Publication information (publisher, year, pages)
   - Physical characteristics (format, binding, color, gilt details)
   - Dust jacket and slipcase status

3. **Condition Tab**
   - Overall condition grade
   - Condition notes
   - Special features
   - Any noted defects

### 🖼️ Image Gallery
- Click thumbnails to switch between images
- Primary image displayed prominently
- All images from your book folders are shown

## File Structure

```
photo_parsing/
├── index.html                          # Main website file
├── styles.css                          # Styling
├── script.js                           # Interactive functionality
├── ebay_bulk_upload.csv               # eBay bulk upload file
├── create_ebay_bulk_upload.py         # CSV generation script
├── WEBSITE_README.md                   # This file
└── [Book Folders]/                     # Listing directories
    ├── first_blood_david_morrell/
    ├── zodiac_neal_stephenson/
    ├── in_laymons_terms/
    ├── october_dreams/
    ├── dark_delicacies/
    ├── the_handyman_bentley_little/
    ├── fearie_tales/
    └── the_stand_stephen_king/
        ├── metadata.json               # Metadata for each book
        └── IMG_*.jpg                   # Book images
```

## How It Works

The website is completely **client-side** and works entirely in your browser:

1. Opens `index.html` in your browser
2. JavaScript loads all `metadata.json` files from book folders
3. Loads images directly from book folders
4. All searching, filtering, and display happens in your browser
5. No server needed - works completely offline after initial load

## Features by Book Type

### Signed Books
- Show signed badge in listing
- Signatory information in overview
- Edition size and copy number displayed

### Limited Editions
- Show limited edition badge
- Edition description and copy size
- Numbered or lettered copy information

### Anthologies
- Editor and contributor information
- Multiple signature pages
- Slipcase information if applicable

### Special Features
- Dust jacket presence and condition
- Slipcase information
- Leather binding and gilt details
- Color and binding type

## Responsive Design

The website works great on:
- ✓ Desktop computers
- ✓ Tablets
- ✓ Mobile phones
- ✓ Small screens (responsive layout adjusts automatically)

## Customization

### Change Business Name
Edit `index.html` line with:
```html
<h1>Muhlbauer Books LLC</h1>
```

### Adjust Colors
Open `styles.css` and modify the CSS variables at the top:
```css
:root {
    --primary-color: #2c3e50;
    --secondary-color: #e74c3c;
    --accent-color: #3498db;
    /* etc */
}
```

### Add More Books
1. Create a new folder in the same directory
2. Add `metadata.json` following the same structure
3. Add images to the folder
4. Update the `listingDirs` array in `script.js` to include the new folder name

## Browser Compatibility

Works on all modern browsers:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Sharing Your Gallery

### With Family/Friends
- Email them this entire folder
- They can open `index.html` directly
- Or host it on a web server

### GitHub Pages (Free Hosting)
1. Upload folder to GitHub repository
2. Enable GitHub Pages in repository settings
3. Share the public URL

### eBay Integration
The `ebay_bulk_upload.csv` file is ready for import into eBay's bulk upload tool.

## Troubleshooting

### Images not showing
- Make sure image files (IMG_*.jpg) are in the book subdirectories
- Check browser console (F12) for error messages
- Try opening with a different browser

### Metadata not loading
- Ensure `metadata.json` files exist in each book folder
- JSON files must be valid (check syntax)
- Open browser console to see error messages

### Search/filter not working
- Make sure browser JavaScript is enabled
- Try refreshing the page
- Check browser console for errors

## Technical Details

### Built With
- HTML5
- CSS3 (Grid, Flexbox, Custom Properties)
- Vanilla JavaScript (no frameworks)
- JSON for metadata storage

### Performance
- Lightweight (~60KB total)
- No external dependencies
- Fast loading (even over slow connections)
- Offline capable

## Future Enhancements

Possible additions:
- Pricing display
- eBay listing links
- Print functionality
- PDF catalog generation
- Database backend for more books
- Admin panel for easy updates

## Support

For issues or questions:
1. Check the browser console (F12) for error messages
2. Ensure all files are in the correct locations
3. Verify metadata.json files are valid
4. Try with a different browser

---

**Created for:** Muhlbauer Books LLC
**Last Updated:** December 6, 2025
