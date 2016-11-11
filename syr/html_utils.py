'''
    HTML utilities

    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-07-07

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    reload(sys)
    sys.setdefaultencoding('utf-8')

    from HTMLParser import HTMLParser
else:
    from html.parser import HTMLParser

import os.path, re
from syr.log import get_log

log = get_log(recreate=True)

DEBUGGING = False

# Tags which will be allowed, unless we're skipping tags
DEFAULT_GOOD_TAGS = set([
    '!doctype',
    'a',
    'abbr',
    'acronym',
    'address',
    'area',
    'b',
    'base',
    'basefont',
    'bdo', # !! what's this?
    'big',
    'blockquote',
    'body',
    'br',
    'break',
    'button',
    'caption',
    'center',
    'code',
    'col',
    'colgroup',
    'dd',
    'del',
    'dir',
    'div',
    'dl',
    'dt',
    'em',
    'face',
    'fieldset',
    'font',
    'form',
    'frame', # !! are frame and frameset ok?
    'frameset',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'head',
    'hr',
    'html',
    'i',
    #'iframe',
    #'img',
    'input',
    'ins',
    'isindex',
    'kbd', # !! what's this?
    'label',
    'legend',
    'li',
    'map',
    'menu',
    'meta',
    'nobr',
    'noframes',
    'noscript',
    'ol',
    'optgroup',
    'option',
    'p',
    'pre',
    'q',
    's',
    'samp', # what's this?
    'select',
    'small',
    'span',
    'strike',
    'strong',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'textarea',
    'tfoot',
    'th',
    'thead',
    'title',
    'tr',
    'tt',
    'u',
    'ul',
    'var',
    ])
# Tags which trigger skipping all tags, until this tag is closed
DEFAULT_SKIPPED_TAGS = set([
    'javascript',
    'script',
    ])
# Attributes within tags which will be ignored
# See
#     HTML Event Attributes
#     http://www.w3schools.com/tags/ref_eventattributes.asp
# !!!! This should be a list of whitelisted attributes.
#      But that requires a lot more encoded html knowledge.
DEFAULT_BAD_ATTRIBUTES = set([
    'javascript',
    'script',
    # Window Event Attributes
    'onafterprint',
    'onbeforeprint',
    'onbeforeunload',
    'onerror',
    'onhashchange',
    'onload',
    'onmessage',
    'onoffline',
    'ononline',
    'onpagehide',
    'onpageshow',
    'onpopstate',
    'onresize',
    'onstorage',
    'onunload',
    # Form Events
    'onblur',
    'onchange',
    'oncontextmenu',
    'onfocus',
    'oninput',
    'oninvalid',
    'onreset',
    'onsearch',
    'onselect',
    'onsubmit',
    # Keyboard Events
    'onkeydown',
    'onkeypress',
    'onkeyup',
    # Mouse Events
    'onclick',
    'ondblclick',
    'ondrag',
    'ondragend',
    'ondragenter',
    'ondragleave',
    'ondragover',
    'ondragstart',
    'ondrop',
    'onmousedown',
    'onmouseleave',
    'onmousemove',
    'onmouseout',
    'onmouseover',
    'onmouseup',
    'onmousewheel',
    'onscroll',
    'onwheel',
    # Clipboard Events
    'oncopy',
    'oncut',
    'onpaste',
    # Media Events
    'onabort',
    'oncanplay',
    'oncanplaythrough',
    'oncuechange',
    'ondurationchange',
    'onemptied',
    'onended',
    'onerror',
    'onloadeddata',
    'onloadedmetadata',
    'onloadstart',
    'onpause',
    'onplay',
    'onplaying',
    'onprogress',
    'onratechange',
    'onseeked',
    'onseeking',
    'onstalled',
    'onsuspend',
    'ontimeupdate',
    'onvolumechange',
    'onwaiting',
    # Misc Events
    'onerror',
    'onshow',
    'ontoggle',
    ])
SOME_BAD_TAGS = ['img', 'javascript', 'script', 'style', 'video']

class HtmlFirewallException(Exception):
    pass

def firewall_html(html_text):
    ''' Firewall html.

        Default deny, then whitelist html.

        Only allow plain html. No executables.

        Css allows embedding of executables, and we don't have a css parser.
        See http://stackoverflow.com/questions/2497146/is-css-turing-complete
        So the 'style' tag and attribute are not allowed.

        Whitelist good tags. Reject all others. For some tags start
        skipping html until tag is closed.

        Blacklist bad attributes within tags. To do: Whitelist attributes
        within tags. But that requires a lot more encoded html knowledge.

        Strip extra instances of "</html>".

        >>> # executable gets through - from Security Audit of GoodCrypto - Taylor Hornby - December 21, 2014
        >>>
        >>> test1 = """
        ... <html>
        ...     <body>
        ...         ... <p onmouseout="alert(1)">
        ...         ... Hover over this text, then move your mouse away.
        ...         ... </p>
        ...     </body>
        ... </html>
        ... """
        >>> clean_test1 = firewall_html(test1)
        >>> assert not 'onmouseout' in clean_test1

        >>> import os
        >>> if IS_PY2:
        ...     from urllib2 import urlopen
        ... else:
        ...     from urllib.request import urlopen

        >>> html_end_tag = r'</html>'

        >>> test1 = '<html> <body> in first body </body> </html> <body> in second body </body> </html> before last html endtags </html>'
        >>> html_segments = re.split(html_end_tag, test1)
        >>> log.debug('test1 html:\\n{}'.format(test1))
        >>> log.debug('test1 html_segments: {}'.format(repr(html_segments)))
        >>> len(html_segments)
        4
        >>> clean_test1 = firewall_html(test1)
        >>> endtags = re.findall(html_end_tag, clean_test1)
        >>> len(endtags)
        1

        # net tests disabled for speed. re-enable them anytime
        # >>> f = urlopen('http://docs.docker.io/en/latest/installation/ubuntulinux/')
        # >>> html = f.read()
        # >>> f.close()
        # >>> log.debug('dockio.io test html:\\n{}'.format(html))

        # >>> endtags = re.findall(html_end_tag, html)
        # >>> log.debug('dockio.io test endtags: {}'.format(repr(endtags)))
        # >>> # may or may not be multiple /html endtags. probably mitm
        # >>> if len(endtags) > 1:
        # ...     clean_html = firewall_html(html)
        # ...     endtags = re.findall(html_end_tag, clean_html)
        # ...     assert len(endtags) <= 1

        >>> # test html files that should not pass
        >>> # some page tests are in both webbox and syr.html because the urls
        >>> # seem to fail in webbox, but not in standalone tests.
        >>> # running these tests in both places would be best
        >>> # how do we run the same doctests in different modules without
        >>> # replicating doctest code?
        >>> # import goodcrypto.webbox.tests # where is webbox?
        >>> for test_module_path in [
        ...     __file__,
        ...     # goodcrypto.webbox.tests.__file__,
        ...     ]:
        ...     test_page_dir = os.path.join(
        ...             os.path.dirname(test_module_path),
        ...             'tests/testdata/html/HtmlFirewallFilter/pages')
        ...     log.debug('test_page_dir: {}'.format(test_page_dir))
        ...     for filename in os.listdir(test_page_dir):
        ...         if filename != 'notes.txt':
        ...             pathname = os.path.join(test_page_dir, filename)
        ...             log.debug('test file pathname: {}'.format(pathname))
        ...             with open(pathname) as testfile:
        ...                 original_html = testfile.read()
        ...                 try:
        ...                     firewalled_html = firewall_html(original_html)
        ...                 except Exception as exp:
        ...                     log.debug(exp)
        ...                     raise
        ...                 else:
        ...                     # save html in /tmp
        ...                     outname = os.path.join('/tmp', 'html-firewall-test.'+filename+'.original')
        ...                     with open(outname, 'wb') as outfile:
        ...                         outfile.write(original_html)
        ...                     outname = os.path.join('/tmp', 'html-firewall-test.'+filename+'.firewalled')
        ...                     with open(outname, 'wb') as outfile:
        ...                         outfile.write(firewalled_html)
        ...
        ...                     for bad_tag in SOME_BAD_TAGS:
        ...                         assert '<'+bad_tag not in firewalled_html, 'tag {} found in cleaned html'.format(bad_tag)
    '''

    def feed_segment(segment):
        ''' Feed segment to parser.

            Replace UnicodeDecodeError chars with '?'.
        '''

        done = False
        while not done:

            try:
                parser.feed(segment)

            except UnicodeDecodeError as ude:

                error_text = str(ude)

                # pattern example: 'UnicodeDecodeError: 'utf8' codec can't decode byte 0xa1 in position 100: invalid start byte'
                pattern = r"codec can't decode byte (.*?) in position (.*?):"
                # log.debug('matching pattern "{}" against error text "{}"'.
                #     format(pattern, error_text))
                match = re.search(pattern, error_text)
                if match:

                    # log.debug('error match: {}'.format(match.group(0)))
                    bad_byte = match.group(1)
                    bad_position = int(match.group(2))

                    log.debug('removing {} at position {}'.format(bad_byte, bad_position))
                    segment = segment[:bad_position-2] + '?' + segment[:bad_position]

                else:
                    raise

            else:
                done = True

    HTML_END_TAG_PATTERN = r'</\s*html\s*>'

    # Strip early instances of "</html>"
    html = html_text
    endtags = re.findall(HTML_END_TAG_PATTERN, html)
    html_segments = re.split(HTML_END_TAG_PATTERN, html)
    if len(endtags) > 1:
        log.debug('{} html end tags'.format(len(endtags)))
        assert len(html_segments) == len(endtags) + 1

    parser = HtmlFirewallFilter()
    for segment in html_segments:
        feed_segment(segment)

    # this will add </html> after every </body>, so we may have
    # multiple </html> instances
    # but we do in fact filter the html in all segments
    # parser.feed('</html>')
    parser.close()
    firewalled_html = parser.results() + '</html>'

    """ takes forever, if it's not an infinite loop
    # if any bad tags, disable tag with '?' prefix
    pattern = re.compile(r'(.*<\s*)([A-Za-z]+)(.*)')
    match = pattern.search(firewalled_html)
    if match:
        new_firewalled_html = ''

        while match:
            before, tag, after = match.group(1, 2, 3)
            if not tag in DEFAULT_GOOD_TAGS:
                log.debug('unfiltered bad tag: {}'.format(tag))
                new_firewalled_html = new_firewalled_html + before + '?' + tag
                match = pattern.search(after)

        firewalled_html = new_firewalled_html
    """

    # quick check using regular expression
    # if bad tags, raise exception
    bad_tags_found = set()
    for tag in SOME_BAD_TAGS:
        pattern = r'<\s*{}'.format(tag)
        if re.search(pattern, firewalled_html):
            bad_tags_found.add(tag)
    if bad_tags_found:
        msg = ('firewall_html() failed. Please send url to goodcrypto.com for testing.' +
        ' HTML tags incorrectly passed firewall: {}'.format(','.join(bad_tags_found)))
        log.error(msg)
        # log.debug('html before firewall_html():\n{}'.format(html))
        with open('/tmp/syr.html.firewall_html.failed.before', 'w') as outfile:
            # the filtered html has line breaks before every tag
            # so to diff, we need line breaks in the unfiltered html
            html_with_newlines = re.sub(r'\n*\s*<\s*(?!/)', '\n<', html)
            outfile.write(html_with_newlines)
        # log.debug('html after firewall_html():\n{}'.format(firewalled_html))
        with open('/tmp/syr.html.firewall_html.failed.after', 'w') as outfile:
            firewalled_html_with_newlines = re.sub(r'\n*\s*<\s*(?!/)', '\n<', firewalled_html)
            outfile.write(firewalled_html_with_newlines)
        raise HtmlFirewallException(msg)
        # we often don't raised an exception because we get false positives, and we don't have a good
        # way to ignore those false positives
        # example:
        #     https://gist.github.com/ah8r/10632982
        #     <input type="text" readonly="None" spellcheck="false" class="url-field js-url-field" name="embed-field" value="<script src="https://gist.github.com/ah8r/10632982.js"></script>">

    return firewalled_html

class HtmlFirewallFilter(HTMLParser, object):

    # !! perhaps this should be a user option
    # CSS can contain embedded scripts, and we don't have a
    # parser that detects them. So no css allowed.
    allow_style_sheets = False

    rel = "rel"
    style = "style"
    stylesheet = "stylesheet"
    link = "link"

    def __init__(self, *args, **kwargs):
        self.good_tags = DEFAULT_GOOD_TAGS
        self.skipped_tags = DEFAULT_SKIPPED_TAGS
        self.bad_attributes = DEFAULT_BAD_ATTRIBUTES
        self.blocked_attributes = set()
        self.blocked_attribute_values = set()

        if (HtmlFirewallFilter.allow_style_sheets):
            self.good_tags.add(HtmlFirewallFilter.style);
            self.good_tags.add(HtmlFirewallFilter.link);
        else:
            self.skipped_tags.add(HtmlFirewallFilter.style);
            self.bad_attributes.add(HtmlFirewallFilter.style);

        self.skipping = None
        self.preformatted = False

        self.plain_html = ''
        self.last_start_tag = ''
        super(HtmlFirewallFilter, self).__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):

        def bad_attribute_value(value):
            """ Check for nasty bypass of firewall.

                Example::
                    javascript:void((function()%7Bvar%20e=document.createElement(&apos;script&apos;);e.setAttribute(&apos;type&apos;,&apos;text/javascript&apos;);e.setAttribute(&apos;charset&apos;,&apos;UTF-8&apos;);e.setAttribute(&apos;src&apos;,&apos;//assets.pinterest.com/js/pinmarklet.js?r=&apos;+Math.random()*99999999);document.body.appendChild(e)%7D)());
            """

            is_bad = False
            if value:
                # strip white space
                value = value.translate({' ': None, '\t': None, '\n': None})
                if ('script:' in value or
                    # &#58; is a hidden colon
                    'script&#58;' in value or
                    '&lt;' in value or
                    '<' in value):

                    is_bad = True

            return is_bad

        if tag in self.skipped_tags:
            if DEBUGGING: log.debug('start skipping tag: ' + tag)
            self.skipping = tag

        elif tag in self.good_tags:
            if DEBUGGING: log.debug('good tag: ' + tag)
            self.plain_html += '<{}'.format(tag)
            for attr, value in attrs:
                if attr in self.bad_attributes:
                    # only mention each attr once
                    if not attr in self.blocked_attributes:
                        self.blocked_attributes.add(attr)
                        if DEBUGGING: log.debug('ignored bad attribute: ' + attr)

                elif bad_attribute_value(value):
                    # only mention each value once
                    if not value in self.blocked_attribute_values:
                        self.blocked_attribute_values.add(value)
                        log.debug('blocked bad attribute value ' + value)

                else:
                    try:
                        self.plain_html += ' {}="{}"'.format(attr, value)
                    except UnicodeEncodeError:
                        try:
                            log.debug('UnicodeEncodeError for attr: {}="{}"'.format(
                                attr.encode('ascii', 'ignore'),
                                value.encode('ascii', 'ignore')))
                            self.plain_html += ' {}="{}"'.format(
                                attr.encode('ascii', 'ignore'),
                                value.encode('ascii', 'ignore'))
                        except:
                            log.warning('could not recover from UnicodeEncodeError')

            self.plain_html += '>'

            if tag == 'pre':
                self.preformatted = True

            if self.last_start_tag != tag:
                if not self.preformatted:
                    self.plain_html += '\n'
            self.last_start_tag = tag

        else:
            if DEBUGGING: log.debug('bad tag, ignored: ' + tag)

    def handle_endtag(self, tag):

        if self.skipping and tag == self.skipping:
            if DEBUGGING: log.debug('end skipping tag: ' + tag)
            self.skipping = None

        elif tag in self.good_tags:
            # log.debug('end good tag: ' + tag)
            self.plain_html += '</{}>'.format(tag)

            if tag == 'pre':
                self.preformatted = False

            if not self.preformatted:
                self.plain_html += '\n'

        else:
            if DEBUGGING: log.debug('end bad tag, ignored: ' + tag)

    def handle_data(self, data):
        if True: # len(data.strip()):

            if self.skipping:
                if DEBUGGING: log.debug('skipping data: ' + data)

            else:
                if DEBUGGING: log.debug('data: ' + data)
                self.plain_html += data

    def handle_entityref(self, name):
        if self.skipping:
            if DEBUGGING: log.debug('skipping entityref: ' + name)

        else:
            if DEBUGGING: log.debug('entityref: ' + name)
            self.plain_html += '&' + name + ';'

    def handle_charref(self, name):
        if self.skipping:
            if DEBUGGING: log.debug('skipping charref: ' + name)

        else:
            if DEBUGGING: log.debug('charref: ' + name)
            self.plain_html += '&#' + name + ';'

    def handle_comment(self, data):
        ''' Comments can contain embedded bad html, and we don't have a
            parser that detects them. So no comments.

            Example:
                <!--[if lte IE 9]><script # ...

            See http://www.gossamer-threads.com/lists/python/dev/459339

            A possible solution is to run this filter recursively on the
            comment data. Do we want to try to handle comments in scripts
            in comments in # ...? If we always remove scripts this may be
            realistic.
        '''

        if DEBUGGING: log.debug('skipping comment: ' + data)
        """
        if self.skipping:
            if DEBUGGING: log.debug('skipping comment: ' + data)

        else:
            if DEBUGGING: log.debug('comment: ' + data)
            self.plain_html += '<!--' + data + '-->'
        """

    def handle_decl(self, data):
        if self.skipping:
            if DEBUGGING: log.debug('skipping decl: ' + data)
        else:
            self.plain_html += '<!{}>'.format(data)

    def results(self):
        return self.plain_html

def extract_text(html):
    ''' Extract plain text from html.

        Requires BeautifulSoup 4.
    '''

    # from http://stackoverflow.com/questions/1936466/beautifulsoup-grab-visible-webpage-text
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html)
    texts = soup.findAll(text=True)

    def visible(element):
        if element.parent.name in ['style', 'script', '[document]', 'head', 'title']:
            return False
        elif re.match('<!--.*-->', str(element)):
            return False
        return True

    if IS_PY2:
        visible_texts = filter(visible, texts)
    else:
        visible_texts = list(filter(visible, texts))

    return '\n'.join(visible_texts)

if __name__ == "__main__":
    import doctest
    doctest.testmod()

