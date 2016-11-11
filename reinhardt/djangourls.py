'''
    Django url patterns.

    Copyright 2009-2015 GoodCrypto
    Last modified: 2015-07-06

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin

from reinhardt.djangoviews import sign_in, sign_out

admin.autodiscover()


urlpatterns = [

    # it's not clear when and why django redirects to 'accounts/login', but it does.
    url(r'^accounts/login/?$', sign_in),
    url(r'^accounts/logout/?$', sign_out),
    
    url(r'^sign_?in/?$', sign_in),
    url(r'^login/?$', sign_in),
    url(r'^sign_?out/?$', sign_out),        
    url(r'^logout/?$', sign_out),
    
    url(r'^admin/doc/?', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    # handle changing the current language
    url(r'^i18n/?', include('django.conf.urls.i18n')),
    
    # serve static files - hopefully this is being done better elsewhere by frontend
    url(r'^media/(.*)$', 'django.views.static.serve',
        {'document_root': '/var/local/projects/%s/media' % settings.TOP_LEVEL_DOMAIN}),
    url(r'^static/(.*)$', 'django.views.static.serve',
        {'document_root': '/var/local/projects/%s/generated_static' % settings.TOP_LEVEL_DOMAIN}),    
]

