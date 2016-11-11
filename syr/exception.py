'''
    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-08-01

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import re, time
from traceback import format_exc

from syr.log import get_log_path, _debug

pathname = get_log_path()

def record_exception(message=None):
    '''
        A central log for exceptions that logs regardless of the user's preferences because
        these are serious errors. This log is for exceptions of all kinds, not just python Exceptions.

        >>> from os.path import exists, join
        >>> from syr.log import BASE_LOG_DIR
        >>> from syr.user import whoami
        >>> record_exception('test')
        >>> exists(join(BASE_LOG_DIR, whoami(), 'syr.exception.log'))
        True
        >>> record_exception()
        >>> exists(join(BASE_LOG_DIR, whoami(), 'syr.exception.log'))
        True
    '''
    global pathname

    try:
        if pathname is None:
            pathname = '/tmp/syr_exceptions'

        _debug(format_exc(), force=True, filename=pathname)
        if message is not None:
            _debug(message, force=True, filename=pathname)
    except:
        _debug(format_exc(), force=True)

