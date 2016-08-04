'''
    Processes.

    We prefer the sh module over python standard modules because linux
    command line programs are more likely to have been thoroughly vetted.

    Copyright 2013-2015 GoodCrypto
    Last modified: 2015-11-18

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import datetime, os, sh, signal, subprocess, thread, threading, time
from contextlib import contextmanager
from traceback import format_exc

import syr.python, syr.times

from log import get_log
import user

log = get_log()

class TimedOutException(Exception):
    ''' Operation timed out exception. '''
    pass

class CallException(Exception):
    ''' call() exception. '''
    pass

def pid_from_port(port):
    ''' Find which pid opened the port.

        This can be much faster than trying to connect to a port.
        Calling socket.socket().connect() sometimes succeeds for every port.

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

        The program is the full path of the running program. This may
        not match the program on the command line, if the program on
        the command line is a link.

        Returns None if none. '''

    # /proc/PID/exe is a link to the program
    try:
        program = os.readlink('/proc/{}/exe'.format(pid))
    except OSError:
        program = None

    log.debug('program_from_pid({}): {}'.format(pid, program))
    return program

def program_from_port(port):
    ''' Find which program opened the port.

        See program_from_pid(pid).

        Returns None if none. '''

    log.debug('port: {}'.format(port))
    pid = pid_from_port(port)
    log.debug('pid: {}'.format(pid))
    if pid:
        program = program_from_pid(pid)
    else:
        program = None

    return program

def programs_using_file(path):
    ''' Find which programs have the file or dir open.

        Returns None if none. '''

    programs = set()

    # fuser
    pids = pids_from_file(path)
    if pids:
        log.debug('pids using {}: {}'.format(path, pids))

        for pid in pids:
            program = program_from_pid(pid)
            if program:
                programs.add(program)
            else:
                log.debug('no program from pid  {}'.format(pid))

    # lsof
    lines = sh.lsof().stdout.strip().split('\n')
    for line in lines:
        fields = line.split()
        command = fields[0]
        command_path = fields[-1]
        if command_path == path or command_path.startswith(path + '/'):
            programs.add(command)

    if programs:
        programs = sorted(programs)
    else:
        programs = None

    return programs

def is_program_running(search_string):
    '''
        Return whether a program is running.

        WARNING: Unreliable, apparently dependent on characters in search_string

        >>> is_program_running('nginx')
        True
        >>> is_program_running('not.running')
        False
    '''

    def capture_output(line):
        output.append(line)

    log.debug('is_program_running() searchstring: {}'.format(search_string))

    try:
        output = []
        psgrep_result = sh.psgrep(search_string)
    except sh.ErrorReturnCode as err:
        running = False
    except:
        running = False
        log.debug(format_exc())
    else:
        running = (
            (psgrep_result.exit_code == 0) and
            (psgrep_result.stdout != '') and
            (search_string in psgrep_result.stdout))

    if not running:
        try:
            ps_result = sh.ps('-eo', 'pid,args', _out=capture_output)
            running = (
                (ps_result.exit_code == 0) and
                (ps_result.stdout != '') and
                (search_string in ps_result.stdout))
            if running:
                log.debug('exit code: {}'.format(ps_result.exit_code))
                #log.debug('stdout: {}'.format(ps_result.stdout))
            else:
                running = search_string in output
                if not running:
                    log.debug('output: {}'.format(output))
        except:
            log.debug(format_exc())
        else:
            pass

    log.debug('{} is_program_running: {}'.format(search_string, running))

    return running

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
        # log.debug(format_exc()) # DEBUG
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
                    format(format_exc()))
                raise
            else:
                log.debug('wait() ignored exception because not timed out:\n{}'.format(
                    format_exc()))

        else:
            success = True

        if not timed_out():
            time.sleep(sleep_time)

    return result

@contextmanager
def fork_child():
    ''' Context manager to run a forked child process.

        Subprocess returns a process result code of 0 on success,
        or -1 if the child block raises an exception.

        >>> parent_pid = os.getpid()
        >>> # if child process
        >>> if os.fork() == 0:
        ...     with fork_child():
        ...         # child process code goes here
        ...         assert parent_pid != os.getpid()
        >>> assert parent_pid == os.getpid()
    '''

    """ Including "if os.fork() == 0:" in the context manager results in::

            RuntimeError: generator didn't yield
    """

    # try to run in a new session
    try:
        os.setsid()
    except:
        pass

    # continue after the calling process ends
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
        yield
    except:
        result_code = -1
    else:
        result_code = 0
    finally:
        os._exit(result_code)

def stop_all_threads():
    ''' NOT WORKING

        Stop all threads.

        Avoid "Exception ... (most likely raised during interpreter shutdown)".

        When the python interpreter exits, it clears globals before it stops
        threads. That causes running threads die very messily. This is a
        security risk. Call stop_all_threads() at the end of your program,
        and before any call to sys.exit() or os._exit().

        Calling thread.exit() is usually a bad idea, but it's ok in this case
        because the threads are about to die anyway.

        WARNING: This function should only be called when the python
        interpreter is about to exit.

        NOT WORKING >>> stop_all_threads()
    '''

    for thread in threading.enumerate():
        try:
            if not thread.daemon:
                thread.exit()
        except:
            # this thread would die anyway as we exit the program, so be quiet
            pass
    assert not threading.enumerate(), 'Not all threads stopped'

def call(*args, **kwargs):
    ''' Call cli command.

        Returns stdout from command. Raises subprocess.CalledProcessError
        on error. If 'Permission denied', retries command with bash.

        strip_white_space::
            Strip white space from output. Default is True.

        ok_return_codes::
            Iterable of return codes that indicate success. Default is None,
            which means only a return code of zero is ok.
    '''

    def _call(strip_white_space=True, ok_return_codes=None, shell=False):

        log.debug('    _call(): {} (type {})'.format(args, type(args))) # DEBUG
        log.debug('    _call(): shell={}'.format(shell)) # DEBUG
        try:
            result = subprocess.check_output(args,
                stderr=subprocess.STDOUT, shell=shell)

        except subprocess.CalledProcessError as cpe:
            log.debug(cpe)
            if ok_return_codes is None:
                ok_return_codes = []
            if cpe.returncode in set(ok_return_codes):
                log.debug('cpe.returncode {} is ok'.format(cpe.returncode))
                result = ''
                if cpe.output:
                    log.debug('cpe.output: {}'.format(cpe.output))
                    log.debug(syr.python.stacktrace()) # DEBUG
                    raise CallException(str(cpe) + ': ' + cpe.output)
            else:
                raise

        if strip_white_space:
            result = result.strip()

        return result

    log.debug('call(): {} (type {})'.format(args, type(args)))
    log.debug('call() whoami: {}'.format(subprocess.check_output('whoami')))
    try:
        result = _call(**kwargs)
    except OSError as ose:
        if 'Permission denied' in ose:
            result = _call(shell=True, **kwargs)
        else:
            raise

    return result
    
def _UNUSED_start(command, user=None, *args):
    ''' Start a program. '''
    
    ''' It can be very hard to start a program from python, especially as 
        another user. Here is a collection of possible ways. 
        
        The ones that use sudo should be skipped if the current user is 
        the target user.
        
        The best solution so far for "sudo -u USER PROGRAM" is syr.user.force().
    '''

    """
    def wait_for_web_proxy():
        ''' Make sure the web proxy started '''

        MAXWAIT = 10 # seconds

        wait = 0
        while (not is_program_running(WEB_FILTERS_PROGRAM)) and (wait < MAXWAIT):
            time.sleep(1)
            wait = wait + 1
        log('web server started in {} seconds: {}'.format(wait, is_program_running(WEB_FILTERS_PROGRAM)))
    
    SRC_DIR = '/usr/local/src'    
    WEB_FILTERS_PROGRAM = 'web/filters.py'
    WEB_FILTERS_PATH = os.path.join(SRC_DIR, WEB_FILTERS_PROGRAM)
    FILTER_STARTUP_TIME = 5 # secs to start, and for any early exceptions to happen

    log('starting web proxy')

    # we are very stubborn about starting the web proxy
    # the web program uses web/__main__.py, and
    # web/__main__.py does not launch filters.py well right now
    # goodcrypto-web start
    # filters.py does the actual work

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start with subprocess.call()')
        if os.fork() == 0:
            with fork_child():
                subprocess.check_output(
                    'sudo -u {} {} &'.format(USER, WEB_FILTERS_PATH),
                    shell=True)
        time.sleep(FILTER_STARTUP_TIME)

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start with sh.sudo()')
        sh.sudo('-u', USER, WEB_FILTERS_PATH, _bg=True)
        time.sleep(FILTER_STARTUP_TIME)

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start without explicit sudo()')
        filters = sh.Command(WEB_FILTERS_PATH)
        filters(_bg=True)
        time.sleep(FILTER_STARTUP_TIME)

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start with explicit sudo()')
        with sudo(USER):
            run = sh.Command(WEB_FILTERS_PATH)
            run(_bg=True)
            time.sleep(FILTER_STARTUP_TIME)

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start with goodcrypto_web')
        sh.goodcrypto_web('start')
        time.sleep(FILTER_STARTUP_TIME)

    if not is_program_running(WEB_FILTERS_PROGRAM):
        log('web app not running. start in foreground of child process')
        if os.fork() == 0:
            with fork_child():
                import goodcrypto.web.filters
                goodcrypto.web.filters.main()
        time.sleep(FILTER_STARTUP_TIME)

    # wait_for_web_proxy()
    assert is_program_running(WEB_FILTERS_PROGRAM), '{} not running'.format(WEB_FILTERS_PROGRAM)

    log('web proxy started')
    
    """
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
