'''
    Create variables within templates

    Variables are set at render time. They are not available earlier,
    such as when {% block %} is evaluated.

    From http://djangosnippets.org/snippets/829/:

        Here is a Django template tag that allows you to create complex
        variables specified in JSON format within a template.

        It enables you to do stuff like:

        {% var as person %}
        {
             "firstName": "John",
             "lastName": "Smith",
              "address": {
                  "streetAddress": "21 2nd Street",
                  "city": "New York",
                  "state": "NY",
                  "postalCode": 10021
              },
              "phoneNumbers": [
                  "212 555-1234",
                  "646 555-4567"
              ]
          }
         {% endvar %}

         <p>{{person.firstName}}, </br>
            {{person.address.postalCode}}, </br>
            {{person.phoneNumbers.1}}
         </p>

        This tag also enables me to do dynamic CSS using as follows:

        # urlpatters
        urlpatterns = patterns('',
            (r'^css/(?P<path>.*\.css)$', 'get_css'),
        )

        #views
        def get_css(request, path):
            return render_to_response('css/%s' % path, {},
                mimetype="text/css; charset=utf-8")

        # dynamic css within in /path/to/app/templates/css'
        {% load var %}
        {% var as col %}
        {
            "darkbg": "#999",
            "lightbg": "#666"
        }
        {% endvar %}

        {% var as dim %}
        {
            "thinmargin": "2em",
            "thickmargin": "10em"
        }
        {% endvar %}

        body {
            background: {{col.darkbg}};
            margin: {{dim.thinmargin}};
        }


    Last modified: 2016-05-30
'''

from django import template
import json, re

import syr.log
log = syr.log.get_log()

register = template.Library()

class VariablesNode(template.Node):
    def __init__(self, nodelist, var_name):
        self.nodelist = nodelist
        self.var_name = var_name
        log.debug('var_name: {}'.format(var_name))

    def render(self, context):
        source = self.nodelist.render(context)
        if source.strip().startswith('{'):
            value = json.loads(source)
            #log.debug('value from json: {}'.format(value))
        else:
            value = source
            #log.debug('value from source: {}'.format(value))
        log.debug('value type: {}'.format(type(value)))
        context[self.var_name] = value
        return ''

@register.tag(name='var')
def do_variables(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        msg = '"%s" tag requires arguments' % token.contents.split()[0]
        log.debug(msg)
        raise template.TemplateSyntaxError(msg)
    log.debug('arg: {}'.format(arg))
    m = re.search(r'as (\w+)', arg)
    if m:
        var_name, = m.groups()
        log.debug('var_name arg: {}'.format(var_name))
    else:
        msg = '"%s" tag had invalid arguments' % tag_name
        log.debug(msg)
        raise template.TemplateSyntaxError(msg)

    nodelist = parser.parse(('endvar',))
    parser.delete_first_token()
    return VariablesNode(nodelist, var_name)

