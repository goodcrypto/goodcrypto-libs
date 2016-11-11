'''
    Html utilities

    Copyright 2010-2016 GoodCrypto
    Last modified: 2016-04-25

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import re

from django.utils.encoding import force_text
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
    value = force_text(value)
    return value

if IS_PY2:
    strip_whitespace_in_html = allow_lazy(strip_whitespace_in_html, unicode)
else:
    strip_whitespace_in_html = allow_lazy(strip_whitespace_in_html, str)
