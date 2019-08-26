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

import sys

import colorama

from scuttle import history, logging
from scuttle.commands import CommandParser, add_subcommands_to_parser
from scuttle.readwrite import ScuttleIO


def invoke_toplevel_help(parser):
    class EmptyCommand:
        def __init__(self):
            self.subcommand = None

    parser.help._execute_verb(EmptyCommand())


def main():
    colorama.init()
    logging.init()

    parser = CommandParser()
    scuttle_io = ScuttleIO()
    ScuttleIO.add_options_to_parser(parser)
    parser.add_global_option('--procs', '-p', destvar='procs', default=-1, type=int)
    parser.add_global_option('--version', destvar='version', action='store_true')
    parser.add_global_option('--help', '-h', '-?', destvar='help', action='store_true')
    add_subcommands_to_parser(parser)

    # If no arguments were specified, the user must want help.  Don't even bother parsing
    if len(sys.argv) == 1:
        invoke_toplevel_help(parser)
        return

    global_args, command_list = parser.parse()

    # CommandParser returns None for global_args if the help submodule was invoked
    # In this case, we don't want to validate
    if global_args is None:
        for c in command_list:
            c.execute()
        return
    if global_args.help:
        invoke_toplevel_help(parser)
        return
    if global_args.version:
        boilerplate = history.blank_entry()
        print(f"Scuttle v{boilerplate['version'][0]}")
        exit(0)

    scuttle_io.validate_args(global_args)
    scuttle_io.process_arguments(global_args)
    data = scuttle_io.load_data()
    for c in command_list:
        c.validate()
        c.execute(data, n_procs=global_args.procs, scuttle_file=scuttle_io.canonical_filename())
    if history.has_file_changed():
        scuttle_io.save_data(data)


if __name__ == '__main__':
    main()
