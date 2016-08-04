'''
    Shared django settings for between projects.

    Copyright 2009-2015 GoodCrypto
    Last modified: 2015-09-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''


import os, sh

REINHARDT_PROJECT_PATH = os.path.dirname(__file__).replace('\\','/')

# probably want to include this directory in the TEMPLATES_DIR so the shared admin templates are used
REINHARDT_TEMPLATE_DIR = os.path.join(REINHARDT_PROJECT_PATH, 'templates', 'reinhardt')

APPEND_SLASH = True

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Atlantic/Reykjavik'

# If you set this to False, Django will not use timezone-aware datetimes.
# We have all our computers run on UTC so is there a need for TZ awareness?
USE_TZ = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-CA'
LANGUAGES = [
    ('en', 'English'),
]

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# reduce "database is locked" errors, especially with sqlite
DATABASE_OPTIONS = {'timeout': 30}

# django staticfiles app url prefix for static files
STATIC_URL = "/static/"

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# login urls
LOGIN_REDIRECT_URL = '/'

# do not allow any pages from our site to be wrapped in frames
X_FRAME_OPTIONS = 'DENY'

# List of template loaders that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader')

# List of processors
TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',

    'reinhardt.context_processors.custom',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.BrokenLinkEmailsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    'reinhardt.middleware.template.RequestMiddleware',
    'reinhardt.middleware.template.SettingsMiddleware',
    'reinhardt.middleware.debug.DebugMiddleware',
)


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
from syr.user import whoami
DJANGO_LOG_DIR = '/var/local/log/{}'.format(whoami())
DJANGO_LOG_FILENAME = '{}/django.log'.format(DJANGO_LOG_DIR)
try:
    if not os.path.exists(DJANGO_LOG_DIR):
        os.makedirs(DJANGO_LOG_DIR)
except Exception:
    DJANGO_LOG_FILENAME = '/tmp/django.log'
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
         'file': {
             'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': DJANGO_LOG_FILENAME,
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file', 'mail_admins'],
            'level': 'INFO',
            'propagate': True,
        },
    }
}

