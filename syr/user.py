'''
    User utilities.

    Copyright 2010 GoodCrypto
    Last modified: 2015-11-18

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

import syr.fs
from syr.log import get_log
log = get_log()

def whoami():
    ''' Get name of current user.

        Calling whoami() writes to /var/log/auth.log. To avoid flooding that
        log, try to cache the result from whoami() when you can.

        >>> assert whoami() == pwd.getpwuid(os.geteuid()).pw_name
    '''

    return sh.whoami().stdout.strip()

    # we used cli() to avoid 'OSError: out of pty devices'
    # import delayed to avoid recursive imports
    # import syr.cli

    # return syr.cli.run('whoami').stdout.strip()

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

        This function is unreliable with ssh, os.openpty(), and more.
        A workaround is to use sudo in an enclosing bash script. Or::

            # if not user VM_OWNER then relaunch this program
            if sh.whoami().strip() != VM_OWNER:
                os.execvp( 'sudo' , ['sudo', '-u', VM_OWNER] + sys.argv)

        Raises OsError if user does not exist or current
        user does not has permission to log in as new user. '''

    if whoami() != newuser:
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

        This function is unreliable with ssh, os.openpty(), and more.
        A workaround is to use sudo in an enclosing bash script. Or::

            # if not user VM_OWNER then relaunch this program
            if sh.whoami().strip() != VM_OWNER:
                os.execvp( 'sudo' , ['sudo', '-u', VM_OWNER] + sys.argv)

        >>> import syr.user

        >>> original_user = syr.user.whoami()
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

    @contextmanager
    def null_contextmanager():
        yield

    @contextmanager
    def active_contextmanager():
        """
        # in python 2.7 os.fork() results in
        #     RuntimeError: not holding the import lock
        # apparently python 3 does not have the bug
        # see  http://bugs.python.org/issue18122
        child = os.fork()
        if child:
            try:
                prev_uid = os.getuid()
                uid = getuid(username)
                os.setuid(uid)
                if set_home_dir:
                    os.environ['HOME'] = getdir(username)
                yield
            finally:
                try:
                    os.setuid(prev_uid)
                except:
                    pass
                if set_home_dir:
                    os.environ['HOME'] = getdir(prev_user)

        else:
            os.waitpid(child, 0)

        """
        try:
            uid = getuid(username)
            if prev_user == 'root':
                os.seteuid(uid)
            else:
                os.setuid(uid)
            os.setuid(uid) # DEBUG
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

    if not username:
        username = 'root'
        log.debug('sudo() using default user root')

    prev_user = whoami()
    if username == prev_user:
        # no need to sudo, and avoid spurious "is not in the sudoers file" error
        context = null_contextmanager()
    else:
        context = active_contextmanager()

    return context

def force(user):
    ''' If current user is not 'user', relaunch program as 'user'. 
    
    
        Example::
                
            if syr.user.whoami() == 'root':
                root_setup()
                ...
            
                # drop privs; relaunch program as USER
                syr.user.force(USER)
                
            # continue as USER
        
    '''

    if whoami() != user:

        this_program = sys.argv[0]
        assert syr.fs.is_executable(this_program), '{} must be executable'.format(this_program)

        for f in [sys.stdout, sys.stderr]:
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                # stdout and stderr usually aren't' real files
                pass
        os.execvp( 'sudo' , ['sudo', '-u', user] + sys.argv)

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
