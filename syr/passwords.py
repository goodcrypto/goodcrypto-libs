'''
   Manage passwords and serial numbers.

   Copyright 2008-2011 GoodCrypto
   Last modified: 2013-11-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import random

Min_Id_Code = 8
Max_Id_Code = 20


def create_id_code():
    '''Create an id code.'''
    
    id_code = get_serial_number(Min_Id_Code)
        
    return id_code


def get_serial_number(digits):
    '''Get a serial number, digits long.'''
    
    Random_Chars = '0123456789'
    
    serial_number = ''
    for i in range(digits):
        serial_number += random.choice(Random_Chars)
    
    return serial_number
    

def get_random_string(digits):
    '''Get a random string, digits long starting and ending with a letter.'''
    
    Random_Letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    Random_Chars = Random_Letters + '0123456789'
    
    random_string = random.choice(Random_Letters)
    if digits > 2:
        for i in range(digits - 2):
            random_string += random.choice(Random_Chars)
    random_string += random.choice(Random_Letters)
    
    return random_string
    


