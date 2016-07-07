'''
    Use openssl to generate a self-signed 4096 RSA cert.
    
    Copyright 2014-2015 GoodCrypto
    Last modified: 2015-07-02
'''
import os, sh
from tempfile import gettempdir
from traceback import format_exc
from OpenSSL import crypto
from OpenSSL.SSL import FILETYPE_PEM

from syr.cli import minimal_env, Responder
from syr.log import get_log
from syr.utils import randint

log = get_log()

PRIVATE_KEY = 'private.key'
PUBLIC_CERT = 'public.crt'

KEY_EXT = '.key'
CERT_SUFFIX = '.pem'
DEFAULT_CA_NAME = 'ca.mitm.com'
DEFAULT_CA_FILE = 'ca{}'.format(CERT_SUFFIX)
TEMP_CERT_PREFIX = '.pymp_'

class CertAuthority(object):
    ''' Manage certs via openssl. '''

    def __init__(self, ca_name=None, ca_file=None, cache_dir=None, ca_domain=None):
        self.ca_name = ca_name or DEFAULT_CA_NAME
        self.ca_file = ca_file or DEFAULT_CA_FILE
        self.ca_domain = ca_domain or DEFAULT_CA_NAME
        log.debug('ca cert file {}'.format(self.ca_file))
        self.cache_dir = cache_dir or gettempdir()
        self._get_serials()
        if os.path.exists(self.ca_file):
            self.cert, self.key = self._read_ca(self.ca_file)
            self._serials.add(self.cert.get_serial_number())
        else:
            self._generate_ca()

    def _get_serials(self):
        ''' Get the set of web site serial numbers. '''
        
        self._serials = set() 
        
        # existing website certificates
        # log.debug('cache dir:\n    {}'.format('\n    '.join(os.listdir(self.cache_dir))))
        for cert_filename in filter(lambda cert_path: 
            cert_path.startswith(TEMP_CERT_PREFIX) and cert_path.endswith(CERT_SUFFIX), 
            os.listdir(self.cache_dir)):
        
            cert_path = os.path.join(self.cache_dir, cert_filename)
            log.debug('existing web site cert path {}'.format(cert_path))
            cert = load_certificate(FILETYPE_PEM, open(cert_path).read())
            sc = cert.get_serial_number()
            assert sc not in self._serials
            self._serials.add(sc)
            log.debug('existing web site cert path {} has serial {}'.
                format(cert_path, cert.get_serial_number()))
            del cert
            
        # ca certs are added to the set separately

    def _generate_ca(self):
        ''' Generate certificate authority's own certificate '''
        
        # Generate key
        self.key = self._gen_key()

        self.cert = crypto.X509()
        self.cert.set_version(3)
        
        self.cert.set_serial_number(self._new_serial())
        self._serials.add(self.cert.get_serial_number())         
        log.debug('ca cert has serial {}'.format(self.cert.get_serial_number()))
        
        self.cert.get_subject().CN = self.ca_name
        self.cert.gmtime_adj_notBefore(0)
        self.cert.gmtime_adj_notAfter(315360000)
        self.cert.set_issuer(self.cert.get_subject())
        self.cert.set_pubkey(self.key)
        self.cert.add_extensions([
            crypto.X509Extension("basicConstraints", True, "CA:TRUE, pathlen:0"),
            crypto.X509Extension("keyUsage", True, "keyCertSign, cRLSign"),
            crypto.X509Extension("subjectKeyIdentifier", False, "hash", subject=self.cert),
            ])
        """
        # the subjectKeyIdentifier must be set before calculating the authorityKeyIdentifier
        self.cert.add_extensions([
            crypto.X509Extension("authorityKeyIdentifier", False, "keyid:always", issuer=self.cert),
            ])
        """
        # sha1 is crap. do we really need it for compatibility? 
        self.cert.sign(self.key, "sha1")

        self.write_ca(self.ca_file, self.cert, self.key)
        log.debug('wrote ca cert to {}'.format(self.ca_file))
 
    def _gen_key(self):
        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 4096)
        
        return key

    def _read_ca(self, file):
        ''' Read a ca cert and key from file '''
        
        cert = crypto.load_certificate(FILETYPE_PEM, open(file).read())
        key = crypto.load_privatekey(FILETYPE_PEM, open(file+KEY_EXT).read())
        
        return cert, key

    def write_ca(self, cert_file, cert, key):
        ''' Write the certificate and key in separate files for security. '''

        with open(cert_file, 'wb+') as f:
            f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
        os.chmod(cert_file, 0644)
        with open(cert_file+KEY_EXT, 'wb+') as f:
            f.write(crypto.dump_privatekey(FILETYPE_PEM, key))
        os.chmod(cert_file+KEY_EXT, 0600)

    def create_signed_cert(self, cn):
        ''' Create new web site certificate signed by our certificate authority '''
        
        cert_path = os.path.sep.join(
            [self.cache_dir, 
            '{}{}{}'.format(TEMP_CERT_PREFIX, cn, CERT_SUFFIX)])
        if not os.path.exists(cert_path):
            # create certificate
            key = self._gen_key()

            # Generate CSR
            req = crypto.X509Req()
            req.get_subject().CN = cn
            req.set_pubkey(key)
            req.sign(key, 'sha1')

            # Sign CSR
            cert = crypto.X509()
            cert.set_subject(req.get_subject())
            cert.set_serial_number(self._new_serial())         
            log.debug('web site cert for {} has serial {}'.
                format(cn, cert.get_serial_number()))
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(31536000)
            cert.set_issuer(self.cert.get_subject())
            cert.set_pubkey(req.get_pubkey())
            cert.sign(self.key, 'sha1')

            # the remote website's certificate and key must be stored together in a temporary file
            with open(cert_path, 'wb+') as f:
                f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
                f.write(crypto.dump_privatekey(FILETYPE_PEM, key))
            assert os.path.exists(cert_path)
            log.debug('wrote {} web site cert to {}'.
                format(cn, cert_path))

        return cert_path

    def _new_serial(self):
        ''' Return an unused serial number '''
        
        # !! what is the range of a cert serial?
        MAXSERIAL = 1000000
        
        s = randint(1, MAXSERIAL)
        while s in self._serials:
            log.debug('serial {} already exists'.format(s))
            s = randint(1, MAXSERIAL)
        self._serials.add(s)
        
        log.debug('new serial {}'.format(s))
            
        return s

class CertificateAuthority(object):
    '''
        
    '''

    def __init__(self, ca_name=None, ca_file=None, cache_dir=None):
        '''
            >>> ca = CertificateAuthority()
            >>> ca.ca_name
            'ca.mitm.com'
            >>> ca.ca_file
            'ca.pem'
            >>> ca.cache_dir == gettempdir()
            True
            >>> ca._serials is not None
            True
            >>> os.path.exists(ca.ca_file)
            True
            >>> ca.cert is not None
            True
            >>> ca.key is not None
            True
            >>> os.remove(ca.ca_file)
            >>> os.remove(ca.ca_file+'.key')
        '''
        self.ca_name = ca_name or DEFAULT_CA_NAME
        self.ca_file = ca_file or DEFAULT_CA_FILE
        log.debug('ca cert file {}'.format(self.ca_file))
        self.cache_dir = cache_dir or gettempdir()
        self._get_serials()
        if os.path.exists(self.ca_file):
            self.cert, self.key = self._read_ca(self.ca_file)
            self._serials.add(self.cert.get_serial_number())
        else:
            self._generate_ca()

    def _get_serials(self):
        ''' Get the set of web site serial numbers.'''
        
        self._serials = set() 
        
        # existing website certificates
        # log.debug('cache dir:\n    {}'.format('\n    '.join(os.listdir(self.cache_dir))))
        for cert_filename in filter(lambda cert_path: 
            cert_path.startswith(TEMP_CERT_PREFIX) and cert_path.endswith(CERT_SUFFIX), 
            os.listdir(self.cache_dir)):
        
            cert_path = os.path.join(self.cache_dir, cert_filename)
            log.debug('existing web site cert path {}'.format(cert_path))
            cert = load_certificate(FILETYPE_PEM, open(cert_path).read())
            sc = cert.get_serial_number()
            assert sc not in self._serials
            self._serials.add(sc)
            log.debug('existing web site cert path {} has serial {}'.
                format(cert_path, cert.get_serial_number()))
            del cert
            
        # ca certs are added to the set separately

    def _generate_ca(self):
        ''' 
            Generate certificate authority's own certificate 
            
            >>> ca = CertificateAuthority(
            ...       ca_name='My Certificate Authority', ca_file='my.ca.crt')
            >>> key = ca.key
            >>> cert = ca.cert
            >>> ca._generate_ca()
            >>> os.path.exists('my.ca.crt')
            True
            >>> os.path.exists('my.ca.crt.key')
            True
            >>> key != ca.key
            True
            >>> cert != ca.cert
            True
            >>> os.remove('my.ca.crt')
            >>> os.remove('my.ca.crt.key')
        '''

        # Generate key
        self.key = self._gen_key()

        self.cert = crypto.X509()
        self.cert.set_version(3)
        
        self.cert.set_serial_number(self._new_serial())
        self._serials.add(self.cert.get_serial_number())         
        log.debug('ca cert has serial {}'.format(self.cert.get_serial_number()))
        
        self.cert.get_subject().CN = self.ca_name
        self.cert.gmtime_adj_notBefore(0)
        self.cert.gmtime_adj_notAfter(315360000)
        self.cert.set_issuer(self.cert.get_subject())
        self.cert.set_pubkey(self.key)
        self.cert.add_extensions([
            crypto.X509Extension("basicConstraints", True, "CA:TRUE, pathlen:0"),
            crypto.X509Extension("keyUsage", True, "keyCertSign, cRLSign"),
            crypto.X509Extension("subjectKeyIdentifier", False, "hash", subject=self.cert),
            ])
        """
        # the subjectKeyIdentifier must be set before calculating the authorityKeyIdentifier
        self.cert.add_extensions([
            crypto.X509Extension("authorityKeyIdentifier", False, "keyid:always", issuer=self.cert),
            ])
        """
        # sha1 is crap. do we really need it for compatibility? 
        self.cert.sign(self.key, "sha1")

        self.write_ca(self.ca_file, self.cert, self.key)
        log.debug('wrote ca cert to {}'.format(self.ca_file))
 
    def _gen_key(self):
        '''
            Generate a key.
            
            >>> ca = CertificateAuthority()
            >>> key = ca._gen_key()
            >>> key is not None
            True
            >>> os.remove(ca.ca_file)
            >>> os.remove(ca.ca_file+'.key')
        '''
        # Generate key
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 4096)
        
        return key

    def _read_ca(self, file):
        '''
            Read a ca cert and key from file 
            
            >>> ca = CertificateAuthority()
            >>> cert, key = ca._read_ca(ca.ca_file)
            >>> cert is not None
            True
            >>> key is not None
            True
            >>> os.remove(ca.ca_file)
            >>> os.remove(ca.ca_file+'.key')
        '''
        
        cert = crypto.load_certificate(FILETYPE_PEM, open(file).read())
        key = crypto.load_privatekey(FILETYPE_PEM, open(file+KEY_EXT).read())
        
        return cert, key

    def write_ca(self, cert_file, cert, key):
        ''' 
            Write the certificate and key in separate files for security. 

            >>> ca = CertificateAuthority()
            >>> cert, key = ca._read_ca(ca.ca_file)
            >>> ca.write_ca(ca.ca_file, cert, key)
            >>> os.path.exists(ca.ca_file)
            True
            >>> os.path.exists(ca.ca_file+'.key')
            True
            >>> os.remove(ca.ca_file)
            >>> os.remove(ca.ca_file+'.key')
        '''

        with open(cert_file, 'wb+') as f:
            f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
        os.chmod(cert_file, 0644)
        with open(cert_file+KEY_EXT, 'wb+') as f:
            f.write(crypto.dump_privatekey(FILETYPE_PEM, key))
        os.chmod(cert_file+KEY_EXT, 0600)

    def __getitem__(self, cn):
        ''' 
            Create new web site certificate signed by our certificate authority.

            <<< ca = CertificateAuthority()
            <<< with open(ca.ca_file) as f:
            ...     cert_path = ca.__getitem__(ca.cert)
            ...     os.path.exists(cert_path)
            True
            <<< os.remove(ca.ca_file)
            <<< os.remove(ca.ca_file+'.key')
        '''
        
        cert_path = os.path.sep.join(
            [self.cache_dir, 
            '{}{}{}'.format(TEMP_CERT_PREFIX, cn, CERT_SUFFIX)])
        if not os.path.exists(cert_path):
            # create certificate
            key = self._gen_key()

            # Generate CSR
            req = crypto.X509Req()
            req.get_subject().CN = cn
            req.set_pubkey(key)
            req.sign(key, 'sha1')

            # Sign CSR
            cert = crypto.X509()
            cert.set_subject(req.get_subject())
            cert.set_serial_number(self._new_serial())         
            log.debug('web site cert for {} has serial {}'.
                format(cn, cert.get_serial_number()))
            cert.gmtime_adj_notBefore(0)
            cert.gmtime_adj_notAfter(31536000)
            cert.set_issuer(self.cert.get_subject())
            cert.set_pubkey(req.get_pubkey())
            cert.sign(self.key, 'sha1')

            # the remote website's certificate and key must be stored together in a temporary file
            with open(cert_path, 'wb+') as f:
                f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
                f.write(crypto.dump_privatekey(FILETYPE_PEM, key))
            assert os.path.exists(cert_path)
            log.debug('wrote {} web site cert to {}'.
                format(cn, cert_path))

        return cert_path

    def _new_serial(self):
        ''' 
            Return an unused serial number 
            
            >>> ca = CertificateAuthority()
            >>> s = ca._new_serial()
            >>> s is not None
            True
        '''
        
        # !! what is the range of a cert serial?
        MAXSERIAL = 1000000
        
        s = randint(1, MAXSERIAL)
        while s in self._serials:
            log.debug('serial {} already exists'.format(s))
            s = randint(1, MAXSERIAL)
        self._serials.add(s)
        
        log.debug('new serial {}'.format(s))
            
        return s

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
        'Common Name (e.g. server FQDN or YOUR name) []:': '{}'.format(domain),
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

