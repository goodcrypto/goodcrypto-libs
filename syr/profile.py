'''
    Python profiling.
    
    Remember that profiling slows your code, so remove it when not needed.

    Copyright 2014 GoodCrypto
    Last modified: 2014-10-02

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import cProfile, pstats, time
from cStringIO import StringIO

import syr.log

log = syr.log.get_log()

def run(command, filename, globals=None, locals=None):
    ''' Profile command string. Profile data is in filename.
    
        profile() runs command string, so for example: 
            profile('myprogram.main()', '/tmp/main.profile')
        is called in place of:
            myprogram.main()
            
        'delay' is the time in seconds before writing the profile to report.  
    
        WARNING: stdout and stderr of the function profiles may go in the bit bucket (why?)
                 If you suspect an error in your code, run it without cProfile. 
        
        >>> import os, os.path, time
        >>>
        >>> def start():
        ...     print('start')
        >>>
        >>> def sleep():
        ...     time.sleep(3)
        >>>
        >>> def end():
        ...     print('end')
        >>>
        >>> def test():
        ...     start()
        ...     sleep()
        ...     end()
        >>>
        >>> REPORT = '/tmp/syr.utils.profile.report'
        >>>
        >>> if os.path.exists(REPORT):
        >>>     os.remove(REPORT)
        >>> profile(test, REPORT)
        >>> assert os.path.getsize(REPORT)
        
    '''
    
    log.debug('run({})'.format(repr(command)))
    
    if globals is None and locals is None:
        cProfile.run(command, filename)
    else:
        cProfile.runctx(command, filename=filename, globals=globals, locals=locals)
        
    log.debug('run() done')

def report(filename, lines=None):
    ''' Default profile report from profile in filename.
    
        Default lines to print is 20.
        
        If you need to profile before the program ends, set a timer to 
        invoke report().
        
        Report text is returned and logged.
    '''
    
    if not lines:
        lines = 20
    
    out = StringIO()
    stats = pstats.Stats(filename, stream=out)
    # stats.strip_dirs()
    stats.sort_stats('cumulative', 'time', 'calls')
    stats.print_stats(lines)
    text = out.getvalue()
    
    log.debug('report from {}:\n{}'.format(filename, text))
    
    return text
        
if __name__ == "__main__":
    import doctest
    doctest.testmod()
