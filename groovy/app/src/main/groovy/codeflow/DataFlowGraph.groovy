
package codeflow

import groovy.transform.CompileStatic
import groovy.transform.EqualsAndHashCode
import groovy.transform.TupleConstructor
import org.codehaus.groovy.ast.*
import org.codehaus.groovy.ast.builder.AstBuilder
import org.codehaus.groovy.ast.expr.*
import org.codehaus.groovy.ast.stmt.*
import org.codehaus.groovy.control.CompilePhase
import org.codehaus.groovy.control.SourceUnit

@CompileStatic
class DataFlowGraph extends ClassCodeVisitorSupport {
    private Map<String,Node> inputs = [:]
    private Set<String> outputs = []
    private Map<String,DataFlowGraph> methods = [:]
    private Map<Integer,Node> nodes = [:]
    private List<String> stackClass = []
    private List<Map<String,Node>> stackNames = [ [:] as Map ]
    private List<Set<Node>> stackPreds = [ new LinkedHashSet<>() ]

    DataFlowGraph() {
    }

    static DataFlowGraph fromString(String sourceText) {
        final dfg = new DataFlowGraph()

        // build abstract syntax tree of source text
        final astNodes = new AstBuilder().buildFromString(CompilePhase.CONVERSION, false, sourceText)

        // visit script node
        astNodes[0].visit(dfg)

        // visit methods of script wrapper class
        // skip auto-generated methods
        final methodNodes = ((ClassNode)astNodes[1]).getMethods()
        for( def methodNode : methodNodes.subList(2, methodNodes.size()) )
            dfg.visitMethod(methodNode)

        return dfg
    }

    private static DataFlowGraph fromAstNodes(Collection<String> inputs, ASTNode... astNodes) {
        final dfg = new DataFlowGraph()

        dfg.inputs = inputs.inject([:], (acc, name) -> { acc[name] = null ; acc })

        for( def astNode : astNodes )
            astNode.visit(dfg)

        return dfg
    }

    private Node getSymbol(String name) {
        // get a variable node from the name table
        for( Map scope : stackNames.reverse() )
            if( name in scope )
                return scope[name]

        return null
    }

    private void putSymbol(String name, Node dn) {
        if( inputs.containsKey(name) && inputs[name] == null )
            inputs[name] = dn

        // put a variable node into the name table
        for( Map scope : stackNames.reverse() ) {
            if( name in scope ) {
                scope[name] = dn
                return
            }
        }

        stackNames.last().put(name, dn)
    }

    private Set<Node> visitWithPreds(ASTNode[] astNodes) {
        visitWithPreds(astNodes.toList())
    }

    private Set<Node> visitWithPreds(Collection<? extends ASTNode> astNodes) {
        // traverse a set of nodes and extract predecessor nodes
        stackPreds << new LinkedHashSet<>()

        for( def astNode : astNodes )
            if( astNode != null )
                astNode.visit(this)

        return stackPreds.removeLast()
    }

    private Node addNode(String label, Node.Type type, Set preds=null, boolean updatePreds=true) {
        // create node
        final id = nodes.size()
        final dn = new Node(
            id,
            label,
            type,
            preds ?: new LinkedHashSet<>())

        // add node to graph
        nodes[id] = dn

        // update predecessors
        if( updatePreds )
            stackPreds.last() << dn

        return dn
    }

    String render() {
        // initialize diagram
        List<String> lines = []
        lines << "flowchart TD"

        // render body
        renderBody('main', lines)

        // render each method definition
        int i = 1
        methods.each { name, subgraph ->
            subgraph.renderBody(name, lines, "f${i}_")
            i++
        }

        return lines.join('\n')
    }

    private void renderBody(String name, List<String> lines, String prefix='') {
        lines << "    subgraph ${name}".toString()

        // prepare inputs and outputs
        final inputs = inputs.values()
        final outputs = outputs.collect( v -> getSymbol(v) )

        // render inputs
        if( inputs.size() > 0 ) {
            lines << '    subgraph " "'
            for( def dn : inputs )
                lines << "    ${prefix}v${dn.id}(\"${dn.label}\")".toString()
            lines << '    end'
        }

        // render nodes
        for( def dn : nodes.values() ) {
            if( dn in inputs || dn in outputs )
                continue

            final label = dn.label
                .replaceAll('\n', '\\\\\n')
                .replaceAll('\"', '\\\\\"')

            lines << "    ${prefix}v${dn.id}(\"${label}\")".toString()
        }

        // render outputs
        if( outputs.size() > 0 ) {
            lines << '    subgraph " "'
            for( def dn : outputs )
                lines << "    ${prefix}v${dn.id}(\"${dn.label}\")".toString()
            lines << '    end'
        }

        // render edges
        for( def dn : nodes.values() )
            for( def dnPred : dn.preds )
                lines << "    ${prefix}v${dnPred.id} --> ${prefix}v${dn.id}".toString()

        lines << '    end'
    }

    /// STATEMENTS

    @Override
    void visitBlockStatement(BlockStatement block) {
        for( def stmt : block.statements )
            stmt.visit(this)
    }

    @Override
    void visitClass(ClassNode node) {
        // visit class contents
        stackClass << node.name
        stackNames << [:]

        final preds = visitWithPreds( node.methods )

        stackClass.removeLast()
        stackNames.removeLast()

        // add class node to graph
        final label = node.name
        final dn = addNode(label, Node.Type.NAME, preds)
        putSymbol(label, dn)
    }

    @Override
    void visitIfElse(IfStatement stmt) {
        final label = 'if'
        final preds = visitWithPreds(
            stmt.booleanExpression,
            stmt.ifBlock,
            stmt.elseBlock
        )

        addNode(label, Node.Type.OP, preds)
    }

    @Override
    void visitMethod(MethodNode method) {
        // get method name
        final name = stackClass.size() > 0
            ? "${stackClass.last()}.${method.name}".toString()
            : method.name

        // build subgraph of method definition
        final inputs = method.parameters.collect( p -> p.name )
        methods[name] = DataFlowGraph.fromAstNodes(inputs, method.code)
    }

    @Override
    void visitReturnStatement(ReturnStatement stmt) {
        if( stmt.expression instanceof VariableExpression ) {
            final var = (VariableExpression)stmt.expression
            outputs << var.name
        }

        super.visitReturnStatement(stmt)
    }

    /// EXPRESSIONS

    private boolean withinOutput = false

    void visitAssignment(BinaryExpression expr) {
        // traverse input expression
        final inputs = visitWithPreds(expr.rightExpression)

        // traverse output expression
        // TODO: what about array/map/object assignment ?
        withinOutput = true
        final outputs = visitWithPreds(expr.leftExpression)
        withinOutput = false

        // connect inputs to outputs
        for( def dn : outputs )
            dn.addPredecessors(inputs)

        // update predecessors
        for( def dn : outputs )
            stackPreds.last() << dn
    }

    @Override
    void visitBinaryExpression(BinaryExpression expr) {
        final op = expr.operation.text
        if( op == '=' ) {
            visitAssignment(expr)
            return
        }

        def lhs = '_'
        def rhs = '_'
        Set<Node> preds = []

        if( expr.leftExpression instanceof ConstantExpression ) {
            lhs = expr.leftExpression.text
            preds.addAll(visitWithPreds(expr.rightExpression))
        }

        if( expr.rightExpression instanceof ConstantExpression ) {
            rhs = expr.rightExpression.text
            preds.addAll(visitWithPreds(expr.leftExpression))
        }

        def label
        if( preds.size() > 0 ) {
            label = "${lhs} ${op} ${rhs}".toString()
        }
        else {
            label = op
            preds = visitWithPreds(expr.leftExpression, expr.rightExpression)
        }

        addNode(label, Node.Type.OP, preds)
    }

    @Override
    void visitConstantExpression(ConstantExpression expr) {
        addNode(expr.text, Node.Type.CONSTANT)
    }

    @Override
    void visitDeclarationExpression(DeclarationExpression expr) {
        visitAssignment(expr)
    }

    // TODO: gstring

    @Override
    void visitListExpression(ListExpression expr) {
        if( withinOutput ) {
            super.visitListExpression(expr)
            return
        }

        addNode('[]', Node.Type.CONSTANT, visitWithPreds(expr.expressions))
    }

    @Override
    void visitMethodCallExpression(MethodCallExpression call) {
        // append nodes for method call and arguments
        final dn = visitWithPreds(call.method).first()
        final preds = visitWithPreds(call.arguments)

        dn.label = "${dn.label}()"
        dn.addPredecessors(preds)

        // update predecessors
        stackPreds.last() << dn
    }

    @Override
    void visitTernaryExpression(TernaryExpression expr) {
        // determine predecessors for condition and true, false expressions
        final dnTest = visitWithPreds(expr.booleanExpression).first()
        final predsTrue = visitWithPreds(expr.trueExpression)
        final predsFalse = visitWithPreds(expr.falseExpression)

        // append if node
        final dnTrue = addNode('true', Node.Type.OP, predsTrue, false)
        final dnFalse = addNode('false', Node.Type.OP, predsFalse, false)
        addNode('if', Node.Type.OP, [dnTest, dnTrue, dnFalse] as Set<Node>)
    }

    @Override
    void visitUnaryMinusExpression(UnaryMinusExpression expr) {
        addNode('-', Node.Type.OP, visitWithPreds(expr.expression))
    }

    // TODO: unary plus/minus, not expressions, prefix, postfix

    @Override
    void visitVariableExpression(VariableExpression var) {
        final name = var.name
        if( withinOutput ) {
            putSymbol(name, addNode(name, Node.Type.NAME))
        }
        else {
            final dn = getSymbol(name)
            if( dn != null )
                stackPreds.last() << dn
            else
                putSymbol(name, addNode(name, Node.Type.NAME))
        }
    }

    @Override
    protected SourceUnit getSourceUnit() {
        throw new UnsupportedOperationException()
    }

    @EqualsAndHashCode(includes=['id'])
    @TupleConstructor
    static class Node {
        enum Type {
            CONSTANT,
            NAME,
            OP
        }

        int id
        String label
        Type type
        Set<Node> preds

        void addPredecessors(Set<Node> preds) {
            this.preds.addAll(preds)
        }

        boolean isHidden() {
            type == Type.CONSTANT
        }

        @Override
        String toString() {
            return "id=${id},label='${label}',type=${type}"
        }
    }

}
