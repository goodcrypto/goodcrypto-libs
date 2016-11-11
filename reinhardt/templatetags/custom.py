'''
    GoodCrypto custom template tags and filters

    Copyright 2010-2016 GoodCrypto
    Last modified: 2016-11-04

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

if IS_PY2:
    import urllib
else:
    import urllib.request

from django.conf import settings
from django.template import Library, Node
import django.templatetags.static

from reinhardt.html import strip_whitespace_in_html
from reinhardt.templatetags.data_img import data_img
from reinhardt.templatetags.expr import do_expr
from reinhardt.templatetags.lookup import lookup
from reinhardt.templatetags.var import do_variables
from syr.times import timedelta_to_human_readable
from syr.utils import get_absolute_url
from syr.log import get_log

log = get_log()

register = Library()

static_url_prefix = get_absolute_url(settings.STATIC_URL, settings.CONTENT_HOME_URL)

# register imported tags and filters that we want to include when we load 'custom'
# re-registering django.templatetags.static.static apparently works
register.simple_tag(django.templatetags.static.static)
register.filter('data_img', data_img)
register.filter('lookup', lookup)
register.tag('var', do_variables)

def get_title(title):
    # this is a special case
    title = settings.TOP_LEVEL_DOMAIN.title()
    if title == 'Goodcrypto':
        title = 'GoodCrypto'
        if settings.CONTENT_HOME_URL == 'http://127.0.0.1':
            title += ' Server'
    return title
register.simple_tag(get_title)

def debugging():
    return settings.DEBUG
register.simple_tag(get_title)

def transcode(url):

    '''
    Template tag to get the contents of a url.

    You can't transcode local urls because django is not re-entrant.
    Instead, in the view set a template variable with the local content.

    This code assumes a url starting with STATIC_URL is served from a different server,
    and so is ok.

    Example usage:

        {% transcode 'http://example.com' %}

    Returns:

        ... contents of http://example.com page ...

    '''

    def url_ok(url):
        ''' A url is ok if it is static or not on the local server '''

        return (
            url.startswith(static_url_prefix) or
            not url.startswith(settings.CONTENT_HOME_URL))

    url = url.strip()
    url = get_absolute_url(url, settings.CONTENT_HOME_URL)
    assert url_ok(url), ValueError('transcode can only include content from other servers')
    if IS_PY2:
        stream = urllib.urlopen(url)
    else:
        stream = urllib.request.urlopen(url)
    contents = stream.read()
    stream.close()
    return contents
register.simple_tag(transcode)


class MinWhiteSpaceNode(Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        ''' Collect the strings from all nodes into a single string, and
            remove excess white space from the entire string.'''

        return strip_whitespace_in_html(self.nodelist.render(context), mintext=True)

def minwhitespace(parser, token):
    '''
    Template tag to remove excess white space.

    The Django builtin tag "spaceless" removes whitespace between html tags.
    This tries to remove as much white space as possible without changing the
    appearance of the rendered html.

    Warning: removes repeated whitespace everywhere, such as in embedded
    javascript and between <pre> html tags.

    Example usage:

        {% minwhitespace %}
            <p>
                <a href="foo/">Foo</a>

                Bar
            </p>
        {% endminwhitespace %}

    Returns:

        <p><a href="foo/">Foo</a>Bar</p>
    '''
    nodelist = parser.parse(('endminwhitespace',))
    parser.delete_first_token()
    return MinWhiteSpaceNode(nodelist)
register.tag(minwhitespace)

class StripWhitespaceNode(Node):

    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        ''' Collect the strings from all nodes into a single string, and
            remove leading and trailing white space from the entire string.'''

        return self.nodelist.render(context).strip()

def stripwhitespace(parser, token):
    '''
    Template tag to remove leading and trailing white space.

    Example usage::

        {% stripwhitespace %}




            <p>
                <a href="foo/">Foo</a>
                Bar
            </p>



        {% endstripwhitespace %}

    Returns::
        <p>
            <a href="foo/">Foo</a>
            Bar
        </p>

    '''
    nodelist = parser.parse(('endstripwhitespace',))
    parser.delete_first_token()
    return StripWhitespaceNode(nodelist)
register.tag(stripwhitespace)

def strip(value):
    ''' Strip text filter. Uses string.strip(). '''
    return value.strip()
strip.is_safe = True
register.filter(strip)

def timedelta_in_words(value):
    ''' Timedelta to human readable template filter.'''
    return timedelta_to_human_readable(value)
timedelta_in_words.is_safe = True
register.filter(timedelta_in_words)

def blankline():
    ''' Template tag for a liquid.css blank row.

        Example usage:

            {% blankline %}

        Returns:

            <div class="block"> &nbsp; </div>
    '''

    return '<div class="block"> &nbsp; </div>'
register.simple_tag(blankline)


class TitleNode(Node):
    def __init__(self, text):
        self.text = text

    def render(self, context):
        ''' Collect the strings from all nodes into a single string, and
            format for a navpane item.'''

        context['title'] = self.text
        return '''
            {%% block title %%}%(text)s{%% endblock %%}
            {%% block titlevar %%}%(text)s{%% endblock %%}
            {%% block headline %%}%(text)s{%% endblock %%}
            ''' % {'text': self.text}

def title(parser, token):
    ''' Not working. Apparently the 'block' tag is processed before render() is called.

    Template tag to set a title.

    SEO requires that a page title match the first header.
    This tag renders the title for our template blocks.

    Example usage:

        {% title 'This title matches' %}

    Returns:

        {% block title %}This title matches{% endblock %}
        {% block titlevar %}This title matches{% endblock %}
        {% block headline %}This title matches{% endblock %}
    '''

    try:
        tag_name, text = token.split_contents()

    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires title text" % tag_name)

    return TitleNode(text)
register.tag(title)


class NavpaneItemNode(Node):
    ''' The navpane tag is no longer used. Left here as an example. '''

    def __init__(self, nodelist, highlight=False):
        self.nodelist = nodelist
        self.highlight = highlight

    def render(self, context):
        ''' Collect the strings from all nodes into a single string, and
            format for a navpane item.'''

        content = self.nodelist.render(context)

        if self.highlight:

            rendered = '''
            <div class="block">
                <div class="column span-3">
                <img src="%simages/forward.png" alt=">" align="top"/>
                </div>
                <div class="column span-20 last">
                    %s
                </div>
            </div>
            ''' % (settings.STATIC_URL, content)

        else:

            rendered = '''
            <div class="block">
                <div class="column prepend-3 span-20 last">
                    %s
                </div>
            </div>
            ''' % content

        return rendered

def navpaneitem(parser, token):
    '''
    Template tag to format a navpane item.

    Formats using liquid.css. The 'highlight' flag as a template argument prepends
    an arrow pointing to the item.

    Example usage:

        {% navpaneitem %} <a href="foo/">Foo</a> {% endnavpaneitem %}

    Returns:

        <div class="block">
            <div class="column prepend-3 span-20 last">
                <a href="foo/">Foo</a>
            </div>
        </div>

    and

        {% navpaneitem highlight %} <a href="foo/">Foo</a> {% endnavpaneitem %}

    Returns:

    <div class="block">
        <div class="column span-3">
            <img src="{{ STATIC_URL }}images/forward.png" align="top"/>
        </div>
        <div class="column span-20 last">
            <a href="foo/">Foo</a>
        </div>
    </div>

    '''

    try:
        tag_name, flag = token.split_contents()
        if flag == 'highlight':
            highlight = True
        else:
            raise template.TemplateSyntaxError(
                "%r tag only allows optional 'highlight' flag" % tag_name)

    except ValueError:
        highlight = False

    nodelist = parser.parse(('endnavpaneitem',))
    parser.delete_first_token()
    return NavpaneItemNode(nodelist, highlight=highlight)
register.tag(navpaneitem)

