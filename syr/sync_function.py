'''
    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-04-23

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals


from threading import RLock

_locks = {}
def lock_for_object(obj, locks=_locks):
    return locks.setdefault(id(obj), RLock())


def synchronized(call):
    def inner(*args, **kwds):
        with lock_for_object(call):
            return call(*args, **kwds)
    return inner


