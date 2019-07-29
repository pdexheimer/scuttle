# Notes on identifying "empty" cells

### "Classic" method

Early versions of CellRanger (< 3.0) used a fairly straightforward method of identifying barcodes that actually belong to cells.  The essence of the algorithm is to define a threshold UMI count, above which the barcode is considered to be a real cell, and below which it is discarded as "empty":

1. Get __*N*__, the number of cells expected in the experiment, from the user (default: 3000)
2. After ordering the cells from most to fewest UMIs, identify the cell at the 99th percentile of __*N*__ (default: cell #30)
3. Establish a threshold at 10% of the UMIs seen in the cell identified in Step 2.  All barcodes with at least this many UMIs are called cells

In cellranger, only __*N*__ is modifiable by the user, with the parameter `--expect-cells` to `cellranger count`.

In the [DropletUtils](https://rdrr.io/github/MarioniLab/DropletUtils/) package, this is implemented in the [defaultDrops](https://rdrr.io/github/MarioniLab/DropletUtils/man/defaultDrops.html) method.  In this implementation, __*N*__ is provided as parameter `expected`, the percentile cutoff used in Step 2 is in parameter `upper.quant`, and the fraction of UMIs used as a threshold in Step 3 is in `lower.prop`.  Defaults are chosen to match the Cellranger defaults.

### EmptyDrops

In [Lun *et al* 2019](https://doi.org/10.1186/s13059-019-1662-y), the authors introduced the EmptyDrops algorithm.  The basic idea is that all of the empty droplets actually contain RNA that is ambient in the environment.  EmptyDrops estimates the gene distribution of this ambient RNA profile, and then tests each barcode against that estimated distribution.  Only barcodes that are significantly different from this distribution are called cells.  The advantage of this approach is that it accounts for cells with wildly different amounts of transcription (ie, neutrophils are typically quite low and were frequently removed with the "classic" algorithm).

CellRanger v3.0 adapted the algorithm as presented in the preprint manuscript, and made it the default way of identifying "real" cells.  However, differences exist between the two implementations (cf [Aaron Lun's comment on GitHub](https://github.com/MarioniLab/DropletUtils/issues/17#issuecomment-508549804)).  The basic algorithm is:

1. Identify a set of barcodes that are assumed to be empty (based on UMI count) and thus represent the ambient distribution
2. Estimate the ambient distribution of genes from the aggregation of all the ambient barcodes (both methods use [Good-Turing smoothing](https://en.wikipedia.org/wiki/Good–Turing_frequency_estimation) to prevent probabilities of zero)
3. Calculate log-likelihoods for each barcode in the data set to be from the ambient distribution
4. Compute p-values from the log likelihoods, and adjust with Benjamini-Hochberg
5. Identify a set of barcodes that are assumed to be real cells.  For all other barcodes, only retain if the corrected p-value is significant

#### Differences between methods

1. Identify presumed empty barcodes
    * **Lun *et al***: The barcodes with 100 UMIs or less (parameter `lower`)
    * **Cellranger**: Barcode numbers 45,000 through 90,000 after ordering by UMI count (ie, the 45,000th most UMIs).  If an ambient distribution cannot be derived from these barcodes, the entire *emptyDrops method is skipped* and the classic method is used instead.
2. Estimate the ambient distribution
    * No known differences
3. Calculate log-likelihoods
    * **Lun *et al***: Distribution is controlled by a parameter `alpha`.  With finite alpha, a Dirichlet multinomial distribution is used, with alpha controlling overdispersion.  With infinite alpha, a multinomial distribution is used.  When alpha is NULL (the default), the value of alpha is estimated from the count profiles of the ambient barcodes. By default, only the barcodes with UMI counts greater than `lower` are tested, though this can be changed with the `test.ambient` parameter.
    * **Cellranger**: A multinomial distribution is used (I believe this is equivalent to `alpha=Inf` in emptyDrops). Only those barcodes with a UMI count greater than 1% of the median of non-ambient barcodes are considered, but there is a minimum of 500.  Of these, only the top 20,000 are used.  None of these parameters are user-modifiable.  If no barcodes satisfy these parameters, the *emptyDrops method is skipped* and the classic method is used instead.
4. Compute p-values
    * **Lun *et al***: A Monte Carlo permutation is used to calculate p-values.  The number of iterations is 10,000 by default, but is controlled by the `niters` parameter.
    * **Cellranger**: I don't know the details of this computation.
5. Identify a set of presumed real cells to retain
    * **Lun *et al***: This is controlled by the `retain` parameter, which sets the threshold UMI count to use.  By default (`retain=NULL`), the threshold is calculated as the knee in the count-rank curve (cf [barcodeRanks](https://rdrr.io/github/MarioniLab/DropletUtils/man/barcodeRanks.html)).  The retained cells have their p-values set to zero before B-H correction.  In the manuscript, an adjusted p-value of 0.001 is used - though no threshold is actually applied by the function.
    * **Cellranger**: The retained cells are selected using the "classic" method described above.  All cells have an adjusted p-value calculated, and significant barcodes are called cells.  *After this step*, the cells called by the classic method are added to the results. An adjusted p-value of 0.01 is used as the threshold (not modifiable).

## Sources:

CellRanger
* [Algorithm overview](https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/algorithms/overview)
* [Source code for emptyDrops implementation](https://github.com/10XGenomics/cellranger/blob/master/lib/python/cellranger/cell_calling.py)
* [Source code for classic method](https://github.com/10XGenomics/cellranger/blob/master/lib/python/cellranger/stats.py) See function `filter_cellular_barcodes_ordmag`, line 175.  I'm only pretty sure this is the correct code.
* [Source code for overall pipeline](https://github.com/10XGenomics/cellranger/blob/master/mro/stages/counter/filter_barcodes/__init__.py)

EmptyDrops
* [Source code](https://github.com/MarioniLab/DropletUtils/blob/master/R/emptyDrops.R)
* [Man page](https://rdrr.io/github/MarioniLab/DropletUtils/man/emptyDrops.html)
* [Published Description](https://doi.org/10.1186/s13059-019-1662-y)