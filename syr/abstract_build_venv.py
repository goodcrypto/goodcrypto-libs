#!/usr/bin/env python
'''
    Build virtualenv for goodcrypto box.
    
    Copyright 2013-2014 GoodCrypto
    Last modified: 2014-01-13

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
import os, sh
    
from abc import ABCMeta, abstractmethod
from syr.log import get_log
from syr.ve import venv


class AbstractBuildVenv(object):
    ''' Build the virtualenv for a site.
    
        Each site should inherit from this abstract class with details about their environment.
    '''
    
    __metaclass__ = ABCMeta

    PROJECTS_DIR = '/var/local/projects'
    VIRTUAL_SUBDIR = 'virtualenv'

    def __init__(self):
        self.log = get_log()

    def build(self):
        
        self.change_to_parent_dir()
        self.init_virtualenv()
        print('created {}'.format(self.virtualenv_dir()))

        if self.virtualenv_dir_exists():
            os.chdir(self.VIRTUAL_SUBDIR)
            self.link_supervisord_files()
            print('linked supervisord')
            
            # activate the virtualenv
            with venv(dirname=self.virtualenv_dir()):
                print('configuring virtualenv')

                """
                # start by getting a faster version of pip
                print('   installing pip-accel')
                sh.pip('install', 'pip-accel')
            
                # set up the basic package requirements
                print('   installing package requirements')
                try:
                    # sh.pip('install', '-r', self.get_requirements())
                    for requirement in self.get_requirements():
                        print('     {}'.format(requirement))
                        sh.pip('install', requirement)
                except Exception as exc:
                    print(exc.stdout)
                    print(exc.stderr)
                    #raise
                """
                
                #print('   linking pip and python')
                #self.link_pip2pip_accel()
            
                os.chdir('lib')
                sh.ln('-s', 'python2.7', 'python')
                
                print('   linking our packages')
                os.chdir('python/site-packages')
                self.link_packages()

            self.finish_build()
            
            print('Finished creating virtualenv')
        else:
            print('!!!Error: Unable to create virtualenv')
            
    @abstractmethod
    def change_to_parent_dir(self):
        ''' Change to the directory where virtualenv will be created. '''
    
    @abstractmethod
    def link_supervisord_files(self):
        ''' Link the supervisord files to the current directory.'''

    @abstractmethod
    def get_requirements(self):
        ''' Return the full path to the virtualenv requirements. '''

    @abstractmethod
    def link_packages(self):
        ''' Link packages to the current directory. '''

    @abstractmethod
    def virtualenv_dir(self):
        ''' Returns the full path to the virtualenv directory. '''
        
    def init_virtualenv(self):
        ''' 
            Initialize the virtualenv.

            Overwrite this function if you want 
            special switches used when running virtualenv.
        '''

        if os.path.exists(self.VIRTUAL_SUBDIR):
            sh.rm('-fr', self.VIRTUAL_SUBDIR)
        sh.virtualenv(self.VIRTUAL_SUBDIR)
        
    def virtualenv_dir_exists(self):
        ''' Return True if the virtualenv directory does exist. '''

        return os.path.exists(self.virtualenv_dir())

    def link_pip2pip_accel(self):
        ''' Configure to use pip-accel whenever pip command is issued.'''
        
        os.chdir('bin')
        
        if os.path.islink('pip'):
            pass

        elif os.path.isfile('pip'):
            if os.path.exists('pip-old'):
                os.remove('pip-old')
            sh.mv('pip', 'pip-old')

            sh.ln('-s', 'pip-accel', 'pip')

        os.chdir('..')
    
    def finish_build(self):
        ''' Overwrite if there are any final steps necessary to create the build.'''
        pass
