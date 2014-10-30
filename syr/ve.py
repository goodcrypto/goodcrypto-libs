'''
    Virtualenv without shell scripts.
    
    No more "cd dir ; bin/activate". Pure python scripts using virtualenv.
    
    Example::
    
        import ve
        ve.activate()
        
        import ... # from virtualenv
        
        ... code to run in virtualenv ...
    
    Example::
    
        from ve import venv
        
        with venv():
            import ... # from virtualenv
            ... code to run in virtualenv ...
            
        with venv(other_vdir):
            ... code to run in a different virtualenv ...
            
        ... code to run outside of virtualenv ...
        
    This module should be installed system wide, not in any virtualenv.
            
    If no virtualenv directory is supplied to activate() or venv(),
    this module will search the calling module's dir and then its
    parent dirs for a virtualenv. See virtualenv_dir().
    
    For maintainers: This module should never have any imports 
    except from the standard python library. This allows you to import 
    this module, activate a virtualenv, and then import other modules 
    from that virtualenv. 
    
    Do not import anything non-standard in this module at global scope.
    If you really need a non-standard import, import in a local scope.
    Example::
    
        _log = None
        
        def log(message):
            global _log
            if _log == None:
                # delayed non-global import, still takes effect globally
                from syr.log import get_log
                _log = get_log()
            _log(message)
            
    This module is not named virtualenv because that module is part of the virtualenv
    program itself.
    
    To do:
        Check whether we are already in an activated virtualenv.
   
    ::
    Copyright 2011-2014 GoodCrypto
    Last modified: 2014-05-22

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os, os.path, sys, traceback
from contextlib import contextmanager
from glob import glob


DEBUGGING = False
LOGGING = False

# site_packages_subdir_glob is relative to the virtualenv dir            
site_packages_subdir_glob = 'lib/python*/site-packages'

if DEBUGGING:
    from syr.log import get_log
    log = get_log(recreate=True)
    
def debug(msg):
    if DEBUGGING:
        if LOGGING:
            log.write(msg)
        else:
            print(msg)

@contextmanager
def venv(dirname=None, django_app=None, restore=True):
    ''' Context manager to activate a virtualenv.
    
        Example::
        
            from ve import venv
            
            with venv():

                # imports delayed until in virtualenv
                import ...
                
                ... code to run in virtualenv ...
    
        To activate a virtualenv once for a module, use activate().

        This context manager will:
           * Set the VIRTUAL_ENV environment variable to the virtualenv dir
           * Set the current dir to the virtualenv dir
           * Prepend virtualenv/bin to the os environment PATH
           * Prepend sites-packages to sys.path
           * Optionally set the DJANGO_SETTINGS_MODULE environment variable
        
        If dir is not included or is None, ve searches for a virtualenv.
        See virtualenv_dir().
          
       On exiting the context, any changes to these system environment 
       variables or python's sys.path are lost. 
    
        Virtualenv's 'bin/activate' doesn't work well with fabric. See
        http://stackoverflow.com/questions/1691076/activate-virtualenv-via-os-system
    '''

    debug('entering venv()')
    
    old_virtualenv = os.environ.get('VIRTUAL_ENV')
    old_settings_module = os.environ.get('DJANGO_SETTINGS_MODULE')
    old_path = os.environ.get('PATH')
    old_python_path = list(sys.path)
    old_cwd = os.getcwd()

    debug('dirname: %s' % dirname)
    venv_dir = virtualenv_dir(dirname)
    os.environ['VIRTUAL_ENV'] = venv_dir
    
    debug('venv dir: %s' % venv_dir)

    bin_dir = os.path.join(venv_dir, 'bin')
    path_dirs = os.environ['PATH'].split(':')
    if not bin_dir in path_dirs:
        new_path = ':'.join([bin_dir] + path_dirs)
        os.environ['PATH'] = new_path

    if django_app:
        os.environ['DJANGO_SETTINGS_MODULE'] = '%s.settings' % django_app
        debug('django settings: %s' % django_app)

    os.chdir(venv_dir)
        
    packages_dir = site_packages_dir(venv_dir)
    sys.path.insert(0, packages_dir)
    
    try:
        yield

    finally:
        
        if restore:
            if old_virtualenv:
                os.environ['VIRTUAL_ENV'] = old_virtualenv
            else:
                del os.environ['VIRTUAL_ENV']
                
            os.environ['PATH'] = old_path
            
            if old_settings_module:
                os.environ['DJANGO_SETTINGS_MODULE'] = old_settings_module
            else:
                if 'DJANGO_SETTINGS_MODULE' in os.environ:
                    del os.environ['DJANGO_SETTINGS_MODULE'] 
    
            # because we may have su'd to another user since we originally 
            # cd'd to the old dir, we may not have permission to cd back
            try:
                os.chdir(old_cwd)
            except OSError:
                # just log it
                #log('could not chdir(%s); probably not an error' % old_cwd)
                pass
            
            sys.path[:] = old_python_path

    debug('finished venv()')

def activate(dirname=None, django_app=None):
    ''' Activate a virtualenv.
    
        Example::
           
            # before any imports from a virtualenv
            import ve
            ve.activate(dirname)   # or ve.activate()
            
            # now we can import from the virtualenv
            import ...
           
        If dirname is not included or is None, ve searches for a virtualenv.
        See virtualenv_dir(). 
          
        If you want to enter and then exit the virtualenv, use the context 
        manager venv().
    '''
    
    venv(dirname, django_app=django_app, restore=False).__enter__()
    
def in_virtualenv(dirname=None):
    ''' Return True if in virtualenv, else return False. 
    
        If dirname is specified, return if in specified venv. '''
        
    in_venv = False
    
    if 'VIRTUAL_ENV' in os.environ:
        
        if not dirname:
            dirname = os.environ['VIRTUAL_ENV']
            
        if dirname == os.environ['VIRTUAL_ENV']:  
            bin_dir = os.path.join(dirname, 'bin')
            path_dirs = os.environ['PATH'].split(':')
            
            if bin_dir in path_dirs:
                
                if os.path.isdir(bin_dir):
                    in_venv = True
                
    return in_venv
    
def virtualenv_dir(dirname=None):
    ''' Return full path to virtualenv dir. Raises exception if the
        specified dirname is not a virtualenv and no virtualenv is found. 
    
        virtualenv_dir() searches for a virtualenv in:
            * dirname
            * any parent dir of dirname
            * any immediate subdir of the above
          
        If dirname is None (the default), virtualenv_dir() sets it to the 
        first of:
            * The VIRTUAL_ENV environment variable
            * the calling program module's dir
          
        This lets you run a program which automatically finds and then
        activates its own virtualenv. You don't need a wrapper script to 
        first activate the virtualenv and then run your python code.
        
        Since there is probably no virtualenv associated with a dir in the
        system path, links in the PATH env dirs are followed. So for a 
        program in a PATH dir which is a link, it's dirname is the dir of 
        the target of the link.
        
        If you have a default virtualenv dir that is not in your module's 
        directory tree, you can still have ve automatically find it. Create 
        a link to the virtualenv dir in the calling module's dir or one of 
        its parent dirs. The link must be named "virtualenv". 
        
        Example::
        
            # if your default virtualenv dir is mydefault/virtualenv
            # and your python code is in /usr/local/bin
            ln --symbolic mydefault/virtualenv /usr/local/bin
        
        '''
        
    if not dirname:
        if 'VIRTUAL_ENV' in os.environ:
            dirname = os.environ['VIRTUAL_ENV']
        
        else:
            
            # find the calling program module
            # we want the last caller which is not this module
            elements = traceback.extract_stack()
            debug('stack: %s' % '\n'+'\n'.join(repr(element) for element in elements))
            debug('__file__: %s' % __file__)
            caller_filename = None
            found_caller = False
            
            # stack filenames end in .py; __file__ filenames end in .pyc or .pyo
            basename, _, extension = __file__.rpartition('.')
            if extension == 'pyc' or extension == 'pyo':
                this_filename = basename + '.py'
            else:
                this_filename = __file__
            debug('basename: %s' % basename)
            debug('extension: %s' % extension)
            debug('this_filename: %s' % this_filename)
            
            for filename, line_number, function_name, text in elements: 
                if not found_caller:
                    if filename == this_filename:
                        found_caller = True
                    else:
                        caller_filename = filename
                        debug('tentative caller filename: %s' % caller_filename)
                        
            if caller_filename:
                # in PATH, follow links
                # we probably don't want to always follow links
                path = os.environ['PATH'].split(':')
                dirname = os.path.dirname(caller_filename)
                debug('os.path.islink({}): {}'.format(caller_filename, os.path.islink(caller_filename)))
                while os.path.islink(caller_filename) and dirname in path:
                    caller_filename = os.readlink(caller_filename)
                    dirname = os.path.dirname(caller_filename)
                    
            if not dirname:
                dirname = os.getcwd()
            debug('dirname: %s' % dirname)
            
    base_dirname = os.path.abspath(dirname)
        
    dirname = base_dirname
    vdir = None
    done = False
    while not done:

        debug('dirname: %s' % dirname)
        if not dirname or dirname == '/':
            done = True
            
        elif is_virtualenv(dirname):
            vdir = dirname
            debug('vdir: %s' % vdir)
            done = True
            
        else:
            for d in os.listdir(dirname):
                if not done:
                    vdir = os.path.join(dirname, d)
                    if os.path.isdir(vdir):
                        debug('testing vdir: %s' % vdir)
                        done = is_virtualenv(vdir)
            if done: debug('vdir: %s' % vdir)
            
        if not done:
            # try the parent dir                                           
            dirname = os.path.dirname(dirname)
    
    if not is_virtualenv(vdir):
        raise Exception('No virtualenv found for {}'.format(base_dirname))
        
    return vdir

def is_virtualenv(vdir):
    ''' Return whether specified dir is a virtualenv. '''
    
    return (
        vdir and 
        os.path.exists(os.path.join(vdir, 'bin', 'python')) and 
        os.path.exists(os.path.join(vdir, 'bin', 'activate')) and 
        os.path.exists(os.path.join(vdir, 'bin', 'pip'))
        )
    
def site_packages_dir(dirname=None):
    ''' Return site-packages dir for venv dir '''
    
    venv_dir = virtualenv_dir(dirname)
    
    old_dir = os.getcwd()
    os.chdir(venv_dir)
    
    local_site_packages_dir = glob(site_packages_subdir_glob)[0]
    result = os.path.abspath(os.path.join(venv_dir, local_site_packages_dir))
    
    os.chdir(old_dir)
    
    return result

def package_dir(package, dirname=None):
    ''' Return package dir in venv dir '''

    return os.path.join(site_packages_dir(dirname), package)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
