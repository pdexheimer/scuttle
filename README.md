# Scuttle - manage and manipulate single-cell data

## Installation

Run `python3 setup.py install`.  Note that this will install python packages as dependencies, so do it inside a virtual environment

## Usage

`scuttle -i FILE [options] [command...]`

Option | Description
-------|------------
--input FILE, -i FILE | The name of the file to load
--input-format &lt;h5ad, 10x, loom> | What is the type of file specified with -i? Default: h5ad
--output FILE, -o FILE | The name of the file to write.  If --input-format is h5ad defaults to the input file
--output-format &lt;h5ad, loom> | In what format should the output be written?
--no-write | Disables writing of output - any changes to the file will be discarded
--no-compress | [h5ad file format only] Disables file compression on output

Command | Description
--------|------------
annotate | Annotate the cells or genes with external data
select | Select cells or genes to keep (discarding the others)
describe | Describe the data
help | Print this help.  Use "help &lt;command>" to get detailed help for that command

Multiple commands can be specified, and will be executed in order.  Therefore:

`scuttle -i input.h5ad --no-write select 'num_genes > 200' describe`

will produce different results than

`scuttle -i input.h5ad --no-write describe select 'num_genes > 200'`

An input file is always required.  Valid input formats are:
 * **h5ad** - The native format of scuttle (all data in memory is stored in h5ad).  This is the anndata format used by scanpy (https://scanpy.rtfd.io)
 * **loom** - An alternative single-cell format created by the Linnarsson lab (http://loompy.org).  Used by velocyto.  Note that the current best way to use a Seurat object with scuttle is to first export it from Seurat as a loom file.
 * **10x** - Both the 10x h5 file (ie, filtered_feature_bc_matrix.h5) and matrix directory (ie, filtered_feature_bc_matrix/) are supported

If the input format is h5ad, scuttle by default will save the updated data back to the same file.  For all other input formats, or to save a new file, specify the appropriate filename using --output/-o.  Output formats are the same as input formats, except that writing 10x files is not supported.  H5ad files are compressed by default, this can be disabled using --no-compress.

## Commands

### `annotate`

Usage: `scuttle -i FILE annotate {cells,genes,cellecta} [options]`

Types| Description
-----|----
cells<br>genes | Add cell or gene annotations from an external (tab-separated) file
cellecta | Process cell barcodes using the Cellecta viral tags, and assign clone ids to cells

`cells`/`genes` Option|Description
-----|------
--file FILE | The (tab-separated) file to read annotations from
--no-header | By default, the first line of the file is assumed to contain column names. Specify this if the first line of the file is data
--name | The name of the annotation to store.  Multiple annotations can be comma-separated
--id-column | The column number (starting with 0) in FILE that contains the cell/gene ids
--annot-column | The column number (starting with 0) in FILE that contains the values to add as annotation. Multiple columns can be comma-separated
--id-suffix | This value will be appended to all cell/gene ids in FILE
--drop | The annotation(s) specified with --name will be REMOVED from the data

`cellecta` Option|Description
-------|---------
--fastqs READ1 READ2 | The raw reads of the barcode library
--bc14 FILE | A tab-separated file containing barcode ids and sequences of the 14bp barcodes
--bc30 FILE | A tab-separated file containing barcode ids and sequences of the 30bp barcodes
--id-suffix | This value will be appended to all cell barcodes in the --fastqs, in order to match the data
--procs NUM, -p NUM | The number of processors to use during error-correction of Cellecta barcodes

### `select`

Usage: `scuttle -i FILE select {cells,genes} <expression>`

&lt;expression> describes the cells/genes to keep, and is expected to be a comparison involving an annotation that already exists.  It should be quoted to prevent interpretation by the shell.  The annotation being compared must be on the left side of the expression

Examples:

`select cells 'num_genes > 200'`

`select genes 'num_cells < 10'`

`select cells 'num_genes > 500 or is_doublet == False'`
