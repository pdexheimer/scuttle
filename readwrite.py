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
readwrite.py - This module is responsible for all import/export from scuttle
"""

import functools
import logging
import os.path

import scanpy as sc

import history


class ScuttleIO:
    """
    Encapsulates the argument parsing and delegation of reading/writing
    """
    def __init__(self):
        self.input_filename = None
        self.output_filename = None
        self.input_format = None
        self.output_format = None
        self.write_output = True
        self.compress_output = True
        self.args = None

    @staticmethod
    def add_options_to_parser(parser):
        parser.add_global_option('--input', '-i', destvar='input')
        parser.add_global_option('--output', '-o', destvar='output')
        parser.add_global_option('--input-format', destvar='input_format',
                                 choices=['h5ad', '10x', 'loom'], default='h5ad')
        parser.add_global_option('--output-format', destvar='output_format', choices=['h5ad', 'loom'], default='h5ad')
        parser.add_global_option('--no-write', destvar='write', action='store_false')
        parser.add_global_option('--no-compress', destvar='compress', action='store_false')

    def process_arguments(self, args):
        self.args = args
        self.input_filename = args.input
        self.input_format = args.input_format
        self.write_output = args.write
        if self.write_output:
            self.output_filename = args.output
            self.output_format = args.output_format
            self.compress_output = args.compress

    def load_data(self):
        load = self._get_loader(self.input_format)
        data = load(self.input_filename)
        if self.input_format != 'h5ad':
            description = (f'Imported {self.input_format} data from {os.path.abspath(self.input_filename)}'
                           f' ({data.n_obs} cells x {data.n_vars} genes)')
            history.add_history_entry(data, self.args, description)
        return data

    def save_data(self, data):
        if not self.write_output:
            return
        write = self._get_writer(self.output_format, self.compress_output)
        write(data, self.output_filename)

    def _get_loader(self, input_format):
        if input_format == 'h5ad':
            return sc.read_h5ad
        elif input_format == 'loom':
            return sc.read_loom
        elif input_format == '10x':
            return ScuttleIO._load_10x
        return lambda filename: None

    def _get_writer(self, output_format, compress):
        if output_format == 'h5ad':
            return functools.partial(ScuttleIO._write_h5ad, compression='gzip' if compress else None)
        elif output_format == 'loom':
            return ScuttleIO._write_loom

    @staticmethod
    def _write_h5ad(data, filename, **kwargs):
        return data.write(filename, **kwargs)

    @staticmethod
    def _write_loom(data, filename):
        return data.write_loom(filename)

    @staticmethod
    def _load_10x(filename):
        if filename.endswith('.h5'):
            return sc.read_10x_h5(filename)
        else:
            return sc.read_10x_mtx(filename)

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

        if not os.path.exists(args.input):
            logging.critical(f'Input file {args.input} does not exist.  Aborting')
            exit(1)

        if args.write:
            if not args.output and args.input_format == 'h5ad':
                args.output = args.input
            if not args.output:
                logging.critical('Must specify an output filename with any input-format that is not h5ad')
                exit(1)
            if args.output_format == 'h5ad':
                ScuttleIO._validate_h5ad_filename(args.output, 'output')
            elif args.output_format == 'loom':
                ScuttleIO._validate_loom_filename(args.output, 'output')
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
