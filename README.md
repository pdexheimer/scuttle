# Scuttle - manage and manipulate single-cell data

## Installation

Note that scuttle is still very much in the alpha stage, I'm adding new features regularly.  I have not taken the time to load it into PyPI yet.

There are two methods of installation:

### Using pipx

[Pipx](https://pipxproject.github.io/pipx/) is a package manager for python applications.  It will install all of the dependencies into a virtual environment that is encapsulated away from the user, and make the script available for use anywhere.  This is my favorite approach, as you don't need to activate a virtual environment every time you run scuttle.  Be sure to read the complete [installation instructions](https://pipxproject.github.io/pipx/installation/).

```
$ pip install pipx
$ pipx ensurepath # Restart the terminal
$ git clone https://github.com/pdexheimer/scuttle
$ pipx install -e --spec scuttle/ scuttle
$ scuttle --version
```

### Using setuptools

The advantage of this method is that it doesn't require any extra software to be installed.  The disadvantage is that you need to maintain your virtual environment yourself (or worse, don't use a virtual environment.  But that's a bad idea), *and you'll need to activate your virtual environment every time you use scuttle*.  See the documentation for the [venv module](https://docs.python.org/3/library/venv.html) and for [creating virtual environments](https://packaging.python.org/installing/#creating-virtual-environments).

```
$ git clone https://github.com/pdexheimer/scuttle
$ cd scuttle
$ python3 -mvenv env
$ source env/bin/activate
$ python setup.py develop  # Or: python setup.py install
$ scuttle --version
```

## Usage

`scuttle -i FILE [options] [command...]`

Option | Description
-------|------------
--input FILE, -i FILE | The name of the file to load
--input-format &lt;h5ad, 10x, loom, bustools-count, mtx, mex> | What is the type of file specified with -i? Default: h5ad
--output FILE, -o FILE | The name of the file to write.  If --input-format is h5ad defaults to the input file
--no-write | Disables writing of output - any changes to the file will be discarded
--no-compress | Disables file compression on output
--procs NUM, -p NUM | The number of processors to use.  Only certain analyses will take advantage of these.
--version | Prints Scuttle's version and exits
--help, -h, -? | Print this help.  Use "help &lt;command>" to get detailed help for that command

Command | Description
--------|------------
annotate | Annotate the cells or genes with external data
describe | Describe the data
export | Export the data in another format
filterempty | Identify (and optionally remove) barcodes that don't look like cells
plot | Generate useful figures
select | Select cells or genes to keep (discarding the others)
help | Print this help.  Use "help &lt;command>" to get detailed help for that command

Multiple commands can be specified, and will be executed in order.  Therefore:

`scuttle -i input.h5ad select 'num_genes > 200' describe`

will produce different output than

`scuttle -i input.h5ad describe select 'num_genes > 200'`

An input file is always required.  Valid input formats are:
 * **h5ad** - The native format of scuttle (all data in memory is stored in h5ad).  This is the anndata format used by scanpy (https://scanpy.rtfd.io)
 * **loom** - An alternative single-cell format created by the Linnarsson lab (http://loompy.org).  Used by velocyto.  Note that the current best way to use a Seurat object with scuttle is to first export it from Seurat as a loom file.
 * **10x** - Both the 10x h5 file (ie, filtered_feature_bc_matrix.h5) and matrix directory (ie, filtered_feature_bc_matrix/) are supported
 * **bustools-count** - Loads the output of the 'bustools count' command (https://bustools.github.io/manual). The value provided to -i should be the same as that provided to bustools count -o. That is, you should supply the basename of the actual files
 * **mtx**, **mex** - Matrix Market Exchange format (https://math.nist.gov/MatrixMarket/formats.html#MMformat). This format does not include cell/gene names, so each will be numbered instead.  Use the `--replace` option in `scuttle annotate cells/genes` to supply correct names.  You should prefer the `10x` or `bustools-count` input formats, as these will automatically load the names


If the input format is h5ad, scuttle by default will save the updated data back to the same file.  If there are no changes to the file (for example, only `scuttle describe` was run), no output will be written.  For all other input formats, or to save a new file, specify the appropriate filename using --output/-o.  H5ad files are compressed by default, this can be disabled using --no-compress.  In order to save in a different format, see the `export` subcommand.

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
--name ANNOTATION | The name of the annotation to store.  Multiple annotations can be comma-separated
--id-column COL | The column number (starting with 0) in FILE that contains the cell/gene ids
--annot-column COL | The column number (starting with 0) in FILE that contains the values to add as annotation. Multiple columns can be comma-separated
--id-suffix SUFFIX | This value will be appended to all cell/gene ids in FILE
--drop ANNOTATION | The specified annotation will be REMOVED from the data
--replace | Instead of adding annotations onto existing ones, all existing annotations will be dropped and replaced by the new ones.  This include the ids, which means that new data will be applied without any reordering whatsoever

`cellecta` Option|Description
-------|---------
--fastqs READ1 READ2 | The raw reads of the barcode library
--bc14 FILE | A tab-separated file containing barcode ids and sequences of the 14bp barcodes
--bc30 FILE | A tab-separated file containing barcode ids and sequences of the 30bp barcodes
--id-suffix | This value will be appended to all cell barcodes in the --fastqs, in order to match the data

### `describe`

Usage: `scuttle -i FILE describe [history] [options]`

Option | Description
-------|------------
--verbose, -v | Enable more detailed output

`describe` prints a summary of the data/annotations contained in FILE to standard output.  Without `--verbose`, only basic dimensions and names of annotations are displayed.  With `--verbose`, a summary of the annotation values is also produced.

`describe history` prints scuttle's history of operations that have been performed on the file.  Once again, adding `--verbose` will include more information

### `export`

Usage: `scuttle -i FILE export [--overwrite] {loom,mtx,mex,cells,genes,textmatrix} <filename>`

Option | Description
-------|------------
--overwrite | By default, scuttle will exit instead of writing data if the destination file exists.  Include --overwrite to overwrite the file instead

Format | Description
-------|------------
loom | The HDF5-based Loom format (http://loompy.org)
mtx,mex | These are synonyms for Market Exchange Format, which is one of the ways CellRanger exports results
cells,genes | Dumps all of the cell or gene metadata, as appropriate.  If &lt;filename> ends with .gz, it will be gzip compressed
textmatrix | Dumps the entire expression matrix to a tab-delimited text file.  This file has the potential to be several gigabytes, depending on the number of cells.  If &lt;filename> ends with .gz, it will be gzip compressed


### `filterempty`

Usage: `scuttle -i FILE filterempty [emptydrops,classic] <options>`

If neither emptydrops or classic is specified, emptydrops will be used.

`emptydrops`&nbsp;Option | Description
--------------------|------------
--fdr FDR | Remove cells with an emptyDrops FDR above this amount (default: 0.001)
--keep-all, -k | If set, all barcodes will be retained, even if they are called empty
--cellranger | Emulate (as closely as possible) CellRanger's parameters
--ambient-cutoff THRESH | Cells with THRESH UMIs or less are used to estimate the ambient RNA distribution (ie, what empty droplets look like) (default: 100)
--retain-cutoff THRESH | Cells with at least THRESH UMIs will be called cells, regardless of the emptyDrops result (adjusted p-value will be set to 0) (default: None, auto-calculated by finding knee in UMI rank plot)
--iters ITERS | How many iterations of Monte Carlo p-value estimation? (default: 10000)
--expect-cells CELLS | Only used when --cellranger is set - number of expected cells (default: 3000)
--plot FILENAME | Saves a barcoderank plot to FILENAME before removing empty cells

`classic`&nbsp;Option | Description
----------------------|------------
--expect-cells CELLS | The number of expected cells in the experiment (default: 3000)
--keep-all, -k | If set, all barcodes will be retained, even if they are called empty
--upper-quant QUANTILE | The position within --expect-cells that is evaluated to determine the calling threshold (default: 0.99)
--lower-prop PROPORTION | The calling threshold will be at PROPORTION times the UMI count of the barcode selected with --expect-cells and --upper-quant (default: 0.1)
--plot FILENAME | Saves a barcoderank plot to FILENAME before removing empty cells

### `plot`

Usage: `scuttle -i FILE plot {barcoderank,dispersiontest} [options] IMAGE`

Plot Types:

**`barcoderank`** Plots the total UMI count of barcodes, ordered from highest to lowest. Most useful if empty barcodes have been identified but retained (either via `filterempty -k` or because this plot was directly generated by `filterempty --plot`).  Details of the filtering algorithm will be included on the plot, as well as the estimated special points (knee and inflection)

**`dispersiontest`** The multinomial distribution used to derive p-values is parameterized.  This command will help to ensure that the chosen parameters are reasonable, by conducting a Kolmogorov Smirnov test of 'background' barcode p-values versus a uniform distribution, and by producing a probability plot to allow a graphical comparison

`dispersiontest`&nbsp;Option | Description
----------------------|------------
--alpha, -a VALUE | The primary parameter for the Dirichlet Multinomial distribution used by emptyDrops.  Set to 'non-dirichlet' to use a simple multinomial distribution (as cellranger does).  Default value: alpha is auto-calculated by emptyDrops
--ambient-cutoff UMI  | Barcodes with a UMI count less than this value will be considered 'ambient', and will be used to derive the ambient distribution as well as to test in this method.  Default: 100
--sample COUNT | If all of the several hundred thousand 'ambient' barcodes found in most experiments are used for the K-S test, the p-value will always be zero. Instead, randomly select COUNT barcodes to use for the test.  Default: 100

### `select`

Usage: `scuttle -i FILE select {cells,genes} <expression>`

&lt;expression> describes the cells/genes to keep, and is expected to be a comparison involving an annotation that already exists.  It should be quoted to prevent interpretation by the shell.  The annotation being compared must be on the left side of the expression

Examples:

`select cells 'num_genes > 200'`

`select genes 'num_cells < 10'`

`select cells 'num_genes > 500 or is_doublet == False'`
