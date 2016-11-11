'''
    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-06-05

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2
if not IS_PY2:
    raise Exception('Deprecated. Use the datetime module.')

import time
from datetime import datetime
from django.utils.timezone import utc


class Timestamp(object):
    '''
        Timestamp provides a standardized datetime stamp.
        The string in the form #DateFormatSpec.
        The standard timezone is UT/UTC.
    '''

    FormatSpec = "yyyy-MM-dd HH:mm:ss.SSS"

    @staticmethod
    def get_timestamp():
        '''
            Gets the current datetime stamp.

            >>> t = get_timestamp()
            >>> print(t)
        '''

        return Timestamp.to_timestamp(datetime.utcnow().replace(tzinfo=utc))


    @staticmethod
    def to_timestamp(date_time=None, tz=None):
        '''
            Converts a date to the standard timestamp format.
            If date_time is None, then gets the current UTC time.
            If date_time is milliseconds since the epoch, converts to datetime.

            @param date datetime
            @param tz  timezone
            @return    timestamp
        '''

        if date_time is None:
            date_time = datetime.utcnow().replace(tzinfo=utc)

        elif isinstance(date_time, float):
            date_time = time.gmtime(date_time)

        return date_time.isoformat(str(' '))


    @staticmethod
    def to_local_timestamp(date_time=None):
        '''
            Converts a date to the standard timestamp format.
            If date_time is None, then gets the current local time.
            If date_time is milliseconds since the epoch, converts to datetime.

            @param date datetime
            @return    timestamp
        '''

        if date_time is None:
            date_time = datetime.now()

        elif isinstance(date_time, float):
            date_time = time.gmtime(date_time)

        return date_time.isoformat(str(' '))


