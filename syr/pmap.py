'''
    Threaded map().

    Copyright 2010-2015 GoodCrypto
    Last modified: 2015-01-04

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''



import __builtin__, sys, threading, time

from syr.log import get_log
from syr.lock import locked
from syr.python import object_name

log = get_log()

class Pmap():
    ''' Parallel map().

        Pmap speeds up parallel processes that are limited by
        a resource other than the cpu. If your work is CPU
        bound, you probably won't see any speed improvement. 
        
        There are other parallel python modules that try to work with 
        multiprocessors, clusters and the cloud. They don't seem reliable. 
        Pmap works in memory on a single cpu.'''

    class Task():
        ''' Task to map one item in a separate thread. '''

        def __init__(self, work_function, item):
            self.work_function = work_function
            self.item = item
            self.lock = threading.Condition()
            self.started = False
            self.done = False
            thread = threading.Thread(
                target=Pmap.Task.run,
                args=(self, work_function, item))
            thread.start()

        def run(self, work_function, item):
            ''' Runs the work function and notifies that the result is ready. '''

            
            #log('%s run() acquiring lock' % self)
            with locked(self.lock):
                #log('%s run() lock accquired' % self)
                self.started = True
                # the work_function() should yield (time.sleep(0)) when possible, 
                # or call lock.wait()/notify() as needed
                self.task_result = work_function(item)
                self.done = True
                #log('%s run() notifying' % self)
                self.lock.notify()
                #log('%s run() releasing' % self)
            #log('%s run() lock released' % self)

        def result(self):
            ''' Waits until the work function is done and the result is ready.
                Returns the result. '''

            ''' We have to acquire the lock first to ensure self.done is 
                in a valid state. 
            
                Otherwise apparently the acquire() in run gets the lock, and 
                then allows other threads to start before acquire() returns. 
                If result() starts during this period, then self.done is 
                False. But because we then call acquire() in result(), we 
                get a deadlock waiting to acquire the lock. We never get to 
                the wait(). '''
            #log('%s result() acquiring lock' % self)
            with locked(self.lock):
                # is this 'if' atomic wrt threading? 
                if not self.done:
                    #log('%s result() waiting' % self)
                    self.lock.wait()
                #log('%s result() releasing' % self)
            #log('%s result() lock released' % self)
                
            return self.task_result
    
        def __unicode__(self):
            return '%s %r' % (object_name(self), self.item)        

    def __init__(self, work_function, required_iterable, *optional_iterables):
        ''' Start tasks. '''

        items = []
        items.extend(required_iterable)
        for optional_iterable in optional_iterables:
            items.extend(optional_iterable)

        self.tasks = (Pmap.Task(work_function, item) for item in items)

    def results(self):
        ''' Get results from tasks. '''

        return (task.result() for task in self.tasks)
            
def _test_function(s):
    ''' Test work function.'''

    return '%sx' % s

def pmap(work_function, iterable, **kwargs):
    ''' Threaded map().

        >>> pmap(_test_function, ['a', 'b'],)
        ['ax', 'bx']
    '''

    return Pmap(work_function, iterable).results()


if __name__ == "__main__":
    import doctest
    doctest.testmod()
