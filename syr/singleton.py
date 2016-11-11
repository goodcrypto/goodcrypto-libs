'''
    Singletons.

    A singleton is a class that has at most one instance. The instance is
    also called a singleton.

    Example:

        only_instance = singleton(MySingletonClass)

    Use singleton() where you would use a class instantiation. Pass any
    class instantion parameters to singleton() after the class. The instance
    is created if needed, or returned if it already exists.

    If you need instances of your class in addition to the singleton
    instance, instantiate them using the standard python syntax.

    This module is thread safe.

    Copyright 2010-2016 GoodCrypto
    Last modified: 2016-06-23

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

from contextlib import contextmanager
import os
import socket
import sys
import threading

from syr.python import last_exception, last_exception_only
from syr.utils import synchronized
from syr.log import get_log
from syr.lock import locked

IS_PY2 = sys.version_info[0] == 2
log = get_log()

_class_locks = {}
_instances = {}

def singleton(singleton_class, *args, **kwargs):
    ''' Returns the instance of a singleton class.

        WARNING: Each caller must import the singleton_class in exactly the
        same way. Otherwise e.g. __main__.MyClass will be considered different
        from mypackage.mymodule.MyClass.

        A single instance of the class is created the first time singleton()
        is called with that particular class as singleton_class. The params
        and kwargs are ignored on subsequent calls.'''

    @synchronized
    def _get_class_lock():

        global _class_locks

        try:
            class_lock = _class_locks[singleton_class]

        except:
            class_lock = threading.Lock()
            _class_locks[singleton_class] = class_lock

        return class_lock


    global _instances

    class_lock = _get_class_lock()
    with locked(class_lock):

        try:
            instance = _instances[singleton_class]

        except:
            instance = singleton_class(*args, **kwargs)
            _instances[singleton_class] = instance

    return instance

def have_singleton(instance):
    ''' Returns whether the instance is from singleton(). '''

    return instance in _instances

def port_singleton(port):
    ''' Port singleton.

        Return True if this program, represented by a port, is a singleton.

        Using ports to create singletons is portable even to Windows.
        Only one program can listen on a port at a time. Each singleton
        must pick a unique port to identify the singleton. When the program
        ends, the port is automatically closed.

        # DOCTEST NOT WORKING
        >>> import sh
        >>> import time
        >>> program_prefix = '/tmp/test_syr_singleton'
        >>> program_suffix = '.py'
        >>> program1 = program_prefix + '1' + program_suffix
        >>> program2 = program_prefix + '2' + program_suffix
        >>> code = ['import time',
        ...         'import syr.singleton',
        ...         'port = 53772',
        ...         'syr.singleton.log.debug("call syr.singleton.system_singleton(port={})".format(port))',
        ...         'is_singleton = syr.singleton.port_singleton(port)',
        ...         'syr.singleton.log.debug("called syr.singleton.system_singleton(port={})".format(port))',
        ...         'print(is_singleton)',]
        >>> code = '\\n'.join(code) + '\\n'
        >>> for program in (program1, program2):
        ...     with open(program, 'w') as f:
        ...         f.writelines(code)
        >>> with open(program1, 'a') as f:
        ...     f.write('time.sleep(20)' + '\\n')
        >>> log.debug('start program1')
        >>> # sh.python(..., _bg=True) doesn't seem to work here
        >>> sh.python(program1, _bg=True)
        >>> # sh.bash('-c', 'python {}'.format(program1), '&')
        >>> log.debug('start program2')
        >>> log.debug('program2')
        >>> sh.python(program2, _bg=True)
        >>> # sh.bash('-c', 'python {}'.format(program2), '&')
        '''

    ALL_INTERFACES = ''

    log.debug('system_singleton() call socket.socket()')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        log.debug('system_singleton() call s.bind()')
        s.bind((ALL_INTERFACES, port))
        log.debug('system_singleton() call s.listen()')
        s.listen(1)
        # DELETE IF UNNEEDED conn, addr = s.accept()
        success = True
    except:
        success = False

    log.debug('system_singleton() success: {}'.format(success))
    return success

@contextmanager
def file_singleton(lockfile):
    ''' (Python 3 only.) File lock singleton.

        If file_singleton(lockfile) is called more than once with the same
        lockfile and before the first context is exited, raises FileExistsError.

        Caller must have write access to the lockfile.

        # DOCTEST NOT WORKING
        >>> LOCKFILE = '/tmp/syr.singleton.lockfile'
        >>> with file_singleton(LOCKFILE):
        ...     try:
        ...         with file_singleton(LOCKFILE):
        ...             raise Exception('syr.file_singleton() failed to detect nested call')
        ...     except FileExistsError:
        ...         pass
        >>> try:
        ...     with file_singleton(LOCKFILE):
        ...         pass
        ... except FileExistsError:
        ...     raise Exception('syr.file_singleton() failed to exit context')
    '''

    if IS_PY2:
        sys.exit('syr.file_singleton() requires python 3 or later')

    try:
        lock = io.FileIO(lockfile, 'x')


    except FileExistsError:
        raise

    else:
        lock.close()
        os.remove(lockfile)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
