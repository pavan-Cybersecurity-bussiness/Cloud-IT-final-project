// auth.js — session cache (token + who you are) plus role-based show/hide.
//
// The account itself now lives in the Auth service's database (see
// backend/auth-service) — this file only caches the current session's JWT
// and user info in localStorage, the same way most real single-page apps
// keep a client-side session alive between page loads. That's a narrower
// job than the old auth.js had, which used localStorage as the actual
// source of truth for who you are.

const SESSION_KEY = 'campusswap_session';

function getCurrentUser() {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : { name: '', role: 'Visitor', token: null };
}

function getAuthToken() {
    return getCurrentUser().token;
}

// Logs in against the Auth service and caches the session it returns.
// Same relaxed semantics as the original front-end demo: no password,
// this just tells the backend who you're saying you are for this session.
function loginUser(name, role) {
    return apiLogin(name, role).then(function (data) {
        localStorage.setItem(SESSION_KEY, JSON.stringify({
            name: data.user.name, role: data.user.role, token: data.token
        }));
        return data.user;
    });
}

function logOut() {
    localStorage.removeItem(SESSION_KEY);
}

// Runs on every page: updates header + shows/hides nav links by role.
function applyRoleToPage() {
    const user = getCurrentUser();
    const role = user.role;

    $('.avatar').text(role === 'Visitor' ? '?' : user.name.slice(0, 2).toUpperCase());
    $('.greeting').text(role === 'Visitor' ? 'Browsing as a visitor' : 'Hi, ' + user.name);

    $('#nav-post-item').toggle(role === 'Member');           // only Members create listings
    $('#nav-my-listings').toggle(role !== 'Visitor');         // Member or Moderator

    if (role === 'Visitor') {
        $('#nav-auth').text('Log in').attr('href', 'login.html');
    } else {
        $('#nav-auth').text('Log out').attr('href', '#');
    }
}

// Dashboard-only: forces the tab that matches the role, hides the other.
function applyRoleToDashboard() {
    const role = getCurrentUser().role;
    if (role === 'Moderator') {
        $('.tab-button[data-tab="my-listings"]').hide();
        $('.tab-button[data-tab="moderator-queue"]').trigger('click');
    } else {
        $('.tab-button[data-tab="moderator-queue"]').hide();
        $('.tab-button[data-tab="my-listings"]').trigger('click');
    }
}
