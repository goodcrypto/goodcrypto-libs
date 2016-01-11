'''
    Times.
    
    Utilties for times. Great for working with time series.
    
    Todo: Provide a way to make UTC or other timezone the default.
   
    Copyright 2009-2015 GoodCrypto
    Last modified: 2015-01-27

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import calendar, re, time
from datetime import date, datetime, timedelta
try:
    from django.utils.timezone import utc
except:
    pass

from syr.format import s_if_plural

    
seconds_in_minute = 60
seconds_in_hour = 60 * seconds_in_minute
seconds_in_day = 24 * seconds_in_hour
microseconds_in_second = 1000000
    
# we don't define one_month, one_year, etc. 
# because the exact definition varies from app to app
one_week = timedelta(days=7)
one_day = timedelta(days=1)
one_hour = timedelta(hours=1)
one_minute = timedelta(minutes=1)
one_second = timedelta(seconds=1)
one_millisecond = timedelta(milliseconds=1)
one_microsecond = timedelta(microseconds=1)
no_time = timedelta(0)

far_past = datetime.min
far_future = datetime.max
# indicate all dates and times
anytime = far_future - one_microsecond

# some constants are defined after we define functions they need

def now(utc=False):
    ''' Get the current date/time.  
    
        If utc=True, return UTC date/time in a form that conforms with django.
        
        Returns a datetime object.
    '''

    if utc:
        try:
            dt = datetime.utcnow().replace(tzinfo=utc)
        except:
            dt = datetime.utcnow()
    else:
        dt = datetime.now()
    return dt
    
def get_short_now(utc=False):
    '''Get datetime up to the minute, not the second, milisecond. 
    
        >>> get_short_now().second == 0 and get_short_now().microsecond == 0
        True
        >>> get_short_now(utc=True).second == 0 and get_short_now(utc=True).microsecond == 0
        True
    '''

    time_now = now(utc=utc)
    return datetime(time_now.year, time_now.month, time_now.day, time_now.hour, time_now.minute)
    
    
def timestamp(microseconds=True):
    ''' Return timestamp in a standard format. Time zone is UTC.
        
        >>> re.match('^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d*$', timestamp()) is not None
        True
        >>> re.match('^^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', timestamp(microseconds=False)) is not None
        True
    '''

    seconds_now = time.time()
    formated_time = time.strftime(
        '%Y-%m-%d %H:%M:%S', time.gmtime(seconds_now))
    if microseconds:
        fractional_second = seconds_now % 1
        formated_microseconds = ('%06d' % int(fractional_second * 1000000))[:6]
        formated_time = '%s.%s' % (formated_time, formated_microseconds)
    return formated_time


def format_date(date=None):
    ''' Return the date in a standard format.
    
        If date is not specified or the date is None, formats today's date. 
        Time zone is UTC.
        
        >>> format_date((2012, 7, 6, 17, 57, 12, 4, 188, 0))
        '2012-07-06'
        >>> re.match('^^\d{4}-\d{2}-\d{2}', format_date()) is not None
        True
    '''
     
    if not date:
        date = time.gmtime()
    return time.strftime('%Y-%m-%d', date)

def timedelta_to_human_readable(td, verbose=True):
    ''' Formats a timedelta in a human readable form.
    
        If total time is less than a second then shows milliseconds 
        instead of microseconds, else rounds to the nearest second.
    
        >>> timedelta_to_human_readable(timedelta(days=1, seconds=123, minutes=4, hours=26))
        '2 days, 2 hours, 6 minutes, 3 seconds'
        >>> timedelta_to_human_readable(timedelta(seconds=123))
        '2 minutes, 3 seconds'
        >>> timedelta_to_human_readable(timedelta(seconds=65))
        '1 minute, 5 seconds'
        >>> timedelta_to_human_readable(timedelta(milliseconds=85))
        '85 ms'
        >>> timedelta_to_human_readable(timedelta(days=1, seconds=123, minutes=4, hours=26), verbose=False)
        '2days, 2hrs, 6mins, 3secs'
        >>> timedelta_to_human_readable(timedelta(seconds=123), verbose=False)
        '2mins, 3secs'
        >>> timedelta_to_human_readable(timedelta(seconds=65), verbose=False)
        '1min, 5secs'
        >>> timedelta_to_human_readable(timedelta(milliseconds=85), verbose=False)
        '85 ms'
    '''
    
    tdString = ''

    if td.days or td.seconds:
            
        # days
        if td.days:
            tdString = str(td.days) + ' day' + s_if_plural(td.days)
            
        # round seconds
        seconds = td.seconds
        if (td.microseconds * 2) >= td.max.microseconds:
            seconds = seconds + 1
    
        # hours
        hours = seconds // seconds_in_hour
        if hours:
            if len(tdString) > 0:
                tdString = tdString + ', '
            tdString = tdString + str(hours) + ' hour' + s_if_plural(hours)
    
        # minutes
        secondsLeft = seconds - (hours * seconds_in_hour)
        if secondsLeft:
            minutes = secondsLeft // seconds_in_minute
            if minutes:
                if len(tdString) > 0:
                    tdString = tdString + ', '
                tdString = tdString + str(minutes) + ' minute' + s_if_plural(minutes)
                secondsLeft = secondsLeft - (minutes * seconds_in_minute)
    
        # seconds
        if secondsLeft:
            if len(tdString) > 0:
                tdString = tdString + ', '
            tdString = tdString + str(secondsLeft) + ' second' + s_if_plural(secondsLeft)

    else:
        # !!!!! python 3
        milliseconds = (td.microseconds + 1) / 1000
        tdString = '%d ms' % milliseconds

    if not verbose:
        m = re.match('.*( day)', tdString)
        if m:
            tdString = tdString.replace(m.group(1), 'day')
            
        m = re.match('.*( hour)', tdString)
        if m:
            tdString = tdString.replace(m.group(1), 'hr')
            
        m = re.match('.*( second)', tdString)
        if m:
            tdString = tdString.replace(m.group(1), 'sec')
            
        m = re.match('.*( minute)', tdString)
        if m:
            tdString = tdString.replace(m.group(1), 'min')

    return tdString


def get_short_date_time(date_time):
    '''Format the date-time without seconds.
    
        >>> get_short_date_time(datetime(2012, 06, 01, 12, 30, 00))
        '2012-06-01 12:30'
        >>> get_short_date_time(datetime(2012, 06, 01, 12, 30, 41))
        '2012-06-01 12:30'
        >>> get_short_date_time(datetime(2012, 06, 01, 12, 30, 00, 00))
        '2012-06-01 12:30'
        >>> get_short_date_time(None)
        ''
    '''
    
    if date_time:
        new_date_time = date_time.isoformat(' ')
        try:
            m = re.match('.*?(\d+\:\d+\:\d+).*', new_date_time)
            if m:
                current_time = m.group(1)
                index = current_time.rfind(':')
                new_date_time = new_date_time.replace(m.group(1), current_time[:index])
        except:
            pass
            
    else:
        new_date_time = ''
        
    return new_date_time    

def datetime_to_date(dt):
    ''' Converts a datetime to a date. If dt is a date, returns a copy.
    
        >>> datetime_to_date(datetime(2012, 06, 01, 12, 30, 00))
        datetime.date(2012, 6, 1)
        >>> datetime_to_date(datetime(2012, 06, 01, 12, 30, 00, 00))
        datetime.date(2012, 6, 1)
    '''
    return date(dt.year, dt.month, dt.day)

def date_to_datetime(d):
    ''' Converts a date or datetime to a datetime at the beginning of the day.
    
        >>> date_to_datetime(datetime(2012, 06, 01, 1, 39))
        datetime.datetime(2012, 6, 1, 0, 0)
        >>> date_to_datetime(date(2012, 06, 01))
        datetime.datetime(2012, 6, 1, 0, 0)
    '''

    return datetime(d.year, d.month, d.day)
        
def timedelta_to_days(td):
    ''' Converts timedelta to floating point days.
    
        >>> timedelta_to_days(timedelta(seconds=864000))
        10.0
        >>> timedelta_to_days(timedelta(days=4, seconds=43200))
        4.5
    '''
    
    # !!!!! python 3
    return timedelta_to_seconds(td) / seconds_in_day

def timedelta_to_seconds(td):
    ''' Converts timedelta to floating point seconds.
    
        >>> timedelta_to_seconds(timedelta(seconds=864000))
        864000.0
        >>> timedelta_to_seconds(timedelta(days=4, seconds=43200))
        388800.0
    '''
    
    # internally timedelta only stores days, seconds, and microseconds
    # !!!!! python 3
    return (
        (td.days * seconds_in_day) + 
        td.seconds + 
        ((1.0 * td.microseconds) / microseconds_in_second))    
    
def one_month_before(date):
    ''' Returns one month before.  
    
        Accepts a date or datetime. Returns a datetime.
    
        >>> one_month_before(date(2012, 06, 01))
        datetime.datetime(2012, 5, 1, 0, 0)
        >>> one_month_before(date(2012, 03, 30))
        datetime.datetime(2012, 2, 29, 0, 0)
        >>> one_month_before(date(2012, 05, 31))
        datetime.datetime(2012, 4, 30, 0, 0)
    '''
        
    if date.month > 1:
        last_year = date.year
        last_month = date.month - 1
    else:
        last_year = date.year - 1
        last_month = 12

    current_date_range = calendar.monthrange(date.year, date.month)
    last_date_range = calendar.monthrange(last_year, last_month)
    if date.day == current_date_range[1]:
        last_day = last_date_range[1]
    else:
        if date.day > last_date_range[1]:
            last_day = last_date_range[1]
        else:
            last_day = date.day

    earlier = datetime(last_year, last_month, last_day)
    return earlier

def start_of_day(d):
    ''' Returns datetime with no hours, minutes, seconds, or microseconds.  
    
        Accepts a date or datetime. Returns a datetime.
    
        >>> start_of_day(date(2012, 06, 01))
        datetime.datetime(2012, 6, 1, 0, 0)
        >>> start_of_day(datetime(2012, 03, 30, 11, 27))
        datetime.datetime(2012, 3, 30, 0, 0)
    '''
        
    return date_to_datetime(datetime_to_date(d))
    
def end_of_day(d):
    ''' Returns the latest datetime for the day.   
    
        Accepts a date or datetime. Returns a datetime.
    
        >>> end_of_day(date(2012, 06, 01))
        datetime.datetime(2012, 6, 1, 23, 59, 59, 999999)
        >>> end_of_day(datetime(2012, 03, 30, 11, 27))
        datetime.datetime(2012, 3, 30, 23, 59, 59, 999999)
    '''
    
    return start_of_day(d) + one_day - one_microsecond
    
def date_range(start, end, lei_convention=False):
    ''' Generates every date in the range from start to end, inclusive.
    
        To follow the endpoint convention [a, b) and exclude the 
        right endpoint, i.e. include the first element and exclude the last,
        set lei_convention=True. See http://mathworld.wolfram.com/Interval.html
    
        If start is later than end, returns dates in reverse chronological 
        order. 
    
        Accepts dates or datetimes. Yields dates.

        >>> list(date_range(date(2012, 06, 01), date(2012, 06, 02)))
        [datetime.date(2012, 6, 1), datetime.date(2012, 6, 2)]
        >>> list(date_range(date(2012, 06, 02), date(2012, 06, 01)))
        [datetime.date(2012, 6, 2), datetime.date(2012, 6, 1)]
        >>> list(date_range(date(2012, 06, 01), date(2012, 06, 01)))
        [datetime.date(2012, 6, 1)]
        >>> list(date_range(date(2012, 06, 01), date(2012, 06, 02), lei_convention=True))
        [datetime.date(2012, 6, 1)]
        >>> list(date_range(date(2012, 06, 02), date(2012, 06, 01), lei_convention=True))
        [datetime.date(2012, 6, 2)]
        >>> list(date_range(datetime(2012, 06, 01, 21, 03), datetime(2012, 06, 02, 00, 00)))
        [datetime.date(2012, 6, 1), datetime.date(2012, 6, 2)]
        >>> list(date_range(datetime(2012, 06, 01, 00, 00), datetime(2012, 06, 02, 23, 59, 59, 999999)))
        [datetime.date(2012, 6, 1), datetime.date(2012, 6, 2)]
        >>> list(date_range(datetime(2012, 06, 02, 23, 59, 59, 999999), datetime(2012, 06, 01, 23, 59, 59, 999999)))
        [datetime.date(2012, 6, 2), datetime.date(2012, 6, 1)]
        >>> list(date_range(datetime(2012, 06, 01, 00, 00), datetime(2012, 06, 01, 23, 59, 59, 999999)))
        [datetime.date(2012, 6, 1)]
    '''
    
    increasing = start <= end
    day = datetime_to_date(start)
    
    if lei_convention:
        if increasing:
            if isinstance(end, datetime):
                end = end - one_microsecond
            else:
                end = end - one_day
        else:
            if isinstance(end, datetime):
                end = end + one_microsecond
            else:
                end = end + one_day
                
    end = datetime_to_date(end)
    
    yield day
    if increasing:
        while day < end:
            day = day + one_day
            yield day
    else:
        while day > end:
            day = day - one_day
            yield day


class elapsed_time(object):
    ''' Context manager to compute elapsed time. 
        
        >>> ms = 200
        >>> with elapsed_time() as et:
        ...     # !!!!! python 3
        ...     time.sleep(float(ms)/1000)
        >>> delta = et.timedelta()
        >>> lower_limit = timedelta(milliseconds=ms)
        >>> upper_limit = timedelta(milliseconds=ms+1)
        >>> assert delta >= lower_limit
        >>> assert delta < upper_limit
        >>> print et
        200 ms
    
    ''' 
    
    def __init__(self):
        self.start = now()
        self.end = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, *exc_info):
        self.end = now()
        
    def __str__(self):
        return timedelta_to_human_readable(self.timedelta())
        
    def timedelta(self):
        ''' Elapsed time as timedelta type.
        
            If still in block, then elapsed time so far. '''
        
        if self.end:
            result = self.end - self.start
        else:
            result = now() - self.start
        return result

def date_string_to_date(date_string):
    ''' Convert a string representation of a date into a python date.

        >>> date_string_to_date('2015-01-14')
        datetime.date(2015, 1, 14)
        >>> date_string_to_date('14-01-2015')
        datetime.date(2015, 1, 14)
        >>> date_string_to_date('test')
    '''
    
    Date_Format1 = '(\d{4})-(\d{2})-(\d{2})'
    Date_Format2 = '(\d{2})-(\d{2})-(\d{4})' # the European alternative
    
    d = None
    m = re.match(Date_Format1, date_string)
    if m:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        m = re.match(Date_Format2, date_string)
        if m:
            d = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        
    return d


today = now()
tomorrow = today + one_day
yesterday = today - one_day
one_month_ago = one_month_before(today)

        
if __name__ == "__main__":
    import doctest
    doctest.testmod()

