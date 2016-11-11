'''
    Transfer files using rsync.

    This should probably be generalized as an interface to command line programs.

    Copyright 2010-2016 GoodCrypto
    Last modified: 2016-04-23

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import os, sh
from syr.log import get_log

log = get_log()

def update(source, dest, **kwargs):
    ''' Update directory using rsync.

        The destination directory must already exist.

        This function deletes files. Use dry-run=True (--dry-run)
        to see which files it will delete. If delete=False rsync
        will not delete files and directories in the dest that
        are not in the source. The default is delete=True.

        Rsync usually will not delete any files on the destination, even
        if those files are no longer on the source. Again, this function
        can files on the destination.

        Additional keyword args are passed to rsync.

        >>> from glob import glob
        >>> def remove_dir(dir):
        ...     if os.path.isdir(dir):
        ...         for f in glob(dir + '/*'):
        ...             if os.path.isdir(f):
        ...                 remove_dir(f)
        ...             else:
        ...                 os.remove(f)
        ...     os.rmdir(dir)
        >>> def create_test_dir(dir):
        ...     os.mkdir(dir)
        ...     f = open('%s/%s' % (dir, dir),'a')
        ...     f.close()
        >>>
        >>> os.chdir('/tmp')
        >>> remove_dir('test_rsync')
        >>> os.mkdir('test_rsync')
        >>> os.chdir('test_rsync')
        >>>
        >>> create_test_dir('a')
        >>> os.chdir('a')
        >>> create_test_dir('c')
        >>> os.chdir('..')
        >>>
        >>> create_test_dir('b')
        >>> glob('b/*')
        ['b/b']
        >>>
        >>> update('a', 'b')
        >>> sorted(glob('b/*'))
        ['b/a', 'b/c']
        >>>
        >>> glob('b/c/*')
        ['b/c/c']
    '''

    if os.path.isdir(source) and not source.endswith('/'):
        source = source + '/'

    rsync(source, dest, recursive=True, **kwargs)

def transfer(source, dest, **kwargs):
    ''' Transfer files using rsync.

        This function eliminates rsync's quirky interpretation of
        source directories. With the command line rsync, but not with
        transfer():
            * a trailing slash means the files in the dir are copied,
              but not the dir itself
            * no trailing slash means the dir is copied with its files

        To transfer the contents of a directory without the enclosing
        source directory, simply call transfer() once for each of the files
        or subdirectories, or use rsync.update(). E.g:

            for source in iglob(dev_dir + '/*'):
                transfer(source=source, dest=testing_dir)
        '''

    if source.endswith('/'):
        source = source[:-1]

    rsync(source, dest, recursive=True, **kwargs)

def rsync(source, dest, **kwargs):
    ''' Python interface to rsync.

        This function could be generalized to interface to many
        command line programs.

        Default args to rsync are "--rsh=ssh --links --delay-updates".
        You can change these defaults with "no_OPTION" keywords, which are
        passed to rsync as "--no-OPTION" flags.

        The "debug" keyword causes the rsync command to print.

        Keywords parameters (other than "debug") are passed to rsync as
        command line flags. A keyword value of True is passed as a flag
        without any value. Underlines in keywords are replaced by dashes.
        Examples:
            * To pass "--bwlimit=100" to rsync, pass the keyword parameter
              "bwlimit=100" to transfer().
            * For "--verbose" use "verbose=True".
            * For "--temp-dir=/tmp" use "temp_dir='/tmp'".
            * For "--no-OPTION" use "no-OPTION=True".

        SSH transfers, the default, are more secure and allow unattended
        operation if you don't use user interactive authentication such as
        passwords.

        In rsync --partial doesn't work well, but --partial-dir works worse.
        If a transfer does not complete, without --partial or --partial-dir
        rsync deletes the destination file, which is very wasteful on large
        file transfers. Using --partial can leave an incomplete file in
        place, but --partial-dir seems buggy.

        Be careful specifying a tempdir. Some destination systems (i.e.
        osx) don't have a "/temp" directory.

        Exclude pathnames are globbed. E.g. you can exclude all bazaar files with
            exclude='*bzr*'
        '''

    ''' We'd like to use  --delay-updates to make the rsync more atomic.
        It's better not to leave the dest dir in an inconsistent state.
        But it's usually more important that a large transfer doesn't have to
        restart from the beginning if rsync is interrupted

        Also if rsync is interrupted with --delay-updates, rsync leaves many hidden
        temporary files and directories. To avoid orphan hidden files you can include
        '--partial-dir=/tmp/rsync-partial-dir'. But that doesn't help you resume
        large transfers.

        An orphan hidden file for '/user/src/abc/xyz' will look like '/user/src/abc/.xyz.H7JG5DV0'
        It is the transferred filename prefixed with a dot and suffixed with a dot and unique ending.
        An orphan hidden temporary subdir is named '.~tmp~'. '''

    assert os.path.exists(source), 'rsync source does not exist: %s' % source

    kwargs.update(dict(
        rsh = ssh,
        links = True,
        # partial_dir = '/tmp/rsync-partial-dir',
        log_file = '/tmp/rsync.log',
        ))

    # verbose is used by this function and is also an rsync keyword
    verbose = 'verbose' in kwargs

    # debug is used by this function but is not an rsync keyword
    debug = 'debug' in kwargs
    if debug:
        del kwargs['debug']

    """
    command = 'rsync %s "%s" "%s"' % (args, source, dest)
    log(command)
    if verbose or debug:
        print(command)
    """

    sh.rsync(command, source, dest, **kwargs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
