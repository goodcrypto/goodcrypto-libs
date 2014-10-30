#!/usr/bin/env python
'''
    Download a file or site.

    Simple download program and library. Wget replacement. Does not yet use proxies or
    rewrite links of downloaded pages.

    See
        Extracting data from HTML
        http://diveintopython.org/html_processing/extracting_data.html

        Resuming download of a file (Python) by Chris Moffitt
        http://code.activestate.com/recipes/83208-resuming-download-of-a-file/

    Portions Copyright 2011-2013 GoodCrypto
    Last modified: 2014-07-10

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from optparse import OptionParser
import os, re, socket, sys, traceback, urllib, urllib2, urlparse
from sgmllib import SGMLParser

common_agent = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.1.3) Gecko/20090824 Firefox/3.5.3 (.NET CLR 3.5.30729)'

seen_urls = []
all_links = set()
all_images = set()

class URLLister(SGMLParser):
    ''' Parse links from html. '''

    def reset(self):
        SGMLParser.reset(self)
        self.links = []
        self.imgs = []

    def start_a(self, attrs):
        href = [v 
            for k, v in attrs if k=='href']
        if href:
            self.links.extend(href)

    def start_img(self, attrs):
        src = [v 
            for k, v in attrs if k=='src']
        if src:
            self.imgs.extend(src)

    def start_enclosure(self, attrs):
        # rss xml
        url = [v 
            for k, v in attrs if k=='url']
        if url:
            self.links.extend(url)

def main():
    ''' Run from command line. '''

    try:
        download()
    except KeyboardInterrupt:
        # don't be noisy if Ctrl-C
        sys.exit(-2)
    except:
        error()
        sys.exit(-1)

def contents(url):
    ''' Get contents of url. '''

    stream = urllib.urlopen(url)
    page = stream.read()
    stream.close()
    return page

def links(url=None, content=None):
    ''' Get links from url or content. Converts relative links to absolute. '''

    if not content:
        content = contents(url)
    parser = URLLister()
    parser.feed(content)
    parser.close()
    links = absolute_urls(url, parser.links)
    all_links.update(links)
    return links

def images(url=None, content=None):
    ''' Get image urls from url or content. Converts relative links to absolute. '''

    if not content:
        content = contents(url)
    parser = URLLister()
    parser.feed(content)
    parser.close()
    image_urls = absolute_urls(url, parser.imgs)
    all_images.update(image_urls)
    return image_urls
    
def absolute_urls(parent_url, urls):
    ''' Get list of absolute urls '''
    
    if parent_url:
        urls = [urlparse.urljoin(parent_url, url) for url in urls]
    else:
        urls = list(urls)
    return urls

def filename(url):
    ''' Get the default filename from the url.

        If the url ends with '/', the filename is "index.html". '''

    name = url.split('/')[-1].split('#')[0].split('?')[0]
    if not name:
        name = 'index.html'
    return name

def filecontents(filename):
    ''' Get file contents. '''

    file = open(filename, 'rb')
    content = file.read()
    file.close()
    return content

def getfile(url, save=True, file=None):
    ''' Get url contents as file. '''

    def open_url(url):
        if options.debug: print('opening {}'.format(url))
        if not options.quiet:
            update_status(byte_count)
        request = get_request(url)
        try:
            result = get_response(request)
        except:
            result = None
            print('unable to open {}'.format(url))
            raise
        return result

    def get_request(url):
        request = urllib2.Request(url)
        request.add_header('User-agent', common_agent)
        if not options.cache:
            request.add_header('Pragma','no-cache')
        return request

    def get_response(request):
        response = urllib2.urlopen(request)
        get_headers(response)
        return response

    def get_headers(response):
        # fold key case
        for k,v in response.headers.items():
            response.headers[k.lower()] = v
        if options.debug:
            print 'http headers:'
            for k,v in response.headers.items():
                print ' ', k, '=', v

    def get_content_filename(url):
        content_filename = filename(url)
        if options.debug: print('content_filename:{}'.format(content_filename))
        return content_filename

    def filesize(filename):
        if os.path.exists(filename):
            size = os.path.getsize(filename)
        else:
            size = 0
        return size
        
    def pathname(filename):
        return os.path.abspath(os.path.join(os.getcwd(), filename))

    def update_status(byte_count):
        ''' Show progress. '''

        current_file_size = filesize(content_filename)
        
        if downloaded and current_file_size:
            
            print(clear_line + '{0:40}\t100%%'.format(content_filename))
                
        elif save:
            
            if byte_count:                                                                               
                
                if full_length:
                    # !!!!! python 3
                    percent = (100.0 * current_file_size) / full_length
                    if options.verbose:
                        print(clear_line +
                            '%40s\t%3.0f%%\t%d/%d bytes' %
                            (content_filename, percent, current_file_size, full_length)),
                    else:
                        print(clear_line +
                            '%40s\t%3.0f%%' %
                            (content_filename, percent)),
                        
                elif current_file_size:
                    print(clear_line +
                        '{filename} {filesize} bytes'.format(filename=content_filename, filesize=current_file_size)),
                    
            else:
                print(clear_line + '{} starting...'.format(content_filename)),

        else:
            print (clear_line +
                '%s %d bytes' %
                (content_filename, byte_count)),

        sys.stdout.flush()

    # clear_line must be at least as long as the longest status line, but less than console width
    clear_line = '\r' + ' '*80 + '\r'
    content_filename = get_content_filename(url)
    current_file_size = filesize(content_filename)
    downloaded = False
    byte_count = 0
    full_length = None
    
    response = open_url(url)
    if response:

        if url != response.geturl():
            if options.verbose:
                print('redirected {url} to {response}'.format(url=url, response=response.geturl()))
            url = response.geturl()

        try:
            content_length = int(response.headers['content-length'])
        except KeyError:
            content_length = None
        full_length = content_length

        if save:

            downloaded = (
                # if the server does not report Content-length, we assume any content we have is complete
                # if the download was interrupted or the content is volatile this may be wrong,
                # but the alternative is to always re-download
                (content_length == None and current_file_size) or
                (full_length != None and full_length <= current_file_size) or
                (not options.resume and current_file_size > 0))

        if downloaded:
            if options.debug: print('already downloaded {}'.format(url))
            response.content = filecontents(content_filename)
            if full_length and full_length < current_file_size:
                print('Warning: {} is larger than content on web'.format(content_filename))
            update_status(byte_count)

        else:

            if save:
                # try to start from end of already downloaded content
                ''' As of 2011-06-13 Archive.org often doesn't supply accept-ranges but accepts Range header.
                    What about other sites? Any that don't accept Range today?
                    We check for content-range anyway so we should be fine.
                if (options.resume and current_file_size and
                    'accept-ranges' in response.headers and response.headers['accept-ranges'] == 'bytes'):
                '''
                if (options.resume and current_file_size):
                    request = get_request(url)
                    request.add_header('Range', 'bytes={}-'.format(current_file_size))
                    if options.debug: print 'added Range header'
                    response = get_response(request)
                    # this content_length is only for the current range
                    content_length = int(response.headers['content-length'])

                # if server is sending requested range, start at the end of the file
                if 'content-range' in response.headers:
                    # header looks like: content-range = bytes 123-456/457
                    full_length = int(response.headers['content-range'].split('/')[1])
                    if options.debug: print 'appending to {}'.format(pathname(content_filename))
                    output_file = open(content_filename, 'ab')
                else:
                    if options.debug: print 'writing to {}'.format(pathname(content_filename))
                    output_file = open(content_filename, 'wb')

            buffer_size = 1024 * 1024

            response.content = ''
            data = response.read(buffer_size)
            # like urllib.urlretrieve(), get all the data available, even if it's more than content-length
            while bool(data):
                response.content += data
                if save:
                    output_file.write(data)
                    output_file.flush()
                byte_count = byte_count + len(data)
                if not options.quiet:
                    update_status(byte_count)
                data = response.read(buffer_size)

            if save:
                output_file.close()

            if content_length and byte_count < content_length:
                '''
                raise urllib.ContentTooShortError(
                    'expected %d bytes, got %d from %s' % (content_length, byte_count, url),
                    response.content)
                '''
                print('expected {} bytes, only got {} from {}'.format(content_length, byte_count, url))
            if not options.quiet:
                # terminate the status line
                print

        response.close()

    else:
        print('no response from {}'.format(url))
        
    return response

def get(url, save=True, depth=0, file=None, offsite=False, linkmask=None):
    ''' Get url contents.

        If save=True, save as file. Otherwise spider the site to the specified depth.

        If depth>0 get contents of links recursively.
        Depth is the recursion depth.

        If offsite is True, offsite links will be followed.

        Linkmask is a regular expression that links must match. '''
        
    def retry(why):
        if options.debug:
            print('{}. retrying'.format(why))
        else:
            print ' retrying'
        return tries - 1
        
    def look_for_links(response, depth):
        ''' Decide whether to look for links in this response. '''
        
        if (response.headers['content-type'].startswith('text/html') 
            or response.headers['content-type'].startswith('text/xml')):
        
            if depth > 0:
                look = True
                
            else:
                look = False
                if options.debug: print 'not getting links because depth is %d' % depth
   
        else:
            look = False
            if options.debug: print 'not getting links because content-type is %s' % response.headers['content-type']
                
        return look

    seen_urls.append(url)
    
    downloaded = False
    tries = 1 + options.retries
    depth = options.depth
    
    while not downloaded and tries:
        if options.debug: print('getting {}'.format(url))
        try:
            response = getfile(url, file=file, save=save)
            if response:
                if options.debug: print 'got response from %s' % url
                downloaded = True
        except urllib2.URLError:
            _, value, _ = sys.exc_info()
            if 'timed out' in str(value):
                tries = retry('timed out opening url')
            else:
                tries = retry('bad url')
        except socket.timeout:
            tries = retry('timed out')
        except urllib.ContentTooShortError:
            tries = retry('content too short')
        except KeyboardInterrupt:
            raise
        except:
            tries = 0
            if options.debug: print 'tries set to zero'
            error()

    if downloaded:

        if options.debug: print 'downloaded %s' % url
        if look_for_links(response, depth):
                
            depth = depth - 1
            try:
                urls = []
                
                if getlinks_implied():
                    urls += links(url, content=response.content)
                    if options.debug: print 'links: %s' % urls
                
                if options.getimages:
                    image_urls = images(url, content=response.content)
                    if options.debug: print 'image urls: %s' % image_urls
                    urls += image_urls

            except:
                if options.debug: print 'error getting links for %s' % url
                error()

            else:
                for link in urls:
                    link = link.split('#')[0]
                    if options.debug: print 'link: %s' % link
                    if link_ok(url, link, linkmask, offsite):
                        get(link, depth=depth, offsite=offsite, linkmask=linkmask)

    else:
        print 'unable to download %s' % url
        if not options.keepon:
            sys.exit(-1)

def make_parser():
    ''' Create command line parser. '''

    usage = 'usage: %prog [option...] <url> [<url>...]'
    parser = OptionParser(usage)
    parser.set_defaults(
        depth=sys.maxint,
        verbose=False,
        quiet=False,
        all=False,
        offsite=False,
        endswith=None,
        linkmask=None,
        file=None,
        resume=True,
        debug=False)
    parser.add_option('', '--getlinks',
                      action='store_true',
                      help='follow and download links')
    parser.add_option('', '--getimages',
                      action='store_true',
                      help='download images')
    parser.add_option('', '--offsite',
                      action='store_true',
                      help='follow offsite links, default is only follow links to the same site')
    parser.add_option('', '--endswith',
                      help="only get links that end with this, example: --endswith=mp3")
    parser.add_option('', '--linkmask',
                      help='only get links that match this regular expression')
    parser.add_option('', '--file',
                      help='output filename for base url')
    parser.add_option('', '--no-resume',
                      action='store_false', dest='resume',
                      help="don't resume partial files, download starting at the beginning")
    parser.add_option('', '--no-cache',
                      action='store_false', dest='cache',
                      help="request content from original server, bypassing any proxy caches")
    parser.add_option('', '--depth',
                      help='depth of links to get if --getlinks, default is zero',
                      type=int, default=0)
    parser.add_option('', '--timeout',
                      help='timeout in seconds, default is 60 seconds',
                      type=int, default=60)
    parser.add_option('', '--retries',
                      help='max retries, default is 10',
                      type=int, default=10)
    parser.add_option('', '--keepon',
                      action='store_true',
                      help='keep going if errors')
    parser.add_option('', '--verbose',
                      action='store_true',
                      help='show more details')
    parser.add_option('', '--quiet',
                      action='store_true',
                      help='no status updates')
    parser.add_option('', '--debug',
                      action='store_true',
                      help='show debugging information')
    return parser

def download():
    ''' Download one or more urls as files. '''

    global options

    options, args = parser.parse_args()
    if args:

        if options.debug: options.verbose = True

        socket.setdefaulttimeout(options.timeout)

        if getlinks_implied():
            
            if options.depth < 1: options.depth = 1

            for url in args:

                # set linkmask
                # --linkmask overrides --endswith
                if options.linkmask:
                    linkmask = options.linkmask
                elif options.endswith:
                    linkmask = '^.*%s$' % options.endswith
                    if options.debug: print 'only links that end with "%s"' % options.endswith
                # linkmask defaults to strings that start with the base url
                # if you want all links, specify "--linkmask=.*"
                else:
                    linkmask = options.linkmask or '^%s.*$' % url
                if options.debug: print 'only links that match "%s"' % linkmask
                save = matches_linkmask(linkmask, url)

                get(url, save=save, depth=options.depth,
                    offsite=options.offsite, linkmask=linkmask)

        else:
            for url in args:
                get(url, file=options.file)
    else:
        parser.error('You must include a base url')
        
def getlinks_implied():
    return options.getlinks or options.endswith or options.linkmask

def link_ok(url, link, linkmask, offsite=False):
    ok = (
        onsite(url, link, offsite) and
        matches_linkmask(linkmask, link) and
        new_url(link))
    if options.debug:
        if ok:
            print 'link ok: %s' % link
        else:
            print 'link not ok: %s' % link
    return ok

def onsite(url, link, offsite=False):
    ok = (
        urlparse.urlparse(url).netloc == urlparse.urlparse(link).netloc or
        offsite)
    if not ok and options.debug:
        print 'not following offsite link: %s' % link
    return ok

def matches_linkmask(linkmask, url):
    if linkmask:
        ok = re.match(linkmask, url)
    else:
        ok = True
    if not ok and options.debug:
        print 'url does not match linkmask: %s' % url
    return ok

def new_url(url):
    ok = url not in seen_urls
    if not ok and options.debug:
        print 'already seen: %s' % url
    return ok

def error():
    type, value, _ = sys.exc_info()
    if options.verbose:
        # AttributeError: format_exception_only
        # return traceback.format_exception_only(type, value)
        print '%s: %s' % (
            str(type).split('.')[-1].strip("'<>"),
            value)
        if options.debug: print traceback.format_exc()
    return type, value

parser = make_parser()
# we reparse args if invoked from command line
options, args = parser.parse_args()

if __name__ == '__main__':
    main()
