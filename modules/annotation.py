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
    ann_group.add_argument('--cell-annot-column', metavar='COLUMN', type=int, help='The (0-based) column number in cell_annot_file that contains the annotation data to be added', default=1)
    ann_group.add_argument('--cell-suffix', metavar='SUFFIX', help='A suffix added to every cell id in cell_annot_file to match the data (ie, "-1")', default='-1')

    ann_group.add_argument('--drop-cell-annot', metavar='NAME', action='append', help='PERMANENTLY remove the indicated cell annotation')

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
    data.obs[annot_name] = annot[annotation_column]

def drop_cell_annotation(data, annotations):
    for annot_name in annotations:
        if annot_name not in data.obs_keys():
            logging.warning(f"Annotation '{annot_name}' not present in cell annotations (obs), ignoring")
            continue
        data.obs.pop(annot_name)