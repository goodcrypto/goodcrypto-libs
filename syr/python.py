'''
    Python programming utilities.
    
    Utiities about python, not just in python.

    Copyright 2009-2014 GoodCrypto
    Last modified: 2015-01-02

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

import os.path, re, traceback, types

def dynamically_import_module(name):
    ''' Dynamically import a module. See python docs on __import__()'''

    module = __import__(name)
    components = name.split('.')
    for component in components[1:]:
        module = getattr(module, component)
    return module

def dynamic_import(name):
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
        print(','.join(sorted(mod.globalnames.keys()[:3])))
    
    print('Modules not imported:')
    for name in finder.badmodules.iterkeys():
        print('    {}'.format(name))
    
def object_name(obj, include_repr=False):
    ''' Get a human readable type name of a module, function, class, class method, or instance.

        The name is not guaranteed to be unique.

        If include_repr is True, an instance has its string representation appended. 
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
        >>> assert name == 'syr.utils' or name == 'utils' or name == 'nosetests', 'unexpected '+name
        
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
    ''' Returns True if object is a python package, else False. ''' 
    
    # this seems to be roughly what python does internally
    return (isinstance(object, types.ModuleType) and 
        os.path.basename(object.__file__).startswith('__init__.py'))
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
