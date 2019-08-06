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
Module for producing any figures requested
"""
import logging

import matplotlib.pyplot as plt
from matplotlib.ticker import EngFormatter
from scipy import stats


def add_to_parser(parser):
    plot_cmd = parser.add_verb('plot')
    br_cmd = plot_cmd.add_verb('barcoderank')
    br_cmd.add_argument('filename')
    test = plot_cmd.add_verb('dispersiontest')
    test.add_option('--alpha', '-a', destvar='alpha')
    test.add_option('--ambient-cutoff', destvar='lower', type=int, default=100)
    test.add_option('--sample', destvar='sample', type=int, default=100)
    test.add_argument('filename')
    plot_cmd.set_executor(process)


def process(args, data, **kwargs):
    if args.subcommand == 'barcoderank':
        barcode_rank(data, args.filename, **kwargs)
    elif args.subcommand == 'dispersiontest':
        run_dispersion_test(args, data, **kwargs)


def barcode_rank(data, filename, **kwargs):
    logging.info(f'Computing Barcode Rank plot')
    if 'emptydrops' in data.uns_keys():
        result = _barcode_rank_emptydrops(data, filename, **kwargs)
    elif 'classic_filter' in data.uns_keys():
        result = _barcode_rank_classic(data, filename, **kwargs)
    else:
        result = _barcode_rank_filtered(data, filename, **kwargs)
    if result:
        logging.info(f"Barcode Rank plot saved to '{filename}'")


def run_dispersion_test(args, data, **kwargs):
    from scuttle.r.dropletutils import DropletUtils
    dropletutils = DropletUtils(n_procs=kwargs['n_procs'])
    use_dirichlet = args.alpha != 'non-dirichlet'
    if use_dirichlet:
        if args.alpha is None:
            logging.info(f'Testing dispersion of ambient p-values from Dirichlet Multinomial distribution, '
                         f'using MLE estimate of alpha')
        else:
            logging.info(f'Testing dispersion of ambient p-values from Dirichlet Multinomial distribution, '
                         f'alpha={args.alpha}')
    else:
        logging.info('Testing dispersion of ambient p-values from Multinomial distribution')
    ambient_p = dropletutils.test_ambient_pval(data, lower=args.lower, use_dirichlet=use_dirichlet,
                                               dirichlet_alpha=args.alpha)
    _, ks_p = stats.kstest(ambient_p.sample(n=args.sample), 'uniform')
    logging.info(f'Dispersion test K-S p-value over {args.sample} barcodes '
                 f'chosen randomly from {len(ambient_p)} ambient barcodes: {ks_p}')
    if ks_p < 0.05:
        logging.warn(f'Chosen parameters do NOT look suitable')
    else:
        logging.info('Chosen parameters seem reasonable')

    logging.info(f'Saving probability plot to {args.filename}')
    fig = plt.figure(figsize=(6, 4), dpi=300)
    stats.probplot(ambient_p, dist='uniform', plot=fig.add_subplot(1, 1, 1))
    fig.savefig(args.filename, dpi='figure')
    plt.close(fig)


def _calculate_ranks(data, lower=100, **kwargs):
    from scuttle.r.dropletutils import DropletUtils
    dropletutils = DropletUtils(n_procs=kwargs['n_procs'])
    ranks, rank_metadata = dropletutils.barcode_ranks(data, lower)
    ranks = ranks.query('total > 0')
    ranks.sort_values('rank', inplace=True)
    knee = rank_metadata.rx2('knee')[0]
    inflect = rank_metadata.rx2('inflection')[0]
    return ranks, knee, inflect


def _annotate_point(ax, ranks, cutoff, label):
    point = ranks.query('total >= @cutoff').tail(1)
    ax.annotate(label, (point['rank'], point['total']), xytext=(60, 90),
                textcoords='offset pixels', arrowprops={'arrowstyle': '->'})


def _barcode_rank_emptydrops(data, filename, **kwargs):
    if 'emptydrops' not in data.uns_keys():
        logging.error('Emptydrops has not been run on this file')
        return False

    # Collect data
    retain = data.uns['emptydrops']['retain']
    lower = data.uns['emptydrops']['lower']
    fdr_cutoff = data.uns['emptydrops']['fdr_cutoff']
    passing_cells = (data.obs['emptydrops_fdr'] <= fdr_cutoff).sum()

    ranks, knee, inflect = _calculate_ranks(data, lower, **kwargs)

    # Manipulate data
    retained = ranks.query('total >= @retain')
    ambient = ranks.query('total <= @lower')
    middle = ranks.query('total <= @retain and total >= @lower')

    # Plot it!
    (fig, ax) = _initialize_log_figure(title=f"{passing_cells:,} called Cells from {kwargs['scuttle_file']}",
                                       xlabel='Barcode Ranks', ylabel='UMI Count')
    ax.plot(retained['rank'], retained['total'], 'k')
    ax.plot(middle['rank'], middle['total'], 'b')
    ax.plot(ambient['rank'], ambient['total'], 'grey')
    _annotate_point(ax, ranks, knee, 'Knee')
    _annotate_point(ax, ranks, inflect, 'Inflection')

    parameter_str = '\n'.join((
        'emptyDrops Parameters',
        f'Lower: {lower}',
        f'Retain: {retain:g}',
        f'FDR Cutoff: {fdr_cutoff}'
    ))
    ax.text(0.05, 0.05, parameter_str, transform=ax.transAxes, fontsize='x-small',
            verticalalignment='bottom', bbox={'boxstyle': 'round', 'facecolor': 'white'})

    fig.savefig(filename, dpi='figure')
    plt.close(fig)
    return True


def _barcode_rank_classic(data, filename, **kwargs):
    if 'classic_filter' not in data.uns_keys():
        logging.error('Classic filtering has not been run on this file')
        return False

    # Collect data
    expect = data.uns['classic_filter']['expect_cells']
    upper_quant = data.uns['classic_filter']['upper_quant']
    lower_prop = data.uns['classic_filter']['lower_prop']
    threshold = data.uns['classic_filter']['threshold']
    passing_cells = (data.obs['total_umis'] >= threshold).sum()

    ranks, knee, inflect = _calculate_ranks(data, 50, **kwargs)

    # Manipulate data
    retained = ranks.query('total >= @threshold')
    discarded = ranks.query('total <= @threshold')

    # Plot it!
    (fig, ax) = _initialize_log_figure(title=f"{passing_cells:,} called Cells from {kwargs['scuttle_file']}",
                                       xlabel='Barcode Ranks', ylabel='UMI Count')
    ax.plot(retained['rank'], retained['total'], 'k')
    ax.plot(discarded['rank'], discarded['total'], 'grey')
    _annotate_point(ax, ranks, knee, 'Knee')
    _annotate_point(ax, ranks, inflect, 'Inflection')

    parameter_str = '\n'.join((
        'classicFilter Parameters',
        f'Expected cells: {expect}',
        f'Upper Quantile: {upper_quant}',
        f'Lower Proportion: {lower_prop}',
        f'Computed Threshold: {threshold}'
    ))
    ax.text(0.05, 0.05, parameter_str, transform=ax.transAxes, fontsize='x-small',
            verticalalignment='bottom', bbox={'boxstyle': 'round', 'facecolor': 'white'})

    fig.savefig(filename, dpi='figure')
    plt.close(fig)
    return True


def _barcode_rank_filtered(data, filename, **kwargs):
    ranks, knee, inflect = _calculate_ranks(data, 50, **kwargs)

    # Plot it!
    (fig, ax) = _initialize_log_figure(title=f"{data.n_obs:,} Cells from {kwargs['scuttle_file']}",
                                       xlabel='Barcode Ranks', ylabel='UMI Count')
    ax.plot(ranks['rank'], ranks['total'], 'k')
    _annotate_point(ax, ranks, knee, 'Knee')
    _annotate_point(ax, ranks, inflect, 'Inflection')

    fig.savefig(filename, dpi='figure')
    plt.close(fig)
    return True


def _initialize_log_figure(title=None, subtitle=None, xlabel=None, ylabel=None):
    """
    Creates a new figure with logged axes, gridlines, tick formatting, and optional labels.

    Returns the (figure, axes) in a tuple
    """
    fig = plt.figure(figsize=(6, 4), dpi=300)
    ax = fig.add_subplot(1, 1, 1)
    if title is not None:
        fig.suptitle(title)
    if subtitle is not None:
        ax.set_title(subtitle)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)
    ax.loglog()
    ax.grid(color='#CCCCCC')
    ax.grid(which='minor', color='#F0F0F0', linewidth=0.5, linestyle='--')
    tick_formatter = EngFormatter(sep='')
    ax.xaxis.set_major_formatter(tick_formatter)
    ax.yaxis.set_major_formatter(tick_formatter)
    return (fig, ax)
