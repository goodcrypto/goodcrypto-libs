'''
    Convert an image file to a data uri.

    Copyright 2012 GoodCrypto            
    Last modified: 2013-11-13

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os.path

from django import template

import reinhardt.data_image

register = template.Library()
    
@register.filter
def data_img(filename, browser=None):
    ''' Encode an image file in base 64 as a data uri.
        The filename is relative to settings.STATIC_URL/settings.STATIC_ROOT.
    
        If the datauri is too large or anything goes wrong, 
        returns the url to the filename. 
        
        Example:
        
            <img alt="embedded image" src="{{ 'images/myimage.png'|data_img:browser }}">
        
    '''
    
    return reinhardt.data_image.data_image(filename, browser=browser)
