// List of all book listing directories
const listingDirs = [
    'first_blood_david_morrell',
    'zodiac_neal_stephenson',
    'in_laymons_terms',
    'october_dreams',
    'dark_delicacies',
    'the_handyman_bentley_little',
    'fearie_tales',
    'the_stand_stephen_king'
];

let allListings = [];
let filteredListings = [];

// Initialize the app
document.addEventListener('DOMContentLoaded', async () => {
    await loadAllListings();
    renderListings(allListings);
    setupEventListeners();
});

// Load all metadata files
async function loadAllListings() {
    try {
        for (const dir of listingDirs) {
            try {
                const response = await fetch(`${dir}/metadata.json`);
                const data = await response.json();
                // Add directory path to metadata for image loading
                data.directory = dir;
                allListings.push(data);
            } catch (error) {
                console.error(`Failed to load ${dir}/metadata.json:`, error);
            }
        }
        console.log(`Loaded ${allListings.length} listings`);
    } catch (error) {
        console.error('Error loading listings:', error);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Search functionality
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        filterListings(searchTerm, 'all');
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const filterType = btn.dataset.filter;
            filterListings(searchTerm, filterType);
        });
    });

    // Tab switching in modal
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabName = btn.dataset.tab;
            switchTab(tabName);
        });
    });
}

// Filter listings
function filterListings(searchTerm, filterType) {
    filteredListings = allListings.filter(listing => {
        const basic = listing.basic_info || {};
        const edition = listing.edition_details || {};

        // Search term filter
        const matchesSearch = !searchTerm ||
            (basic.title && basic.title.toLowerCase().includes(searchTerm)) ||
            (basic.author && basic.author.toString().toLowerCase().includes(searchTerm)) ||
            (basic.editor && basic.editor.toString().toLowerCase().includes(searchTerm));

        if (!matchesSearch) return false;

        // Type filter
        if (filterType === 'all') return true;
        if (filterType === 'signed') return edition.is_signed;
        if (filterType === 'limited') return edition.is_limited_edition;

        return true;
    });

    renderListings(filteredListings);
}

// Render listings grid
function renderListings(listings) {
    const container = document.getElementById('listings-container');

    if (listings.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <h2>No books found</h2>
                <p>Try adjusting your search or filter criteria</p>
            </div>
        `;
        return;
    }

    container.innerHTML = listings.map(listing => createListingCard(listing)).join('');

    // Add click handlers to cards
    document.querySelectorAll('.listing-card').forEach((card, index) => {
        card.addEventListener('click', () => openModal(listings[index]));
    });
}

// Create a listing card
function createListingCard(listing) {
    const basic = listing.basic_info || {};
    const edition = listing.edition_details || {};
    const physical = listing.physical_details || {};
    const images = listing.images || {};

    const primaryImage = images.primary_image || images.files?.[0];
    const imageUrl = primaryImage ? `${listing.directory}/${primaryImage}` : 'placeholder.jpg';

    // Build author/editor text
    let creator = '';
    if (basic.author) {
        const author = Array.isArray(basic.author) ? basic.author[0] : basic.author;
        creator = `by ${author}`;
    } else if (basic.editor) {
        const editor = Array.isArray(basic.editor) ? basic.editor[0] : basic.editor;
        creator = `Ed. ${editor}`;
    }

    // Build badges
    let badges = '';
    if (edition.is_signed) badges += '<span class="badge signed">Signed</span>';
    if (edition.is_limited_edition) badges += '<span class="badge limited">Limited</span>';
    if (physical.has_slipcase) badges += '<span class="badge slipcase">Slipcase</span>';

    return `
        <div class="listing-card">
            <img src="${imageUrl}" alt="${basic.title}" class="listing-image" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22280%22 height=%22350%22%3E%3Crect fill=%22%23f0f0f0%22 width=%22280%22 height=%22350%22/%3E%3Ctext x=%2250%25%22 y=%2250%25%22 font-size=%2218%22 fill=%22%23999%22 text-anchor=%22middle%22 dominant-baseline=%22middle%22%3EImage not found%3C/text%3E%3C/svg%3E'">
            <div class="listing-info">
                <h3 class="listing-title">${basic.title || 'Unknown Title'}</h3>
                ${creator ? `<p class="listing-author">${creator}</p>` : ''}
                <div class="listing-badges">
                    ${badges}
                </div>
                <div class="listing-footer">
                    <span>${images.files?.length || 0} images</span>
                    <button class="view-btn">View Details</button>
                </div>
            </div>
        </div>
    `;
}

// Open detail modal
function openModal(listing) {
    const modal = document.getElementById('detailModal');
    const basic = listing.basic_info || {};
    const pub = listing.publication_details || {};
    const edition = listing.edition_details || {};
    const physical = listing.physical_details || {};
    const condition = listing.condition || {};
    const images = listing.images || {};

    // Set title
    document.getElementById('detailTitle').textContent = basic.title || 'Unknown Title';

    // Set main image
    const primaryImage = images.primary_image || images.files?.[0];
    const mainImageUrl = primaryImage ? `${listing.directory}/${primaryImage}` : '';
    if (mainImageUrl) {
        document.getElementById('mainImage').src = mainImageUrl;
    }

    // Build thumbnails
    const thumbnailGallery = document.getElementById('thumbnailGallery');
    thumbnailGallery.innerHTML = (images.files || []).map((file, idx) => `
        <div class="thumbnail ${idx === 0 ? 'active' : ''}" onclick="switchImage('${listing.directory}/${file}', this)">
            <img src="${listing.directory}/${file}" alt="Image ${idx + 1}">
        </div>
    `).join('');

    // Build overview tab
    const overviewTab = document.getElementById('overview');
    let overviewHTML = '<div class="info-section">';

    // Creator info
    if (basic.author) {
        const author = Array.isArray(basic.author) ? basic.author.join(', ') : basic.author;
        overviewHTML += `<div class="info-item"><span class="info-label">Author:</span><span class="info-value">${author}</span></div>`;
    }
    if (basic.editor) {
        const editor = Array.isArray(basic.editor) ? basic.editor.join(', ') : basic.editor;
        overviewHTML += `<div class="info-item"><span class="info-label">Editor:</span><span class="info-value">${editor}</span></div>`;
    }
    if (basic.illustrator) {
        overviewHTML += `<div class="info-item"><span class="info-label">Illustrator:</span><span class="info-value">${basic.illustrator}</span></div>`;
    }

    // Edition info
    if (edition.edition_description) {
        overviewHTML += `<div class="edition-box"><strong>${edition.edition_description}</strong>`;
        if (edition.edition_size) {
            overviewHTML += `<div>Limited to ${edition.edition_size} copies</div>`;
        }
        if (edition.copy_identifier) {
            overviewHTML += `<div>Copy: ${edition.copy_identifier.value}</div>`;
        }
        if (edition.is_signed) {
            overviewHTML += `<div><strong>✓ Signed</strong>`;
            if (edition.signed_by) {
                const signedBy = Array.isArray(edition.signed_by) ? edition.signed_by.join(', ') : edition.signed_by;
                overviewHTML += ` by ${signedBy}`;
            }
            overviewHTML += `</div>`;
        }
        overviewHTML += '</div>';
    }

    overviewHTML += '</div>';

    // Notes section
    if (listing.notes) {
        overviewHTML += `<div class="info-section"><h3>Details</h3><p>${listing.notes}</p></div>`;
    }

    overviewTab.innerHTML = overviewHTML;

    // Build details tab
    const detailsTab = document.getElementById('details');
    let detailsHTML = '<div class="info-section"><h3>Publication</h3>';

    if (pub.publisher) detailsHTML += `<div class="info-item"><span class="info-label">Publisher:</span><span class="info-value">${pub.publisher}</span></div>`;
    if (pub.publication_year) detailsHTML += `<div class="info-item"><span class="info-label">Year:</span><span class="info-value">${pub.publication_year}</span></div>`;
    if (pub.page_count) detailsHTML += `<div class="info-item"><span class="info-label">Pages:</span><span class="info-value">${pub.page_count}</span></div>`;

    detailsHTML += '</div><div class="info-section"><h3>Physical</h3>';

    if (physical.format) detailsHTML += `<div class="info-item"><span class="info-label">Format:</span><span class="info-value">${physical.format}</span></div>`;
    if (physical.binding_type) detailsHTML += `<div class="info-item"><span class="info-label">Binding:</span><span class="info-value">${physical.binding_type}</span></div>`;
    if (physical.binding_color) detailsHTML += `<div class="info-item"><span class="info-label">Color:</span><span class="info-value">${physical.binding_color}</span></div>`;
    if (physical.gilt_details) detailsHTML += `<div class="info-item"><span class="info-label">Gilt:</span><span class="info-value">${physical.gilt_details}</span></div>`;
    if (physical.has_dust_jacket) detailsHTML += `<div class="info-item"><span class="info-label">Dust Jacket:</span><span class="info-value">Yes</span></div>`;
    if (physical.has_slipcase) detailsHTML += `<div class="info-item"><span class="info-label">Slipcase:</span><span class="info-value">Yes</span></div>`;

    detailsHTML += '</div>';
    detailsTab.innerHTML = detailsHTML;

    // Build condition tab
    const conditionTab = document.getElementById('condition');
    let conditionHTML = '<div class="info-section">';

    if (condition.overall_grade) {
        const gradeMap = {
            'NEW': 'New',
            'LIKE_NEW': 'Like New',
            'VERY_GOOD': 'Very Good',
            'GOOD': 'Good',
            'ACCEPTABLE': 'Acceptable'
        };
        const grade = gradeMap[condition.overall_grade] || condition.overall_grade;
        conditionHTML += `<div class="info-item"><span class="info-label">Grade:</span><span class="info-value condition-good">${grade}</span></div>`;
    }

    if (condition.condition_notes) {
        conditionHTML += `<p>${condition.condition_notes}</p>`;
    }

    if (condition.special_features && condition.special_features.length > 0) {
        conditionHTML += '<h3>Special Features</h3><ul>';
        condition.special_features.forEach(feature => {
            conditionHTML += `<li>✓ ${feature}</li>`;
        });
        conditionHTML += '</ul>';
    }

    if (condition.defects && condition.defects.length > 0) {
        conditionHTML += '<h3>Noted Issues</h3><ul>';
        condition.defects.forEach(defect => {
            conditionHTML += `<li>• ${defect}</li>`;
        });
        conditionHTML += '</ul>';
    }

    conditionHTML += '</div>';
    conditionTab.innerHTML = conditionHTML;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
    document.getElementById('detailModal').style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Switch image in modal
function switchImage(imagePath, element) {
    document.getElementById('mainImage').src = imagePath;
    document.querySelectorAll('.thumbnail').forEach(th => th.classList.remove('active'));
    element.classList.add('active');
}

// Switch tabs in modal
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('detailModal');
    if (e.target === modal) {
        closeModal();
    }
});
