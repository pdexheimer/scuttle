#!/usr/bin/env python

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

from argparse import ArgumentParser
from commands import command as cmd, select, describe, annotate
import functools
import logging.config
import os
import scanpy as sc

logConfig = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(levelname)s %(asctime)s] %(message)s',
            'datefmt': '%H:%M:%S %Y-%m-%d'
        }
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['default']
    }
}

global_options = [
    cmd.CommandLineOption('--input', '-i', destvar='input'),
    cmd.CommandLineOption('--output', '-o', destvar='output'),
    cmd.CommandLineOption('--input-format', destvar='input_format', choices=['h5ad', '10x', 'loom'], default='h5ad'),
    cmd.CommandLineOption('--output-format', destvar='output_format', choices=['h5ad', 'loom'], default='h5ad'),
    cmd.CommandLineOption('--no-write', destvar='write', action='store_false'),
    cmd.CommandLineOption('--no-compress', destvar='compress', action='store_false')
]

class SingleCellIO:
    def __init__(self):
        self.loader = lambda filename: None
        self.writer = lambda data, filename: None
        self.input_filename = None
        self.output_filename = None
        self.write_output = True

    def process_args(self, args):
        self.input_filename = args.input
        self.write_output = args.write
        if self.write_output:
            self.output_filename = args.output
            self.writer = self.get_writer(args.output_format, args.compress)
        self.loader = self.get_loader(args.input_format)

    def get_loader(self, input_format):
        if input_format == 'h5ad':
            return sc.read_h5ad
        elif input_format == 'loom':
            return sc.read_loom
        elif input_format == '10x':
            return SingleCellIO.load_10x
        return lambda filename: None
    
    def get_writer(self, output_format, compress):
        if output_format == 'h5ad':
            return functools.partial(SingleCellIO.write_h5ad, compression='gzip' if compress else None)
        elif output_format == 'loom':
            return SingleCellIO.write_loom

    def write_h5ad(data, filename, **kwargs):
        return data.write(filename, **kwargs)
    
    def write_loom(data, filename):
        return data.write_loom(filename)
    
    def load_10x(filename):
        if filename.endswith('.h5'):
            return sc.read_10x_h5(filename)
        else:
            return sc.read_10x_mtx(filename)

    def validate_args(args):
        if args.input_format == 'h5ad':
            SingleCellIO._validate_h5ad_filename(args.input, 'input')
        elif args.input_format == '10x':
            SingleCellIO._validate_10x_filename(args.input, 'input')
        elif args.input_format == 'loom':
            SingleCellIO._validate_loom_filename(args.input, 'input')
        
        if not os.path.exists(args.input):
            logging.critical(f"Input file {args.input} does not exist.  Aborting")
            sys.exit(1)
                
        if args.write:
            if not args.output and args.input_format == 'h5ad':
                args.output = args.input
            if not args.output:
                logging.critical('Must specify an output filename with any input-format that is not h5ad')
                sys.exit(1)
            if args.output_format == 'h5ad':
                SingleCellIO._validate_h5ad_filename(args.output, 'output')
            elif args.output_format == 'loom':
                SingleCellIO._validate_loom_filename(args.output, 'output')
        else:
            if args.output is not None:
                logging.warning('Output file and --no-write specified.  No output will be written')

    def _validate_h5ad_filename(filename, input_or_output):
        if not filename.endswith('.h5ad'):
            logging.critical(f"{input_or_output} file '{filename}' does not have an .h5ad extension.  Change the expected format with --{input_or_output}-format")
            sys.exit(1)

    def _validate_loom_filename(filename, input_or_output):
        if not filename.endswith('.loom'):
            logging.critical(f"{input_or_output} file '{filename}' does not have a .loom extension.  Change the expected format with --{input_or_output}-format")
            sys.exit(1)

    def _validate_10x_filename(filename, input_or_output):
        if not (os.path.isdir(filename) or filename.endswith('.h5')):
            logging.critical(f"{input_or_output} file '{filename}' does not look like a 10x file. It should either be an .h5 file or the directory containing the .mtx file. Change the expected format with --{input_or_output}-format")
            sys.exit(1)

def parse_arguments(scio):
    command_templates = []
    command_templates.extend(select.commands())
    command_templates.extend(describe.commands())
    command_templates.extend(annotate.commands())

    return cmd.parse(command_templates, 
                    cmd.GlobalTemplate(global_options, scio.process_args, SingleCellIO.validate_args))

def main():
    logging.config.dictConfig(logConfig)
    scio = SingleCellIO()
    global_args, command_list = parse_arguments(scio)

    global_args.validate_args()
    for c in command_list:
        c.validate_args()

    global_args.execute()
    data = scio.loader(scio.input_filename)
    for c in command_list:
        c.execute(data)
    scio.writer(data, scio.output_filename)

if __name__ == '__main__':
    main()