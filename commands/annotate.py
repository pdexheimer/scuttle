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

from . import command as cmd
from .cellecta import assign_tags
import logging
import pandas as pd

def commands():
    annot_cmd = cmd.CommandDescription('annotate')
    cell_cmd = cmd.CommandDescription('cells')
    _add_options(cell_cmd)
    annot_cmd.add_subcommand(cell_cmd)
    gene_cmd = cmd.CommandDescription('genes')
    _add_options(gene_cmd)
    annot_cmd.add_subcommand(gene_cmd)
    cellecta_cmd = cmd.CommandDescription('cellecta')
    cellecta_cmd.add_option('--fastqs', destvar='fastqs', nargs=2)
    cellecta_cmd.add_option('--bc14', destvar='bc14')
    cellecta_cmd.add_option('--bc30', destvar='bc30')
    cellecta_cmd.add_option('--id-suffix', destvar='id_suffix', default='')
    cellecta_cmd.add_option('--procs', '-p', destvar='procs', default=-1, type=int)
    annot_cmd.add_subcommand(cellecta_cmd)
    return [ cmd.CommandTemplate(annot_cmd, process, validate_args) ]

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
    annotations = ( args.annot_file is not None,
                    args.annotation is not None)
    if any(annotations) and not all(annotations):
        logging.critical(f"{args.target.capitalize()} annotations have only been partially specified (see --file, --name, --id-column, and --annot-column)")
        exit(1)
    args.annotation = args.annotation.split(',') if args.annotation else ['none']
    try:
        args.annot_column = [ int(x) for x in args.annot_column.split(',') ]
    except ValueError:
        logging.critical("--annot-column must be (possibly comma-separated) integer(s)")
        exit(1)
    if len(args.annotation) != len(args.annot_column):
        logging.critical("Length of --name must match --annot-column")
        exit(1)

def process(args, data):
    if args.subcommand == 'cellecta':
        assign_tags.assign_tags(data, args.fastqs, args.bc14, args.bc30, args.id_suffix, args.procs)
    else:
        if args.drop:
            drop_annotation(data, args.subcommand, args.drop)
        if args.annot_file is not None:
            add_annotation(data, args.subcommand, args.annot_file, args.header, args.annotation, 
                                args.id_column, args.annot_column, args.id_suffix)

def add_annotation(data, target, filename, header_present, annot_name, id_column, annotation_column, id_suffix=''):
    header_row = 'infer' if header_present else None
    annot = pd.read_csv(filename, sep='\t', header=header_row, index_col=id_column)
    if id_suffix:
        annot.rename(lambda x: x+id_suffix, inplace=True)
    for name, col in zip(annot_name, annotation_column):
        if target == 'cells':
            data.obs[name] = annot[col]
        else:
            data.var[name] = annot[col]

def drop_annotation(data, target, annotations):
    if target == 'cells':
        _drop_cell_annotation(data, annotations)
    else:
        _drop_gene_annotation(data, annotations)

def _drop_cell_annotation(data, annot_name):
    if annot_name not in data.obs_keys():
        logging.warning(f"Annotation '{annot_name}' not present in cell annotations (obs), ignoring")
        return
    data.obs.pop(annot_name)

def _drop_gene_annotation(data, annot_name):
    if annot_name not in data.var_keys():
        logging.warning(f"Annotation '{annot_name}' not present in gene annotations (var), ignoring")
        return
    data.var.pop(annot_name)