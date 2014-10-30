'''
    Ssh utilities.

    Copyright 2014 GoodCrypto
    Last modified: 2014-09-26

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

import cStringIO, os, re, sh, sys, time, traceback

import syr.lock, syr.log, syr.process, syr.times
log = syr.log.get_log()

class SshException(Exception):
    pass

class SshSession(object):
    ''' Ssh session. '''

    DEFAULT_TIMEOUT = 60 # secs

    RECOVERABLE_ERRORS = [
        # matches
        #     Connection closed by ...
        #     ssh_exchange_identification: Connection closed by remote host
        'Connection closed',
        ]
    # UNRECOVERABLE_ERRORS is unused, since behavior is identical to other errors
    UNRECOVERABLE_ERRORS = []

    def __init__(self, host,
        port=None, timeout=None, password=None, strict_host_key_checking=True):
        ''' Connect via ssh.

            'host' is the host domain to connect to.

            'port' is an optional alternate port.

            'timeout' is the connection timeout in seconds. Default is 60.
            Use 0 (zero) to timeout immediately.

            'password' is the ssh password. Default is None. If there is no
            password and the ssh server prompts for one, an exception is
            raised.

            If 'strict_host_key_checking' is True, SshSession will not try to
            handle changed keys, and ssh StrictHostKeyChecking is set to 'yes'.
            Else StrictHostKeyChecking is set to 'no'. The default is True.

            Recoverable errors are just logged unless the connection times out.
            An example is 'Connection closed'. which can happen while a server
            is booting.
        '''

        def try_connect_once():
            ''' Try to connect once. '''

            # 'pwd' is arbitrary, just to check connection
            return self.run('pwd')

        def connect():
            self.connected = False
            done = False
            while not done:

                # can we ssh into the host?
                # there should only be ssh access if this is a test build of the box
                # so maybe http access would be better
                log.debug('try ssh access')

                try:
                    result = try_connect_once()

                except sh.ErrorReturnCode as exc:
                    self.check_key_has_changed_error()
                    if not self.is_recoverable_error(exc):
                        log.debug(
                            'try_connect_once() raised sh.ErrorReturnCode:\n{}'.
                            format(traceback.format_exc()))
                        raise

                except:
                    log.debug(
                        'try_connect_once() raised unexpected exception:\n{}'.
                        format(traceback.format_exc()))
                    log.debug(traceback.format_exc())
                    raise

                else:
                    log.debug('try_connect_once() result: {}'.format(result))
                    self.check_key_has_changed_error()
                    if result.exit_code == 0:
                        self.connected = True
                        log.debug('ssh access succeeded')
                        done = True

                if not self.connected and not done:
                    check_deadline()

            if self.connected:
                # issue one more command to clear any ssh messsges such as
                #     Permanently added ... to the list of known hosts.
                try_connect_once()
            else:
                log.error('unable to ssh to {} on {}'.format(self.port, self.host))

        def check_deadline():
            now = syr.times.now()
            # we use '>=' instead of '>' to avoid a possible race
            # when self.timeout is zero
            # if check_deadline() is called quickly enough,
            # we could go through connect()'s 'while not done' loop again,
            # and timeout=0 means just once through the loop.
            if now >= self.deadline:
                actual_duration = syr.times.timedelta_to_human_readable(
                    self.deadline - self.start)
                msg = 'timed out in {} seconds (actual {})'.format(
                    self.timeout, actual_duration)
                log.debug(msg)
                raise syr.process.TimedOutException(msg)

            else:
                log.debug('{} until timeout'.format(
                    syr.times.timedelta_to_human_readable(self.deadline - now)))
                time.sleep(1)

        self.host = host
        self.port = port
        if timeout is None:
            log.debug('set timeout to default {}'.format(SshSession.DEFAULT_TIMEOUT))
            self.timeout = SshSession.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout
        self.strict_host_key_checking = strict_host_key_checking
        self.password = password

        self.start = syr.times.now()
        self.deadline = self.start + (syr.times.one_second * self.timeout)
        
        # we can't use sh result's stdout/stderr because they wait for the program to finish
        self.stdout_buffer = cStringIO.StringIO()
        self.stderr_buffer = cStringIO.StringIO()
        
        self.base_args = []
        if self.port:
            self.base_args.extend(['-p', self.port])
        # the ssh default for StrictHostKeyChecking is 'ask',
        # which is not appropriate for unattended use
        if self.strict_host_key_checking:
            self.base_args.extend(['-o', 'StrictHostKeyChecking=yes'])
        else:
            self.base_args.extend(['-o', 'StrictHostKeyChecking=no'])
        self.base_args.append(self.host)

        connect()
        
    @property
    def stdout(self):
        return self.stdout_buffer.getvalue()

    @property
    def stderr(self):
        return self.stderr_buffer.getvalue()

    def run(self, *args, **kwargs):
        """ Run a command using the ssh session. 
        
            Returns a result in the same form as the sh module.
        """
        
        """ UNUSED
            If the command succeeds, we set the .stdout and .stderr attrbutes 
            of the self.stdout and self.stderr on exit. In case the command 
            raises an exception, we also set self.stdout and self.stderr to
            stdout and stderr from the most recent run().
        """
        
        """
            SshSession.run() is implemented as separate calls to ssh. 
            This gives run() access to the exit code of each remote command.
            It also is arguably more secure, since each invocation of ssh 
            negociates a new session key.
            
            Every ssh connection requires a minimum of time to defeat timing attacks.
        
            Example prompts::
    
                The authenticity of host '[127.0.0.1]:8122 ([127.0.0.1]:8122)' can't be established.
                RSA key fingerprint is db:a7:d3:b7:18:34:f9:ad:b1:fd:bd:42:75:4c:39:89.
                Are you sure you want to continue connecting (yes/no)? MY_RESPONSE_1
                Warning: Permanently added '[127.0.0.1]:8122' (RSA) to the list of known hosts.
                root@127.0.0.1's password: MY_RESPONSE_2
        """
        
        def _cli_out(output):
            ''' Save cli.Responder command stdout. '''
    
            self.stdout_buffer.write(output)
            log.debug('run() stdout: {}'.format(output.rstrip()))
    
        def _cli_err(output):
            ''' Save and log cli.Responder command stderr. '''
    
            self.stderr_buffer.write(output)
            log.debug('run() stderr: {}'.format(output.rstrip()))

        def no_password(prompt):
            ''' If we are prompted for a password, raise an exception. '''
            
            raise SshException('password required')

        # log command
        log.debug('ssh.run({})'.format(', '.join([repr(arg) for arg in args])))
        """
        # log args and kwargs
        log.debug('ssh.run({})'.
            # args
            format(', '.join([repr(arg) for arg in args]) +
            ', ' +
            # kwargs
            ', '.join(['{}={}'.format(key, repr(value)) for key, value in kwargs.items()])))
        """

        responses = {}
        if self.strict_host_key_checking:
            responses['(yes/no)? '] = 'yes'
        if self.password:
            responses['password:'] = self.password
        else:
            # if we are prompted for a password, raise an exception
            responses['password:'] = no_password

        env = syr.cli.minimal_env()

        program = 'ssh'
        all_args = [responses, program] + self.base_args + list(args)
        all_kwargs = dict(
            _clilog=_cli_out,
            _env=env,
            _err=_cli_err,
            _tee=True)
        all_kwargs.update(kwargs)
        # log.debug('all_args: {}'.format(all_args))
        # log.debug('all_kwargs: {}'.format(all_kwargs))

        return syr.cli.Responder(*all_args, **all_kwargs).result

    def is_recoverable_error(self, exc):
        ''' Check exception and output buffer text for recoverable errors. '''

        exc_text = str(exc)

        recoverable = False
        for ok_text in SshSession.RECOVERABLE_ERRORS:
            if not recoverable:
                recoverable = (
                    ok_text in exc_text or 
                    ok_text in self.stdout or 
                    ok_text in self.stderr)
                if recoverable:
                    log.debug(
                        'possible recoverable error from ssh: {}'.
                        format(ok_text))

        return recoverable

    def check_key_has_changed_error(self):
        ''' If key has changed and not self.strict_host_key_checking, remove old key. '''

        """
            Error message example::

                @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                @    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
                @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
                IT IS POSSIBLE THAT SOMEONE IS DOING SOMETHING NASTY!
                Someone could be eavesdropping on you right now (man-in-the-middle attack)!
                It is also possible that a host key has just been changed.
                The fingerprint for the RSA key sent by the remote host is
                e8:90:1e:bd:f0:24:e9:cf:57:fe:8e:2c:09:7a:c8:f7.
                Please contact your system administrator.
                Add correct host key in /root/.ssh/known_hosts to get rid of this message.
                Offending RSA key in /root/.ssh/known_hosts:4
                RSA host key for [127.0.0.1]:8122 has changed and you have requested strict checking.
                Host key verification failed.
        """

        # pattern example: 'Offending RSA key in /root/.ssh/known_hosts:4'
        pattern = r'Offending RSA key in (.*?):(\d+)'
        # does this output really sometimes go to stderr, and sometimes to stdout?
        output = self.stdout + self.stderr
        # log.debug('matching pattern "{}" against output "{}"'.
        #     format(pattern, output))
        match = re.search(pattern, output)
        if match and not self.strict_host_key_checking:

            log.debug('check_key_has_changed_error() fixing error')

            # log.debug('error match: {}'.format(match.group(0)))
            log.debug('filenane: {}'.format(match.group(1)))
            log.debug('bad line number: {}'.format(match.group(2)))

            filename = match.group(1)
            bad_line_number = int(match.group(2))

            with open(filename) as known_hosts:
                text = known_hosts.read()
                log.debug('old known_hosts:\n{}'.format(text))
                lines = text.split('\n')

            lines = lines[:bad_line_number-1] + lines[bad_line_number:]

            with open(filename, 'w') as known_hosts:
                text = '\n'.join(lines)
                log.debug('new known_hosts:\n{}'.format(text))
                known_hosts.write(text)
            os.chmod(filename, 0600)
    
        return bool(match)
