'''
    Utility classes and functions.
    
    These generally need to be split into other packages.
    For example, many could go in syr.debug or syr.fs.
    But you need time to find and change the callers.

    Copyright 2009-2014 GoodCrypto
    Last modified: 2015-01-17

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from contextlib import contextmanager
from datetime import datetime, timedelta
from fnmatch import fnmatch
from functools import wraps
from glob import glob
from cStringIO import StringIO
import bz2, calendar, os, os.path, re, sh, string, sys, tempfile, types, zipfile
import gzip as gz
import threading, trace, traceback
import re, time, types, unicodedata, urlparse

from syr.python import object_name
from syr.times import timedelta_to_human_readable
from syr.lock import locked

# we can't use syr.log here because syr.log uses this module
_debug = False
if _debug:
    def log(msg):
        print(msg)
else:
    def log(msg):
        pass

prefered_encoding = 'utf-8'

Http_Separator = '://'


_synchronized_master_lock = threading.Lock()
_synchronized_locks = {}

_cached_return_values = {}

# linux allows almost any characters, but this is cross platform pathnames
valid_pathname_chars = "-_.()/\\: %s%s" % (string.ascii_letters, string.digits)


class NotImplementedException(Exception):
    ''' Operation not implemented exception. '''
    pass

class MovedPermanentlyException(Exception):
    ''' Object moved permanently exception. 
    
        Always say where it was moved. '''
    pass

def set_default_encoding(encoding=prefered_encoding):

    try:
        sys.setdefaultencoding(encoding)
    except AttributeError:
        '''Already used by the site module, which removes it from sys namespace'''
        pass


def get_scheme_netloc(url):
    ''' Return (scheme, netloc) from url.
    
        If the port is non-standard, the netloc is 'domain:port'. Otherwise 
        netloc is the domain.

       This is used because python 2.4 and 2.5
       give slightly different results from urlparse.

        >>> get_scheme_netloc('http://goodcrypto.com')
        ('http', 'goodcrypto.com')
        >>> get_scheme_netloc('https://test:8211')
        ('https', 'test:8211')
    '''

    parsed_url = urlparse.urlparse(url)
    try:
        scheme = parsed_url.scheme
        netloc = parsed_url.netloc
    except:
        scheme = parsed_url[0]
        netloc = parsed_url[1]

    return (scheme, netloc)


def get_remote_ip(request):
    '''Get the remote ip. If there is a forwarder, assume the first IP 
       address (if there are more than 1) is the original machine's address.
       
       Otherwise, use the remote addr.
       
       Any errors, return 0.0.0.0
    '''

    Unknown_IP = '0.0.0.0'
    
    if request:
        try:
            # if we're using a reverse proxy, the ip is the proxy's ip address
            remote_addr = request.META.get('REMOTE_ADDR', '')
            forwarder = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if forwarder and forwarder is not None and len(forwarder) > 0:
                m = re.match('(.*?),.*?', forwarder)
                if m:
                    remote_ip = m.group(1)
                else:
                    remote_ip = forwarder
            else:
                remote_ip = remote_addr
        
            if not remote_ip or remote_ip is None or len(remote_ip) <= 0:
                remote_ip = Unknown_IP
        except:
            log(traceback.format_exc())
            remote_ip = Unknown_IP
    else:
        remote_ip = Unknown_IP
        log('no request so returning unknown ip address')
        
    return remote_ip

def stacktrace():
    'Returns a printable stacktrace.'

    stack = traceback.extract_stack()[:-1]
    lines = traceback.format_list(stack)
    return 'Traceback (most recent call last):\n' + ''.join(lines)

def last_exception(noisy=False):
    ''' Returns a printable string of the last exception.

        If noisy=True calls say() with last_exception_only(). '''

    if noisy:
        say(last_exception_only())
    return traceback.format_exc()

def last_exception_only():
    ''' Returns a printable string of the last exception without a traceback. '''

    type, value, traceback = sys.exc_info()
    if type:
        s = str(type).split('.')[-1].strip('>').strip("'")
        if value != None and len(str(value)):
            s += ': %s' % value
    else:
        s = ''
    return s
    
def get_module(name):
    ''' Get the module based on the module name. 
    
        The module name is available within a module as __name__. 
        
        >>> get_module(__name__) # doctest: +ELLIPSIS 
        <module '...' from '...utils.py...'>
    ''' 
        
    return sys.modules[name]
    
def caller_dir():
    ''' Get the caller's dir. 
    
        This is actually the source dir for the caller of the caller of this module.
    '''
    
    stack = traceback.extract_stack()[:-2]
    (filename, line_number, function_name, text) = stack[0]
    return os.path.dirname(filename) or os.getcwd()
    
def caller_file():
    ''' Get the caller's file. 
    
        This is actually the source file for the caller of the caller of this module.
    '''
    
    stack = traceback.extract_stack()[:-2]
    (filename, line_number, function_name, text) = stack[0]
    return filename
    
def get_absolute_url(url, home_url, request=None):
    ''' Return an absolute url from a relative url
        adapting for protocol if request included.'''

    final_home_url = home_url
    
    if url.startswith('/'):
        url = url[1:]

    try:
        if request is not None and request.META.get('HTTP_REFERER') is not None:
            # use the same protocol for the new url
            referer = requestMETA.get('HTTP_REFERER')
            if (referer.find('://' + TOP_LEVEL_DOMAIN) > 0 and
                referer.lower().startswith('https')):
                index = final_home_url.find('://')
                if index >= 0:
                    final_home_url = 'https' + final_home_url[index]
                    log('final url: {}'.format(final_home_url))
    except:
        pass

    return urlparse.urljoin(final_home_url, url)

def say(message):
    ''' Speak a message.

        Runs a "say" program, passing the message on the command line.
        Because most systems are not set up for speech, it is not an
        error if the "say" program is missing or fails.

        It is often easy to add a "say" program to a system. For example,
        a linux system using festival for speech can use a one line script:
            festival --batch "(SayText \"$*\")"

        Depending on the underlying 'say' command's implementation, say()
        probably does not work unless user is in the 'audio' group.
        
        >>> say('test say')
        '''
        
    enabled = True
    
    if enabled:
        try:
            #log('say "%s"' % message)
            #if _debug: log(stacktrace())
            #log(last_exception())
            # the words are unintelligible, and usually all we want is to know something happened
            # message = 'tick' # just a sound #DEBUG
            # os.system passes successive lines to sh
            message = message.split('\n')[0]
            sh.say(*message)
        except:
            pass

def synchronized(function):
    ''' Decorator to lock a function so each call completes before
        another call starts.

        If you use both the staticmethod and synchronized decorators,
        @staticmethod must come before @synchronized. '''

    @wraps(function)
    def synchronizer(*args, **kwargs):
        ''' Lock function access so only one call at a time is active.'''

        # get a shared lock for the function
        with locked(_synchronized_master_lock):
            lock_name = object_name(function)
            if lock_name in _synchronized_locks:
                lock = _synchronized_locks[lock_name]
            else:
                lock = threading.Lock()
                _synchronized_locks[lock_name] = lock

        with locked(lock):
            result = function(*args, **kwargs)

        return result

    return synchronizer

def pdb_break():
    ''' Breakpoint for pdb command line debugger.

    Usage:
        from syr import pdb_break ; pdb_break()
    '''

    import pdb
    log('breakpointing for pdb')
    pdb.set_trace()

def winpdb_break():
    ''' Breakpoint for winpdb debugger.

        Example:
            from syr import winpdb_break; winpdb_break() #DEBUG
    '''

    import rpdb2 #DEBUG
    log('breakpointing for winpdb')
    rpdb2.start_embedded_debugger("password") #DEBUG

def cache(function):
    ''' Decorator to cache returned value.
        Use @cache for expensive calculations that should only run once.

        >>> @cache
        ... def test():
        ...     import random
        ...     return random.random()

        >>> a = test()
        >>> b = test()
        >>> assert a == b
    '''

    @wraps(function)
    def cacher(*args, **kwargs):
        ''' Cache returned value.'''

        @synchronized
        def get_value():
            key = object_name(function)
            if key in _cached_return_values:
                value = _cached_return_values[key]
            else:
                value = function(*args, **kwargs)
                _cached_return_values[key] = value

        return get_value()

    return cacher

def exec_trace(code, ignoredirs=[sys.prefix, sys.exec_prefix], globals=None, locals=None, coverdir='/tmp'):
    ''' Trace code.

        Code must be a string. Code must start at column 1 in the string.

        exec_trace() usually requires passing "globals=globals(), locals=locals()".

        Example:
            from syr import exec_trace
            exec_trace("""
from jean.events import log_event
log_event(name, request=request, details=details)
                """,
                globals=globals(), locals=locals())
        '''

    tracer = trace.Trace(ignoredirs=ignoredirs)
    tracer.runctx(code.strip(), globals=globals, locals=locals)
    r = tracer.results()
    r.write_results(show_missing=True, coverdir=coverdir)

def clean_pathname(pathname):
    ''' Clean a pathname by removing all invalid chars.

        See http://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-pathname-in-python
        From that page, roughly:

            The unicodedata.normalize call replaces accented characters
            with the unaccented equivalent, which is better than simply
            stripping them out. After that all disallowed characters are
            removed. Doesn't avoid possible disallowed pathnames."
    '''

    ascii_pathname = unicodedata.normalize('NFKD', unicode(pathname)).encode('ASCII', 'ignore')
    return ''.join(c for c in ascii_pathname if c in valid_pathname_chars)


def strip_input(data):
    '''Strip the leading and trailing spaces.'''

    try:
        if data is not None:
            if isinstance(data, basestring) or isinstance(data, CharField):
                data = data.strip()

            elif isinstance(data, EmailField):
                data = '%s' % data
                data = data.strip()
    except:
        log(traceback.format_exc())

    return data
    
    
def trace_func(frame, event, arg):
    ''' NOT WORKING - Log trace of python code.

        Usage:
            import sys

            old_trace = sys.gettrace()
            sys.settrace(trace)

            ... code to trace ...

            sys.settrace(old_trace)

        See python tracing a segmentation fault
            http://stackoverflow.com/questions/2663841/python-tracing-a-segmentation-fault

        >>> def test():
        ...     print "Line 8"
        ...     print "Line 9"
        >>> import sys
        >>> old_trace = sys.gettrace()
        >>> # NOT WORKING - sys.settrace(trace_func)
        >>> test()
        Line 8
        Line 9
        >>> sys.settrace(old_trace)
    '''

    print('trace: %(event)-12s %(filename)s:%(lineno)d' % {
        'event': event,
        'filename': frame.f_code.co_filename,
        'lineno': frame.f_lineno })
    return trace


def pipe(value, *fns):
    ''' Pipe data from functions a() to b() to c() to d() ...

        "pipe(x, a, b, c, d)" is more readble than "d(c(b(a(x))))".

        See http://news.ycombinator.com/item?id=3349429

        pipe() assumes every function in its list will consume and return the data.
        If you need more control such as filtering and routing, see
        the syr.coroutine package.

        >>> def sqr(x):
        ...     return x*x

        >>> def half(x):
        ...     return x/2.0

        >>> for i in range(5):
        ...     pipe(i, sqr, half)
        0.0
        0.5
        2.0
        4.5
        8.0
    '''

    for fn in fns:
        value = fn(value)
    return value

def ltrim(string, prefix):
    ''' Trim all prefixes from string. '''

    length = len(prefix)
    while string.startswith(prefix):
        string = string[length:]
    return string

def rtrim(string, suffix):
    ''' Trim all suffixes from string. '''

    length = len(suffix)
    while string.endswith(suffix):
        string = string[:-length]
    return string

def trim(string, xfix):
    ''' Trim all prefixes or suffixes of xfix from string. '''

    length = len(xfix)
    while string.startswith(xfix):
        string = string[length:]
    while string.endswith(xfix):
        string = string[:-length]
    return string

def remove_lines(string, count):
    ''' Remove lines from string.

        If count is negative, removes lines from end of string. '''

    if count > 0:
        string = '\n'.join(string.split('\n')[count:])
    elif count < 0:
        string = '\n'.join(string.split('\n')[:count])
    return string

def pathmatch(path, pattern):
    ''' Test whether the path matches the pattern.
    
        This is a mess that needs to be replaced with an ant-style path match.

        The pattern is a shell-style wildcard, not a regular expression.
        fnmatch.fnmatch tests filenames, not paths. 
        
        '**' at the beginning of a pattern matches anything at the beginning 
        of a path, but no other wildcards are allowed in the pattern. '''

    def split(path):
        path = os.path.expanduser(path)
        path = os.path.abspath(path)
        return path.split('/')

    if pattern.startswith('**'):
        result = path.endswith(pattern[2:])
    
    else:
        path = split(path)
        pattern = split(pattern)
        result = (len(path) == len(pattern) and
            all(fnmatch(path[i], pattern[i]) for i in range(len(path))))
        
    return result

def resolve_path(path):
    ''' Resolves file path wildcards, links, and relative directories.

        To resolve a wildcard path that matches more than one file, use
        glob() and pass each result to resolve_path().

        Returns None if wildcard does not match any files. Raises
        ValueError if wildcard matches more than one file. '''

    paths = glob(path)
    if paths:
        if len(paths) > 1:
            raise ValueError('Matches more than one path: %s' % path)
            path = os.path.normpath(os.path.realpath(paths[0]))
    else:
        path = None
    return path

def domain_base(domain):
    ''' Returns base name from domain.

        I.e. base.tld or base.co.countrydomain or base.com.countrydomain
        all have the same base name.

        E.g. google.com, google.bg, google.de, google.co.in all are based
        on google.

        This can be fooled by domain spoofers or squatters. '''

    # regexes might be clearer (or not) but would be slower
    parts = domain.split('.')
    if len(parts) > 1:
        # toss the top level domain
        parts = parts[:-1]
        if len(parts) > 1:
            # toss generic second level domains
            if parts[-1] in ['com', 'co', 'org', 'net']:
                parts = parts[:-1]
    # top level left is the base name
    return parts[-1]
     
class textfile(object):
    ''' Open possibly gzipped text file as file using contextmanager.
    
        E.g. "with textfile('mytext.gz') as f".
    
        Avoids "AttributeError: GzipFile instance has no attribute '__exit__'"
        prior to Python 3.1. 
        
        As of Python 2.6 contextlib.closing() doesn't work. It doesn't expose underlying 
        gzip functions because its __enter__() returns the inner object, and it has no 
        __getattr__()
        to expose the inner gzip.open(). '''
    
    def __init__(self, filename, rwmode='r'):
        if filename.endswith('.gz'):
            self.f = gz.open(filename, '%sb' % rwmode)
        elif filename.endswith('.bz2'):
            self.f = bz2.BZ2File(filename, '%sb' % rwmode)
        elif filename.endswith('.zip'):
            self.f = zipfile.ZipFile(filename, '%sb' % rwmode)
        else:
            self.f = open(filename, rwmode)
        self.opened = True
            
    def __iter__(self):
        return iter(self.f)
        
    def __enter__(self):
        return self.f
        
    def __exit__(self, *exc_info):
        self.close()
        
    def unused_close(self):
        if self.opened:
            self.f.close()
            self.opened = False
    
    def __getattr__(self, name):
        return getattr(self.f, name)
        
def gzip(uncompressed):
    ''' Gzip a string '''
    
    compressed_fileobj = StringIO()
    with gz.GzipFile(fileobj=compressed_fileobj, mode='w') as f:  #, compresslevel=5) as f:
        f.write(uncompressed)
    return compressed_fileobj.getvalue()
 
def gunzip(compressed):
    ''' Gunzip a string '''

    compressed_fileobj = StringIO(compressed)
    with gz.GzipFile(fileobj=compressed_fileobj, mode='r') as f:
        uncompressed = f.read()
    return uncompressed

@contextmanager
def chdir(dirname=None):
    ''' Chdir contextmanager that restores current dir. 
    
        From http://www.astropython.org/snippet/2009/10/chdir-context-manager 

        This context manager restores the value of the current working 
        directory (cwd) after the enclosed code block completes or 
        raises an exception.  If a directory name is supplied to the 
        context manager then the cwd is changed prior to running the 
        code block.
    '''
        
    curdir = os.getcwd()
    try:
        if dirname is not None:
            os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)

def different(file1, file2):
    ''' Returns whether the files are different. '''
    
    # diff succeeds if there is a difference, and fails if no difference
    try:
        sh.diff(file1, file2, brief=True)
        different = False
            
    except sh.ErrorReturnCode:
        different = True
        
    return different        

def slugify(value):
    ''' Converts string to a form usable in a url withjout encoding. 
    
        Strips white space from ends, converts to lowercase, 
        converts spaces to hyphens, and removes non-alphanumeric characters.
    '''
    value = value.strip().lower()
    value = re.sub('[\s-]+', '-', value)
    
    newvalue = ''
    for c in value:
        if (
              (c >= 'A' and c <= 'Z') or 
              (c >= 'a' and c <= 'z') or 
              (c >= '0' and c <= '9') or
              c == '-' or
              c == '_'
              ):
            newvalue += c 
    return newvalue
    
def is_class_instance(obj):
    ''' Returns whether the object is an instance of a class. 
    
        You can't reliably detect a class instance with
        
            isinstance(obj, types.InstanceType)
            
        as of Python 2.6 2013-05-02. The types module only handles old style
        python defined classes, so types.InstanceType only detects instances 
        of the same style.
        
        >>> import datetime
        >>> c_style_class_instance = datetime.date(2000, 12, 1)
        >>> is_class_instance(c_style_class_instance)
        True
         
        >>> class OldStyleClass:
        ...     class_data = 27
        ...
        ...     def __init__(self):
        ...         self.instance_data = 'idata'
        
        ...     def instance_function(self):
        ...         return 3
        >>> old_c = OldStyleClass()
        >>> is_class_instance(old_c)
        True
        
        >>> class NewStyleClass(object):
        ...     class_data = 27
        ...
        ...     def __init__(self):
        ...         self.instance_data = 'idata'
        
        ...     def instance_function(self):
        ...         return 3
        >>> new_c = NewStyleClass()
        >>> is_class_instance(new_c)
        True
        
        >>> # base types are not instances
        >>> is_class_instance(2)
        False
        >>> is_class_instance([])
        False
        >>> is_class_instance({})
        False
         
        >>> # classes are not instances
        >>> is_class_instance(datetime.date)
        False
        >>> is_class_instance(OldStyleClass)
        False
        >>> is_class_instance(NewStyleClass)
        False
        
        >>> # test assumptions and python imlementation details
        
        >>> type(2)
        <type 'int'>
        >>> type([])
        <type 'list'>
        >>> type({})
        <type 'dict'>
        
        >>> cls = getattr(2, '__class__')
        >>> cls
        <type 'int'>
        >>> superclass = getattr(cls, '__class__')
        >>> superclass
        <type 'type'>
        
        >>> str(type(datetime.date))
        "<type 'type'>"
        >>> str(type(c_style_class_instance))
        "<type 'datetime.date'>"
        >>> repr(datetime.date)
        "<type 'datetime.date'>"
        >>> repr(c_style_class_instance)
        'datetime.date(2000, 12, 1)'
        >>> isinstance(c_style_class_instance, types.InstanceType)
        False
        >>> hasattr(c_style_class_instance, '__class__')
        True
        >>> '__dict__' in dir(c_style_class_instance)
        False
        >>> cls = c_style_class_instance.__class__
        >>> hasattr(cls, '__class__')
        True
        >>> '__dict__' in dir(cls)
        False
        >>> hasattr(cls, '__slots__')
        False
        >>> cls = getattr(c_style_class_instance, '__class__')
        >>> cls
        <type 'datetime.date'>
        >>> superclass = getattr(cls, '__class__')
        >>> superclass
        <type 'type'>
        
        >>> '__dict__' in dir(old_c)
        False
        >>> hasattr(old_c, '__slots__')
        False
        
        >>> '__dict__' in dir(new_c)
        True
        >>> hasattr(new_c, '__slots__')
        False
        
        '''
       
    type_str = str(type(obj))
    
    # old style python defined classes
    if type_str == "<type 'instance'>":
            is_instance = True

    # C defined classes
    elif type_str.startswith('<type '):
        # base types don't have a dot
        is_instance =  '.' in type_str
        
    # new style python defined classes
    elif type_str.startswith('<'):
        # if it has an address, it's an instance, not a class
        is_instance =  ' 0x' in repr(obj)
                    
    else:
        is_instance = False
    
    return is_instance
    
    """ does not detect c-style classes e.g. datetime.xyz
    def is_old_style_instance(obj):
        return isinstance(obj, types.InstanceType)
        
    def is_new_style_instance(obj):
        # http://stackoverflow.com/questions/14612865/how-to-check-if-object-is-instance-of-new-style-user-defined-class
        is_instance = False
        if hasattr(obj, '__class__'):
            cls = obj.__class__
            if hasattr(cls, '__class__'):
                is_instance = ('__dict__' in dir(cls)) or hasattr(cls, '__slots__')
        return is_instance
       
    return is_new_style_instance(obj) or is_old_style_instance(obj)
    """

def replace_strings(text, replacements, regexp=False):
    """ Replace text. Returns new text. 
    
        'replacements' is a dict of {old: new, ...}.
        Every occurence of each old string is replaced with the 
        matching new string.
        
        If regexp=True, the old string is a regular expression.
        
        >>> text = 'ABC DEF 123 456'
        >>> replacements = {
        ...     'ABC': 'abc',
        ...     '456': 'four five six'
        ... }
        >>> replace_strings(text, replacements)
        'abc DEF 123 four five six'
    """
        
    for old in replacements:
        new = replacements[old]
        if regexp:
            text = re.sub(old, new, text)
        else:
            text = text.replace(old, new)
    return text

def caller_module_name(ignore=None, syr_utils_valid=False):
    raise MovedPermanentlyException('moved to syr.python')
            
def run(command, expected_output=None, verbose=False, quiet=False, no_stdout=False, raise_exception=False):
    ''' Runs the command.

        Returns True iff:
            1. The return code is zero.
            2. There was no stderr output.
            3. Any expected output appears at the end of stdout.
        Otherwise returns False.
        Note that any warnings to stderr result in False.

        To get the output from a command see get_command_output().

        If verbose is True, print the command to stderr.

        If quiet is True, don't print details of why command failed, just
        print a message with the return code. By default run() prints why a
        command failed to stderr. Quiet implies not verbose.
        
        If no_stdout is True, don't print stdout.
        
        If raise_exception is True and the command fails, raise an 
        exception instead of returning False.
    '''
    
    class RunFailed(Exception):
        pass

    def report_failure(why):
        if not quiet:
            message = 'command "%s" failed: %s' % (command, why)
            print >> sys.stderr, message
            log(message)
            
    raise Exception('Deprecated. Use the sh module.')

    import subprocess
    
    if no_stdout:
        verbose = False

    if verbose and not quiet:
        print command

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = process.communicate()

    if not no_stdout:
        if stdout:
            stdout = stdout.rstrip()
            print stdout
        if stderr:
            stderr = stderr.rstrip()
            print stderr

    # a return code of zero is success in linux, anything else is failure
    if process.returncode:
        msg = 'exit status %d' % process.returncode
        report_failure(msg)
        success = False 
        if raise_exception:
            raise RunFailed, msg
            
    elif stderr:
        success = False
        if raise_exception:
            raise RunFailed, 'stderr: %s' % stderr.rstrip()
        
    elif expected_output and not (
        stdout and stdout.endswith(expected_output)):
        msg = 'expected "%s", got "%s"' % (expected_output, command_output)
        report_failure(msg)
        success = False
        if raise_exception:
            raise RunFailed, msg
        
    else:
        success = True
       
    return success

def run2(command, check=True, timeout=None, *args, **kwargs):
    ''' Run a command.
    
        If check=True (the default), 
        then if return code is not zero or there is stderr output, 
        raise CalledProcessError. Return any output in the exception. 
        
        If timeout (in seconds) is set and command times out, raise TimeoutError. '''
    
    ''' Parts from subprocess32.check_output(). '''
    
    raise Exception('Deprecated. Use the sh module.')
    
    # use subprocess32 for timeout
    from subprocess32 import Popen, CalledProcessError, TimeoutExpired
    
    process = Popen(command, stdout=stdout, stderr=stderr, *args, **kwargs)
    try:
        process.wait(timeout=timeout)
    except TimeoutExpired:
        print('TimeoutExpired') #DEBUG
        #print('stdout: %s, (%d)' % (str(stdout), len(str(stdout)))) #DEBUG
        #print('stderr: %s, (%d)' % (str(stderr), len(str(stderr)))) #DEBUG
        try:
            process.kill()
            process.wait()
        finally:
            print('after kill/wait') #DEBUG
            #print('stdout: %s, (%d)' % (str(stdout), len(str(stdout)))) #DEBUG
            #print('stderr: %s, (%d)' % (str(stderr), len(str(stderr)))) #DEBUG
            raise TimeoutExpired(process.args, timeout)
        
    if check:
        retcode = process.poll()
        if retcode:
            raise CalledProcessError(retcode, process.args)
            
def get_command_output(command, quiet=False):
    ''' Runs the command. Returns stdout.

        On linux you can use commands.getoutput() and commands.getstatusoutput().

        If quiet is True, don't print stderr.
    '''
    
    raise Exception('Deprecated. Use the sh module.')

    import subprocess

    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)

    (stdout, stderr) = process.communicate()

    if stderr and not quiet:
        stderr = stderr.rstrip()
        print >> sys.stderr, stderr

    return stdout
    
def delete_empty_files(directory):
    ''' Delete empty files in directory.
    
        Does not delete any subdirectories or files in them.
    
        >>> directory = tempfile.mkdtemp()
        >>> assert os.path.isdir(directory)
        
        >>> handle, filename1 = tempfile.mkstemp(dir=directory)
        >>> os.close(handle)
        >>> assert os.path.exists(filename1)
        >>> handle, filename2 = tempfile.mkstemp(dir=directory)
        >>> os.close(handle)
        >>> assert os.path.exists(filename2)
        
        >>> with open(filename2, 'w') as f2:
        ...     f2.write('data')
        
        >>> delete_empty_files(directory)
        >>> assert not os.path.exists(filename1)
        >>> assert os.path.exists(filename2)
        
        >>> os.remove(filename2)
        >>> assert not os.path.exists(filename2)
        >>> os.rmdir(directory)
        >>> assert not os.path.isdir(directory)
    '''

    wildcard = os.path.join(directory, '*')
    for filename in glob(wildcard):
        if os.path.getsize(filename) <= 0:
            os.remove(filename)

def dynamically_import_module(name):
    raise MovedPermanentlyException('moved to syr.python')

def dynamic_import(name):
    raise MovedPermanentlyException('moved to syr.python')

def randint(min=None, max=None):
    ''' Get a random int.
    
        random.randint() requires that you specify the min and max of 
        the integer range for a random int. But you almost always want 
        the min and max to be the system limits for an integer. 
        If not use random.randint(). 
    
        'min' defaults to system minimum integer.
        'max' defaults to system maximum integer.
    '''
    
    import sys, random
    
    if min is None:
        min = -(sys.maxint-1)
    if max is None:
        max = sys.maxint
    
    return random.randint(min, max)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
