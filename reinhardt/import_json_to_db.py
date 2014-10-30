#!/usr/bin/env python
'''
    Load the tables from json files.

    Copyright 2000-2014 GoodCrypto
    Last modified: 2014-09-13

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
import os, sh

from reinhardt import get_json_dir
from syr.log import get_log

log = get_log()


def import_json_files(package_dir, filenames=None):
    
    if filenames is None:
        filenames = os.listdir(get_json_dir())

    if filenames:
        for filename in filenames:
            json_path = os.path.join(get_json_dir(), filename)
            if filename.endswith('.json') and os.stat(json_path).st_size > 4:
                import_data(filename, package_dir)
    else:
        print('no json files in {}'.format(get_json_dir()))

def import_data(json_name, package_dir):

    json_path = os.path.join(get_json_dir(), json_name)
    if os.path.exists(json_path):
        print('loading %s' % json_name)
        sh.cd(package_dir)
        sh.python('manage.py', 'loaddata', json_path)
    else:
        log('%s does not exist' % json_path)

