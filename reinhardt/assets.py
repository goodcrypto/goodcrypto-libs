'''
    Django assets for reinhardt. Inline css and js, etc.

    See http://django-assets.readthedocs.io/en/latest/

    Copyright 2015 GoodCrypto
    Last modified: 2016-09-06

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django_assets import Bundle, register


reinhardt_css = Bundle('static/css/bootstrap.min.css', 'static/css/reinhardt.bootstrap.css',
                        filters='yui_css', output='static/css/reinhardt.css')
register('reinhardt_css', reinhardt_css)

reinhardt_js = Bundle('static/js/bootstrap_js.js',
                      filters='yui_js', output='js/reinhardt_js.js')
register('reinhardt_js', reinhardt_js)

