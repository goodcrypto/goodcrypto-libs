'''
    Abstract classes are defined differently between python 2 and 3.
    A syntax error is thrown if you even include the python3 format
    in python 2 code (even inside guards that prevent the code from executing).

    This is the appropriate definition for python 3.

    Copyright 2016 GoodCrypto
    Last modified: 2016-04-23

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

from abc import ABCMeta

class AbstractPythonClass(object, metaclass=ABCMeta):
    ''' Abstract class for python 3. '''

    pass

