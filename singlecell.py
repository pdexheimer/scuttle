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

from argparse import ArgumentParser
from modules import annotation, cellecta, file, summarize, filter
import logging.config

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

def parse_arguments():
    parser = ArgumentParser()
    file.add_arguments(parser)
    cellecta.add_arguments(parser)
    annotation.add_arguments(parser)
    filter.add_arguments(parser)
    summarize.add_arguments(parser)
    return parser.parse_args()

def validate_arguments(args):
    file.validate_args(args)
    annotation.validate_args(args)

def process_data(data, args):
    annotation.process(data, args)
    cellecta.process(data, args)
    filter.process(data, args)
    summarize.process(data, args)

def main():
    logging.config.dictConfig(logConfig)
    args = parse_arguments()
    validate_arguments(args)
    data = file.load_data(args)
    process_data(data, args)
    file.save_data(data, args)

if __name__ == '__main__':
    main()