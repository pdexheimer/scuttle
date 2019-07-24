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
This module uses the Cellecta viral tags to define clonal lineages among the cells.
"""

import gzip
import logging
import multiprocessing

import numpy as np
import pandas as pd

from . import barcode


def _read_sequence(f):
    if f.readline() == '':
        return None
    seq = f.readline()
    f.readline()
    f.readline()
    return seq


def _extract_r1_barcodes(r1):
    # Read 1 format: [Cell barcode (16bp)][UMI (10bp)][Poly-T]
    if r1[26:30] == 'TTTT':
        return r1[:16], r1[16:26]
    else:
        return 'N/A', 'N/A'


def _extract_r2_barcodes(r2):
    # Read 2 format: [BC14 (14bp)]TGGT[BC30 (30bp)]
    if r2[14:18] == 'TGGT':
        return r2[:14], r2[18:48]
    else:
        return 'N/A', 'N/A'


def _load_tags(filename):
    tags = {}
    with open(filename, 'r') as f:
        for line in f:
            bc_id, seq = line.rstrip().split('\t')
            tags[seq] = bc_id
    return tags


def _next_barcode(read1_fastq, read2_fastq):
    with gzip.open(read1_fastq, 'rt') as r1:
        with gzip.open(read2_fastq, 'rt') as r2:
            while True:
                read1 = _read_sequence(r1)
                read2 = _read_sequence(r2)
                if read1 is None or read2 is None:
                    break
                r1_barcodes = _extract_r1_barcodes(read1)
                if r1_barcodes[0] == 'N/A':
                    continue
                r2_barcodes = _extract_r2_barcodes(read2)
                if r2_barcodes[0] == 'N/A':
                    continue
                yield r1_barcodes + r2_barcodes


def _filter_confident_tags(cell_counts):
    conf_tags = {cell: {bc: count for bc, count in cell_counts[cell].items() if count > 1} for cell in cell_counts}
    return {cell: barcodes for cell, barcodes in conf_tags.items() if len(barcodes) > 0}


def _accumulate_counts(counts):
    result = {}
    for count in counts:
        for cell in count:
            result.setdefault(cell, {})
            for bc in count[cell]:
                result[cell].setdefault(bc, 0)
                result[cell][bc] += count[cell][bc]
    return result


def assign_tags(data, fastqs, bc14_file, bc30_file, cell_suffix, n_proc=-1):
    whitelist = set([cell_bc.rsplit('-', maxsplit=1)[0] for cell_bc in data.obs_names])
    with multiprocessing.Pool(n_proc, barcode.initialize_barcodes, (bc14_file, bc30_file)) as pool:
        cell_counts = _accumulate_counts(pool.imap_unordered(barcode.count,
                                         ((bc,) for bc in _next_barcode(*fastqs) if bc[0] in whitelist),
                                         chunksize=100000))
    cell_counts = _filter_confident_tags(cell_counts)
    doublets = pd.Series(np.zeros(data.obs_names.shape, dtype=np.bool_), index=data.obs_names)
    tags = pd.Series(np.empty(data.obs_names.shape, dtype=str), index=data.obs_names)
    conf_count = 0
    doublet_count = 0
    for cell in cell_counts:
        if len(cell_counts[cell]) > 1:
            doublets[f'{cell}{cell_suffix}'] = 1
            doublet_count += 1
        else:
            tags[f'{cell}{cell_suffix}'] = list(cell_counts[cell])[0]
            conf_count += 1
    data.obs['doublet'] = doublets
    data.obs['tags'] = tags
    logging.info(f'Confidently assigned cells: {conf_count}')
    logging.info(f'Putative_doublets: {doublet_count}')
