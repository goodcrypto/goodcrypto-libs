'''
    Convert an image file to a data uri.

    Copyright 2012-2014 GoodCrypto           
    Last modified: 2015-02-07

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os.path
from traceback import format_exc

from django.conf import settings

from syr.log import get_log

log = get_log()
log.debugging = False

img_cache = {}

def data_image(filename, browser=None, mime_type=None):
    ''' Encode a file in base 64 as a data uri.
    
        The filename is relative to settings.STATIC_ROOT.
        'browser' is defined in syr.browser.
        
        If the data uri is too large for ie8 or anything goes wrong, 
        returns the filename. 
    '''
    
    if browser: 
        log_if_debugging('browser: {}'.format(browser))
        
    # data uris don't work well with all browsers
    if browser and (
        'unknown' in browser or 
        'ie5' in browser or 
        'ie6' in browser or 
        'ie7' in browser or 
        # opera only supports images up to 4K so we just ignore them
        'opera' in browser or 
        'java' in browser):
    
        log_if_debugging('browser "%s" does not support data uri' % browser)
        if filename.startswith('/'):
            result = filename
        else:
            result = '/static/' + filename
           
    elif filename in img_cache:
        
        result = img_cache[filename]
        
    else:
            
        log_if_debugging('filename : %s' % filename)
        
        result = filename
        try:
            if not mime_type:
                basename = filename.split('/')[-1]
                data_type = basename.split('.')[-1].lower()
                if data_type == 'jpeg':
                    data_type = 'jpg'
                # until we handle other types
                if not data_type in ['png', 'jpg', 'gif']:
                    assert ValueError, "filename does not end in '.png', '.jpg', or '.gif', and no mime_type specified"
                mime_type = 'image/%s' % data_type
                log_if_debugging('set mime_type to %s' % mime_type)
            
            # if there's no leading path, add one
            pathname = os.path.join(settings.STATIC_ROOT, filename)
            log_if_debugging('pathname = %s' % pathname)
      
            ''' 
                Only IE8 is officially to limited to 32K. 
                Earlier versions of Internet Explorer don't support data uris,
                and later ones don't have this limit. 
                See http://en.wikipedia.org/wiki/Data_URI_scheme.
                
                But other browsers (e.g. Firefox on linux) can bog down 
                badly with large data uris. 
            '''
            if browser and ('ie8' in browser):
                max_size = 32 * 1024
            else:
                # the RFC says the max size is 1024, but most browsers
                #  that support data images support up to 100K
                max_size = 100 * 1024
    
            log_if_debugging('os.path.getsize(%s)' % pathname)
            log_if_debugging('os.path.exists(%s) = %s' % (pathname, os.path.exists(pathname)))
            assert os.path.exists(pathname), pathname
            log_if_debugging('os.path.getsize(%s) = %s' % (pathname, os.path.getsize(pathname)))
            if os.path.getsize(pathname) < max_size:      
                log_if_debugging('file_to_data_uri(%s, %s)' % (pathname, mime_type))
                result = file_to_data_uri(pathname, mime_type)
                log_if_debugging('done file_to_data_uri(%s, %s)' % (pathname, mime_type))
                    
            else:
                #log_if_debugging('IE8 does not allow data uris larger than 32K: %s' % 
                #    pathname)
                log_if_debugging('No data uris larger than 32K: %s' % pathname)
                    
        except Exception, e:
            log.error(format_exc())
            # like django template processing, fail quietly
            result = ''
                             
        log_if_debugging('result: %s' % result)
        img_cache[filename] = result
        
    return result
        
def data_uri(data, mime_type, charset=None):
    ''' Convert binary data to a data uri '''
    
    base64_data = data.encode('base64').replace('\n', '')
    if charset:
        uri = 'data:%s;%s;base64,%s' % (charset, mime_type, base64_data)
    else:
        uri = 'data:%s;base64,%s' % (mime_type, base64_data)
    log_if_debugging('uri: %s' % uri)
    return uri

def file_to_data_uri(filename, mime_type):
    ''' Convert file to a data uri '''
    
    f = open(filename, 'rb')
    datauri = data_uri(f.read(), mime_type)
    f.close()
    return datauri

def log_if_debugging(message):
    ''' Log if debugging. '''
    
    if log.debugging:
        log.debug(message)
