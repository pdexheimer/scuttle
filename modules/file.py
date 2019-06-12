"""
This module is responsible for reading and writing data.  While the native format is h5ad,
conversions can be performed using the options in this module
"""

import logging
import os.path
import sys
import scanpy as sc

def add_arguments(arg_parser):
    io_group = arg_parser.add_argument_group('Input/Output')
    io_group.add_argument('--input-format', '-if', default='h5ad',
                        choices=['h5ad', '10x', 'loom'],
                        help='Format of the input data (default: %(default)s)')
    io_group.add_argument('--output-format', '-of', default='h5ad',
                        choices=['h5ad', 'loom'],
                        help='Format to save the output (default: %(default)s)')
    io_group.add_argument('--no-write', action='store_true',
                        help='If specified, no output will be written')
    io_group.add_argument('file', nargs='?', help='File/directory containing the input data')
    io_group.add_argument('output_file', nargs='?',
                        help='Filename to save results to.  If the input format is h5ad and this is not specified, will overwrite the input file')

def validate_args(args):
    if args.input_format == 'h5ad':
        _validate_h5ad_filename(args.file, 'input')
    elif args.input_format == '10x':
        _validate_10x_filename(args.file, 'input')
    elif args.input_format == 'loom':
        _validate_loom_filename(args.file, 'input')
    
    if not os.path.exists(args.file):
        logging.critical(f"Input file {args.file} does not exist.  Aborting")
        sys.exit(1)
    
    if args.no_write:
        if args.output_file:
            logging.warning('Output file and --no-write specified.  No output will be written')
    else:
        if not args.output_file and args.input_format == 'h5ad':
            args.output_file = args.file
        if not args.output_file:
            logging.critical('Must specify an output filename with any input-format that is not h5ad')
            sys.exit(1)
        if args.output_format == 'h5ad':
            _validate_h5ad_filename(args.output_file, 'output')
        elif args.output_format == 'loom':
            _validate_loom_filename(args.output_file, 'output')

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

def load_data(args):
    if args.input_format == 'h5ad':
        return sc.read_h5ad(args.file)
    if args.input_format == 'loom':
        return sc.read_loom(args.file)
    if args.input_format == '10x':
        if args.file.endswith('.h5'):
            return sc.read_10x_h5(args.file)
        else:
            return sc.read_10x_mtx(args.file)
    return None

def save_data(data, args):
    if args.no_write:
        return
    if args.output_format == 'h5ad':
        data.write(args.output_file)
    elif args.output_format == 'loom':
        data.write_loom(args.output_file)
