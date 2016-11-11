#! /usr/bin/env python

'''
    Search engine proxy main program.

    Maybe try:

        import requests
        from lxml import html

        res = requests.get('http://www.example.com')
        doc = html.fromstring(res.text)
        el = doc.cssselect('#id.class')

    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import ve
ve.activate()

import sys
IS_PY2 = sys.version_info[0] == 2

import os, random, re, sh, sys, time
from miproxy.proxy import AsyncMitmProxy, RequestInterceptorPlugin, ResponseInterceptorPlugin
from pyquery import PyQuery as pq

if IS_PY2:
    from urlparse import urljoin
else:
    from urllib.parse import urljoin

from syr.utils import chdir

port = 8369 # 'SE'arch as str(int(...))
proxies = {
  "http": "localhost:8118",
  "https": "localhost:8118",
}
cache_root_dir = '/var/local/search/cache'
encoding = 'utf8'
jquery_url = 'http://ajax.googleapis.com/ajax/libs/jquery/1.8.0/jquery.min.js'

http_eol = '\r\n'
http_separator = http_eol + http_eol

class SearchEngine(object):
    ''' Abstract class for search engines. '''

    def __init__(self, *args, **kwargs):
        if not os.path.isdir(self.cache_dir()):
            os.makedirs(self.cache_dir())

    def click_next(self):
        ''' Insert javascript to click the 'Next' button '''

        pass

    def search(self, terms):

        search_page = self.get_page('%s search' % self.engine, self.form_url)
        #print('search_page: %s' % search_page)

        form = search_page(self.search_form_selector)
        assert form
        print('form: %s' % form)
        method = form.attr('method')
        if not method:
            method = 'GET'
        print('method: %s' % method)

        action_url = form.attr('action')
        print('action_url: %s' % action_url)
        search_query_url = urljoin(self.form_url, action_url)

        data = self.get_form_data(form, terms)

        page_number = 1
        while page_number <= 5:

            # wait a while to look slightly more human
            time.sleep(random.randint(120, 300))

            page_name = '%s - page %d' % (self.results_name(terms), page_number)
            print('search_query_url: %s' % search_query_url)
            data['total_results'] = 1000
            results_page = self.get_page(page_name, search_query_url, method=method, data=data)

            # find and use the "Next" form (actually finds the last 'Next')
            # very startpage specific
            forms = results_page('form')
            for form_element in forms:
                form = pq(form_element)
                data = self.get_form_data(form, terms)
                inputs = form.find('input')
                if inputs is not None:
                    for input in inputs:
                        if syr.PY2:
                            attrs = dict(input.items())
                        else:
                            attrs = dict(list(input.items()))
                        #print('input attrs: %s' % attrs)
                        if attrs['type'] == 'submit' and attrs['value'].startswith('Next'):

                            print('found Next form: %s' % form)
                            action_url = form.attr('action')
                            print('action_url: %s' % action_url)
                            search_query_url = urljoin(search_query_url, action_url)
                            data = self.get_form_data(form, terms)
                else:
                    print('skipping form: %s' % form)

            page_number = page_number + 1

    def get_page(self, name, url, method='GET', data=None):
        ''' Get page from search engine.

            Use cache if possible, else get page from web and cache it.
            If data is not None, data is posted. '''

        cache_filename = os.path.join(self.cache_dir(), name)
        print('cache_filename: %s' % cache_filename)

        if os.path.exists(cache_filename):
            with open(cache_filename) as cache_file:
                form_html = cache_file.read().decode(encoding)
            page = pq(form_html)
            print('Using "%s" from cache' % name)

        else:
            print('getting name: %s, url: %s, method=%s, data: %s' % (name, url, method, data))
            # proxy support broken in requests as of 2012-01-02
            # https://github.com/kennethreitz/requests/issues/1074
            if data:
                page = pq(url=url, method=method, data=data) #, proxies=proxies)
                #page = pq(url=url, method=method, proxies=proxies, data=data)
            else:
                page = pq(url=url, method=method) #, proxies=proxies)
                #page = pq(url=url, method=method, proxies=proxies)
            with open(cache_filename, 'w') as cache_file:
                cache_file.write(page.html().encode(encoding))
        # print('page: %s' % page)

        return page

    def get_form_data(self, form, terms):
        data = {}
        inputs = form.find('input')
        if inputs is not None:
            for input in inputs:
                if syr.PY2:
                    attrs = dict(input.items())
                else:
                    attrs = dict(list(input.items()))
                #print('input attrs: %s' % attrs)
                if attrs['type'] == 'text':

                    # !!! we have to quote phrases
                    quoted_terms = []
                    for term in terms:
                        if ' ' in term:
                            quoted_terms.append('"%s"' % term)
                        else:
                            quoted_terms.append(term)
                    data[attrs['name']] = ' '.join(quoted_terms)

                else:
                    if 'name' in attrs and 'value' in attrs:
                        data[attrs['name']] = attrs['value']
        #print('data: %s' % data)

        return data

    def results_name(self, terms):
        return '%s: %s' % (self.engine, ' '.join (terms))

    def cache_dir(self):
        return os.path.join(cache_root_dir, self.engine)

""" earlier SearchEngine() version all in python, no js
    use with old main()
class SearchEngine(object):
    ''' Abstract class for search engines. '''

    def __init__(self, *args, **kwargs):
        if not os.path.isdir(self.cache_dir()):
            os.makedirs(self.cache_dir())

    def search(self, terms):

        search_page = self.get_page('%s search' % self.engine, self.form_url)
        #print('search_page: %s' % search_page)

        form = search_page(self.search_form_selector)
        assert form
        print('form: %s' % form)
        method = form.attr('method')
        if not method:
            method = 'GET'
        print('method: %s' % method)

        action_url = form.attr('action')
        print('action_url: %s' % action_url)
        search_query_url = urljoin(self.form_url, action_url)
        data = self.get_form_data(form, terms)

        page_number = 1
        while page_number <= 5:

            # wait a while to look slightly more human
            time.sleep(random.randint(120, 300))

            page_name = '%s - page %d' % (self.results_name(terms), page_number)
            print('search_query_url: %s' % search_query_url)
            data['total_results'] = 1000
            results_page = self.get_page(page_name, search_query_url, method=method, data=data)

            # find and use the "Next" form (actually finds the last 'Next')
            # very startpage specific
            forms = results_page('form')
            for form_element in forms:
                form = pq(form_element)
                data = self.get_form_data(form, terms)
                inputs = form.find('input')
                if inputs is not None:
                    for input in inputs:
                        if syr.PY2:
                            attrs = dict(input.items())
                        else:
                            attrs = dict(list(input.items()))
                        #print('input attrs: %s' % attrs)
                        if attrs['type'] == 'submit' and attrs['value'].startswith('Next'):

                            print('found Next form: %s' % form)
                            action_url = form.attr('action')
                            print('action_url: %s' % action_url)
                            search_query_url = urljoin(search_query_url, action_url)
                            data = self.get_form_data(form, terms)
                else:
                    print('skipping form: %s' % form)

            page_number = page_number + 1

    def get_page(self, name, url, method='GET', data=None):
        ''' Get page from search engine.

            Use cache if possible, else get page from web and cache it.
            If data is not None, data is posted. '''

        cache_filename = os.path.join(self.cache_dir(), name)
        print('cache_filename: %s' % cache_filename)

        if os.path.exists(cache_filename):
            with open(cache_filename) as cache_file:
                form_html = cache_file.read().decode(encoding)
            page = pq(form_html)
            print('Using "%s" from cache' % name)

        else:
            print('getting name: %s, url: %s, method=%s, data: %s' % (name, url, method, data))
            # proxy support broken in requests as of 2012-01-02
            # https://github.com/kennethreitz/requests/issues/1074
            if data:
                page = pq(url=url, method=method, data=data) #, proxies=proxies)
                #page = pq(url=url, method=method, proxies=proxies, data=data)
            else:
                page = pq(url=url, method=method) #, proxies=proxies)
                #page = pq(url=url, method=method, proxies=proxies)
            with open(cache_filename, 'w') as cache_file:
                cache_file.write(page.html().encode(encoding))
        # print('page: %s' % page)

        return page

    def get_form_data(self, form, terms):
        data = {}
        inputs = form.find('input')
        if inputs is not None:
            for input in inputs:
                if syr.PY2:
                    attrs = dict(input.items())
                else:
                    attrs = dict(list(input.items()))
                #print('input attrs: %s' % attrs)
                if attrs['type'] == 'text':

                    # !!! we have to quote phrases
                    quoted_terms = []
                    for term in terms:
                        if ' ' in term:
                            quoted_terms.append('"%s"' % term)
                        else:
                            quoted_terms.append(term)
                    data[attrs['name']] = ' '.join(quoted_terms)

                else:
                    if 'name' in attrs and 'value' in attrs:
                        data[attrs['name']] = attrs['value']
        #print('data: %s' % data)

        return data

    def results_name(self, terms):
        return '%s: %s' % (self.engine, ' '.join (terms))

    def cache_dir(self):
        return os.path.join(cache_root_dir, self.engine)
"""

class DuckDuckGo(SearchEngine):
    ''' DuckDuckGo search engine. '''

    def __init__(self, *args, **kwargs):
        self.engine = 'duckduckgo'
        self.form_url = 'http://duckduckgo.com/'
        # tor url
        # self.form_url = 'http://3g2upl4pq6kufc4m.onion/'
        self.search_form_selector = '#search_form_homepage'

        super(DuckDuckGo, self).__init__(*args, **kwargs)

class StartPage(SearchEngine):
    ''' StartPage just repeatedly returns the first search results page. '''

    def __init__(self, *args, **kwargs):
        self.engine = 'startpage'
        self.form_url = 'https://startpage.com/'
        self.search_form_selector = 'form'
        super(StartPage, self).__init__(*args, **kwargs)

search_engines = [
    DuckDuckGo(),
    StartPage(),
]

class SearchInterceptor(RequestInterceptorPlugin, ResponseInterceptorPlugin):

    def summary(self, data, bytes=100):
        # return repr(data:bytes) # one line
        return data[:bytes].replace(http_eol, '\r\n   ')

    def parse_response(self, response):
        ''' Return http response into (params, html) where params is a dict. '''

        header, _, html = response.partition(http_separator)

        print('<< %s' % self.summary(header)) #DEBUG
        print() #DEBUG

        lines = header.split(http_eol)

        prefix = lines[0]

        params  = {}
        for line in lines[1:]:
            if ':' in line:
                name, _, value = line.partition(':')
                name = name.strip()
                value = value.strip()
                params[name.lower()] = value

        if params.get('content-type', None) == 'text/html': #DEBUG
            if params.get('content-encoding', None) != 'gzip': #DEBUG
                print('   %s' % self.summary(html)) #DEBUG
        #print('<< %s' % self.summary(response, bytes=1000)) #DEBUG

        return prefix, params, html

    def params_to_str(self, params):
        return http_eol.join(
            '%s: %s' % (name, params[name])
            for name in params)

    def known_search_engine(request):
        ''' Return matching search engine or None. '''

        for engine in search_engines:
            pass

    def do_request(self, request):
        print('>> %s' % self.summary(request)) #DEBUG
        return request

    def do_response(self, response):

        prefix, params, html = self.parse_response(response)

        modified_html = html #DEBUG
        #print('self.params_to_str(params): %s' % self.params_to_str(params)) #DEBUG
        for name in params: #DEBUG
            print('params[%s]' % name) #DEBUG
        for name in params: #DEBUG
            print('params[%s] = %s' % (name, params[name])) #DEBUG

        modified_response = prefix + http_eol + self.params_to_str(params) + http_separator + modified_html
        return modified_response

def proxy(ca_file=None):
    ''' Use a proxy to inject javascript that does the search '''

    proxy = None
    if ca_file:
        proxy = AsyncMitmProxy(ca_file=ca_file, server_address=('', port))
    else:
        proxy = AsyncMitmProxy(server_address=('', port))
    proxy.register_interceptor(SearchInterceptor)

    try:
        proxy.serve_forever()
    except KeyboardInterrupt:
        proxy.server_close()

injected_html = '''

    <noscript>
        <div class="row well">
            <h3>Please enable javascript to automate search. </h3>
        </div>
    </noscript>

    <script src="%s"></script>
    <script type="text/javascript">
        (function($) {
            $(document).ready(function() {
                %s
            }:
        }:
    </script>
'''

def get_injected_js():
    global injected_js

    module_dir = os.path.dirname(__file__)
    module_filename = os.path.basename(__file__)
    module_basename, _, _ = module_filename.rpartition('.')
    rapydscript_filename = module_basename + '.pyj'
    javascript_filename = module_basename + '.js'

    with chdir(module_dir):
        sh.rapydscript(rapydscript_filename)
        with open(javascript_filename) as jsfile:
            injected_js = jsfile.read()

def main():
    print('HTTP proxy at 127.0.0.1:%d' % port)
    proxy()

""" old main(), python without js
def main():
    #args = sys.argv[1:]
    #DuckDuckGo().search(args)
"""

if __name__ == "__main__":

    main()

