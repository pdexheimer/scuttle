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
Run EmptyDrops!
"""
import logging

import pandas as pd

from scuttle import history
from scuttle.commands import select


def add_to_parser(parser):
    filter_cmd = parser.add_verb('filterempty')
    _add_emptydrops_options(filter_cmd)
    emptydrops = filter_cmd.add_verb('emptydrops')
    _add_emptydrops_options(emptydrops)
    classic = filter_cmd.add_verb('classic')
    _add_classic_options(classic)
    filter_cmd.set_executor(process)


def _add_emptydrops_options(parser):
    """
    Support making the 'emptydrops' specification optional by adding the
    same command line options to the root filterempty and the emptydrops groups
    """
    parser.add_option('--ambient-cutoff', destvar='lower', type=int, default=100)
    parser.add_option('--iters', destvar='iters', type=int, default=10000)
    parser.add_option('--retain-cutoff', destvar='retain', type=int, default=None)
    parser.add_option('--fdr', destvar='fdr', type=float, default=None)
    parser.add_option('--cellranger', destvar='cellranger', action='store_true')
    parser.add_option('--expect-cells', destvar='expect_cells', type=int, default=3000)


def _add_classic_options(parser):
    parser.add_option('--expect-cells', destvar='expect_cells', type=int, default=3000)
    parser.add_option('--upper-quant', destvar='upper_quant', type=float, default=0.99)
    parser.add_option('--lower-prop', destvar='lower_prop', type=float, default=0.1)
    parser.add_option('--keep-all', '-k', destvar='keep', action='store_true')


def process(args, data, **kwargs):
    if args.subcommand is None or args.subcommand == 'emptydrops':
        run_emptydrops(args, data, **kwargs)
    else:
        run_classic(args, data, **kwargs)


def run_emptydrops(args, data, **kwargs):
    from scuttle.r.dropletutils import DropletUtils
    dropletutils = DropletUtils(n_procs=kwargs['n_procs'])
    use_dirichlet = True
    message = 'Running emptyDrops'
    if args.cellranger:
        message = message + ' with CellRanger defaults'
    logging.info(message)
    if args.cellranger:
        args.lower, args.retain = _compute_cr_thresholds(data, args.expect_cells)
        use_dirichlet = False
        args.fdr = 0.01
    result, metadata = dropletutils.emptyDrops(data, lower=args.lower, niters=args.iters,
                                               retain=args.retain, use_dirichlet=use_dirichlet)
    result.index = data.obs_names
    data.obs['emptydrops_fdr'] = result['FDR']
    description = (f"Ran emptyDrops with lower={metadata.rx2('lower')[0]}, alpha={metadata.rx2('alpha')[0]},"
                   f" retain={metadata.rx2('retain')[0]}")
    history.add_history_entry(data, args, description)
    if args.fdr is not None:
        class Arguments:
            pass
        selection = Arguments()
        selection.subcommand = 'cells'
        selection.expression = f'emptydrops_fdr <= {args.fdr}'
        select.process(selection, data)


def run_classic(args, data, **kwargs):
    from scuttle.r.dropletutils import DropletUtils
    dropletutils = DropletUtils(n_procs=kwargs['n_procs'])
    result = dropletutils.classic_filter(data, expect=args.expect_cells, upper_quant=args.upper_quant,
                                         prop=args.lower_prop)
    data.obs['is_cell'] = pd.Series(result, index=data.obs_names)
    history.add_history_entry(data, args, 'Used classic method to identify cells')
    if not args.keep:
        class Arguments:
            pass
        selection = Arguments()
        selection.subcommand = 'cells'
        selection.expression = 'is_cell == 1'
        select.process(selection, data)


def _compute_cr_thresholds(data, expect):
    """
    Compute the two emptyDrops thresholds (lower and retain) that
    CellRanger has automagic for
    """
    total_umis = pd.Series(data.X.sum(axis=1).getA1(), data.obs_names)
    total_umis.sort_values(ascending=False, inplace=True)
    upper_value = total_umis[int(expect * 0.01)] / 10
    empty_bc = total_umis[45000:90000]
    lower_value = empty_bc.max()
    return lower_value, upper_value
