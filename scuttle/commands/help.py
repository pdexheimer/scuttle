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
Command line help system
"""

import textwrap


def add_to_parser(parser):
    parser.help.add_verb('annotate')
    parser.help.add_verb('describe')
    parser.help.add_verb('filterempty')
    parser.help.add_verb('select')
    parser.help.set_executor(process)


def process(args, **kwargs):
    if args.subcommand is None:
        help_text = global_help()
    elif args.subcommand == 'annotate':
        help_text = annotate_help()
    elif args.subcommand == 'describe':
        help_text = describe_help()
    elif args.subcommand == 'select':
        help_text = select_help()
    elif args.subcommand == 'filterempty':
        help_text = filter_help()
    print(help_text)


def global_help():
    return textwrap.dedent("""\
    scuttle - A single-cell utility program

    Usage:
      scuttle -i FILE [options] [command...]

    Options:
      --input FILE, -i FILE               The name of the file to load
      --input-format <h5ad, 10x, loom>    What is the type of file specified with -i? Default: h5ad
      --output FILE, -o FILE              The name of the file to write.  If --input-format is h5ad,
                                          defaults to the input file
      --output-format <h5ad, loom>        In what format should the output be written?
      --no-write                          Disables writing of output - any changes to the file will be discarded
      --no-compress                       [h5ad file format only] Disables file compression on output
      --procs NUM, -p NUM                 The number of processors to use.  Only certain analyses can take advantage.
      --version                           Print Scuttle's version and quit

    Commands:
      annotate                            Annotate the cells or genes with external data
      filterempty                         Identify (and optionally remove) barcodes that don't look like cells
      select                              Select cells or genes to keep (discarding the others)
      describe                            Describe the data
      help                                Print this help.  Use "help <command>" to get detailed help for that command

    Multiple commands can be specified, and will be executed in order.  Therefore:

      scuttle -i input.h5ad --no-write select 'num_genes > 200' describe

    will produce different results than

      scuttle -i input.h5ad --no-write describe select 'num_genes > 200'

    An input file is always required.  Valid input formats are:
      h5ad  -- The native format of scuttle (all data in memory is stored in h5ad).  This is the anndata
               format used by scanpy (https://scanpy.rtfd.io)
      loom  -- An alternative single-cell format created by the Linnarsson lab (http://loompy.org).  Used
               by velocyto.  Note that the current best way to use a Seurat object with scuttle is to
               first export it from Seurat as a loom file.
      10x   -- Both the 10x h5 file (ie, filtered_feature_bc_matrix.h5) and matrix directory (ie,
               filtered_feature_bc_matrix/) are supported

    If the input format is h5ad, scuttle by default will save the updated data back to the same file.  If there are no
    changes to the file (for example, only 'scuttle describe' was run), no output will be written.  For all other
    input formats, or to save a new file, specify the appropriate filename using --output/-o.  Output formats are the
    same as input formats, except that writing 10x files is not supported.  H5ad files are compressed by default, this
    can be disabled using --no-compress.
    """)


def annotate_help():
    return textwrap.dedent("""\
    scuttle annotate - Add annotations to single-cell data from external sources

    Usage:
      scuttle -i FILE annotate {cells,genes,cellecta} [options]

    Types:
      cells
      genes            Add cell or gene annotations from an external (tab-separated) file
      cellecta         Process cell barcodes using the Cellecta viral tags, and assign clone ids to cells

    Cells/Genes Options
      --file FILE         The (tab-separated) file to read annotations from
      --no-header         By default, the first line of the file is assumed to contain column names.
                          Specify this if the first line of the file is data
      --name ANNOTATION   The name of the annotation to store.  Multiple annotations can be comma-separated
      --id-column COL     The column number (starting with 0) in FILE that contains the cell/gene ids
      --annot-column COL  The column number (starting with 0) in FILE that contains the values to add as annotation.
                          Multiple columns can be comma-separated
      --id-suffix SUFFIX  This value will be appended to all cell/gene ids in FILE
      --drop ANNOTATION   The specified annotation will be REMOVED from the data

    Cellecta Options
      --fastqs READ1 READ2   The raw reads of the barcode library
      --bc14 FILE            A tab-separated file containing barcode ids and sequences of the 14bp barcodes
      --bc30 FILE            A tab-separated file containing barcode ids and sequences of the 30bp barcodes
      --id-suffix            This value will be appended to all cell barcodes in the --fastqs, in order to
                             match the data
    """)


def describe_help():
    return textwrap.dedent("""\
    scuttle describe - Describe the data and metadata for a single-cell dataset

    Usage:
      scuttle -i FILE describe [history] [options]

    Options:
      --verbose, -v       Descibe the metadata in more detail - numerical data is
                          summarized, most frequent categories are shown, etc

    If 'describe history' is given, then scuttle's history of operations on the file will be displayed.
    With just 'describe', the data and annotations in the file are described.
    """)


def select_help():
    return textwrap.dedent("""\
    scuttle select - Filter cells or genes based on their metadata

    Usage:
      scuttle -i FILE select {cells,genes} <expression>

    <expression> describes the cells/genes to keep, and is expected to be a comparison involving an annotation that
    already exists.  It should be quoted to prevent interpretation by the shell.  The annotation being compared must
    be on the left side of the expression

    Examples:
      select cells 'num_genes > 200'
      select genes 'num_cells < 10'
      select cells 'num_genes > 500 or is_doublet == False'

    """)


def filter_help():
    return textwrap.dedent("""\
    scuttle filterempty - Identify (and optionally remove) barcodes that don't look like cells

    Usage:
      scuttle -i FILE filterempty [emptydrops,classic] <options>

    emptydrops Options:
      --fdr FDR                 Remove cells with an emptyDrops FDR above this amount
                                (default: None, no filter)
      --cellranger              Emulate (as closely as possible) CellRanger's parameters
      --ambient-cutoff THRESH   Cells with THRESH UMIs or less are used to estimate the ambient
                                RNA distribution (ie, what empty droplets look like) (default: 100)
      --retain-cutoff THRESH    Cells with at least THRESH UMIs will be called cells, regardless
                                of the emptyDrops result (adjusted p-value will be set to 0)
                                (default: None, auto-calculated by finding knee in UMI rank plot)
      --iters ITERS             How many iterations of Monte Carlo p-value estimation? (default: 10000)
      --expect-cells CELLS      Only used when --cellranger is set - number of expected cells (default: 3000)

    classic Options:
      --expect-cells CELLS      The number of expected cells in the experiment (default: 3000)
      --keep-all, -k            If set, all barcodes will be retained, even if they are called empty
      --upper-quant QUANTILE    The position within --expect-cells that is evaluated to determine the
                                calling threshold (default: 0.99)
      --lower-prop PROPORTION   The calling threshold will be at PROPORTION times the UMI count of the
                                barcode selected with --expect-cells and --upper-quant (default: 0.1)

    If neither emptydrops or classic is specified, emptydrops will be used.
    """)
