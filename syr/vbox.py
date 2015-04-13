#! /usr/bin/env python
'''
    VirtualBox management.
    
    Includes defaults so you don't need to be a virtualbox expert.
    
    This module is for debian stable wheezy and virtualbox 4.1.18-dfsg-2+deb7u3.
    Other os or virtualbox versions may work.
    
    VirtualBox's api is far too volatile. It changes often. The docs are 
    usually behind. So we don't use the api.
    
    VirtualBox's command line interface is better. It is also volatile, 
    usually changing with every significant release. But it's more stable,
    more reliable, and the docs are more likely to be up to date.
    
    To do: Turn goodcrypto.box.utils.ops.create_vm() into a doctest. 
    Maybe using Tails iso?

    References:
        VBoxHeadless - Running Virtual Machines With VirtualBox 4.1 On A Headless CentOS 6.2 Server | HowtoForge - Linux Howtos and Tutorials
            http://www.howtoforge.com/vboxheadless-running-virtual-machines-with-virtualbox-4.1-on-a-headless-centos-6.2-server
        Chapter 8. VBoxManage
            http://www.virtualbox.org/manual/ch08.html

    Copyright 2014 GoodCrypto
    Last modified: 2014-12-04

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''

from __future__ import print_function

import os.path, sh, re

import syr.log, syr.user, syr.utils

log = syr.log.get_log()

class VboxException(Exception):
    pass

def vbox(*args, **kwargs):
    ''' DEPRECATED. Use VirtualMachine(), Storage(), etc.
    
        Run vboxmanage. 
    
        Accepts an 'owner' keyword not supported by vboxmanage.
        If present, vboxmanage is run as the owner user.
        Probably much simpler to:
        
            with syr.user.sudo(owner):
                sh.vboxmanage(...)
    '''
    
    log.warning('vbox() is DEPRECATED')
    log.debug(syr.utils.stacktrace())
    
    if 'owner' in kwargs:
        owner = kwargs['owner']
        del kwargs['owner']
    else:
        owner = False
        
    if owner and syr.user.whoami() != owner:
        with syr.user.sudo(owner):
            result = sh.vboxmanage(*args, **kwargs)
        
    else:
        result = sh.vboxmanage(*args, **kwargs)
    
    return result
    
class Storage(object):
    ''' Virtualbox storage device. '''
    
    DEVICE_NAME = 'SATA Controller'
    DEVICE_TYPE = 'sata'

    def __init__(self, medium, port=None, device=None, storage_type=None):
        ''' Parameters from vboxmanage storageattach. 
        
            'medium' is a filename for a virtual drive or iso.
            If the virtual drive does not exist it will be created.
            An iso file must exist.
        '''
        
        self.medium = medium
        
        # set storage type and port, based on medium
        if self.medium.endswith('.iso'):
            if not os.path.exists(self.medium):
                raise VboxException('file does not exist: {}'.format(self.medium))
            self.storage_type = 'dvddrive'
            self.port = port or 1
            
        else:
            if not os.path.exists(self.medium):
                Storage.create_drive(self.medium)
            self.storage_type = 'hdd'
            self.port = port or 0
            
        self.device = device or 0
                
    def attach(self, vm): #, passthrough=False, forceunmount=False):
        ''' Attach storage to a vm. 
        
            'vm' is a VirtualMachine.
        '''
    
        log.debug('attach storage: {}'.format(self))
        
        # from VBoxHeadless - Running Virtual Machines With VirtualBox 4.1 On A Headless CentOS 6.2 Server | HowtoForge - Linux Howtos and Tutorials
        #      http://www.howtoforge.com/vboxheadless-running-virtual-machines-with-virtualbox-4.1-on-a-headless-centos-6.2-server
        #      $ VBoxManage storageattach "Ubuntu 12.04 Server" --storagectl "IDE Controller" --port 0 --device 0 --type hdd --medium Ubuntu_12_04_Server.vdi
        sh.vboxmanage.storageattach(vm.name, 
            '--storagectl', Storage.DEVICE_NAME, 
            '--port', self.port, 
            '--device', self.device, 
            '--type', self.storage_type, 
            '--medium', self.medium)
    
    def detach(self, vm):
        ''' Detach storage from a vm. 
        
            'vm' is a VirtualMachine.
        '''
                
        # '--medium none' is ridiculous syntax for detaching a drive
        # http://www.1stbyte.com/2011/02/03/how-to-remove-or-detach-dvd-from-virtualbox-machine-using-vboxmanage-command-line/
        # or maybe in place of '--medium none'? different virtualbox versions?
        #   storageattach ... -forceunmount
        #   closemedium ... -delete

        log.debug('detach storage: {}'.format(self))
        sh.vboxmanage.storageattach(vm.name, 
            '--storagectl', Storage.DEVICE_NAME, 
            '--port', self.port, 
            '--device', self.device, 
            '--type', self.storage_type,
            '--medium', 'none',
            )
        
    @staticmethod
    def add_controller(vm):
        ''' Add drive controller. '''
        
        sh.vboxmanage.storagectl(vm.name, '--name', Storage.DEVICE_NAME, '--add', Storage.DEVICE_TYPE)
        
    @staticmethod
    def create_drive(filename, size=10000):
        ''' Create a virtual drive. 
        
            'size' is in MB and defaults to 10000 (10 GB).
        '''
                
        sh.vboxmanage.createhd('--filename', filename, '--size', size)
        
    def __str__(self):
        """Convert to a string."""
        
        result = self.medium
        if self.port:
            result = result = ', port: {}'.format(self.port)
        if self.device:
            result = result = ', device: {}'.format(self.device)
        return result
        
    def __unicode__(self):
        """Convert to a unicode string."""

        return u'%s' % str(self)
        
class NetworkAdapter(object):
    ''' VirtualBox network adapter. '''
    
    # python needs enums
    MODE_NOT_ATTACHED = 'none'      # no networking
    MODE_NULL = 'null'              # only on this guest
    MODE_NAT = 'nat'                # NAT, Network Address Translation
    MODE_BRIDGED = 'bridged'        # Bridged adapter
    MODE_INTERNAL = 'intnet'        # Internal network, only between guests 
    MODE_HOST_ONLY = 'hostonly'     # Host-only adapter, only host and guests
    MODE_GENERIC = 'generic'        # Generic driver
        
    def __init__(self, vm, number=1, name=None, mode=None):
        ''' 'number' is the adapter ID number in the range 1-4.
        
            'name' is a human readable name. Default is None, which is the 
            same as a blank name.
        
            'mode' is the networking mode. It must be None, or one of the
            NetworkAdapter.MODE_* constants. Default is None, which is the 
            same as MODE_NAT, Network Address Translation.
        '''
        
        self.vm = vm
        assert number >= 1 and number <= 4
        self.number = number
        self.name = name
        self.mode = mode or NetworkAdapter.MODE_NAT
        self.device = 'eth{}'.format(self.number - 1)
        
    def create_bridged_interface(self, device):
        ''' UNTESTED. Configure bridged interface,
        
            'device' is the host network interface to use.
            Virtualbox uses a host driver to inject and extract packets 
            directly from the host interface hardware.
            
            Because bridged networking hijacks the host network hardware,
            it is a security risk. But there may not be another 
            way to run some kinds of servers, such as a web server, in
            a Virtualbox vm.
        '''

        """ what we want
        VBoxManage modifyvm testMachine --bridgeadapter1 eth0
        
        support@tester:~$ VBoxManage modifyvm testMachine --nic1 bridged

        support@tester:~$ VBoxManage showvminfo testMachine | grep "NIC 1"
        """
        
        assert self.mode == NetworkAdapter.MODE_BRIDGED
        
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--nic{}'.format(self.number),
            'bridged')
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--bridgeadapter{}'.format(self.number),
            self.device)
            
    def create_host_only_interface(self, name=None, ip=None):
        ''' UNTESTED. Configure host only interface,
        
            'name' is the hostonly config name, and defaults to the device name.
            
            'ip' defaults to dhcp, or is the ip address for the interface.
        '''
        
        log.debug('create host only interface: {}'.format(self))
        assert self.mode == NetworkAdapter.MODE_HOST_ONLY
        
        name = name or self.device
        
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--nic{}'.format(self.number),
            'hostonly')
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--hostonlyadapter{}'.format(self.number),
            self.device)
        
        if ip:
            sh.vboxmanage.hostonlyif.ipconfig(
                name,
                '--ip{}'.format(ip))
        else:
            sh.vboxmanage.hostonlyif.ipconfig(
                name,
                '--dhcp')
        
    def forward_port(self, host_port, guest_port=None, 
        name=None, protocol=None, host_ip=None, guest_ip=None):
        ''' Forward port on host machine to port on guest machine.
            All access to the port on the host, accesses the port on the guest.
        
            Network adapter mode must be NetworkAdapter.MODE_NAT, the default.
            
            'host_port' is the port on the host to use.

            'guest_port' is the port on the guest to forward. Default is host_port.
        
            'name' is a human readable name for the rule. Default is None, 
            which is the same as a blank name.
            
            'protocol' is 'tcp' or 'udp'. Default is None, which is the same 
            as 'tcp'.
            
            'host_ip' is the host ip address. Default is None, which is the 
            same as the current host ip.
        
            Syntax:
                --natpf<1-N> [<name>],tcp|udp,[<hostip>],<hostport>,[<guestip>], <guestport>)
        '''
        
        log.debug('forward port: {} from host {} to guest {}'.
            format(self.vm.name, host_port, guest_port))
        assert self.mode == NetworkAdapter.MODE_NAT
        assert host_port
        
        if guest_port is None:
            guest_port = host_port

        # port forwarding args, which becomes a single comma separated command line arg
        args = []
        args.append(name or '')
        args.append(protocol or 'tcp')
        args.append(host_ip or '')
        args.append(str(host_port))
        args.append(guest_ip or '')
        args.append(str(guest_port))
        cli_arg = ','.join(args)
        
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--natpf{}'.format(self.number),
            cli_arg)

    def delete_port_forwarding_rule(self, name):
        ''' Delete port forwarding rule. 
        
            'name' is a human readable name for the rule.
        '''

        log.debug('delete port forwarding rule: {} {}'.format(self.vm.name, name))
        sh.vboxmanage.modifyvm(
            self.vm.name,
            '--natpf{}'.format(self.number),
            'delete', name)
        
class VirtualMachine(object):
    ''' VirtualBox virtual machine.
    
        >>> assert VirtualMachine.list('vms')
    '''
        
    def __init__(self, name, user_home=None):
        ''' 'name' is the name of the vm.
        
            NOT IMPLEMENTED:
            'user_home' is the VBOX_USER_HOME directory.
            This is the parent directory virtualbox will use.
            It is where will virtualbox will look for or create
            the "VirtualBox VMs" directory, VBoxSVC.log, VirtualBox.xml, etc.
        '''
        
        self.name = name
        
        self.user_home = user_home
        """
        if (self.user_home):
            # !! messy, no restore, last setting wins, etc.
            os.environ['VBOX_USER_HOME'] = self.user_home
        """
        
    def exists(self):
        ''' Return True if vm exists, else False. '''
        
        return self.name in VirtualMachine.vms()
            
    def create_vm(self, force=False, 
        memory=1024, acpi=True, boot=None, nic='nat'): # , bridgeadapter='eth0'):
        ''' Create a vm.
        
            If 'force' is True, delete any existing machine with this name.
            
            'memory' is in megabytes and defaults to 1024 (1 GB).
        '''
        
        log.debug('create vm: {}'.format(self.name))
        if self.exists():
            raise VboxException(
                'Virtual machine "{}" already exists'.
                format(self.name))
        
        self.memory = memory
        self.acpi = acpi
        self.boot = boot
        self.nic = nic
        #self.bridgeadapter = bridgeadapter
        
        if force and self.exists():
            self.remove()
        
        args = ('--name', self.name, '--register')
        try:
            sh.vboxmanage.createvm(*args)
        
        except sh.ErrorReturnCode as erc:
            # if settings file exists and force=True
            settings_file = VirtualMachine.check_settings_file_already_exists(erc)
            if settings_file and force:
                log.warning('during create vm, settings file exists and force is True')
                log.warning('removing settings file: {}'.format(settings_file))
                sh.rm(settings_file)
                sh.vboxmanage.createvm(*args)
                
            else:
                raise
    
        assert self.exists()
        
        # modifyvm args
        args = [
            self.name, 
            '--memory', str(self.memory),
            ]
        # some defaults
        args.extend([
            # security
            '--vrde', 'off',
            '--teleporter', 'off',
            # boot order: dvd/disk
            '--boot1', 'dvd',
            '--boot2', 'disk',
            '--boot3', 'none',
            '--boot4', 'none',
            # leave a little cpu so you can stop a runaway vm
            '--cpuexecutioncap', 95,
            ])
        if self.acpi:
            args.extend(['--acpi', 'on'])
        if self.boot:
            args.extend(['--boot1', self.boot])
        if self.nic:
            args.extend(['--nic1', self.nic])
        #if self.bridgeadapter:
        #    args.extend(['--bridgeadapter1', self.bridgeadapter])
        # log.debug('vboxmanage modifyvm {}'.format(' '.join(args)))
        sh.vboxmanage.modifyvm(*args)

    def start(self, headless=False):
        ''' Start vm. '''
            
        if headless:        
            log.debug('start vm headless: {}'.format(self.name))
            result = sh.vboxmanage.startvm(self.name, type='headless')
        else:        
            log.debug('start vm: {}'.format(self.name))
            result = sh.vboxmanage.startvm(self.name)
        self.check_result(result)
        
        return result
        
    def stop(self):
        ''' Stop vm. 
        
            For virtualbox, this is poweroff.
        '''
        
        log.debug('stop vm: {}'.format(self.name))
        return sh.vboxmanage.controlvm(self.name, 'poweroff')
        
    def reset(self):
        ''' Reset vm. '''
        
        log.debug('reset vm: {}'.format(self.name))
        return sh.vboxmanage.controlvm(self.name, 'reset')

    def is_running(self):
        
        vms = VirtualMachine.running_vms()
        log.debug('looking for "{}" in running vms: "{}"'.format(self.name, vms))
        running = self.name in vms
        log.debug('{} running: "{}"'.format(self.name, running))
        return running
    
    def remove(self, all=False):
        ''' Remove vm. 
        
            If 'all' is True, delete medium files. Default is False.
        '''
        
        log.debug('remove vm: {}'.format(self.name))
        if self.exists():
            try:
                sh.vboxmanage.unregistervm(self.name, '--delete')
            except sh.ErrorReturnCode as erc:
                medium_file = VirtualMachine.check_could_not_delete_medium(erc)
                if medium_file:
                    log.warning('during delete vm, could not delete medium file: {}'.format(medium_file))
                    if not os.path.exists(medium_file):
                        log.debug('during delete vm, medium file does not exist: {}'.format(medium_file))
                        try:
                            Storage(medium_file).detach(self)
                        except sh.ErrorReturnCode as sh_ex:
                            if 'Could not find a registered machine named' in str(sh_ex):
                                log.debug('vm not registered during detach: {}'.
                                    format(medium_file))
                            else:
                                raise
                else:
                    raise
                        
        else:
            log.debug('vm does not exist: {}'.format(self.name))
                
    def check_result(self, result):
        ''' Virtualbox sometimes gets an error but exits with no sh.ErrorReturnCode 
        
            Maybe Virtualbox reports errors just in the text output,
            and returns a successful error code. 
        
            Or it could be that in the sh module:
            
                Signals will not raise an ErrorReturnCode. 
                The command will return as if it succeeded, 
                but its exit_code property will be set to -signal_num. 
                So, for example, if a command is killed with a SIGHUP, 
                its return code will be -1.
        '''
            
        def check_output(stdtype, output):
            if 'VBoxManage: error:' in output:
                raise VboxException('error reported in {}: {}\n{}'.format(
                    stdtype, output.strip(), result.strip()))
            
        if result.exit_code != 0:
            raise VboxException('bad exit code {}: {}'.format(result.exit_code, result.strip()))
            
        check_output('STDOUT', result.stdout)
        
        # waitng for the vm to power on is not an error
        if 'Waiting for VM' in result.stderr and 'to power on...' in result.stderr:
            pass
        else:
            check_output('STDERR', result.stderr)
        
    @staticmethod
    def list(what):
        ''' Get 'vboxmanage list' output as list. 
        
            'what' is a parameter to 'vboxmanage list', e.g. 'vms'.
        '''
        
        # return sh.vboxmanage.list(what).stdout.strip().split('\n')
        command = sh.vboxmanage.list.bake()
        try:
            result = command(what).stdout.strip().split('\n')
        except sh.ErrorReturnCode_1:
            result = []
        log.debug('list {}: {}'.format(what, result))
        return result
        
    @staticmethod
    def vms():
        ''' Get names of vms. Use list('vms') for raw list of vms. '''
        
        raw_vms = VirtualMachine.list('vms')
        return VirtualMachine.vm_names(raw_vms)

    @staticmethod
    def running_vms():
        ''' Get names of running vms. Use list('runningvms') for raw list of vms. '''
        
        raw_vms = VirtualMachine.list('runningvms')
        return VirtualMachine.vm_names(raw_vms)

    @staticmethod
    def vm_names(raw_vms):
        ''' Get list of vm names from raw list of vms. '''
        
        vms = []
        for raw in raw_vms:
            name = raw.strip('"').split('"')[0]
            if name:
                vms.append(name)
        return vms

    @staticmethod
    def check_settings_file_already_exists(erc):
        ''' Checks if vboxmanage error was "Machine settings file already exists". 
        
            'erc' is an sh error return code.
            
            Return False, or settings pathname.
            
            This error can happen when
              * you call create_vm() without first checking exists()  
              * an earlier error occured and VirtualBox did not clean up. 
        '''

        match = re.search(
            "Machine settings file '(.*?)' already exists",
            erc.stderr
            )
        
        if match:
            pathname = match.group(1)
            log.debug('machine settings file already exists: {}'.format(pathname))
            result = pathname
            
        else:
            result = False
            
        return result

    @staticmethod
    def check_could_not_delete_medium(erc):
        ''' Checks if vboxmanage error was "Could not delete the medium storage unit". 
        
            'erc' is an sh error return code.
            
            Return False, or medium pathname.
            
            This error happens when the medium does not exist. 
        '''

        match = re.search(
            "Could not delete the medium storage unit '(.*?)'",
            erc.stderr
            )
        
        if match:
            pathname = match.group(1)
            log.debug('could not delete the medium file: {}'.format(pathname))
            result = pathname
            
        else:
            result = False
            
        return result

if __name__ == "__main__":
    import doctest
    doctest.testmod()
    
