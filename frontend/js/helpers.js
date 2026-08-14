// helpers.js — small helpers used across pages. These don't talk to the
// network or localStorage at all — see api.js and auth.js for that.

const CATEGORY_LABELS = {
    textbooks: 'Textbooks', electronics: 'Electronics', furniture: 'Furniture',
    bikes: 'Bikes & transport', clothing: 'Clothing', other: 'Other'
};

// Escapes text before it's inserted into the DOM — used both for element
// text and for text going inside an HTML attribute (like data-title="...").
// Escaping quotes even in plain text is harmless, so this one function is
// safe everywhere, with nothing to get wrong by picking the "wrong" helper
// for a given spot.
function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : String(str);
    return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
