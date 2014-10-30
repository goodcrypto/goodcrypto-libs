'''
    Redirect stdout and stderr to file-like streams.
    
    This does not work with all forms of output, such as the archaic "print >>".
   
    Copyright 2011 GoodCrypto
    Last modified: 2014-04-30

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

from contextlib import contextmanager
from cStringIO import StringIO
import sys

from log import get_log

log = get_log()
    
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
