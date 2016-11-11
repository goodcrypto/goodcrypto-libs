'''
    Chroot.

    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-04-23

    To do: Include functionality from dbuild.rootdir.temp_chroot().

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

from contextlib import contextmanager
import os, os.path, sh

import syr.cli, syr.fs, syr.log

from syr.log import get_log
log = get_log()

class ChrootException(Exception):
    ''' Chroot exception. '''
    pass

class Chroot(object):
    ''' Chroot.

        >>> import os, os.path, sh

        >>> # this has to be a dir with /dev/pts, mount, umount, etc.
        >>> dir = '/var/local/projects/goodcrypto/build/data/dist/new_root'
        >>> if os.path.exists(dir):
        ...     filename = '_xyzzy'
        ...     path = os.path.join(dir, filename)
        ...     result = sh.touch(path)
        ...     output = Chroot(dir).run('ls', filename, '-1').stdout
        ...     assert output.strip() == filename
        ...     result = sh.rm(path)
    '''

    # a chroot dir is defined as a dir that has all REQUIRED_ROOT_DIR_SUBDIRS
    REQUIRED_ROOT_DIR_SUBDIRS = [
        'bin', 'dev', 'etc', 'lib', 'proc', 'sbin', 'sys', 'tmp', 'usr', 'var']
    REQUIRED_PROGRAMS = [] # ['mount', 'umount']

    CHROOT_ABSOLUTE_PATH = sh.which('chroot')

    def __init__(self, directory, bind=False):
        ''' Initialize chroot.

            'directory'::
                Chroot directory.
            'bind'::
                If bind=True then  use "mount --bind" for pseudo-filesystems.
                Default is False. As of late 2015 jessie's chroot usually
                handles pseudo-filesystems without explicit mounting and
                unmounting.
        """

        '''

        def validate_chroot(directory):
            ''' Validate chroot directory. '''

            for subdir in Chroot.REQUIRED_ROOT_DIR_SUBDIRS:
                if not os.path.isdir(os.path.join(directory, subdir)):
                    raise ChrootException(
                        '"{}" does not appear to be a chroot dir'.
                        format(directory))

            for program in Chroot.REQUIRED_PROGRAMS:
                try:
                    self.run_raw('which', program)
                except:
                    raise ChrootException(
                        '"{}" command required in chroot'.
                        format(program, directory))

        validate_chroot(directory)
        self.directory = directory
        self.bind = bind
        # if another process has already mounted a dir, don't disturb it
        self.was_mounted = set()

    def log(self, msg):
        log.debug('{}: {}'.format(self.directory, msg))

    def log_warning(self, msg):
        log.warning('{}: {}'.format(self.directory, msg))

    def run(self, command, *args, **kwargs):
        ''' Run shell command in chroot.

            'command' is the command name to run in the chroot directory.
            Other arguments and returned results are passed to 'command', as
            specified by the sh module.

            args are command line positional arguments. kwargs become
            command line flag arguments. If the flag has no arguments of
            its own, set the keyword to True.

            Single letter keywords are prefixed with a single dash:

                'a=True' becomes '-a'
                'b=1' becomes '-b=1'

            Keywords more than one letter long are prefixed with a double
            dash:

                'aaa=True' becomes '--aaa'
                'bbb=1' becomes '--bbb=1'

            Keyword arguments appear at the end of the command line. If a
            command needs flags to appear before some positional arguments,
            specify the flags explicitly as positional arguments:

                chroot.run(command, '-a', a, '--bbb', bbb, ...)

            Also specify flags with are not python identifiers as
            positional arguments:

                chroot.run(command, '-5', ...)
        '''

        if '_log' in kwargs:
            self.log = kwargs['_log']
            del kwargs['_log']
        else:
            self.log = None

        # log the command
        cmdstr = ''
        for arg in args:
            if cmdstr:
                cmdstr += ' '
            cmdstr += str(arg)
        for key, value in kwargs.items():
            if cmdstr:
                cmdstr += ' '
            cmdstr += '{}={}'.format(key, value)
        self.log.debug('sh_chroot "{}"'.format(cmdstr))

        with self.pseudo_filesystems():
            result = self.run_raw(command, *args, **kwargs)

        return result

    def run_raw(self, command, *args, **kwargs):
        ''' Run shell command in chroot with no setup or cleanup. '''

        def sh_error(result):
            self.log_warning(result)
            if result.exit_code:
                self.log_warning('exit code: {}'.format(result.exit_code))
            if result.stdout:
                self.log_warning('STDOUT {}'.format(result.stdout))
            if result.stderr:
                self.log_warning('STDERR {}'.format(result.stderr))

            raise ChrootException(result)

        # very minimal chroot env
        if '_env' in kwargs:
            env = kwargs['_env']
            del kwargs['_env']
        else:
            env = syr.cli.minimal_env()

        sh_command = sh.Command(Chroot.CHROOT_ABSOLUTE_PATH)
        try:
            result = sh_command(self.directory, command, *args, _env=env, **kwargs)

            if result.exit_code or result.stderr:
                sh_error(result)

        except sh.ErrorReturnCode as erc:
                sh_error(erc)

        return result

        pass

    def bind_mount_pseudo_filesystems(self):
        ''' Mount pseudo filesystems in chroot '''

        """
            The behavior of debian pseudo filesystems is constantly changing.

            This simple "mount --bind" is suggested unofficially in several places.
            See "boot - How do I run update-grub from a LiveCD? - Ask Ubuntu"
                    http://askubuntu.com/questions/145241/how-do-i-run-update-grub-from-a-livecd
                "update-grub2 in a chroot | AnySpeak.Org"
                    https://www.anyspeak.org/update-grub2-in-a-chroot/

        """

        for psuedo_fs in [
            'sys',
            'proc',
            'dev',
            ]:

            mount_point = os.path.join(self.directory, psuedo_fs)
            if syr.fs.mounted(mount_point):
                self.was_mounted.add(mount_point)
                log.debug('{} already mounted in {}'.format(psuedo_fs, self.directory))
            else:
                syr.fs.mount('--bind', '/'+psuedo_fs, mount_point)
                assert syr.fs.mounted(mount_point), 'could not mount {}'.format(mount_point)

    def bind_unmount_pseudo_filesystems(self):
        ''' Unmount pseudo filesystems in chroot. '''

        for psuedo_fs in [
            'sys',
            'proc',
            'dev'
            ]:

            mount_point = os.path.join(self.directory, psuedo_fs)

            if mount_point in self.was_mounted:
                log.debug('not unmounting {} because originally was mounted)'.format(mount_point))

            else:
                if syr.fs.mounted(mount_point):
                    # try to unmount inside the chroot
                    try:
                        self.run_raw('umount', '/' + psuedo_fs)
                    except Exception as exc:
                        # just log it
                        log.debug(exc)

                if syr.fs.mounted(mount_point):
                    # try to unmount from outside the chroot
                    try:
                        syr.fs.unmount(mount_point)
                    except Exception as exc:
                        log.debug(exc)
                        raise

                log.debug('about to assert not mounted: {}'.format(mount_point))
                assert not syr.fs.mounted(mount_point), 'could not unmount {}'.format(mount_point)

    def OLD_mount_pseudo_filesystems(self):
        ''' Mount pseudo filesystems in chroot '''

        """
            The behavior of debian pseudo filesystems is constantly changing.

            Is it better to mount some or all of these inside the chroot?

            See:
                chroot - Debian Wiki
                https://wiki.debian.org/chroot
                Debootstrap - Debian Wiki
                https://wiki.debian.org/Debootstrap

            From https://wiki.debian.org/chroot::

                In the primary filesystem, NOT the chroot:

                    /etc/fstab should look something like:

                        /dev $CHROOT/dev auto bind 0 0
                        /dev/pts $CHROOT/dev/pts auto bind 0 0
                        /proc $CHROOT/proc auto bind 0 0

                    in /etc/rc.local (or init.d, or in a chroot wrapper such as chr):

                        mount --bind /dev/pts $CHROOT/dev/pts

            From https://wiki.debian.org/Debootstrap::

                    main # echo "proc $MY_CHROOT/proc proc defaults 0 0" >> /etc/fstab
                    main # mount proc $MY_CHROOT/proc -t proc
                    main # echo "sysfs $MY_CHROOT/sys sysfs defaults 0 0" >> /etc/fstab
                    main # mount sysfs $MY_CHROOT/sys -t sysfs
                    main # cp /etc/hosts $MY_CHROOT/etc/hosts
                    main # cp /proc/mounts $MY_CHROOT/etc/mtab

            The jessie debootstrap man page has very similar instructions, except
            it does not include::

                main # cp /proc/mounts $MY_CHROOT/etc/mtab

            For wheezy we also had to mount /dev/pts::

                mount_point = path_in_new_root(specs, 'dev/pts')
                while mount_point in syr.fs.mount().str():
                    workdir.umount_path(specs, mount_point)
                workdir.mount(specs, '/dev/pts', mount_point, bind=True)
                # sh_chroot_raw(specs, 'mount', '-o', 'remount,nosuid', mount_point)
                syr.fs.mount('-o', 'remount,nosuid', mount_point)

            Debian Wiki chroot page says wheezy automatically mounts proc and sys.
            But it doesn't mount /proc, at least. Wheezy chroot detects when you
            need /proc, and the error messsage tells you to mount it inside the
            chroot.

            Use a meaningful pseudo-device name with mount instead of "none"
            so umount doesn't give the misleading message "none busy".

            tails iso pseudo filesystems after boot:
              proc on /proc type proc (rw,noexec,nosuid,nodev)
              sysfs on /sys type sysfs (rw,noexec,nosuid,nodev)
              udev on /dev type tmpfs (rw,mode=0755)
              devpts on /dev/pts type devpts (rw,noexec,nosuid,gid=5,mode=620)
        """

        """ At least in wheezy, it's common for /proc to already be
            mounted, because /proc/sys/fs/binfmt_misc didn't unmount.
            Why? a quick search gives no answer.
       """
       # sys and proc are very similar
        for psuedo_fs in [
            'sys',
            'proc',
            ]:

            mount_point = os.path.join(self.directory, psuedo_fs)
            if syr.fs.mounted(mount_point):
                self.was_mounted.add(mount_point)
                log.debug('{} already mounted in {}'.format(psuedo_fs, self.directory))
            else:
                if psuedo_fs == 'sys':
                    fs_type = 'sysfs'
                else:
                    fs_type = psuedo_fs
                syr.fs.mount(psuedo_fs, mount_point, '-t', fs_type)
                assert syr.fs.mounted(mount_point), 'could not mount {}'.format(mount_point)

        # possibly not needed in jessie
        dev_pts_dir = os.path.join(self.directory, 'dev/pts')
        if syr.fs.mounted(dev_pts_dir):
            self.was_mounted.add(dev_pts_dir)
            log.debug('dev/pts already mounted in {}'.format(self.directory))
        else:
            # self.log.debug('mount /dev/pts in chroot before chrooting')
            if not os.path.exists(dev_pts_dir):
                raise ChrootException('cannot execute commands in chroot without a /dev/pts')
            # bind or rbind? bind, at least for now
            # We want rbind if we mount all of /dev, because there may well be
            # nested mounts within /dev. But is there any chance of mounts
            # within /dev/pts? If not, we want to use bind, not rbind.
            # see Gentoo Forums :: View topic - openpty failed: 'out of pty devices' why it looks for?
            #     http://forums.gentoo.org/viewtopic-t-725408-start-0.html
            syr.fs.mount('/dev/pts', dev_pts_dir, bind=True)
            # you can't change mount options during --bind; you have to remount
            syr.fs.mount('-o', 'remount,nosuid', dev_pts_dir)
            assert syr.fs.mounted(dev_pts_dir), 'could not mount {}'.format(dev_pts_dir)

    def OLD_unmount_pseudo_filesystems(self):
        ''' Unmount pseudo filesystems in chroot '''

        for psuedo_fs in [
            'sys',
            'proc',
            # possibly not needed in jessie
            'dev/pts'
            ]:

            mount_point = os.path.join(self.directory, psuedo_fs)

            if mount_point in self.was_mounted:
                log.debug('not unmounting {} because originally was mounted)'.format(mount_point))

            else:
                if syr.fs.mounted(mount_point):
                    # try to unmount inside the chroot
                    try:
                        self.run_raw('umount', '/' + psuedo_fs)
                    except Exception as exc:
                        log.debug(exc)

                if syr.fs.mounted(mount_point):
                    # try to unmount from outside the chroot
                    syr.fs.unmount(mount_point)

                log.debug('about to assert not mounted: {}'.format(mount_point))
                assert not syr.fs.mounted(mount_point), 'could not unmount {}'.format(mount_point)

    @contextmanager
    def pseudo_filesystems(self):
        ''' Mount and automatically unmount chroot pseudo-filesystems.  '''

        if self.bind:
            self.bind_mount_pseudo_filesystems()
        try:
            yield
        finally:
            if self.bind:
                self.bind_unmount_pseudo_filesystems()

if __name__ == "__main__":
    import doctest
    doctest.testmod()
