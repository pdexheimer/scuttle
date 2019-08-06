#!/usr/bin/env python

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

import logging.config
import sys

from scuttle import history
from scuttle.commands import CommandParser, add_subcommands_to_parser
from scuttle.readwrite import ScuttleIO

logConfig = {
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(levelname)s %(asctime)s] %(message)s',
            'datefmt': '%H:%M:%S %Y-%m-%d'
        }
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['default']
    }
}


def main():
    logging.config.dictConfig(logConfig)

    # RPy2 uses the warnings module, and complains about POSIXct objects not specifying a timezone
    if not sys.warnoptions:
        import warnings
        warnings.simplefilter('ignore')

    parser = CommandParser()
    scuttle_io = ScuttleIO()
    ScuttleIO.add_options_to_parser(parser)
    parser.add_global_option('--procs', '-p', destvar='procs', default=-1, type=int)
    parser.add_global_option('--version', destvar='version', action='store_true')
    add_subcommands_to_parser(parser)

    if len(sys.argv) == 1:
        # An empty command line altogether.  Make a dummy 'arguments' and call help
        class dummy:
            def __init__(self):
                self.subcommand = None

        parser.help._execute_verb(dummy())
        return

    global_args, command_list = parser.parse()

    if global_args is None:
        # Help was explicitly invoked - no need to validate args or load data
        for c in command_list:
            c.execute()
        return

    if global_args.version:
        boilerplate = history.blank_entry()
        print(f"Scuttle v{boilerplate['version'][0]}")
        exit(0)

    scuttle_io.validate_args(global_args)
    scuttle_io.process_arguments(global_args)
    data = scuttle_io.load_data()
    for c in command_list:
        c.execute(data, n_procs=global_args.procs, scuttle_file=scuttle_io.canonical_filename())
    if history.has_file_changed():
        scuttle_io.save_data(data)


if __name__ == '__main__':
    main()
