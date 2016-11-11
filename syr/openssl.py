'''
    Use openssl to generate a self-signed 4096 RSA cert.

    To do: Sanitize syr.cli inputs.
    Do we need to include a "distinguished_name" or group or req name in the conf file?

    Copyright 2014-2016 GoodCrypto
    Last modified: 2016-09-04
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import os, re, sh
from datetime import datetime, timedelta
from OpenSSL import crypto
from OpenSSL.SSL import FILETYPE_PEM
from tempfile import gettempdir
from traceback import format_exc

from syr.cli import minimal_env, Responder
from syr.lock import locked
from syr.log import get_log
from syr.utils import randint

log = get_log()

PRIVATE_KEY = 'private.key'
PUBLIC_CERT = 'public.crt'

SELF_SIGNED_CERT_ERR_MSG = 'self signed certificate'
EXPIRED_CERT_ERR_MSG = 'certificate expired on'

def verify_certificate(hostname, port, ca_certs_dir=None):
    '''
        Verify a certificate is valid. Compare against openssl's published certs.

        Debian Jessie openssl does not support proxies, so we can't specify a tor proxy directly.
        This function uses sh, so syr.net.torify() doesn't work.

        >>> ok, _, _ = verify_certificate('google.com', 443)
        >>> ok
        True

        >>> ok, _, error_message = verify_certificate('goodcrypto.private.server', 443)
        >>> ok
        False
        >>> if IS_PY2:
        ...     error_message == u'self signed certificate'
        ... else:
        ...     error_message == 'self signed certificate'
        True

        >>> ok, _, error_message = verify_certificate('www.mjvmobile.com.br', 443)
        >>> ok
        False
        >>> if IS_PY2:
        ...     error_message == u'certificate has expired'
        ... else:
        ...     error_message == 'certificate has expired'
        True
    '''

    def extract_cert(response):

        cert = None

        i = response.find('-----BEGIN CERTIFICATE-----')
        if i > 0:
            temp_cert = response[i:]
            i = temp_cert.find('-----END CERTIFICATE-----')
            if i > 0:
                cert = temp_cert[:i+len('-----END CERTIFICATE-----')]

        return cert

    def verify_date(cert):

        ok = True
        error_message = None

        not_before, not_after = get_dates(cert)
        try:
            after_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
        except:
            try:
                after_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %z')
            except:
                after_date = datetime.now() + timedelta(days=1)
        if after_date < datetime.now():
            ok = False
            error_message = '{} {}'.format(EXPIRED_CERT_ERR_MSG, not_after)

        return ok, error_message

    ok = True
    error_message = ''
    cert = None

    server = '{}:{}'.format(hostname, port)
    log('verify cert for {}'.format(server))

    if ca_certs_dir is None:
        ca_certs_dir = get_ca_certs_dir()
    log('ca certs dir: {}'.format(ca_certs_dir))

    try:
        # s_client waits for stdin after connecting, so we provide a short stdin
        # _in=' ' instead of _in='' because apparently sh does something like
        # checks '_in' instead of '_in is None'
        result = sh.openssl('s_client', '-connect', server, '-CApath', ca_certs_dir, _in=' ')

    except sh.ErrorReturnCode as erc:
        ok = False
        try:
            stderr = erc.stderr.strip()
            log('verify failed stderr:\n{}'.format(stderr))
            # parse 'connect: No route to host\nconnect:errno=22'
            # to 'connect: No route to host'
            error_message = stderr.split('\n')[0].strip()
        except:
            error_message = erc # 'Unable to verify SSL certificate'
        log(erc)

    else:
        if IS_PY2:
            result_stderr = result.stderr
        else:
            result_stderr = result.stderr.decode()
        log('verify result stderr:\n{}'.format(result_stderr))
        lines = result_stderr.split('\n')
        return_code = None
        for line in lines:
            if line.startswith('verify return:'):
                return_code = line[len('verify return:'):]
            elif line.startswith('verify error:'):
                m = re.match('verify error:num=(\d+):(.*)', line)
                if m:
                    return_code = m.group(1)
                    error_message += m.group(2)
                else:
                    return_code = -1
                    error_message = line

        # get the certificate so we can do additional verification
        if IS_PY2:
            cert = extract_cert(result.stdout)
        else:
            cert = extract_cert(result.stdout.decode())

        # it seems like we're never able to verify the local issuer so ignore the error
        if return_code == '0' and error_message == 'unable to get local issuer certificate':
            error_message = None

        if error_message is not None and len(error_message) > 0:
            ok = False
            log('error verifying {} certificate: {}'.format(hostname, error_message))
        else:
            error_message = None

        if return_code == '0' and error_message is None:
            ok, error_message = verify_date(cert)

    log('cert ok: {}'.format(ok))

    return ok, cert, error_message

def get_issuer(cert):
    '''
        Get the issuer of an SSL certificate.

        >>> web_cert = '/var/local/projects/goodcrypto/server/data/web/security/web.ca.crt'
        >>> with open(web_cert) as f:
        ...     get_issuer(f.read())
        '/O=GoodCrypto Private Server Certificate Authority/CN=goodcrypto.private.server.proxy'
    '''
    issuer = None
    try:
        result = sh.openssl('x509', '-noout', '-issuer', _in=cert)
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        m = re.match('issuer=(.*)', result_stdout)
        if m:
            issuer = m.group(1).strip()
        else:
            log('issuer result stdout: {}'.format(result_stdout))
            log('issuer result stderr: {}'.format(result.stderr))
    except:
        log(format_exc())

    return issuer

def get_issued_to(cert):
    '''
        Get to whom an SSL certificate was issued.

        >>> web_cert = '/var/local/projects/goodcrypto/server/data/web/security/web.ca.crt'
        >>> with open(web_cert) as f:
        ...     get_issued_to(f.read())
        '/O=GoodCrypto Private Server Certificate Authority/CN=goodcrypto.private.server.proxy'
    '''
    issued_to = None
    try:
        result = sh.openssl('x509', '-noout', '-subject', _in=cert)
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        m = re.match('subject=(.*)', result_stdout)
        if m:
            issued_to = m.group(1).strip()
        else:
            log('issued_to result stdout: {}'.format(result_stdout))
            log('issued_to result stderr: {}'.format(result.stderr))
    except:
        log(format_exc())

    return issued_to

def get_valid_dates(cert):
    '''
        Get the dates an SSL certificate is valid.

        >>> web_cert = '/var/local/projects/goodcrypto/server/data/web/security/web.ca.crt'
        >>> with open(web_cert) as f:
        ...     not_before, not_after = get_valid_dates(f.read())
        ...     not_before is not None
        ...     not_after is not None
        True
        True
    '''
    not_before = not_after = None
    try:
        result = sh.openssl('x509', '-noout', '-dates', _in=cert)
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        m = re.match('notBefore=(.*?)\nnotAfter=(.*)', result_stdout)
        if m:
            not_before = m.group(1).strip()
            not_after = m.group(2).strip()
        else:
            log('dates result stdout: {}'.format(result_stdout))
            log('dates result stderr: {}'.format(result.stderr))
    except:
        log(format_exc())

    return not_before, not_after

def get_hash(cert):
    '''
        Get the hash of an SSL certificate.

        >>> web_cert = '/var/local/projects/goodcrypto/server/data/web/security/web.ca.crt'
        >>> with open(web_cert) as f:
        ...     cert_hash = get_hash(f.read())
        ...     cert_hash is not None
        True
    '''
    cert_hash = None
    try:
        result = sh.openssl('x509', '-noout', '-hash', _in=cert)
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        cert_hash = result_stdout.strip()
    except:
        log(format_exc())

    return cert_hash

def get_fingerprint(cert):
    '''
        Get the MD5 fingerprint of an SSL certificate.

        >>> web_cert = '/var/local/projects/goodcrypto/server/data/web/security/web.ca.crt'
        >>> with open(web_cert) as f:
        ...     fingerprint = get_fingerprint(f.read())
        ...     fingerprint is not None
        True
    '''
    fingerprint = None
    try:
        result = sh.openssl('x509', '-noout', '-fingerprint', _in=cert)
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        m = re.match('SHA1 Fingerprint=(.*)', result_stdout)
        if m:
            fingerprint = m.group(1).strip()
        else:
            log('fingerprint result stdout: {}'.format(result_stdout))
            log('fingerprint result stderr: {}'.format(result.stderr))
    except:
        log(format_exc())

    return fingerprint

def generate_certificate(
  domain, dirname, private_key_name=PRIVATE_KEY, public_cert_name=PUBLIC_CERT, name=None, days=365):
    '''
        Generate a self-signed SSL certficate.

        Writes the public cert to the file dirname/public_cert_name.
        Creates a dir dirname/private. Writes the private key to
        dirname/private/private_key_name.

        >>> generate_certificate('test.domain.com', '/tmp')
    '''

    if name is None:
        name = domain

    log('starting to generate certificate for {}'.format(name))

    if not os.path.exists(dirname):
        os.mkdir(dirname)
        log('created {}'.format(dirname))

    private_dirname = os.path.join(dirname, 'private')
    if not os.path.exists(private_dirname):
        os.mkdir(private_dirname)
        log('created {}'.format(private_dirname))
    try:
        sh.chown('root:ssl-cert', private_dirname)
    except:
        try:
            sh.chown('root:root', private_dirname)
        except:
            pass
    sh.chmod('go-rwx', private_dirname)

    delete_old_cert(domain, dirname, private_key_name, public_cert_name)
    gen_private_key(domain, dirname, private_key_name)
    gen_csr(domain, dirname, name, private_key_name)
    gen_cert(domain, dirname, private_key_name, public_cert_name, days)
    log('created certificate for {}'.format(domain))

def gen_private_key(domain, dirname, private_key_name):
    ''' Generate an openssl private key for the domain. '''

    log('starting to generate private key')

    # remove the following DEBUG lines by 2016-09-30
    OPENSSL_CNF_FILENAME = os.path.join(dirname, 'openssl.cnf') #DEBUG
    log('openssl.cnf exists: {}'.format(os.path.exists(OPENSSL_CNF_FILENAME)))  #DEBUG
    if os.path.exists(OPENSSL_CNF_FILENAME): #DEBUG
        log('openssl.cnf filesize: {}'.format(os.stat(OPENSSL_CNF_FILENAME).st_size)) #DEBUG

    private_key = os.path.join(dirname, 'private', private_key_name)
    temp_private_key = '{}.tmp'.format(private_key)
    kwargs = dict(_clilog=sh_out, _env=minimal_env(), _err=sh_err)

    responses = [
        ('Enter pass phrase for {}:'.format(private_key), 'secret'),
        ('Verifying - Enter pass phrase for {}:'.format(private_key), 'secret'),
        ]

    args = ['genrsa', '-aes256', '-out', private_key, '4096']
    #args = ['genpkey', '-out', private_key, '-outform', 'PEM', '-aes256', '-algorithm', 'rsa', '-pkeyopt', 'rsa_keygen_bits:4096']
    Responder(responses, 'openssl', *args, **kwargs)
    assert os.path.exists(private_key), 'could not generate {}'.format(private_key)

    sh.cp(private_key, temp_private_key)
    responses = [('Enter pass phrase for {}:'.format(temp_private_key), 'secret')]
    args = ['rsa', '-in', temp_private_key, '-out', private_key]
    Responder(responses, 'openssl', *args, **kwargs)
    os.remove(temp_private_key)

def gen_csr(domain, dirname, name, private_key_name):
    ''' Generate an openssl CSR for the domain. '''

    log('starting to generate csr')

    private_key = os.path.join(dirname, 'private', private_key_name)
    csr = os.path.join(dirname, '{}.csr'.format(domain))
    kwargs = dict(_clilog=sh_out, _env=minimal_env(), _err=sh_err)

    responses = [
        ('State or Province Name (full name) [Some-State]:', '.'),
        ('Locality Name (eg, city) []:', '.'),
        ('Organizational Unit Name (eg, section) []:', '.'),
        ('A challenge password []:', ''),
        ('An optional company name []:', ''),
        ('Country Name (2 letter code) [AU]:', '.'),
        ('Email Address []:', '.'),
        ('Common Name (e.g. server FQDN or YOUR name) []:', domain),
        ('Organization Name (eg, company) [Internet Widgits Pty Ltd]:', name),
        ('Enter pass phrase for {}:'.format(private_key), 'secret'),
        ]

    args = ['req', '-new', '-key', private_key, '-out', csr]
    cli_result = Responder(responses, 'openssl', *args, **kwargs).result
    assert os.path.exists(csr), 'could not generate {}'.format(csr)

def gen_cert(domain, dirname, private_key_name, public_cert_name, days):
    ''' Generate the public certificate. '''

    log('generating certificate')

    private_key = os.path.join(dirname, 'private', private_key_name)
    public_cert = os.path.join(dirname, public_cert_name)
    csr = os.path.join(dirname, '{}.csr'.format(domain))

    sh.openssl('x509', '-req', '-days', days, '-in', csr, '-signkey', private_key, '-out', public_cert)
    assert os.path.exists(public_cert), 'could not generate {}'.format(public_cert)
    os.remove(csr)

    # only the owner should be able to read the private key
    sh.chmod('u+r', private_key)
    sh.chmod('u-wx', private_key)
    sh.chmod('go-rwx', private_key)

    # everyone can read the public certificate
    sh.chmod('ugo+r', public_cert)
    sh.chmod('ugo-wx', public_cert)

def delete_old_cert(domain, dirname, private_key_name, public_cert_name):
    log('deleting old certficate files for {}'.format(domain))

    private_key = os.path.join(dirname, 'private', private_key_name)
    if os.path.exists(private_key):
        os.remove(private_key)
    elif os.path.exists(os.path.join(dirname, private_key_name)):
        os.remove(os.path.join(dirname, private_key_name))

    public_cert = os.path.join(dirname, public_cert_name)
    if os.path.exists(public_cert):
        os.remove(public_cert)

    csr = os.path.join(dirname, '{}.csr'.format(domain))
    if os.path.exists(csr):
        os.remove(csr)

def move_private_key(dirname, private_key_name):
    ''' Move the private key to the dirname.

        By default openssl puts private keys in a 'private' subdir. Some
        apps need them in a different dir, such as the dir where the pub
        keys are.
    '''

    private_dir = os.path.join(dirname, 'private')
    private_key_path = os.path.join(private_dir, private_key_name)
    new_private_key_path = os.path.join(dirname, private_key_name)

    with locked():
        sh.mv(private_key_path, new_private_key_path)
        log('moved {} to {}'.format(private_key_path, new_private_key_path))
        # remove openssl's 'private' dir when empty
        if not os.listdir(private_dir):
            sh.rmdir(private_dir)
        log('removed {}'.format(os.path.join(private_dir, private_key_name)))

def get_ca_certs_dir():
    '''
        Get the directory where openssl keeps known certs.

        >>> certs = get_ca_certs_dir()
        >>> if IS_PY2:
        ...     certs == u'/etc/ssl/certs'
        ... else:
        ...     certs == '/etc/ssl/certs'
        True
    '''

    # /etc/ssl/certs is debian standard ca certs dir
    # alternatives include /usr/lib/ssl/certs, etc.
    ca_certs_dir = '/etc/ssl/certs'
    """
    try:
        result = sh.openssl('version', '-d')
        if IS_PY2:
            result_stdout = result.stdout
        else:
            result_stdout = result.stdout.decode()
        m = re.match('OPENSSLDIR: "(.*?)"', result_stdout)
        if m:
            ca_certs_dir = '{}/certs'.format(m.group(1))
    except:
        log(format_exc())
    """

    return ca_certs_dir

def sh_out(output):
    log.debug(output.rstrip())

def sh_err(output):
    log.warning('STDERR {}'.format(output.rstrip()))


if __name__ == "__main__":
    import doctest
    doctest.testmod()

