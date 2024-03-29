
import ast
import astunparse as aup


class CFGNode:
    '''
    CFGNode represents a node in a control flow graph.

    :param id       node id in the control flow graph
    :param label    node label, usually the source text
    :param type     node type, used to control visual properties
    :param preds    set of nodes that directly precede this node in the control flow
    :param callers  set of nodes that call this node (if it is callable)

    The node type can be one of the following:
    - def:      function or class definition
    - if:       node that branches based on a condition
    - if_true:  "true" branch of an if-type node
    - if_false: "false" branch of an if-type node
    - start:    global start node
    - stop:     global stop end
    '''
    def __init__(self, id, label='', type=None, preds=set()):
        self.id = id
        self.label = label
        self.type = type
        self.preds = preds
        self.callers = set()

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    def is_hidden(self):
        return not self.label

    def add_predecessors(self, *args):
        for other in args:
            self.preds.add(other)

    def add_callers(self, *args):
        for other in args:
            self.callers.add(other)


class ControlFlowGraph(ast.NodeVisitor):
    '''
    A control flow graph models the flow of execution through
    source code. Nodes represent individual statements, while edges
    represent one of the following relationships:

    - predecessor: a node directly precedes another node in the flow of execution
    - caller: a node that calls another node (must be callable)
    '''
    def __init__(self, verbose=False):
        self._verbose = verbose

    def build(self, source_text):
        '''
        Build the control flow graph for a source code string.

        :param source_text
        '''
        # initialize graph state
        self._nodes = {}
        self._functions = {}
        self._stack_class = []
        self._stack_function = []
        self._stack_loop = []
        self._stack_preds = [set()]

        # append start node
        self.add_node(label='start', type='start')

        # traverse abstract syntax tree of source text
        self.visit(ast.parse(source_text))

        # append stop node
        self.add_node(label='stop', type='stop')

        return self

    def add_node(self, ast_node=None, label=None, type=None):
        '''
        Add a node to the control flow graph.

        :param ast_node
        :param label
        :param type
        '''
        # create node
        id = len(self._nodes)
        cn = CFGNode(
            id,
            label=label if label is not None else aup.unparse(ast_node).strip(),
            type=type,
            preds=self._stack_preds.pop())

        # add node to graph
        self._nodes[id] = cn

        # update predecessors
        self._stack_preds.append({cn})

        return cn

    def visit(self, ast_node):
        '''
        Traverse a node in the abstract syntax tree of the source text.

        :param ast_node
        '''
        if self._verbose:
            print('walk', ast_node.__class__.__name__, {p.id for p in self._stack_preds[-1]})

        super().visit(ast_node)

    def render(self, include_calls=False, include_hidden=False, include_start_stop=True):
        '''
        Convert a control flow graph to Mermaid notation.

        :param include_calls
        :param include_hidden
        :param include_start_stop
        '''
        # initialize diagram
        lines = []
        lines.append('flowchart TD')

        # skip start/stop nodes if enabled
        nodes = self._nodes.values()

        if not include_start_stop:
            nodes = {cn for cn in nodes if cn.type not in {'start', 'stop'}}

        # iterate through control flow nodes
        for cn in nodes:
            # skip hidden nodes if enabled
            if not include_hidden and cn.is_hidden():
                continue

            # add node to mmd graph
            if cn.type in {'start', 'stop', 'def'}:
                lines.append('    p%d((("%s")))' % (cn.id, cn.label))
            elif cn.type in {'if'}:
                lines.append('    p%d{"%s"}' % (cn.id, cn.label))
            else:
                lines.append('    p%d("%s")' % (cn.id, cn.label))

            # connect predecessors to node
            for cn_pred in cn.preds:
                # get edge type
                cn_pred_type = cn_pred.type

                # skip hidden predecessors if enabled
                if not include_hidden:
                    while cn_pred.is_hidden():
                        cn_pred = list(cn_pred.preds)[0]

                # connect node to predecessor
                if cn_pred_type == 'if_true':
                    lines.append('    p%d -->|True| p%d' % (cn_pred.id, cn.id))
                elif cn_pred_type == 'if_false':
                    lines.append('    p%d -->|False| p%d' % (cn_pred.id, cn.id))
                else:
                    lines.append('    p%d --> p%d' % (cn_pred.id, cn.id))

            # connect callers to callees if enabled
            if include_calls:
                for cn_caller in cn.callers:
                    lines.append('    p%d -.-> p%d' % (cn_caller.id, cn.id))

        return '\n'.join(lines)

    def print_nodes(self):
        '''
        Print all of the control flow nodes in a table.
        '''
        print('%4s %20s %12s %8s' % (
            'id',
            'label',
            'type',
            'preds'))

        for cn in self._nodes.values():
            print('%4d %20s %12s %8s' % (
                cn.id,
                cn.label,
                cn.type,
                ','.join('%d' % (p.id) for p in cn.preds)))


    '''
    The following section defines custom visitor methods
    for statement types in the Python abstract grammar.
    '''
    def visit_FunctionDef(self, ast_node):
        '''
        FunctionDef(identifier name, arguments args,
                    stmt* body, expr* decorator_list, expr? returns,
                    string? type_comment)
        '''
        # construct function name
        if len(self._stack_class) > 0:
            class_name = self._stack_class[-1]
            func_name = '%s.%s' % (class_name, ast_node.name)
        else:
            func_name = ast_node.name

        # enter function body
        self._stack_function.append(func_name)
        self._stack_preds.append(set())

        # append definition node
        self._functions[func_name] = self.add_node(
            label='def %s(%s)' % (func_name, ', '.join(a.arg for a in ast_node.args.args)),
            type='def')

        # visit each statement in function body
        for stmt in ast_node.body:
            self.visit(stmt)

        # exit function body
        self._stack_function.pop()
        self._stack_preds.pop()

    def visit_AsyncFunctionDef(self, ast_node):
        '''
        AsyncFunctionDef(identifier name, arguments args,
                         stmt* body, expr* decorator_list, expr? returns,
                         string? type_comment)
        '''
        return self.visit_FunctionDef(ast_node)

    def visit_ClassDef(self, ast_node):
        '''
        ClassDef(identifier name,
                 expr* bases,
                 keyword* keywords,
                 stmt* body,
                 expr* decorator_list)
        '''
        # enter class body
        self._stack_class.append(ast_node.name)
        self._stack_preds.append(set())

        # append definition node
        self.add_node(
            label='class %s' % (ast_node.name),
            type='def')

        # visit each statement in class body
        for stmt in ast_node.body:
            self.visit(stmt)

        # exit class body
        self._stack_class.pop()
        self._stack_preds.pop()

    def visit_Return(self, ast_node):
        '''
        Return(expr? value)
        '''
        # append statement node
        self.add_node(ast_node)

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_Delete(self, ast_node):
        '''
        Delete(expr* targets)
        '''
        # append statement node
        self.add_node(ast_node)

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_Assign(self, ast_node):
        '''
        Assign(expr* targets, expr value)
        '''
        # append statement node
        self.add_node(ast_node)

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_AugAssign(self, ast_node):
        '''
        AugAssign(expr target, operator op, expr value)
        '''
        # append statement node
        self.add_node(ast_node)

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_For(self, ast_node):
        '''
        For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            label='for %s in %s' % (aup.unparse(ast_node.target).strip(), aup.unparse(ast_node.iter).strip()),
            type='if')

        # visit target and iter expressions
        self.visit(ast_node.target)
        self.visit(ast_node.iter)

        # enter loop body
        cn_exits = {self.add_node(label='', type='if_false')}
        self._stack_loop.append([cn_enter, cn_exits])

        # visit each statement in loop body
        self.add_node(label='', type='if_true')

        for stmt in ast_node.body:
            self.visit(stmt)

        # connect end of loop back to loop entry
        cn_enter.add_predecessors(*self._stack_preds.pop())

        # exit loop body
        self._stack_loop.pop()
        self._stack_preds.append(cn_exits)

    def visit_AsyncFor(self, ast_node):
        '''
        AsyncFor(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        return self.visit_For(ast_node)

    def visit_While(self, ast_node):
        '''
        While(expr test, stmt* body, stmt* orelse)
        '''
        # append loop entry node
        cn_enter = self.add_node(
            label='while %s' % (aup.unparse(ast_node.test).strip()),
            type='if')

        # visit test expression
        self.visit(ast_node.test)

        # enter loop body
        cn_exits = {self.add_node(label='', type='if_false')}
        self._stack_loop.append([cn_enter, cn_exits])

        # visit each statement in loop body
        self.add_node(label='', type='if_true')

        for stmt in ast_node.body:
            self.visit(stmt)

        # connect end of loop back to loop entry
        cn_enter.add_predecessors(*self._stack_preds.pop())

        # exit loop body
        self._stack_loop.pop()
        self._stack_preds.append(cn_exits)

    def visit_If(self, ast_node):
        '''
        If(expr test, stmt* body, stmt* orelse)
        '''
        # append entry node
        self.add_node(
            label='if %s' % (aup.unparse(ast_node.test).strip()),
            type='if')

        # visit test expression
        self.visit(ast_node.test)

        # visit each statement in the if branch
        self._stack_preds.append(self._stack_preds[-1])
        self.add_node(label='', type='if_true')

        for stmt in ast_node.body:
            self.visit(stmt)

        cn_if = self._stack_preds.pop()

        # visit each statement in the else branch
        self.add_node(label='', type='if_false')

        for stmt in ast_node.orelse:
            self.visit(stmt)

        cn_else = self._stack_preds.pop()

        # combine nodes from both branches
        self._stack_preds.append(cn_if | cn_else)

    def visit_With(self, ast_node):
        '''
        With(withitem* items, stmt* body, string? type_comment)
        '''
        # append with entry node
        self.add_node(
            label='with %s' % (', '.join(aup.unparse(item).strip() for item in ast_node.items)))

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_AsyncWith(self, ast_node):
        '''
        AsyncWith(withitem* items, stmt* body, string? type_comment)
        '''
        return self.visit_With(ast_node)

    def visit_Raise(self, ast_node):
        '''
        Raise(expr? exc, expr? cause)
        '''
        self.add_node(ast_node)

    def visit_Try(self, ast_node):
        '''
        Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
        '''
        # visit each statement in the try body
        for stmt in ast_node.body:
            self.visit(stmt)

        # visit each statement in the finally body
        for stmt in ast_node.finalbody:
            self.visit(stmt)

    def visit_Assert(self, ast_node):
        '''
        Assert(expr test, expr? msg)
        '''
        # append statement node
        self.add_node(ast_node)

        # visit child nodes
        self.generic_visit(ast_node)

    def visit_Import(self, ast_node):
        '''
        Import(alias* names)
        '''
        self.add_node(ast_node)

    def visit_ImportFrom(self, ast_node):
        '''
        ImportFrom(identifier? module, alias* names, int? level)
        '''
        self.add_node(ast_node)

    def visit_Expr(self, ast_node):
        '''
        Expr(expr body)
        '''
        # determine whether expression has side-effects
        has_effect = False

        for node in ast.walk(ast_node):
            if node.__class__.__name__ in {'Yield', 'YieldFrom', 'Call'}:
                has_effect = True
                break

        # append statement node if expression has side-effects
        if has_effect:
            self.add_node(ast_node)
            self.generic_visit(ast_node)

    def visit_Pass(self, ast_node):
        '''
        Pass
        '''
        self.add_node(ast_node)

    def visit_Break(self, ast_node):
        '''
        Break
        '''
        # retrieve parent loop
        _, cn_exits = self._stack_loop[-1]

        # append break node to loop exit nodes
        cn_exits.add(self.add_node(ast_node))

        # break has no immediate children
        self._stack_preds[-1] = set()

    def visit_Continue(self, ast_node):
        '''
        Continue
        '''
        # retrieve parent loop
        cn_enter, _ = self._stack_loop[-1]

        # connect continue node to loop entry
        cn_enter.add_predecessors(self.add_node(ast_node))

        # continue has no other children
        self._stack_preds[-1] = set()


    '''
    The following section defines custom visitor methods
    for expression types in the Python abstract grammar.
    '''
    def visit_Call(self, ast_node):
        '''
        Call(expr func, expr* args, keyword* keywords)
        '''
        # add predecessors as callers of this function
        func_name = aup.unparse(ast_node.func).strip()

        if func_name in self._functions:
            self._functions[func_name].add_callers(*self._stack_preds[-1])

        # visit child nodes
        self.generic_visit(ast_node)
