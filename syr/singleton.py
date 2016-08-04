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

    Copyright 2010-2013 GoodCrypto
    Last modified: 2015-09-24

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''



import threading

from syr.python import last_exception, last_exception_only
from syr.utils import synchronized
from syr.log import get_log
from syr.lock import locked

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
