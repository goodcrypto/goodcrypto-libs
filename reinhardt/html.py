'''
    Html utilities
   
    Copyright 2010-2013 GoodCrypto
    Last modified: 2013-11-13

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import re

from django.utils.encoding import force_unicode
from django.utils.functional import allow_lazy

def strip_whitespace_in_html(value, mintext=False):
    ''' Returns the given HTML with minimum white space.
    
        To also change white space sequences in text between tags 
        to a single space, set mintext to True. This is dangerous 
        with embedded javascript, <pre>, etc.
        
        >>> strip_whitespace_in_html(' <a>   <b> test test2 </b></a>')
            u'<a><b> test test2 </b></a>'
    '''
        
    value = value.strip()
    # no spaces around tags
    value = re.sub(r'>[\s\n\t]+<', '><', value)
    if mintext:
        # other space sequences replaced by single space
        value = re.sub(r'\s+', ' ', value)
    value = force_unicode(value)
    return value
strip_whitespace_in_html = allow_lazy(strip_whitespace_in_html, unicode)
 