'''
    Utility classes and functions.

    Copyright 2009-2014 GoodCrypto
    Last modified: 2014-03-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''


import os, urllib
from datetime import datetime

from django.conf import settings
#from django.http import HttpResponse
from django.utils.encoding import force_unicode

from syr.log import get_log


log = get_log()



def to_unicode(s):
    ''' Converts string to unicode. If can't convert, returns u''.

        See
            django.utils.encoding.smart_str() and smart_unicode() for an better implementation.
            http://www.saltycrane.com/blog/2008/11/python-unicodeencodeerror-ascii-codec-cant-encode-character/
            http://wiki.python.org/moin/UnicodeEncodeError'''

    try:
        unicode_s = force_unicode(s)
        str(unicode_s)

    except Exception, e:

        try:
            unicode_s = force_unicode(s, encoding=syr.prefered_encoding)
            str(unicode_s)

        except:
            try:
                # \u0000 through \u00FF, inclusive
                unicode_s = force_unicode(s, encoding='iso-8859-1')
                str(unicode_s)

            except Exception, e:
                log('Unable to convert %r to unicode: %r' % (s, e))
                unicode_s = u''

    return unicode_s
    

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

    return (django_error_1 in html) and (django_error_2 in html)

    
"""
def transclude(url):
    ''' Returns the response from the url.

        Any relative links to another web site in the response won't work.

        An advantage of using urlretrieve() is that we get a web server log
        entry we can analyze. Other approaches such as directly reading a file
        or processing the page in django wouldn't touch the log.'''

    (filename, headers) = urllib.urlretrieve(url)
    file = open(filename)
    response = file.read()
    file.close()
    return HttpResponse(response)
"""
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()


