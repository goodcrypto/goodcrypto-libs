'''
    Dict utilities.

    Copyright 2013-2015 GoodCrypto
    Last modified: 2015-09-24

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import collections, datetime, types

from syr.format import pretty
from syr.log import get_log
from syr.python import last_exception, stacktrace, is_class_instance, object_name

global_debug = False
log = get_log()

class CaseInsensitiveDict(collections.Mapping):
    ''' Case insensitive dict.

        Dict lookups ignore key case. The key matches in lower, upper, or mixed case.

        Mostly from http://stackoverflow.com/questions/3296499/case-insensitive-dictionary-search-with-python
    '''

    def __init__(self, d=None):
        if d is None:
            d = {}
        self._d = d
        self._s = dict((k.lower(), k) for k in d)

    def __contains__(self, k):
        return k.lower() in self._s

    def __len__(self):
        return len(self._s)

    def __iter__(self):
        return iter(self._s)

    def __getitem__(self, k):
        return self._d[self._s[k.lower()]]

    def __setitem__(self, k, v):
        self._d[k] = v
        self._s[k.lower()] = k

    def __delitem__(self, k):
        del self._d[self._s[k.lower()]]
        del self._s[k.lower()]

    def pop(self, k):
        k0 = self._s.pop(k.lower())
        return self._d.pop(k0)

    def actual_key_case(self, k):
        return self._s.get(k.lower())

_dictify_references = set()
_unimplemented_types = set()
datetime_types = (datetime.timedelta, datetime.date, datetime.datetime, datetime.time)

def dictify(obj, deep=False, circular_refs_error=False, json_compatible=False, debug=False):
    ''' Resolves an object to a dictionary.

        If deep is True, recurses as needed. Default is False.

        Allowable object types are:
            NoneType,
            BooleanType,
            IntType, LongType, FloatType, ComplexType,
            StringTypes,
            TupleType, ListType, DictType,
            MethodType, FunctionType,
            GeneratorType,
            datetime.timedelta, datetime.date, datetime.datetime, datetime.time,
            class instances

        As of Python 2.6 2013-05-02 types.Instancetype is not reliable. We use
        syr.python.is_class_instance().

        A class instance is converted to a dict, with only data members and
        functions without parameters. Functions that require parameters (beyond self)
        are ignored. To convert a dict back to an object that accepts dot
        notation so you may not have to change your code, see
        syr.dict.DictObject(). Builtin instance member names beginning
        with '__' are ignored.

        dictify tries to use the current return value from methods.
        The method is called with no args (except self, i.e. the instance).
        We try a static method with no arguments. If these fail,
        the method is ignored.

        dictify converts a generator to a list. Warning: This may result in
        large, or even infinite, lists.

        With the default param circular_refs_error=False, circular references are
        replaced by None. If circular_refs_error=True, circular references
        raise a ValueError.

        json_compatible makes dictionary keys compatible with json, i.e. one of
        (str, unicode, int, long, float, bool, None).

        >>> class Test(object):
        ...     a = 1
        ...     b = 'hi'
        ...     def __init__(self):
        ...         self.c = 2
        ...         self.d = 'ho'
        ...         self.e = datetime.timedelta(weeks=1, days=2, hours=3,
        ...                                     minutes=4, seconds=5)
        ...         self.f = datetime.date(2000, 1, 2)
        ...         self.g = datetime.datetime(2000, 1, 2, 3, 4, 5, 6)
        ...         self.h = datetime.time(1, 2, 3, 4)

        >>> test = Test()
        >>> print pretty(dictify(test))
        {
        'a': 1,
        'b': 'hi',
        'c': 2,
        'd': 'ho',
        'e': {
        'days': 9,
        'microseconds': 0,
        'seconds': 11045,
        },
        'f': {
        'day': 2,
        'month': 1,
        'year': 2000,
        },
        'g': {
        'day': 2,
        'hour': 3,
        'microsecond': 6,
        'minute': 4,
        'month': 1,
        'second': 5,
        'tzinfo': None,
        'year': 2000,
        },
        'h': {
        'hour': 1,
        'microsecond': 4,
        'minute': 2,
        'second': 3,
        'tzinfo': None,
        },
        }

        >>> import datetime
        >>> d = datetime.date(2000, 12, 1)
        >>> print pretty(dictify(d))
        {
        'day': 1,
        'month': 12,
        'year': 2000,
        }

        >>> d = {datetime.date(2001, 12, 1): 1}
        >>> print pretty(dictify(d))
        {
        {'month': 12, 'day': 1, 'year': 2001}: 1,
        }

        >>> d = {1: datetime.date(2002, 12, 1)}
        >>> print pretty(dictify(d))
        {
        1: {
        'day': 1,
        'month': 12,
        'year': 2002,
        },
        }

        >>> class OldStyleClass:
        ...     class_data = 27
        ...
        ...     def __init__(self):
        ...         self.instance_data = 'idata'

        ...     def instance_function(self):
        ...         return 3
        >>> old_c = OldStyleClass()
        >>> print pretty(dictify(old_c))
        {
        'class_data': 27,
        'instance_data': 'idata',
        }

        >>> class NewStyleClass(object):
        ...     class_data = 27
        ...
        ...     def __init__(self):
        ...         self.instance_data = 'idata'

        ...     def instance_function(self):
        ...         return 3
        >>> new_c = NewStyleClass()
        >>> print pretty(dictify(new_c))
        {
        'class_data': 27,
        'instance_data': 'idata',
        }

    '''

    allowed_types = (
            types.NoneType,
            types.BooleanType,
            types.IntType, types.LongType, types.FloatType, types.ComplexType,
            # ?? StringTypes is itself a tuple; can we nest it like this?
            types.StringTypes,
            types.TupleType, types.ListType, types.DictType,
            types.InstanceType, types.MethodType, types.FunctionType,
            types.ModuleType,
            types.GeneratorType,
            ) + datetime_types

    def type_allowed(obj):
        return (isinstance(obj, allowed_types) or
            is_class_instance(obj))

    def check_circular_reference(obj):
        ''' Check for circular references to instances. '''

        global global_debug

        if (is_class_instance(obj)
            # do not check classes that we resolve specially
            and not isinstance(obj, datetime_types)):

            if id(obj) in _dictify_references:
                if global_debug: log('circular reference to %s, type %s' % (obj, type(obj)))
                if circular_refs_error:
                    raise ValueError('Circular reference to %r' % obj)
                else:
                    obj = None

            else:
                _dictify_references.add(id(obj))

        return obj

    def resolve_string(obj):
        ''' Return object if unicode, else return str().

            Starting with python 2.6 all strings are unicode.
            But for readability we use a plain string where possible. '''

        try:
            value = str(obj)
        except:
            value = unicode(obj)

        return value

    def resolve_datetime(obj):
        global global_debug

        if isinstance(obj, datetime.timedelta):
            value = DictObject({
                'days': obj.days,
                'seconds': obj.seconds,
                'microseconds': obj.microseconds,
                })
        elif isinstance(obj, datetime.datetime):
            value = DictObject({
                'year': obj.year,
                'month': obj.month,
                'day': obj.day,
                'hour': obj.hour,
                'minute': obj.minute,
                'second': obj.second,
                'microsecond': obj.microsecond,
                'tzinfo': obj.tzinfo,
                })
        elif isinstance(obj, datetime.date):
            value = DictObject({
                'year': obj.year,
                'month': obj.month,
                'day': obj.day,
                })
        elif isinstance(obj, datetime.time):
            value = DictObject({
                'hour': obj.hour,
                'minute': obj.minute,
                'second': obj.second,
                'microsecond': obj.microsecond,
                'tzinfo': obj.tzinfo,
                })
        else:
            value = None

        if global_debug: log('datetime obj: %r, type: %s, value: %r' % (obj, type(obj), value))
        return value

    def resolve_dict(obj, json_compatible=False):
        ''' Resolve a dict object. This is a deep resolve to a DictObject. '''

        global global_debug

        d = DictObject({})
        for key in obj:

            # a dictionary needs a hashable key
            try:
                new_key = resolve_obj(key)
                hash(new_key)
            except:
                new_key = '%s-%s' % (type(key), id(key))

            if json_compatible:
               # convert key to a json compatible type
               if not isinstance(new_key, (str, unicode, int, long, float, bool, None)):
                   new_key = repr(new_key)

            new_value = resolve_obj(obj[key])

            try:
                d[new_key] = new_value
            except TypeError: # e.g. unhashable type
                if global_debug:
                    log('resolving DictObject, got TypeError')
                    log('    key is %s, type %s' % (key, type(key)))
                    log('    new_key is %s, type %s' % (new_key, type(new_key)))
                    log('    obj[key] is %s, type %s' % (obj[key], type(obj[key])))
                    log('    new_value is %s, type %s' % (new_value, type(new_value)))
                    log(last_exception())
                d[key] = new_value

        return d

    def resolve_instance(obj):
        ''' Resolve an instance of a class. '''

        def log_needs_params(instance, name):
            if global_debug:
                log("instance %s method %s needs params, but we don't have them" %
                    (instance, name))
                log(last_exception())

        global global_debug #DEBUG

        d = DictObject({})

        # call the obj an instance for clarity here
        instance = obj
        # get names of instance attributes
        for name in dir(instance):
            # ignore builtins, etc.
            if not name.startswith('__'):

                # usually commented out - set debug to test special case
                #if name == 'previous_conversion': #DEBUG
                #    _old_debug = global_debug #DEBUG
                #    global_debug = True #DEBUG

                if global_debug: log('in resolve_obj() getting "%s" attribute "%s"' %
                    (repr(instance), name))

                try:
                    attr = getattr(instance, name)
                    if global_debug: log(
                        'in resolve_obj() instance: "%s", attribute: "%s", type: %s' %
                        (repr(instance), name, type(attr)))

                    # convert name to an allowed type
                    name = resolve_obj(name)

                    if type_allowed(attr):

                        # if this attr is a method object
                        if isinstance(attr, types.MethodType):
                            try:
                                if global_debug: log('%r is a MethodType' % attr)
                                # try calling it with no args (except self, i.e. the instance)
                                d[name] = resolve_obj(apply(attr, [instance]))
                            except:
                                log_needs_params(instance, name)

                        # if this attr is a static method object
                        elif isinstance(attr, types.FunctionType) and deep:
                            try:
                                if global_debug: log('%r is a FunctionType' % attr)
                                # this tries static methods that take no args
                                d[name] = resolve_obj(apply(attr, []))
                            except:
                                log_needs_params(instance, name)

                        else:
                            if global_debug: log('member %s.%r is an allowed type so resolving object' % (name, attr))
                            d[name] = resolve_obj(attr)

                    else:
                        if global_debug: log('in resolve_obj() type not allowed (%r)' % attr)

                except:
                    # these seem to be caused by using @property, making it hard to
                    # get a function attr without calling the function
                    if global_debug:
                        log('in resolve_obj() ignoring following exception')
                        log(last_exception())
                    pass

                # usually commented out - set debug to test special case
                #if name == 'previous_conversion': #DEBUG
                #    global_debug = _old_debug #DEBUG

        return d

    def resolve_module(module):
        ''' Resolve a module to a dict object. '''

        global global_debug

        d = DictObject({})
        for k, v in module.__dict__.items():
            if not k.startswith('__'):
                d[k] = v

        return d

    def resolve_obj(obj):
        ''' Resolve any type to a dict object. '''

        global global_debug

        #assert not debug #DEBUG
        # usually commented out - set debug locally to test special case
        # if isinstance(obj, datetime_types): #DEBUG
        #     debug = True #DEBUG

        if global_debug: log('resolve_obj(%s) type %s' % (obj, type(obj)))
        obj = check_circular_reference(obj)

        if (isinstance(obj, types.StringTypes)):
            value = resolve_string(obj)

        elif (isinstance(obj, types.TupleType) or
            isinstance(obj, types.GeneratorType)):

            # immutable iterators
            value = tuple(resolve_obj(item) for item in obj)
            if global_debug: log('resolve_obj(%s) value is tuple: %r' % (obj, value))

        elif isinstance(obj, types.ListType):

            # mutable iterator
            value = list(resolve_obj(item) for item in obj)
            if global_debug: log('resolve_obj(%s) value is list: %r' % (obj, value))

        elif isinstance(obj, types.DictType):

            value = resolve_dict(obj, json_compatible=json_compatible)
            if global_debug: log('resolve_obj(%s) value is dict: %r' % (obj, value))

        elif isinstance(obj, datetime_types):

            value = resolve_datetime(obj)

        elif is_class_instance(obj):

            value = resolve_instance(obj)
            if global_debug: log('resolve_obj(%s) value is instance: %r' % (obj, value))

        elif isinstance(obj, types.ModuleType):

            value = resolve_module(obj)
            if global_debug: log('resolve_obj(%s) value is module: %r' % (obj, value))

        elif type_allowed(obj):
            value = obj
            if global_debug: log('resolve_obj(%s) value is allowed type: %s' % (obj, type(obj)))

        else:
            # any other type as just the type, not restorable
            value = str(type(obj))
            if not value in _unimplemented_types:
                # mention each type just once
                _unimplemented_types.add(value)
                if global_debug: log('resolve_obj(%s) value is unimplemented type: %s' % (obj, value))

        if global_debug: log('resolve_obj(%s) final type: %s, value: %r' % (obj, type(value), value))
        assert not isinstance(value, datetime_types) #DEBUG
        return value

    global global_debug
    global_debug = debug

    if global_debug: log('dictify(%r)' % obj)
    value = resolve_obj(obj)

    # remove the object from circular references
    if id(obj) in _dictify_references:
        _dictify_references.remove(id(obj))

    # if global_debug: log('dictify(%s) is %r' % (object_name(obj, include_repr=True), value))
    return value

class DictObject(dict):
    ''' Wraps a dict in a class to add <dict>.<attribute> syntax.
        This allows you to access a dict either as usual, or the way you
        access members of an instance.

        Keys and values which are of type dict are converted to DictObject.

        To convert a class instance to a dict, see syr.dictify().

        >>> class Test(object):
        ...     a = 1
        ...     b = 'hi'
        ...     c = {'a': a, 'b': b}

        >>> print('test repr')
        test repr
        >>> x = Test()
        >>> print repr(x)
        ... # doctest: +ELLIPSIS
        <__main__.Test ...

        >>> print('test dictify')
        test dictify
        >>> d = dictify(x)
        >>> print repr(d)
        {'a': 1, 'c': {'a': 1, 'b': 'hi'}, 'b': 'hi'}

        >>> print('test DictObject')
        test DictObject
        >>> o = DictObject(d)
        >>> print repr(o)
        {'a': 1, 'c': {'a': 1, 'b': 'hi'}, 'b': 'hi'}
        >>> print dir(o)
        ['a', 'b', 'c']
        >>> o.a
        1
        >>> o.b
        'hi'
        >>> o.c
        {'a': 1, 'b': 'hi'}
        >>> isinstance(o.c, DictObject)
        True
        >>> o.d
        Traceback (most recent call last):
            ...
        KeyError: 'd'

        >>> print('test dictify(DictObject)')
        test dictify(DictObject)
        >>> d2 = dictify(o)
        >>> print repr(d2)
        {'a': 1, 'c': {'a': 1, 'b': 'hi'}, 'b': 'hi'}
    '''

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        if isinstance(name, types.DictType):
            name = DictObject(name)
        if isinstance(value, types.DictType):
            value = DictObject(value)
        self[name] = value

    def __delattr__(self, name):
        if name in self.keys():
            del self[name]
        else:
            raise AttributeError(name)

    def __repr__(self):
        try:
            result = repr(dict(self))
        except:
            result = '<<<DictObject repr error>>>'
        return result

    def __str__(self):
        try:
            result = str(dict(self))
        except:
            result = 'DictObject str error'
        return result

    def __dir__(self):
        return self.keys()

    def __hash__(self):
        return id(self)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
