'''
    HTTP utilities

    Copyright 2013 GoodCrypto
    Last modified: 2015-11-17

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import httplib
import socks
import ssl
import traceback
import urlparse

from syr.dict import CaseInsensitiveDict
from syr.log import get_log
from syr.utils import gunzip

log = get_log()

http_eol = '\r\n'
http_separator = http_eol + http_eol

ports = dict(
    http = 80,
    https = 443)

def TEST_get_response(url, proxy=None, cert_file=None):
    ''' Get an httplib.HttpResponse for the url '''
    
    if proxy:
        log.debug('get response from "{}" using proxy "{}"'.format(url, proxy))
        # see python - Using SocksiPy with SSL - Stack Overflow
        #     http://stackoverflow.com/questions/16136916/using-socksipy-with-ssl
        
        if not cert_file:
            cert_file = '/etc/ssl/certs/ca-certificates.crt'
                
        proxy_parts = urlparse.urlsplit(proxy)
        
        s = socks.socksocket()
        s.setproxy(socks.PROXY_TYPE_SOCKS5, proxy_parts.hostname, port=proxy_parts.port)
        s.connect(('check.torproject.org', 443))
        ss = ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ca_certs=cert_file)
        
        # print "Peer cert: ", ss.getpeercert()
        
        ss.write("""GET / HTTP/1.0\r\nHost: {}\r\n\r\n""".format(proxy_parts.hostname))
        
        content = []
        while True:
            data = ss.read()
            if not data: break
            content.append(data)
        
        ss.close()
        result = "".join(content)
        
    else:
        log.debug('get response from {}'.format(url))
        
        url_parts = urlparse.urlsplit(url)

        if url_parts.scheme == 'https':
            HTTPxConnection = httplib.HTTPSConnection
        elif url_parts.scheme == 'http':
            HTTPxConnection = httplib.HTTPConnection
            kwargs = {}
        else:
            raise ValueError('{} not supported'.format(url_parts.scheme))

        conn = HTTPxConnection(url_parts.hostname,
            url_parts.port or ports[url_parts.scheme],
            **kwargs)

        relative_url = urlparse.urlunsplit(('', '',
            url_parts.path, url_parts.query, url_parts.fragment))
        conn.request('GET', relative_url)
    
        result = conn.getresponse()
        
    return result
    
def get_response(url, proxy=None, cert_file=None):
    ''' Get an httplib.HttpResponse for the url '''

    url_parts = urlparse.urlsplit(url)

    if url_parts.scheme == 'https':
        HTTPxConnection = httplib.HTTPSConnection
        if cert_file is not None:
            kwargs = dict(cert_file=cert_file)
    elif url_parts.scheme == 'http':
        HTTPxConnection = httplib.HTTPConnection
        kwargs = {}
    else:
        raise ValueError('{} not supported'.format(url_parts.scheme))

    if proxy is None:
        log.debug('get response from {}'.format(url))
        conn = HTTPxConnection(url_parts.hostname,
            url_parts.port or ports[url_parts.scheme],
            **kwargs)

    else:
        log.debug('get response from "{}" using proxy "{}"'.format(url, proxy))
        # weirdly, HTTPConnection() gets the proxy, and set_tunnel() gets the destination domain
        proxy_parts = urlparse.urlsplit(proxy)
        conn = HTTPxConnection(
            proxy_parts.hostname,
            proxy_parts.port,
            **kwargs)

        conn.set_tunnel(
            url_parts.hostname,
            url_parts.port or ports[url_parts.scheme])

    relative_url = urlparse.urlunsplit(('', '',
        url_parts.path, url_parts.query, url_parts.fragment))
    conn.request('GET', relative_url)

    return conn.getresponse()

def check_response(url, why=None, proxy=None):
    ''' Check that we got a good response from the url.

        'why' is why we're checking. 'proxy' is http proxy.

        Returns response.

        response.data is set to http data.
    '''

    def err_msg(err):
        msg = ('''{}
        why: {}
        testing url: {}'''.
        format(err, why, url))

        if proxy:
            msg = msg + ('''
        proxy url: {}
        '''.format(proxy))

        return msg

    if not why:
        why = 'check http response'

    log.debug('url: {}'.format(url))
    try:
        response = get_response(url, proxy=proxy)
    except:
        print(err_msg('error in get_response()'))
        raise

    # check for OK response
    assert response.status == 200, err_msg('bad status: {}'.format(response.status))

    # check data exists
    response.data = response.read()
    assert len(response.data) > 0, err_msg('no data')

    return response

def parse_request(request):
    ''' Parse raw http request data into prefix and params where params is a dict. '''

    request = request.strip(http_eol)
    lines = request.split(http_eol)
    prefix = lines[0]
    params = parse_params(lines[1:])
    return prefix, params

def parse_response(response):
    ''' Parse raw http response data into (prefix, params, html) where params is a dict. '''

    header, _, data = response.partition(http_separator)

    lines = header.split(http_eol)
    prefix = lines[0]
    params  = parse_params(lines[1:])

    # unzip text
    if is_text(params) and is_gzipped(params):

        data = gunzip(data)
        del params['Content-Encoding']
        params['Content-Length'] = len(data)

    # see Python Unicode HowTo
    #     http://docs.python.org/2/howto/unicode.html
    #         "Software should only work with Unicode strings internally,
    #         converting to a particular encoding on output."
    charset = content_encoding_charset(params)
    if charset is not None:
        try:
            data = data.decode(charset, 'ignore')
        except:
            msg = 'Charset {} not supported'.format(charset)
            log.debug(msg)
            log.debug(traceback.format_exc())
            raise ValueError(msg)

    return prefix, params, data

def parse_params(lines):
    ''' Parse raw http params '''

    params  = CaseInsensitiveDict()
    for line in lines:
        if len(line.strip()):
            name, _, value = line.partition(':')
            name = name.strip()
            if len(name):
                value = value.strip()
                params[name] = value

    return params

def create_response(status, params=None, data=None):
    ''' Return raw http response.

        'status' is an integer. httplib defines status constants and .

        'params' is an optional dict. 'data' is an optional string. '''

    if params is None:
        params = {}
    if data is None:
        data = ''

    prefix = 'HTTP/1.1 {} {}'.format(status, httplib.responses[status])
    params['Content-Length'] = len(data)
    response = prefix + http_eol + params_to_str(params) + http_separator + data
    return response

def params_to_str(params):
    return http_eol.join(
        '{}: {}'.format(name, params[name])
        for name in params)

def header(data):
    ''' Parse header from raw http data '''

    header_data, _, _ = data.partition(http_separator)
    return header_data

def is_html(params):
    result = (
        'Content-Type' in params and
        params['Content-Type'].startswith('text/html'))
    return result

def is_gzipped(params):
    ''' Return True if params indicate content is gzipped, else False. '''

    return (
        'Content-Encoding' in params and
        'gzip' in params['Content-Encoding'])

def is_text(params):
    ''' Return True if params indicate content is text, else False. '''

    return (
        'Content-Type' in params and
        params['Content-Type'].startswith('text/'))

def is_app_data(params):
    ''' Return True if params indicate content is application data, else False. '''

    return (
        'Content-Type' in params and
        params['Content-Type'].startswith('application/'))

def content_encoding_charset(params):
    ''' Parse content-encoding charset from http response. '''

    charset = None
    if 'Content-Type' in params:
        content_type =  params['Content-Type']
        # content-type = text/html; charset=UTF-8
        for ct_param in content_type.split(';'):
            if charset is None:
                if '=' in ct_param:
                    name, value = ct_param.split('=')
                    name = name.strip()
                    if name == 'charset':
                        charset = value.strip()

    return charset

if __name__ == "__main__":
    import doctest
    doctest.testmod()

