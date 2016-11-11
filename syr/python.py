'''
    Python programming utilities.

    Utiities about python, not just in python.

    Copyright 2009-2016 GoodCrypto
    Last modified: 2016-06-18

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import print_function
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import importlib, os.path, sh, re, traceback, types

from syr._log import log

prefered_encoding = 'utf-8'

def set_default_encoding(encoding=prefered_encoding):
    '''
        >>> set_default_encoding(prefered_encoding)
        >>> encoding = sys.getdefaultencoding()
        >>> if IS_PY2:
        ...     encoding == 'ascii' or encoding == 'utf-8'
        ... else:
        ...     encoding == 'utf-8'
        True
    '''

    if IS_PY2:
        try:
            # only available in python2
            sys.setdefaultencoding(encoding)
        except AttributeError:
            '''Already used by the site module, which removes it from sys namespace'''
            pass

def dynamically_import_module(name):
    '''
        Dynamically import a module. See python docs on __import__()

        >>> mod = dynamically_import_module('syr')
        >>> if IS_PY2:
        ...     str(mod) == "<module 'syr' from '/usr/local/lib/python2.7/dist-packages/syr/__init__.pyc'>"
        ... else:
        ...     str(mod) == "<module 'syr' from '/usr/local/lib/python3.4/dist-packages/syr/__init__.py'>"
        True
     '''

    module = __import__(name)
    components = name.split('.')
    for component in components[1:]:
        module = getattr(module, component)
    return module

def dynamic_import(name):
    '''
        >>> mod = dynamic_import('syr')
        >>> if IS_PY2:
        ...     str(mod) == "<module 'syr' from '/usr/local/lib/python2.7/dist-packages/syr/__init__.pyc'>"
        ... else:
        ...     str(mod) == "<module 'syr' from '/usr/local/lib/python3.4/dist-packages/syr/__init__.py'>"
        True
    '''
    # from Python Library Reference, Built-in Functions, __import__
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def print_imported_modules(filename):
    ''' Print modules imported by filename.

        Warning: Runs filename.

        >>> # how do we test this? how we generally use it:
        >>> # print_imported_modules(__file__)
    '''

    import modulefinder

    if filename.endswith('.pyc') or filename.endswith('.pyo'):
        filename = filename[:-1]
    print(filename)

    finder = modulefinder.ModuleFinder()
    finder.run_script(filename)

    # See /usr/share/doc/python2.7/html/library/modulefinder.html
    print('Loaded modules:')
    for name in sorted(finder.modules.keys()):
        mod = finder.modules[name]
        print('    {}: '.format(name), end='')
        if IS_PY2:
            print(','.join(sorted(mod.globalnames.keys()[:3])))
        else:
            print(','.join(sorted(list(mod.globalnames.keys())[:3])))

    print('Modules not imported:')
    if IS_PY2:
        keys = finder.badmodules.iterkeys()
    else:
        keys = finder.badmodules.keys()
    for name in keys:
        print('    {}'.format(name))

def object_name(obj, include_repr=False):
    ''' Get a human readable type name of a module, function, class, class method, or instance.

        The name is not guaranteed to be unique.

        If include_repr is True, an instance has its string representation appended.

        >>> name = object_name('syr')
        >>> if IS_PY2:
        ...     name == u'__builtin__.unicode instance'
        ... else:
        ...     name == 'builtins.str instance'
        True
    '''

    module_name = getattr(obj, '__module__', None)
    local_object_name = getattr(obj, '__name__', None)
    if module_name and local_object_name and local_object_name != '__main__':
        name = '%s.%s' % (module_name, local_object_name)
    elif module_name:
        name = module_name
    elif local_object_name:
        name = local_object_name
    else:
        #name = repr(obj)
        class_name = getattr(obj, '__class__', None)
        module_name = getattr(class_name, '__module__', None)
        local_object_name = getattr(class_name, '__name__', None)
        name = '%s.%s instance' % (module_name, local_object_name)
        if include_repr:
            name = '%s: %s' % (name, repr(obj))
    return name

def caller_module_name(ignore=None, syr_utils_valid=False):
    ''' Get the caller's fully qualified module name.

        If this function is called from syr.utils, set syr_utils_valid=True.

        To do: Test linked package dirs in parent dirs.

        >>> # this code really needs to be tested from a different module
        >>> name = caller_module_name(syr_utils_valid=True)
        >>> if IS_PY2:
        ...     name == u'python'
        ... else:
        ...     name == 'python'
        True

        To get the parent caller instead of the module that actually
        calls caller_module_name():

            name = caller_module_name(ignore=[__file__])
    '''

    def ignore_filename(filename):
        ''' Ignore files in ignore list and runpy.py. '''

        if _debug_caller_module_name: print('in ignore_filename() ignore: {}'.format(repr(ignore))) #DEBUG
        return (filename in ignore) or filename.endswith('/runpy.py')

    def is_python_module_dir(dirname):
        # a python module dir has an __init__.py file
        init_path = os.path.join(dirname, '__init__.py')
        return os.path.exists(init_path)

    def strip_py(filename):
        if filename.endswith('.py'):
            filename, _, _ = filename.rpartition('.')
        return filename

    _debug_caller_module_name = False

    if _debug_caller_module_name: print('ignore: {}'.format(repr(ignore))) #DEBUG

    # make ignore list
    if ignore:
        _ignore = ignore
    else:
        _ignore = []
    # ignore syr.utils unless syr_utils_valid=True
    if not syr_utils_valid:
        _ignore = _ignore + [__file__]
    # make stack and __file__ filenames match
    ignore = []
    for filename in _ignore:
        # the ignore=[...] param is usually ignore=[__file__]
        # stack filenames end in .py; __file__ filenames end in .pyc or .pyo
        # make them all .py
        basename, _, extension = filename.rpartition('.')
        if extension == 'pyc' or extension == 'pyo':
            filename = basename + '.py'
        ignore.append(filename)

    name = None

    if _debug_caller_module_name:
        print('caller_module_name traceback.extract_stack():') #DEBUG
        for stack_item in traceback.extract_stack():
            print('    {}'.format(stack_item)) #DEBUG

    stack = list(traceback.extract_stack())
    stack.reverse()
    # filename, line number, function name, text
    for filename, _, _, _ in stack:

        if not name:
            if ignore_filename(filename):
                if _debug_caller_module_name: print('caller_module_name ignored filename: {}'.format(filename)) #DEBUG

            else:
                if _debug_caller_module_name: print('caller_module_name filename: {}'.format(filename)) #DEBUG
                # find python module dirs in filename
                modules = []
                dirname, _, basename = filename.rpartition('/')
                while dirname and is_python_module_dir(dirname):
                    #if _debug_caller_module_name: print('caller_module_name is_python_module_dir: {}'.format(dirname)) #DEBUG
                    modules.append(os.path.basename(dirname))
                    dirname, _, _ = dirname.rpartition('/')
                modules.reverse()

                # if the filename is a __main__.py for a package, just use the package name
                if basename != '__main__.py':
                    modules.append(strip_py(basename))
                #if _debug_caller_module_name: print('caller_module_name modules: {}'.format(repr(modules))) #DEBUG

                name = '.'.join(modules)

    assert name
    """
    if not name:
        filename, _, _, _ = stack[0]
        name = strip_py(os.path.basename(filename))
    """

    if _debug_caller_module_name: print('caller_module_name: {}'.format(name)) #DEBUG
    return name

def is_package_type(object):
    '''
        Returns True if object is a python package, else False.

        >>> import syr
        >>> is_package_type(syr)
        True
        >>> import syr.python
        >>> is_package_type(syr.python)
        False
    '''

    # this seems to be roughly what python does internally
    return (is_module_type(object) and
        (os.path.basename(object.__file__).endswith('__init__.py') or
         os.path.basename(object.__file__).endswith('__init__.pyc') or
         os.path.basename(object.__file__).endswith('__init__.pyo')))

def is_module_type(object):
    ''' Returns True if object is a python module, else False.

        Convenience function for symmetry with is_package_type().

        >>> import syr
        >>> is_module_type(syr)
        True
        >>> import syr.python
        >>> is_module_type(syr.python)
        True
    '''

    return isinstance(object, types.ModuleType)

def is_instance(obj, cls):
    '''
        More reliable version of python builtin isinstance()

        >>> if IS_PY2:
        ...     is_instance('syr', unicode)
        ... else:
        ...     is_instance('syr', str)
        True
    '''

    log('is_instance(obj={}, cls={})'.format(obj, cls))
    log('is_instance() type: obj={}, cls={}'.format(type(obj), type(cls)))
    try:
        mro = obj.__mro__
    except AttributeError:
        mro = type(obj).__mro__
    log('is_instance() mro: {}'.format(mro))
    match = cls in mro

    log('is_instance() match: {}'.format(match))
    return match

def is_class_instance(obj):
    ''' Returns whether the object is an instance of any class.

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

        >>> t = type(2)
        >>> if IS_PY2:
        ...     str(t) == "<type 'int'>"
        ... else:
        ...     str(t) == "<class 'int'>"
        True
        >>> t = type([])
        >>> if IS_PY2:
        ...     str(t) == "<type 'list'>"
        ... else:
        ...     str(t) == "<class 'list'>"
        True
        >>> t = type({})
        >>> if IS_PY2:
        ...     str(t) == "<type 'dict'>"
        ... else:
        ...     str(t) == "<class 'dict'>"
        True

        >>> cls = getattr(2, '__class__')
        >>> if IS_PY2:
        ...     str(cls) == "<type 'int'>"
        ... else:
        ...     str(cls) == "<class 'int'>"
        True
        >>> superclass = getattr(cls, '__class__')
        >>> if IS_PY2:
        ...     str(superclass) == "<type 'type'>"
        ... else:
        ...     str(superclass) == "<class 'type'>"
        True

        >>> t = str(type(datetime.date))
        >>> if IS_PY2:
        ...     t == "<type 'type'>"
        ... else:
        ...     t == "<class 'type'>"
        True
        >>> t = str(type(c_style_class_instance))
        >>> if IS_PY2:
        ...     t == "<type 'datetime.date'>"
        ... else:
        ...     t == "<class 'datetime.date'>"
        True
        >>> t = repr(datetime.date)
        >>> if IS_PY2:
        ...     t == "<type 'datetime.date'>"
        ... else:
        ...     t == "<class 'datetime.date'>"
        True
        >>> repr(c_style_class_instance)
        'datetime.date(2000, 12, 1)'
        >>> if IS_PY2:
        ...     isinstance(c_style_class_instance, types.InstanceType)
        ... else:
        ...     isinstance(c_style_class_instance, types.MethodType)
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
        >>> if IS_PY2:
        ...     str(cls) == "<type 'datetime.date'>"
        ... else:
        ...     str(cls) == "<class 'datetime.date'>"
        True
        >>> superclass = getattr(cls, '__class__')
        >>> if IS_PY2:
        ...     str(superclass) == "<type 'type'>"
        ... else:
        ...     str(superclass) == "<class 'type'>"
        True

        >>> ok = '__dict__' in dir(old_c)
        >>> if IS_PY2:
        ...    ok == False
        ... else:
        ...    ok == True
        True
        >>> hasattr(old_c, '__slots__')
        False

        >>> '__dict__' in dir(new_c)
        True
        >>> hasattr(new_c, '__slots__')
        False

        '''

    type_str = str(type(obj))

    if IS_PY2:
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

    else:
        # old style python defined classes
        if type_str == "<class 'instance'>":
                is_instance = True
    
        # C defined classes
        elif type_str.startswith('<class '):
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

def run(sourcecode):
    '''
        Run source code text.

        >>> run('print("hi")')
        hi
    '''

    # magic. bad. but wasted too many hours trying pythonic solutions
    # in python 2.7 importlib doesn't know spec.Specs is the same as dbuild.spec.Specs

    import tempfile

    _, exec_path = tempfile.mkstemp(
        suffix='.py',
        dir='/tmp')

    log('sourcecode:\n{}'.format(sourcecode.strip()))

    with open(exec_path, 'w') as exec_file:
        exec_file.write(sourcecode)

    try:
        if IS_PY2:
            execfile(exec_path, globals())
        else:
            exec(compile(open(exec_path).read(), exec_path, 'exec'), globals())
    finally:
        os.remove(exec_path)

def import_module(name):
    '''
        Import with debugging

        >>> module = import_module("syr.user")
        >>> if IS_PY2:
        ...     str(module) == "<module 'syr.user' from '/usr/local/lib/python2.7/dist-packages/syr/user.pyc'>"
        ... else:
        ...     str(module) == "<module 'syr.user' from '/usr/local/lib/python3.4/dist-packages/syr/user.py'>"
        True
    '''

    try:
        log('import_module({})'.format(name)) #DEBUG
        module = importlib.import_module(name)
        log('import_module() result: {}'.format(module)) #DEBUG
    except ImportError as imp_error:
        log('unable to import {}'.format(name))
        log('ImportError: ' + str(imp_error))
        msg = 'could not import {}'.format(name)
        log(msg)
        # find out why
        if IS_PY2:
            log(sh.python('-c', 'import {}'.format(name)).stderr)
        else:
            log(sh.python3('-c', 'import {}'.format(name)).stderr)
        raise BuildException(msg)
    return module

def stacktrace():
    '''
        Returns a printable stacktrace.

        >>> t = stacktrace()
        >>> t.startswith('Traceback')
        True
    '''

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
        <module '...' from 'python.py...'>
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

def format_exception(exc):
    ''' Format exception for printing.

        Bug: If exc is not the most recent, but is the same value
        as the most recent exception, we print the most recent traceback.
        This probably will almost never happen in practice.
    '''

    exc_type, exc_value, exc_traceback = sys.exc_info()
    # bug: if exc is not the most recent, but is the same exc_value
    if exc_value == exc:
        # in python 2.7 traceback.format_exception() does not perform as docced
        lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        exc = ''.join(lines).strip()
    else:
        # the exc Exception is not the most recent, so no traceback
        self.debug('log.debug() called with an exception but no traceback available')
        exc = traceback.format_exception_only(type(exc), exc)

def is_string(obj):
    '''
        Return True iff obj is a string.

        >>> is_string('test')
        True
    '''

    if IS_PY2:
        return isinstance(obj, basestring)
    else:
        return isinstance(obj, str)

def is_list(obj):
    '''
        Return True iff obj is a list.

        >>> is_list([])
        True
    '''

    if IS_PY2:
        return type(obj) is types.ListType
    else:
        log(type(obj))
        return isinstance(obj, list)


def is_tuple(obj):
    '''
        Return True iff obj is a tuple.

        >>> is_string('test')
        True
    '''

    if IS_PY2:
        return type(obj) is types.TupleType
    else:
        return isinstance(obj, tuple)

def is_dict(obj):
    '''
        Return True iff obj is a dictionary.

        >>> is_string('test')
        True
    '''

    if IS_PY2:
        return type(obj) is types.DictType
    else:
        return isinstance(obj, dict)



if __name__ == "__main__":
    import doctest
    doctest.testmod()

