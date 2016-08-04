'''
    Save a python expression as a variable. 
    
    Django's philosophy is that code is for business logix and 
    templates are for rendering. But sometimes calculations are 
    needed purely for rendering, such as in calculating css 
    opacity.
    
    If you don't calc in the template, you have to split rendering 
    between python files and templates. That's a maintenance nightmare,
    much worse than expressions in a template. 
    
    The expr tag can be misused to make Django templates much more like php,
    with no distinction between MVC model and view.

    From http://djangosnippets.org/snippets/9/:
        
        This tag can be used to calculate a python expression, and 
        save it into a template variable which you can reuse later or 
        directly output to template. So if the default django tag 
        can not be suit for your need, you can use it.
        
        How to use it
        
            {% expr "1" as var1 %}
            {% expr [0, 1, 2] as var2 %}
            {% expr _('Menu') as var3 %}
            {% expr var1 + "abc" as var4 %}
            ...
            {{ var1 }}
        
        Syntax
        
            {% expr python_expression as variable_name %}
        
        python_expression can be valid python expression, and you can 
        even use _() to translate a string. Expr tag also can use 
        context variables. 
            
    Last modified: 2012-05-08
'''
from django import template
from django.utils.translation import gettext_lazy as _
import re

register = template.Library()

class ExprNode(template.Node):
    def __init__(self, expr_string, var_name):
        self.expr_string = expr_string
        self.var_name = var_name

    def render(self, context):
        try:
            clist = list(context)
            clist.reverse()
            d = {}
            d['_'] = _
            for c in clist:
                d.update(c)
            '''            
            for c in clist:
                for item in c:
                    if isinstance(item, dict): 
                        d.update(item)
            '''
            if self.var_name:
                context[self.var_name] = eval(self.expr_string, d)
                return ''
            else:
                return str(eval(self.expr_string, d))
        except:
            raise

r_expr = re.compile(r'(.*?)\s+as\s+(\w+)', re.DOTALL)    
def do_expr(parser, token):
    try:
        tag_name, arg = token.contents.split(None, 1)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % token.contents[0]
    m = r_expr.search(arg)
    if m:
        expr_string, var_name = m.groups()
    else:
        if not arg:
            raise template.TemplateSyntaxError, "%r tag at least require one argument" % tag_name
            
        expr_string, var_name = arg, None
    return ExprNode(expr_string, var_name)
do_expr = register.tag('expr', do_expr)

