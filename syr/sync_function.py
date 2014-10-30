'''
    Copyright 2014 GoodCrypto
    Last modified: 2014-01-08

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from threading import RLock

_locks = {}
def lock_for_object(obj, locks=_locks):
    return locks.setdefault(id(obj), RLock())


def synchronized(call):
    def inner(*args, **kwds):
        with lock_for_object(call):
            return call(*args, **kwds)
    return inner


