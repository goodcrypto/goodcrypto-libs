'''
    OS identification.

    Copyright 2008-2014 GoodCrypto
    Last modified: 2014-07-17

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import platform

def get_os_name():
    ''' Return the name of the OS in lower case. '''
    return platform.system().lower()

def is_windows():
    ''' Return True if the underlying OS is any variant of Windows. '''
    osname = get_os_name()
    return osname.startswith("win") or osname.startswith("microsoft windows")

def is_windows_vista():
    ''' Return True if the underlying OS is Windows Vista. '''
    winVista = False
    osname = get_os_name()
    if is_windows():
        winVista = osname.find("vista") > 0
    return winVista

def is_windows7():
    ''' Return True if the underlying OS is Windows 7. '''
    win7 = False
    osname = get_os_name()
    if is_windows():
        win7 = osname.find("7") > 0
    return win7

def is_windows8():
    ''' Return True if the underlying OS is Windows 8. '''
    win8 = False
    osname = get_os_name()
    if is_windows():
        win8 = osname.find("8") > 0
    return win8

def is_windows_xp():
    ''' Return True if the underlying OS is Windows XP. '''
    winXP = False
    osname = get_os_name()
    if is_windows():
        #  sometimes XP falsely reports that its W2K
        if osname.find("xp") > 0 or osname.find("2000") > 0:
            winXP = True
    return winXP

def is_unix():
    ''' Return True if the underlying OS is any variant of unix. '''
    osname = get_os_name()
    return osname.find("unix") >= 0 or is_linux() or is_aix() or is_hp_unix() or is_solaris() or is_mac_os_x()

def is_linux():
    ''' Return True if the underlying OS is Linux. '''
    osname = get_os_name()
    return osname.find("linux") >= 0

def is_aix():
    ''' Return True if the underlying OS is IBM's AIX. '''
    osname = get_os_name()
    return osname.find("aix") >= 0

def is_hp_unix():
    ''' Return True if the underlying OS is HP's unix. '''
    osname = get_os_name()
    return osname.find("hp-ux") >= 0 or osname.find("hpux") >= 0 or osname.find("irix") >= 0

def is_solaris():
    ''' Return True if the underlying OS is Solaris. '''
    osname = get_os_name()
    return osname.find("solaris") >= 0 or osname.find("sunos") >= 0

def is_mac_os_x():
    ''' Return True if the underlying OS is Mac OS X. '''
    osname = get_os_name()
    return osname.find("mac os x") >= 0

def is_mac():
    ''' Return True if the underlying OS is any variant of Mac. '''
    osname = get_os_name()
    return osname.find("mac os") >= 0 or osname.find("macos") >= 0
    
