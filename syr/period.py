'''
    A period of time.
   
    Copyright 2010 GoodCrypto
    Last modified: 2015-05-19

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import datetime

from syr.log import get_log
import syr.times
from syr.times import one_microsecond, date_to_datetime, one_day, start_of_day, end_of_day

class Period(object):
    ''' A period of time. Similar to timedelta plus the actual start and end dates.
        
        In accordance with the "endpoint convention [a, b)", 
        the start time is included, and the end time isn't. 
        A time is in the period if time >= start and time < end.
        See http://mathworld.wolfram.com/Interval.html.
        
        If the the period start is a date, period.precise_start is one 
        microsecond after midnight of the day before the start date. 
        Otherwise period.precise_start is the same as start. 
        Similarly if the the period end is a date, period.precise_end 
        is midnight of the end date. Otherwise period.precise_end is 
        the same as end. '''
    
    def __init__(self, start, end=None):
        ''' Start and end are dates or datetimes. If end is not present or 
            is None, end is the same as start. '''
            
        if end == None:
            end = start
        
        self.start = start
        self.end = end
        
        if isinstance(start, datetime.date):
            self.precise_start = start_of_day(start)
        else:
            self.precise_start = start
        if isinstance(end, datetime.date):
            self.precise_end = end_of_day(end)
        else:
            self.precise_end = end
        
        assert self.precise_start <= self.precise_end, 'Start is after end, %s > %s' % (
            self.precise_start, self.precise_end)
            
    def __str__(self):
        """Convert the period to a string."""
        
        if self.start != self.end:
            result = '%s to %s' % (self.start, self.end)
        else:
            result = '%s' % self.start
        result = result.replace(' 00:00:00', '')
        return result
        
    def __unicode__(self):
        return u'%s' % str(self)
        
    def __contains__(self, when):
        ''' Returns whether the time is in this period. The 'when' arg may 
            be a date, datetime, or Period.
        
            If 'when' is a Period, then the 'Endpoint convention [a, b)' 
            convention is modified. The left endpoint is included in the 
            period as usual. But if 'when' is a period, and its start time 
            is in the period, and its end time is the same as this period's 
            end, then 'when' is in the period.
            
            In other words, if 'when' is a Period, it is in this period if 
            when >= start and time <= end. Otherwise 'when' is in this period 
            if when >= start and when < end. 
            
            See http://mathworld.wolfram.com/Interval.html    
        '''
            
        def in_period(when):
            when = date_to_datetime(when)
            # endpoint convention [a, b) convention
            # see http://mathworld.wolfram.com/Interval.html 
            return when >= self.precise_start and when < self.precise_end
            
        if isinstance(when, Period):
            result = (
                in_period(when.precise_start) and
                (in_period(when.precise_end) or when.precise_end == self.precise_end))
        else:
            result = in_period(when)
        return result
             
    def __cmp__(self, other):
        ''' Compare periods '''

        return self.precise_end - self.precise_start

    def includes(self, when):
        ''' DEPRECATED. Use 'in' operator, e.g. 'if when in period'.
        
            Returns whether the time is in the period.
        
            The left endpoint is included in the period. The right endpoint 
            is not. A time is in the period if time >= start and time < end. '''
            
        return when in self
        
    def duration(self):
        ''' Time between start and end.'''
        
        return self.end - self.start
        
    def overlaps(period):
        ''' Return whether the periods overlap.
        
            By the endpoint convention [a, b) convention, 
            equaling either end period is not sufficient.
        
            See http://mathworld.wolfram.com/Interval.html
        '''
        
        return (
            self.precise_start < period.precise_end and 
            self.precise_end > period.precise_start)
        
    def date_range(self):
        return syr.times.date_range(self.start, self.end)
       
    @staticmethod
    def shorter(a, b):
        ''' Return the period with the shorter duration.
        
            We don't do this as __cmp__ because comparing periods 
            isn't the same as comparing their durations.'''
            
        if a.duration() <= b.duration():
            shorter_period = a
        else:
            shorter_period = b
        return shorter_period
        
    @staticmethod
    def longer(a, b):
        ''' Return the period with the longer duration.
        
            We don't do this as __cmp__ because comparing periods 
            isn't the same as comparing their durations.'''
            
        if a.duration() > b.duration():
            longer_period = a
        else:
            longer_period = b
        return longer_period
        
    @staticmethod
    def shortest(periods):
        ''' Return the period with the shortest duration'''
        
        return reduce(Period.shorter, periods)
  
    @staticmethod
    def longest(periods):
        ''' Return the period with the longest duration'''
        
        return reduce(Period.longer, periods)

    @staticmethod
    def concurrent(periods):
        ''' Longest period contained in all periods, i.e. the intersection of periods. '''
        
        if periods:
            # we're going to scan this sequence twice,
            # so make sure it's not a generator
            periods = list(periods)
            start = max(period.start for period in periods)
            end = min(period.end for period in periods)
            
            if start < end:
                period = Period(start, end)
            else:
                period = None
                
        else:
            period = None
            
        return period
        
    @staticmethod
    def inclusive(periods):
        ''' Period containing all periods, i.e. the union of periods 
            and any times between periods. '''
        
        periods = list(periods)
        if periods:
            start = min((period.start for period in periods))
            end = max((period.end for period in periods))
            
            if start <= end:
                period = Period(start, end)
            else:
                period = None
                
        else:
            period = None
            
        return period
        

        
if __name__ == "__main__":
    import doctest
    doctest.testmod()

