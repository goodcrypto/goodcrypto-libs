'''
    Retry 404 response on another backend http server.
    
    If static resources such as css and js are served by a front end server, 
    that static server must also serve the static resources of the other 
    backend http server. See redirect404.py for an alternative. Or you may
    choose to bypass the front end server, at a cost in performance. 
    
    The server is specified by settings.PROXY_404_SERVER.
    PROXY_404_SERVER is in the form:
    
        [USERNAME[:PASSWORD]@]HOST[:PORT]
        
    HOST can be a DNS name or IP address.
    PROXY_404_SERVER Examples::
    
        example.com
        example.com:8080
        username@example.com:8080
        username:password@example.com:8080
        127.0.0.1
        127.0.0.1:8080
            
    Copyright 2014 GoodCrypto
    Last modified: 2014-03-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import traceback, urllib
from urlparse import urlsplit, urlunsplit

from django.contrib.redirects.models import Redirect
from django import http
from django.conf import settings

from syr.log import get_log

log = get_log()


class Proxy404Middleware(object):
    
    def process_response(self, request, response):
        
        try:
            if response.status_code == 404:
                
                log('got 404')
                url = request.get_full_path()
                parts = urlsplit(url)
                
                if parts.scheme == '':
                    if request.is_secure():
                        scheme = 'https'
                    else:
                        scheme = 'http'
                else:
                    scheme = parts.scheme
                    
                old_host = request.get_host()
                new_host = settings.PROXY_404_SERVER
                if new_host != old_host:
                    
                    log('old host: %s, new host: %s' % (old_host, new_host)) #DEBUG
                    new_url = urlunsplit([scheme, new_host, 
                        parts.path, parts.query, parts.fragment])
                    log('url: %s' % url) #DEBUG
                    log('parts: %s' % repr(parts)) #DEBUG
                    log('new url: %s' % new_url) #DEBUG

                    try:
                        log('opening %s' % new_url) #DEBUG
                        stream = urllib.urlopen(new_url)
                        log('reading %s' % new_url) #DEBUG
                        try:
                            new_response = http.HttpResponse(stream.read())
                        finally:
                            stream.close()
                        if new_response.status_code == 404:
                            log('404 ' % new_url) #DEBUG
                        else:
                            log('got %s' % new_url) #DEBUG
                            response = new_response
    
                    except:
                        # just log it and return the exsting 404
                        log('url: %s' % url)
                        log('parts: %s' % repr(parts))
                        log('new url: %s' % new_url)
                        log(traceback.format_exc()) 
                        pass
                
        except:
            log(traceback.format_exc())
            raise

        return response
