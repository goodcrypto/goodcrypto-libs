'''
    Use openssl to generate a self-signed 4096 RSA cert.
    
    Copyright 2014-2015 GoodCrypto
    Last modified: 2015-04-09
'''
import os, sh
from traceback import format_exc

from syr.cli import minimal_env, Responder
from syr.log import get_log

log = get_log()

PRIVATE_KEY = 'private.key'
PUBLIC_CERT = 'public.crt'

def generate_certificate(
  domain, dirname, private_key_name=PRIVATE_KEY, public_cert_name=PUBLIC_CERT, name=None, days=365):
    '''
        Generate a self-signed SSL certficate.
        
        >>> generate_certificate('test.domain.com', '/tmp')
    '''
    
    if name is None:
        name = domain

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
    
    private_key = os.path.join(dirname, 'private', private_key_name)
    temp_private_key = '{}.tmp'.format(private_key)
    kwargs = dict(_clilog=sh_out, _env=minimal_env(), _err=sh_err)
    
    responses = {
        'Enter pass phrase for {}:'.format(private_key): 'secret',
        'Verifying - Enter pass phrase for {}:'.format(private_key): 'secret',
        }

    args = ['genrsa', '-aes256', '-out', private_key, '4096']
    Responder(responses, 'openssl', *args, **kwargs)
    assert os.path.exists(private_key), 'could not generate {}'.format(private_key)
    
    sh.cp(private_key, temp_private_key)
    responses = {'Enter pass phrase for {}:'.format(temp_private_key): 'secret',}
    args = ['rsa', '-in', temp_private_key, '-out', private_key]
    Responder(responses, 'openssl', *args, **kwargs)
    os.remove(temp_private_key)
    
def gen_csr(domain, dirname, name, private_key_name):
    ''' Generate an openssl CSR for the domain. '''

    log('starting to generate csr')
    
    private_key = os.path.join(dirname, 'private', private_key_name)
    csr = os.path.join(dirname, '{}.csr'.format(domain))
    kwargs = dict(_clilog=sh_out, _env=minimal_env(), _err=sh_err)

    responses = {
        'Enter pass phrase for {}:'.format(private_key): 'secret',
        'Country Name (2 letter code) [AU]:': '.',
        'State or Province Name (full name) [Some-State]:': '.',
        'Locality Name (eg, city) []:': '.',
        'Organization Name (eg, company) [Internet Widgits Pty Ltd]:': '{}'.format(name),
        'Organizational Unit Name (eg, section) []:': '.',
        'Common Name (e.g. server FQDN or YOUR name) []:': '.',
        'Email Address []:': '.',
        'A challenge password []:': '',
        'An optional company name []:': '',
        }

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
    ''' Move the private key to the dirname. '''
    
    sh.mv(os.path.join(dirname, 'private', private_key_name), os.path.join(dirname, private_key_name))
    log('moved {} to {}'.format(os.path.join(dirname, 'private', private_key_name), os.path.join(dirname, private_key_name)))
    sh.rmdir(os.path.join(dirname, 'private'))
    log('removed {}'.format(os.path.join(dirname, 'private', private_key_name)))
    
def sh_out(output):
    log.debug(output.rstrip())

def sh_err(output):
    log.warning('STDERR {}'.format(output.rstrip()))


if __name__ == "__main__":
    import doctest
    doctest.testmod()

