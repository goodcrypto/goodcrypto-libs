'''
    Log for syr.log and modules it uses.

    The modules syr.log uses cannot use syr.log itself. Use syr.log instead
    of this module if you can. This module is much less efficient and
    powerful than syr.log. To debug this module use print().

    Functions that are used by both log and _log are here.

    Copyright 2015-2016 GoodCrypto
    Last modified: 2016-05-24

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import os, pwd, sh, time

def log(message, filename=None, mode=None):
    ''' Log message that syr.log can't. '''

    if filename is None:
        filename = '/tmp/_log.{}.log'.format(whoami())
    if mode is None:
        mode = '0666'

    # print(message)
    sh.touch(filename)
    try:
        sh.chmod(mode, filename)
    except sh.ErrorReturnCode_1:
        # hopefully the perms are already ok
        pass
    with open(filename, 'a') as logfile:
        try:
            logfile.write('{} {}\n'.format(timestamp(), message))
        except UnicodeDecodeError:
            from syr.python import is_string
            
            logfile.write('unable to write message because it is a type: {}'.format(type(message)))
            if not is_string(message):
                logfile.write('{} {}\n'.format(timestamp(), message.decode(errors='replace')))

def whoami():
    ''' Get user '''

    # without using syr.user.whoami()
    return pwd.getpwuid(os.geteuid()).pw_name

def timestamp():
    ''' Timestamp as a string. Duplicated in this module to avoid recursive
        imports. '''

    ct = time.time()
    if IS_PY2:
        milliseconds = int((ct - long(ct)) * 1000)
    else:
        milliseconds = int((ct - int(ct)) * 1000)
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    return '{},{:03}'.format(t, milliseconds)
