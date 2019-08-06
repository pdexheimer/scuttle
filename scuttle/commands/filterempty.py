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
from scuttle.commands import plot, select


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
    parser.add_option('--fdr', destvar='fdr', type=float, default=0.001)
    parser.add_option('--cellranger', destvar='cellranger', action='store_true')
    parser.add_option('--expect-cells', destvar='expect_cells', type=int, default=3000)
    parser.add_option('--keep-all', '-k', destvar='keep', action='store_true')
    parser.add_option('--plot', destvar='plot')


def _add_classic_options(parser):
    parser.add_option('--expect-cells', destvar='expect_cells', type=int, default=3000)
    parser.add_option('--upper-quant', destvar='upper_quant', type=float, default=0.99)
    parser.add_option('--lower-prop', destvar='lower_prop', type=float, default=0.1)
    parser.add_option('--keep-all', '-k', destvar='keep', action='store_true')
    parser.add_option('--plot', destvar='plot')


def process(args, data, **kwargs):
    if args.subcommand is None or args.subcommand == 'emptydrops':
        run_emptydrops(args, data, **kwargs)
    elif args.subcommand == 'classic':
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
    comp_lower = metadata.rx2('lower')[0]
    comp_alpha = metadata.rx2('alpha')[0]
    comp_retain = metadata.rx2('retain')[0]
    description = (f'Ran emptyDrops with lower={comp_lower}, alpha={comp_alpha},'
                   f' retain={comp_retain}')
    history.add_history_entry(data, args, description)
    history.set_parameter(data, 'emptydrops', 'lower', comp_lower)
    history.set_parameter(data, 'emptydrops', 'alpha', comp_alpha)
    history.set_parameter(data, 'emptydrops', 'retain', comp_retain)
    history.set_parameter(data, 'emptydrops', 'fdr_cutoff', args.fdr)
    if args.plot is not None:
        plot.barcode_rank(data, args.plot, **kwargs)
    if not args.keep:
        class Arguments:
            pass
        selection = Arguments()
        selection.subcommand = 'cells'
        selection.expression = f'emptydrops_fdr <= {args.fdr}'
        select.process(selection, data)


def run_classic(args, data, **kwargs):
    logging.info('Running classic method of empty cell filtering')
    _, threshold = _compute_cr_thresholds(data, args.expect_cells, args.upper_quant, args.lower_prop)
    history.add_history_entry(data, args, f'Used classic method to identify cells, threshold is {threshold}')
    history.set_parameter(data, 'classic_filter', 'expect_cells', args.expect_cells)
    history.set_parameter(data, 'classic_filter', 'upper_quant', args.upper_quant)
    history.set_parameter(data, 'classic_filter', 'lower_prop', args.lower_prop)
    history.set_parameter(data, 'classic_filter', 'threshold', threshold)
    if args.plot is not None:
        plot.barcode_rank(data, args.plot, **kwargs)
    if not args.keep:
        class Arguments:
            pass
        selection = Arguments()
        selection.subcommand = 'cells'
        selection.expression = f'total_umis >= {threshold}'
        select.process(selection, data)


def _compute_cr_thresholds(data, expect, upper_quant=0.99, lower_prop=0.1):
    """
    Compute the two emptyDrops thresholds (lower and retain) that
    CellRanger has automagic for
    """
    if 'total_umis' not in data.obs_keys():
        data.obs['total_umis'] = pd.Series(data.X.sum(axis=1).getA1(), data.obs_names)
    total_umis = data.obs['total_umis'].sort_values(ascending=False)
    upper_value = total_umis[int(expect * (1 - upper_quant))] * lower_prop
    if len(total_umis) >= 45000:
        lower_value = total_umis[44999]
    else:
        # CellRanger creates the ambient profile from barcodes 45000-90000
        # If we don't have that many, just set it to 1
        lower_value = 1
    return lower_value, upper_value
