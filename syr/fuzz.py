'''
    Fuzzers.

    Copyright 2013-2014 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

import random, sh

from syr import utils

def random_fuzz(data, ratio, seed=None):
    ''' Randomly fuzz input using zzuf.

        'data' is an iterable to fuzz. To fuzz ints and floats, use the
        random package.

        'ratio' is a a float saying how many bits to fuzz. For example, if
        ratio is 0.1, 10% of data bits are fuzzed.

        'seed' is an integer seed for the random fuzzing. Default is a
        random integer.

        Returns data with 'ratio' bits randomly fuzzed.

        >>> data = bin(utils.randint())
        >>> ratio = 0.5
        >>> fuzzed = random_fuzz(data, ratio)
        >>> assert data != fuzzed, 'data: {}, fuzzed: {}'.format(data, fuzzed)
    '''

    if seed is None:
        seed = utils.randint()

    try:
        iter(data)

    except TypeError:
        raise ValueError('data must be iterable')

    result = sh.zzuf('--ratio=0.01', '--seed={}'.format(seed), _in=data)
    return result.stdout

if __name__ == "__main__":
    import doctest
    doctest.testmod()
