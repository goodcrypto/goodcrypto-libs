'''
    User utiltities.
   
    Copyright 2010 GoodCrypto
    Last modified: 2014-11-21  

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from contextlib import contextmanager
import fs, grp, os, pwd, sh, sys
from functools import wraps
try:
    from stat import S_ISDIR
except:
    pass
from tempfile import TemporaryFile

def drop_privileges(user):
    ''' Drop privileges to another user. '''
    
    if whoami() != user:
        # print('started as user {}, switching to {}'.format(whoami(), user))
        su(user)
    require_user(user)

def whoami():
    ''' Get name of current user.
    
        Calling whoami() writes to /var/log/auth.log. To avoid flooding that
        log, try to cache the result from whoami() when you can.
    
        >>> assert whoami() == pwd.getpwuid(os.geteuid()).pw_name
    '''
    
    # import delayed to avoid recursive imports
    import syr.cli
    
    return syr.cli.run(sh.whoami).stdout.strip()
    
def require_user(user):
    ''' Require a specific current user. '''
        
    if whoami() != user:
        sys.exit('This program must be run as {}'.format(user))

def su(username):
    ''' Login as user.
    
        Raises OsError if user does not exist or current 
        user does not has permission to log in as new user.'''
    
    if whoami() != username:
        uid = getuid(username)
        os.setuid(uid)
    assert whoami() == username
    
def sudo(username=None):
    ''' Context manager to run code as another user.
    
        The current user must have the NOPASSWD option set in /etc/sudoers. 
        Otherwise sh.sudo will hang.
        
        >>> import sh
        >>> import syr.user
        
        >>> original_user = syr.user.whoami()
        >>> if original_user == 'root':
        ...
        ...     for user in syr.user.users():
        ...         if user != original_user:
        ...
        ...             with syr.user.sudo(user):
        ...                 assert syr.user.whoami() == user, 'could not sudo as {}'.format(user)
        ...             assert syr.user.whoami() == original_user
    '''
    
    # import delayed to avoid recursive imports
    import syr.cli
    
    @contextmanager
    def null_contextmanager():
        yield
         
    if username:
        if username == whoami():
            # no need to sudo, and avoid spurious "is not in the sudoers file" error
            context = null_contextmanager()
        else:
            context = sh.sudo.bake('-u', username, _with=True)
    else:
        # sudo defaults to root
        context = syr.cli.run(sh.sudo, _with=True)
    return context
    
@contextmanager
def user(username):
    ''' Context manager to select a user.
    
        The new user must have permission to su to the old user.
    
        We probably should rename this to temp_user() to better reflect what it is.
    '''
    
    old_user = whoami()
    if username == old_user:
        yield
    else:
        su(username)
        assert whoami() == username
        try:
            yield
        finally:
            su(old_user)
            assert whoami() == old_user
            
def users():
    ''' Get active users '''
    
    # import delayed to avoid recursive imports
    import syr.cli
    
    return set(syr.cli.run(sh.users).stdout.split())
        
def why_file_permission_denied(pathname, mode='r'):
    ''' Return string saying why file access didn't work.
    
        If permission is not denied, returns None.
        
        If present, the mode parameter is one or more of the characters 
        'r', 'w', 'x', '+' for 'read', 'write', 'execute', and 'append'.  
        
        '+' is treated as 'w'. '''
    
    if type(mode) == int:
        mode = fs.filemode(mode)
                
    reason = None
    permission = False
    while pathname and reason is None:
        
        try:
            stat_info = os.stat(pathname)
            
        except:
            # if os.stat fails it 's probably because of a dir in the path
            pass
            #reason = 'os.stat() failed for {}'.format(pathname)
            
        else:
            
            #print('{} mode: {}'.format(pathname, fs.filemode(stat_info.st_mode))) #DEBUG
            
            for perm in mode:
                
                if os.path.isdir(pathname):
                    try:
                        # 'x' is search, but is this right for 'r'?
                        if perm == 'r' or perm == 'x':
                            os.listdir(pathname)
                        else:
                            f = TemporaryFile(dir=pathname)
                            f.close()
                        permission = True
                    except:
                        reason = 'no "{}" access for {}'.format(perm, pathname)
                        
                else:
                    try:
                        f = open(pathname, mode)
                        f.close()
                        permission = True
                    except:
                        reason = 'no "{}" access for {}'.format(perm, pathname)
                
        if pathname:
            # remove last component of pathname
            parts = pathname.split('/')
            pathname = '/'.join(parts[:-1])
        
    return reason
    
def filemode(st_mode):
    raise Exception('Deprecated. Moved to syr.fs.')
    
def getuid(username):
    ''' Return uid for username. '''
    
    name_info = pwd.getpwnam(username)
    return name_info.pw_uid
    
def getgid(groupname):
    ''' Return gid for groupname. '''
    
    name_info = grp.getgrnam(groupname)
    return name_info.gr_gid
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
