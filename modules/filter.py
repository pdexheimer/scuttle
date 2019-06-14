import ast
import logging
import numpy as np
import pandas as pd
import sys

def add_arguments(arg_parser):
    filter_group = arg_parser.add_argument_group('Filter')
    filter_group.add_argument('--select-cells', '-C', metavar='EXPR',
                                help='Select cells that meet the given criteria')
    filter_group.add_argument('--select-genes', '-G', metavar='EXPR',
                                help='Select genes that meet the given criteria')

def process(data, args):
    if args.select_cells:
        tree = ast.parse(args.select_cells, mode='eval')
        cell_subset = EvaluateFilter(data, 'cell').visit(tree)
        s = np.sum(~cell_subset)
        logging.info(f'Removed {s} cells')
        data._inplace_subset_obs(cell_subset)
    if args.select_genes:
        tree = ast.parse(args.select_genes, mode='eval')
        gene_subset = EvaluateFilter(data, 'gene').visit(tree)
        s = np.sum(~gene_subset)
        logging.info(f'Removed {s} genes')
        data._inplace_subset_var(gene_subset)

class EvaluateFilter(ast.NodeVisitor):
    def __init__(self, data, cell_or_gene):
        self.data = data
        self.use_cells = cell_or_gene == 'cell'
        ast.NodeVisitor.__init__(self)

    def visit_Expression(self, node):
        return self.visit(node.body)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not):
            return np.logical_not(self.visit(node.operand))
        logging.critical("Unary addition, subtraction, and inversion are not supported")
        sys.exit(1)
    
    def visit_BinaryOp(self, node):
        logging.critical("Binary operators are not supported")
        sys.exit(1)

    def visit_BoolOp(self, node):
        if isinstance(node.op, ast.And):
            result = np.logical_and(self.visit(node.values[0]), self.visit(node.values[1]))
            if len(node.values) > 2:
                for i in range(2, len(node.values)):
                    result = np.logical_and(result, node.values[2])
            return result
        elif isinstance(node.op, ast.Or):
            result = np.logical_or(self.visit(node.values[0]), self.visit(node.values[1]))
            if len(node.values) > 2:
                for i in range(2, len(node.values)):
                    result = np.logical_or(result, node.values[2])
            return result
        return None # AND and OR are the only possible BoolOps
    
    def visit_Compare(self, node):
        if len(node.ops) > 1:
            logging.critical("Multiple comparisons (ie, 1 < a < 10) are not allowed")
            sys.exit(1)
        left = self.visit(node.left)
        right = self.visit(node.comparators[0])
        if not isinstance(left, str):
            logging.critical("The left side of a comparison must be an annotation (n_genes > 200, not 200 < n_genes)")
            sys.exit(1)
        return self.filter_data(left, right, node.ops[0])

    def visit_Num(self, node):
        return node.n
    
    def visit_Name(self, node):
        return node.id
    
    def filter_data(self, annotation, target, op):
        if self.use_cells:
            if annotation not in self.data.obs_keys():
                logging.critical(f"Annotation '{annotation}' not present in cells")
                sys.exit(1)
            metric = self.data.obs[annotation]
            return self.apply_filter(metric, target, op)
        else:
            if annotation not in self.data.var_keys():
                logging.critical(f"Annotation '{annotation}' not present in genes")
                sys.exit(1)
            metric = self.data.var[annotation]
            return self.apply_filter(metric, target, op)

    def apply_filter(self, metric, target, op):
        if isinstance(metric.dtype, pd.CategoricalDtype):
            target = str(target)
        elif metric.dtype == bool:
            try:
                t = int(target)
                target = bool(t)
            except ValueError:
                target = target.lower() == 'true'
        if isinstance(op, ast.Eq):
            return metric == target
        if isinstance(op, ast.NotEq):
            return metric != target
        if isinstance(op, ast.Lt):
            return metric < target
        if isinstance(op, ast.LtE):
            return metric <= target
        if isinstance(op, ast.Gt):
            return metric > target
        if isinstance(op, ast.GtE):
            return metric >= target
        logging.critical("The operators is, is not, in, and in not are not supported")
        sys.exit(1)
