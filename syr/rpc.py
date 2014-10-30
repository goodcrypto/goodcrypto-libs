'''
    Remote process call.
    
    Not working. Celery is simple enough. Use it directly.
    
    Copyright 2013 GoodCrypto
    Last modified: 2013-11-16

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from celery import Celery

#app = Celery('tasks', broker='amqp://guest@localhost//')
app = Celery('tasks', backend='amqp', broker='amqp://')

class Worker(object):
    """ Create an rpc worker. 

        >>> def multiply(x, y):
        ...     return x * y
        
        >>> worker = Worker(multiply)
        
        >>> worker.call(2, 3)
        
    """
    
    def __init__(self, function):
        self.function = function
        self.task = app.task(function)
        
    def start(*args, **kwargs):
        return self.task.delay(*args, **kwargs)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
