'''
    Django url patterns.

    Copyright 2009-2013 GoodCrypto
    Last modified: 2013-11-21

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django.conf import settings
from django.conf.urls import *
from django.contrib import admin

from reinhardt.djangoviews import sign_in, sign_out

admin.autodiscover()


urlpatterns = patterns('',

    # it's not clear when and why django redirects to 'accounts/login', but it does.
    (r'^accounts/login/?$', sign_in),
    (r'^accounts/logout/?$', sign_out),
    
    (r'^sign_?in/?$', sign_in),
    (r'^login/?$', sign_in),
    (r'^sign_?out/?$', sign_out),        
    (r'^logout/?$', sign_out),
    
    (r'^admin/doc/?', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),

    # handle changing the current language
    (r'^i18n/?', include('django.conf.urls.i18n')),
    
    # serve static files - hopefully this is being done better elsewhere by frontend
    url(r'^media/(.*)$', 'django.views.static.serve',
        {'document_root': '/var/local/projects/%s/media' % settings.TOP_LEVEL_DOMAIN}),
    url(r'^static/(.*)$', 'django.views.static.serve',
        {'document_root': '/var/local/projects/%s/generated_static' % settings.TOP_LEVEL_DOMAIN}),    
)

