// Muhlbauer Books - Catalog Application
// Loads listings from ./listings/ directories

const LISTINGS_PATH = './listings';

let allListings = [];
let currentListing = null;
let currentImageIndex = 0;

// Book directories to load
const bookDirs = [
    'dark_delicacies',
    'fearie_tales',
    'first_blood_david_morrell',
    'in_laymons_terms',
    'october_dreams',
    'the_handyman_bentley_little',
    'the_stand_stephen_king',
    'zodiac_neal_stephenson'
];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadListings();
    renderBooks(allListings);
    updateStats();
    setupEventListeners();
});

// Load all listings
async function loadListings() {
    for (const dir of bookDirs) {
        try {
            const res = await fetch(`${LISTINGS_PATH}/${dir}/metadata.json`);
            if (res.ok) {
                const data = await res.json();
                data._directory = dir;
                allListings.push(data);
            }
        } catch (e) {
            console.warn(`Could not load ${dir}`);
        }
    }
}

// Update hero stats
function updateStats() {
    const total = allListings.length;
    const signed = allListings.filter(b => b.edition_details?.is_signed).length;
    const limited = allListings.filter(b => b.edition_details?.is_limited_edition).length;

    document.getElementById('totalBooks').textContent = total;
    document.getElementById('signedBooks').textContent = signed;
    document.getElementById('limitedBooks').textContent = limited;
}

// Render book grid
function renderBooks(books) {
    const grid = document.getElementById('bookGrid');
    const empty = document.getElementById('emptyState');

    if (books.length === 0) {
        grid.innerHTML = '';
        empty.style.display = 'block';
        return;
    }

    empty.style.display = 'none';
    grid.innerHTML = books.map((book, idx) => createBookCard(book, idx)).join('');

    // Attach click handlers
    grid.querySelectorAll('.book-card').forEach((card, idx) => {
        card.addEventListener('click', () => openModal(books[idx]));
    });
}

// Create book card HTML
function createBookCard(book, idx) {
    const basic = book.basic_info || {};
    const edition = book.edition_details || {};
    const physical = book.physical_details || {};
    const images = book.images || {};

    const primaryImg = images.primary_image || images.files?.[0] || '';
    const imgSrc = primaryImg ? `${LISTINGS_PATH}/${book._directory}/${primaryImg}` : '';

    let creator = basic.author || basic.editor || '';
    if (basic.author) creator = `by ${creator}`;
    else if (basic.editor) creator = `Ed. ${creator}`;

    const badges = [];
    if (edition.is_signed) badges.push('<span class="badge badge-signed">Signed</span>');
    if (edition.is_limited_edition) badges.push('<span class="badge badge-limited">Limited</span>');
    if (physical.has_slipcase) badges.push('<span class="badge badge-slipcase">Slipcase</span>');

    return `
        <article class="book-card" data-idx="${idx}">
            <div class="book-image-container">
                <img class="book-image" src="${imgSrc}" alt="${basic.title}" loading="lazy"
                     onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 133%22%3E%3Crect fill=%22%231a1a2e%22 width=%22100%22 height=%22133%22/%3E%3Ctext x=%2250%22 y=%2270%22 fill=%22%23666%22 text-anchor=%22middle%22 font-size=%2210%22%3ENo Image%3C/text%3E%3C/svg%3E'">
                <div class="book-image-overlay"></div>
                <div class="book-badges">${badges.join('')}</div>
            </div>
            <div class="book-info">
                <h3 class="book-title">${basic.title || 'Untitled'}</h3>
                <p class="book-creator">${creator}</p>
                <div class="book-meta">
                    <span class="book-edition">${edition.edition_description || physical.format || ''}</span>
                    <span class="book-images-count">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2"/>
                            <circle cx="8.5" cy="8.5" r="1.5"/>
                            <path d="m21 15-5-5L5 21"/>
                        </svg>
                        ${images.files?.length || 0}
                    </span>
                </div>
            </div>
        </article>
    `;
}

// Setup event listeners
function setupEventListeners() {
    // Search
    document.getElementById('searchInput').addEventListener('input', filterBooks);

    // Filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterBooks();
        });
    });

    // Modal close
    document.querySelector('.modal-close').addEventListener('click', closeModal);
    document.querySelector('.modal-backdrop').addEventListener('click', closeModal);

    // Gallery navigation
    document.querySelector('.gallery-prev').addEventListener('click', () => navigateGallery(-1));
    document.querySelector('.gallery-next').addEventListener('click', () => navigateGallery(1));

    // Tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(`tab${btn.dataset.tab.charAt(0).toUpperCase() + btn.dataset.tab.slice(1)}`).classList.add('active');
        });
    });

    // Keyboard navigation
    document.addEventListener('keydown', e => {
        if (!document.getElementById('bookModal').classList.contains('active')) return;
        if (e.key === 'Escape') closeModal();
        if (e.key === 'ArrowLeft') navigateGallery(-1);
        if (e.key === 'ArrowRight') navigateGallery(1);
    });
}

// Filter books
function filterBooks() {
    const search = document.getElementById('searchInput').value.toLowerCase();
    const filter = document.querySelector('.filter-btn.active').dataset.filter;

    let filtered = allListings.filter(book => {
        const basic = book.basic_info || {};
        const edition = book.edition_details || {};
        const physical = book.physical_details || {};

        // Search
        if (search) {
            const searchable = [
                basic.title, basic.author, basic.editor,
                edition.edition_description, book.notes
            ].filter(Boolean).join(' ').toLowerCase();
            if (!searchable.includes(search)) return false;
        }

        // Filter
        if (filter === 'signed' && !edition.is_signed) return false;
        if (filter === 'limited' && !edition.is_limited_edition) return false;
        if (filter === 'slipcase' && !physical.has_slipcase) return false;

        return true;
    });

    renderBooks(filtered);
}

// Open modal
function openModal(book) {
    currentListing = book;
    currentImageIndex = 0;

    const modal = document.getElementById('bookModal');
    const basic = book.basic_info || {};
    const edition = book.edition_details || {};
    const physical = book.physical_details || {};
    const pub = book.publication_details || {};
    const condition = book.condition || {};
    const images = book.images || {};

    // Title and creator
    document.getElementById('modalTitle').textContent = basic.title || 'Untitled';
    let creator = basic.author ? `by ${basic.author}` : basic.editor ? `Edited by ${basic.editor}` : '';
    if (basic.illustrator) creator += ` / Illustrated by ${basic.illustrator}`;
    document.getElementById('modalCreator').textContent = creator;

    // Badges
    const badges = [];
    if (edition.is_signed) badges.push('<span class="badge badge-signed">Signed</span>');
    if (edition.is_limited_edition) badges.push('<span class="badge badge-limited">Limited Edition</span>');
    if (physical.has_slipcase) badges.push('<span class="badge badge-slipcase">Slipcase</span>');
    if (physical.has_dust_jacket) badges.push('<span class="badge badge-limited">Dust Jacket</span>');
    document.getElementById('modalBadges').innerHTML = badges.join('');

    // Gallery
    const files = images.files || [];
    if (files.length > 0) {
        updateGalleryImage();
        document.getElementById('galleryThumbs').innerHTML = files.map((f, i) => `
            <div class="gallery-thumb ${i === 0 ? 'active' : ''}" data-idx="${i}">
                <img src="${LISTINGS_PATH}/${book._directory}/${f}" alt="Image ${i + 1}">
            </div>
        `).join('');

        document.querySelectorAll('.gallery-thumb').forEach(thumb => {
            thumb.addEventListener('click', () => {
                currentImageIndex = parseInt(thumb.dataset.idx);
                updateGalleryImage();
            });
        });
    }

    // Overview tab
    let overviewHTML = '';
    if (edition.edition_description) {
        overviewHTML += `<div class="edition-box"><strong>${edition.edition_description}</strong>`;
        if (edition.edition_size) overviewHTML += `<br>Limited to ${edition.edition_size} copies`;
        if (edition.copy_identifier) overviewHTML += `<br>Copy: ${edition.copy_identifier.value}`;
        if (edition.is_signed) {
            overviewHTML += `<br><strong>Signed</strong>`;
            if (edition.signed_by) overviewHTML += ` by ${edition.signed_by}`;
            if (edition.signature_notes) overviewHTML += ` (${edition.signature_notes})`;
        }
        overviewHTML += '</div>';
    }
    if (book.notes) {
        overviewHTML += `<p class="notes-text">${book.notes}</p>`;
    }
    document.getElementById('tabOverview').innerHTML = overviewHTML || '<p class="notes-text">No additional details available.</p>';

    // Details tab
    let detailsHTML = '<div class="detail-section"><h4>Publication</h4>';
    if (pub.publisher) detailsHTML += `<div class="detail-row"><span class="detail-label">Publisher</span><span class="detail-value">${pub.publisher}</span></div>`;
    if (pub.publication_year) detailsHTML += `<div class="detail-row"><span class="detail-label">Year</span><span class="detail-value">${pub.publication_year}</span></div>`;
    if (pub.isbn_10 || pub.isbn_13) detailsHTML += `<div class="detail-row"><span class="detail-label">ISBN</span><span class="detail-value">${pub.isbn_13 || pub.isbn_10}</span></div>`;
    detailsHTML += '</div><div class="detail-section"><h4>Physical</h4>';
    if (physical.format) detailsHTML += `<div class="detail-row"><span class="detail-label">Format</span><span class="detail-value">${physical.format}</span></div>`;
    if (physical.binding_type) detailsHTML += `<div class="detail-row"><span class="detail-label">Binding</span><span class="detail-value">${physical.binding_type}</span></div>`;
    if (physical.binding_color) detailsHTML += `<div class="detail-row"><span class="detail-label">Color</span><span class="detail-value">${physical.binding_color}</span></div>`;
    if (physical.gilt_details) detailsHTML += `<div class="detail-row"><span class="detail-label">Gilt</span><span class="detail-value">${physical.gilt_details}</span></div>`;
    detailsHTML += '</div>';
    document.getElementById('tabDetails').innerHTML = detailsHTML;

    // Condition tab
    let conditionHTML = '<div class="detail-section">';
    if (condition.overall_grade) {
        const grades = { NEW: 'New', LIKE_NEW: 'Like New', VERY_GOOD: 'Very Good', GOOD: 'Good', ACCEPTABLE: 'Acceptable' };
        conditionHTML += `<div class="detail-row"><span class="detail-label">Grade</span><span class="detail-value">${grades[condition.overall_grade] || condition.overall_grade}</span></div>`;
    }
    if (condition.condition_notes) {
        conditionHTML += `<p class="notes-text" style="margin-top: 1rem;">${condition.condition_notes}</p>`;
    }
    conditionHTML += '</div>';
    document.getElementById('tabCondition').innerHTML = conditionHTML;

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
    document.getElementById('bookModal').classList.remove('active');
    document.body.style.overflow = '';
    currentListing = null;
}

// Navigate gallery
function navigateGallery(direction) {
    if (!currentListing) return;
    const files = currentListing.images?.files || [];
    if (files.length === 0) return;

    currentImageIndex = (currentImageIndex + direction + files.length) % files.length;
    updateGalleryImage();
}

// Update gallery image
function updateGalleryImage() {
    if (!currentListing) return;
    const files = currentListing.images?.files || [];
    if (files.length === 0) return;

    const src = `${LISTINGS_PATH}/${currentListing._directory}/${files[currentImageIndex]}`;
    document.getElementById('modalMainImage').src = src;

    document.querySelectorAll('.gallery-thumb').forEach((thumb, i) => {
        thumb.classList.toggle('active', i === currentImageIndex);
    });
}
