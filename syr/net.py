'''
    Net utilities.

    Copyright 2014-2015 GoodCrypto
    Last modified: 2015-11-15

    There is some inconsistency in function naming.

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from cookielib import CookieJar
import re, sh, socket, socks, ssl, urllib2
from traceback import format_exc
from urllib import urlencode

from syr.log import get_log
from syr.utils import trim

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
            interface = interface_from_ip(host_by_name)

            if interface and not interface == 'lo':
                log.debug('setting ip to host by name: {}'.format(host_by_name))
                ip = host_by_name
            else:
                log.warning('socket.gethostbyname(hostname()) returned {}, '.format(host_by_name) +
                    'but no interface has that address. Is /etc/hosts wrong?')

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
    ''' Get net interfaces. '''

    output = sh.ifconfig().stdout
    return re.findall(r'^(\w+)', output, flags=re.MULTILINE)

def device_address(device):
    ''' Get device ip address '''

    ip = None
    output = sh.ifconfig(device).stdout
    for line in output.split('\n'):
        m = re.match(r'.*inet addr:(\d+\.\d+\.\d+\.\d+)', line)
        if m:
            ip = m.group(1)

    log.debug('{} ip: {}'.format(device, ip))

    return ip

def mac_address(device):
    ''' Get device mac address '''

    mac = None
    output = sh.ifconfig(device).stdout
    for line in output.split('\n'):
        if not mac:
            m = re.match(r'.* HWaddr +(..:..:..:..:..:..)', line)
            if m:
                mac = m.group(1)
                log.debug('mac: {}'.format(mac))

    return mac

def interface_from_ip(ip):
    ''' Find interface using ip address '''

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
        import socks
    except:
        msg = 'Requires the socks module from SocksiPy'
        log.debug(msg)
        raise Exception(msg)

    def create_connection(address, timeout=None, source_address=None):
        ''' Return a socksipy socket connected through tor. '''
        
        assert socket.socket == socks.socksocket
        log('create_connection() to {} through tor'.format(address))
        sock = socks.socksocket()
        sock.connect(address)
        return sock

    if host is None:
        host = '127.0.0.1'
    if port is None:
        port = 9050

    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, host, port)
    socket.socket = socks.socksocket
    socket.create_connection = create_connection
    log('socket.socket and socket.create_connection now go through tor')

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
        
    page = None

    try:
        if use_tor:
            CA_CERTS = '/etc/ssl/certs/ca-certificates.crt'
            

            host, url = split_host_url(full_url)
            proxy_host, proxy_port = split_host_port(proxy_dict)
            
            s = socks.socksocket()
            s.setproxy(socks.PROXY_TYPE_SOCKS5, proxy_host, port=proxy_port)
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
                opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))
            else:
                proxy_handler = urllib2.ProxyHandler(proxy_dict)
                opener = urllib2.build_opener(proxy_handler, urllib2.HTTPCookieProcessor(CookieJar()))
    
            request = urllib2.Request(full_url, urlencode(params))
            handle = opener.open(request)
            page = handle.read()

    except urllib2.HTTPError as http_error:
        page = None
        log('full_url: {}'.format(full_url))
        log('http error: {}'.format(str(http_error)))
        log(format_exc())

    except socks.Socks5Error:
        page = None
        log('socks error while connecting to full_url: {}'.format(full_url))
        
    except:
        page = None
        log('full_url: {}'.format(full_url))
        log(format_exc())

    return page

if __name__ == "__main__":
    import doctest
    doctest.testmod()

