# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals
'''
    Python logging for humans.

      * Instant logs. No complex setup.
      * Logs have useful default names.
        * Easy to find in a single directory tree.
        * You always know which log goes with a module.
      * There's no conflict between users.
      * A master log for each user shows you all log entries in order.

    >>> import syr.log
    >>> log = syr.log.open()
    >>> log('message')

    The default log file is "/var/local/log/USER/MODULE.log".
    USER is the current user. MODULE is the module calling this one.

    Logging levels work as usual. The default logging level is DEBUG.
    >>> log.debug('debugging message')
    >>> log.info('informational message')
    >>> log('debugging message')

    You can specify a log filename, which appears in the
    /var/local/log/USER directory.
    >>> log = get_log('special.log')
    >>> log('log message to specified file')

    You can specify a log pathname.
    >>> log = get_log('/tmp/special.log')
    >>> log('log message to specified path')
    
    Log an exceptions and get a traceback:
    >>> try:
    ...     raise Exception('test')
    ... except Exception as exc:
    ...     log(exc)

    The log defaults work especially well in complex systems when apps run 
    as separate users, but the apps share modules that generate their own 
    logs. There's no conflict over which user owns a module's log. There 
    are no jumbled log lines from different users or processes.

    If a program that doesn't use syr.log needs to access a log directory
    in /var/local/log, you may need to create /var/local/log/USER in advance.

    Bugs:
        Log.info() can write to more than one log. (may be fixed)

    Copyright 2008-2016 GoodCrypto
    Last modified: 2016-07-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

"""
    Developer notes.

    Based on python standard logging.

    Python gets confused about circular imports.
    It's best for this module to delay imports of other modules that use this module.
    An alternative is to use the sh module here instead of calling the other module.
    Another alternative is delayed import of syr.log in the other module.
    Example::

        _log = None
        def log(msg):
            global _log
            if not _log:
                from syr.log import get_log
                _log = get_log()
            _log(message)

    Some modules can't import this one, e.g. django's settings.py. An alternative
    is to use syr.log._debug(..., force=True), or python's built-in logger directly.
    Example:

        import logging
        # since settings.py imports * from this module, settings.py may also use this log
        LOG_FILENAME = '/var/local/goodcrypto/server/data/logs/settings.log'
        logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,
                            format='%(asctime)s %(name)s %(levelname)s %(message)s')
        try:
            os.chmod(LOG_FILENAME, 0666)
        except:
            pass
        log = logging.debug

        ...

        log(...)
"""
import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

import atexit, logging, os, os.path, pwd, sh, shutil, smtplib, stat, sys
import tempfile, threading, time, traceback
from threading import Thread
from traceback import format_exc, format_stack
from glob import glob

import syr._log

# analogous to /var/log
BASE_LOG_DIR = '/var/local/log'

# These perms are very convenient, but not secure. If you want more secure
# perms for the base log dir, then create the BASE_LOG_DIR in advance with
# the perms you want. Also, create a subdirectory for each user that will run apps
# which write using syr.log. For example, create the following subdirectories:
# goodcrypto, www-data, and one for each local user. Each subdirectory should be
# owned by its user. If a program that doesn't use syr.log needs a directory,
# you may need to create it in advance.
BASE_LOG_DIR_PERMS = 0o777

logs = {}
_master_logs = {}
_use_master_log = True
_raise_logging_errors = False

# the log module cannot easily use logs itself
# so _DEBUGGING turns alternate logging on and off
# use _debug(msg) to log debugging messages
# WARNING: Setting _DEBUGGING to True will destroy isolation of logs for
#          different users. This will cause strange seemingly unrelated
#          errors and cost you days of debugging. Leave _DEBUGGING set to
#          False except when you're explicitly debugging this module.
_DEBUGGING = False
_DEBUGGING_LOG_REMOVE_DISABLE = False

_DEFAULT_LOG_DIR_PERMS = 0o755
_DEFAULT_PERMS = 0o644
TOTAL_WORLD_ACCESS = 0o666

# set these values if you want mail sent if a serious error occurs
alert_from_address = None
alert_to_address = None

_get_log_lock = threading.Lock()

# configure basic python logging
'''
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
    def close(self):
        pass
null_handler = NullHandler()
logging.getLogger('').addHandler(null_handler)
'''
basic_logging_file = tempfile.NamedTemporaryFile(
    mode='a',
    prefix='syr.logs.default.', suffix='.log',
    delete=True)
os.chmod(basic_logging_file.name, TOTAL_WORLD_ACCESS)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s',
                    # using os.devnull results in "Bad file descriptor" when
                    # python logging closes the stream
                    # stream=open(os.devnull, 'a'))
                    stream=basic_logging_file)
def _debug(message, force=False, filename=None, mode=None):
    if force or _DEBUGGING:
        syr._log.log(message, filename=filename, mode=mode)

'''
    For speed, tested log messages queued and written to
    the log file in a separate thread. This avoids the main thread
    waiting on every write.

    Queuing log writes is actually slower, eats too much memory, and
    gets strange errors. Probably the overhead of queueing is higher
    than the overhead of writing a log message to disk. Because we do
    not limit the size of the log queue, it will grow to the size of
    unwritten logs.

    Example error:

        Error in atexit._run_exitfuncs:
        Traceback (most recent call last):
          File "/usr/lib/python2.6/atexit.py", line 24, in _run_exitfuncs
            func(*targs, **kargs)
          File "/usr/lib/python2.6/logging/__init__.py", line 1517, in shutdown
            h.close()
          File "/usr/lib/python2.6/logging/__init__.py", line 836, in close
            self.stream.close()
        IOError: close() called during concurrent operation on the same file object.
        Error in sys.exitfunc:
        Traceback (most recent call last):
          File "/usr/lib/python2.6/atexit.py", line 24, in _run_exitfuncs
            func(*targs, **kargs)
          File "/usr/lib/python2.6/logging/__init__.py", line 1517, in shutdown
            h.close()
          File "/usr/lib/python2.6/logging/__init__.py", line 836, in close
            self.stream.close()
        IOError: close() called during concurrent operation on the same file object.
    '''
class CustomFileHandler(logging.FileHandler):
    ''' Our FileHandler. '''

    def flush(self):
        ''' Flush the handler. '''

        # don't recurse
        if not getattr(self, '_flushing', False):

            self._flushing = True

            # requires magic knowledge of logging.FileHandler internals
            self.close()
            self._open()

            self._flushing = False

    def handleError(self, record):
        ''' Fix for useless logging during some errors:

                Traceback (most recent call last):
                  File "/usr/lib/python2.7/logging/__init__.py", line 850, in emit

            see Getting a more useful 'logging' module error output in python
                http://stackoverflow.com/questions/6898674/getting-a-more-useful-logging-module-error-output-in-python
        '''
        raise

class StreamHandlerFixed(logging.StreamHandler):
    ''' Fix for useless logging during some errors:

            Traceback (most recent call last):
              File "/usr/lib/python2.7/logging/__init__.py", line 850, in emit

        see Getting a more useful 'logging' module error output in python
            http://stackoverflow.com/questions/6898674/getting-a-more-useful-logging-module-error-output-in-python
    '''

    def handleError(self, record):
        raise

class _Log(object):
    ''' Log file.

        Wrapper to simplify python's logging facility.

        >>> from syr.log import get_log

        >>> log = get_log()
        >>> log('log message')

        >>> log2 = get_log('/tmp/testlog.log')
        >>> log('log message 2')

        Logs all messages at python's DEBUG level.
    '''

    lock = threading.Lock()

    log_dir = None
    filename = None


    def __init__(self,
        filename=None, dirname=None, group=None,
        recreate=False, verbose=False, audible=False):
        ''' 'filename' is an explicit filename.
            'dirname' is the dir to use with the default log file basename.
            'group' is the group that wns the lof file. Defaults to the group
            for the current user.
            'recreate' will delete any existing log before use.
            'verbose' prints log entries to stdout. The 'verbose' keyword can
            be overridden for a log entry.
            If audible=True, the command line 'say' program will be called
            with the message.
       '''

        self.filename = filename
        self.dirname = dirname
        self.group = group
        self.user = None
        self.recreate = recreate
        self.verbose = verbose
        self.audible = audible

        self.handler = None
        self.opened = False
        self.debugging = False
        self.stdout_stack = []

    def __call__(self, message, verbose=None, audible=None, exception=None):
        ''' Output message to log.debug, optionally also to stdout and audibly.

            If verbose=True, this log message will also be printed to stdout.
            If verbose=False, this message will not printed to stdout, even if
            the log was initialized with verbose=True. Default is None, which
            uses the verbose value passed to Log() or get_log(, if any).

            If audible=True, the command line 'say' program will be called
            with the message. Otherwise audible is similar to verbose. Since
            voice generation can be nearly unintelligible, the message should
            be very short and used infrequently.

            If exception=True, the last exception will be logged.
        '''

        self.debug(message)
        # previously was "self.write(message)". did some caller specify 'DEBUG', 'INFO' etc?

        if not self.is_master():

            if verbose is None:
                verbose = self.verbose
            if verbose:
                print('{} {}'.format(syr._log.timestamp(), message))

            if audible is None:
                audible = self.audible
            if audible:
                try:
                    from syr.utils import say
                    say(message)
                except:
                    pass

            # this is 'exception' passed to __call__()
            if exception:
                self.last_exception()

    def write(self, message):
        ''' Write message to log.

            write() writes to a log as you would to a file.
            This lets you redirect sys.stdout to the log and log print output
            generated by third party libraries, even if the library uses
            print statements without '>>' or print functions without 'stream='.
        '''

        def notify_webmaster(message):
            ''' Send the message to the webmaster.

                We can't use jean.dmail.send because it imports this module.
            '''

            if alert_from_address is not None and alert_to_address is not None:
                msg = ("From: %s\nTo: %s\nSubject: %s\n\n%s\n"
                   % (alert_from_address, alert_to_address, subject, message))
                server = smtplib.SMTP('localhost')
                server.sendmail(alert_from_address, alert_to_address, msg)

        # we don't use @synchronized here because of import errors

        global _raise_logging_errors

        try:
            from syr.python import is_string

            if is_string(message):
                self._write(message)
            elif isinstance(message, bytes) or isinstance(message, bytearray):
                self._write(message.decode(errors='replace'))
            else:
                self.write('unable to write message because it is a {}'.format(type(message)))

            if self.verbose:
                print(message)
            if _use_master_log and not self.is_master():
                try:
                    _master_logs[self.user]._write('- %s - %s' % (self.filename, message))
                except UnicodeDecodeError:
                    _master_logs[self.user]._write('- %s - !! Unable to log message -- UnicodeDecodeError !!' % (self.filename))

        except UnicodeDecodeError:
            try:
                _debug(message.decode(errors='replace'))
            except UnicodeDecodeError:
                self.write('unable to write message because it is a type: {}'.format(type(message)))
                subject = '!! Unable to log message !!'
                self._write(subject)
                if _raise_logging_errors:
                    _raise_logging_errors = False
                    notify_webmaster(message)

        except:

            raise
            self._write(format_exc())
            subject = '!! Unable to log message !!'
            self._write(subject)
            if _raise_logging_errors:
                _raise_logging_errors = False
                notify_webmaster(message)

    def _write(self, message):
        ''' Write directly to python logger. '''

        from syr.lock import locked

        with locked(_Log.lock):

            self.check_user()

            if not self.opened:
                try:
                    self.open()
                except:
                    self.last_exception()

            try:
                self.logger_debug(str(message))
            except:
                self.last_exception()

    def info(self, msg, *args, **kwargs):
        ''' Compatibility with standard python logging. '''

        self.log('INFO', msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        ''' Compatibility with standard python logging. 
        
            If the message is an Exception, Log.debug() logs everything we 
            know about the Exception. If you call Log.warning() etc. and 
            want Exception details, also call log.debug().
        '''

        if isinstance(msg, UnicodeError):
            
            # don't log the bad data; it screws up some editors
            self.debug(traceback.format_exception_only(type(msg), msg))
            self.debug('UnicodeError stacktrace:\n' + '    '.join(traceback.format_stack()))

        elif isinstance(msg, Exception):
            
            if msg.args:
                # log any Exception args
                try:
                    msg.args
                    
                except AttributeError:
                    pass
                    
                else:
                    if type(msg.args) is tuple:
                        try:
                            self.debug(' '.join(map(str, list(msg.args))))
                        except UnicodeDecodeError:
                            self.debug(b' '.join(map(bytes, list(msg.args))))
                    else:
                        self.debug(msg.args)

            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            # is the exc_info for this Exception?
            if type(exc_value) == type(msg) and str(exc_value) == str(msg):
                # in python 2.7 traceback.format_exception() does not perform as docced
                # it does not format the entire stack
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback, limit=1000)
                msg = ''.join(lines).strip()
            else:
                # the msg Exception is not the most recent, so no traceback for this exception
                self.debug('log.debug() called with an exception but no traceback available')
                msg = traceback.format_exception_only(type(msg), msg)
                
            self.log('DEBUG', msg)

        else:
            self.log('DEBUG', msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        ''' Compatibility with standard python logging. '''

        self.log('WARNING', msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        ''' Compatibility with standard python logging. '''

        self.log('ERROR', msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        ''' Compatibility with standard python logging.

            Utility function to support log.debug(), etc.
            Called as self.log('DEBUG', ...), self.log('INFO', ...), etc.
        '''

        if len(kwargs.keys()):
            args = args + (kwargs,)
        if len(args):
            message = msg.format(*args)
        else:
            message = msg

        try:
            try:
                level.encode('utf-8')
            except UnicodeDecodeError:
                level = ''

            try:
                if IS_PY2:
                    message = unicode(message, encoding='utf-8', errors='replace')
                else:
                    if isinstance(message, Exception):
                        message = str(message)
                    elif isinstance(message, bytes) or isinstance(message, bytearray):
                        message = message.decode(errors='replace')
            except TypeError:
                # don't change message. but would it be better to still encode as utf8?
                pass
            except UnicodeDecodeError:
                message = '-- message contains unprintable characters --'

            self.write('{} {}'.format(level, message))

        except Exception:
            self.last_exception()

    def logger_debug(self, message):
        try:
            try:
                message.encode('utf-8', errors='replace')
            except UnicodeDecodeError:
                message = '-- message contains unprintable characters --'

            self.logger.debug(message)

        except:
            _debug(message, force=True)
            self.last_exception()

    def open(self):
        '''Open the file for appending.
           Set the permissions.'''

        if not self.opened:

            self.pathname = get_log_path(filename=self.filename, dirname=self.dirname)
            # filename and dirname have likely changed
            self.filename = os.path.basename(self.pathname)
            self.dirname = os.path.dirname(self.pathname)
            if self.recreate and os.path.exists(self.pathname):
                if _DEBUGGING_LOG_REMOVE_DISABLE:
                    _debug('_DEBUGGING_LOG_REMOVE_DISABLE disabled: __init__() removing {}'.format(self.pathname)) #DEBUG
                else:
                    os.remove(self.pathname)

            makedir(self.dirname)

            if self.user not in _master_logs:
                _master_logs[self.user] = get_log('master.log', dirname=self.dirname)

            try:
                self.handler = CustomFileHandler(self.pathname, encoding = 'UTF-8')
            except IOError:
                import syr.fs
                why = syr.fs.why_file_permission_denied(self.pathname, mode='w')
                _debug(
                    'Could not log to {}. {}. Check if get_log() was called as a different user.'.
                    format(self.pathname, why), force=True)
                raise
            else:
                formatter = logging.Formatter("%(asctime)s %(message)s")
                self.handler.setFormatter(formatter)
                self.handler.setLevel(logging.DEBUG)

            name = self.filename
            if name.endswith('.log'):
                name = name[:-4]
            self.logger = logging.getLogger(name)
            self.logger.addHandler(self.handler)

            try:
                os.chmod(self.pathname, _DEFAULT_PERMS)
            except:
                self.last_exception()

            # try to match the file group to the owner
            """
            try:
                # why doesn't this error show in the logs?
                os.chgrp(pathname, self.user)
            except:
                self.last_exception()
            """

            self.opened = True

    def flush(self):
        ''' Flush the current buffer by closing and opening the log. '''

        if self.opened and self.handler is not None:
            self.handler.flush()

    def close(self):
        ''' Close the log. '''

        if self.opened and self.handler is not None:
            self.handler.close()
            self.opened = False

    def is_master(self):
        ''' Return whether this log is a master log. '''

        if self.user is None:
            self.user = syr._log.whoami()
        if self.user is None:
            master = False
        else:
            master = self == _master_logs[self.user]

        return master

    def last_exception(self, message=None):
        ''' Try to notify of last exception.

            We don't want to stop a program because of a log error
        '''

        import syr.python

        try:
            _debug(syr.python.last_exception(), force=True)
        except:
            pass

        try:
            if message:
                self.write(message)
        except:
            pass

    def check_user(self):
        ''' Detect user changed.

            Each user has its own separate set of logs.
        '''

        current_user = syr._log.whoami()
        if self.user is None:
            self.user = current_user
        elif self.user != current_user:
            msg = 'Log user changed from {} to {}.'.format(self.user, current_user)
            _debug(msg, force=True)
            self.user = current_user
            # the next write() should open the log as the right user
            self.close()

def get_log(filename=None, dirname=None, group=None, recreate=False, verbose=False):    
    ''' get_log() is the deprecated name for open(). '''
    
    return open(filename=filename, dirname=dirname, group=group, recreate=recreate, verbose=verbose)

def open(filename=None, dirname=None, group=None, recreate=False, verbose=False):
    ''' Open log. Default is a log for the calling module.
    
        The default log path is "BASE_LOG_DIR/USER/MODULE.log".
        If filename is specified and starts with a '/', it is the log path.
        If filename is specified and does not start with a '/', it replaces "MODULE.log".
        If dirname is specified, it replaces "BASE_LOG_DIR/USER".

        Log instances are cached by pathname.

        If recreate=True and the log file is not already open, any existing 
        log file is removed.

        >>> import os.path
        >>> import syr.log

        >>> log = syr.log.open('testlog3.log')
        >>> log('log message')
        >>> user_log_dir = os.path.join(BASE_LOG_DIR, syr._log.whoami())
        >>> assert os.path.dirname(log.pathname) == user_log_dir

        >>> log = get_log('testlog1.log', dirname='/tmp/logs')
        >>> log('log message')
        >>> print(log.dirname)
        /tmp/logs

        >>> log = syr.log.open('/tmp/testlog2.log')
        >>> log('log message')
        >>> print(log.dirname)
        /tmp
    '''

    from syr.lock import locked
    with locked(_get_log_lock):

        logpath = get_log_path(filename=filename, dirname=dirname)

        if logpath in logs.keys():
            log = logs[logpath]

        else:
            log = _Log(
                filename=filename, dirname=dirname,
                group=group, recreate=recreate, verbose=verbose)
            logs[logpath] = log

    return log


def get_log_path(filename=None, dirname=None):
    ''' Returns log path.

        The default log path is "BASE_LOG_DIR/USER/MODULE.log".
        If filename is specified and starts with a '/', it is the log path.
        If filename is specified and does not start with a '/', it replaces "MODULE.log".

        >>> import os.path
        >>> from syr.log import get_log

        >>> path = get_log_path('testlog1.log', dirname='/tmp/logs')
        >>> assert os.path.basename(path) == 'testlog1.log'
        >>> assert os.path.dirname(path) == '/tmp/logs'

        >>> path = get_log_path('/tmp/testlog2.log')
        >>> assert os.path.basename(path) == 'testlog2.log'
        >>> assert os.path.dirname(path) == '/tmp'

        >>> path = get_log_path('testlog3.log')
        >>> assert os.path.basename(path) == 'testlog3.log'
        >>> assert os.path.dirname(path) == os.path.join(BASE_LOG_DIR, syr._log.whoami())
    '''

    if filename is None:
        from syr.python import caller_module_name
        filename = caller_module_name(ignore=[__file__])

    # sometimes we pass the filename of the caller so strip the end
    if filename.endswith('.py') or filename.endswith('.pyc'):
        filename, _, _ = filename.rpartition('.')

    filename = default_log_filename(filename)
    if dirname is None:
        dirname = default_log_dir()
    else:
        # no relative dir names
        assert dirname.startswith('/')

    logpath = os.path.join(dirname, filename)

    return logpath

def default_log_dir():
    '''
       We want to keep the logs together as much as possible,

       The default is /var/local/log/USER. This avoids log ownership conflicts.
    '''

    create_base_log_dir()
    user = syr._log.whoami()
    dirname = os.path.join(BASE_LOG_DIR, user)
    makedir(dirname)
    return dirname

def delete_all_logs(dirname=None):
    ''' Delete all files in dir. '''

    if not dirname:
        dirname = default_log_dir()

    if _DEBUGGING_LOG_REMOVE_DISABLE:
        _debug('_DEBUGGING_LOG_REMOVE_DISABLE disabled: delete_all_logs() removing {}'.format(dirname)) #DEBUG

    else:
        # don't delete dirname itself
        entries = glob(os.path.join(dirname, '*'))
        # make sure this dir has at least one log, i.e. is possibly a logs dir
        assert any(entry.endswith('.log') for entry in entries)
        for entry in entries:
            if os.path.isdir(entry):
                shutil.rmtree(entry)
            else:
                os.remove(entry)

def default_log_filename(name):
    ''' Make sure log filenames look like logs. '''
    if name.endswith('.log'):
        log_name = name
    else:
        log_name = '{}.log'.format(name)
    return log_name

def set_alert_addresses(from_address, to_address):
    '''Set the mail addresses to use if serious error detected while logging.
    '''

    alert_from_address = from_address
    alert_to_address = to_address

def create_base_log_dir():
    ''' Make sure BASE_LOG_DIR exists. '''

    if not os.path.exists(BASE_LOG_DIR):

        # BASE_LOG_DIR must be created by root
        if syr._log.whoami() != 'root':
            sys.exit('As root, run "mkdir --parents --mode={} {}", then chmod {} {}'.
                format(
                    oct(BASE_LOG_DIR_PERMS), BASE_LOG_DIR),
                oct(BASE_LOG_DIR_PERMS), BASE_LOG_DIR)

        os.makedirs(BASE_LOG_DIR, BASE_LOG_DIR_PERMS)
        # redo perms using chmod to avoid umask
        os.chmod(BASE_LOG_DIR, BASE_LOG_DIR_PERMS)

def makedir(dirname, perms=_DEFAULT_LOG_DIR_PERMS):
    if not os.path.exists(dirname):
        try:
            os.makedirs(dirname, perms)
        except:
            from syr.fs import why_file_permission_denied
            why = why_file_permission_denied(dirname, perms)
            print('syr.log: Could not create log dir: {}'.format(why), file=sys.stderr)
            _debug(why, force=True)
            raise
    assert os.path.isdir(dirname)

if __name__ == "__main__":

    import doctest
    doctest.testmod()
