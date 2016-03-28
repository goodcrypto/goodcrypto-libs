'''
    User utilities.
   
    Copyright 2010 GoodCrypto
    Last modified: 2015-04-12  

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from contextlib import contextmanager
import grp, os, pwd, sh, sys
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
