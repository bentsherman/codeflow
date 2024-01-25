#!/usr/bin/env python3
import argparse
import ast
import astpretty

import codeflow.cfg as cfg
import codeflow.dfg as dfg


def create_cfg(source_text, **kwargs):
    # build control flow graph
    G = cfg.ControlFlowGraph(verbose=kwargs['verbose'])
    G.build(source_text)

    # print control flow nodes
    if kwargs['verbose']:
        print()
        G.print_nodes()

    # convert graph to mmd format
    G_mmd = G.to_mmd(
        include_calls=kwargs['include_calls'],
        include_hidden=kwargs['include_hidden'],
        include_start_stop=not kwargs['exclude_start_stop'])

    # print mmd diagram
    print(G_mmd)


def create_dfg(source_text, **kwargs):
    # build data flow graph
    G = dfg.DataFlowGraph(verbose=kwargs['verbose'])
    G.build(source_text)

    # print data flow nodes
    if kwargs['verbose']:
        print()
        G.print_nodes()

    # convert graph to mmd format
    G_mmd = G.to_mmd()

    # print mmd diagram
    print(G_mmd)


def main():
    # parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('source_files', help='Python source files to visualize', nargs='*')
    parser.add_argument('--source', help='Python source string to visualize')
    parser.add_argument('--type', help='Type of graph to build (cfg, dfg)', choices=['cfg', 'dfg'], default='dfg')
    parser.add_argument('--print-ast', help='print abstract syntax tree', action='store_true')
    parser.add_argument('--verbose', help='print verbose output', action='store_true')
    parser.add_argument('--exclude-start-stop', help='exclude start/stop nodes', action='store_true')
    parser.add_argument('--include-calls', help='include caller/callee edges', action='store_true')
    parser.add_argument('--include-hidden', help='include hidden nodes', action='store_true')

    args = parser.parse_args()
    kwargs = vars(args)

    # print flow graph for source string if specified
    if args.source:
        # print ast if specified
        if args.print_ast:
            astpretty.pprint(ast.parse(args.source), indent='  ')

        # create specified flow graph
        if args.type == 'cfg':
            create_cfg(args.source, **kwargs)

        if args.type == 'dfg':
            create_dfg(args.source, **kwargs)

    # print flow graph for each source file
    for source_file in args.source_files:
        if len(args.source_files) > 1:
            print(source_file)

        # load source file
        with open(source_file, 'r') as f:
            source_text = f.read().strip()

        # print ast if specified
        if args.print_ast:
            astpretty.pprint(ast.parse(source_text), indent='  ')

        # create specified flow graph
        if args.type == 'cfg':
            create_cfg(source_text, **kwargs)

        if args.type == 'dfg':
            create_dfg(source_text, **kwargs)


if __name__ == '__main__':
    main()
