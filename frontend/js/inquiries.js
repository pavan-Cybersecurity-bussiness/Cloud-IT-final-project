// inquiries.js — creating and rendering inquiries tied to a listing.
// Now backed by the Messaging service through api.js instead of localStorage.

function createInquiry(listingId, listingTitle, sellerName, fromName, message) {
    return apiCreateInquiry({
        listingId: listingId,
        listingTitle: listingTitle,
        sellerName: sellerName,
        fromName: fromName.trim(),
        message: message.trim()
    });
}

function dismissInquiry(id) {
    return apiDismissInquiry(id);
}

// Every inquiry sent to any listing owned by the current seller.
function renderMessages(inquiries) {
    const $section = $('#messages');
    $section.empty();

    if (!inquiries.length) { $section.html('<p class="subtitle">No messages yet.</p>'); return; }

    inquiries.forEach(function (inquiry) {
        $section.append(`
      <div class="dashboard-row" data-id="${escapeHTML(inquiry.id)}">
        <div class="row-info">
          <h3>${escapeHTML(inquiry.fromName)} — re: ${escapeHTML(inquiry.listingTitle)}</h3>
          <p>${escapeHTML(inquiry.message)}</p>
          <span class="subtitle">${escapeHTML(inquiry.datePosted)}</span>
        </div>
        <div class="row-actions"><button class="btn-secondary btn-dismiss">Dismiss</button></div>
      </div>
    `);
    });
}
