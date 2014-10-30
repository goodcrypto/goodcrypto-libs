'''
    Net utilities.

    Copyright 2014 GoodCrypto
    Last modified: 2014-10-02

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from cookielib import CookieJar
import re, sh, socket, urllib2
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
    
def hostaddress():
    ''' Convenience method to get the host ip address. 
    
        If the primary network interface isn't eth0 or wan0, use
        syr.net.device_address().
    '''
    
    by_name = socket.gethostbyname(hostname())
    
    # socket.gethostbyname(hostname()) can be wrong depending on what is in /etc/hosts
    in_use = False
    for interface in interfaces():
        if by_name == device_address(interface):
            in_use = True
    if not in_use:
        raise Exception(
            'socket.gethostbyname(hostname()) returned {}, but no interface has that address. Is /etc/hosts wrong?'
            .format(by_name))
        
    return by_name
    
def interfaces():
    ''' Get net interfaces. '''
    
    output = sh.ifconfig().stdout
    return re.findall(r'^(\w+)', output, flags=re.MULTILINE)
    
def device_address(device):
    ''' Get device ip address '''
    
    ip = None
    output = sh.ifconfig(device).stdout
    for line in output.split('\n'):
        m = re.match(r'.*inet addr:(\d+.\d+.\d+.\d+)', line)
        if m:
            ip = m.group(1)
            log.debug('ip: {}'.format(ip))
            
    return ip
            
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
        
    # check # /etc/hosts
    assert read_file('/etc/hosts') == newtext


def torify(host=None, port=None):
    ''' Use tor. 
    
        You must call torify() very early in your app, before importing 
        any modules that may do network io.
        
        The host and port are for your tor proxy. They default to '127.0.0.1' 
        and 9050. 
    
        Requires the socks module from SocksiPy.
        
        Warning: If you call ssl.wrap_socket() before socket.connect(), tor 
        may be disabled.
    
        See http://stackoverflow.com/questions/5148589/python-urllib-over-tor    
    '''
    
    import socket
    try:
        import socks
    except:
        raise Exception('Requires the socks module from SocksiPy')
        
    def create_connection(address, timeout=None, source_address=None):
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
    
def send_api_request(url, params):
    '''Send a post to a url and get the response.'''
    
    page = post_data(url, params)
    
    if page is None:
        body_text = ''
        log('page is empty')
    else:
        body_text = page.strip()
        body_text = body_text.lstrip()
        body_text = trim(body_text, '<HTML><BODY>')
        body_text = trim(body_text, '</BODY></HTML>')
        
    return body_text

def post_data(full_url, params):
    '''Send a post to a url and return the data.'''
    
    page = None

    try:
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(CookieJar()))
        request = urllib2.Request(full_url, urlencode(params))
        handle = opener.open(request)
        page = handle.read()
            
    except:
        log(format_exc())
        log('full_url: {}'.format(full_url))

    return page

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
