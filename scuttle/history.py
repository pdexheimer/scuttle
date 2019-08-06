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
Manages and writes history information to the h5ad
"""

import datetime
import getpass
import logging
import platform

import numpy as np
from numpy.lib import recfunctions as rfn
from pkg_resources import DistributionNotFound, get_distribution

_dirty_history = False

# Note that, as of version 0.6.22, anndata does not properly save pandas dataframes to uns:
# https://github.com/theislab/anndata/issues/134
# So as a workaround, we'll use numpy record arrays (which are actually read as plain old structured arrays)


def blank_entry():
    try:
        version = get_distribution('scuttle').version
    except DistributionNotFound:
        version = '[Unknown]'
    return np.rec.fromarrays([
        (platform.node(),),
        (getpass.getuser(),),
        (platform.python_version(),),
        (platform.platform(aliased=True, terse=True),),
        (datetime.datetime.now().ctime(),),
        (version,)
    ], names=('hostname', 'user', 'python', 'operating_system', 'timestamp', 'version'))


def add_history_entry(data, args, description):
    global _dirty_history
    logging.info(description)
    _dirty_history = True
    entry = rfn.append_fields(blank_entry(), ('parameters', 'description'), [(repr(vars(args)),), (description,)])
    if 'history' in data.uns_keys():
        data.uns['history'] = rfn.stack_arrays((entry, data.uns['history']), usemask=False, autoconvert=True)
    else:
        data.uns['history'] = entry


def set_parameter(data, algorithm, key, value):
    if algorithm not in data.uns_keys():
        data.uns[algorithm] = {}
    data.uns[algorithm][key] = value


def has_file_changed():
    global _dirty_history
    return _dirty_history
