'''
    Locked threading.Lock context.

    Copyright 2011-2012 GoodCrypto
    Last modified: 2013-11-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import atexit, os, threading
from contextlib import contextmanager
from os import O_CREAT, O_EXCL, O_RDWR

@contextmanager
def locked(lock=None, blocking=1):
    ''' Context manager to acquire a lock.

        This is a lock within a process. See system_locked() for a system wide lock.

        You can't call threading.Lock.release() if the lock is unlocked.
        This context manager enforces that restriction painlessly by
        calling release automatically for you.

        >>> with locked():
        >>>     print 'this is a locked thread'
    '''

    if not lock:
        lock = threading.Lock()

    lock.acquire(blocking)

    try:
        yield

    finally:
        lock.release()

@contextmanager
def system_locked(name):
    ''' Context manager to acquire a system wide lock.
    
        'name' is typically '__module__' or '__file__'.

        See locked() for a lock within a process.

        The name must only contain characters allowed in filenames.

        Credit:
            Miki Tebeka
            <miki.tebeka at zoran.com>
            http://tebeka.bizhat.com
            http://mail.python.org/pipermail/python-win32/2005-February/002958.html

        >>> name = 'locktest'
        >>> with system_locked(name) as locked:
        >>>     if locked:
        >>>         print 'this is locked system wide'
        >>>     else:
        >>>         print 'another process or program has already locked %s' % name
        '''

    def lock():
        try:
            # try to remove any abandoned lockfile 
            os.remove(lockfile)
        except OSError: 
            # no abandoned lockfile
            pass
        
        try:
            lockfd = os.open(lockfile, O_CREAT|O_EXCL|O_RDWR)
            os.write(lockfd, '%d' % os.getpid())
        except OSError: # Already locked          
            lockfd = None
            
        return bool(lockfd)

    def unlock():
        if lockfd:
            try:
                try:
                    os.close(lockfd)
                except:
                    pass
                os.remove(lockfile)
                unlocked = True
            except OSError:
                unlocked = False
        else:
            unlocked = False
        return unlocked

    name = name.replace('/', '_').replace(' ', '_')

    lockfile = '/tmp/_%s_.lock' % name
    lockfd = None

    locked = lock()
    try:
        if locked:
            atexit.register(unlock)
        yield locked
    finally:
        if locked:
            unlock()
