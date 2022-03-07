import argparse
import ast
import astpretty
import astunparse as aup
import pydot



class CFNode:
    '''
    CFNode represents a node in a control flow graph.

    :param id       node id in the control flow graph
    :param label    node label, usually the source text
    :param type     node type, used to control visual properties
    :param parents  set of nodes that directly precede this node in the control flow
    :param callers  set of nodes that call this node (if it is callable)

    The node type can be one of the following:
    - def:      function or class definition
    - if:       node that branches based on a condition
    - if_true:  "true" branch of an if-type node
    - if_false: "false" branch of an if-type node
    - start:    global start node
    - stop:     global stop end
    '''
    def __init__(self, id, label='', type=None, parents=set()):
        self.id = id
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
        for other in args:
            self.callers.add(other)



class ControlFlowGraph:
    '''
    A control flow graph models the flow of execution through
    source code. Nodes represent individual statements, while edges
    may represent one of the following relationships:

    - parent: a node is a parent of another node if it directly precedes
              the other node in the flow of execution
    - caller: a node is a caller of another node if it calls the other
              node (the other node must be callable)
    '''
    def __init__(self, verbose=False):
        self.verbose = verbose

    def generate(self, source_text):
        '''
        Construct the control flow graph for a source code string.

        :param source_text
        '''
        # initialize graph state
        self.nodes = {}
        self.functions = {}
        self.stack_class = []
        self.stack_function = []
        self.stack_loop = []

        # append start node
        self.cn_start = self.add_node(label='start', type='start')

        # parse syntax tree
        ast_node = ast.parse(source_text)

        # compute control flow graph
        parents = self.walk(ast_node, {self.cn_start})

        # append stop node
        self.cn_stop = self.add_node(label='stop', type='stop', parents=parents)

        return self

    def add_node(self, ast_node=None, label=None, type=None, parents=set()):
        '''
        Add a node to the control flow graph.

        :param ast_node
        :param label
        :param type
        :param parents
        '''
        # create node
        id = len(self.nodes)
        cn = CFNode(
            id,
            label=label if label is not None else aup.unparse(ast_node).strip(),
            type=type,
            parents=parents)

        # add node to graph
        self.nodes[id] = cn

        return cn

    def walk(self, ast_node, parents):
        '''
        Traverse a node in the abstract syntax tree of the source text.

        :param ast_node
        :param parents
        '''
        # print verbose output if specified
        if self.verbose:
            print('walk', ast_node.__class__.__name__, {p.id for p in parents})

        # route node to handler based on node type
        handler = 'on_%s' % ast_node.__class__.__name__.lower()
        if hasattr(self, handler):
            return getattr(self, handler)(ast_node, parents)
        else:
            return parents

    def to_dot(self, include_calls=False, include_hidden=False, include_start_stop=True):
        '''
        Convert a control flow graph to DOT notation.

        :param include_calls
        :param include_hidden
        :param include_start_stop
        '''
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
        '''
        Print all of the control flow nodes in a table.
        '''
        print('%4s %20s %12s %8s' % (
            'id',
            'label',
            'type',
            'parents'))

        for cn in self.nodes.values():
            print('%4d %20s %12s %8s' % (
                cn.id,
                cn.label,
                cn.type,
                ','.join('%d' % (p.id) for p in cn.parents)))


    '''
    The following section defines control flow handlers
    for all statement types in the Python abstract grammar.
    '''
    def on_module(self, ast_node, parents):
        '''
        Module(stmt* body, type_ignore* type_ignores)
        '''
        # traverse each statement in module body
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        return parents

    def on_functiondef(self, ast_node, parents):
        '''
        FunctionDef(identifier name, arguments args,
                    stmt* body, expr* decorator_list, expr? returns,
                    string? type_comment)
        '''
        # construct function name
        if len(self.stack_class) > 0:
            class_name = self.stack_class[-1]
            func_name = '%s.%s' % (class_name, ast_node.name)
        else:
            func_name = ast_node.name

        # append definition node
        cn_def = self.add_node(
            label='def %s(%s)' % (func_name, ', '.join(a.arg for a in ast_node.args.args)),
            type='def')

        # save function def
        self.functions[func_name] = cn_def

        # enter function body
        self.stack_function.append(func_name)

        # traverse each statement in function body
        cn_body = {cn_def}
        for stmt in ast_node.body:
            cn_body = self.walk(stmt, cn_body)

        # exit function body
        self.stack_function.pop()

        # return original parents
        return parents

    def on_asyncfunctiondef(self, ast_node, parents):
        '''
        AsyncFunctionDef(identifier name, arguments args,
                         stmt* body, expr* decorator_list, expr? returns,
                         string? type_comment)
        '''
        return self.on_functiondef(ast_node, parents)

    def on_classdef(self, ast_node, parents):
        '''
        ClassDef(identifier name,
                 expr* bases,
                 keyword* keywords,
                 stmt* body,
                 expr* decorator_list)
        '''
        # enter class body
        self.stack_class.append(ast_node.name)

        # traverse each statement in class body
        cn_body = set()
        for stmt in ast_node.body:
            cn_body = self.walk(stmt, cn_body)

        # exit class body
        self.stack_class.pop()

        # return original parents
        return parents

    def on_return(self, ast_node, parents):
        '''
        Return(expr? value)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse return value
        parents = self.walk(ast_node.value, parents)

        # return has no immediate children
        return set()

    def on_delete(self, ast_node, parents):
        '''
        Delete(expr* targets)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse delete targets
        for target in ast_node.targets:
            parents = self.walk(target, parents)

        return parents

    def on_assign(self, ast_node, parents):
        '''
        Assign(expr* targets, expr value)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse assignment targets
        for target in ast_node.targets:
            parents = self.walk(target, parents)

        # traverse assignment value
        parents = self.walk(ast_node.value, parents)

        return parents

    def on_augassign(self, ast_node, parents):
        '''
        AugAssign(expr target, operator op, expr value)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse assignment target
        parents = self.walk(ast_node.target, parents)

        # traverse assignment value
        parents = self.walk(ast_node.value, parents)

        return parents

    def on_for(self, ast_node, parents):
        '''
        For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            label='for %s in %s' % (aup.unparse(ast_node.target).strip(), aup.unparse(ast_node.iter).strip()),
            type='if',
            parents=parents)

        # traverse target and iter expressions
        parents = self.walk(ast_node.target, {cn_enter})
        parents = self.walk(ast_node.iter, parents)

        # enter loop body
        cn_exits = {self.add_node(label='', type='if_false', parents=parents)}
        self.stack_loop.append([cn_enter, cn_exits])

        # traverse each statement in loop body
        parents = {self.add_node(label='', type='if_true', parents=parents)}
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        # connect end of loop back to loop entry
        cn_enter.add_parents(*parents)

        # exit loop body
        self.stack_loop.pop()

        # return loop exit nodes
        return cn_exits

    def on_asyncfor(self, ast_node, parents):
        '''
        AsyncFor(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        return self.on_for(ast_node, parents)

    def on_while(self, ast_node, parents):
        '''
        While(expr test, stmt* body, stmt* orelse)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            label='while %s' % (aup.unparse(ast_node.test).strip()),
            type='if',
            parents=parents)

        # traverse test expression
        parents = self.walk(ast_node.test, {cn_enter})

        # enter loop body
        cn_exits = {self.add_node(label='', type='if_false', parents=parents)}
        self.stack_loop.append([cn_enter, cn_exits])

        # traverse each statement in loop body
        parents = {self.add_node(label='', type='if_true', parents=parents)}
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        # connect end of loop back to loop entry
        cn_enter.add_parents(*parents)

        # exit loop body
        self.stack_loop.pop()

        # return loop exit nodes
        return cn_exits

    def on_if(self, ast_node, parents):
        '''
        If(expr test, stmt* body, stmt* orelse)
        '''
        # append entry node
        cn_test = self.add_node(
            label='if %s' % (aup.unparse(ast_node.test).strip()),
            type='if',
            parents=parents)

        # traverse test expression
        parents = self.walk(ast_node.test, {cn_test})

        # traverse each statement in the if branch
        cn_if = {self.add_node(label='', type='if_true', parents=parents)}
        for stmt in ast_node.body:
            cn_if = self.walk(stmt, cn_if)

        # traverse each statement in the else branch
        cn_else = {self.add_node(label='', type='if_false', parents=parents)}
        for stmt in ast_node.orelse:
            cn_else = self.walk(stmt, cn_else)

        return cn_if | cn_else

    def on_with(self, ast_node, parents):
        '''
        With(withitem* items, stmt* body, string? type_comment)
        '''
        # append entry node
        cn_enter = self.add_node(
            label='with %s' % (', '.join(aup.unparse(item).strip() for item in ast_node.items)),
            parents=parents)

        # traverse each statement in the with body
        parents = {cn_enter}
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        return parents

    def on_asyncwith(self, ast_node, parents):
        '''
        AsyncWith(withitem* items, stmt* body, string? type_comment)
        '''
        return self.on_with(ast_node, parents)

    def on_raise(self, ast_node, parents):
        '''
        Raise(expr? exc, expr? cause)
        '''
        return {self.add_node(ast_node, parents=parents)}

    def on_try(self, ast_node, parents):
        '''
        Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
        '''
        # traverse each statement in the try body
        for stmt in ast_node.body:
            parents = self.walk(stmt, parents)

        # traverse each statement in the finally body
        for stmt in ast_node.finalbody:
            parents = self.walk(stmt, parents)

        return parents

    def on_assert(self, ast_node, parents):
        '''
        Assert(expr test, expr? msg)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse test expression
        parents = self.walk(ast_node.test, parents)

        return parents

    def on_import(self, ast_node, parents):
        '''
        Import(alias* names)
        '''
        return {self.add_node(ast_node, parents=parents)}

    def on_importfrom(self, ast_node, parents):
        '''
        ImportFrom(identifier? module, alias* names, int? level)
        '''
        return {self.add_node(ast_node, parents=parents)}

    def on_expr(self, ast_node, parents):
        '''
        Expr(expr body)
        '''
        # append statement node
        parents = {self.add_node(ast_node, parents=parents)}

        # traverse expression body
        parents = self.walk(ast_node.value, parents)

        return parents

    def on_pass(self, ast_node, parents):
        '''
        Pass
        '''
        return {self.add_node(ast_node, parents=parents)}

    def on_break(self, ast_node, parents):
        '''
        Break
        '''
        # retrieve parent loop
        _, cn_exits = self.stack_loop[-1]

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
        cn_enter, _ = self.stack_loop[-1]

        # connect continue node to loop entry
        cn_continue = self.add_node(ast_node, parents=parents)
        cn_enter.add_parents(cn_continue)

        # continue has no other children
        return set()


    '''
    The following section defines control flow handlers
    for all expression types in the Python abstract grammar.

    Since control flow nodes generally correspond to individual
    statements, most expression handlers simply invoke traversals
    of inner expressions for the purpose of tracing function calls.
    '''
    def on_binop(self, ast_node, parents):
        '''
        BinOp(expr left, operator op, expr right)
        '''
        parents = self.walk(ast_node.left, parents)
        parents = self.walk(ast_node.right, parents)
        return parents

    def on_unaryop(self, ast_node, parents):
        '''
        UnaryOp(unaryop op, expr operand)
        '''
        return self.walk(ast_node.operand, parents)

    def on_compare(self, ast_node, parents):
        '''
        Compare(expr left, cmpop* ops, expr* comparators)
        '''
        parents = self.walk(ast_node.left, parents)
        parents = self.walk(ast_node.comparators[0], parents)
        return parents

    def on_call(self, ast_node, parents):
        '''
        Call(expr func, expr* args, keyword* keywords)
        '''
        # add parents as callers of this function
        func_name = aup.unparse(ast_node.func).strip()

        if func_name in self.functions:
            cn_def = self.functions[func_name]
            cn_def.add_callers(*parents)

        # traverse each arg
        for arg in ast_node.args:
            parents = self.walk(arg, parents)

        # traverse each keyword arg
        for keyword in ast_node.keywords:
            parents = self.walk(keyword.value, parents)

        return parents



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
