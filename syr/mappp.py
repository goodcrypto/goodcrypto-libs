'''
    Map function using Parallel Python.
    
    Copyright 2010 GoodCrypto
    Last modified: 2013-11-11

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

import __builtin__, sys


class MapPP():
    ''' Parallel map().
    
        Mappp speeds up parallel processes that are limited by 
        a resource other than the cpu. If your work is CPU 
        bound, you probably won't see any speed improvement on 
        a single processor machine. 

        This version is based on the Parallel Python module. PP 
        works with multiple processes on a single processor, 
        multiple processors on a single machine, or multiple 
        machines in a cluster. Because MapPP abstracts the parallel 
        implementation, it can easily use a different underlying
        parallelization in the future.
        
        The default number of parallel processes for a single 
        processor machine with one core is 10. For a multi-processor 
        machine it is the number of processors. For a cluster it is 
        the number of ppservers passed in the "ppservers" keyword. 
        You can set ncpus to the maximum number of local processes 
        you want. If you set it to one this class will map each 
        item consecutively, like python's builtin map().
    
        The instantiation args are passed through to pp.Server and 
        pp.Server.submit(). See the pp module documentation for details.
            
        If the work function you pass to map calls any other 
        functions or requires any imported modules, list them in the 
        depfuncs and modules args. The depfuncs arg is a tuple of 
        functions. The modules arg is a tuple of strings, where each 
        string is a module name. 
        
        The imported modules for pp are relative to the pp module. So
        if you need to import pp.pp itself, move the import to within 
        the function that uses it, use 'import pp.pp', and the 
        import name passed in the modules arg is 'pp'.'''
    
    default_min_cpus = 10
    
    server_is_singleton = False
    pp_server = None
        
    def __init__(self, 
    
        # pp.Server args
        ncpus='autodetect', ppservers=(), secret="mappp-secret", 
        loglevel=30, logstream=sys.stderr,
        restart=False, proto=0,
        
        # pp.Server.submit() args
        depfuncs=(), modules=(), 
        callback=None, callbackargs=(), group='default', globals=None):
        
        ''' Initialize a parallel map.'''

        ''' The debian (version 1.57 on lenny) distribution for pp is 
            slightly different. Ubuntu is a debian derivative and behaves 
            similarly.
        '''
        try:
            from pp import pp
        except:
            import pp
        
        def new_server():
            ''' Instantiate a pp server.'''
            
            if pp.version.startswith('1.5'):
                
                server = pp.Server(
                    ncpus=ncpus, ppservers=ppservers, secret=secret, 
                    loglevel=loglevel, logstream=logstream,
                    )
                
            else:
                
                server = pp.Server(
                    ncpus=ncpus, ppservers=ppservers, secret=secret,
                    restart=restart, proto=proto
                    )
            
            return server

        if MapPP.server_is_singleton:
            if not MapPP.pp_server:
                MapPP.pp_server = new_server()
            self.pp_server = MapPP.pp_server
        else:
            self.pp_server = new_server()
            
        if self.pp_server.get_ncpus() <= 1 and ncpus == 'autodetect':
            self.pp_server.set_ncpus(MapPP.default_min_cpus)
        
        self.depfuncs = depfuncs
        self.modules = modules
        self.callback = callback
        self.callbackargs = callbackargs
        self.group = group
        self.globals = globals
        
    def map(self, work_function, required_iterable, *optional_iterables):
        ''' Parallel map().'''
            
        def submit(item):
            ''' Submit work_function(item) to pp as a separate task.'''
            
            return self.pp_server.submit(
                work_function, (item,), 
                depfuncs = self.depfuncs,
                modules = self.modules,
                callback = self.callback,
                callbackargs = self.callbackargs,
                group = self.group,
                globals = self.globals)
            
        items = []
        items.extend(required_iterable)
        for optional_iterable in optional_iterables:
            items.extend(optional_iterable)

        tasks = __builtin__.map(submit, items)
        results = [task_result() for task_result in tasks]
        
        if not MapPP.server_is_singleton:
            self.pp_server.destroy()
            
        return results

def test_read_from_web(url):
    ''' Test work function.'''
    import urllib
    return urllib.urlopen(url).getcode() 
        
def mappp(work_function, iterable, **kwargs):
    ''' Map function using Parallel Python.
    
        Warning: unreliable and cumbersome.

        This function is not called map() because Parallel Python 
        imposes some significant restrictions over the standard map().
        
        In the  work_function, scoping is very different from the 
        builtin map(). All variables used must be local to the function. 
        All functions used must be declared using the "depfuncs" keyword. 
        All imported modules used must be declared using the "modules" 
        keyword.
        
        All arguments to the work_function and the return value must be 
        picklable.

        In order for this map function to accept pp keyword arguments, it 
        only allows one iterable. This is almost always the case with map(),
        and it's easy to combine iterables anyway.
        
        >>> mappp(test_read_from_web, ['http://google.com', 'http://bing.com'], depfuncs=['test_read_from_web'], modules=['syr.mappp', 'pp', 'urllib'],)
        [200, 200]
    '''
                    
    return MapPP(**kwargs).map(work_function, iterable)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
