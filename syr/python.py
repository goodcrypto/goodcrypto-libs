'''
    Python programming utilities.
    
    Utiities about python, not just in python.

    Copyright 2009-2014 GoodCrypto
    Last modified: 2014-05-27

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

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
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
