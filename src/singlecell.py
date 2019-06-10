from argparse import ArgumentParser
import cellecta
import annotation
import load
import summarize

parser = ArgumentParser()
load.add_arguments(parser)
cellecta.add_arguments(parser)
annotation.add_arguments(parser)
summarize.add_arguments(parser)

args = parser.parse_args()
data = load.load_data(args)
annotation.process(data, args)
cellecta.process(data, args)
summarize.process(data, args)
load.save_data(data, args)