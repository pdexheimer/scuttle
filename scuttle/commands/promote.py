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
Promote cell annotations to proper genes
"""
import logging

import pandas as pd
from scipy.sparse import csc_matrix, hstack, issparse

from scuttle import history


def add_to_parser(parser):
    promote_cmd = parser.add_verb('promote')
    promote_cmd.add_argument('annotation')
    promote_cmd.set_executor(process)


def process(args, data, **kwargs):
    if args.annotation not in data.obs_keys():
        logging.critical(f"'{args.annotation}' not in cell annotations, cannot promote")
        return
    annot = data.obs[args.annotation].fillna(0)
    logging.debug(f'Annotation shape: {annot.shape}')
    new_gene = pd.DataFrame([[None] * data.var.shape[1]], columns=data.var_keys(),
                            index=[annot.name])
    logging.debug(f'Gene annotation shape: {data.var.shape}')
    logging.debug(f'New gene shape: {new_gene.shape}')
    logging.debug(f'Adding to gene annotations: {new_gene}')
    data._n_vars += 1
    data.var = pd.concat([data.var, new_gene])
    if issparse(data.X):
        data.X = hstack((data.X, csc_matrix(annot).transpose()), format='csc')
    else:
        data.X = pd.merge(data.X, annot, how='left', left_index=True, right_index=True)
    del data.obs[args.annotation]
    history.add_history_entry(data, args, f"Promoted cell annotation '{args.annotation}' to a gene")
