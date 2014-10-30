'''
    Copyright 2014 GoodCrypto
    Last modified: 2014-01-08

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

limit = 100

i = 1
while i <= limit:
    if i % 3 == 0 and i % 5 == 0:
        print('fizzbuzz')
    elif i % 3 == 0:
        print('fizz')
    elif i % 5 == 0:
        print('buzz')
    else:
        print(i)
    i = i + 1
