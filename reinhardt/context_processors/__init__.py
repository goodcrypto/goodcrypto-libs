'''
    Context processor to set all custom template variables.

    Copyright 2009-2014 GoodCrypto    
    Last modified: 2014-03-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django.conf import settings
from django.conf import settings


from syr.browser import browser_types, is_primitive_browser
from syr.log import get_log

log = get_log()



def custom(request):
    ''' Django context processor to set all custom template variables. '''
    
    custom_context = {}
    
    custom_context['is_live'] = settings.LIVE

    custom_context.update(browser(request))
    custom_context.update(css_ok(request))
    custom_context.update(javascript_ok(request))
    #DEBUG log('request: %r' % request)
    
    return custom_context

def browser(request):
    ''' Django context processor to set 'browser' template variable.
    
        The 'browser' variable is a string containing common names of browsers
        compatible with the user's browser and platform. See
            http://web.koesbong.com/2011/01/28/python-css-browser-selector/
        
        Examples:
        
            <html class="{{ browser }}">
                ....
                {% if browser=='ie6' %}
                    ...
                {% endif %}
                ...
            </html>
        
        '''
    
    b = ' '.join(browser_types(request))
    # log('browser: %s' % b)
    return {'browser': b}

def css_ok(request):
    ''' Django context processor to set 'css_ok' template variable.
    
        The 'css_ok' variable is a boolean indicating if the user agent can properly display css.
        
        Example:
        
            {% if css_ok %}
                ...
            {% endif %}
            
        '''
    
    return {'css_ok': not is_primitive_browser(request)}

def javascript_ok(request):
    ''' Django context processor to set 'javascript_ok' template variable.
    
        The 'javascript_ok' variable is a boolean indicating if the user agent 
        can properly display javascript.
        
        Example:
        
            {% if javascript_ok %}
                ...
            {% endif %}
            
        '''
    
    return {'javascript_ok': not is_primitive_browser(request)}

