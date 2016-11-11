'''
    Log Django debug pages.

    Copyright 2010-2016 GoodCrypto
    Last modified: 2016-05-27

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import os
from tempfile import NamedTemporaryFile

from reinhardt.utils import is_django_error_page
from syr.log import get_log

log = get_log()

class DebugMiddleware(object):
    ''' Write to debugging log.

        Logs Django debug pages and says it's an error. '''

    def process_response(self, request, response):

        def logit(why):
            log(why)
            log('response: %r' % response)
            log('request: %r' % request)

        if is_django_error_page(response.content):
            with NamedTemporaryFile(
                prefix='django.debug.page.', suffix='.html',
                delete=False) as htmlfile:
                htmlfile.write(response.content)
            os.chmod(htmlfile.name, 0o644)
            log('django app error: django debug page at %s' % htmlfile.name)
        elif response.status_code >= 400:
            logit('http error %d' % response.status_code)

        return response
