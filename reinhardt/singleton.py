'''
    Get and save a singleton record.

    Copyright 2015 GoodCrypto
    Last modified: 2015-11-29

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from traceback import format_exc

from syr.lock import locked
from syr.log import get_log

log = get_log()

def get_singleton(model, db=None):
    ''' Get a singleton record. '''

    with locked():
        try:
            if db is None:
                record = model.objects.get()
            else:
                record = model.objects.using(db).get()
        except model.MultipleObjectsReturned:
            if db is None:
                records = model.objects.all()
            else:
                records = model.objects.using(db).all()
            for r in records:
                if r.pk == 1:
                    record = r
                else:
                    r.delete()
        except model.DoesNotExist:
            # the higher level must handle this case
            raise

    return record


def save_singleton(model, record, db=None):
    ''' Save a singleton record. '''
    try:
        if db is None:
            record.save()
        else:
            record.save(using=db)

        # get the singleton again to insure there's only 1 record
        get_singleton(model, db=db)
    except:
        log('tried to save {}'.format(model))
        log(format_exc())
        raise

