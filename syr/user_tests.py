'''
    User test decorators.
   
    Copyright 2009-2014 GoodCrypto
    Last modified: 2014-01-16

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''



from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME

from syr.log import get_log

log = get_log()

def is_staff(u):
    return u.is_authenticated() and u.is_staff

def is_superuser(u):
    return u.is_authenticated() and u.is_superuser

def staff_required(function, redirect_field_name=REDIRECT_FIELD_NAME):
    ''' Staff required decorator.'''

    actual_decorator = user_passes_test(
        is_staff,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

    
def superuser_required(function, redirect_field_name=REDIRECT_FIELD_NAME):
    ''' Superuser required decorator.'''

    actual_decorator = user_passes_test(
        is_superuser,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


