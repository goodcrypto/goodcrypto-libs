'''
    Coroutine classes and utilties.
    
    Simple replacements for overly complex threading, generators, Queues, etc.
    
    See the doctests for examples.
    
    These functions and classes, especially Pump and Coroutine, hide 
    the obscure python linkages between iterables and generators. In 
    most cases you don't need threading at all. They also add optional 
    common functionality such as filters and one time processing. Very 
    memory efficient implementation.
    
    Some functions are from:
      * Dave Beasley's Generator Tricks for System Programers
        http://www.dabeaz.com/generators-uk/
      * Pipe Fitting with Python Generators
        http://paddy3118.blogspot.com/2009/05/pipe-fitting-with-python-generators.html

    Portions Copyright 2012-2015 GoodCrypto
    Last modified: 2015-01-04

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from itertools import imap
from Queue import Queue

from syr.python import object_name
from syr.utils import last_exception, last_exception_only, synchronized
from syr.iter import iter
from syr.log import get_log
        
# log in non-standard dir because of concurrency issues
log = get_log('/tmp/coroutine.log')
debug = True

def consumer(func):    
    ''' Co-routine consumer decorator.
    
        Thanks to Dave Beasley. '''

    def start(*args,**kwargs):
        c = func(*args,**kwargs)
        c.next()
        return c
    return start
    
def pipe(source, *pumps):
    ''' Pipe data from generators a() to b() to c() to d() ...

        pipe(a,b,c,d, ...) -> yield from ...d(c(b(a())))
        
        The source is an iterator. A pump is any callable that takes a 
        single generator parameter and returns a generator, such as a 
        function or coroutine.Pump instance. 
        
        In practice as of 2012-02-12 we've never used this, but had a need for a simpler:
            pipeline = source()
            for pump in pumps:
                pipeline = pump(pipeline)
            return pipeline


        See Pipe Fitting with Python Generators
            http://paddy3118.blogspot.com/2009/05/pipe-fitting-with-python-generators.html

        >>> from itertools import count
        >>> def sqr(x):
        ...     for val in x:
        ...         yield val*val
        
        # !!!!! python 3
        >>> def half(x):
        ...     for val in x:
        ...         yield val/2.0
                
        >>> p = pipe(count(), sqr, half)
        >>> [p.next() for i in range(5)]
        [0.0, 0.5, 2.0, 4.5, 8.0]
    '''

    gen = source
    for cmd in pumps:
        gen = cmd(gen)

    for x in gen:
        yield x
       
def pull(iterator):
    ''' Used e.g. on a pipe(), a Pump, or the last Pump at the end of a pipe to pull items 
        through the pipeline. 
        
        Simply traverses iterator. '''
        
    for item in iterator:
        pass

class Pump(object):
    ''' A Pump is a data processsing station on a python pipeline. 
        A pump can include filters, modify data items, and do one 
        time processing both before and after pumping.
    
        This class abstracts encapsulating an iterator, yield, filters, 
        and one time processing before and after.
    
        This is a superclass for classes that process data from one pipe 
        which is an iterable, and output that data as another iterable. 
        The data may be filtered or otherwise processed by overiding methods.
   
        Pump is implemented as a generator for memory efficiency. 
    
        Standard map() and reduce() are not suitable for pipes because 
        reduce() consumes the iterable, and the pipe stops. 
        You can think of this as map-reduce without consuming the iterable.
        See coroutine.Count for an example. A Pump can also filter both
        input and output data, and perform one time processing before and 
        after pumping.

        Subclass this class and supply your own methods to change default
        behavior.

        The rough equivalent of map-reduce is the method process(object). 
        process() must return an object.  The default process(self, object) 
        just returns the same object unchanged.

        Use before_filter() to filter objects before process().
        Use after_filter() to filter afterwards.
        If you only want your Pump to process certain objects, 
        but pass all objects downstream, use an "if" in process().
        The ...filter() methods filter objects going downstream.


        One time setup goes in before(). The default before() does nothing.
        Any final processing goes in after(), which also does nothing by default.

        It's generally a good idea to only subclass Pump directly. If you 
        subclass another subclass of Pump, you have to keep track of when to 
        call super(). Instead try to pass one Pump as the iterator of the other 
        Pump, or use multiple inheritance.

        >>> class Printer(Pump):
        ...     def process(self, object):
        ...         print object
        ...         return object
        
        >>> class Adder(Pump):
        ...
        ...     def before(self, *args, **kwargs):
        ...         self.total = 0
        ...
        ...     def process(self, object):
        ...         self.total += object
        ...         return object
        ...
        ...     def after(self):
        ...         print 'total: {}'.format(self.total)
        
        >>> class Counter(Pump):
        ...
        ...     def before(self, *args, **kwargs):
        ...         self.count = 0
        ...
        ...     def process(self, object):
        ...         self.count += 1
        ...         return object
        ...
        ...     def after(self):
        ...         print 'count:{}'.format(self.count)
            
        >>> a=[1, 2, 3]
        
        Pump list --> Printer --> Adder --> Counter --> len(list())
        >>> p1 = Printer(a)
        >>> p2 = Adder(p1)
        >>> p3 = Counter(p2)
        >>> count = len(list(p3))
        1
        2
        3
        total: 6
        count: 3
        
        >>> assert p2.total == sum(a)
        >>> assert p3.count == count
        
        >>> print '{count} items total to {total}'.format(count=p3.count, total=p2.total)
        3 items total to 6
        '''

    def __init__(self, iterable, *args, **kwargs):
        ''' Initialize the pipe. Call before() before all other processsing. '''

        self.source = iterable
        #if debug: log('iterable: {iterable}, self.source: {source!r}'.format(iterable=iterable, source=self.source))
        self.before(*args, **kwargs)

    def __iter__(self):
        return self

    def next(self):
        ''' Get and process the next item. '''

        try:
            # get objects until one passes both before_filter() and
            # after_filter(), or there are no more objects
            done = False
            while not done:
                object = self.source.next()
                '''
                if debug:
                    assert_message = 'process: {process}, object: {object}'.format(process=object_name(self.process), object=object_name(object))
                    try:
                        assert_message += ', name: {}'.format(self.name)
                    except:
                        pass
                    if debug: assert isinstance(object, Person), assert_message
                    if debug: assert hasattr(object, 'experienced_event'), assert_message
                '''
                if self.before_filter(object):
                    #if debug: log('calling {process}({object})'.format(process=object_name(self.process), object=object_name(object)))
                    object = self.process(object)
                    #if debug: log('after calling {process} object is {object}'.format(process=object_name(self.process), object=object_name(object)))
                    #if debug: assert isinstance(object, Person) and hasattr(object, 'experienced_event'), object_name(self.process)
                    if self.after_filter(object):
                        done = True
        except (StopIteration, GeneratorExit):
            # any exception before raise will hide StopIteration
            try:
                if debug: log(last_exception_only())
                self.after()
            except:
                log(last_exception())
            raise

        #if debug: assert isinstance(object, Person) and hasattr(object, 'experienced_event'), object_name(self.process)
        return object

    def before(self, *args, **kwargs):
        ''' Initial one time setup.
        
            Do most of the things you'd ordinarily do in __init__ here.

            The input iterable is available as self.source. Other positional and
            keyword instantiation arguments are passed as *args and **kwargs. '''
        pass

    def after(self):
        ''' Final one time processing.

            Any exception that may have occured is available using the
            usual python calls. '''
        pass

    def before_filter(self, object):
        ''' Returns True if the object passes this filter. Otherwise returns False.

            Only objects that pass before_filter() are sent to process().
            The default is to pass all objects. '''

        return True

    def after_filter(self, object):
        ''' Returns True if the object passes this filter.  Otherwise returns False.

            Only objects that pass after_filter() after processing are returned
            from instances of this iterator.  The default is to pass all objects. '''

        return True

    def process(self, object):
        ''' Perform any processing on an object.
        
            If you only want your Pump to process certain objects, 
            but pass all objects downstream, use an "if" here.
            The ...filter() methods filter objects going downstream.

            The defaut is to return the object unchanged. '''

        return object

    def __getattr__(self, name):
        ''' Pass anything else to the iterable. '''

        getattr(self.source, name)

    @staticmethod
    def build_pipeline(source, *pumps):
        ''' Connect a series of pump functions to a source. A pump 
            function is a generator function that takes an iterator 
            argument. Examples:
            
                def double(iterator):
                    for item in iterator:
                        ... change or filter item ...
                        yield item * 2
                        
                def counter(iterator):
                    return Count(iterator)
            
                lambda iterator: Count(iterator)
            
            E.g. to feed from source through the generator functions pump1 and pump2:
            
                pipeline = Pump.build_pipeline(source, pump1, pump2)
                
            'pipeline' is a generator (pump2(pump1(source))).
            
            '''
            
        #if debug: log('build_pipeline({source!r}, {pumps!r})'.format(source=source, pumps=pumps))
        pipeline = source()
        for pump in pumps:
            pipeline = pump(pipeline)
        return pipeline
        
class Count(Pump):
    ''' Adds a count attribute to an iterable.

        The count is the number of items iterated over so far.
        If an object already has a way to count its items, such as len(),
        it may be better to use that.

        >>> a=[2, 4, 8]
        >>> b=Count(a)
        >>> for x in b:
        ...     print x
        2
        4
        8
        >>> b.count
        3

        '''

    def before(self, attribute=None, *args, **kwargs):
        ''' Initialize the counter. 
        
            'attribute' is the count attribute, by default 'count'. '''

        self.attribute = attribute or 'count'
        setattr(self, self.attribute, 0)

    def process(self, object):
        ''' Count. '''

        setattr(self, self.attribute, getattr(self, self.attribute) + 1)
        return object

class Coroutine(object):
    ''' Generator based coroutine with piping, broadcasting, and aggregating.
    
        Gennerators are very memory efficient, but complex to use. This class 
        abstracts away the magic "while True", "(yield)", and superfluous "next()".
        Adds piping, broadcasting, and receiving from multiple sources.
        Includes an optional filter and one time processing before and after.
        
        Pass objects to a Coroutine subclass using the co-routine's send().
        You can also specify another Coroutine as a data source.
        Override receive() to process received data.
        (not working: Calls to receive() are synchronized to avoid races in 
        python implementations that don't lock access properly.)
        
        If you try to send() back to a Coroutine that is currently sending 
        to you, send() raises a ValueError. 
        
        When a Coroutine receives from multiple sources, the order of 
        sources is undefined. Data from each source is processed in order 
        for that source.

        When a Coroutine sends to multiple sinks, the order of sinks 
        is undefined. Data sent to a Coroutine sink is processed in the order 
        received.
        
        >>> class NoTrueScotsmanFilter(Coroutine):
        ...     # Filter out 'No true Scotsman...' definitions
        ...
        ...     def filter(self, definition):
        ...         return definition != 'No true Scotsman...'
        ...
        ...     def receive(self, object):
        ...         print object
        ...         return object
        
        >>> coroutine = NoTrueScotsmanFilter()
        >>> coroutine.send('No true Scotsman...') # no response expected
        >>> coroutine.send('Cooperating process')
        Cooperating process

        >>> class Test(Coroutine):
        ...
        ...     def receive(self, object):
        ...         print '{name} {object}'.format(name=self.name(), object=object)
        ...         return object*2

        >>> a = Test('a')
        >>> b = Test('b', sources=a)
        >>> c = Test('c', sources=b)
        
        >>> d = Test('d', sources=[b, c], sinks=[a, b])
        Traceback (most recent call last):
        ...
        ValueError: path exists from sink to self: b -> d -> b
        
        >>> e = Test('e')
        >>> d = Test('d', sources=[b, c], sinks=e)
        >>> a.send(1)
        a 1
        b 2
        d 4
        e 8
        c 4
        d 8
        e 16
        
        >>> a.send(3)      
        a 3
        b 6
        d 12
        e 24
        c 12
        d 24
        e 48
        
        '''

    def __init__(self, name=None, sources=None, sinks=None, *args, **kwargs):
        ''' A source is another coroutine which sends its output to this coroutine.
            The arg 'sources' may be a single source.
        
            A sink is another coroutine which gets its input from this coroutine.
            The arg 'sinks' may be a single sink.
        
            Initialize the receiver loop. Call before() before all other processsing. '''
        
        self._name = name
        
        self.sinks = set()
        for sink in iter(sinks):
            self.add_sink(sink)
        
        for source in iter(sources):
            source.add_sink(self)
        
        self.before(*args, **kwargs)        
        
        self.running = True
        self._c_loop = self._loop()
        self._c_loop.next()

    def _loop(self):
        ''' Receive, filter, and process each item. 
            Call after() after all other processsing. '''

        try:
            while self.running:
                object = (yield)
                if self.filter(object):
                    object = self.receive(object) # self._receive(object)
                    for sink in self.sinks:
                        sink.send(object)

        except (StopIteration, GeneratorExit):
            # any exception before raise will hide StopIteration
            try:
                if debug: log(last_exception_only())
                self.after()
            except:
                log(last_exception())
            finally:
                raise
            
    def name(self):
        return self._name or 'unknown'
            
    def send(self, object):
        ''' Called to send an object to this Coroutine. '''
        
        self._c_loop.send(object)
        
    def before(self, *args, **kwargs):
        ''' Override this function to perform any one time setup.
        
            Do what you'd ordinarily do in __init__. '''
        pass

    def after(self):
        ''' Override this function to perform any one time cleanup.

            Any exception that may have occured is available using the
            usual python calls. '''
        pass

    def filter(self, object):
        ''' Returns True if the object passes this filter. Otherwise returns False.

            Only objects that pass filter() are sent to receive().
            The default is to pass all objects. '''

        return True
        
    @synchronized # this doesn't appear to work, so _loop() calls receive() directly
    def _receive(self, object):
        ''' Perform any processing on an object. Synchronized wraper for receive(). '''

        self.receive(object)
    
    def receive(self, object):
        ''' Override this function to perform any processing on an object. '''

        return object
    
    def stop(self):
        ''' Stop running. '''
        
        self.running = False

    def add_sink(self, sink):
        ''' Add a sink safely. 
        
            Looped data pipes raise a ValueError. '''
            
        def check(sinks):
            for sink in sinks:
                if sink == self:
                    path.append(self.name())
                    raise ValueError, 'path exists from sink to self: ' + ' -> '.join(path)
                else:
                    path.append(sink.name())
                    check(sink.sinks)
            
        if sink == self:
            raise ValueError, 'sink for {} is self'.format(self.name())
        else:
            path = [self.name(), sink.name()]
            check(sink.sinks)
                
        self.sinks.add(sink)
        
def Coiterator(Coroutine):
    ''' Coroutine that is an iterator. 
    
        The items you send() to a Coiterator are produced as 
        iterator items. '''

    def before(self, block=False, *args, **kwargs):
        ''' One time setup. '''
        
        self.q = Queue()
        self.block = block
        self.done = False

    def after(self):
        ''' One time cleanup. '''
            
        self.done = True

    def receive(self, object):
        ''' Receive an object. 
        
            If 'block=True' then wait for space in the queue. Otherwise 
            if the queue is full raise Queue.Full. '''
 
        self.q.put(object, self.block)
        return object
    
    def __iter__(self):
        return self

    def next(self):
        ''' Get and process the next item. 
            Block until an object is available.
            Raise StopIteration if the source is done. '''
            
        if self.done:
            raise StopIteration
        else:
            return self.q.get(True)

if __name__ == "__main__":

    import doctest
    doctest.testmod()
