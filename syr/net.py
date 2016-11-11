'''
    Net utilities.

    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-08-04

    There is some inconsistency in function naming.

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    from cookielib import CookieJar
    from urllib import urlencode
    from urllib2 import build_opener, HTTPCookieProcessor, HTTPError, ProxyHandler, Request, URLError
else:
    from http.cookiejar import CookieJar
    from urllib.parse import urlencode
    from urllib.request import build_opener, HTTPCookieProcessor, ProxyHandler, Request
    from urllib.error import HTTPError, URLError

import re, sh, socket, ssl
from traceback import format_exc

from syr.log import get_log
from syr.utils import trim
from syr.user import whoami, require_user

log = get_log()

def hostname():
    ''' Convenience method to get the host name.

        >>> import sh
        >>> assert hostname() == sh.uname('--nodename').stdout.strip()
    '''

    return socket.gethostname()

def hostaddress(name=None):
    ''' Get the host ip address.

        Returns None if not found.
        Default is to return this host's ip.

        Because this function uses gethostbyname(), be sure you are not
        vulnerable to the GHOST attack.
        https://security-tracker.debian.org/tracker/CVE-2015-0235
    '''

    ip = None

    host = name or hostname()
    log.debug('host: {}'.format(host))

    try:
        host_by_name = socket.gethostbyname(host)

    except socket.gaierror:
        log.debug('no address for hostname: {}'.format(host))

    else:
        log.debug('host by name: {}'.format(host_by_name))

        if name:
            ip = host_by_name

        else:
            # socket.gethostbyname(hostname()) can be wrong depending on what is in /etc/hosts
            # but interface_from_ip() requires we are root, and we want to continue if possible
            if whoami() == 'root':
                interface = interface_from_ip(host_by_name)
                if interface and not interface == 'lo':
                    log.debug('setting ip to host by name: {}'.format(host_by_name))
                    ip = host_by_name
                else:
                    log.warning('socket.gethostbyname(hostname()) returned {}, '.format(host_by_name) +
                        'but no interface has that address. Is /etc/hosts wrong?')

            else:
                # accept socket.gethostbyname() because we can't verify it
                ip = host_by_name

    if not ip:
        # use the first net device with an ip address, excluding 'lo'
        for interface in interfaces():
            if not ip:
                if interface != 'lo':
                    ip = device_address(interface)
                    log.debug('set ip to {} from first net device {}'.format(ip, interface))

    if ip:
        log.debug('ip address: {}'.format(ip))
    else:
        msg = 'no ip address'
        log.debug(msg)
        raise Exception(msg)

    return ip

def interfaces():
    ''' Get net interfaces.

        >>> 'lo' in interfaces()
        True
    '''

    require_user('root')
    output = sh.ifconfig().stdout
    if not IS_PY2:
        output = sh.ifconfig().stdout.decode()
    return re.findall(r'^(\S+?)\s', output, flags=re.MULTILINE)

def device_address(device):
    ''' Get device ip address

        >>> device_address('lo')
        '127.0.0.1'
    '''

    require_user('root')

    ip = None
    output = sh.ifconfig(device).stdout
    if not IS_PY2:
        output = output.decode()
    for line in output.split('\n'):
        m = re.match(r'.*inet addr:(\d+\.\d+\.\d+\.\d+)', line)
        if m:
            ip = str(m.group(1))

    log.debug('{} ip: {}'.format(device, ip))

    return ip

def mac_address(device):
    ''' Get device mac address '''

    require_user('root')
    mac = None
    output = sh.ifconfig(device).stdout
    if not IS_PY2:
        output = output.decode()
    for line in output.split('\n'):
        if not mac:
            m = re.match(r'.* HWaddr +(..:..:..:..:..:..)', line)
            if m:
                mac = m.group(1)
                log.debug('mac: {}'.format(mac))

    return mac

def interface_from_ip(ip):
    ''' Find interface using ip address

        >>> interface_from_ip('127.0.0.1')
        'lo'
    '''

    interface_found = None
    for interface in interfaces():
        if not interface_found:
            if ip == device_address(interface):
                interface_found = interface

    return interface_found

def set_etc_hosts_address(hostname, ip):
    ''' Set host address in /etc/hosts from device address. '''

    def read_file(path):
        with open(path) as file:
            contents = file.read()
        return contents

    def write_etc_hosts(text):
        assert text.strip()
        with open('/etc/hosts', 'w') as hosts_file:
            hosts_file.write(text)

    def edit_text():
        # write /etc/hosts

        hostname_found = False
        newlines = []
        for line in oldlines:

            parts = line.split()

            # if hostname is already in /etc/hosts
            if hostname in parts:
                parts[0] = ip
                hostname_found = True

            line = ' '.join(parts)
            log.debug('new line: {}'.format(line))
            newlines.append(line)

        # if hostname is not in /etc/hosts
        if not hostname_found:
            # append the ip and hostname
            line = '{} {}'.format(ip, hostname)
            newlines.append(line)

        newtext = '\n'.join(newlines).strip() + '\n'
        log.debug('new text:\n{}'.format(newtext))
        return newtext

    require_user('root')

    oldlines = read_file('/etc/hosts').strip().split('\n')
    log.debug('old /etc/hosts:\n{}'.format('\n'.join(oldlines)))

    newtext = edit_text()
    assert newtext
    write_etc_hosts(newtext)

    # check /etc/hosts
    assert read_file('/etc/hosts') == newtext


def torify(host=None, port=None):
    ''' Use tor for all python sockets.

        You must call torify() very early in your app, before importing
        any modules that may do network io.

        The host and port are for your tor proxy. They default to '127.0.0.1'
        and 9050.

        Requires the socks module from SocksiPy.

        Warnings:

            If you call ssl.wrap_socket() before socket.connect(), tor may be
            disabled.

            This function only torifies python ssl calls. If you use e.g. the
            sh module to connect, this function will not make your connection
            go through tor.

        See http://stackoverflow.com/questions/5148589/python-urllib-over-tor
    '''

    import socket
    try:
        from socks import socket, socksocket, setdefaultproxy, PROXY_TYPE_SOCKS5
    except:
        msg = 'Requires the debian module from python-socksipy'
        log(msg)
        raise Exception(msg)

    def create_connection(address, timeout=None, source_address=None):
        ''' Return a socksipy socket connected through tor. '''

        assert socket == socksocket
        log('create_connection() to {} through tor'.format(address))
        sock = socksocket()
        sock.connect(address)
        return sock

    if host is None:
        host = '127.0.0.1'
    if port is None:
        port = 9050

    setdefaultproxy(PROXY_TYPE_SOCKS5, host, port)
    socket.socket = socksocket
    socket.create_connection = create_connection
    log('socket.socket and socket.create_connection now go through tor proxy at {}:{}'.format(host, port))

def send_api_request(url, params, proxy_dict=None):
    '''Send a post to a url and get the response.'''

    page = post_data(url, params, proxy_dict=proxy_dict)

    if page is None:
        body_text = ''
        log('page is empty')
    else:
        body_text = page.strip()
        body_text = body_text.lstrip()
        body_text = trim(body_text, '<HTML><BODY>')
        body_text = trim(body_text, '</BODY></HTML>')

    return body_text

def post_data(full_url, params, proxy_dict=None, use_tor=False):
    '''
        Send a post to a url and return the data.

        >>> page = post_data('https://goodcrypto.com', '')
        >>> page is not None
        True

        >>> page = post_data('https://goodcrypto.com', '', proxy_dict={'https': 'http://127.0.0.1:8398'})
        >>> page is not None
        True

        >>> page = post_data('https://goodcrypto.com', '', proxy_dict={'https': '127.0.0.1:8398'}, use_tor=True)
        >>> page is not None
        True
    '''

    def split_host_url(full_url):
        # extract the host and the remainder of the url
        m = re.match('https?://(.*/?)(.*)', full_url)
        if m:
            host = m.group(1)
            try:
                url = '/{}'.format(m.group(2))
            except:
                url = '/'
        else:
            host = full_url
            url = '/'

        if params is not None and len(params) > 0:
            url = '{}?{}'.format(url, urlencode(params))

        return host, url

    def split_host_port(proxy_dict):
        # extract the proxy's host and port
        m = re.match('(\d+.\d+.\d+.\d+):(\d+)', proxy_dict['https'])
        if m:
            proxy_host = m.group(1)
            proxy_port = int(m.group(2))

        return proxy_host, proxy_port

    try:
        from socks import socksocket, Socks5Error, PROXY_TYPE_SOCKS5
        log('imported socks in post_data')
    except:
        msg = 'Requires the debian module from python-socksipy'
        log(msg)
        raise Exception(msg)

    page = None
    try:
        if use_tor:
            CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'

            host, url = split_host_url(full_url)
            proxy_host, proxy_port = split_host_port(proxy_dict)

            s = socksocket()
            s.setproxy(PROXY_TYPE_SOCKS5, proxy_host, port=proxy_port)
            log('connecting to {}'.format(host))
            s.connect((host, 443))
            log('connected to {}'.format(host))
            ss = ssl.wrap_socket(s, cert_reqs=ssl.CERT_REQUIRED, ca_certs=CA_CERTS)
            log('wrapped socket')
            ss.write("""GET {} HTTP/1.0\r\nHost: {}\r\n\r\n""".format(url, host))
            log('requested page')

            content = []
            while True:
                data = ss.read()
                log(data) #DEBUG
                if not data: break
                content.append(data)
            ss.close()

            page = "".join(content)
        else:
            if proxy_dict is None:
                opener = build_opener(HTTPCookieProcessor(CookieJar()))
            else:
                proxy_handler = ProxyHandler(proxy_dict)
                opener = build_opener(proxy_handler, HTTPCookieProcessor(CookieJar()))

            if params is None or len(params) < 1:
                encoded_params = None
            else:
                if IS_PY2:
                    encoded_params = urlencode(params)
                else:
                    encoded_params = urlencode(params).encode()
                log('params: {}'.format(params)) #DEBUG
                log('encoded params: {}'.format(encoded_params)) #DEBUG
                log('type encoded params: {}'.format(type(encoded_params))) #DEBUG
            request = Request(full_url, encoded_params)

            handle = opener.open(request)
            page = handle.read()

    except HTTPError as http_error:
        page = None
        log('full_url: {}'.format(full_url))
        log('http error: {}'.format(str(http_error)))

    except Socks5Error as socks_error:
        page = None
        log('{} to {}'.format(socks_error, full_url))

    except URLError as url_error:
        page = None
        log('{} to {}'.format(url_error, full_url))

    except:
        page = None
        log('full_url: {}'.format(full_url))
        log(format_exc())

    return page

if __name__ == "__main__":
    import doctest
    doctest.testmod()

