'''
    File system.

    Copyright 2008-2014 GoodCrypto
    Last modified: 2015-01-01

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os, os.path, sh, shutil, stat, tempfile, threading
from contextlib import contextmanager
from datetime import datetime

from syr.log import get_log
import syr.process, syr.user, syr.utils

log = get_log()

empty_dir = None

DEFAULT_PERMISSIONS_DIR_OCTAL = 0775
DEFAULT_PERMISSIONS_FILE_OCTAL = 0660
# use strings with chmod command, sh.chmod(), and syr.fs.chmod()
DEFAULT_PERMISSIONS_DIR = 'u=rwX,g=rwX,o=rX'
DEFAULT_PERMISSIONS_FILE = 'u=rw,g=rw,o='
""" This produces an unreadable int and ignores the difference in 
    chmod between 'x' and 'X'. 
try:
    DEFAULT_PERMISSIONS_DIR = (
        stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
        stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
        stat.S_IROTH | stat.S_IXOTH)
    assert DEFAULT_PERMISSIONS_DIR == DEFAULT_PERMISSIONS_DIR_OCTAL
    DEFAULT_PERMISSIONS_FILE = (
        stat.S_IRUSR | stat.S_IWUSR |
        stat.S_IRGRP | stat.S_IWGRP |
        stat.S_IROTH | stat.S_IWOTH)
    assert DEFAULT_PERMISSIONS_FILE == DEFAULT_PERMISSIONS_FILE_OCTAL
except:
    DEFAULT_PERMISSIONS_DIR = DEFAULT_PERMISSIONS_DIR_OCTAL
    DEFAULT_PERMISSIONS_FILE = DEFAULT_PERMISSIONS_FILE_OCTAL
"""

class OpSysException(Exception):
    pass

@contextmanager
def cd(dirname):
    ''' Context manager to change dir temporarily.

        >>> startdir = '/tmp'
        >>> os.chdir(startdir)
        >>> assert os.getcwd() == startdir
        >>> import tempfile
        >>> tempdir = tempfile.mkdtemp()
        >>> with cd(tempdir):
        ...     assert os.getcwd() == tempdir
        ...     assert os.getcwd() != startdir
        >>> assert os.getcwd() == startdir

    '''

    olddir = os.getcwd()
    os.chdir(dirname)
    try:
        yield
    finally:
        os.chdir(olddir)

def chmod(mode, path, recursive=False):
    ''' Change permissions of path.

        mode is a string or octal integer for the chmod command. 
        Examples::
            'o+rw,g+rw'
            0660
        
        (Delete this warning if no errors by 2015-01-01.)
        WARNING: Arg order used to be chmod(path, mode).
    '''

    # arg order used to be chmod(path, mode, ...), so check types
    # delete this assert if no assertion errors 2015-01-01
    # after we remove this assert, mode can be a string
    assert isinstance(path, str)
    
    if isinstance(mode, int):
        # chmod wants an octal int, not decimal
        # so if it's an int we convert to an octal string
        mode = '0'+oct(mode)

    try:
        if recursive:
            sh.chmod('--recursive', mode, path)
        else:
            sh.chmod(mode, path)
    except sh.ErrorReturnCode as sh_exception:
        log.error('unable to chmod: path={}, mode={}'.format(path, mode))
        log.error(sh_exception)
        raise

def chown(owner, path, recursive=False):
    ''' Change owner of path.

        Log and reraise any exception.
    '''

    try:
        if recursive:
            sh.chown('--recursive', owner, path)
        else:
            sh.chown(owner, path)
        #log.debug('chown(owner={}, path=={})'.format(owner, path))
    except sh.ErrorReturnCode as sh_exception:
        log.error('unable to chown: user={}, owner={}, path={}'.
            format(syr.user.whoami(), owner, path))
        log.error(sh_exception)
        raise

def chgrp(group, path, recursive=False):
    ''' Change group of path.

        Log and reraise any exception.
    '''

    try:
        if recursive:
            sh.chgrp('--recursive', group, path)
        else:
            sh.chgrp(group, path)
        #log.debug('chgrp(group={}, path=={})'.format(group, path))
    except sh.ErrorReturnCode as sh_exception:
        log.error('unable to chgrp: user={}, group={}, path={}'.
            format(syr.user.whoami(), group, path))
        log.error(sh_exception)
        raise

def getmode(path):
    ''' Return permissions (mode) of a path.

        >>> oct(getmode('/var/local/projects/syr/fs.py'))
        '0644'
    '''

    return stat.S_IMODE(os.lstat(path)[stat.ST_MODE])

def getuid(path):
    ''' Return uid of a path. '''

    os.stat(path).st_uid

def getgid(path):
    ''' Return uid of a path. '''

    os.stat(path).st_uid

def makedir(dirname, owner=None, group=None, perms=None):
    ''' Make dir with correct ownership and permissions.

        Makes parent dirs if needed.
    '''

    if not perms:
        perms = DEFAULT_PERMISSIONS_DIR

    lock = threading.Lock()
    lock.acquire(1) # 1 means blocking

    try:
        if not os.path.exists(dirname):

            # makedirs(dirname, mode) uses umask, so we also call chmod() explicitly
            #log.debug('makedir(dirname={}, owner={}, group={}, perms={})'.format(
            #    dirname, owner, group, oct(perms))) #DEBUG
            try:
                os.makedirs(dirname)
                chmod(perms, dirname, recursive=True)
            except OSError:
                from syr.user import why_file_permission_denied
                log.error(why_file_permission_denied(dirname, perms))
                raise

            # set ownership and permissions
            if owner:
                chown(owner, dirname, recursive=True)
            if group:
                chgrp(group, dirname, recursive=True)
            chmod(perms, dirname)
            #log.debug('ls -l {})'.format(sh.ls('-ld', dirname))) #DEBUG

    finally:
        lock.release()

    assert os.path.isdir(dirname)

@contextmanager
def temp_mount(*args, **kwargs):
    ''' Context manager to mount/umount a filesystem.

        See "man mount" and python package "sh".

        disabled>>> import os, os.path, sh

        disabled>>> d = str(sh.mktemp(directory=True)).strip()
        disabled>>> d2 = str(sh.mktemp(directory=True)).strip()
        disabled>>> t = os.path.join(d, 'test')
        disabled>>> t2 = os.path.join(d2, 'test')
        disabled>>> # how do we ignore the <BLANKLINE> from sh.touch()? And why do we get it?
        disabled>>> x = sh.touch(t)
        disabled>>> assert os.path.exists(t)
        disabled>>> with temp_mount('--bind', d, d2):
        disabled>>> # with temp_mount(d, d2, bind=True):
        disabled...     assert os.path.exists(t2)
        disabled>>> assert not os.path.exists(t2)
    '''

    """ Needs more tests, especially for --bind/move/make-xxx with sh.umount(args[-1]) """

    with sh.sudo:
        sh.mount(*args, **kwargs)

    try:
        yield

    finally:
        # the last arg is reliably the mount point
        # even with --bind, --move, etc.
        mount_point = os.path.abspath(args[-1])
        with sh.sudo:
            sh.umount(mount_point)

def mounts():
    """ Return filesystem mounts as list.

        List elements are (device, dir, type, params, deleted).

        'deleted' is a boolean. All other items are strings.

        disabled>>> m = mounts()
        disabled>>> # how do we verify this?
        disabled>>> assert 'proc' in repr(m)
    """

    results = []
    with sh.sudo:

        with open('/etc/mtab') as mtab:
            for line in mtab:
                device, _, rest = line.partition(' ')
                dir, _, rest = rest.partition(' ')
                type, _, rest = rest.partition(' ')
                params, _, rest = rest.partition(' ')
                fsck, _, dump = rest.partition(' ')
                results.append((device, dir, type, params))

    return results

def umount_all(dirname):
    """ Unmount all points in the named dir.

        Sometimes this doesn't work if mounts are in use.
        Use syr.process.program_from_file() to find the active processes
        using the mounts and kill them.
        Or reboot, or wait a while, etc.
    """

    log.debug('unmount all in {}'.format(dirname))
    # make sure we have a trailing slash
    dir_prefix = os.path.join(dirname, '')
    # umount last mounted first
    for device, dir, type, params in reversed(mounts()):
        if dir.startswith(dir_prefix):
            log.debug('unmounting {}'.format(dir))
            sh.umount(dir)

        """
        if mounted(dir):
            log.debug('unable to unmount {}, opened by {}'.format(
                dir,
                syr.process.program_from_file(dir)))
        """

def mounted(path):
    ''' Return True iff path mounted. '''

    mounted = False
    for device, dir, type, params in mounts():
        if dir == path:
            mounted = True
    return mounted

def match_parent_owner(path, mode=None):
    ''' Chown to the parent dir's uid and gid.

        If mode is present, it is an integer passed to chmod(). '''

    try:
        statinfo = os.stat(os.path.dirname(path))
        os.chown(path, statinfo.st_uid, statinfo.st_gid)
    except:
        # probably don't have the right to change the file at all,
        # or to change the owner to the specified user
        log.error('unable to chown: user={}, uid={}, gid={}, path={}'.
            format(syr.user.whoami(), statinfo.st_uid, statinfo.st_gid, path))
        pass
    finally:
        if mode is not None:
            chmod(mode, path)

def get_unique_filename(dirname, prefix, suffix):
    '''Get a unique filename.'''

    now = datetime.now()
    base_filename = '%s-%d-%02d-%02d-%02d-%02d-%02d' % \
     (prefix, now.year, now.month, now.day, now.hour, now.minute, now.second)
    filename = '%s.%s' % (base_filename, suffix)

    if os.path.exists(os.path.join(dirname, filename)):
        i = 1
        filename = '%s-%02d.%s' % (base_filename, i, suffix)
        while os.path.exists(os.path.join(dirname, filename)):
            i += 1
            filename = base_filename + '%s-%02d.%s' % (base_filename, i, suffix)

    return os.path.join(dirname, filename)

def copy(source, dest, symlinks=True, ignore=None, owner=None, group=None, perms=None):
    ''' Copy source to dest dir.

        copy() tries to generally follow the behavior of the
        cp command.

        copy() creates any missing parent dirs of dest.
        File ownership and permissions are also copied.

        If dest is a dir, source is copied into dest.
        An exception is when dest and source have the same basename.
        This is a very common error when the intent is to replace the dest.
        In this case the contents of source are copied to dest.
        This is different from merge() because copy() always deletes the
        dest dir. If you really want a dest named "basename/basename",
        specify it explicitly.

        Otherwise, like cp, source will overwrite any existing dest.

        Unlike shutil.copytree() which this function eventually calls,
        the default is symlinks=True. So symlinks are copied as symlinks.
        If you want the links replaced by the content, set symlinks=False.

        Set ownership and permissions from keywords, or if None copy from
        the corresponding source file.

        >>> import os, os.path, sh

        >>> testdir = '/tmp/testcopy'
        >>> if os.path.exists(testdir):
        ...     result = sh.rm('--force', '--recursive', testdir)
        >>> result = sh.mkdir(testdir)

        >>> dir1 = os.path.join(testdir, 'dir1')
        >>> result = sh.mkdir(dir1)
        >>> assert os.path.exists(dir1)
        >>> dir2 = os.path.join(testdir, 'dir2')
        >>> result = sh.mkdir(dir2)
        >>> assert os.path.exists(dir2)

        >>> file1 = os.path.join(dir1, 'file1')
        >>> result = sh.touch(file1)
        >>> file2 = os.path.join(dir1, 'file2')
        >>> result = sh.touch(file2)

        >>> copy(dir1, dir2)
        >>> dir1_in_2 = os.path.join(dir2, os.path.basename(dir1))
        >>> assert os.path.isdir(dir1_in_2)
        >>> file1_in_dir1_in_2 = os.path.join(dir1_in_2, 'file1')
        >>> assert os.path.exists(file1_in_dir1_in_2)

        >>> dir3 = os.path.join(testdir, 'subdir', 'dir1')
        >>> result = makedir(dir3)
        >>> copy(dir1, dir3)
        >>> dir1_not_in_3 = os.path.join(dir3, os.path.basename(dir1))
        >>> assert not os.path.isdir(dir1_not_in_3)
        >>> file1_in_dir3 = os.path.join(dir3, 'file1')
        >>> assert os.path.exists(file1_in_dir3)
    '''

    #log.debug('copy(source={}, dest={}, symlinks=={}, ignore=={}, owner=={}, group=={}, perms=={})'.
    #    format(source, dest, symlinks, ignore, owner, group, perms))

    # source must exist, but a dangling link is acceptable
    if not os.path.exists(source) and not os.path.islink(source):
        raise ValueError('source "{}" does not exist'.format(source))

    if symlinks and os.path.islink(source):
        dest = os.path.join(dest, os.path.basename(source))
        if os.path.exists(dest):
            log.debug('copy() dest exists, removed: {}'.format(dest))
            os.remove(dest)
        os.symlink(os.readlink(source), dest)

    else:

        if os.path.isdir(dest):
            # append the source's basename to dest if the source
            # and destination basenames are different
            # leave an explicit "basename/basename" dest alone.
            if os.path.basename(dest) != os.path.basename(os.path.dirname(dest)):
                if os.path.basename(source) != os.path.basename(dest):
                    dest = os.path.join(dest, os.path.basename(source))

        if os.path.exists(dest):
            sh.rm(dest, force=True, recursive=True)

        if os.path.isdir(source):

            umount_all(source)

            # if there's no reason to traverse the dir tree
            if (symlinks is True and ignore is None and
                owner is None and group is None and perms is None):
                sh.cp(source, dest, archive=True)

            else:
                makedir(dest)
                # copystat does *not* affect owner and group
                shutil.copystat(source, dest)
                if owner:
                    chown(owner, dest)
                if group:
                    chgrp(group, dest)

                files = os.listdir(source)
                if ignore:
                    ignored = ignore(source, files)
                else:
                    ignored = []

                for file in files:

                    source_path = os.path.join(source, file)
                    if source_path not in ignored:
                        copy(source_path, dest,
                             symlinks=symlinks, ignore=ignore, owner=owner, group=group, perms=perms)

        else:
            sh.cp(source, dest, preserve='all')
            log.debug('cp results: dest={}, owner=={}, group=={}, perms=={})'.
                format(dest, os.stat(dest).st_uid, os.stat(dest).st_gid, oct(getmode(dest))))
            # delete these 2 lines if the cp --preserve above works
            #shutil.copy(source, dest)
            #shutil.copystat(source, dest)
            if owner:
                chown(owner, dest)
            if group:
                chgrp(group, dest)
            if perms:
                chmod(perms, dest)
            log.debug('copy results: dest={}, owner=={}, group=={}, perms=={}, set perms=={})'.
                format(dest, os.stat(dest).st_uid, os.stat(dest).st_gid, oct(getmode(dest)), perms))

def merge(source, dest, symlinks=True, ignore=None, owner=None, group=None, perms=None):
    ''' Merge source to dest dir.

        Like shutil.copytree(), but merges with existing dest dir.
        Unlike shutil.copytree(), symlinks=Truee. This symlinks behavior is
        compatible with syr.fs.copy(), and seems to almost always be what we want.

        Set ownership and permissions from keywords, or if None copy from
        the corresponding source file.
    '''

    """ Largely copied frpm http://code.activestate.com/lists/python-list/191783/
        which in turn is largely copied from shutil.copytree(). """

    if not os.path.exists(source):
        raise ValueError('source "{}" does not exist'.format(source))

    if not os.path.isdir(dest):
        raise ValueError('dest "{}" must be a dir'.format(dest))

    #log.debug('merge(source={}, dest={}, symlinks=={}, ignore=={}, owner=={}, group=={}, perms=={})'.
    #    format(source, dest, symlinks, ignore, owner, group, perms))

    names = os.listdir(source)
    if ignore is not None:
        ignored_names = ignore(source, names)
    else:
        ignored_names = set()

    errors = []

    for name in names:
        if name not in ignored_names:

            sourcename = os.path.join(source, name)
            destname = os.path.join(dest, name)

            try:
                if symlinks and os.path.islink(sourcename):
                    linkto = os.readlink(sourcename)
                    #log.debug('merge() symlink({}, {})'.format(linkto, destname)) #DEBUG
                    if os.path.exists(destname):
                        os.remove(destname)
                    os.symlink(linkto, destname)
                elif os.path.isdir(sourcename):
                    if not os.path.isdir(destname):
                        mode = getmode(sourcename)
                        #log.debug('merge() makedirs({}, {})'.format(destname, mode)) #DEBUG
                        makedir(destname, perms=mode)
                    merge(sourcename, destname,
                        symlinks, ignore,
                        owner, group, perms)
                else:
                    #log.debug('merge() copy2({}, {})'.format(sourcename, destname)) #DEBUG
                    shutil.copy2(sourcename, destname)
                    if owner:
                        chown(owner, destname)
                    if group:
                        chgrp(group, destname)

                    mode = perms or getmode(sourcename)
                    #log.debug('  src mode: {}'.format(oct(getmode(sourcename)))) #DEBUG
                    chmod(mode, destname)
                # XXX What about devices, sockets etc.?

            except (IOError, os.error), why:
                errors.append((sourcename, destname, str(why)))

            # catch the shutil.Error from the recursive merge so that we can
            # continue with other files
            except shutil.Error, err:
                errors.extend((sourcename, destname, err.args[0]))

    if errors:
        raise shutil.Error, errors

def move(source, dest, owner=None, group=None, perms=None):
    ''' Move source to dest.

        move() tries to generally follow the behavior of the
        'mv --force' command.

        move() creates any missing parent dirs of dest.

        If dest is a dir, source is copied into dest.

        Otherwise, source will overwrite any existing dest.

        >>> import os.path, sh, tempfile

        >>> def temp_filename(dir=None):
        ...     if dir is None:
        ...         dir = test_dir
        ...     handle, path = tempfile.mkstemp(dir=dir)
        ...     # we don't need the handle
        ...     os.close(handle)
        ...     return path
        >>>
        >>> test_dir = tempfile.mkdtemp()
        >>>
        >>> # test move to dir
        >>> source = temp_filename()
        >>> dest_dir = tempfile.mkdtemp(dir=test_dir)
        >>> move(source, dest_dir)
        >>> assert not os.path.exists(source)
        >>> basename = os.path.basename(source)
        >>> assert os.path.exists(os.path.join(dest_dir, basename))
        >>>
        >>> # test move to new filename
        >>> source = temp_filename()
        >>> dest_filename = temp_filename(dir=test_dir)
        >>> move(source, dest_filename)
        >>>
        >>> # test move to existing filename
        >>> DATA = 'data'
        >>> source = temp_filename()
        >>> dest_filename = temp_filename()
        >>> with open(source, 'w') as sourcefile:
        ...     sourcefile.write(DATA)
        >>> move(source, dest_filename)
        >>> assert not os.path.exists(source)
        >>> assert os.path.exists(dest_filename)
        >>> with open(dest_filename) as destfile:
        ...     assert DATA == destfile.read()
        >>>
        >>> # clean up
        >>> sh_result = sh.rm('--force', '--recursive', test_dir)
        >>> assert sh_result.exit_code == 0
    '''

    parent_dir = os.path.dirname(dest)
    if not os.path.exists(parent_dir):
        makedir(parent_dir, owner=owner, group=None, perms=None)
    sh.mv('--force', source, dest)

    if owner:
        chown(owner, dest)
    if group:
        chgrp(group, dest)
    if perms:
        chmod(perms, dest)

def clonedirs(sourceroot, destroot, destdir, owner=None, group=None, perms=None):
    ''' Make destdir within destroot. Make any needed intermediate-level
        directories.

        Any mountpoints in sourceroot are unmounted.

        The destdir is relative, and so can not start with '/'.

        Set ownership and permissions from keywords, or if None copy from
        the corresponding dir in sourceroot.

        Only directories are cloned, not data files.

        >>> testroot = '/tmp/test-clonedirs'
        >>> sourceroot = os.path.join(testroot, '1')
        >>> destroot = os.path.join(testroot, '2')
        >>> destdir = 'x/y/z'

        >>> if os.path.exists(sourceroot):
        ...     shutil.rmtree(sourceroot)
        >>> if os.path.exists(destroot):
        ...     shutil.rmtree(destroot)
        >>> assert not os.path.exists(sourceroot)
        >>> assert not os.path.exists(destroot)

        >>> sourcepath = os.path.join(sourceroot, destdir)
        >>> makedir(sourcepath)

        >>> makedir(destroot)

        >>> destpath = os.path.join(destroot, destdir)
        >>> assert not os.path.exists(destpath)
        >>> clonedirs(sourceroot, destroot, destdir)
        >>> assert os.path.isdir(destpath)
    '''

    if not os.path.exists(sourceroot):
        raise ValueError('dir does not exist: {}'.format(sourceroot))
    if not os.path.exists(destroot):
        raise ValueError('dir does not exist: {}'.format(destroot))
    if destdir.startswith('/'):
        raise ValueError(
            'dest dir must be relative. It can not start with /: {}'.
            format(destdir))

    sourcepath = os.path.join(sourceroot, destdir)
    destpath = os.path.join(destroot, destdir)

    log.debug('clonedirs sourcepath={}, destpath={}'.format(sourcepath, destpath))
    if type(perms) is int:
        log.debug('   owner={}, group={}, perms={}'.format(owner, group, oct(perms)))
    else:
        log.debug('   owner={}, group={}, perms={}'.format(owner, group, perms))

    # a chroot might have active mounts
    umount_all(sourcepath)

    if os.path.exists(destpath):
        # if it's a dir, we're done
        if os.path.isfile(destpath):
            raise ValueError('dest dir is not a dir: {}'.format(destdir))

    else:
        # make any needed parent dirs
        parent = os.path.dirname(destdir)
        clonedirs(sourceroot, destroot, parent, owner, group, perms)

        perms = perms or getmode(sourcepath)
        makedir(destpath, perms=perms)

        if owner:
            chown(owner, destpath)
        if group:
            chgrp(group, destpath)

def remove(path):
    ''' Remove the path.

        If path is a dir, empty it first by rsyncing an empty dir to the 
        path. With a large directory this is much faster than rm or 
        shutil.rmtree().
        
        It is not an error if the path does not exist.

        If path is a link, only remove the link, not the target.
        
        If path is a mount, raise ValueError.
    '''

    global empty_dir

    if os.path.exists(path):

        if empty_dir is None:
            empty_dir = tempfile.mkdtemp(prefix='syr.fs.empty.')

        if os.path.ismount(path):
            raise ValueError('path is mount point: {}'.format(path))

        elif os.path.islink(path) or os.path.isfile(path):
            sh.rm('--force', path)

        else:
            assert os.path.isdir(path)

            # empty the dir using rsync for speed
            sh.rsync('--archive', '--delete',
                empty_dir + '/',
                path + '/')
            if os.listdir(path):
                log.warning('remove() dir not empty after rsync: {}\n{}'.format(
                    path, sh.ls('-al', path)))
            sh.rm('--force', '--recursive', path)

        assert not os.path.exists(path), 'could not remove {}'.format(path)

def relative_path(path):
    ''' Return path as relative path, with no leading or trailing '/'. '''
    
    return path.strip('/')
    
def filemode(st_mode):
    ''' Convert integer file permissions to an octal string.
    
        Function named after python 3.3 os.stat.filemode(). 
    
        See python - How to convert a stat output to a unix permissions string - Stack Overflow
            http://stackoverflow.com/questions/17809386/how-to-convert-a-stat-output-to-a-unix-permissions-string
            
        >>> import os, stat, tempfile
        
        >>> fd, filename = tempfile.mkstemp()
        >>> os.close(fd)
        
        >>> # rwx for user and group
        >>> os.chmod(filename, stat.S_IRWXU | stat.S_IRWXG)
        
        >>> filemode(os.stat(filename).st_mode)
        '-rwxrwx---'
        
        >>> os.remove(filename)
    '''
    
    try:
        if S_ISDIR(st_mode):  
            is_dir = 'd' 
        else:
            is_dir = '-'
    except:
        is_dir = '-'
    octal_to_readable = {
        '7':'rwx', 
        '6' :'rw-', 
        '5' : 'r-x', 
        '4':'r--', 
        '3':'-wx', 
        '2':'-w-', 
        '1':'--x', 
        '0': '---'}
    perm = str(oct(st_mode)[-3:])
    return is_dir + ''.join(octal_to_readable.get(x,x) for x in perm)
    
@contextmanager
def restore_file(filename):
    ''' Context manager restores a file to its previous state. 
    
        If the file exists on entry, it is backed up and restored.
        
        If the file does not exist on entry and does exists on exit, 
        it is deleted. 
    '''
        
    exists = os.path.exists(filename)
    
    if exists:
        # we just want the pathname, not the handle
        # tiny chance of race if someone gets the temp filename
        handle, backup = tempfile.mkstemp()
        os.close(handle)
        log('restore_file() backing up "{}" to "{}"'.format(filename, backup))
        sh.cp('--archive', filename, backup)
    else:
        log('restore_file() not backing up "{}" because does not exist'.format(filename))
        
    try:
        yield
        
    finally:
        if os.path.exists(filename):
            sh.rm(filename)
        if exists:
            log('restore_file() restoring "{}" from "{}"'.format(filename, backup))
            # restore to original state
            sh.mv(backup, filename)
        else:
            log('restore_file() not restoring "{}" because did not exist'.format(filename))
            
def edit_file_in_place(filename, replacements, regexp=False, lines=False):
    """ Replace text in file. 
    
        'replacements' is a dict of {old: new, ...}.
        Every occurence of each old string is replaced with the 
        matching new string.
        
        If regexp=True, the old string is a regular expression.
        If lines=True, each line is matched separately.
        
        Perserves permissions.
        
        >>> # note double backslashes because this is a string within a docstring
        >>> text = (
        ...     'browser.search.defaultenginename=Startpage HTTPS\\n' +
        ...     'browser.search.selectedEngine=Startpage HTTPS\\n' +
        ...     'browser.startup.homepage=https://tails.boum.org/news/\\n' +
        ...     'spellchecker.dictionary=en_US')
        
        >>> f = tempfile.NamedTemporaryFile(mode='w', delete=False)
        >>> f.write(text)
        >>> f.close()
        
        >>> HOMEPAGE = 'http://127.0.0.1/'
        >>> replacements = {
        ...     'browser.startup.homepage=.*':
        ...         'browser.startup.homepage={}'.format(HOMEPAGE),
        ...     }
        
        >>> edit_file_in_place(f.name, replacements, regexp=True, lines=True)
        
        >>> with open(f.name) as textfile:
        ...     newtext = textfile.read()
        >>> assert HOMEPAGE in newtext
        
        >>> os.remove(f.name)
    """
    
    # read text
    mode = os.stat(filename).st_mode
    with open(filename) as textfile:
        text = textfile.read()
    
    if lines:
        newtext = []
        for line in text.split('\n'):
            newline = syr.utils.replace_strings(line, replacements, regexp)
            newtext.append(newline)
        text = '\n'.join(newtext)
    else:
        text = syr.utils.replace_strings(text, replacements, regexp)
    
    # write text
    with open(filename, 'w') as textfile:
        textfile.write(text)
    os.chmod(filename, mode)
    assert mode == os.stat(filename).st_mode

def replace_file(filename, content):
    """ Replace file content.
    
        Perserves permissions.
    """
    
    mode = os.stat(filename).st_mode
    with open(filename, 'w') as f:
        f.write(content)
    os.chmod(filename, mode)
    assert mode == os.stat(filename).st_mode
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
