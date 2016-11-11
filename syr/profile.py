'''
    Python profiling.

    This module does not work well with threads. Run a profile inside the thread.
    Remember that profiling slows your code, so remove it when not needed.

    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-06-06

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import cProfile, pstats, time
if IS_PY2:
    from cStringIO import StringIO
else:
    from io import StringIO

import syr.log

log = syr.log.get_log()

def run(command, datafile, globals=None, locals=None):
    ''' Profile command string. Record profile data in filename.

        profile() runs command string, so for example:
            profile('myprogram.main()', '/tmp/main.profile')
        is called in place of:
            myprogram.main()

        WARNING: stdout and stderr of the function profiles may go in the bit bucket (why?)
                 If you suspect an error in your code, run it without cProfile.

        >>> import os, os.path, time
        >>>
        >>> DATA = '/tmp/syr.utils.profile.data'
        >>>
        >>> if os.path.exists(DATA):
        ...     os.remove(DATA)
        >>> run('_sample_test_code()', DATA, globals(), locals())
        start
        end
        >>> assert os.path.getsize(DATA)
    '''

    log.debug('run({})'.format(repr(command)))

    if globals is None and locals is None:
        cProfile.run(command, datafile)
    else:
        cProfile.runctx(command, filename=datafile, globals=globals, locals=locals)

    log.debug('run() done')

def report(datafile, lines=None):
    ''' Report on profile data from datafile.

        Default lines to print is 20.

        If you need to profile before the program ends, set a timer to
        invoke report().

        Returns report text.
        
        >>> import os, os.path
        >>>
        >>> DATA = '/tmp/syr.utils.profile.data'
        >>> REPORT = '/tmp/syr.utils.profile.report'
        >>>
        >>> for path in [DATA, REPORT]:
        ...     if os.path.exists(path):
        ...         os.remove(path)
        >>> run('_sample_test_code()', DATA, globals(), locals())
        start
        end
        >>> text = report(DATA)
        >>> assert text
        >>>
        >>> with open(REPORT, 'w') as f:
        ...     f.write(text)
        >>> assert os.path.getsize(REPORT)
    '''

    if not lines:
        lines = 20

    out = StringIO()
    stats = pstats.Stats(datafile, stream=out)
    # stats.strip_dirs()
    stats.sort_stats('cumulative', 'time', 'calls')
    stats.print_stats(lines)
    text = out.getvalue()

    log.debug('report from {}:\n{}'.format(datafile, text))

    return text
    
def report_to_file(codestring, reportfile, datafile=None, globals=None, locals=None):
    ''' Profile codestring and write report to reportfile. '''
    
    def write_report():
        text = syr.profile.report(datafile)
        with open(reportfile, 'w') as f:
            f.write(text)
        log.debug('profile report is in {}'.format(reportfile))
        
    if datafile is None:
        datafile = reportfile + '.data'
        
    try:
        run(codestring, datafile, globals=globals, locals=locals)
    except:
        log.debug('always report profile')
        write_report()
        raise
        
    else:
        write_report()
    
def write_report(datafile, reportfile):
    ''' Write report from datafile to reportfile. '''
    
    text = syr.profile.report(datafile)
    with open(reportfile, 'w') as f:
        f.write(text)
    log.debug('profile report is in {}'.format(reportfile))
    
def _sample_test_code():
    ''' Sample code to use for profile testing. '''
   
    def start():
        print('start')
   
    def sleep():
        time.sleep(3)
   
    def end():
        print('end')

    start()
    sleep()
    end()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
