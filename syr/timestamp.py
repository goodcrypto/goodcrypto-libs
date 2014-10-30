#!/usr/bin/env python
'''
    Copyright 2013 Good Crypto
    Last modified: 2013-10-27

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
import time
from datetime import datetime
from django.utils.timezone import utc


class Timestamp(object):
    '''
        Timestamp provides a standardized datetime stamp.
        The string in the form #DateFormatSpec.
        The standard timezone is UT/UTC.
    '''

    DateFormatSpec = "yyyy-MM-dd HH:mm:ss.SSS"

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

        return date_time.isoformat(' ')


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

        return date_time.isoformat(' ')


