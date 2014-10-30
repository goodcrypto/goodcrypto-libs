'''
    Text formating.
    
    Because this module uses some modules that use this one,
    imports that are not from standard libs should not be
    at global scope. Put the import where it's used.
   
    Copyright 2008-2013 GoodCrypto
    Last modified: 2014-01-08

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import datetime, json, pprint
from traceback import format_exc


# try to import an html prettyprinter
try:
    from BeautifulSoup import BeautifulSoup
    html_prettifier = 'beautifulsoup'
except:
    try:
        from tidylib import tidy_document
        html_prettifier = 'tidy'
    except:
        html_prettifier = None

# delayed import of log so syr.log can use this module
_log = None
def log(message):
    global _log
    if not _log:
        from syr.log import get_log
        _log = get_log()
    _log(message)

def pretty(object, indent=0, base_indent=0):
    ''' Prettyprint 'pprint' replacement. 
        
        Places every dictionary item on a separate line in key order.
        Formats nested dictionaries.
        
        For long lists, places every item on a separate line.
    
        'indent' is the increment for each indentation level, and defaults to 0.
        'base_indent' is the current indentation, and defaults to 0.
    
        >>> data = {
        ...     'a': 1, 
        ...     'c': 2, 
        ...     'b': 'hi', 
        ...     'x': {1: 'a', 2: 'b'}, 
        ...     'e': datetime.timedelta(9, 11045), 
        ...     'd': 'ho', 
        ...     'g': datetime.datetime(2000, 1, 2, 3, 4, 5, 6), 
        ...     'f': datetime.date(2000, 1, 2), 
        ...     'h': datetime.time(1, 2, 3, 4),
        ...     }
        >>> data['l'] = [data['a'], data['b'], data['c'], data['d'], data['e'], data['f'], data['g'], data['h'], data['x']]
        >>> p = pretty(
        ...     data,
        ...     indent=4
        ...     )
        >>> print p
        {
            'a': 1,
            'b': 'hi',
            'c': 2,
            'd': 'ho',
            'e': datetime.timedelta(9, 11045),
            'f': datetime.date(2000, 1, 2),
            'g': datetime.datetime(2000, 1, 2, 3, 4, 5, 6),
            'h': datetime.time(1, 2, 3, 4),
            'l': [
                1,
                'hi',
                2,
                'ho',
                datetime.timedelta(9, 11045),
                datetime.date(2000, 1, 2),
                datetime.datetime(2000, 1, 2, 3, 4, 5, 6),
                datetime.time(1, 2, 3, 4),
                {
                    1: 'a',
                    2: 'b',
                },
            ],
            'x': {
                1: 'a',
                2: 'b',
            },
        }
        
        >>> p1 = eval(p)
        >>> print pretty(p1, indent=4)
        {
            'a': 1,
            'b': 'hi',
            'c': 2,
            'd': 'ho',
            'e': datetime.timedelta(9, 11045),
            'f': datetime.date(2000, 1, 2),
            'g': datetime.datetime(2000, 1, 2, 3, 4, 5, 6),
            'h': datetime.time(1, 2, 3, 4),
            'l': [
                1,
                'hi',
                2,
                'ho',
                datetime.timedelta(9, 11045),
                datetime.date(2000, 1, 2),
                datetime.datetime(2000, 1, 2, 3, 4, 5, 6),
                datetime.time(1, 2, 3, 4),
                {
                    1: 'a',
                    2: 'b',
                },
            ],
            'x': {
                1: 'a',
                2: 'b',
            },
        }
        
    '''
    
    max_list_width = 60

    if isinstance(object, dict):
        p = '{\n'
        base_indent += indent
        try:
            keys = sorted(object.keys())
        except:
            keys = object.keys()
        for key in keys:
            p += (' ' * base_indent) + repr(key) + ': '
            value = object[key]
            p += pretty(value, indent=indent, base_indent=base_indent)
            p += ',\n'
        base_indent -= indent
        p += (' ' * base_indent) + '}'
        
    elif isinstance(object, list):
        p = '[\n'
        base_indent += indent
        for item in object:
            p += (' ' * base_indent) + pretty(item, indent=indent, base_indent=base_indent)
            p += ',\n'
        base_indent -= indent
        p += (' ' * base_indent) + ']'
        # put short lists on one line
        if len(p) < max_list_width:
            p = p.replace('\n ', ' ')
            p = p.replace('  ', ' ')

    else:
        pp = pprint.PrettyPrinter(indent=indent)
        try:
            p = pp.pformat(object)
        except:
            try:
                log('unable to pretty print object: %r' % type(object))
                p = repr(object)
                log('object len: %d' % len(str(p)))
            except:
                log(format_exc())
                from syr.utils import last_exception_only
                p = 'syr.format.pretty ERROR: %s' % last_exception_only()
        
    return p

def add_commas(number):
    ''' Add commas to a number,
    
        >>> print add_commas(0)
        0
        >>> print add_commas(1)
        1
        >>> print add_commas(1234)
        1,234
        >>> print add_commas(1234567)
        1,234,567
        >>> print add_commas(0.0)
        0.0
        >>> print add_commas(0.1234)
        0.1234
        >>> print add_commas(1.1234)
        1.1234
        >>> print add_commas(1234.1234)
        1,234.1234
        >>> print add_commas(1234567.1234)
        1,234,567.1234
    '''

    if '.' in str(number):
        (integer, decimal) = str(number).split('.')
    else:
        integer = str(number)
        decimal = ''

    formattedNumber = ''
    while len(integer) > 3:
        formattedNumber = "," + integer[-3:] + formattedNumber
        integer = integer[:-3]
    formattedNumber = integer + formattedNumber

    if decimal:
        formattedNumber += '.' + decimal

    return formattedNumber

def s_if_plural(number):
    ''' Return an empty string if the number is one, else return the letter \'s\'.
        This is used to form standard plural nouns.
        
        >>> print 'house' + s_if_plural(0)
        houses
        >>> print 'house' + s_if_plural(1)
        house
        >>> print 'house' + s_if_plural(2)
        houses
        
    '''
        
    if number == 1:
        result = ''
    else:
        result = 's'
    return result

def replace_angle_brackets(s):
    ''' Replace '<' with '&lt;' and '>' with '&gt;'.
    
        This allows html to display correctly when embedded in html. '''
    
    s = s.replace('<', '&lt;')
    s = s.replace('>', '&gt;')
    return s

def camel_back(s):
    ''' Combine words into a string with no spaces and every word capitalized.
        Already capitalized letters after the first letter are preserved. 
    
        >>> camel_back('wikipedia article name')
        'WikipediaArticleName'
        >>> camel_back('WikiPedia CamelBack')
        'WikiPediaCamelBack'
            
        '''
    
    words = s.split(' ');
    camel_back_words = []
    for word in words:
        # the word may itself be camel back, or at least have some capitalized letters
        camel_back_words.append(word[:1].capitalize() + word[1:])
    return ''.join(camel_back_words)
    
def pretty_html(html):
    ''' Prettyprint html.
    
        Requires BeautifulSoup or tidylib. 
    

        >>> print(pretty_html('<head><title>Test HTML</title></head><body>The test text</body>'))
        <head>
         <title>
          Test HTML
         </title>
        </head>
        <body>
         The test text
        </body>
    '''
    
    if html_prettifier == 'beautifulsoup':
        try:
            html = BeautifulSoup(html).prettify()
        except:
            log(format_exc())
        
    elif html_prettifier == 'tidy':
        
        # tidy_document() does not work with framesets
        if not '<frameset' in html:
            
            pretty_html, errors = tidy_document(html)
            if errors:
                log('tidy error: %r' % errors)
            elif not pretty_html:
                log('tidy returned an empty page')
            else:
                html = pretty_html
            
    return html
    
def pretty_json(json_string, indent=4):
    ''' Prettyprint json string.
    
        >>> json_string = '{"b": 2, "a": 1, "d": {"y": "b", "x": "a"}, "c": 3}'
        >>> print(pretty_json(json_string))
        {
            "a": 1, 
            "b": 2, 
            "c": 3, 
            "d": {
                "x": "a", 
                "y": "b"
            }
        }

    '''
    
    decoded = json.loads(json_string)
    encoded = json.dumps(decoded, indent=indent, sort_keys=True)
    return encoded
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
