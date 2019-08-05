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
Summarizes the annotations attached to the h5ad
"""

import numpy as np
import pandas as pd
from scipy.sparse import issparse


def add_to_parser(parser):
    describe_cmd = parser.add_verb('describe')
    describe_cmd.add_option('--verbose', '-v', destvar='verbose', action='store_true')
    history_cmd = describe_cmd.add_verb('history')
    history_cmd.add_option('--verbose', '-v', destvar='verbose', action='store_true')
    describe_cmd.set_executor(process)


def process(args, data, **kwargs):
    if args.subcommand == 'history':
        _show_history(data, args.verbose)
    else:
        if args.verbose:
            _full_summary(data)
        else:
            _brief_summary(data)


def _show_history(data, verbose):
    if 'history' not in data.uns_keys():
        print('No history stored in this file')
        return
    for entry in data.uns['history']:
        if verbose:
            print(f"[{entry['timestamp']}]")
            print(f"    {entry['description']}")
            print(f"    Run by {entry['user']}@{entry['hostname']} ({entry['operating_system']})")
            print(f"    scuttle v{entry['version']} (Python {entry['python']}), parameters: {entry['parameters']}")
        else:
            print(f"[{entry['timestamp']}] {entry['description']}")


def _brief_summary(data):
    print(f'Number of cells: {data.n_obs}')
    print('Cell annotations:')
    for x in data.obs_keys(): print(f'  {x}')
    print('Multi-dimensional per-cell data:')
    for x in data.obsm_keys(): print(f'  {x}')

    print(f'Number of genes: {data.n_vars}')
    print('Gene annotations:')
    for x in data.var_keys(): print(f'  {x}')
    print('Multi-dimensional per-gene data:')
    for x in data.varm_keys(): print(f'  {x}')

    print('Extra layers:')
    for x in data.layers.keys(): print(f'  {x}')


def _full_summary(data):
    print(f'Main expression matrix: {data.n_obs} cells by {data.n_vars} genes [{data.X.dtype}]', end='')
    print(' [sparse]' if issparse(data.X) else '')
    for x in data.layers.keys(): print(f'  (Layer) {_summarize(x, data.layers[x])}')
    print()
    print('Cell annotations')
    print(_summarize_index(data.obs_names))
    for x in data.obs_keys(): print(_summarize(x, data.obs[x]))
    print()
    print('Multi-dimensional per-cell data')
    for x in data.obsm_keys(): print(_summarize(x, data.obsm[x]))
    print()
    print('Gene annotations')
    print(_summarize_index(data.var_names))
    for x in data.var_keys(): print(_summarize(x, data.var[x]))
    print()
    print('Multi-dimensional per-gene data')
    for x in data.varm_keys(): print(_summarize(x, data.varm[x]))
    print()
    print('Unstructured data')
    for x in data.uns_keys():
        if x != 'history':
            print(_summarize(x, data.uns[x]))


def _summarize(name, collection):
    if isinstance(collection, np.ndarray):
        return _summarize_numpy(name, collection)
    elif isinstance(collection, pd.Series):
        if isinstance(collection.dtype, pd.CategoricalDtype) or not np.issubdtype(collection.dtype, np.number):
            return _summarize_pandas_categorical(name, collection)
        else:
            return _summarize_pandas_numerical(name, collection)
    else:
        return _summarize_python_data(name, collection)


def _summarize_index(index):
    result = 'Names look like:'
    for i in range(min(5, len(index))):
        result += f'\n  {index[i]}'
    return result


def _summarize_numpy(name, collection):
    return f"{name} [{collection.dtype}]: {'x'.join([ str(x) for x in collection.shape ])}"


def _summarize_pandas_categorical(name, collection):
    summary = collection.value_counts()
    result = f"""{collection.name} [{collection.dtype}]: {collection.count():d} non-null values
  {len(summary):d} distinct values, most frequent:"""
    for i in range(min(5, len(summary))):
        result += f'\n    {summary.index[i]}: {summary.iloc[i]:g}'
    return result


def _summarize_pandas_numerical(name, collection):
    summary = collection.describe()
    return f"""{collection.name} [{collection.dtype}]: {summary['count']:.0f} non-null values
  Range: {summary['min']:g} - {summary['max']:g}
  Mean (SD): {summary['mean']:g} ({summary['std']:g})
  Median (IQR): {summary['50%']:g} ({summary['25%']:g} - {summary['75%']:g})"""


def _summarize_python_data(name, data):
    return name
