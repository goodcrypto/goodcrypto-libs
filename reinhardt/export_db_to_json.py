'''
    Export database tables to json files.

    Copyrght 2000-2015 GoodCrypto
    Last modified: 2015-05-03
'''

import os, re, sys, tarfile
from traceback import format_exc

from django.conf import settings
from django.core import serializers
from django.db.models.loading import get_models

import django
django.setup()

from reinhardt import get_json_dir
from syr import text_file
from syr.log import get_log
from syr.fs import match_parent_owner


log = get_log()


def reloadable_models():
    ''' Returns reloadable models. 
    
        Returns a list of tuples, (app_name, model, table_name). '''
    
    models = []
    for model in get_models():
        app_name = model._meta.app_label.lower()
        table_name = model._meta.object_name.lower()
        
        if app_name == 'admin' or app_name == 'contenttypes' or app_name == 'sessions':
            pass
        elif app_name == 'auth' and (table_name == 'message' or table_name == 'permission'):
            pass
        else:
            models.append((app_name, model, table_name,))

    log('reloadable models: {}'.format(models))

    return models


def non_django_models():
    ''' Returns all non django models. 
    
        Returns a list of tuples, (app_name, model, table_name). '''
    
    models = []
    for model in get_models():
        app_name = model._meta.app_label.lower()
        table_name = model._meta.object_name.lower()
        
        model_string = str(model)
        m = re.match("<class '(.*?)'>", model_string)
        if m:
            model_name = m.group(1)
        else:
            model_name = None

        if (model_name and model_name.startswith('django')):
            pass
        else:
            models.append((app_name, model, table_name,))

    log('non-django models: {}'.format(models))

    return models


def export_reloadable_models():
    '''Export the models which can be reloaded to create the database.
    
       The admin, auth.message, auth.permission, contenttypes, and sessions
       models and tables cause challenges when reloaded.
       
       The auth.group is stripped of permissions as the permissions are non importable.
    '''

    def strip_group_permissions():
        '''Strip the permissions from the group table.
    
           The permissions must be manually recreated when you reload 
           the database from scratch.'''
    
        try:
            new_lines = []
            permissions_started = False
            
            fullname = os.path.join(get_json_dir(), get_json_filename('auth', 'group'))
            lines = text_file.read(fullname)
            for line in lines:
                if line.find('"permissions": [') >= 0:
                    permissions_started = True
                    new_lines.append(line)
                elif line.find(']') >= 0:
                    permissions_started = False
                    new_lines.append(line)
                elif not permissions_started:
                    new_lines.append(line)
                    
            text_file.write(fullname, new_lines)
            log('group permissions stripped')
    
        except:
            log(format_exc())
            print(format_exc())
  

    clean_json_files()
    
    ok = True
    if export_models(reloadable_models()):
        log('all models exported ok')
    else:
        log("one or more models didn't export")
    strip_group_permissions()

    return ok


def export_non_django_models():
    '''Export the non-djanog models.'''

    django.setup()

    clean_json_files()
    
    return export_models(non_django_models())


def clean_json_files():
    '''Erase all the json files.'''
    
    create_json_dir()
        
    filenames = os.listdir(get_json_dir())
    if filenames:
        for filename in filenames:
            if filename.endswith('.json'):
                os.remove(os.path.join(get_json_dir(), filename))
        

def export_models(models):
    '''Export the models to json files.'''

    ok = True
    if models:
        for app_name, model, table_name in models:
            if not export_data(model, app_name, table_name):
                ok = False
                log('unable to dump %r:%r' % (app_name, table_name))
    else:
        ok = False
        log('no models defined')
        
    return ok


def export_data(model, app_name, table_name):
    
    ok = True
    
    try:
        create_json_dir()
        
        data = serializers.serialize('json', model.objects.all(), indent=4)
        log('exported %r from %r' % (len(model.objects.all()), table_name))
        
        full_path = os.path.join(get_json_dir(), get_json_filename(app_name, table_name))
        out = open(full_path, 'w')
        out.write(data)
        out.close()
        
        match_parent_owner(full_path)
        os.chmod(full_path, 0660)
        
        log('finished exporting %s' % table_name)
        
    except:
        ok = False
        log('unable to export {} {} {}'.format(model, app_name, table_name))

    return ok
    

def compress_files(compress_name=settings.TOP_LEVEL_DOMAIN):

    ok = True
    
    try:
        '''
        # a little magic knowledge to keep good crypto's databases separate
        if compress_name.lower() == 'goodcrypto':
            database_name = settings.DATABASES['default']['NAME']
            if database_name.lower().endswith('server.sqlite'):
                compress_name = '{}-server'.format(settings.TOP_LEVEL_DOMAIN)
        '''
        compressed_filename = os.path.join(get_json_dir(), '{}.json.tgz'.format(compress_name))
        log('started to compress json files to %s' % compressed_filename)
        tar = tarfile.open(compressed_filename, 'w:gz')
        
        # compress all of the json files, without their directory structure
        file_list = os.listdir(get_json_dir())
        for filename in file_list:
            if filename.endswith('.json'):
                full_path = os.path.join(get_json_dir(), filename)
                tar.add(full_path, arcname=filename, recursive=False)
        tar.close()
        match_parent_owner(compressed_filename)
        os.chmod(compressed_filename, 0660)
        
        ok = True
        
        # verify the files were compressed successfully
        tar = tarfile.open(compressed_filename, 'r:gz')
        for tarinfo in tar:
            
            try:
                full_path = os.path.join(get_json_dir(), tarinfo.name)

                statinfo = os.stat(full_path)
                
                if statinfo.st_size != tarinfo.size:
                    ok = False
                    log(full_path + ' size does not match tar file')
                else:
                    os.remove(full_path)
            except:
                ok = False
                log(format_exc())
        tar.close()

        log('finished compressing json files ok: %r' % ok)
        
        if ok and file_list is not None:
            # remove uncompressed files
            for filename in file_list:
                if filename.endswith('.json'):
                    try:
                        os.remove(os.path.join(get_json_dir(), filename))
                    except:
                        pass
            log('finished deleting json files')
        
    except:
        ok = False
        log(format_exc())
        
    return ok
        
def get_json_filename(app_name, table_name):
    
    return '%s.%s.json' % (app_name, table_name)
    
def create_json_dir():
    dir = get_json_dir()
    if not os.path.exists(dir):
        os.mkdir(dir)
        match_parent_owner(get_json_dir())
        os.chmod(get_json_dir(), 0770)


def main(arg='reloadable'):

    django.setup()
    if arg == 'reloadable':
        ok = export_reloadable_models()
        if ok:
            compress_files()
    elif arg == 'non-django':
        ok = export_non_django_models()
        
    return ok


if __name__ == '__main__':
    if len(sys.argv) > 1:
        arg = sys.argv[1]
    else:
        arg = 'reloadable'
    ok = main(arg=arg)
    code = int(not ok)        
    sys.exit(code)
