'''
    Not django itself, but in the family.

    Copyright 2014 GoodCrypto
    Last modified: 2014-04-28

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import os.path
from django.conf import settings

def get_json_dir():
    '''Get the directory name where json output from the database are stored.'''
    
    return  os.path.join(settings.DATA_DIR, 'json')




