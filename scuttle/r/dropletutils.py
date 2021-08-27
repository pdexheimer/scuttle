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
Interfaces with the DropletUtils R package, specifically the emptyDrops function
"""
import logging

import rpy2.robjects as ro
import rpy2.robjects.packages as rpackages

from scuttle.r import ScuttlR


class DropletUtils(ScuttlR):
    def __init__(self, n_procs):
        super(DropletUtils, self).__init__(3, 6, n_procs=n_procs)
        self.droplet_utils = None
        if not self.is_package_installed('DropletUtils'):
            self.install()
        self.droplet_utils = rpackages.importr('DropletUtils')

    def install(self):
        """
        Installs DropletUtils, which first requires Bioconductor.
        """
        if not self.is_package_installed('BiocManager'):
            self.install_package('BiocManager')
        bioc_manager = rpackages.importr('BiocManager')
        logging.info('Installing Bioconductor')
        bioc_manager.install(ask=False, quiet=True, Ncpus=self.ncpus)
        logging.info('Installing DropletUtils')
        bioc_manager.install('DropletUtils', ask=False, quiet=True, Ncpus=self.ncpus)

    def emptyDrops(self, data, lower=100, niters=10000, retain=None, use_dirichlet=True, dirichlet_alpha=None):
        with ro.conversion.localconverter(self.converter):
            base = rpackages.importr('base')
            s4v = rpackages.importr('S4Vectors')
            if not use_dirichlet:
                dirichlet_alpha = ro.r('1/0')[0]  # Infinity!  I can't find a way to get Inf in rpy2
            raw_result = self.droplet_utils.emptyDrops(data.X.T, lower=lower, niters=niters, retain=retain,
                                                       alpha=dirichlet_alpha, **{'test.ambient': False})
            # raw_result is a DataFrame from the S4Vectors package, not a data.frame from base R
            pandas_result = ro.conversion.rpy2py(base.as_data_frame(raw_result))
            metadata = s4v.metadata(raw_result)
        return pandas_result, metadata

    def classic_filter(self, data, expect=3000, upper_quant=0.99, prop=0.1):
        with ro.conversion.localconverter(self.converter):
            raw_result = self.droplet_utils.defaultDrops(data.X.T, expected=expect, upper_quant=upper_quant,
                                                         lower_prop=prop)
            result = ro.conversion.rpy2py(raw_result)
        return result

    def barcode_ranks(self, data, lower=100):
        with ro.conversion.localconverter(self.converter):
            base = rpackages.importr('base')
            s4v = rpackages.importr('S4Vectors')
            raw_result = self.droplet_utils.barcodeRanks(data.X.T, lower=lower)
            # raw_result is a DataFrame from the S4Vectors package, not a data.frame from base R
            pandas_result = ro.conversion.rpy2py(base.as_data_frame(raw_result))
            metadata = s4v.metadata(raw_result)
        return pandas_result, metadata

    def test_ambient_pval(self, data, lower=100, use_dirichlet=True, dirichlet_alpha=None):
        with ro.conversion.localconverter(self.converter):
            base = rpackages.importr('base')
            if not use_dirichlet:
                dirichlet_alpha = ro.r('1/0')[0]
            elif dirichlet_alpha is not None:
                dirichlet_alpha = float(dirichlet_alpha)
            raw_result = self.droplet_utils.testEmptyDrops(data.X.T, lower=lower, alpha=dirichlet_alpha,
                                                           test_ambient=True)
            pandas_result = ro.conversion.rpy2py(base.as_data_frame(raw_result))
            pandas_result = pandas_result.query('0 < Total <= @lower')
        return pandas_result['PValue']
