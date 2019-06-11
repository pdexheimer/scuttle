#!/usr/bin/env python

from argparse import ArgumentParser
from modules import annotation, cellecta, load, summarize
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
    load.add_arguments(parser)
    cellecta.add_arguments(parser)
    annotation.add_arguments(parser)
    summarize.add_arguments(parser)
    return parser.parse_args()

def process_data(data, args):
    annotation.process(data, args)
    cellecta.process(data, args)
    summarize.process(data, args)

if __name__ == '__main__':
    logging.config.dictConfig(logConfig)
    args = parse_arguments()
    data = load.load_data(args)
    process_data(data, args)
    load.save_data(data, args)
