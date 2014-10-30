'''
    Django views

    Copyright 2012-2014 GoodCrypto
    Last modified: 2014-03-03

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from traceback import format_exc

from django.contrib.auth.views import login, logout
from syr.log import get_log

log = get_log()


def sign_in(request):

    return login(request, template_name='admin/sign_in.html')

def sign_out(request):

    Sign_Out_Page = 'admin/signed_out.html'
    
    return logout(request, template_name=Sign_Out_Page)

