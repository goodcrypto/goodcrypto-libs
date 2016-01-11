'''
    Serialize objects.
    
    Abstract and encapsulate object serialization.
    There are many serialiation implementations with tradeoffs.
    This module provides a common api and a default implementation.

    Implementators: Implementations that are dependent on nonstandard 
    imports should be enclosed in try/except. The last 
        "DefaultSerializer = " 
    wins. Default serializers should be set in order of increasing 
    preference. 
    
    Copyright 2014 GoodCrypto.
    Last modified: 2015-01-26

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
    
    >>> # test the default serializer
    >>> # use dictify to create a common format so one set of 
    >>> # tests works with any serializer
    >>> from syr.serialize import serializer
    
    >>> filename = '/tmp/syr.serialize.test'
    
    >>> # test class instance
    >>> # jsonpickle can't decode a class defined in the doctest
    >>> # so this test class is globally defined in this module
    >>> t1 = _Test()
    >>> dictify(t1)
    {'a': 1, 'c': u'\u04d2', 'b': 'a', 'd': {'y': 'b', 'x': 2}}
    >>> encoded = serializer.encode(t1)
    >>> new_t1 = serializer.decode(encoded)
    >>> new_t1_d = dictify(serializer.decode(encoded))
    >>> new_t1_d
    {'a': 1, 'c': u'\u04d2', 'b': 'a', 'd': {'y': 'b', 'x': 2}}
    >>> serializer.tofile(filename, t1)
    >>> new_t1 = serializer.fromfile(filename)
    >>> new_t1_d = dictify(new_t1_d)
    >>> new_t1_d
    {'a': 1, 'c': u'\u04d2', 'b': 'a', 'd': {'y': 'b', 'x': 2}}
    
    >>> # test datetime
    >>> t2 = {'datetime': datetime.datetime(1, 2, 3, 4, 5)}
    >>> dictify(t2)
    {'datetime': {'hour': 4, 'month': 2, 'second': 0, 'microsecond': 0, 'year': 1, 'tzinfo': None, 'day': 3, 'minute': 5}}
    >>> encoded = serializer.encode(t2)
    >>> print encoded
    {
        "datetime": {
            "day": 3, 
            "hour": 4, 
            "microsecond": 0, 
            "minute": 5, 
            "month": 2, 
            "second": 0, 
            "tzinfo": null, 
            "year": 1
        }
    }
    
    >>> new_t2 = serializer.decode(encoded)
    >>> new_t2
    {u'datetime': {u'hour': 4, u'month': 2, u'second': 0, u'microsecond': 0, u'year': 1, u'tzinfo': None, u'day': 3, u'minute': 5}}
    
    >>> new_t2_d = dictify(serializer.decode(encoded))
    >>> new_t2_d
    {'datetime': {'hour': 4, 'month': 2, 'second': 0, 'microsecond': 0, 'year': 1, 'tzinfo': None, 'day': 3, 'minute': 5}}
    >>> serializer.tofile(filename, t2)
    >>> new_t2 = serializer.fromfile(filename)
    >>> new_t2
    {u'datetime': {u'hour': 4, u'month': 2, u'second': 0, u'microsecond': 0, u'year': 1, u'tzinfo': None, u'day': 3, u'minute': 5}}
    
    >>> dictify(new_t2)
    {'datetime': {'hour': 4, 'month': 2, 'second': 0, 'microsecond': 0, 'year': 1, 'tzinfo': None, 'day': 3, 'minute': 5}}


    Copyright 2013 GoodCrypto
    Last modified: 2014-01-08
'''

import datetime, os, pickle, tempfile
from syr.dict import dictify, DictObject
from syr.format import pretty
from syr.log import get_log
from syr.times import elapsed_time
from syr.utils import last_exception, NotImplementedException

log = get_log()
                        
def json_date_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat() 
    else:
        return obj
    
# jsonpickle can't decode a class defined in the doctest
class _Test(object):
    a = 1
    b = 'a'
    c = unichr(1234)
    
    def __init__(self):
        self.d = {'x': 2, 'y': 'b'}

class AbstractSerializer(object):
    ''' Serializer abstract class. 
    
        Subclasses  must implement at least encode() and decode(). '''
    
    def encode(self, obj):
        ''' Encode object to serialized form '''
        
        raise NotImplementedException
        
    def decode(self, encoded):
        ''' Decode object from serialized form '''
        
        raise NotImplementedException
        
    def read(self, openfile):
        ''' Read object from open file.
        
            Use fromfile() to deserialize from a named file. '''
        
        return self.decode(openfile.read())
        
    def write(self, openfile, obj):
        ''' Write object to open file.
        
            Use tofile() to serialize to a named file.  '''
        
        openfile.write(self.encode(obj))
        
    def fromfile(self, filename):
        ''' Read object from file.
        
            Use read() to deserialize from an open file. '''
        
        with open(filename, 'rt') as infile:
            decoded = self.read(infile)
        return decoded
        
    def tofile(self, filename, obj):
        ''' Write object to file.
        
            Use write() to serialize to an open file.  '''
        
        with open(filename, 'wt') as outfile:
            self.write(outfile, obj)
        
class BuiltinPickle(AbstractSerializer):
    ''' Builtin pickle serializer
        
        >>> # Test datetime as value in dict
        >>> from datetime import datetime
        >>> d = {'12345': datetime(1, 2, 3, 4, 5)}
        >>> ed = pickle.dumps(d)
        >>> dd = pickle.loads(ed)
        >>> dd
        {'12345': datetime.datetime(1, 2, 3, 4, 5)}
    '''
    
    def encode(self, obj):
        ''' Encode object to serialized form '''
        
        with elapsed_time() as et:
            encoded = pickle.dumps(obj)
        log('BuiltinPickle.encode elapsed time: %s' % et.timedelta())
        return encoded
        
        
    def decode(self, encoded):
        ''' Decode object from serialized form '''
        
        log('decoding with BuiltinPickle')
        with elapsed_time() as et:
            decoded = pickle.loads(encoded)
        log('BuiltinPickle decode elapsed time: %s' % et.timedelta())
        return decoded
        
DefaultSerializer = BuiltinPickle
          
try:
    import jsonpickle
 
except ImportError:
    pass

else:
    class JsonPickle(AbstractSerializer):
        ''' jsonpickle serializer 
        
            jsonpickle can't decode a class defined in a doctest.
            
            >>> # Test datetime as value in dict
            >>> from datetime import datetime
            >>> d = {'12345': datetime(1, 2, 3, 4, 5)}
            >>> ed = jsonpickle.encode(d)
            >>> dd = jsonpickle.decode(ed)
            >>> dd
            {'12345': datetime.datetime(1, 2, 3, 4, 5)}
        '''
        
        def encode(self, obj):
            ''' Encode object to serialized form '''
            
            with elapsed_time() as et:
                encoded = jsonpickle.encode(obj)
            log('JsonPickle.encode elapsed time: %s' % et.timedelta())
            return encoded
            
            
        def decode(self, encoded):
            ''' Decode object from serialized form '''
            
            log('decoding with JsonPickle')
            with elapsed_time() as et:
                decoded = jsonpickle.decode(encoded)
            log('JsonPickle decode elapsed time: %s' % et.timedelta())
            return decoded
            
    DefaultSerializer = JsonPickle
  
try:
    from zodbpickle import pickle as zpickle
 
except ImportError:
    pass

else:
    class ZodbPickle(AbstractSerializer):
        ''' zodbpickle serializer
            
            >>> # Test datetime as value in dict
            >>> from datetime import datetime
            >>> d = {'12345': datetime(1, 2, 3, 4, 5)}
            >>> ed = jsonpickle.encode(d)
            >>> dd = jsonpickle.decode(ed)
            >>> dd
            {'12345': datetime.datetime(1, 2, 3, 4, 5)}
        '''
        
        def encode(self, obj):
            ''' Encode object to serialized form '''
            
            with elapsed_time() as et:
                encoded = zpickle.dumps(obj)
            log('ZodbPickle.encode elapsed time: %s' % et.timedelta())
            return encoded
            
            
        def decode(self, encoded):
            ''' Decode object from serialized form '''
            
            log('decoding with ZodbPickle')
            with elapsed_time() as et:
                decoded = zpickle.loads(encoded)
            log('ZodbPickle decode elapsed time: %s' % et.timedelta())
            return decoded
            
    DefaultSerializer = ZodbPickle
                
try:
    import jspickle
 
except ImportError:
    pass

else:
    class JsPickle(AbstractSerializer):
        ''' jspickle serializer 
        
            Gets error "A dict with references to itself is not JSON encodable".
        '''
        
        def encode(self, obj):
            ''' Encode object to serialized form '''
            
            with elapsed_time() as et:
                encoded = jspickle.encode(obj)
            log('JsPickle.encode elapsed time: %s' % et.timedelta())
            return encoded
            
            
        def decode(self, encoded):
            ''' Decode object from serialized form '''
            
            log('decoding with JsPickle')
            with elapsed_time() as et:
                decoded = jspickle.decode(encoded)
            log('JsPickle decode elapsed time: %s' % et.timedelta())
            return decoded
            
    DefaultSerializer = JsPickle
  
class Dictify(AbstractSerializer):
    ''' syr.dict.dictify serializer '''
    
    def encode(self, obj, json_compatible=False):
        ''' Encode object to serialized form '''
        
        #log('Dictify.encode obj: %s' % obj)
        with elapsed_time() as et:
            encoded = dictify(obj, deep=True, json_compatible=json_compatible)
            #log('Dictify.encode encoded: %s' % encoded)
        log('Dictify.encode elapsed time: %s' % et.timedelta())
        with tempfile.NamedTemporaryFile( #DEBUG
            prefix='dictify_serializer.', suffix='.dict', delete=False #DEBUG
            ) as debug_store: #DEBUG
            pretty_encoded = pretty(encoded, indent=4)
            # log('Dictify.encode pretty_encoded: %s' % pretty_encoded)
            debug_store.write(pretty_encoded) #DEBUG
            os.chmod(debug_store.name, 0664) #DEBUG
            log('Dictify.encode saved to %s' % debug_store.name) #DEBUG
        return encoded
        
        
    def decode(self, encoded):
        ''' Decode object from serialized form '''
        
        log('decoding with Dictify')
        with elapsed_time() as et:
            decoded = eval(encoded)
        log('Dictify.decode elapsed time: %s' % et.timedelta())
        return decoded
        
    def write(self, openfile, obj):
        ''' Write object to open file.
        
            Use tofile() to serialize to a named file.  '''
        
        encoded = self.encode(obj)
        openfile.write(pretty(encoded, indent=4))
        
DefaultSerializer = Dictify

try:
    import json
    from syr.format import pretty_json
 
except ImportError:
    pass

else:
    class Json(AbstractSerializer):
        ''' json serializer. 
        
            This serializer uses the json module, which can only serialize 
            data types in the current scope. E.g. if you want to serialize 
            datetime, import datetime in this module. '''
        
        class ExtendedEncoder(json.JSONEncoder):
            ''' Default to json.JSONEncoder with a fallback to dictify(obj). '''
            
            def default(self, obj):
                ''' Encode types not included in the standard json module. '''
                
                try:
                    result = json.JSONEncoder.default(self, obj)
                except:
                    log('could not json encode %s' % type(obj))
                    result = json.JSONEncoder.default(self, dictify(obj))
                        
                return result

        
        def encode(self, obj):
            ''' Encode object to serialized form '''
            
            with elapsed_time() as et:
                json_object = json.dumps(obj, cls=Json.ExtendedEncoder)
                encoded = pretty_json(json_object)
            log('Json.encode elapsed time: %s' % et.timedelta())
            return encoded
            
            
        def write(self, openfile, obj):
            ''' Write object to open file.
            
                Use tofile() to serialize to a named file.  '''
            
            json.dump(obj, openfile)
            
        def decode(self, encoded):
            ''' Decode object from serialized form '''
            
            log('decoding with Json')
            with elapsed_time() as et:
                #decoded = DictObject(json.loads(encoded))
                decoded = json.loads(encoded)
            log('Json decode elapsed time: %s' % et.timedelta())
            return decoded

    DefaultSerializer = Json
  
class JsonWithDictify(Json):
    ''' Hybrid serializer using syr.dict.dictify and json. 
    
        Our dictify module can serialize more types than json.
        JSON is a better transport and storage format than repr(dict). 
        So we use json to serialize the dict from dictify. '''
    
    import sys
    if sys.version < '2.6':
        def decode(self, encoded):
            ''' Decode object from serialized form '''
            
            log('decoding with JsonWithDictify')
            with elapsed_time() as et:
                # first decode using json
                json_decoded = json.loads(encoded)
                # next, turn the names in the dictionary into strings instead of unicode
                decoded = Dictify().encode(json_decoded, json_compatible=True)
            log('JsonWithDictify.decode elapsed time: %s' % et.timedelta())
            return decoded


    def encode(self, obj):
        ''' Encode object to serialized form '''
        
        with elapsed_time() as et:
            dictified = Dictify().encode(obj, json_compatible=True)
            # log('JsonWithDictify.encode dictified: %s' % dictified)
            encoded = Json().encode(dictified)
            # log('JsonWithDictify.encode encoded: %s' % encoded)
        log('JsonWithDictify.encode elapsed time: %s' % et.timedelta())
        return encoded
    
    def write(self, openfile, obj):
        ''' Write object to open file.  '''
        
        encoded = self.encode(obj)
        # log('JsonWithDictify.write encoded: %s' % encoded)
        openfile.write(encoded)
            
        
        
DefaultSerializer = JsonWithDictify

serializer = DefaultSerializer()
log('serializer is %s' % type(serializer))

if __name__ == "__main__":
    import doctest
    doctest.testmod()
