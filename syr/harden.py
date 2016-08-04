'''
    Harden a system.

    These functions generally need to be run as root. The exception is when
    a chroot is accessed from outside.

    Bluetooth and wi-fi are automatically installed by debian.
    None of the standard removal methods like rmmod have any apparent effect.
    So renamed to *-unused:
        /lib/modules/OS.VERSION/kernel/drivers/bluetooth
        /lib/modues/OS.VERSION/kernel/net/bluetooth, and
        /lib/modules/OS.VERSION/kernel/drivers/net/wireless
        /etc/init.d/bluetooth
    Renaming modules doesn't help when bluetooth etc. is in the kernel.

    Copyright 2013-2015 GoodCrypto
    Last modified: 2015-11-01

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

# delete in python 3
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os, os.path, sh, shutil, traceback
from glob import glob
from shutil import rmtree

import syr.fs

Bluetooth = 'bluetooth'
Wireless = 'wireless'
BadModules = [Bluetooth, Wireless]

service_script_text = """#! /bin/bash
name=$1
shift
exec /etc/init.d/$name "$@"
"""

def disable_selinux(chroot=None):
    ''' Disable selinux.

        Selinux is "security" code from NSA.
    '''

    badpath = fullpath('/selinux', chroot)

    if os.path.exists(badpath):
        rmtree(badpath)

def stop_rtkit():
    ''' Stop rtkit.

        It seems someone hid a rootkit in a program named rtkit.
        Probably made them giggle.
        We haven't noticed any ill effects from killing rtkit-daemon or goa-daemon
    '''

    for program in ['rtkit-daemon', 'goa-daemon']:
        try:
            sh.killmatch(program)
        except sh.SignalException_9:
            pass
        except:
            # "OSError: [Errno 9] Bad file descriptor"?
            # not worth diagnosing; just ignore it
            pass

def disable_ecdsa(chroot=None):
    ''' Disable elliptic curve dsa keys.

        We should disable all ec keys. After multiple corruptions by NSA
        of elliptic curve, it is an unnecessary risk.

        A debian update recreated these keys on 2014-04-06.
    '''

    for key in glob(fullpath('/etc/ssh/*ecdsa*', chroot)):
        os.remove(key)
    for key in glob(fullpath('/home/*/.ssh/*ecdsa*', chroot)):
        os.remove(key)

def uninstall_modemmanager(chroot=None):
    ''' Uninstall modemmanager to resists auto-installing modems.

        Who installs it? It does not seem have other packages dependent on it.
    '''

    try:
        sh.apt_get.purge('modemmanager')
    except:
        pass

def stop_wireless():
    ''' Try official ways to stop wireless such as nmcli and rfkill.

        These often leave the service enabled, or the service is re-enabled
        on boot.

        To do: check rmcomm piconets
    '''

    if not sh.which('nm'):
        sh.aptitude('install', 'nmcli')
    assert sh.which('nm')

    if not sh.which('service'):
        service_path = '/usr/local/sbin/service'
        with open(service_path, 'w') as service_file:
            service_file.write(service_script_text)
        os.chmod(service_path, 0755)
    assert sh.which('service')

    try:
        sh.nmcli('nm', 'wifi', 'off')
        sh.nmcli('nm', 'wwan', 'off')
    except:
        pass

    # rfkill block all
    try:
        #if not sh.which ('rfkill'):
        #    sh.aptitude('install', 'rfkill')
        #assert sh.which ('rfkill')
        sh.rfkill('block', 'all')
    except:
        # some variants of linux don't have /dev/rfkill,
        # so there's no program rfkill
        pass

    # /etc/init.d/bluetooth stop
    try:
        sh.service(Bluetooth, 'stop')
    except:
        try:
            sh.service(Bluetooth+'-unused', 'stop')
        except:
            pass

def disable_lib_modules(chroot=None):
    """ This doesn't help when bluetooth etc. are in the kernel.

        Bluetooth and wi-fi are automatically installed and enabled by debian.
        None of the standard disabling methods like rmmod have any apparent
        effect. So rename

            /lib/modules/.../bluetooth
            /lib/modules/.../wireless

        to *-unused.
    """

    for module in BadModules:
        lib_module_paths_text = sh.find(fullpath('/lib/modules', chroot))
        lib_module_paths = lib_module_paths_text.strip().split('\n')
        for path in lib_module_paths:
            if path.endswith('/{}'.format(module)):
                if os.path.exists(path):
                    try:
                        sh.mv('--force', path, path + '-unused')
                    except e:
                        print(e)

def disable_etc(chroot=None):
    '''Disable bluetooth etc. directories in /etc.'''

    for module in BadModules:
        etc_paths_text = sh.find(fullpath('/etc', chroot))
        etc_paths = etc_paths_text.strip().split('\n')
        for path in etc_paths:
            if path.endswith('/{}'.format(module)):
                if os.path.exists(path):
                    try:
                        sh.mv('--force', path, path + '-unused')
                    except e:
                        print(e)

def harden_ssh_server(chroot=None):
    ''' Harden ssh server.

        Require key authentication.
        Disable root login, challenge/response, passwords, X11 forwarding, or PAM.

        Consider using a nonstandard port to reduce log noise. The packages
        sshguard and fail2ban can help, but may be difficult to confure with a
        firewall.
    '''

    # only allow key acccess
    old_config_lines = {
        r'.*PermitRootLogin  .*': '',
        r'.*ChallengeResponseAuthentication .*': '',
        r'.*PasswordAuthentication .*': '',
        r'.*X11Forwarding .*': '',
        r'.*UsePAM .*': '',
        r'.*AcceptEnv  .*': '',
        }
    new_config_lines = [
        'PermitRootLogin no',
        'ChallengeResponseAuthentication no',
        'PasswordAuthentication no',
        'X11Forwarding no',
        'UsePAM no',
        # if we use a language other than English, uncomment the next line
        # 'AcceptEnv LANG LC_*',
        ]

    config_path = fullpath('/etc/ssh/sshd_config', chroot)

    if not os.path.exists(config_path):
        raise dBuild.excepts.BuildException('ssh not installed')

    # remove old config lines
    syr.fs.edit_file_in_place(config_path, old_config_lines, regexp=True, lines=True)
    # add new config lines
    with open(config_path, 'a') as config_file:
        config_file.write('\n# following lines added by goodcrypto harden_ssh_server()')
        for line in new_config_lines:
            config_file.write(line + '\n')

def make_dir_unused(standard_dir):
    ''' If the standard dir exists, then rename it to "-unused".

        It may be necessary to delete the dir, or at least move it to
        another dir tree with a different root.
    '''

    unused_dir = standard_dir + '-unused'

    if os.path.exists(standard_dir):
        if os.path.exists(unused_dir):
            shutil.rmtree(unused_dir)
        try:
            os.rename(standard_dir, unused_dir)
        except Exception:
            try:
                # if the rename fails, try mv
                sh.mv(standard_dir, unused_dir)
            except:
                pass

def fullpath(path, chroot):
    ''' Return full path, including chroot if any. '''

    if chroot:
        path = os.path.join(chroot, path.strip('/'))
    return path
