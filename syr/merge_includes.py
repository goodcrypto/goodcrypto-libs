#!/usr/bin/env python   
#
#  Copyright 2010-2012 GoodCrypto
#  Last modified: 2013-11-11
#
#  This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
#

import os.path, re, sys

from syr import text_file


def write_output(infile, outfile):
    '''Write the output file.'''
    
    ok = True
    new_lines = []
    
    try:
        add_lines(infile, new_lines)
        if len(new_lines) > 0:
            
            text_file.write(outfile, new_lines)
            
    except IOError, ioe:
        print 'Unable to convert %s to %s' % (infile, outfile)
        raise

    return ok
        

def add_lines(infile, new_lines):
    '''Add lines from infile.'''
    
    lines = text_file.read(infile)
    if lines and len(lines) > 0:
        
        dir_name = os.path.dirname(infile)
        
        for line in lines:
            m = re.match('<!--#include "(.*)"-->', line)
            if m:
                add_lines(
                  os.path.join(dir_name, m.group(1)), new_lines)
                
            else:
                new_lines.append(line)
        

def main(argv):
    """Merge include files into html."""

    if argv and \
       len(argv) == 2:

        infile = argv[0]
        outfile = argv[1]
            
        try:
            write_output(infile, outfile)

        except:
            import traceback
            traceback.print_exc()
            print 'Unexpected error while merging %s' % infile

    else:
        print 'usage: python merge-includes.py <infile> <outfile>'



if __name__ == "__main__":
    from virtualenv import venv
    with venv(django_app='goodcrypto'):
        main(sys.argv[1:])


