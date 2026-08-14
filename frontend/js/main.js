// main.js — per-page startup. Talks to the backend via api.js instead of
// localStorage now; page structure and behaviour otherwise match the
// original front-end demo.

$(function () {
    applyRoleToPage();

    $('.search-bar').on('submit', function (e) {
        e.preventDefault();
        applyFilters();
    });

    // ---------- Homepage / listing grid ----------
    if ($('#listing-grid').length) {
        const user = getCurrentUser();
        const favoritesPromise = user.role !== 'Visitor'
            ? apiGetFavoriteListings().catch(function () { return []; })
            : Promise.resolve([]);

        Promise.all([apiGetListings(), favoritesPromise]).then(function (results) {
            const listings = results[0];
            const favoriteIds = new Set(results[1].map(function (l) { return l.id; }));
            renderListingGrid(listings, favoriteIds);
        });

        $('#search-input').on('input', applyFilters);
        $('.filter-pill').on('click', function () {
            $('.filter-pill').removeClass('active');
            $(this).addClass('active');
            applyFilters();
        });
        $(document).on('click', '.favorite-btn', function (e) {
            e.preventDefault();
            if (getCurrentUser().role === 'Visitor') {
                alert('Log in as a Member or Moderator to save favorites.');
                return;
            }
            const $btn = $(this);
            const id = $btn.closest('.listing-card').attr('data-id');
            toggleFavorite(id).then(function (result) {
                $btn.toggleClass('active', result.favorited);
            });
        });
    }

    // ---------- Listing detail page ----------
    if ($('#listing-detail').length) {
        const id = new URLSearchParams(window.location.search).get('id');
        let currentListing = null;

        apiGetListing(id).then(function (listing) {
            currentListing = listing;
            renderListingDetail(listing);
            if (getCurrentUser().name) $('#inquiry-name').val(getCurrentUser().name);
        }).catch(function () {
            renderListingDetail(null);
        });

        $('#inquiry-form').on('submit', function (e) {
            e.preventDefault();
            if (!validateForm($(this), ['name', 'message'])) return;
            const sellerName = currentListing ? currentListing.sellerName : '';
            const listingTitle = currentListing ? currentListing.title : 'a listing';
            createInquiry(id, listingTitle, sellerName, $('#inquiry-name').val(), $('#inquiry-message').val())
                .then(function () {
                    $('#inquiry-form').html('<p class="subtitle">Message sent — the seller will see it under Messages on their dashboard.</p>');
                })
                .catch(function (err) { alert(err.message || 'Could not send the message.'); });
        });

        $('#report-form').on('submit', function (e) {
            e.preventDefault();
            const reason = $('#report-reason').val();
            if (!reason) return;
            reportListing(id, reason).then(function () {
                $('#report-form').addClass('hidden');
                $('#report-confirm').removeClass('hidden');
            });
        });
    }

    // ---------- Dashboard ----------
    if ($('#my-listings').length && getCurrentUser().role === 'Visitor') {
        window.location.href = 'login.html';
    } else if ($('#my-listings').length) {
        $('.tab-button').on('click', function () {
            const tab = $(this).data('tab');
            $('.tab-button').removeClass('active');
            $(this).addClass('active');
            $('.tab-panel').removeClass('active');
            $('#' + tab).addClass('active');
        });

        const role = getCurrentUser().role;
        const moderationPromise = role === 'Moderator' ? apiGetModerationQueue() : Promise.resolve([]);

        Promise.all([
            apiGetMyListings(),
            moderationPromise,
            apiGetFavoriteListings(),
            apiGetMyInquiries()
        ]).then(function (results) {
            const mine = results[0], queue = results[1], favs = results[2], inquiries = results[3];
            renderMyListings(mine, inquiries);
            renderModeratorQueue(queue);
            renderFavorites(favs);
            renderMessages(inquiries);
            applyRoleToDashboard();
        });

        $(document).on('click', '.btn-edit', function () {
            const id = $(this).closest('.dashboard-row').attr('data-id');
            window.location.href = 'create-listing.html?edit=' + encodeURIComponent(id);
        });

        $(document).on('click', '.btn-delete', function () {
            const id = $(this).closest('.dashboard-row').attr('data-id');
            if (!confirm('Delete this listing?')) return;
            removeListing(id)
                .then(function () { return Promise.all([apiGetMyListings(), apiGetMyInquiries()]); })
                .then(function (results) { renderMyListings(results[0], results[1]); });
        });

        $(document).on('click', '.btn-remove', function () {
            const id = $(this).closest('.dashboard-row').attr('data-id');
            if (!confirm('Remove this listing from CampusSwap?')) return;
            removeListing(id)
                .then(function () { return apiGetModerationQueue(); })
                .then(function (queue) { renderModeratorQueue(queue); });
        });

        $(document).on('click', '.btn-dismiss', function () {
            const id = $(this).closest('.dashboard-row').attr('data-id');
            dismissInquiry(id)
                .then(function () { return Promise.all([apiGetMyInquiries(), apiGetMyListings()]); })
                .then(function (results) {
                    renderMessages(results[0]);
                    renderMyListings(results[1], results[0]);
                });
        });
    }

    // ---------- Create / edit listing ----------
    if ($('#listing-form').length) {
        if (getCurrentUser().role !== 'Member') window.location.href = 'index.html';

        let selectedFile = null;
        const editId = new URLSearchParams(window.location.search).get('edit');

        if (editId) {
            apiGetListing(editId).then(function (listing) { prefillListingForm(listing); });
        }

        $('#image-upload').on('change', function () {
            const file = this.files[0];
            if (!file) return;
            if (file.size > 1000000) {
                alert('Please choose an image under 1MB.');
                this.value = '';
                return;
            }
            selectedFile = file;
            const reader = new FileReader();
            reader.onload = function (e) {
                $('#image-preview').attr('src', e.target.result).removeClass('hidden');
                $('#upload-label').text(file.name);
            };
            reader.readAsDataURL(file);
        });

        $('#listing-form').on('submit', function (e) {
            e.preventDefault();
            if (!validateForm($(this), ['title', 'category', 'price', 'condition', 'description'])) return;

            const formData = new FormData();
            formData.append('title', $('#title').val());
            formData.append('category', $('#category').val());
            formData.append('price', $('#price').val());
            formData.append('condition', $('#condition').val());
            formData.append('description', $('#description').val());
            if (selectedFile) formData.append('image', selectedFile);

            const request = editId ? updateListing(editId, formData) : createListing(formData);
            request.then(function () {
                window.location.href = 'dashboard.html';
            }).catch(function (err) {
                alert(err.message || 'Could not save the listing.');
            });
        });
    }

    // ---------- Login ----------
    if ($('#login-form').length) {
        $('#login-form').on('submit', function (e) {
            e.preventDefault();
            const name = $('#login-name').val().trim();
            if (!name) return;
            loginUser(name, $('#login-role').val()).then(function () {
                window.location.href = 'index.html';
            }).catch(function (err) {
                alert(err.message || 'Could not log in.');
            });
        });
        $('#continue-visitor').on('click', function (e) { e.preventDefault(); logOut(); window.location.href = 'index.html'; });
    }

    $('#nav-auth').on('click', function (e) {
        if ($(this).text() === 'Log out') { e.preventDefault(); logOut(); window.location.href = 'index.html'; }
    });
});
