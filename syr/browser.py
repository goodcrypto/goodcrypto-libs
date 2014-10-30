#!/usr/bin/env python
'''
    Browser utilities.
    
    Copyright 2012-2013 GoodCrypto
    Last modified: 2014-01-08

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import re
from syr.log import get_log

log = get_log()

def user_agent_tags(ua):
    ''' Returns list of browser types indicated by the user agent. 

        License: http://creativecommons.org/licenses/by/2.5/
        Credits:
            GoodCrypto: http://goodcrypto.com
            This is a port from Koes Bong: http://web.koesbong.com/2011/01/28/python-css-browser-selector/,
            which is a port from Bastian Allgeier's PHP CSS Browser Selector: http://www.bastian-allgeier.de/css_browser_selector/, 
            which is a port from Rafael Lima's original Javascript CSS Browser Selector: http://rafael.adm.br/css_browser_selector
            
    >>> user_agent_tags('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.56 Safari/536.5')
    ['webkit safari chrome', 'linux']
    >>> user_agent_tags('Safari/7534.57.2 CFNetwork/520.4.3 Darwin/11.4.0 (x86_64) (MacBookPro8%2C2)')
    ['unknown', 'mac']
    >>> user_agent_tags('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)')
    ['ie ie7', 'win']
    >>> user_agent_tags('Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.19) Gecko/2012020109 Iceweasel/3.0.6 (Debian-3.0.6-3)')
    ['gecko', 'linux']
    >>> user_agent_tags('curl/7.21.0 (i486-pc-linux-gnu) libcurl/7.21.0 OpenSSL/0.9.8o zlib/1.2.3.4 libidn/1.15 libssh2/1.2.6')
    ['curl', 'linux']
    >>> user_agent_tags('Lynx/2.8.8dev.5 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.8.6')
    ['lynx']
    >>> user_agent_tags('Wget/1.12 (linux-gnu)')
    ['wget', 'linux']
    
    '''
    
    ua = ua.lower()
    g = 'gecko'
    w = 'webkit'
    s = 'safari'
    browser = []
    
    opera_webtv_matches = re.search(r'opera|webtv', ua)
    opera_matches = re.search(r'opera(\s|\/)(\d+)', ua)
    msie_matches = re.search(r'msie\s(\d)', ua)
    
    if opera_webtv_matches is None and msie_matches is not None:
        browser.append('ie ie' + msie_matches.group(1))
    elif ua.find(r'firefox/2') != -1:
        browser.append(g + ' ff2')
    elif ua.find(r'firefox/4') != -1:
        browser.append(g + ' ff4')
    elif ua.find(r'firefox/3.6') != -1:
        browser.append(g + ' ff36')
    elif ua.find(r'firefox/3.5') != -1:
        browser.append(g + ' ff35')
    elif ua.find(r'firefox/3') != -1:
        browser.append(g + ' ff3')
    elif ua.find(r'firefox/5') != -1:
        browser.append(g + ' ff5')
    elif ua.find(r'gecko/') != -1:
        browser.append(g)
    elif opera_matches is not None:
        browser.append('opera opera' + opera_matches.group(2))
    elif ua.find(r'konquerer') != -1:
        browser.append('konquerer')
    elif ua.find(r'chrome') != -1:
        browser.append(w + ' ' + s + ' chrome')
    elif ua.find(r'iron') != -1:
        browser.append(w + ' ' + s + ' iron')
    elif ua.find(r'applewebkit/') != -1:
        applewebkit_ver_matches = re.search(r'version\/(\d+)', ua)
        if applewebkit_ver_matches is not None:
            browser.append(w + ' ' + s + ' ' + s + applewebkit_ver_matches.group(1))
        else:
            browser.append(w + ' ' + s)
    elif ua.find(r'mozilla/') != -1:
        browser.append(g)
    elif ua.find(r'chrome/') != -1:
        browser.append('chrome')
    elif ua.find(r'wget/') != -1:
        browser.append('wget')
    elif ua.find(r'lynx/') != -1:
        browser.append('lynx')
    elif ua.find(r'curl/') != -1:
        browser.append('curl')
    elif ua.find(r'unknown'):
        browser.append('unknown')
    
    #platform
    if ua.find('j2me') != -1:
        browser.append('j2me')
    elif ua.find('java') != -1:
        browser.append('java')
    elif ua.find('python') != -1:
        browser.append('python')
    elif ua.find('iphone') != -1:
        browser.append('iphone')
    elif ua.find('ipod') != -1:
        browser.append('ipod')
    elif ua.find('ipad') != -1:
        browser.append('ipad')
    elif ua.find('android') != -1:
        browser.append('android')
    elif ua.find('blackberry') != -1:
        browser.append('blackberry')
    elif ua.find('mobile') != -1:
        browser.append('mobile')
    elif ua.find('mac') != -1 or ua.find('darwin') != -1:
        browser.append('mac')
    elif ua.find('webtv') != -1:
        browser.append('webtv')
    elif ua.find('win') != -1:
        browser.append('win')
    elif ua.find('freebsd') != -1:
        browser.append('freebsd')
    elif ua.find('x11') != -1 or ua.find('linux') != -1:
        browser.append('linux')
        
    return browser

def browser_types(request):
    ''' Returns list of compatible browser types from Django request. '''
    
    ua = request.META.get('HTTP_USER_AGENT', 'unknown')
    return user_agent_tags(ua)    
    
def is_primitive_browser(request):
    ''' Returns whether browser is dumb based on Django request. 
        A browser is primitive if it can not properly display javascript or css. '''
    
    b = browser_types(request)    
    dumb = (
        'unknown' in b or
        'wget' in b or
        'lynx' in b or
        'curl' in b or  
        # presumably a modern browser written in a language will not identify as that language
        'python' in b or
        'java' in b) 
    # log('is_primitive_browser: {}'.format(dumb))
    return dumb
          

def is_known_bot(browser, other):
    ''' Returns True if this access is from a known bot. '''
    
    def explicitly_accepted():
        accepted = False
        try:
            from jean import agent_accepted
            accepted = agent_accepted(browser)
        except:
            pass
        
        return accepted

    browser_lc = browser.lower()
    other_lc = other.lower()
    return (
        
        not explicitly_accepted() and  
        
        (len(browser) <= 0 or
         len(other) <= 0 or                       # essential in some form, may filter out too much
         (browser_lc == 'mozilla' and len(other) <= 0) or # fake mozilla
         browser_lc.find('bot') >= 0 or           # bot
         other_lc.find('bot') >= 0 or
         browser_lc.find('spider') >= 0 or        # spider
         other_lc.find('spider') >= 0 or
         browser_lc.find('baidu') >= 0 or         # BaiduSpider
         other_lc.find('baidu') >= 0 or
         browser_lc.find('walker') >= 0 or        # walker
         other_lc.find('walker') >= 0 or
         browser_lc.find('crawl') >= 0 or         # crawl
         other_lc.find('crawl') >= 0 or
         browser_lc.startswith('java') or         # language lib
         browser_lc.find('python-urllib') >= 0 or
         browser_lc.find('libwww-perl') >= 0 or
         browser_lc.find('yahoo') >= 0 or         # Yahoo
         browser_lc.find('slurp') >= 0 or         # slurp
         other_lc.find('slurp') >= 0 or
         browser_lc.find('curl') >= 0 or          # curl
         browser_lc.find('python') >= 0 or        # python
         browser_lc.find('perl') >= 0 or          # perl
         browser_lc.find('nambu') >= 0 or         # nambu
         browser_lc.find('docomo') >= 0 or        # DoCoMo
         browser_lc.find('digext') >= 0 or        # DigExt
         browser_lc.find('morfeus') >= 0 or       # Morfeus
         browser_lc.find('twitt') >= 0 or         # twitt
         browser_lc.find('sphere') >= 0 or        # sphere
         browser_lc.find('perl') >= 0 or          # perl
         browser_lc.find('pear') >= 0 or          # PEAR
         browser_lc.find('wordpress') >= 0 or     # wordpress
         browser_lc.find('radian') >= 0 or        # radian
         browser_lc.find('eventbox') >= 0 or      # eventbox
         browser_lc.find('monitor') >= 0 or       # monitor
         browser_lc.find('mechanize') >= 0 or     # mechanize
         browser_lc.find('facebookexternal') >= 0 or # facebookexternal
         other_lc.find('scoutjet') >= 0 or        # Scoutjet
         browser_lc.find('yandex') >= 0 or        # Yandex
         other_lc.find('yandex') >= 0 or
         browser_lc.find('archiver') >= 0 or      # Archiver
         browser_lc.find('ia_archiver') >= 0 or   # Alexa
         other_lc.find('qqdownload') >= 0 or      # QQ
         other_lc.find('ask jeeves') >= 0 ) )     # Ask Jeeves 

def is_known_harvester(user_agent):
    ''' Returns True if this access is from a known harvester. '''
    
    return ( user_agent.startswith('Java/1.4.1_04') or
             user_agent.startswith('Mozilla/4.0 (compatible ; MSIE 6.0; Windows NT 5.1)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows 98)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.0; Windows NT; DigExt; DTS Agent') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1)') or
             user_agent.startswith('Java/1.6.0_04') or
             user_agent.startswith('Mozilla/4.0(compatible; MSIE 5.0; Windows 98; DigExt)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)') or
             user_agent.startswith('MJ12bot/v1.0.8 (http://majestic12.co.uk/bot.php?+)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.01; Windows NT 5.0)') or
             user_agent.startswith('Java/1.6.0_20') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.0; Windows NT; DigExt)') or
             user_agent.startswith('Java/1.6.0_21') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)') or
             user_agent.startswith('Mozilla/5.0 (compatible; Googlebot/2.1; http://www.google.com/bot.html)') or
             user_agent.startswith('Java/1.5.0_06') or
             user_agent.startswith('Java/1.6.0_13') or
             user_agent.startswith('Java/1.6.0_24') or
             user_agent.startswith('Java/1.6.0_11') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows 98) XX') or
             user_agent.startswith('Java/1.6.0_17') or
             user_agent.startswith('Java/1.6.0_22') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)') or
             user_agent.startswith('Java/1.6.0_07') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)') or
             user_agent.startswith('Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us; rv:1.9.2.3) Gecko/20100401 YFF35 Firefox/3.6.3') or
             user_agent.startswith('Java/1.6.0_23') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en)') or
             user_agent.startswith('Java/1.6.0_06') or
             user_agent.startswith('Java/1.6.0_26') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET') or
             user_agent.startswith('Java/1.6.0_05') or
             user_agent.startswith('ISC Systems iRc Search 2.1') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)') or
             user_agent.startswith('Java/1.6.0_15') or
             user_agent.startswith('Java/1.6.0_14') or
             user_agent.startswith('Java/1.6.0_03') or
             user_agent.startswith('Java/1.6.0_12') or
             user_agent.startswith('Mozilla/3.0 (compatible)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 2.0.50727)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; InfoPath.1)') or
             user_agent.startswith('Java/1.6.0_02') or
             user_agent.startswith('Mozilla/3.0 (compatible; Indy Library)') or
             user_agent.startswith('Java/1.6.0_18') or
             user_agent.startswith('Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.0.7) Gecko/20060909 Firefox/1.5.0.7') or
             user_agent.startswith('Missigua Locator 1.9') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET)') or
             user_agent.startswith('Java/1.6.0_16') or
             user_agent.startswith('Java/1.5.0_04') or
             user_agent.startswith('Java/1.6.0_01') or
             user_agent.startswith('Wells Search II') or
             user_agent.startswith('Java/1.6.0') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; .NET CLR 1.0.3705)') or
             user_agent.startswith('Java/1.6.0_29') or
             user_agent.startswith('Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US; rv:1.9.2.11) Gecko/20101012 Firefox/3.6.11 GTB7.1 ( .NET CLR 3.5.30729; .NET4.0E)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; MyIE2; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.0; Windows NT)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.0.3705;') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Win32)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 2.0.50727)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; InfoPath.1)') or
             user_agent.startswith('Java/1.5.0_02') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)') or
             user_agent.startswith('Java/1.4.2_03') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; InfoPath.2)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 5.0)') or
             user_agent.startswith('Java/1.6.0_25') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0b; Windows NT 6.0)') or
             user_agent.startswith('Opera/9.0 (Windows NT 5.1; U; en)') or
             user_agent.startswith('Java/1.6.0-oem') or
             user_agent.startswith('Microsoft URL Control - 6.01.9782') or
             user_agent.startswith('Microsoft URL Control - 6.00.8862') or
             user_agent.startswith('Java/1.5.0_11') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Win32)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727; .NET CLR 3.0.04506)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE8.0; Windows NT 6.0) .NET CLR 2.0.50727)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; FunWebProducts)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506; InfoPath.2)') or
             user_agent.startswith('Java/1.6.0_27') or
             user_agent.startswith('Java/1.5.0_05') or
             user_agent.startswith('Mozilla/5.0 (Windows NT 5.1; U; en) Opera 8.01') or
             user_agent.startswith('Opera/9.00 (Windows NT 5.1; U; en)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; Win64; AMD64)') or
             user_agent.startswith('Java/1.6.0_10') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; .NET CLR 1.0.3705; .NET CLR 1.1.4322)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; FREE; .NET CLR 1.1.4322)') or
             user_agent.startswith('8484 Boston Project v 1.0') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; MRA 4.3 (build 01218))') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.0.3705)') or
             user_agent.startswith('Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.2; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)') )
    
    
def get_agent_info(agent):
    '''Get the browser name, version, and other data from the agent.
    
       If agent not defined, return empty strings.
    '''
    
    if agent:
        User_Agent_Format = re.compile(r"(?P<browser>.*?)/(?P<version>[0-9\.]*)\s*(?P<other>\(?.*\)?)")
        m = User_Agent_Format.search(agent)
        if m:
            browser_name = m.group('browser')
            browser_version = m.group('version')
            other = m.group('other')
        else:
            browser_name = browser_version = other = ''
    else:
        browser_name = browser_version = other = ''

    return browser_name, browser_version, other


if __name__ == "__main__":
    import doctest
    doctest.testmod()

