
package dagger

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
    private Map<Integer,Node> nodes = [:]
    private List<String> stackClass = []
    private List<Map<String,Node>> stackNames 
    private List<Set<Node>> stackPreds

    DataFlowGraph() {
        stackNames = [ [:] as Map ]
        stackPreds = [ new LinkedHashSet<>() ]
    }

    static DataFlowGraph build(String sourceText) {
        final cfg = new DataFlowGraph()

        // build abstract syntax tree of source text
        final astNodes = new AstBuilder().buildFromString(CompilePhase.CONVERSION, false, sourceText)

        // visit script node
        astNodes[0].visit(cfg)

        // visit methods of script wrapper class
        // skip auto-generated methods
        final methodNodes = ((ClassNode)astNodes[1]).getMethods()
        for( def methodNode : methodNodes.subList(2, methodNodes.size()) )
            cfg.visitMethod(methodNode)

        return cfg
    }

    protected Node getSymbol(String name) {
        // get a variable node from the name table
        for( Map scope : stackNames.reverse() )
            if( name in scope )
                return scope[name]

        return null
    }

    protected void putSymbol(String name, Node dn) {
        // put a variable node into the name table
        for( Map scope : stackNames.reverse() ) {
            if( name in scope ) {
                scope.put(name, dn)
                return
            }
        }

        stackNames.last().put(name, dn)
    }

    protected Set visitWithPreds(List<? extends ASTNode> astNodes) {
        // traverse a set of nodes and extract predecessor nodes
        stackPreds << new LinkedHashSet<>()

        for( def astNode : astNodes )
            if( astNode != null )
                astNode.visit(this)

        return stackPreds.removeLast()
    }

    protected Node addNode(String label=null, Node.Type type=null, Set preds=null) {
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
        stackPreds.last() << dn

        return dn
    }

    String renderDiagram() {
        // initialize diagram
        final lines = []
        lines << "flowchart TD"

        // render each node
        for( def dn : nodes.values() ) {
            final label = dn.label
                .replaceAll('\n', '\\\\\n')
                .replaceAll('\"', '\\\\\"')

            lines << "    p${dn.id}(\"${label}\")"
        }

        // render each edge
        for( def dn : nodes.values() )
            for( def dnPred : dn.preds )
                lines << "    p${dnPred.id} --> p${dn.id}"

        return lines.join('\n')
    }

    @Override
    void visitBlockStatement(BlockStatement block) {
        for( def statement : block.getStatements() )
            statement.visit(this)
    }

    @Override
    void visitClass(ClassNode node) {
        // visit class contents
        stackClass << node.getName()
        stackNames << [:]

        final preds = visitWithPreds( node.getMethods() )

        stackClass.removeLast()
        stackNames.removeLast()

        // add class node to graph
        final label = node.getName()
        final dn = addNode(label, Node.Type.NAME, preds)
        putSymbol(label, dn)
    }

    @Override
    void visitIfElse(IfStatement statement) {
        final label = 'if'
        final preds = visitWithPreds([
            statement.getBooleanExpression(),
            statement.getIfBlock(),
            statement.getElseBlock()
        ])

        addNode(label, Node.Type.OP, preds)
    }

    @Override
    void visitMethod(MethodNode node) {
        // visit method body
        stackNames << [:]
        final preds = visitWithPreds([ node.getCode() ])
        stackNames.removeLast()

        // add method node to graph
        final label = stackClass.isEmpty()
            ? node.getName()
            : "${stackClass.last()}.${node.getName()}".toString()

        final dn = addNode(label, Node.Type.NAME, preds)
        putSymbol(label, dn)
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

        void addPredecessors(Set preds) {
            this.preds.addAll(preds)
        }

        boolean isHidden() {
            type == Type.CONSTANT
        }

        @Override
        String toString() {
            return "${id}:\"${label ?: type}\""
        }
    }

}
