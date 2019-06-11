"""
This module uses the Cellecta viral tags to define clonal lineages among the cells.
"""

import gzip
import Levenshtein
import multiprocessing
import pandas as pd
import numpy as np
import sys
from . import count_bc

def add_arguments(arg_parser):
    viral_tag_group = arg_parser.add_argument_group('Cellecta Viral Tag Processing')
    viral_tag_group.add_argument('--cellecta-fastqs', nargs=2, metavar=('FASTQ1', 'FASTQ2'),
                                help='Two fastqs (read 1 & 2) representing the viraltag library')
    viral_tag_group.add_argument('--bc14-file', help='A tab separated file where the first column is the barcode ID and the second is the sequence')
    viral_tag_group.add_argument('--bc30-file', help='A tab separated file where the first column is the barcode ID and the second is the sequence')

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

def _error_correct(sequence, tags):
    # Perfect match
    if sequence in tags:
        return tags[sequence]
    
    # Error correct - it's faster to iterate through all possible tags and check the distance
    # than it is to generate all possible variations of this sequence
    for expected_seq, name in tags.items():
        if Levenshtein.hamming(sequence, expected_seq) < 3:
            return name
    
    # Error correct failed, no idea what this sequence should be
    return None

def _next_barcode(read1_fastq, read2_fastq):
    with gzip.open(read1_fastq, 'rt') as r1:
        with gzip.open(read2_fastq, 'rt') as r2:
            while True:
                read1 = _read_sequence(r1)
                read2 = _read_sequence(r2)
                if read1 == None or read2 == None:
                    break
                r1_barcodes = _extract_r1_barcodes(read1)
                if r1_barcodes[0] == 'N/A':
                    continue
                r2_barcodes = _extract_r2_barcodes(read2)
                if r2_barcodes[0] == 'N/A':
                    continue
                yield r1_barcodes + r2_barcodes

def _filter_confident_tags(cell_counts):
    conf_tags = { cell: { bc: count for bc, count in cell_counts[cell].items() if count > 1 } for cell in cell_counts }
    return { cell: barcodes for cell, barcodes in conf_tags.items() if len(barcodes) > 0 }

def _accumulate_counts(counts):
    result = {}
    for count in counts:
        for cell in count:
            result.setdefault(cell, {})
            for bc in count[cell]:
                result[cell].setdefault(bc, 0)
                result[cell][bc] += count[cell][bc]
    return result

def process(data, args):
    if args.cellecta_fastqs is None:
        return
    whitelist = set([ cell_bc.rsplit('-', maxsplit=1)[0] for cell_bc in data.obs_names ])
    with multiprocessing.Pool(6, count_bc.initialize_barcodes, (args.bc14_file, args.bc30_file)) as pool:
        cell_counts = _accumulate_counts(pool.imap_unordered(count_bc.count,
                        ((bc,) for bc in _next_barcode(*args.cellecta_fastqs) if bc[0] in whitelist),
                        chunksize=100000))
    print("", file=sys.stderr)
    cell_counts = _filter_confident_tags(cell_counts)
    doublets = pd.Series(np.zeros(data.obs_names.shape, dtype=np.bool_), index=data.obs_names)
    tags = pd.Series(np.empty(data.obs_names.shape, dtype=str), index=data.obs_names)
    conf_count = 0
    doublet_count = 0
    for cell in cell_counts:
        if len(cell_counts[cell]) > 1:
            doublets[f'{cell}-1'] = 1
            doublet_count += 1
        else:
            tags[f'{cell}-1'] = list(cell_counts[cell])[0]
            conf_count += 1
    data.obs['doublet'] = doublets
    data.obs['tags'] = tags
    print(f"Confidently assigned cells: {conf_count}", file=sys.stderr)
    print(f"Putative_doublets: {doublet_count}", file=sys.stderr)

def old_process(data, args):
    whitelist = set([ cell_bc.rsplit('-', maxsplit=1)[0] for cell_bc in data.obs_names ])
    error_correction = args.bc14_file != None and args.bc30_file != None
    if error_correction:
        bc14_tags = _load_tags(args.bc14_file)
        bc30_tags = _load_tags(args.bc30_file)
    cell_counts = {}
    for cell, umi, fourteen, thirty in _next_barcode(*args.cellecta_fastqs):
        if cell not in whitelist:
            continue
        if error_correction:
            id14 = _error_correct(fourteen, bc14_tags)
            if id14 == None:
                continue
            id30 = _error_correct(thirty, bc30_tags)
            if id30 == None:
                continue
            barcode = f"{id14}:{id30}"
        else:
            barcode = f"{fourteen}:{thirty}"
        
        # Count reads for each cell/tag combination
        # If this should ever change to a count of UMIs, store the UMIs in a set and take the len at the end
        cell_counts.setdefault(cell, {})
        cell_counts[cell].setdefault(barcode, 0)
        cell_counts[cell][barcode] += 1
    cell_counts = _filter_confident_tags(cell_counts)

    doublets = pd.Series(np.zeros(data.obs_names.shape, dtype=np.bool_), index=data.obs_names)
    tags = pd.Series(np.empty(data.obs_names.shape, dtype=str), index=data.obs_names)
    conf_count = 0
    doublet_count = 0
    for cell in cell_counts:
        if len(cell_counts[cell]) > 1:
            doublets[f'{cell}-1'] = 1
            doublet_count += 1
        else:
            tags[f'{cell}-1'] = list(cell_counts[cell])[0]
            conf_count += 1
    data.obs['doublet'] = doublets
    data.obs['tags'] = tags
    print(f"Confidently assigned cells: {conf_count}", file=sys.stderr)
    print(f"Putative_doublets: {doublet_count}", file=sys.stderr)