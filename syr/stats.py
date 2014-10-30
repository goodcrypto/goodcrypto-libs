'''
    Statistics
    
    This used to be named stat.py. It was renamed to avoid conflict 
    with the standard library named stat.

    Copyright 2010-2013 GoodCrypto
    Last modified: 2014-07-10

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import math, numpy

#from log import get_log

#log = get_log()
debug = False

def mean(values):
    ''' Mean of an iterable.

        Returns a float.

        When people say "average" they usually mean "mean".
 
        >>> mean([6, 2, 5, 1])
        3.5
        >>> mean([5])
        5.0
        >>> mean([])
        nan
    '''

    return numpy.array(values).mean()

def median(values):
    ''' Median of an iterable.

        Returns a float.
        
        The median is less sensitive to outliers than the mean is.
        The values do not have to be sorted since this function sorts them.

        >>> median([1, 2, 5])
        2.0
        >>> median([1, 2])
        1.5
        >>> median([5])
        5.0
        >>> median(3)
        3.0
        >>> median([])
        nan
        >>> median(x for x in [1, 2, 5])
        2.0
    '''

    # numpy.lib.median() seems to have trouble with generators
    try:
        values = list(values)
    except TypeError:
        # numpy would handle this if we hadn't explicitly used list()
        values = [values]
        
    # numpy.lib.median() assumes already sorted
    values = sorted(values)
    
    return numpy.lib.median(numpy.array(values))

def is_significant(a, b):
    ''' True if the difference between the values is statisically
        significant, else False.

        A difference may be staticially significant, but still not
        be significant. For example, if everyone in all groups in a
        split test hits the conversion, the difference between
        converted and not converted is staticially significant, but
        there is no difference between the groups. '''

    return (
        a + b > 0 and
        abs(a - b) > math.sqrt(a + b))

def smooth(raw_data, smoothing_periods):
    ''' Return a list of smoothed data using a running average.

        For each period after the first smoothing_periods, calculate the
        average (mean) the previous smoothing_periods of data and the
        current period. Discards the first smoothing_periods periods.

        >>> raw_data = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
        >>> smoothing_periods = 7
        >>> smooth_data = smooth(raw_data, smoothing_periods)
        >>> smooth_data
        [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0]
        >>> len(smooth_data) == (len(raw_data) - smoothing_periods)
        True
        '''

    data = []
    period_count = 0

    if len(raw_data) > smoothing_periods:
        for period in raw_data:
            period_count += 1
            if period_count > smoothing_periods:
                data.append(mean(raw_data[period_count-smoothing_periods:period_count]))
    else:
        raise ValueError, 'Too few elements to smooth'
        
    return data

def percent(numerator, denominator):
    ''' Calculate floating point percentage.

        Returns None if the denominator is 0, rather than throwing an exception.

        >>> percent(1, 10)
        10.0
        >>> percent(0, 10)
        0.0
        '''

    if denominator:
        if numerator is None:
            numerator = 0
        # !!!!! python 3
        result = (numerator * 100.0) / denominator
    else:
        result = None

    return result    
    
def assert_100_percent(total):
    ''' Assert that the total is 100.0, within roundiong errors. ''' 
    assert total > 97.5000 and total < 102.5000, (
        'percentage %f should be 100' % total)

def bin(kv, bins=5):
    ''' Returns keys binned by value rank.
    
        kv is a dict of {key:value; ...}.
    
        Pareto's law of 80:20 suggests quintiles, or 5 bins.
        We want to be able to indicate the top 20%.
        So 5 bins is the default
    
        Returns a dict of {key: 1..bins, ...}. '''
        
    def value_key(item):
        key, value = item
        return value, key
        
    def log(x):
        print x

    if debug: log('kv %r' % kv)                                                                            
    binned_keys = {}
    number_of_keys = len(kv)
    if debug: log('number_of_keys %d' % number_of_keys)
    keys_by_value = sorted(kv.iteritems(), key=value_key)
    if debug: log('keys_by_value %r' % keys_by_value)
    # !!!!! python 3
    bin_size = number_of_keys/bins
    if debug: log('bin_size %d' % bin_size)
    for bin in range(bins):
        start_bin = bin * bin_size
        for index in range(start_bin, start_bin + bin_size):
            if index < number_of_keys:
                key, value = keys_by_value[index]
                binned_keys[key] = bin + 1 # 1-indexed, not 0-indexed
        # get the rest of the last bin
        if bin == bins - 1:
            start_bin = (bin * bin_size) + bin_size
            for index in range(start_bin, number_of_keys):
                key, value = keys_by_value[index]
                binned_keys[key] = bin + 1 # 1-indexed, not 0-indexed
            
    if debug: log('binned_keys %r' % binned_keys)
    return binned_keys
        
    ''' get a float value in 0..1 for each key -- does not render well    
    scaled_values = {}
    max_value = max(kv.values())
    if debug: log('max_value: %r' % max_value)
    for key in kv:
        # !!!!! python 3
        scaled_values[key] = float(kv[key]) / max_value
    if debug: log('scaled_values: %r' % scaled_values)
        
    return scaled_values
    '''
         

if __name__ == "__main__":

    import doctest
    doctest.testmod()
