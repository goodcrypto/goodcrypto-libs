'''
    HTML utilities

    Copyright 2013-2014 GoodCrypto
    Last modified: 2015-09-26

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

# delete in python 3
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

import os.path, re
from syr.log import get_log

log = get_log(recreate=True)

import HTMLParser

DEBUGGING = False

def firewall_html(html):
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

        >>> import os, urllib2

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
        # >>> f = urllib2.urlopen('http://docs.docker.io/en/latest/installation/ubuntulinux/')
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
        ...     for filename in os.listdir(test_page_dir):
        ...         if filename != 'notes.txt':
        ...             pathname = os.path.join(test_page_dir, filename)
        ...             with open(pathname) as testfile:
        ...                 original_html = testfile.read()
        ...                 try:
        ...                     firewalled_html = firewall_html(original_html)
        ...                 except exp:
        ...                     raise
        ...                 else:
        ...                     # save html in /tmp
        ...                     outname = os.path.join('/tmp', filename+'.original')
        ...                     with open(outname, 'wb') as outfile:
        ...                         outfile.write(original_html)
        ...                     outname = os.path.join('/tmp', filename+'.firewalled')
        ...                     with open(outname, 'wb') as outfile:
        ...                         outfile.write(firewalled_html)
        ...
        ...                     bad_tags = ['javascript', 'video']
        ...                     for bad_tag in bad_tags:
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

    HTML_END_TAG_PATTERN = r'</html>' # !! why doesn't r'</\s*html\s*>' work?
    BAD_TAGS = ['script', 'img', 'style']

    # Strip early instances of "</html>"
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

    bad_tags_found = []
    for tag in BAD_TAGS:
        pattern = '<{}'.format(tag) # !! why not regex e.g. '<\s*{}'?
        if pattern in firewalled_html:
            bad_tags_found.append(tag)
    if bad_tags_found:
        msg = ('firewall_html() failed. Please save url for testing.' +
        ' Tags passed firewall: {}'.format(bad_tags_found))
        log.error(msg)
        log.debug('html before firewall_html():\n{}'.format(html))
        log.debug('html after firewall_html():\n{}'.format(firewalled_html))
        # we don't raised an exception because the only bad tags we've seen in
        # months (2014-04-16) are false positives, and we don't have a good
        # way to ignore those false positives
        # example:
        #     https://gist.github.com/ah8r/10632982
        #     <input type="text" readonly="None" spellcheck="false" class="url-field js-url-field" name="embed-field" value="<script src="https://gist.github.com/ah8r/10632982.js"></script>">
        # we probably need to raise a custom exception here
        #raise AssertionError(msg)

    return firewalled_html

class HtmlFirewallFilter(HTMLParser.HTMLParser, object):

    # !! perhaps this should be a user option
    # CSS can contain embedded scripts, and we don't have a
    # parser that detects them. So no css.
    allow_style_sheets = False

    rel = "rel"
    style = "style"
    stylesheet = "stylesheet"
    link = "link"

    # Tags which will be allowed, unless we're skipping tags
    default_good_tags = [
        '!doctype',
        'a',
        'abbr',
        'acronym',
        'address',
        'area',
        'b',
        'base',
        'basefont',
        'bdo', # what's this?
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
        'frame', # are frame and frameset ok?
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
        'kbd', # what's this?
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
        ]

    # Tags which trigger skipping all tags, until this tag is closed
    default_skipped_tags = [
        'javascript',
        'script',
        ]

    # Attributes within tags which will be ignored
    # See
    #     HTML Event Attributes
    #     http://www.w3schools.com/tags/ref_eventattributes.asp
    # !!!! This should be a list of whitelisted attributes.
    #      But that requires a lot more encoded html knowledge.
    default_bad_attributes = [
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
        ]

    def __init__(self, *args, **kwargs):
        self.good_tags = HtmlFirewallFilter.default_good_tags
        self.skipped_tags = HtmlFirewallFilter.default_skipped_tags
        self.bad_attributes = HtmlFirewallFilter.default_bad_attributes

        if (HtmlFirewallFilter.allow_style_sheets):
            self.good_tags.append(HtmlFirewallFilter.style);
            self.good_tags.append(HtmlFirewallFilter.link);
        else:
            self.skipped_tags.append(HtmlFirewallFilter.style);
            self.bad_attributes.append(HtmlFirewallFilter.style);

        self.skipping = None
        self.preformatted = False

        self.plain_html = ''
        self.last_start_tag = ''
        super(HtmlFirewallFilter, self).__init__(*args, **kwargs)

    def handle_starttag(self, tag, attrs):

        if tag in self.skipped_tags:
            if DEBUGGING: log.debug('start skipping tag: ' + tag)
            self.skipping = tag

        elif tag in self.good_tags:
            if DEBUGGING: log.debug('good tag: ' + tag)
            self.plain_html += '<{}'.format(tag)
            for attr, value in attrs:
                if attr in self.bad_attributes:
                    if DEBUGGING: log.debug('bad attribute, ignored: ' + attr)
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


if __name__ == "__main__":
    import doctest
    doctest.testmod()

