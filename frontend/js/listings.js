// listings.js — rendering + CRUD for listings.

// Appends the read-only SAS token (see config.js) to Azure Blob Storage
// URLs so <img> tags can load photos — the container itself stays
// private; this is a scoped, revocable credential, not public access.
function withImageAccess(url) {
    if (url && typeof AZURE_BLOB_SAS !== 'undefined' && AZURE_BLOB_SAS && url.includes('blob.core.windows.net')) {
        return url + (url.includes('?') ? '&' : '?') + AZURE_BLOB_SAS;
    }
    return url;
}

function buildListingCard(listing, favoriteIds) {
    const categoryLabel = CATEGORY_LABELS[listing.category] || listing.category;
    const favActive = (favoriteIds && favoriteIds.has(listing.id)) ? ' active' : '';
    return `
    <article class="listing-card" data-id="${escapeHTML(listing.id)}" data-title="${escapeHTML(listing.title.toLowerCase())}" data-description="${escapeHTML(listing.description.toLowerCase())}" data-category="${escapeHTML(listing.category)}">
      <button type="button" class="favorite-btn${favActive}" title="Save to favorites">&#9825;</button>
      <a href="listing.html?id=${encodeURIComponent(listing.id)}">
        <img src="${escapeHTML(withImageAccess(listing.imageUrl) || 'assets/img/placeholder.png')}" alt="${escapeHTML(listing.title)}">
        <div class="listing-info">
          <h3>${escapeHTML(listing.title)}</h3>
          <div class="listing-meta">
            <span class="price">€${escapeHTML(String(listing.price))}</span>
            <span class="category-tag">${escapeHTML(categoryLabel)}</span>
          </div>
          <span class="seller">Posted by ${escapeHTML(listing.sellerName)}</span>
        </div>
      </a>
    </article>
  `;
}

function renderListingGrid(listings, favoriteIds) {
    const $grid = $('#listing-grid');
    $grid.empty();
    const visible = listings.filter(function (l) { return l.status === 'active'; });
    if (visible.length === 0) {
        $grid.html('<p class="subtitle">No listings match yet. Be the first to post something.</p>');
        return;
    }
    visible.forEach(function (listing) { $grid.append(buildListingCard(listing, favoriteIds)); });
    $grid.append('<p class="subtitle hidden" id="no-results">No listings match your search.</p>');
}

function applyFilters() {
    const query = $('#search-input').val().trim().toLowerCase();
    const category = $('.filter-pill.active').data('category');
    let anyVisible = false;

    $('.listing-card').each(function () {
        const $card = $(this);
        const matchesCategory = (category === 'all') || (String($card.data('category')) === String(category));
        const matchesQuery = !query ||
            String($card.data('title')).includes(query) ||
            String($card.data('description')).includes(query);
        const show = matchesCategory && matchesQuery;
        $card.toggle(show);
        if (show) anyVisible = true;
    });

    $('#no-results').toggle(!anyVisible);
}

function renderListingDetail(listing) {
    if (!listing) { $('#listing-detail').html('<p class="subtitle">This listing no longer exists.</p>'); return; }
    document.title = listing.title + ' – CampusSwap';
    $('.main-image').attr('src', withImageAccess(listing.imageUrl) || 'assets/img/placeholder.png').attr('alt', listing.title);
    $('.detail-info h1').text(listing.title);
    $('.detail-info .price').text('€' + listing.price);
    $('.detail-info .category-tag').text(CATEGORY_LABELS[listing.category] || listing.category);
    $('#detail-condition').text(listing.condition);
    $('#detail-posted').text(listing.datePosted);
    $('#detail-description').text(listing.description);
    $('#contact-card .subtitle').text('Start a conversation with ' + listing.sellerName);
    $('#seller-name').text(listing.sellerName);
}

function createListing(formData) {
    return apiCreateListing(formData);
}

function updateListing(id, formData) {
    return apiUpdateListing(id, formData);
}

function removeListing(id) {
    return apiDeleteListing(id);
}

function reportListing(id, reason) {
    return apiReportListing(id, reason);
}

function toggleFavorite(id) {
    return apiToggleFavorite(id);
}

function prefillListingForm(listing) {
    $('#title').val(listing.title);
    $('#category').val(listing.category);
    $('#price').val(listing.price);
    $('#condition').val(listing.condition);
    $('#description').val(listing.description);
    if (listing.imageUrl && !listing.imageUrl.endsWith('placeholder.png')) {
        $('#image-preview').attr('src', withImageAccess(listing.imageUrl)).removeClass('hidden');
        $('#upload-label').text('Current photo (choose a new file to replace it)');
    }
    $('h1').text('Edit listing');
    $('.form-actions button').text('Save changes');
}

function renderMyListings(listings, inquiries) {
    const $section = $('#my-listings');
    $section.empty();
    if (!listings.length) { $section.html('<p class="subtitle">You haven\'t posted anything yet.</p>'); return; }
    listings.forEach(function (listing) {
        const count = inquiries.filter(function (i) { return i.listingId === listing.id; }).length;
        $section.append(`
      <div class="dashboard-row" data-id="${escapeHTML(listing.id)}">
        <img src="${escapeHTML(withImageAccess(listing.imageUrl))}" alt="">
        <div class="row-info"><h3>${escapeHTML(listing.title)}</h3><span class="price">€${escapeHTML(String(listing.price))}</span></div>
        <span class="badge-count${count === 0 ? ' zero' : ''}">${count}</span>
        <div class="row-actions"><button class="btn-secondary btn-edit">Edit</button><button class="btn-secondary btn-delete">Delete</button></div>
      </div>
    `);
    });
}

function renderModeratorQueue(listings) {
    const $list = $('#moderator-queue .queue-list');
    $list.empty();
    if (!listings.length) { $list.html('<p class="subtitle">Nothing reported right now.</p>'); return; }
    listings.forEach(function (listing) {
        $list.append(`
      <div class="dashboard-row" data-id="${escapeHTML(listing.id)}">
        <div class="row-info"><h3>${escapeHTML(listing.title)}</h3><span class="subtitle">Reason: ${escapeHTML(listing.reportReason)}</span></div>
        <div class="row-actions"><a href="listing.html?id=${encodeURIComponent(listing.id)}" class="btn-secondary">View</a> <button class="btn-danger btn-remove">Remove</button></div>
      </div>
    `);
    });
}

function renderFavorites(listings) {
    const $section = $('#favorites');
    $section.empty();
    if (!listings.length) { $section.html('<p class="subtitle">Nothing favorited yet — tap the heart on any listing from the homepage.</p>'); return; }
    listings.forEach(function (listing) {
        $section.append(`
      <div class="dashboard-row" data-id="${escapeHTML(listing.id)}">
        <img src="${escapeHTML(withImageAccess(listing.imageUrl))}" alt="">
        <div class="row-info"><h3>${escapeHTML(listing.title)}</h3><span class="price">€${escapeHTML(String(listing.price))}</span></div>
        <div class="row-actions"><a href="listing.html?id=${encodeURIComponent(listing.id)}" class="btn-secondary">View</a></div>
      </div>
    `);
    });
}
