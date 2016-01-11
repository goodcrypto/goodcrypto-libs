'''
    Template middleware.
            
    Copyright 2011-2014 GoodCrypto
    Last modified: 2014-03-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django.conf import settings
from syr.log import get_log

log = get_log()

def set_context(response, key, value):
    # is this necessary, or can we just e.g. "response.context_data['request'] = request"?
    try:
        # TemplateResponse
        context = response.context
    except AttributeError:
        # SimpleTemplateResponse
        context = response.context_data
    if context == None:
        context = {}
        
    if key not in context:
        context[key] = value

class RequestMiddleware(object):
    ''' Add the request to the template context. '''
    
    def process_template_response(self, request, response):
            
        set_context(response, 'request', request)
        return response
        
class SettingsMiddleware(object):
    ''' Add the settings to the template context. '''
    
    def process_template_response(self, request, response):
            
        set_context(response, 'settings', settings)
        return response
