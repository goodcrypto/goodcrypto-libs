'''
    Redirect stdout and stderr to file-like streams.

    This does not work with all forms of output, such as the archaic "print >>".

    Copyright 2011-2016 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import print_function
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

from contextlib import contextmanager
if IS_PY2:
    from cStringIO import StringIO
else:
    from io import StringIO

from syr.log import get_log

log = get_log()

@contextmanager
def redir_stdin(stream):
    ''' Context manager for print that redirects sys.stdin, and hence
        standard raw_input(), to another file-like stream.

        >>> import cStringIO
        >>> input = cStringIO.StringIO('test stdin data')
        >>> with redir_stdin(input):
        ...     print(raw_input())
        test stdin data
    '''

    saved_stdin = sys.stdin
    sys.stdin = stream
    try:
        yield
    finally:
        sys.stdin = saved_stdin

@contextmanager
def redir_stdout(stream):
    ''' Context manager for print that redirects sys.stdout, and hence
        standard print(), to another file-like stream.

        >>> import cStringIO
        >>> output = cStringIO.StringIO()
        >>> with redir_stdout(output):
        ...     output.write('test')
        >>> value = output.getvalue()
        >>> output.close()
        >>> print(value)
        test
    '''

    assert hasattr(stream, 'write')
    saved_stdout = sys.stdout
    sys.stdout = stream
    try:
        yield
    finally:
        sys.stdout = saved_stdout

@contextmanager
def redir_stderr(stream):
    ''' Context manager for print that redirects sys.stderr to another
        file-like stream. '''

    assert hasattr(stream, 'write')
    saved_stderr = sys.stderr
    sys.stderr = stream
    try:
        yield
    finally:
        sys.stderr = saved_stderr

@contextmanager
def redir_stdout_and_stderr(stream):
    ''' Context manager for print() that redirects both sys.stdout and
        sys.stderr to the same file-like stream. '''

    assert hasattr(stream, 'write')
    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    sys.stdout = stream
    sys.stderr = stream
    try:
        yield
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr

"""
@contextmanager
def redir_raw_input(stream):
    ''' Context manager for print that redirects raw_input to another file-like stream.

        >>> import cStringIO
        >>> input = cStringIO.StringIO('test raw data')
        >>> with redir_raw_input(input):
        ...     print(raw_input())
        test raw data
    '''

    saved_raw_input = __builtins__.raw_input
    __builtins__.raw_input = stream
    try:
        yield
    finally:
        __builtins__.raw_input = saved_raw_input
"""

class stdout_str_value(object):
    ''' Context manager to redirect stdout as a value for str().

        Returns a value which can be converted into a string, either
        automatically or using str().

        >>> TEST = 'test'
        >>> with stdout_str_value() as output:
        ...     print(TEST)
        >>> print(output)
        test
        <BLANKLINE>

    '''

    def __enter__(self):
        self.stream = StringIO()

        self.saved_stdout = sys.stdout
        sys.stdout = self.stream

        return self

    def __exit__(self, *exc_info):
        sys.stdout = self.saved_stdout

        self.value = self.stream.getvalue()
        self.stream.close()

    def __str__(self):
        return self.value

class stderr_str_value(object):
    ''' Context manager to redirect stderr as a value for str().

        Returns a value which can be converted into a string, either
        automatically or using str().

        >>> import sys
        >>> TEST = 'test'
        >>> with stderr_str_value() as output:
        ...     print(TEST, file=sys.stderr)
        >>> print(output)
        test
        <BLANKLINE>

    '''

    def __enter__(self):
        self.stream = StringIO()

        self.saved_stderr = sys.stderr
        sys.stderr = self.stream

        return self

    def __exit__(self, *exc_info):
        sys.stderr = self.saved_stderr

        self.value = self.stream.getvalue()
        self.stream.close()

    def __str__(self):
        return self.value

class stdout_and_stderr_str_value(object):
    ''' Context manager to redirect stdout and stderr as a value for str().

        Returns a value which can be converted into a string, either
        automatically or using str().

        >>> import sys
        >>> TEST = 'test'
        >>> with stdout_and_stderr_str_value() as output:
        ...     print(TEST)
        ...     print(TEST, file=sys.stderr)
        >>> print(output)
        test
        test
        <BLANKLINE>

    '''

    def __enter__(self):
        self.stream = StringIO()

        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr

        sys.stdout = self.stream
        sys.stderr = self.stream

        return self

    def __exit__(self, *exc_info):
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr

        self.value = self.stream.getvalue()
        self.stream.close()

    def __str__(self):
        return self.value

if __name__ == "__main__":
    import doctest
    doctest.testmod()
