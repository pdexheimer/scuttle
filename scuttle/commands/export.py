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
export.py - Export data from scuttle in different formats (ie, not h5ad)
"""

import gzip
import logging
import os
import os.path

import pandas as pd
import scipy.io
from scipy.sparse import issparse


def add_to_parser(parser):
    export_cmd = parser.add_verb('export')
    export_cmd.add_option('--overwrite', destvar='overwrite', action='store_true')
    loom_cmd = export_cmd.add_verb('loom')
    loom_cmd.add_argument('filename')
    mex_cmd = export_cmd.add_verb('mex')
    mex_cmd.add_argument('filename')
    mtx_cmd = export_cmd.add_verb('mtx')
    mtx_cmd.add_argument('filename')
    cells_cmd = export_cmd.add_verb('cells')
    cells_cmd.add_argument('filename')
    genes_cmd = export_cmd.add_verb('genes')
    genes_cmd.add_argument('filename')
    bigmtx_cmd = export_cmd.add_verb('textmatrix')
    bigmtx_cmd.add_argument('filename')
    export_cmd.set_executor(process)
    export_cmd.set_validator(validate)


def process(args, data, **kwargs):
    if args.subcommand == 'loom':
        _save_loom(args.filename, data)
    elif args.subcommand == 'mex' or args.subcommand == 'mtx':
        _save_mex(args.filename, data)
    elif args.subcommand == 'cells':
        _save_cell_metadata(args.filename, data)
    elif args.subcommand == 'genes':
        _save_gene_metadata(args.filename, data)
    elif args.subcommand == 'textmatrix':
        _save_matrix_to_text_file(args.filename, data)


def validate(args):
    if not args.overwrite and (os.path.isfile(args.filename) or os.path.isdir(args.filename)):
        logging.critical(f'Export to {args.filename} failed, file exists.  Rerun with --overwrite')
        exit(1)
    if args.subcommand == 'mex' or args.subcommand == 'mtx':
        args.filename = os.path.abspath(args.filename)


def _save_loom(filename, data):
    logging.info(f"Exporting to loom file '{filename}'")
    data.write_loom(filename)


def _save_mex(filename, data):
    logging.info(f"Saving in Market Exchange Format to directory '{filename}'")
    os.makedirs(filename, exist_ok=True)
    _save_cell_names(os.path.join(filename, 'barcodes.tsv.gz'), data)
    _save_cr_genes(os.path.join(filename, 'features.tsv.gz'), data)
    with gzip.open(os.path.join(filename, 'matrix.mtx.gz'), 'wb') as f:
        scipy.io.mmwrite(f, data.X)


def _save_cell_names(filename, data):
    with gzip.open(filename, 'wt') as f:
        for barcode in data.obs_names:
            f.write(barcode + '\n')


def _save_cr_genes(filename, data):
    has_ids = True
    if 'gene_ids' not in data.var_keys():
        has_ids = False
        logging.warn("There is no 'gene_ids' annotation on gene - downstream programs might be confused")
    has_types = 'feature_types' in data.var_keys()
    with gzip.open(filename, 'wt') as f:
        for gene_name, row in data.var.iterrows():
            gene_id = row['gene_ids'] if has_ids else gene_name
            gene_type = row['feature_types'] if has_types else 'Gene Expression'
            f.write(f'{gene_id}\t{gene_name}\t{gene_type}\n')


def _save_cell_metadata(filename, data):
    logging.info(f'Exporting cell metadata to {filename}')
    data.obs.to_csv(filename, sep='\t', index_label='barcode')


def _save_gene_metadata(filename, data):
    logging.info(f'Exporting gene metadata to {filename}')
    data.var.to_csv(filename, sep='\t', index_label='gene')


def _save_matrix_to_text_file(filename, data):
    logging.info(f'Exporting expression matrix to {filename}.  This might be a very big file')
    df = pd.DataFrame(data.X.toarray() if issparse(data.X) else data.X,
                      index=data.obs_names,
                      columns=data.var_names)
    df.to_csv(filename, sep='\t', index_label='barcode')
