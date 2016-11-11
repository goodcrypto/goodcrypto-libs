'''
    Build virtualenv for goodcrypto box.

    Copyright 2013-2016 GoodCrypto
    Last modified: 2016-04-20

    This file is open source, licensed under GPLv3 <http://www.gnu.org/licenses/>.
'''
from __future__ import unicode_literals

import sys
IS_PY2 = sys.version_info[0] == 2

import os, sh

from abc import abstractmethod
from syr.log import get_log
from syr.ve import venv

if IS_PY2:
    from syr.abstract_python2_class import AbstractPythonClass
else:
    from syr.abstract_python3_class import AbstractPythonClass

class AbstractBuildVenv(AbstractPythonClass):
        ''' Build the virtualenv for a site.

            Each site should inherit from this abstract class with details about their environment.
        '''

        if IS_PY2:
            VIRTUAL_SUBDIR = 'virtualenv'
        else:
            VIRTUAL_SUBDIR = 'virtualenv3'

        PROJECTS_DIR = '/var/local/projects'

        def __init__(self):
            self.log = get_log()

        def build(self):

            self.change_to_parent_dir()
            self.init_virtualenv()
            print('created {}'.format(self.virtualenv_dir()))

            if self.virtualenv_dir_exists():
                os.chdir(self.VIRTUAL_SUBDIR)
                if IS_PY2:
                    self.link_supervisord_files()
                    print('linked supervisord')

                # activate the virtualenv
                with venv(dirname=self.virtualenv_dir()):
                    print('configuring virtualenv')

                    os.chdir('lib')
                    if IS_PY2:
                        sh.ln('-s', 'python2.7', 'python')
                    else:
                        sh.ln('-s', 'python3.4', 'python')

                    print('   installing requirements')
                    with open(self.get_requirements()) as f:
                        for line in f.readlines():
                            if len(line.strip()) > 0:
                                print('     {}'.format(line.strip()))
                                if IS_PY2:
                                    sh.pip('install', line.strip())
                                else:
                                    sh.pip3('install', line.strip())

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
            if IS_PY2:
                sh.virtualenv(self.VIRTUAL_SUBDIR)
            else:
                sh.virtualenv('-p', '/usr/bin/python3.4', self.VIRTUAL_SUBDIR)

        def virtualenv_dir_exists(self):
            ''' Return True if the virtualenv directory does exist. '''

            return os.path.exists(self.virtualenv_dir())

        def finish_build(self):
            ''' Overwrite if there are any final steps necessary to create the build.'''
            pass

