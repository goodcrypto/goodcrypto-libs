'''
    Remote process call.

    We should probably factor out a syr.jobqueue module from this one.

    Internally uses RQ.

    Copyright 2015 GoodCrypto
    Last modified: 2015-08-01

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.

'''

import redis, rq

class RpcException(Exception):
    pass

class RpcNotFinished(Exception):
    pass

class Connection(object):
    def __init__(self, function):
        self.redis_connection = redis.Redis(REDIS_HOST, GPG_REDIS_PORT)

class Queue(object):
    def __init__(self, name, connection):
        ''' 'name' is the name of this queue. 'connection' is a syr.rpc.Connection. '''
        self.queue = rq.Queue(name=name, connection=connection)

    def add(self, job):
        ''' Add the job to this queue.

            'job' is a syr.rpc.Job.
        '''
        job._rqjob = queue.enqueue_call(job.function, job.args, timeout=job.timeout)

class Worker(object):
    """ Create an rpc worker.

        >>> def triple(x):
        ...     return 3 * x

        >>> import sh
        >>> process = sh.rqworker('test', _bg=True)

        >>> worker = Worker(triple)
        >>> worker.start()

        >>> worker.call(2, 3)

        >>> process.kill()

    """

    def __init__(self, function):
        self.function = function
        self.task = app.task(function)

    def start(*args, **kwargs):
        return self.task.delay(*args, **kwargs)

class Job(object):
    def __init__(self, function, *args, _timeout=None):
        ''' Remote job.

            To add a job to a queue::

                queue = Queue(...)
                ...
                queue.add(Job(...))
        '''

        self.function = function
        self.args = args
        self.timeout = _timeout
        self._rqjob = None

    @property
    def result(self):
        ''' Result of rpc call.

            Raises RpcException if job has not been added to a queue.
            Raises RpcNotFinished if job is not finished.
        '''

        try:
            # is exc_info still pickled? if so we need 'pickle.loads(self._rqjob.exc_info)'
            raise self._rqjob.exc_info
        except KeyError:
            # no worker exception (yet)
            pass

        if self._rqjob is None:
            raise RpcException('job must be added to a queue')
        elif not self._rqjob.result is None:
            # this is cleaner than rq's choice to return None because
            # of the ambiguity when a worker returns sometimes None, and
            # sometimes doesn't
            raise RpcNotFinished()
        else:
            job_result = self._rqjob.result

        return job_result

if __name__ == "__main__":
    import doctest
    doctest.testmod()
