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
readwrite.py - This module is responsible for all import into scuttle, as well as saving h5ad files
"""

import logging
import os.path

import pandas as pd
import scanpy as sc

from scuttle import history


class ScuttleIO:
    """
    Encapsulates the argument parsing and delegation of reading/writing
    """
    def __init__(self):
        self.input_filename = None
        self.output_filename = None
        self.input_format = None
        self.write_output = True
        self.compress_output = True
        self.args = None

    @staticmethod
    def add_options_to_parser(parser):
        parser.add_global_option('--input', '-i', destvar='input')
        parser.add_global_option('--output', '-o', destvar='output')
        parser.add_global_option('--input-format', destvar='input_format',
                                 choices=['h5ad', '10x', 'loom', 'mtx', 'mex', 'bustools-count'],
                                 default='h5ad')
        parser.add_global_option('--no-write', destvar='write', action='store_false')
        parser.add_global_option('--no-compress', destvar='compress', action='store_false')

    def process_arguments(self, args):
        self.args = args
        self.input_filename = args.input
        self.input_format = args.input_format
        self.write_output = args.write
        if self.write_output:
            self.output_filename = args.output
            self.compress_output = args.compress

    def load_data(self):
        logging.info(f'Loading {self.input_filename} ({self.input_format} format)')
        data = self._load()
        if self.input_format != 'h5ad':
            description = (f'Imported {self.input_format} data from {os.path.abspath(self.input_filename)}'
                           f' ({data.n_obs} cells x {data.n_vars} genes)')
            history.add_history_entry(data, self.args, description)
        logging.info(f'Loaded {data.n_obs} cells and {data.n_vars} genes')
        return data

    def save_data(self, data):
        if not self.write_output:
            return
        logging.info(f'Saving {data.n_obs} cells and {data.n_vars} genes to {self.output_filename}')
        data.write(self.output_filename, compression='gzip' if self.compress_output else None)

    def canonical_filename(self):
        return self.output_filename if self.write_output else self.input_filename

    def _load(self):
        if self.input_format == 'h5ad':
            return sc.read_h5ad(self.input_filename)
        elif self.input_format == 'loom':
            return sc.read_loom(self.input_filename)
        elif self.input_format == '10x':
            return self._load_10x()
        elif self.input_format == 'mtx' or self.input_format == 'mex':
            return sc.read_mtx(self.input_filename)
        elif self.input_format == 'bustools-count':
            return self._load_bustools_count()
        return None

    def _load_10x(self):
        data = sc.read_10x_h5(self.input_filename) if (
            self.input_filename.endswith('.h5')) else (
            sc.read_10x_mtx(self.input_filename))
        data.var_names_make_unique()
        return data

    def _load_bustools_count(self):
        data = sc.read_mtx(self.input_filename + '.mtx')
        data.var = pd.read_csv(self.input_filename + '.genes.txt', sep='\t', header=None, index_col=0)
        data.obs = pd.read_csv(self.input_filename + '.barcodes.txt', sep='\t', header=None, index_col=0)
        return data

    @staticmethod
    def validate_args(args):
        if args.input is None:
            logging.critical('Input file must be specified with -i')
            exit(1)

        if args.input_format == 'h5ad':
            ScuttleIO._validate_h5ad_filename(args.input, 'input')
        elif args.input_format == '10x':
            ScuttleIO._validate_10x_filename(args.input, 'input')
        elif args.input_format == 'loom':
            ScuttleIO._validate_loom_filename(args.input, 'input')
        elif args.input_format == 'bustools-count':
            ScuttleIO._validate_bustools_filename(args.input)

        if args.input_format != 'bustools-count' and not os.path.exists(args.input):
            logging.critical(f'Input file {args.input} does not exist.  Aborting')
            exit(1)

        if args.write:
            if not args.output and args.input_format == 'h5ad':
                args.output = args.input
            if not args.output:
                logging.critical('Must specify an output filename with any input-format that is not h5ad')
                exit(1)
            ScuttleIO._validate_h5ad_filename(args.output, 'output')
        else:
            if args.output is not None:
                logging.warning('Output file and --no-write specified.  No output will be written')

    @staticmethod
    def _validate_h5ad_filename(filename, input_or_output):
        if not filename.endswith('.h5ad'):
            logging.critical(f"{input_or_output} file '{filename}' does not have an .h5ad extension."
                             f' Change the expected format with --{input_or_output}-format')
            exit(1)

    @staticmethod
    def _validate_loom_filename(filename, input_or_output):
        if not filename.endswith('.loom'):
            logging.critical(f"{input_or_output} file '{filename}' does not have a .loom extension."
                             f' Change the expected format with --{input_or_output}-format')
            exit(1)

    @staticmethod
    def _validate_10x_filename(filename, input_or_output):
        if not (os.path.isdir(filename) or filename.endswith('.h5')):
            logging.critical(f"{input_or_output} file '{filename}' does not look like a 10x file."
                             f' It should either be an .h5 file or the directory containing the .mtx file.'
                             f' Change the expected format with --{input_or_output}-format')
            exit(1)

    @staticmethod
    def _validate_bustools_filename(basename):
        if not all([
            os.path.exists(basename + '.mtx'),
            os.path.exists(basename + '.genes.txt'),
            os.path.exists(basename + '.barcodes.txt')
        ]):
            logging.critical(f"'{basename}' does not look like the parameter given to 'bustools count -o'."
                             f' At least one of the mtx, genes.txt, or barcodes.txt files does not exist')
            exit(1)
