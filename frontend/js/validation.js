const VALIDATORS = {
    title: function (v) { return v.trim().length >= 3 ? null : 'Title must be at least 3 characters.'; },
    category: function (v) { return v ? null : 'Choose a category.'; },
    price: function (v) {
        const n = Number(v);
        return (v !== '' && !isNaN(n) && n >= 0) ? null : 'Enter a valid, non-negative price.';
    },
    condition: function (v) { return v ? null : 'Choose a condition.'; },
    description: function (v) { return v.trim().length >= 10 ? null : 'Add at least a short description.'; },
    name: function (v) { return v.trim().length >= 2 ? null : 'Enter a name.'; },
    message: function (v) { return v.trim().length >= 5 ? null : 'Write a short message before sending.'; }
};

function validateForm($form, fields) {
    let isValid = true;
    fields.forEach(function (field) {
        const $input = $form.find('[name="' + field + '"]');
        const $group = $input.closest('.form-group');
        const error = VALIDATORS[field]($input.val());
        $group.toggleClass('has-error', !!error);
        if (error) { $group.find('.error-text').text(error); isValid = false; }
    });
    return isValid;
}