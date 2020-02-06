# scuttle - manage and manipulate sc-rna data files
# Copyright (C) 2019 Phillip Dexheimer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Manages the R interface
"""

import logging
import os
import os.path

import rpy2.rinterface_lib.callbacks as callbacks
import rpy2.robjects as robjects
import rpy2.robjects.numpy2ri as numpy2ri
import rpy2.robjects.packages as rpackages
import rpy2.robjects.pandas2ri as pandas2ri
import scipy
from rpy2.robjects.vectors import FloatVector, IntVector


def spMatrixToR(x):
    matrix_pkg = rpackages.importr('Matrix')
    coo_matrix = x.tocoo()
    numpy2ri.activate()
    result = matrix_pkg.sparseMatrix(i=IntVector(coo_matrix.row),
                                     j=IntVector(coo_matrix.col),
                                     x=FloatVector(coo_matrix.data),
                                     dims=IntVector(coo_matrix.shape),
                                     index1=False)
    numpy2ri.deactivate()
    return result


def noneToNull(x):
    return robjects.NULL


class ScuttlR:

    r_lib_path = None
    orig_consolewrite_print = None
    orig_consolewrite_warnerror = None
    console_warning_buffer = []
    console_output_buffer = []
    converter = None

    def __init__(self, required_major=None, required_minor=None, n_procs=-1):
        self.ncpus = n_procs if n_procs > 0 else 1
        if required_major is not None:
            self.verify_r_version(required_major, required_minor)
        self._set_lib_path()
        self._set_r_console_writers()
        if ScuttlR.converter is None:
            ScuttlR.converter = robjects.conversion.Converter('ScuttlR converter')
            ScuttlR.converter.py2rpy.register(scipy.sparse.spmatrix, spMatrixToR)
            ScuttlR.converter.py2rpy.register(type(None), noneToNull)
            ScuttlR.converter = ScuttlR.converter + robjects.default_converter
            ScuttlR.converter = ScuttlR.converter + numpy2ri.converter
            ScuttlR.converter = ScuttlR.converter + pandas2ri.converter

    @classmethod
    def _set_r_console_writers(cls):
        if cls.orig_consolewrite_print is None:
            cls.orig_consolewrite_print = callbacks.consolewrite_print
            callbacks.consolewrite_print = cls._console_print
            cls.orig_consolewrite_warnerror = callbacks.consolewrite_warnerror
            callbacks.consolewrite_warnerror = cls._console_warn

    @staticmethod
    def _console_print(x):
        ScuttlR.console_output_buffer.append(x)
        if '\n' in x:
            output = ''.join(ScuttlR.console_output_buffer).replace('\n', '')
            logging.info('[R console] ' + output)
            ScuttlR.console_output_buffer = []

    @staticmethod
    def _console_warn(x):
        ScuttlR.console_warning_buffer.append(x)
        if '\n' in x:
            output = ''.join(ScuttlR.console_warning_buffer).replace('\n', '')
            logging.warning('[R console] ' + output)
            ScuttlR.console_warning_buffer = []

    @classmethod
    def _make_scuttle_r_lib_directory(cls, r_version=None):
        homedir = os.path.expanduser('~')
        if r_version is None:
            r_version = cls.get_r_version()
        return os.path.join(homedir, '.scuttle', 'R', r_version)

    @classmethod
    def _set_lib_path(cls):
        if cls.r_lib_path is None:
            cls.r_lib_path = cls._make_scuttle_r_lib_directory()
            os.makedirs(cls.r_lib_path, exist_ok=True)
            logging.debug(f'Adding {cls.r_lib_path} to the beginning of the R library path')
            robjects.r['.libPaths'](cls.r_lib_path)

    @staticmethod
    def get_r_version():
        major = robjects.r['R.version'].rx2('major')[0]
        minor = robjects.r['R.version'].rx2('minor')[0]
        logging.debug(f'R version: Major: {major}, Minor: {minor}')
        if '.' in minor:
            # It contains a patchlevel, remove
            pos = minor.rfind('.')
            minor = minor[:pos]
        logging.debug(f'After removing patchlevel, minor is: {minor}')
        return f'{major}.{minor}'

    def verify_r_version(self, required_major, required_minor):
        r_major, r_minor = (int(x) for x in self.get_r_version().split('.'))
        if required_minor is None:
            if r_major < required_major:
                logging.critical(f'R version {r_major}.{r_minor} found, but version {required_major} is required.'
                                 ' Please upgrade.')
                exit(1)
        else:
            if r_major < required_major or (r_major == required_major and r_minor < required_minor):
                logging.critical(f'R version {r_major}.{r_minor} found, but {required_major}.{required_minor}'
                                 ' is required. Please upgrade')
                exit(1)

    def install_package(self, package_name):
        # https://rpy2.github.io/doc/v3.0.x/html/robjects_rpackages.html#installing-removing-r-packages
        utils = rpackages.importr('utils')
        if not self.is_mirror_set():
            utils.chooseCRANmirror(ind=1)
        robjects.r['options'](install_packages_compile_from_source='always')
        logging.info(f'Installing {package_name}')
        utils.install_packages(package_name, quiet=True, Ncpus=self.ncpus)

    def is_mirror_set(self, repo='CRAN'):
        defined_mirror = robjects.r['options']('repos')[0].rx(repo)[0]
        return defined_mirror != '@CRAN@'

    def is_package_installed(self, package):
        return rpackages.isinstalled(package)
