'''
    Processes.

    We prefer the sh module over python standard modules because linux
    command line programs are more likely to have been thoroughly vetted.

    Copyright 2013-2014 GoodCrypto
    Last modified: 2015-02-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import datetime, sh, time, traceback

import syr.times

from log import get_log
import user

log = get_log()

class TimedOutException(Exception):
    ''' Operation timed out exception. '''
    pass

def pid_from_port(port):
    ''' Find which pid opened the port.

        Returns None if none. '''

    # fuser requires --namespace before port, so can't use namespace='tcp'
    pids = pids_from_fuser('--namespace', 'tcp', port)
    if pids:
        assert len(pids) == 1, 'pids: {}'.format(pids)
        pid = pids[0]
        result = int(pid)
    else:
        result = None
    return result

def pids_from_file(path):
    ''' Get list of pids that have the file or dir open.

        Returns None if none. '''

    return pids_from_fuser(path)

def pids_from_program(program):
    ''' Get list of pids for program. 
    
        Returns empty list if none
    '''

    try:
        pid_strings = sh.pidof(program).stdout.strip().split()
    except sh.ErrorReturnCode_1:
        pids = []
    else:
        pids = [int(pid) for pid in pid_strings]
        
    return pids

def program_from_pid(pid):
    ''' Find which program has the pid.

        Returns None if none. '''

    # /proc/PID/exe is a link to the program
    try:
        proc_exe = sh.ls('-l', '/proc/{}/exe'.format(pid))
        log.debug('proc_exe: {}'.format(proc_exe))
        _, _, program = proc_exe.strip().rpartition('->')
        program = program.strip()
    except:
        program = None

    log.debug('program_from_pid({}): {}'.format(pid, program))
    return program

def program_from_port(port):
    ''' Find which program opened the port.

        Returns None if none. '''

    log.debug('port: {}'.format(port))
    pid = pid_from_port(port)
    log.debug('pid: {}'.format(pid))
    if pid:
        program = program_from_pid(pid)
    else:
        program = None

    return program

def programs_from_file(path):
    ''' Find which programs have the file or dir open.

        Returns None if none. '''

    pids = pids_from_file(path)
    if pids:
        programs = []
        for pid in pids:
            program = program_from_pid(pid)
            if program and not program in programs:
                programs.append(program)
        if not programs:
            programs = None
    else:
        programs = None

    return programs

def pids_from_fuser(*args):
    ''' Get list of pids using fuser.

        Returns Empty list if none. '''

    user.require_user('root') # fuser requires root

    log.debug('pids_from_fuser(*args) args: {}'.format(repr(args)))
    try:
        ''' Example:
                # fuser --namespace tcp 9050
                9050/tcp:             3331

            WARNING: Very strangely, fuser sends the first part of the line to
            stderr, and the second part to stdout. The stdout splits on the
            spaces.

            fuser also returns an exit code of 1.
        '''
        fuser_out = sh.fuser(*args, _ok_code=[0, 1])
    except:
        # import traceback # DEBUG
        # log.debug(traceback.format_exc()) # DEBUG
        pids = None
    else:
        log.debug('pids_from_fuser() fuser_out: {}'.format(repr(fuser_out)))
        # only the pids g to stdout
        pid_strings = fuser_out.stdout.strip().split()
        pids = [int(pid) for pid in pid_strings]

    log.debug('pids_from_fuser() pid: {}'.format(pids))
    return pids

def wait(event, timeout=None, sleep_time=1, event_args=None, event_kwargs=None):
    ''' Wait for an event. Retries event until success or timeout.

        Default is to ignore exceptions except when there is a timeout.

        'event' is a function. event() succeeds if it does not raise an 
        exception. Each call to event() continues until it succeeds or 
        raises an exception. It is not interrupted if it times out.

        'timeout' can be in seconds as an int or float, or a 
        datetime.timedelta, or a datetime.datetime. Default is None, which 
        means no timeout. If the timeout deadline passes while event() is 
        running, event() is not interrupted. If event() times out while 
        running and does not succeed, wait() raises the exception from event().

        'sleep_time' is in seconds. Default is one.

        'event_args' is an list of positional args to event(). Default is None.
        'event_kwargs' is an dict of keyword args to event(). Default is None.

        Returns result from event() if no timeout, or if timeout returns last exception. 
    '''

    def timed_out():
        return timeout and (syr.times.now() >= deadline)

    if timeout:

        if isinstance(timeout, int) or isinstance(timeout, float):
            deadline = syr.times.now() + datetime.timedelta(seconds=timeout)

        elif isinstance(timeout, datetime.timedelta):
            deadline = syr.times.now() + timeout

        elif isinstance(timeout, datetime.datetime):
            deadline = timeout

        else:
            raise TypeError('timeout must be an int, float, datetime.timedelta, or datetime.datetime')

        log.debug('wait() timeout: {}, deadline: {}'.format(timeout, deadline))

    if event_args is None:
        event_args = []
    if event_kwargs is None:
        event_kwargs = {}

    success = False
    while not success:
        try:
            result = event(*event_args, **event_kwargs)

        except KeyboardInterrupt:
            raise
            
        except:
            if timed_out():
                log.debug('wait() timed out with exception: {}'.
                    format(traceback.format_exc()))
                raise
            else:
                log.debug('wait() ignored exception because not timed out:\n{}'.format(
                    traceback.format_exc()))

        else:
            success = True

        if not timed_out():
            time.sleep(sleep_time)

    return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()
