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
import os.path

import pandas as pd

import history

from .cellecta import assign_tags


def add_to_parser(parser):
    annot_cmd = parser.add_verb('annotate')
    cell_cmd = annot_cmd.add_verb('cells')
    _add_options(cell_cmd)
    gene_cmd = annot_cmd.add_verb('genes')
    _add_options(gene_cmd)
    cellecta_cmd = annot_cmd.add_verb('cellecta')
    cellecta_cmd.add_option('--fastqs', destvar='fastqs', nargs=2)
    cellecta_cmd.add_option('--bc14', destvar='bc14')
    cellecta_cmd.add_option('--bc30', destvar='bc30')
    cellecta_cmd.add_option('--id-suffix', destvar='id_suffix', default='')
    cellecta_cmd.add_option('--procs', '-p', destvar='procs', default=-1, type=int)
    annot_cmd.set_validator(validate_args)
    annot_cmd.set_executor(process)


def _add_options(command):
    command.add_option('--file', destvar='annot_file')
    command.add_option('--no-header', destvar='header', action='store_false')
    command.add_option('--name', destvar='annotation')
    command.add_option('--id-column', destvar='id_column', type=int, default=0)
    command.add_option('--annot-column', destvar='annot_column', default='1')
    command.add_option('--id-suffix', destvar='id_suffix', default='')
    command.add_option('--drop', destvar='drop')


def validate_args(args):
    if args.subcommand == 'cellecta':
        return
    annotations = (args.annot_file is not None,
                   args.annotation is not None)
    if any(annotations) and not all(annotations):
        logging.critical(f'{args.target.capitalize()} annotations have only been partially specified'
                         f' (see --file, --name, --id-column, and --annot-column)')
        exit(1)
    args.annotation = args.annotation.split(',') if args.annotation else ['none']
    try:
        args.annot_column = [int(x) for x in args.annot_column.split(',')]
    except ValueError:
        logging.critical('--annot-column must be (possibly comma-separated) integer(s)')
        exit(1)
    if len(args.annotation) != len(args.annot_column):
        logging.critical('Length of --name must match --annot-column')
        exit(1)


def process(args, data):
    if args.subcommand == 'cellecta':
        assign_tags.assign_tags(data, args.fastqs, args.bc14, args.bc30, args.id_suffix, args.procs)
        history.add_history_entry(data, args,
                                  f'Processed Cellecta tags from FASTQs {os.path.abspath(args.fastqs[0])}'
                                  f' and {os.path.abspath(args.fastq[1])}')
    else:
        if args.drop:
            description = drop_annotation(data, args.subcommand, args.drop)
        if args.annot_file is not None:
            add_annotation(data, args.subcommand, args.annot_file, args.header, args.annotation,
                           args.id_column, args.annot_column, args.id_suffix)
            if args.subcommand == 'cells':
                target = 'cell'
            else:
                target = 'gene'
            description = f'Added {target} annotation(s) {args.annotation} from file {os.path.abspath(args.annot_file)}'
        if description is not None:
            history.add_history_entry(data, args, description)


def add_annotation(data, target, filename, header_present, annot_name, id_column, annotation_column, id_suffix=''):
    header_row = 'infer' if header_present else None
    annot = pd.read_csv(filename, sep='\t', header=header_row, index_col=id_column)
    if id_suffix:
        annot.rename(lambda x: x + id_suffix, inplace=True)
    for name, col in zip(annot_name, annotation_column):
        if target == 'cells':
            data.obs[name] = annot[col]
        else:
            data.var[name] = annot[col]


def drop_annotation(data, target, annotation):
    """Returns a description of the operation, or None in case of error"""
    if target == 'cells':
        return _drop_cell_annotation(data, annotation)
    return _drop_gene_annotation(data, annotation)


def _drop_cell_annotation(data, annot_name):
    if annot_name not in data.obs_keys():
        logging.warning(f"Annotation '{annot_name}' not present in cell annotations (obs), ignoring")
        return None
    data.obs.pop(annot_name)
    return f'Removed cell annotation {annot_name}'


def _drop_gene_annotation(data, annot_name):
    if annot_name not in data.var_keys():
        logging.warning(f"Annotation '{annot_name}' not present in gene annotations (var), ignoring")
        return None
    data.var.pop(annot_name)
    return f'Removed gene annotation {annot_name}'
