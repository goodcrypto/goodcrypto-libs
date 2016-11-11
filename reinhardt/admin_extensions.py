'''
    Add a couple of formsets.

    Copyright 2012-2016 GoodCrypto
    Last modified: 2016-04-23

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import os

from django.contrib import admin
from django.contrib.admin.options import get_ul_class
from django.core import serializers
from django.forms import ValidationError
from django.forms.models import BaseInlineFormSet
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from syr.log import get_log


log = get_log()


class CustomModelAdmin(admin.ModelAdmin):
    '''Custom model admin.'''

    save_on_top = True

    def get_form(self, request, obj=None, **kwargs):
        '''Restrict all foreign keys to the access_group and hide the access_group for staff.'''

        if request.user.is_superuser:
            self.fieldsets = self.superuser_fieldsets
        else:
            self.fieldsets = self.staff_fieldsets

        return super(CustomModelAdmin, self).get_form(request, obj, **kwargs)


    class Media:
        css = {
            'all': ('/static/css/admin.css',)
        }
        js = ('/static/js/reinhardt.custom.js',)


    def get_list_display(self, request):
        if request.user.is_superuser:
            try:
                self.list_display = self.superuser_list_display
            except:
                pass
        else:
            try:
                self.list_display = self.staff_list_display
            except:
                pass
        return self.list_display


class CustomStackedInline(admin.StackedInline):
    '''Custom inline form.'''

    extra = 0

    def get_fieldsets(self, request, obj=None):
        '''Set the fieldsets depending on the user.'''
        if request.user.is_superuser:
            self.fieldsets = self.superuser_fieldsets
        else:
            self.fieldsets = self.staff_fieldsets

        return self.fieldsets


class ShowOneFormSet(BaseInlineFormSet):
    '''
        Show at least one form in the formset.
    '''

    def total_form_count(self):
        """Returns the total number of forms in this FormSet."""

        total_forms = get_total_form_count(
            self, super(ShowOneFormSet, self).total_form_count(), 1)

        return total_forms


class RequireOneFormSet(ShowOneFormSet):
    '''
        Show and require at least one form in the formset to be completed.
    '''

    def clean(self):

        cleaned_data = super(RequireOneFormSet, self).clean()
        if cleaned_data:
            for data in cleaned_data:
                log('cleaned_data: %r' % data)
        for error in self.errors:
            if error:
                log('errors %r' % error)
                return

        verify_min_formsets_ok(self, 1)

        return cleaned_data


class ShowTwoFormSet(BaseInlineFormSet):
    '''
        Show at least two forms in the formset.
    '''

    def total_form_count(self):
        """Returns the total number of forms in this FormSet."""

        total_forms = get_total_form_count(
            self, super(ShowTwoFormSet, self).total_form_count(), 2)

        return total_forms


class RequireTwoFormSets(ShowTwoFormSet):
    '''
        Show and require at least two forms in the formset to be completed.
    '''

    def clean(self):

        cleaned_data = super(RequireTwoFormSets, self).clean()
        for error in self.errors:
            if error:
                log('errors %r' % error)
                return

        verify_min_formsets_ok(self, 2)

        return cleaned_data


def get_total_form_count(formset, total_forms, minimum):
    """Returns the total number of forms in this FormSet."""

    if not formset.is_bound and total_forms < minimum:
        formset.extra = total_forms - minimum
        total_forms = minimum
    return total_forms


def verify_min_formsets_ok(formset, minimum):
    '''Verify the mininum form sets have been completed.

       Adapted from http://code.google.com/p/wadofstuff/source/browse/trunk/python/forms/wadofstuff/django/forms/forms.py
    '''
    completed = 0

    try:
        deleted_forms = formset.deleted_forms
        total_forms = formset.total_form_count()
        log('total_forms: %r' % total_forms)
        for i in range(0, total_forms):
            form = formset.forms[i]
            if form not in deleted_forms:
                if form.cleaned_data:
                    for cleaned_data in form.cleaned_data:
                        log('cleaned_data: %r' % cleaned_data)
                        # form has data
                        if cleaned_data and not len(cleaned_data) <= 0:
                            completed += 1
    except:
        log(format_exc())
        completed = 0

    try:
        if formset:
            name = formset.model._meta.verbose_name.lower()
        else:
            name = 'inline form'
    except:
        name = 'inline form'

    if completed < minimum:
        error_message = 'Requires at least {} {}.'.format(minimum, name)
        log(error_message)

        raise ValidationError(error_message)


def get_formfield_for_foreignkey_kwargs(self, db_field, **kwargs):
    ''' Returns kwargs with any special 'widget' and 'empty_label' values added..

        Copied from django.contrib.admin.options.formfield_for_foreignkey()

        Similar functions could be built for other formfield_for_XYZ().
    '''

    db = kwargs.get('using')
    if db_field.name in self.raw_id_fields:
        kwargs['widget'] = admin.widgets.ForeignKeyRawIdWidget(db_field.rel, using=db)
    elif db_field.name in self.radio_fields:
        kwargs['widget'] = admin.widgets.AdminRadioSelect(attrs={
            'class': get_ul_class(self.radio_fields[db_field.name]),
        })
        kwargs['empty_label'] = db_field.blank and _('None') or None

    return kwargs

def export_as_json(modeladmin, request, queryset):
    ''' Django admin action to export selected items as json.

        From "Admin actions" in Django documentation. '''

    response = HttpResponse(mimetype="text/javascript")
    serializers.serialize("json", queryset, stream=response, indent=4)
    return response
export_as_json.short_description = _('Export as JSON')

""" untested, and not for django admin
def save(request, models):
    ''' Save data to fixtures.

        We don't save the Access table because it takes too long,
        contains strange characters, and we can recreate it from the logs.'''

    fixtures_subdir = 'fixtures'
    format = 'json'

    fixture_dir = os.path.join(os.path.dirname(__file__), fixtures_subdir)
    if not os.path.exists(fixture_dir):
        os.mkdir(fixture_dir)

    for model in models:
        filename = os.path.join(fixture_dir,
            '%s.%s' % (model._meta.module_name, format))
        file = open(filename, 'w')
        try:
            serializers.serialize(
                format, model.objects.all(), stream=file, ensure_ascii=False, indent=4)
        finally:
            file.close()

    return HttpResponse('Saved models: %s' % ', '.join(models))
"""
