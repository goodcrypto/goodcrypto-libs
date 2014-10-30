'''
  Read/write small text files.
  
  This module can be replaced using python directly,
  but there are many times when I want to read and write
  simple text files, but if something doesn't work, I want
  the error logged and the higher level to continue. In
  other words, if you try to read a file and it doesn't exist,
  then you just get an empty list instead of an exception.

  Copyright 2008-2012 GoodCrypto
  Last modified: 2014-01-08

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import shutil
from traceback import format_exc
from syr.log import get_log
    

log = get_log()


def read(filename):
    '''Read the contents of a text file. Return the lines as a list.
    
       If the file doesn't exist, return empty list.
    '''
    
    try:
        inputFile = open(filename, 'rt')
        lines = inputFile.readlines()
        inputFile.close()
    except:
        log('Unable to read %s' % filename)
        log(format_exc())
        lines = []

    return lines
    
        
def write_line(filename, line, append=False):
    '''Write a line to a text file.
    
      Log any io errors and then raise another ioerrr.
    '''
    
    lines = [line]
    return write(filename, lines, append)
    
        
def write(filename, lines, append=False):
    '''Write the lines to a text file.
    
      Log any io errors and then raise another ioerrr.
    '''
    
    try:
        if append:
            method = 'at'
        else:
            method = 'wt'
                
        outputFile = open(filename, method)
        for line in lines:
            if isinstance(line, basestring):
                if not line.endswith('\n'):
                    line += '\n'
                outputFile.write(line)
            else:
                # line must be another list
                # let's assume there aren't any more nested lists
                for l in line:
                    if not l.endswith('\n'):
                        l += '\n'
                    outputFile.write(l)
        outputFile.close()
        
    except IOError:
        log('Unable to write %s' % filename)
        log(format_exc())
        raise IOError

    return lines
    
        
def backup_and_write(filename, lines, append=False):
    '''Backup the text file and then write the new content.
    
      Log any io errors and then raise another ioerrr.
    '''
    
    backup(filename)

    return write(filename, lines, append)
    

def backup(filename):
    '''Backup the text file.
    
      Log any io errors and then raise another ioerrr.
    '''
    
    try:
        shutil.copy2(filename, filename + '.bak')
        
    except IOError, (errno, strerror):
        log('Unable to backup %s' % filename)
        log("   (%d) %s" % (errno, strerror))
        raise IOError
    

