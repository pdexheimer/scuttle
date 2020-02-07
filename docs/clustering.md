# Notes on clustering single-cell data

I read Valentine Svensson's [blog post about clustering single cells in an "actionable" way](http://www.nxn.se/valent/2018/3/5/actionable-scrna-seq-clusters).  These are my notes on implementing something like this.

Links:
* [Actionable scRNA-seq clusters](http://www.nxn.se/valent/2018/3/5/actionable-scrna-seq-clusters) - the original blog post
* [Jupyter notebooks](https://github.com/vals/Blog/tree/master/180302-actionable-clusters) with the code behind his post
* [Library code](https://github.com/Teichlab/NaiveDE/blob/master/NaiveDE/cell_types.py) used in those Jupyter notebooks

Svensson defines an "actionable" clustering as having a small number (< 10) of genes that define each cluster.  This is actionable because it becomes feasible to biologically validate these genes. Svensson does this by:

1. Defining a clustering of size *K* on the data
    * In his simulated data set, he operates on the first 15 principle components
    * In the bone marrow data set, he instead uses the first 25 components of a truncated SVD.  I think this is similar, but more resistant to outliers
    * In all cases, he uses a Variational Bayesian Gaussian Mixture model.  It's not clear to me why this is better than a simple k-means.
2. Using Logistic Regression to predict the "correct" cluster for each cell
    * Data is split into train/test (50/50)
    * A "one vs rest" Logistic Regression with Lasso regularization is trained with the training set
    * The fitted model is then used to predict the values for the test set
3. Evaluating the fit
    * He plots an ROC curve for each cluster, and expects to see AUCs near 1 for all of them (evaluated by eye)

By repeating this procedure over a range of *K*s, he identifies the best K for his data.  He can then extract the genes with the highest coefficients from the regression to use as marker genes.

## Weaknesses

1. The regularization parameter for every single value of K must be tweaked in order to keep the number of genes in use down to a manageable number -- which itself is poorly defined, but probably means < 30 (with some room to expand)
2. The evaluation is a manual process - this seems like it should be automated somehow
3. I'm not sure I like the one-vs-rest regression - a multinomial/softmax regression seems more appropriate here
4. As he points out in the post, using a ROC curve may not be the best choice since cluster sizes can vary so much.  However, it seems to be "good enough"

## Strengths

1. I like the idea of forcing clusters to be defined by a small number of genes
2. This should make the task of auto-defining cell types simpler - or at the least, feature selection is better defined

## Thoughts

* Changing the regression to SoftMax is trivial
* Anything magic about 15 PCs?  Obviously not - how to pick the best coordinate space?
* Might be worth using an ElasticNet regularization?  Not sure.  In the best case, it might help stabilize the regularization parameter, but that's probably dreaming
    * Have seen a couple of references to some instability in pure Lasso, people recommend keeping a small piece of Ridge in there to prevent it.  Possibly around 0.99 lasso / 0.01 ridge?
* Similarly, it might be worth thinking about using SGD during training.  Minibatch training uses partial_fit, but would have to write my own convergence checking
* Hastie & Tibshirani propose a Gap metric for defining the optimal K.  Generate a random dataset over the same range of values, and calculate the within-cluster sum of squares for this background dataset.  K is optimal when the "gap" between this value and the value you get for real data is the largest.  Might be worth trying here
* ~~Need to do more work to figure out the difference between GMMs and K-means for classification - they might be equivalent.~~  EDIT -- of course.  GMM is a "soft" clustering, because it assigns probabilities of each class rather than simply picking the best.  This leads to smoother boundaries and better outlier handling.
* There's a package called glmnet that looks like it will help me to optimize the regularization parameter.  Once concern is that it has no way to include a term for "small number of features" in the fitness test, but I may be able to work around that