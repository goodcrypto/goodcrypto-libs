'''
    Utility classes and functions.

    Copyright 2009-2016 GoodCrypto
    Last modified: 2016-05-18

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import os
from datetime import datetime
from traceback import format_exc

from django.conf import settings
from django.utils.encoding import force_text, smart_text, DjangoUnicodeDecodeError

from syr.log import get_log


log = get_log()



def to_unicode(s):
    ''' Converts string to unicode. If can't convert, returns u''.

        See
            django.utils.encoding.smart_str() and smart_unicode() for an better implementation.
            http://www.saltycrane.com/blog/2008/11/python-unicodeencodeerror-ascii-codec-cant-encode-character/
            http://wiki.python.org/moin/UnicodeEncodeError'''

    try:
        unicode_s = force_text(s)
        str(unicode_s)

    except Exception as e:

        try:
            unicode_s = force_text(s, encoding=syr.prefered_encoding)

        except:
            try:
                # \u0000 through \u00FF, inclusive
                unicode_s = force_text(s, encoding='iso-8859-1')

            except Exception as e:
                log('Unable to convert %r to unicode: %r' % (s, e))
                unicode_s = force_text('')

    return unicode_s

def is_secure_connection(request):
    ''' Check if connection is secure. '''

    secure = False
    try:
        if 'HTTP_X_SCHEME' in request.META:
            secure = 'https' == request.META['HTTP_X_SCHEME']
        elif 'wsgi.url_scheme' in request.META:
            secure = 'https' == request.META['wsgi.url_scheme']
    except:
        log(format_exc())

    return secure

def django_error_page_response(request, error=None):
    ''' Return a response with Django's error page.

        If settings.DEBUG is True, Django automatically shows a useful
        error page for exceptions in views. But sometimes an exception
        isn't propogated out of the view, such as when the exception
        occurs in a separate thread. This shows the Django error page
        for any exception.

        If error is not present or is None, returns an error page for the
        last exception.

        Example:
            error = None
            ...
            # in separate thread
            error = sys.exc_info()
            ...
            # in parent thread
            show_django_error_page(error)
        '''

    from django.views.debug import technical_500_response
    # error should be sys.exc_info() from an earlier except block
    if not error:
        error = sys.exc_info()
    exc_type, exc_value, tb = error
    response = technical_500_response(request, exc_type, exc_value, tb)


def is_django_error_page(html):
    ''' Returns True if this html contains a Django error page,
        else returns False.'''

    django_error_1 = "You're seeing this error because you have"
    django_error_2 = 'display a standard 500 page'

    try:
        smart_html = smart_text(html)
    except DjangoUnicodeDecodeError:
        # definitely not a django html error page
        result = False
    else:
        result = (django_error_1 in smart_html) and (django_error_2 in smart_html)

    return result


if __name__ == "__main__":
    import doctest
    doctest.testmod()


