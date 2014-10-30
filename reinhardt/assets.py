'''
    Django assets for reinhardt.

    Copyright 2014 GoodCrypto
    Last modified: 2014-01-13

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django_assets import Bundle, register

bootstrap_js = Bundle('js/jquery.js', 'js/bootstrap.js', 
                      filters='yui_js', output='js/bootstrap_js.js')
register('bootstrap_js', bootstrap_js)

admin_js = Bundle('js/jquery.ui.core.js', 'js/jquery.ui.widget.js', 
                  'js/jquery.ui.mouse.js', 'js/drag.drop.sort.js',
                  'js/jquery.ui.draggable.js', 'js/jquery.ui.droppable.js', 
                  'js/jquery.ui.sortable.js',
                   filters='yui_js', output='js/admin_js.js')
register('admin_js', admin_js)


bootstrap_css = Bundle('css/bootstrap.css', 'css/reinhardt.bootstrap.css',  'css/admin.css',
                        filters='yui_css', output='css/bootstrap_css.css')
register('bootstrap_css', bootstrap_css)


