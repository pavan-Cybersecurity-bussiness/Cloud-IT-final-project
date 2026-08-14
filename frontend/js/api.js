// api.js — the only file that talks to the network. Every call goes
// through the API gateway at API_BASE; the gateway fans each request out
// to the auth, listings, or messaging microservice behind it.
// Every function here returns a Promise — see auth.js for getAuthToken().

function authHeaders() {
    const token = getAuthToken();
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

// Wraps fetch(): parses the JSON body and rejects (with the parsed error,
// or a generic fallback) on any non-2xx response, so callers can just
// chain .then(...).catch(showError) without checking res.ok everywhere.
function apiFetch(path, options) {
    return fetch(API_BASE + path, options).then(function (res) {
        const contentType = res.headers.get('content-type') || '';
        const bodyPromise = contentType.includes('application/json') ? res.json() : res.text();
        return bodyPromise.then(function (body) {
            if (!res.ok) {
                const message = (body && body.error) || 'Something went wrong. Please try again.';
                return Promise.reject({ status: res.status, body: body, message: message });
            }
            return body;
        });
    });
}

function apiLogin(name, role) {
    return apiFetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, role: role })
    });
}

function apiGetListings() {
    return apiFetch('/listings');
}

function apiGetListing(id) {
    return apiFetch('/listings/' + encodeURIComponent(id));
}

function apiGetMyListings() {
    return apiFetch('/listings/mine', { headers: authHeaders() });
}

function apiGetModerationQueue() {
    return apiFetch('/listings/moderation-queue', { headers: authHeaders() });
}

function apiGetFavoriteListings() {
    return apiFetch('/listings/favorites', { headers: authHeaders() });
}

function apiCreateListing(formData) {
    return apiFetch('/listings', { method: 'POST', headers: authHeaders(), body: formData });
}

function apiUpdateListing(id, formData) {
    return apiFetch('/listings/' + encodeURIComponent(id), { method: 'PUT', headers: authHeaders(), body: formData });
}

function apiDeleteListing(id) {
    return apiFetch('/listings/' + encodeURIComponent(id), { method: 'DELETE', headers: authHeaders() });
}

function apiReportListing(id, reason) {
    return apiFetch('/listings/' + encodeURIComponent(id) + '/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
    });
}

function apiToggleFavorite(id) {
    return apiFetch('/listings/' + encodeURIComponent(id) + '/favorite', { method: 'POST', headers: authHeaders() });
}

function apiCreateInquiry(payload) {
    return apiFetch('/inquiries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
}

function apiGetMyInquiries() {
    return apiFetch('/inquiries/mine', { headers: authHeaders() });
}

function apiDismissInquiry(id) {
    return apiFetch('/inquiries/' + encodeURIComponent(id), { method: 'DELETE', headers: authHeaders() });
}
