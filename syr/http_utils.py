'''
    HTTP utilities

    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-08-16

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    from httplib import HTTPConnection, HTTPSConnection
    from httplib import responses as http_responses
    from urlparse import urlsplit, urlunsplit
else:
    from http.client import HTTPConnection, HTTPSConnection
    from http.client import responses as http_responses
    from urllib.parse import urlsplit, urlunsplit
import http_status

import ssl
import traceback

from syr.dict import CaseInsensitiveDict
from syr.log import get_log
from syr.utils import gunzip

log = get_log()

HTTP_EOL = '\r\n'
HTTP_SEPARATOR = HTTP_EOL + HTTP_EOL

# dict to look up HTTP status code by name
# name is a string as specified by http_status
# use http_status directly to look up name or description by code
code = {}
for number, name in http_status.name.items():
    code[name] = number

ports = dict(
    http = 80,
    https = 443)

def TEST_get_response(url, proxy=None, cert_file=None):
    ''' Get an HttpResponse for the url '''

    if proxy:
        log.debug('get response from "{}" using proxy "{}"'.format(url, proxy))
        # see python - Using SocksiPy with SSL - Stack Overflow
        #     http://stackoverflow.com/questions/16136916/using-socksipy-with-ssl

        if not cert_file:
            cert_file = '/etc/ssl/certs/ca-certificates.crt'

        proxy_parts = urlsplit(proxy)

        try:
            from socks import socksocket, PROXY_TYPE_SOCKS5
        except:
            msg = 'Requires the debian module from python-socksipy'
            log.debug(msg)
            raise Exception(msg)

        s = socksocket()
        s.setproxy(PROXY_TYPE_SOCKS5, proxy_parts.hostname, port=proxy_parts.port)
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

        url_parts = urlsplit(url)
        if url_parts.scheme == 'https':
            HTTPxConnection = HTTPSConnection
        elif url_parts.scheme == 'http':
            HTTPxConnection = HTTPConnection
            kwargs = {}
        else:
            raise ValueError('{} not supported'.format(url_parts.scheme))

        conn = HTTPxConnection(url_parts.hostname,
            url_parts.port or ports[url_parts.scheme],
            **kwargs)

        relative_url = urlunsplit(('', '',
                url_parts.path, url_parts.query, url_parts.fragment))
        conn.request('GET', relative_url)

        result = conn.getresponse()

    return result

def get_response(url, proxy=None, cert_file=None):
    ''' Get an HttpResponse for the url '''

    url_parts = urlsplit(url)
    if url_parts.scheme == 'https':
        HTTPxConnection = HTTPSConnection
        if cert_file is not None:
            kwargs = dict(cert_file=cert_file)
    elif url_parts.scheme == 'http':
        HTTPxConnection = HTTPConnection
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
        proxy_parts = urlsplit(proxy)
        conn = HTTPxConnection(
            proxy_parts.hostname,
            proxy_parts.port,
            **kwargs)

        conn.set_tunnel(
            url_parts.hostname,
            url_parts.port or ports[url_parts.scheme])

    relative_url = urlunsplit(('', '',
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
    ''' Parse raw http request data into prefix, params, and data.
        'prefix' is a string. 'params' is a dict. 'data' is a string or None. '''

    prefix, _, remainder = request.partition(HTTP_EOL)
    if HTTP_SEPARATOR in remainder:
        raw_params, _, content = remainder.partition(HTTP_SEPARATOR)
    else:
        raw_params = remainder
        content = None
    params = parse_params(raw_params.split(HTTP_EOL))

    return prefix, params, content

def parse_response(response):
    ''' Parse raw http response data into (prefix, params, html) where params is a dict. '''

    header, _, data = response.partition(HTTP_SEPARATOR)
    prefix, params = parse_header(header)
    params, data = uncompress_content(params, data)
    data = unicode_content(params, data)

    return prefix, params, data

def unparse_response(prefix, params, data):
    ''' Constructs a string with an http response.

        This is essentially the reverse of parse_response().
    '''

    try:
        data = data.decode('utf-8', 'replace')
    except AttributeError:
        # AttributeError: 'str' object has no attribute 'decode'
        # already unicode
        pass

    return (prefix + HTTP_EOL +
            params_to_str(params) + HTTP_SEPARATOR +
            data)

def parse_prefix(prefix):
    ''' Parse raw http prefix into command, url, and http version. '''

    command, _, remainder = prefix.partition(' ')
    url, _, version = remainder.partition(' ')

    return command, url, version

def parse_header(header):
    ''' Parse raw http header into prefix line and a CaseInsensitiveDict. '''

    lines = header.split(HTTP_EOL)
    prefix = lines[0]
    params  = parse_params(lines[1:])

    return prefix, params

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

def uncompress_content(params, data):
    ''' If content is gzipped, unzip it and set new Content-Length. '''

    if is_text(params) and is_gzipped(params):

        data = gunzip(data)
        del params['Content-Encoding']
        params['Content-Length'] = str(len(data))

    return params, data

def unicode_content(params, data):
    ''' Return content as unicode. If params specify a charset, decode data from that charset. '''

    # see Python Unicode HowTo
    #     http://docs.python.org/2/howto/unicode.html
    #         "Software should only work with Unicode strings internally,
    #         converting to a particular encoding on output."
    if type(data) in [bytes, bytearray]:
        charset = content_encoding_charset(params)
        if charset is not None:
            try:
                data = data.decode(charset, 'replace')
            except AttributeError:
                # AttributeError: 'str' object has no attribute 'decode'
                # already unicode
                pass
            except:
                msg = 'Charset {} not supported'.format(charset)
                log.debug(msg)
                log.debug(traceback.format_exc())
                raise ValueError(msg)

    return data

def create_response(status, params=None, data=None):
    ''' Return raw http response.

        'status' is an integer. http lib defines status constants and .

        'params' is an optional dict. 'data' is an optional string. '''

    if params is None:
        params = {}
    if data is None:
        data = ''

    prefix = 'HTTP/1.1 {} {}'.format(status, http_responses[status])
    params['Content-Length'] = len(data)
    response = prefix + HTTP_EOL + params_to_str(params) + HTTP_SEPARATOR + data
    return response

def params_to_str(params):
    def camelCase(name):
        ''' Upper case the first letter of each word in the name. '''

        return name.replace('-', ' ').title().replace(' ', '-')

    return HTTP_EOL.join(
        '{}: {}'.format(camelCase(name), params[name])
        for name in params)

def header(data):
    ''' Parse header from raw http data '''

    header_data, _, _ = data.partition(HTTP_SEPARATOR)
    return header_data

def is_content_type(params, prefix):
    ''' Return True if Content-Type sarts with prefix, else False. '''

    result = (
        'Content-Type' in params and
        params['Content-Type'].startswith(prefix))
    return result

def is_html(params):
    return is_content_type(params, 'text/html')

def is_text(params):
    ''' Return True if params indicate content is text, else False. '''

    return is_content_type(params, 'text/')

def is_app_data(params):
    ''' Return True if params indicate content is application data, else False. '''

    return is_content_type(params, 'application/')

def is_image(params):
    ''' Return True if params indicate content is image data, else False. '''

    return is_content_type(params, 'image/')

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

def is_gzipped(params):
    ''' Return True if params indicate content is gzipped, else False. '''

    return (
        'Content-Encoding' in params and
        'gzip' in params['Content-Encoding'])

def verify_cert_locally(host, port):
    ''' Verify the site's certificate using openssl locally. '''

    log.warning('verify_cert_locally() bypasses any proxy such as Tor, so it may leak DNS info')

    # Verify the cert is ok before proceeding
    log.debug('verifying cert for: {}:{}'.format(host, port))
    ok, original_cert, cert_error_details = syr.openssl.verify_certificate(host, port)
    log.debug('{}:{} cert ok: {}'.format(host, port, ok))

    if not ok:
        log.debug(cert_error_details)

        # if the cert is self signed or expired, let the user decide what to do
        if syr.openssl.SELF_SIGNED_CERT_ERR_MSG in cert_error_details:
            log.debug('cert is self.signed')
            ok = True
        elif syr.openssl.EXPIRED_CERT_ERR_MSG in cert_error_details:
            log.debug('cert is expired')
            ok = True

    return ok, original_cert, cert_error_details

if __name__ == "__main__":
    import doctest
    doctest.testmod()

