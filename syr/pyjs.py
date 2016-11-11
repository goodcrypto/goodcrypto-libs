#! /usr/bin/env python

'''
    Python to javascript compiler.

    Do not confuse this pyjs module with the python dialect at pyjs.org.

    Currently compiles RapydScript, a dialect of python designed to
    compile to javascript.

    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

assert False, 'Untested'

import sys
IS_PY2 = sys.version_info[0] == 2

import os
from tempfile import mkstemp
if IS_PY2:
    from cStringIO import StringIO
else:
    from io import StringIO

from rapydscript.compiler import parse_file, finalize_source

def compile(py):
    ''' Compile python to javascript.

        As of 2012-01 RapydScript does not have a module function that
        compiles. Compiling requires a source file, not a stream or string.
'''
    # save py code to file
    rsfile, rsfilename = mkstemp()
    os.write(rsfile, py)
    os.close(rsfile)

    parse_output = StringIO()
    handler = parse_file(rsfilename, parse_output)

    os.unlink(rsfilename)

    js = finalize_source(parse_output.getvalue(), handler)
    parse_output.close()

    return js

