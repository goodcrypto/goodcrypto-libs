'''
    Command line interface.
    
    A wrapper for the sh module. 
    The Responder class responds to prompts from programs.
    The Commands class issues multiple commands at the command prompt.
    
    Copyright 2013-2014 GoodCrypto
    Last modified: 2014-12-22

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

# delete in python 3
import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from abc import ABCMeta, abstractmethod
import os, re, sh, sys, traceback
from threading import Timer

from lock import locked
import log, times

log = log.get_log()

class CliException(Exception):
    pass


class StderrException(Exception):
    ''' Raised when run() detects stderr output '''
    
    def __init__(self, sh_result):
        self.sh_result = sh_result

class AbstractCli(object):
    ''' Run a command line interface program with responses. '''
    
    PRINT_LOG = False
    DEFAULT_MAX_TIME_TO_RECEIVE_LINE = 60 # seconds
    
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        self._clilog = None

    def _log(self, line):
        ''' Log line. '''
        
        log.debug('output: {}'.format(line.strip('\n')))
        if self._clilog:
            self._clilog(line)
        elif self.PRINT_LOG:
            print('(no cli_log) ' + line.strip('\n'))
            
    def log_exception(self):
        ''' Log latest exception. '''
        
        def strip_str(msg, str):
            msg = msg.rstrip()
            if msg.endswith(str):
                msg = msg[:-len(str)]
                msg = msg.rstrip()
            return msg
        
        msg = traceback.format_exc()
        # if STDOUT and STDERR are blank, strip them to avoid confusion
        msg = strip_str(msg, 'STDERR:')
        msg = strip_str(msg, 'STDOUT:')
        self._log(msg)
        log.debug('output logged earlier as "output:"')
        
    def sh_command(self, program):
        ''' return sh.Command(prograa), or None if program not found. '''
        
        # sh.Command requires an absolute path
        program = sh.which(program)
        if not program:
            raise CliException('program not found: {}'.format(program))
            
        return sh.Command(program)
        
    def buffer(self, out):
        ''' Buffer and log custom command output. '''
    
        with locked():
            try:
                self.line_buffer += out
            except UnicodeDecodeError:
                for ch in out:
                    try:
                        self.line_buffer += ch
                    except UnicodeDecodeError:
                        log.debug('skipping char: {}'.format(ord(ch)))
                
            if '\n' in out:
                self.flush_buffer()
            else:
                self.reset_line_timeout()
    
    def flush_buffer(self):
        ''' Log any last partial line from custom command output. '''
        
        with locked():
            if self.line_buffer:
                self._log(self.line_buffer)
                self.line_buffer = ''
            self.cancel_line_timeout()

    def line_timeout(self):
        ''' Log anything that is in custom command output buffer. '''
        
        with locked():
            if self.line_buffer:
                log.debug('LINE TIMED OUT after {} seconds. Possible prompt without response: "{}"'.
                    format(Responder.DEFAULT_MAX_TIME_TO_RECEIVE_LINE, self.line_buffer))

    def reset_line_timeout(self):
        ''' To log an unanswered prompt, set a timer to flush the buffer if we 
            haven't received any output in a while. '''

        with locked():
            self.cancel_line_timeout()
            self.log_buffer_thread = Timer(
                Responder.DEFAULT_MAX_TIME_TO_RECEIVE_LINE, self.line_timeout)
            self.log_buffer_thread.start()
                    
    def cancel_line_timeout(self):

        with locked():
            if self.log_buffer_thread:
                self.log_buffer_thread.cancel()
                self.log_buffer_thread = None

class Responder(AbstractCli):
    ''' Run a command line interface program with responses.
    
        Assumes a fixed set of prompts, and the same prompt always gets the 
        same response. The response may be a callable that returns a
        response string or raises an exception::
        
            def my_response(prompt):
                if ...:
                    raise ...
                return my_response_string
        
        When matching a prompt, leading characters are ignored.
        Trailing spaces are significant only if prompt ends with a space.
        
        Another advantage over using the sh module directly is that when a 
        command prompts, sh freezes completely silently. Responder logs the 
        prompt (see "To do" for timeout).
        
        You can use Responder to log any unexpected prompts::
        
            Responder(response={}, program, ...)
        
        For an advanced Responder example, see jean.ssh.
        
        To do:
            Add two prompt timeouts like the line timeout.
            
              * time out any unexpected prompt. Just use 
                DEFAULT_MAX_TIME_TO_RECEIVE_LINE as the default for a line 
                timeout param, and raise an exception when it times out
              * internal timeout requiring the prompt to be stable for half 
                a second or so
    
        >>> # test not working because stdin and/or stdout are wrong
        >>> def log(line):
        ...     print(line + '\\n')
        
        >>> responses = {
        ... 'Are you sure you want to continue connecting (yes/no)?': 'n',
        ... "Please type 'yes' or 'no':": 'no',
        ... '$': 'exit',
        ... '>': 'exit',
        ... }
        
        >>> #DISABLED responder = Responder(responses, 'ssh', 'localhost', _clilog=log)
    '''
    
    def __init__(self, responses, program, *args, **kwargs):
        ''' Respond to command line prompts from an sh program. 
        
            'responses' is a dict of {prompt: response, ...}.
            Leading and trailing spaces in a prompt are ignored.
            
            '_clilog', if provided, is a log function called as '_clilog(line)'.
            '_clilog' is never passed as an argument to the called program.
            
            The other parameters are passed to sh.Command().
            
            The result from the sh module is returned as (Responder instance).result.
            
            If the sh module raises an error, Responder will propagate that error. 
        '''

        super(Responder, self).__init__()

        # log the command
        cmdstr = ''
        for arg in args:
            if cmdstr:
                cmdstr += ' '
            cmdstr += str(arg)
        for key, value in kwargs.items():
            if cmdstr:
                cmdstr += ' '
            cmdstr += '{}={}'.format(key, value)
        log.debug('Responder command: "{} {}"'.format(program, cmdstr))
        # log.debug('start Responder responses={}, program={}, args={}, kwargs={}'.format(
        #     repr(responses), repr(program), repr(args), repr(kwargs)))
            
        self.responses = responses
        self.log_buffer_thread = None
            
        if '_clilog' in kwargs:
            self._clilog = kwargs['_clilog']
            del kwargs['_clilog']
        else:
            self._clilog = None

        # we can't use sh result's stdout because it waits for the program to finish
        self.line_buffer = ''
    
        command = self.sh_command(program)
    
        # sh does not propagate exceptions from an _out function, so...
        self.exc_info = None
        kwargs.update(
            dict(_out=self.interact, _out_bufsize=0, _tty_in=True,))
        self.result = command(*args, **kwargs)
        try:
            self.result.wait()
        except sh.SignalException_9:
            if self.exc_info:
                raise CliException(self.exc_info)
        except: 
            self.log_exception()
            raise
                
        self.flush_buffer()
        self.cancel_line_timeout()

    def interact(self, out, stdin, process):

        def answer(response):
            ''' Answer a prompt. '''
            
            log.debug('response: {}'.format(response))
            self.buffer(response)
            stdin.put(response + '\n')
                
        # sh locks up if function used in sh _out=function throws an error
        try:            
            # log.debug('stdout: {}'.format(repr(out)))    
            self.buffer(out)
            
            answered = False
            for prompt in self.responses:
                if not answered:
                     
                    if prompt.endswith(' '):
                        match = self.line_buffer.endswith(prompt) 
                    else:
                        match = self.line_buffer.strip(' ').endswith(prompt.strip(' '))
                        
                    if match:
                        self.flush_buffer()
                        response = self.responses[prompt]
                        
                        if callable(response):
                            log.debug('response to prompt "{}" is callable'.
                                format(prompt))
                            log.debug('call {}'.format(repr(response)))
                            response = response(prompt)
                            
                        log.debug('cli prompt: "{}", response: "{}"'.
                            format(prompt, response))
                        answer(response)
                        answered = True
            
        except:
            # sh does not propagate exceptions from an _out function, so...
            self.exc_info = sys.exc_info()
            self.log_exception()
            log.debug('intentionally killing process due to sh idiom')
            # the sh module does not propagate a raised exception here
            # the sh 1.08 idiom is: 
            process.kill()
            return True            

class Commands(AbstractCli):
    ''' 
        Run a command line program that prompts for commands.
        Some commands don't allow redirecting stdin.
        
        Example:
            user = 'test'
            password = 'secret'
            connect_to_db = '\connect {}'. format(db)
            change_password = "ALTER USER {} WITH PASSWORD '{}'".format(user, password)
            
            prompt = ':/# '
            commands = [
                'psql --command="{}"'.format(connect_to_db),
                'psql --command="{}"'.format(change_password),
                'exit'
                ]
            
            command = Commands(prompt, commands)
            args = ['su', '--login', 'postgres']
            kwargs = dict(_ok_code=2, _clilog=sh_out, _env=minimal_env(), _err=sh_err)
            result = command.run('sudo', *args, **kwargs)
    '''
    
    def __init__(self, prompt, commands):
        ''' 
            'prompt' is the prompt that appears after running the command line program.
            When matching the prompt, leading characters are ignored.
            Trailing spaces are significant only if prompt ends with a space.
            
            'commands' is a list of commands in sequential order.
        '''
    
        super(Commands, self).__init__()

        log.debug('prompt={}, commands={}'.format(prompt, repr(commands)))
            
        self.prompt = prompt
        self.commands = commands
        
        self.line_buffer = ''
        self.log_buffer_thread = None

    def run(self, program, *args, **kwargs):
        ''' 
            Run a program with its own command line prompts.
            
            '_clilog', if provided, is a log function called as '_clilog(line)'.
            '_clilog' is never passed as an argument to the called program.
            
            The other parameters are passed to sh.Command().
            
            The result from the sh module is returned.
            
            If the sh module raises an error, SudoCommands will propagate that error. 
        '''
    
        log.debug('program={}, args={}, kwargs={}'.format(program, repr(args), repr(kwargs)))
            
        if '_clilog' in kwargs:
            self._clilog = kwargs['_clilog']
            del kwargs['_clilog']
    
        command = self.sh_command(program)
        self.result = command(
            _out=self.interact, _out_bufsize=0, _tty_in=True,
            *args, **kwargs)

        # sh does not propagate exceptions from an _out function, so...
        self.exc_info = None
        try:
            self.result.wait()
        except sh.SignalException_9:
            if self.exc_info:
                raise CliException(self.exc_info)
        except: 
            self.log_exception()
            raise

        self.flush_buffer()
        self.cancel_line_timeout()

        return self.result

    def interact(self, out, stdin, process):

        # sh locks up if function used in sh _out=function throws an error
        try:                
            self.buffer(out)
            
            if len(self.commands) > 0:
                if self.prompt.endswith(' '):
                    match = self.line_buffer.endswith(self.prompt) 
                else:
                    match = self.line_buffer.strip(' ').endswith(self.prompt.strip(' '))
                        
                if match:
                    self.flush_buffer()
                    
                    command = self.commands[0]
                    if len(self.commands) > 1:
                        self.commands = self.commands[1:]
                    else:
                        self.commands = []
                    log.debug('cli command: "{}"'.format(command))
                    self.buffer(command)
                    stdin.put(command + '\n')

        except:
            # sh does not propagate exceptions from an _out function, so...
            self.exc_info = sys.exc_info()
            self.log_exception()
            log.debug('intentionally killing process due to sh idiom')
            # the sh module does not propagate a raised exception here
            #  nor does this function have access to self
            # the sh 1.08 idiom is: 
            process.kill()
            return True
            
def run(sh_function, *args, **kwargs):
    ''' Run an sh command, catching errors carefully. 
    
        An error is:
          * any exit code which is not zero and not specified in _ok_code
          * anything in stderr
          * any exception
          
        To treat stderr output as not an error, pass _stderr_ok=True.
        
        Note that signals do not raise an exception.
        
        Most of the error checking is handled by the sh module.
        
        >>> import syr.user
        >>> assert run(sh.whoami).strip() == syr.user.whoami()
    '''
    
    _stderr_ok = '_stderr_ok' in kwargs
    if _stderr_ok:
        del kwargs['_stderr_ok']
    
    try:
        result = sh_function(*args, **kwargs)
        if not _stderr_ok:
            if result.stderr.strip():
                raise StderrException(result)
        
    except sh.ErrorReturnCode as erc:
        raise
        
    return result

def minimal_env(user=None):
    ''' 
        Get very minimal, safe chroot env. 
        
        Be sure to validate anything that comes from environment variables
        before using it. According to David A. Wheeler, a common cracker's
        technique is to change an environment variable.
        
        If user is not set, gets the user from syr.user.whoami(). This 
        can flood /var/log/auth.log, so call with user set when you can.
        
        >>> env = minimal_env()
        >>> env['PATH']
        '/bin:/usr/bin:/usr/local/bin'
    '''
    
    # import delayed to avoid recursive imports
    import syr.user
    
    if not user:
        user = syr.user.whoami()

    env = {}
    
    # use a minimal path
    if user == 'root':
        env['PATH'] = '/bin:/usr/bin:/usr/local/bin:/sbin:/usr/sbin:/usr/local/sbin'
    else:
        env['PATH'] = '/bin:/usr/bin:/usr/local/bin'
    
    env_var = 'HOME'
    if env_var in os.environ:
        var = os.environ[env_var]
        # make sure the home directory is something reasonable and reasonably safe
        # Wheeler's Secure Programming warns against directories with '..'
        var = os.path.abspath(var)
        if os.path.exists(var):
            env[env_var] = var

    env_var = 'TZ'
    if env_var in os.environ:
        var = os.environ[env_var]
        # only set the variable if it's reasonable
        m = re.match('^([A-Za-z]+[A-Za-z_-]*/?[A-Za-z_-]*/?[A-Za-z_-]*\+?-?[A-Za-z0-9]*)$', var)
        if m and (m.group(1) == var):
            env[env_var] = var

    env_var = 'IFS'
    if env_var in os.environ:
        # force the variable to a known good value
        env[env_var] = "$' \t\n'"

    env_var = 'LC_ALL'
    if env_var in os.environ:
        # force the variable to a known good value
        env[env_var] = 'C'

    return env
                
def test():
    ''' Test. '''
    
    import doctest
    doctest.testmod()
    
    """
    def log(line):
        print(line, end=None)
        
    responses = {
        # answer one prompt wrong so we get another
        'Are you sure you want to continue connecting (yes/no)?': 'n',
        "Please type 'yes' or 'no':": 'no',
        '$': 'exit',
        '>': 'exit',
        }
        
    responder = Responder(responses, 'ssh', 'localhost', _clilog=log)
    """
    
if __name__ == "__main__":
    test()
    
