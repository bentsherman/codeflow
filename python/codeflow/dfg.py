
import ast
import astunparse as aup

from ordered_set import OrderedSet


class DFNode:
    '''
    DFNode represents a node in a data flow graph.

    :param id     node id in the data flow graph
    :param label  node label, usually the source text
    :param type   node type, used to control visual properties
    :param preds  node predecessors

    The node type can be one of the following:
    - constant: constant value
    - name:     named value (variable, function def, class def)
    - op:       function call or operator
    '''
    def __init__(self, id, label='', type=None, preds=OrderedSet()):
        self.id = id
        self.label = label
        self.type = type
        self.preds = OrderedSet(preds)

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return self.id == other.id

    def is_hidden(self):
        return self.type in {'constant'}

    def add_predecessors(self, *args):
        for dn in args:
            self.preds.add(dn)


class DataFlowGraph(ast.NodeVisitor):
    '''
    A data flow graph models the flow of data through source code.
    A node represents a literal value, a variable, or a function, while
    an edge represents an input/output dependency between two nodes.
    '''
    def __init__(self, verbose=False):
        self._verbose = verbose

    def build(self, source_text):
        '''
        Build the data flow graph for a source code string.

        :param source_text
        '''
        # initialize graph state
        self._nodes = {}
        self._stack_class = []
        self._stack_names = [{}]
        self._stack_preds = [OrderedSet()]

        # traverse abstract syntax tree of source text
        self.visit(ast.parse(source_text))

        return self

    def visit(self, ast_node):
        '''
        Traverse a node in the abstract syntax tree of the source text.

        :param ast_node
        '''
        if self._verbose:
            print('walk', ast_node.__class__.__name__, {p.id for p in self._stack_preds[-1]})

        super().visit(ast_node)

    def get_symbol(self, name):
        '''
        Get a variable node from the name table.

        :param name
        '''
        for names in self._stack_names[::-1]:
            if name in names:
                return names[name]

        return None

    def put_symbol(self, name, dn):
        '''
        Put a variable node into the name table.

        :param name
        '''
        for names in self._stack_names[::-1]:
            if name in names:
                names[name] = dn
                return

        self._stack_names[-1][name] = dn

    def visit_with_preds(self, *ast_nodes):
        '''
        Traverse a set of nodes and extract predecessor nodes.

        :param ast_nodes
        '''
        self._stack_preds.append(OrderedSet())

        for ast_node in ast_nodes:
            if ast_node:
                self.visit(ast_node)

        return self._stack_preds.pop()

    def add_node(self, label=None, type=None, preds=OrderedSet()):
        '''
        Add a node to the data flow graph.

        :param label
        :param type
        :param preds
        '''
        # create node
        id = len(self._nodes)
        dn = DFNode(id, label=label, type=type, preds=preds)

        # add node to graph
        self._nodes[id] = dn

        # update predecessors
        self._stack_preds[-1].add(dn)

        return dn

    def to_mmd(self):
        '''
        Convert a data flow graph to Mermaid notation.

        :param include_hidden
        '''
        # initialize diagram
        lines = []
        lines.append('flowchart TD')

        # render each node
        for dn in self._nodes.values():
            label = dn.label \
                .replace('\n', '\\n') \
                .replace('\"', '\\"')

            lines.append('    p%d("%s")' % (dn.id, label))

        # render each edge
        for dn in self._nodes.values():
            for dn_pred in dn.preds:
                lines.append('    p%d --> p%d' % (dn_pred.id, dn.id))

        return '\n'.join(lines)

    def print_nodes(self):
        '''
        Print all of the data flow nodes in a table.
        '''
        print('%4s %20s %12s %8s' % (
            'id',
            'label',
            'type',
            'preds'))

        for dn in self._nodes.values():
            print('%4d %20s %12s %8s' % (
                dn.id,
                dn.label,
                dn.type,
                ','.join(p.label for p in dn.preds)))


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
        if len(self._stack_class) > 0:
            label = '%s.%s' % (self._stack_class[-1], ast_node.name)
        else:
            label = ast_node.name

        self._stack_names.append({})
        preds = self.visit_with_preds(*ast_node.body)
        self._stack_names.pop()

        dn = self.add_node(label=label, type='name', preds=preds)
        self.put_symbol(label, dn)

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
        self._stack_class.append(ast_node.name)
        self._stack_names.append({})
        label = ast_node.name
        preds = self.visit_with_preds(*ast_node.bases, *ast_node.keywords, *ast_node.body)
        self._stack_class.pop()
        self._stack_names.pop()

        dn = self.add_node(label=label, type='name', preds=preds)
        self.put_symbol(label, dn)

    def visit_Delete(self, ast_node):
        '''
        Delete(expr* targets)
        '''
        label = 'del'
        preds = self.visit_with_preds(*ast_node.targets)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Assign(self, ast_node):
        '''
        Assign(expr* targets, expr value)
        '''
        # traverse value and targets
        inputs = self.visit_with_preds(ast_node.value)
        outputs = self.visit_with_preds(*ast_node.targets)

        # connect value to targets
        for dn in outputs:
            dn.add_predecessors(*inputs)

        # update predecessors
        for dn in outputs:
            self._stack_preds[-1].add(dn)

    def visit_AugAssign(self, ast_node):
        '''
        AugAssign(expr target, operator op, expr value)
        '''
        # append op node
        ast_node.target.ctx = ast.Load()
        dn = self.add_node(
            label=aup.Unparser.binop[ast_node.op.__class__.__name__],
            type='op',
            preds=self.visit_with_preds(ast_node.target, ast_node.value))
        ast_node.target.ctx = ast.Store()

        # append target node
        label = aup.unparse(ast_node.target).strip()
        self.put_symbol(label, self.add_node(label=label, type='name', preds={dn}))

    def visit_For(self, ast_node):
        '''
        For(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        self._stack_names.append({})
        label = 'for'
        preds = self.visit_with_preds(ast_node.target, ast_node.iter, *ast_node.body, *ast_node.orelse)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_AsyncFor(self, ast_node):
        '''
        AsyncFor(expr target, expr iter, stmt* body, stmt* orelse, string? type_comment)
        '''
        return self.visit_For(ast_node)

    def visit_While(self, ast_node):
        '''
        While(expr test, stmt* body, stmt* orelse)
        '''
        label = 'while'
        preds = self.visit_with_preds(ast_node.test, *ast_node.body, *ast_node.orelse)

        self.add_node(label=label, type='op', preds=preds)

    def visit_If(self, ast_node):
        '''
        If(expr test, stmt* body, stmt* orelse)
        '''
        # determine predecessors for condition and true, false branches
        test = self.visit_with_preds(ast_node.test)[0]
        preds_true = self.visit_with_preds(*ast_node.body)
        preds_false = self.visit_with_preds(*ast_node.orelse)

        # determine shared branch outputs
        outs_true = set(dn.label for dn in preds_true if dn.type == 'name')
        outs_false = set(dn.label for dn in preds_false if dn.type == 'name')
        outputs = outs_true.intersection(outs_false)
        preds_true = [dn for dn in preds_true if dn.label in outputs]
        preds_false = [dn for dn in preds_false if dn.label in outputs]

        # append if node
        dn_true = self.add_node(label='true', type='op', preds=preds_true)
        dn_false = self.add_node(label='false', type='op', preds=preds_false)
        dn_if = self.add_node(label='if', type='op', preds=[test, dn_true, dn_false])

        for output in outputs:
            self.put_symbol(output, self.add_node(label=output, type='name', preds=[dn_if]))

    def visit_With(self, ast_node):
        '''
        With(withitem* items, stmt* body, string? type_comment)
        '''
        self._stack_names.append({})
        label = 'with'
        preds = self.visit_with_preds(*ast_node.items, *ast_node.body)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_AsyncWith(self, ast_node):
        '''
        AsyncWith(withitem* items, stmt* body, string? type_comment)
        '''
        return self.visit_With(ast_node)

    def visit_Try(self, ast_node):
        '''
        Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)
        '''
        label = 'try'
        preds = self.visit_with_preds(*ast_node.body, *ast_node.finalbody)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Assert(self, ast_node):
        '''
        Assert(expr test, expr? msg)
        '''
        label = 'assert'
        preds = self.visit_with_preds(ast_node.test)

        self.add_node(label=label, type='op', preds=preds)


    '''
    The following section defines custom visitor methods
    for expression types in the Python abstract grammar.
    '''
    def visit_BoolOp(self, ast_node):
        '''
        BoolOp(boolop op, expr* values)
        '''
        label = aup.Unparser.boolops[ast_node.op.__class__]
        preds = self.visit_with_preds(*ast_node.values)

        self.add_node(label=label, type='op', preds=preds)

    def visit_BinOp(self, ast_node):
        '''
        BinOp(expr left, operator op, expr right)
        '''
        label = aup.Unparser.binop[ast_node.op.__class__.__name__]
        preds = self.visit_with_preds(ast_node.left, ast_node.right)

        self.add_node(label=label, type='op', preds=preds)

    def visit_UnaryOp(self, ast_node):
        '''
        UnaryOp(unaryop op, expr operand)
        '''
        label = aup.Unparser.unop[ast_node.op.__class__.__name__]
        preds = self.visit_with_preds(ast_node.operand)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Lambda(self, ast_node):
        '''
        Lambda(arguments args, expr body)
        '''
        self._stack_names.append({})
        label = aup.unparse(ast_node).strip()
        preds = self.visit_with_preds(ast_node.args, ast_node.body)
        self._stack_names.pop()

        self.add_node(label=label, type='name', preds=preds)

    def visit_IfExp(self, ast_node):
        '''
        IfExp(expr test, expr body, expr orelse)
        '''
        label = '{} ? {} : {}'
        preds = self.visit_with_preds(ast_node.test, ast_node.body, ast_node.orelse)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Dict(self, ast_node):
        '''
        Dict(expr* keys, expr* values)
        '''
        label = '{:}'
        preds = self.visit_with_preds(*ast_node.keys, *ast_node.values)

        self.add_node(label=label, type='constant', preds=preds)

    def visit_Set(self, ast_node):
        '''
        Set(expr* elts)
        '''
        label = '{}'
        preds = self.visit_with_preds(*ast_node.elts)

        self.add_node(label=label, type='constant', preds=preds)

    def visit_ListComp(self, ast_node):
        '''
        ListComp(expr elt, comprehension* generators)
        '''
        self._stack_names.append({})
        label = '[...]'
        preds = self.visit_with_preds(*ast_node.generators, ast_node.elt)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_SetComp(self, ast_node):
        '''
        SetComp(expr elt, comprehension* generators)
        '''
        self._stack_names.append({})
        label = '{...}'
        preds = self.visit_with_preds(*ast_node.generators, ast_node.elt)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_DictComp(self, ast_node):
        '''
        DictComp(expr key, expr value, comprehension* generators)
        '''
        self._stack_names.append({})
        label = '{...}'
        preds = self.visit_with_preds(*ast_node.generators, ast_node.key, ast_node.value)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_GeneratorExp(self, ast_node):
        '''
        GeneratorExp(expr elt, comprehension* generators)
        '''
        self._stack_names.append({})
        label = '(...)'
        preds = self.visit_with_preds(*ast_node.generators, ast_node.elt)
        self._stack_names.pop()

        self.add_node(label=label, type='op', preds=preds)

    def visit_Compare(self, ast_node):
        '''
        Compare(expr left, cmpop* ops, expr* comparators)
        '''
        label = ','.join(aup.Unparser.cmpops[op.__class__.__name__] for op in ast_node.ops)
        preds = self.visit_with_preds(ast_node.left, *ast_node.comparators)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Call(self, ast_node):
        '''
        Call(expr func, expr* args, keyword* keywords)
        '''
        # append '()' to func node
        # TODO: prevent duplicate append '()' on each call
        dn_func = self.visit_with_preds(ast_node.func)[0]
        preds = self.visit_with_preds(*ast_node.args, *ast_node.keywords)

        dn_func.label = '%s()' % (dn_func.label)
        dn_func.add_predecessors(*preds)

        # update predecessors
        self._stack_preds[-1].add(dn_func)

    def visit_Num(self, ast_node):
        '''
        Num(object n)
        '''
        self.add_node(label=str(ast_node.n), type='constant')

    def visit_Str(self, ast_node):
        '''
        Str(string s)
        '''
        self.add_node(label='\'%s\'' % (ast_node.s), type='constant')

    def visit_JoinedStr(self, ast_node):
        '''
        JoinedStr(expr* values)
        '''
        label = '\'%s\'' % (''.join(v.s if isinstance(v, ast.Str) else '{}' for v in ast_node.values))
        preds = self.visit_with_preds(*[v for v in ast_node.values if isinstance(v, ast.FormattedValue)])

        self.add_node(label=label, type='constant', preds=preds)

    def visit_Bytes(self, ast_node):
        '''
        Bytes(bytes s)
        '''
        self.add_node(label=str(ast_node.s), type='constant')

    def visit_NameConstant(self, ast_node):
        '''
        NameConstant(singleton value)
        '''
        self.add_node(label=str(ast_node.value), type='constant')

    def visit_Attribute(self, ast_node):
        '''
        Attribute(expr value, identifier attr, expr_context ctx)
        '''
        label = '.%s' % (ast_node.attr)
        preds = self.visit_with_preds(ast_node.value)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Subscript(self, ast_node):
        '''
        Subscript(expr value, slice slice, expr_context ctx)
        '''
        label = '.[]'
        preds = self.visit_with_preds(ast_node.value, ast_node.slice)

        self.add_node(label=label, type='op', preds=preds)

    def visit_Name(self, ast_node):
        '''
        Name(identifier id, expr_context ctx)
        '''
        # add variable in load context to name table (if not present)
        if ast_node.ctx.__class__ in {ast.Load, ast.Del}:
            label = aup.unparse(ast_node).strip()
            dn = self.get_symbol(label)
            if dn:
                self._stack_preds[-1].add(dn)
            else:
                self.put_symbol(label, self.add_node(label=label, type='name'))

        # add variable in store context to name table (overwrite any existing variable)
        elif isinstance(ast_node.ctx, ast.Store):
            label = aup.unparse(ast_node).strip()
            self.put_symbol(label, self.add_node(label=label, type='name'))

        else:
            self.generic_visit(ast_node)

    def visit_List(self, ast_node):
        '''
        List(expr* elts, expr_context ctx)
        '''
        if isinstance(ast_node.ctx, ast.Load):
            label = '[]'
            preds = self.visit_with_preds(*ast_node.elts)

            self.add_node(label=label, type='constant', preds=preds)

        else:
            self.generic_visit(ast_node)

    def visit_Tuple(self, ast_node):
        '''
        Tuple(expr* elts, expr_context ctx)
        '''
        if isinstance(ast_node.ctx, ast.Load):
            label = '()'
            preds = self.visit_with_preds(*ast_node.elts)

            self.add_node(label=label, type='constant', preds=preds)

        else:
            self.generic_visit(ast_node)

    def visit_Slice(self, ast_node):
        '''
        Slice(expr? lower, expr? upper, expr? step)
        ExtSlice(slice* dims)
        '''
        label = '::'
        preds = self.visit_with_preds(ast_node.lower, ast_node.upper, ast_node.step)

        self.add_node(label=label, type='constant', preds=preds)

    def visit_arg(self, ast_node):
        '''
        arg(identifier arg, expr? annotation)
        '''
        label = ast_node.arg
        self._stack_names[-1][label] = self.add_node(label=label, type='name')
