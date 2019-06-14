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
Manage cell/gene annotations - add from external sources, etc
"""

import logging
import pandas as pd

def add_arguments(arg_parser):
    ann_group = arg_parser.add_argument_group('Annotations')
    ann_group.add_argument('--cell-annot-file', metavar='FILE', help='A TSV containing annotations per cell')
    ann_group.add_argument('--cell-annot-no-header', action='store_true', help='If specified, the file used in --cell-annot-file should not have a header line')
    ann_group.add_argument('--cell-annotation', metavar='NAME', help='The name of the cell annotation to add')
    ann_group.add_argument('--cell-id-column', metavar='COLUMN', type=int, help='The (0-based) column number in cell_annot_file that contains the cell ID', default=0)
    ann_group.add_argument('--cell-annot-column', metavar='COLUMN', help='The (0-based) column number in cell_annot_file that contains the annotation data to be added', default='1')
    ann_group.add_argument('--cell-suffix', metavar='SUFFIX', help='A suffix added to every cell id in cell_annot_file to match the data (ie, "-1")', default='-1')

    ann_group.add_argument('--drop-cell-annot', metavar='NAME', action='append', help='PERMANENTLY remove the indicated cell annotation')

def validate_args(args):
    cell_annotations = ( args.cell_annot_file is not None,
                         args.cell_annotation is not None,
                         args.cell_id_column is not None,
                         args.cell_annot_column is not None)
    if any(cell_annotations) and not all(cell_annotations):
        logging.critical("Cell annotations have only been partially specified (see --cell-annot-file, --cell-annotation, --cell-id-column, and --cell-annot-column)")
        exit(1)
    args.cell_annotation = args.cell_annotation.split(',')
    args.cell_annot_column = [ int(x) for x in args.cell_annot_column.split(',') ]
    if len(args.cell_annotation) != len(args.cell_annot_column):
        logging.critical("Length of --cell-annotation must match --cell-annot-column")
        exit(1)

def process(data, args):
    if args.drop_cell_annot:
        drop_cell_annotation(data, args.drop_cell_annot)
    if args.cell_annot_file is not None:
        add_cell_annotation(data, args.cell_annot_file, args.cell_annot_no_header, args.cell_annotation, 
                            args.cell_id_column, args.cell_annot_column, args.cell_suffix)

def add_cell_annotation(data, filename, header_absent, annot_name, cell_column, annotation_column, cell_suffix=''):
    header_row = None if header_absent else 'infer'
    annot = pd.read_csv(filename, sep='\t', header=header_row, index_col=cell_column)
    if cell_suffix:
        annot.rename(lambda x: x+cell_suffix, inplace=True)
    for name, col in zip(annot_name, annotation_column):
        data.obs[name] = annot[col]

def drop_cell_annotation(data, annotations):
    for annot_name in annotations:
        if annot_name not in data.obs_keys():
            logging.warning(f"Annotation '{annot_name}' not present in cell annotations (obs), ignoring")
            continue
        data.obs.pop(annot_name)