'''
    Chroot.

    Copyright 2014 GoodCrypto
    Last modified: 2014-09-22

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os, os.path, sh

import syr.cli, syr.log

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
    
    REQUIRED_ROOT_DIR_SUBDIRS = ['dev', 'etc', 'proc', 'selinux', 'sys', 'var']
    REQUIRED_PROGRAMS = ['mount', 'umount']
    
    CHROOT_ABSOLUTE_PATH = sh.which('chroot')
    
    def __init__(self, directory):
        ''' Initialize chroot. 
        
            'directory' is the chroot directory.
        '''
        
        def validate_chroot(directory):
            ''' Validate chroot directory. '''
            
            for subdir in Chroot.REQUIRED_ROOT_DIR_SUBDIRS:
                if not os.path.isdir(os.path.join(directory, subdir)):
                    raise ChrootException(
                        '"{}" does not appear to be a chroot dir'.
                        format(command))
    
            for program in REQUIRED_PROGRAMS:
                try:
                    self.run_raw('which', program)
                except:
                    raise ChrootException(
                        'cannot execute commands in chroot without a "{}" command'.
                        format(program))
            
        validate_chroot(directory)
        self.directory = directory

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
            
        if self.log:
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
            log.debug('sh_chroot "{}"'.format(cmdstr))
            
        self.mount_pseudo_filesystems()
        try:
            result = self.run_raw(command, *args, **kwargs)
        
        finally:
            self.unmount_pseudo_filesystems()
            
        return result
            
    def run_raw(self, command, *args, **kwargs):
        ''' Run shell command in chroot with no setup or cleanup. '''
        
        def sh_error(result):
            if self.log:
                self.log.warning(result)
                if result.exit_code:
                    self.log.warning('exit code: {}'.format(result.exit_code))
                if result.stdout:
                    self.log.warning('STDOUT {}'.format(result.stdout))
                if result.stderr:
                    self.log.warning('STDERR {}'.format(result.stderr))
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
    
    def mount_pseudo_filesystems(self):
        ''' Mount pseudo filesystems in chroot '''
        
        # Debian Wiki chroot page says wheezy automatically mounts proc and sys
        # but it doesn't mount /proc, at least
        # see chroot - Debian Wiki
        #     https://wiki.debian.org/chroot#Mounting_pseudo_filesystems
        
        # tails iso psuedo filesystems after boot:
        #   proc on /proc type proc (rw,noexec,nosuid,nodev)
        #   sysfs on /sys type sysfs (rw,noexec,nosuid,nodev)
        #   udev on /dev type tmpfs (rw,mode=0755)
        #   devpts on /dev/pts type devpts (rw,noexec,nosuid,gid=5,mode=620)
    
        if self.log:
            self.log.debug('mount /dev/pts in chroot before chrooting')
        # rbind, not bind
        # !! maybe not rbind
        # We want rbind if we mount all of /dev, because there may well be 
        # nested mounts within /dev. But is there any chance of mounts
        # within /dev/pts? If not, we want to use bind, not rbind.
        # see Gentoo Forums :: View topic - openpty failed: 'out of pty devices' why it looks for?
        #     http://forums.gentoo.org/viewtopic-t-725408-start-0.html
        dev_pts_dir = os.path.join(self.directory, 'dev/pts')
        if not os.path.exists(dev_pts_dir):
            raise ChrootException('cannot execute commands in chroot without a /dev/pts')
        sh.mount('/dev/pts', dev_pts_dir, bind=True)
        # you can't change mount options during --bind; you have to remount
        sh.mount('-o', 'remount,nosuid', dev_pts_dir)
            
        if self.log:
            self.log.debug('mount /proc in chroot before chrooting')
            
        # Use a meaningful psuedo-device name with mount instead of "none" 
        # so umount doesn't give the misleading message "none busy".
        self.run_raw('mount', '-t', 'proc', 'proc', '/proc')
        #self.run_raw('mount', '-t', 'sysfs', 'sysfs', '/sys')
    
    def unmount_pseudo_filesystems(self):
        ''' Unmount pseudo filesystems in chroot '''

        self.run_raw('umount', '/proc')
        self.run_raw('umount', '/dev/pts')
        
if __name__ == "__main__":
    import doctest
    doctest.testmod()
