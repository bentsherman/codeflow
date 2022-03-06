import argparse
import ast
import astpretty
import astunparse as aup
import pydot



class CFNode:
    def __init__(self, id, lineno=0, label='', type=None, parents=set()):
        self.id = id
        self.lineno = lineno
        self.label = label
        self.type = type
        self.parents = parents
        self.callers = set()

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    def is_hidden(self):
        return not self.label

    def add_parents(self, *args):
        for other in args:
            self.parents.add(other)

    def add_callers(self, *args):
        for v in args:
            self.callers.add(v)



class ControlFlowGraph:
    def __init__(self, verbose=False):
        self.verbose = verbose

    def generate(self, source_text):
        # initialize graph state
        self.nodes = {}
        self.functions = {}
        self.loop_stack = []

        # append start node
        self.cn_start = self.add_node(lineno=0, label='start', type='start')

        # parse syntax tree
        ast_node = ast.parse(source_text)

        # compute control flow graph
        parents = self.walk(ast_node, {self.cn_start})

        # append stop node
        self.cn_stop = self.add_node(lineno=0, label='stop', type='stop', parents=parents)

        return self

    def add_node(self, ast_node=None, lineno=None, label=None, type=None, parents=set()):
        # create node
        id = len(self.nodes)
        cn = CFNode(
            id,
            lineno=lineno if lineno is not None else ast_node.lineno,
            label=label if label is not None else aup.unparse(ast_node).strip(),
            type=type,
            parents=parents)

        # add node to graph
        self.nodes[id] = cn

        return cn

    def walk(self, ast_node, parents):
        if self.verbose:
            print('walk', ast_node.__class__.__name__, {p.id for p in parents})

        # route node to handler based on node type
        fname = 'on_%s' % ast_node.__class__.__name__.lower()
        if hasattr(self, fname):
            return getattr(self, fname)(ast_node, parents)
        else:
            return parents

    def get_function_at(self, lineno):
        # find most recently defined function by line number
        func_name = None
        func_lineno = 0

        for f_name in self.functions:
            f_lineno, _, _ = self.functions[f_name]

            if func_lineno < f_lineno <= lineno:
                func_name = f_name
                func_lineno = f_lineno

        return func_name

    def on_module(self, ast_node, parents):
        '''
        Module(stmt* body, type_ignore* type_ignores)
        '''
        # process each statement in the module
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        return parents

    def on_functiondef(self, ast_node, parents):
        '''
        FunctionDef(identifier name, arguments args,
                    stmt* body, expr* decorator_list, expr? returns,
                    string? type_comment)
        '''
        # append entry node
        cn_enter = self.add_node(
            lineno=ast_node.lineno,
            label='def %s(%s)' % (ast_node.name, ', '.join(a.arg for a in ast_node.args.args)),
            type='def')

        # initialize return nodes
        cn_returns = set()

        # save function def
        self.functions[ast_node.name] = (ast_node.lineno, cn_enter, cn_returns)

        # process each statement in function body
        cn_body = {cn_enter}
        for stmt in ast_node.body:
            cn_body = self.walk(stmt, cn_body)

        # return original parents
        return parents

    def on_return(self, ast_node, parents):
        '''
        Return(expr? value)
        '''
        # retrieve function def
        func_name = self.get_function_at(ast_node.lineno)
        _, _, cn_returns = self.functions[func_name]

        # process return value
        parents = self.walk(ast_node.value, parents)
        cn_value = self.add_node(ast_node, parents=parents)

        # append return value to return nodes
        cn_returns.add(cn_value)

        # return has no immediate children
        return set()

    def on_assign(self, ast_node, parents):
        '''
        Assign(expr* targets, expr value)
        '''
        if len(ast_node.targets) > 1:
            raise NotImplementedError('multiple assignment')

        parents = {self.add_node(ast_node, parents=parents)}
        parents = self.walk(ast_node.value, parents)
        return parents

    def on_for(self, ast_node, parents):
        '''
        For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            lineno=ast_node.lineno,
            label='for %s in %s' % (aup.unparse(ast_node.target).strip(), aup.unparse(ast_node.iter).strip()),
            type='if',
            parents=parents)

        # enter loop body
        cn_exits = {self.add_node(lineno=0, label='', type='if_false', parents={cn_enter})}
        self.loop_stack.append([cn_enter, cn_exits])

        # process each statement in the loop body
        parents = {self.add_node(lineno=0, label='', type='if_true', parents={cn_enter})}
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        # connect end of loop back to loop entry
        cn_enter.add_parents(*parents)

        # exit loop body
        self.loop_stack.pop()

        return cn_exits

    def on_while(self, ast_node, parents):
        '''
        While(expr test, stmt* body, stmt* orelse)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            lineno=ast_node.lineno,
            label='while %s' % (aup.unparse(ast_node.test).strip()),
            type='if',
            parents=parents)

        # enter loop body
        cn_exits = {self.add_node(lineno=0, label='', type='if_false', parents={cn_enter})}
        self.loop_stack.append([cn_enter, cn_exits])

        # process each statement in the loop body
        parents = {self.add_node(lineno=0, label='', type='if_true', parents={cn_enter})}
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        # connect end of loop back to loop entry
        cn_enter.add_parents(*parents)

        # exit loop body
        self.loop_stack.pop()

        # return loop exit nodes
        return cn_exits

    def on_if(self, ast_node, parents):
        '''
        If(expr test, stmt* body, stmt* orelse)
        '''
        # process test expression
        parents = self.walk(ast_node.test, parents)

        # append entry node
        cn_test = self.add_node(
            ast_node.test,
            type='if',
            parents=parents)

        # process each statement in the if branch
        cn_if = {self.add_node(lineno=0, label='', type='if_true', parents={cn_test})}
        for stmt in ast_node.body:
            cn_if = self.walk(stmt, cn_if)

        # process each statement in the else branch
        cn_else = {self.add_node(lineno=0, label='', type='if_false', parents={cn_test})}
        for stmt in ast_node.orelse:
            cn_else = self.walk(stmt, cn_else)

        return cn_if | cn_else

    def on_expr(self, ast_node, parents):
        '''
        Expr(expr body)
        '''
        parents = {self.add_node(ast_node, parents=parents)}
        parents = self.walk(ast_node.value, parents)
        return parents

    def on_pass(self, ast_node, parents):
        '''
        Pass
        '''
        parents = {self.add_node(ast_node, parents=parents)}
        return parents

    def on_break(self, ast_node, parents):
        '''
        Break
        '''
        # retrieve parent loop
        _, cn_exits = self.loop_stack[-1]

        # append break node to loop exit nodes
        cn_break = self.add_node(ast_node, parents=parents)
        cn_exits.add(cn_break)

        # break has no immediate children
        return set()

    def on_continue(self, ast_node, parents):
        '''
        Continue
        '''
        # retrieve parent loop
        cn_enter, _ = self.loop_stack[-1]

        # connect continue node to loop entry
        cn_continue = self.add_node(ast_node, parents=parents)
        cn_enter.add_parents(cn_continue)

        # continue has no other children
        return set()

    def on_binop(self, ast_node, parents):
        '''
        BinOp(expr left, operator op, expr right)
        '''
        cn_left = self.walk(ast_node.left, parents)
        cn_right = self.walk(ast_node.right, cn_left)
        return cn_right

    def on_unaryop(self, ast_node, parents):
        '''
        UnaryOp(unaryop op, expr operand)
        '''
        return self.walk(ast_node.operand, parents)

    def on_compare(self, ast_node, parents):
        '''
        Compare(expr left, cmpop* ops, expr* comparators)
        '''
        cn_left = self.walk(ast_node.left, parents)
        cn_right = self.walk(ast_node.comparators[0], cn_left)
        return cn_right

    def on_call(self, ast_node, parents):
        '''
        Call(expr func, expr* args, keyword* keywords)
        '''
        # process func expression
        mapper = {
            ast.Name:      lambda f: f.id,
            ast.Attribute: lambda f: f.attr,
            ast.Call:      lambda f: f.func
        }
        func_name = ast_node

        while not isinstance(func_name, str):
            func_name = mapper[type(func_name)](func_name)

        # add parents as callers of this function
        _, cn_enter, _ = self.functions[func_name]
        cn_enter.add_callers(*parents)

        # process each arg
        for arg in ast_node.args:
            parents = self.walk(arg, parents)

        return parents

    def to_dot(self, include_calls=False, include_hidden=False, include_start_stop=True):
        def node_peripheries(cn):
            if cn.type in {'start', 'stop', 'def'}:
                return '2'
            return '1'

        def node_shape(cn):
            if cn.type in {'start', 'stop', 'def'}:
                return 'oval'
            if cn.type in {'if'}:
                return 'diamond'
            return 'rectangle'

        def edge_color(cn_src, cn_dst=None):
            colors = {
                'if_true': 'blue',
                'if_false': 'red'
            }
            if cn_src.type in colors:
                return colors[cn_src.type]
            return 'black'

        # initialize graph
        G = pydot.Dot(graph_type='digraph')

        # skip start/stop nodes if enabled
        nodes = self.nodes.values()

        if not include_start_stop:
            nodes = {cn for cn in nodes if cn.type not in {'start', 'stop'}}

        # iterate through control flow nodes
        for cn in nodes:
            # skip hidden nodes if enabled
            if not include_hidden and cn.is_hidden():
                continue

            # add node to dot graph
            G.add_node(pydot.Node(
                cn.id,
                label=cn.label,
                shape=node_shape(cn),
                peripheries=node_peripheries(cn)))

            # connect parents to children
            for cn_parent in cn.parents:
                # get edge color
                color = edge_color(cn_parent)

                # skip hidden parents if enabled
                if not include_hidden:
                    while cn_parent.is_hidden():
                        cn_parent = list(cn_parent.parents)[0]

                # connect node to parent
                G.add_edge(pydot.Edge(
                    cn_parent.id,
                    cn.id,
                    color=color))

            # connect callers to callees if enabled
            if include_calls:
                for cn_caller in cn.callers:
                    G.add_edge(pydot.Edge(
                        cn_caller.id,
                        cn.id,
                        style='dotted'))

        return G

    def print_nodes(self):
        print('%4s %8s %20s %12s %8s' % (
            'id',
            'lineno',
            'label',
            'type',
            'parents'))

        for cn in self.nodes.values():
            print('%4d %8d %20s %12s %8s' % (
                cn.id,
                cn.lineno,
                cn.label,
                cn.type,
                ','.join('%d' % (p.id) for p in cn.parents)))



if __name__ == '__main__':
    # parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('source_files', help='Python source files to visualize', nargs='*')
    parser.add_argument('--source', help='Python source string to visualize')
    parser.add_argument('--format', help='output format (raw, png)', default='png')
    parser.add_argument('--print-ast', help='print abstract syntax tree', action='store_true')
    parser.add_argument('--verbose', help='print verbose output', action='store_true')
    parser.add_argument('--exclude-start-stop', help='exclude start/stop nodes', action='store_true')
    parser.add_argument('--include-calls', help='include caller/callee edges', action='store_true')
    parser.add_argument('--include-hidden', help='include hidden nodes', action='store_true')

    args = parser.parse_args()

    # print flow graph for source string if specified
    if args.source:
        # print ast if specified
        if args.print_ast:
            astpretty.pprint(ast.parse(args.source), indent='  ')

        # generate control flow graph
        G = ControlFlowGraph(verbose=args.verbose)
        G.generate(args.source)

        # print control flow nodes
        if args.verbose:
            print()
            G.print_nodes()

        # convert graph to dot format
        G_dot = G.to_dot(
            include_calls=args.include_calls,
            include_hidden=args.include_hidden,
            include_start_stop=not args.exclude_start_stop)

        # print dot graph if specified
        if args.verbose:
            print()
            print(G_dot.to_string())

    # generate flow graph for each source file
    for source_file in args.source_files:
        print(source_file)

        # load source file
        with open(source_file, 'r') as f:
            source_text = f.read().strip()

        # print ast if specified
        if args.print_ast:
            astpretty.pprint(ast.parse(source_text), indent='  ')

        # generate control flow graph
        G = ControlFlowGraph(verbose=args.verbose)
        G.generate(source_text)

        # print control flow nodes
        if args.verbose:
            print()
            G.print_nodes()

        # convert graph to dot format
        G_dot = G.to_dot(
            include_calls=args.include_calls,
            include_hidden=args.include_hidden,
            include_start_stop=not args.exclude_start_stop)

        # print dot graph if specified
        if args.verbose:
            print()
            print(G_dot.to_string())

        # save graph to file
        ext = args.format
        if ext == 'raw':
            ext = 'dot'
        path = '%s.%s' % (source_file, ext)

        G_dot.write(path, format=args.format)
