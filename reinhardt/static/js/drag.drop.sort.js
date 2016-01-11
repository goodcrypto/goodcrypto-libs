/* Adapted from http://djangosnippets.org/snippets/1053/ Original author: Simon Willison */
/* The model for the 'inline' must include a field that is required and matches the field */
/* referenced in the "if" statement below plus an order field must defined that is */
/* optional. Both of these fields must be included in the fieldsets, but the */
/* order field will only appear if the user does not have javascript enabled. */
jQuery(function($) {
    $('div.inline-group').sortable({
        /*containment: 'parent',
        zindex: 10, */
        items: 'div.inline-related',
        handle: 'h3:first',
        update: function() {
            $(this).find('div.inline-related').each(function(i) {
                if ($(this).find('input[id$=url]').val()) {
                    $(this).find('input[id$=order]').val(i+1);
                }
            });
        }
    });
    $('div.inline-related h3').css('cursor', 'move');
    $('div.inline-related').find('input[id$=order]').parent('div').hide();
});


