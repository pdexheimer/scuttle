"""
Summarizes the annotations attached to the h5ad
"""

def add_arguments(arg_parser):
    arg_parser.add_argument('--summary', choices=['none', 'brief', 'detailed'], default='brief',
                            help='Summarize the annotations before saving (Default: %(default)s)')
    arg_parser.add_argument('--no-summary', '-q', dest='summary', action='store_const', const='none',
                            help='Synonym for --summary=none')
    arg_parser.add_argument('--details', dest='summary', action='store_const', const='detailed',
                            help='Synonym for --summary=detailed')

def process(data, args):
    if args.summary == 'brief':
        _brief_summary(data)
    elif args.summary == 'detailed':
        _full_summary(data)

def _brief_summary(data):
    print(f"Number of cells: {data.n_obs}")
    print("Cell annotations:")
    for x in data.obs_keys(): print(f"  {x}")
    print("Multi-dimensional per-cell data:")
    for x in data.obsm_keys(): print(f"  {x}")

    print(f"Number of genes: {data.n_vars}")
    print("Gene annotations:")
    for x in data.var_keys(): print(f"  {x}")
    print("Multi-dimensional per-gene data:")
    for x in data.varm_keys(): print(f"  {x}")

def _full_summary(data):
    print("To be implemented!")
    _brief_summary(data)