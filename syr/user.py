'''
    User utilities.
   
    Copyright 2010 GoodCrypto
    Last modified: 2015-07-17  

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from contextlib import contextmanager
import grp, os, pwd, sh, sys, traceback
from functools import wraps
try:
    from stat import S_ISDIR
except:
    pass
from tempfile import TemporaryFile

def whoami():
    ''' Get name of current user.
    
        Calling whoami() writes to /var/log/auth.log. To avoid flooding that
        log, try to cache the result from whoami() when you can.
    
        >>> assert whoami() == pwd.getpwuid(os.geteuid()).pw_name
    '''
    
    return sh.whoami().stdout.strip()
    
    # why did we use cli()?
    # import delayed to avoid recursive imports
    # import syr.cli
    
    # return syr.cli.run(sh.whoami).stdout.strip()
    
def require_user(user):
    ''' Require a specific current user. '''
       
    current_user = whoami()
    if current_user != user:
        sys.exit('This program must be run as {}. Current user is {}.'.
            format(user, current_user))

def su(newuser, set_home_dir=True):
    ''' Login as newuser.
    
        Use sudo() if you want to return to the original user later.
        This will usually only work if you call sudo() as root.
    
        This function only successfully changes the euid, not the uid.
        Programs which use the uid, such as ssh and gpg, need extra help.
        One solution is to prefix commands with "sudo -u USER".
        See the jean.ssh module.
        
        Raises OsError if user does not exist or current 
        user does not has permission to log in as new user. '''
        
    
    user = whoami()
    if user != newuser:
        uid = getuid(newuser)
        os.seteuid(uid)
        # why doesn't this work?
        try:
            # See http://stackoverflow.com/questions/7529252/operation-not-permitted-on-using-os-setuid-python
            # if os.fork():
            #     os._exit(0)
            
            os.setuid(uid)
        except:
            # print(traceback.format_exc().strip()) # DEBUG
            # print('ERROR IGNORED. Because os.setuid() does not appear to work even for root') # DEBUG
            pass
        
    require_user(newuser)
    if set_home_dir:
        os.environ['HOME'] = getdir(newuser)
    
def sudo(username=None, set_home_dir=True):
    ''' Context manager to temporarily run code as another user.
    
        This will usually only work if you call sudo() as root.
        
        Use su() if you do not want to return to the original user later. 
        If you are root, this function only sets the euid.
        Some programs use the uid instead of the euid, such as ssh or gpg.
    
        The current user must have the NOPASSWD option set in /etc/sudoers. 
        Otherwise sh.sudo will hang. (This is true for sh. Is NOPASSWD needed 
        for this function?)
        
        >>> import syr.user
       
        >>> original_user = syr.user.whoami()
        >>> print('before: ' + whoami())
        >>> if original_user == 'root':
        ...
        ...     for user in syr.user.users():
        ...         if user != original_user:
        ...
        ...             with syr.user.sudo(user):
        ...                 print('during: ' + whoami())
        ...                 assert syr.user.whoami() == user, 'could not sudo as {}'.format(user)
        ...             print('after: ' + whoami())
        ...             assert syr.user.whoami() == original_user
    '''
    
    # import delayed to avoid recursive imports
    import syr.cli
    
    @contextmanager
    def null_contextmanager():
        yield
        
    @contextmanager
    def active_contextmanager():
        try:
            uid = getuid(username)
            if prev_user == 'root':
                os.seteuid(uid)
            else:
                os.setuid(uid)
            if set_home_dir:
                os.environ['HOME'] = getdir(username)
            yield
        finally:
            prev_uid = getuid(prev_user)
            try:
                os.seteuid(prev_uid)
            except:
                pass
            else:
                if set_home_dir:
                    os.environ['HOME'] = getdir(prev_user)
         
    prev_user = whoami()
    if username:
        if username == prev_user:
            # no need to sudo, and avoid spurious "is not in the sudoers file" error
            context = null_contextmanager()
        else:
            context = active_contextmanager()
    else:
        # sudo defaults to root
        if prev_user == 'root':
            # no need to sudo, and avoid spurious "is not in the sudoers file" error
            context = null_contextmanager()
        else:
            username = 'root'
            context = active_contextmanager()
                
    return context
            
def users():
    ''' Get active users '''
    
    # import delayed to avoid recursive imports
    import syr.cli
    
    return set(syr.cli.run(sh.users).stdout.split())
        
def getuid(username):
    ''' Return uid for username. '''
    
    name_info = pwd.getpwnam(username)
    return name_info.pw_uid
    
def getuid_name(uid):
    ''' Return user name for uid.
    
        >>> import pwd
        
        >>> getuid_name('not an int')        
        Traceback (most recent call last):
            ...
        ValueError: uid is not an int: not an int
        
        >>> for entry in pwd.getpwall():
        ...     assert getuid_name(entry.pw_uid) == entry.pw_name
    '''
    
    try:
        uid = int(uid)
    except ValueError:
        raise ValueError, 'uid is not an int: {}'.format(uid)
    
    name = None
    for entry in pwd.getpwall():
        if entry.pw_uid == uid:
            name = entry.pw_name
        
    if name is None:
        raise ValueError, 'No uid {}'.format(uid)
        
    return name
    
def getgid(groupname):
    ''' Return gid for groupname. '''
    
    name_info = grp.getgrnam(groupname)
    return name_info.gr_gid
    
def getgid_name(gid):
    ''' Return group name for gid. 
    
        >>> import grp
        
        >>> getgid_name('not an int')        
        Traceback (most recent call last):
            ...
        ValueError: gid is not an int: not an int
    
        >>> for entry in grp.getgrall():
        ...     assert getgid_name(entry.gr_gid) == entry.gr_name 
    '''
    
    try:
        gid = int(gid)
    except ValueError:
        raise ValueError, 'gid is not an int: {}'.format(gid)
        
    name = None
    for entry in grp.getgrall():
        if entry.gr_gid == gid:
            name = entry.gr_name
        
    if name is None:
        raise ValueError, 'No gid {}'.format(uid)
        
    return name
    
def getdir(username):
    ''' Return home dir for username. '''
    
    name_info = pwd.getpwnam(username)
    return name_info.pw_dir
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
