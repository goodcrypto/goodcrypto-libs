'''
    Session and cookies.

    When we use Django authentication it handles this for us.

    Copyright 2008-2016 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

from traceback import format_exc

from syr.log import get_log

log = get_log()

def gotCookie(request):
    '''Check that we got a cookie from the user.

    If not, set a test cookie.'''

    try:
        keys = request.session.keys()
        if keys:
            gotIt = True
            # for key in keys:
            #     log('session[%s]: %s' % (key, request.session[key]))
            # log('got session, so got cookie')

        else:
            gotIt = gotTestCookie(request)
            if not gotIt:

                request.session.set_test_cookie()
                # log('tried to set test cookie')

    except:
        log(format_exc())
        gotIt = False

    return gotIt

def gotTestCookie(request):
    '''Check that we got the test cookie from the user.'''
    gotIt = request.session.test_cookie_worked()
    if gotIt:
        request.session.delete_test_cookie()
        # log('got test cookie')
    return gotIt

def setUpCookies(request):
    '''Make sure we either have a cookie or send a test cookie.

    The function gotCookie does what we need, if we just ignore the result.'''
    gotCookie(request)

def clearSession(request, clearAuth=True):
    '''Clear the session.

    If clearAuth is True, the default, all settings are cleared.
    If clearAuth is False, the Django authorization settings are not cleared.

    This code depends on the Django authorization keys having a specific prefix, which may change.'''
    AuthPrefix = '_auth_user_'
    keys = request.session.keys()
    if clearAuth:
        for key in keys:
            del request.session[key]
        log('cleared session')
    else:
        for key in keys:
            if not key.startswith(AuthPrefix):
                del request.session[key]
        log('cleared session except for authorization')
