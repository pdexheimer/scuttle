"""
This module is responsible for loading the h5ad - either by loading it directly, or importing
it from other sources (ie, 10x output)
"""

import logging
import os.path
import sys
import scanpy as sc

def add_arguments(arg_parser):
    loading_group = arg_parser.add_argument_group('Loading Data')
    loading_group.add_argument('--10x', dest='cellranger', metavar='H5_OR_MTX_DIR',
                                help='Load data from a 10x .h5 file or mtx directory')
    loading_group.add_argument('--overwrite', action='store_true',
                                help='Overwrite the existing h5ad file')
    loading_group.add_argument('--save-as', metavar='FILE', 
                                help='Save to this file rather than overwriting the input file')
    arg_parser.add_argument('file', help='.h5ad file containing data to be modified/viewed.  To create, see "Loading Data"')

def _import_requested(args):
    return args.cellranger != None

def _save(data, filename):
    data.write(filename)

def load_data(args):
    data = None
    if _import_requested(args):
        if os.path.exists(args.file) and not args.overwrite:
            logging.critical('Attempting to overwrite an existing file with new data.  If you really want to do this, use --overwrite', file=sys.stderr)
            exit(1)
        if args.save_as is not None:
            logging.warning('--save-as is incompatible with an import method.  Simply use the default FILE argument')
            args.save_as = None
        if args.cellranger != None:
            if os.path.isfile(args.cellranger):
                data = sc.read_10x_h5(args.cellranger)
            else:
                data = sc.read_10x_mtx(args.cellranger)
    else:
        if not os.path.exists(args.file):
            logging.critical(f"[Can't open {args.file}, file doesn't exist", file=sys.stderr)
            exit(1)
        data = sc.read_h5ad(args.file)
    return data

def save_data(data, args):
    _save(data, args.file if args.save_as is None else args.save_as)