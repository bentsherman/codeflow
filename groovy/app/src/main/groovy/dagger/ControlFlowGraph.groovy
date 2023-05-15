
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
class ControlFlowGraph extends ClassCodeVisitorSupport {
    private Map<Integer,Node> nodes = [:]
    private Map<String,Node> methods = [:]
    private List<String> stackClass = []
    private List<String> stackMethod = []
    private List<Node> stackLoop = []
    private List<Set<Node>> stackPreds

    ControlFlowGraph() {
        stackPreds = [[] as Set]
    }

    static ControlFlowGraph build(String sourceText) {
        final cfg = new ControlFlowGraph()

        // append start node
        cfg.addNode('start', Node.Type.START)

        // build abstract syntax tree of source text
        final astNodes = new AstBuilder().buildFromString(CompilePhase.CONVERSION, false, sourceText)

        // visit script node
        astNodes[0].visit(cfg)

        // visit methods of script wrapper class
        // skip auto-generated methods
        final methodNodes = ((ClassNode)astNodes[1]).getMethods()
        for( def methodNode : methodNodes.subList(2, methodNodes.size()) )
            cfg.visitMethod(methodNode)

        // append stop node
        cfg.addNode('stop', Node.Type.STOP)

        return cfg
    }

    protected Node addNode(String label, Node.Type type, ASTNode astNode=null) {
        // create node
        final id = nodes.size()
        final cn = new Node(
            id,
            label != null ? label : astNode.getText(),
            type,
            stackPreds.removeLast())

        // add node to graph
        nodes[id] = cn

        // update graph state
        stackPreds << ([cn] as Set)

        return cn
    }

    String renderDiagram() {
        // initialize diagram
        final lines = []
        lines << "flowchart TD"

        // iterate through each node
        final nodes = nodes.values()

        for( def cn : nodes ) {
            // sanitize label
            final label = cn.label.replaceAll('\"', '\\\\\"') ?: " "

            // add node to mmd graph
            switch( cn.type ) {
            case Node.Type.START:
            case Node.Type.STOP:
            case Node.Type.DEFINITION:
                lines << "    p${cn.id}(((\"${label}\")))"
                break
            case Node.Type.IF:
                lines << "    p${cn.id}{\"${label}\"}"
                break
            default:
                lines << "    p${cn.id}(\"${label}\")"
            }

            // connect predecessors to node
            for( def cnPred : cn.preds ) {
                // connect node to predecessor
                switch( cnPred.type ) {
                case Node.Type.IF_TRUE:
                    lines << "    p${cnPred.id} -->|True| p${cn.id}"
                    break
                case Node.Type.IF_FALSE:
                    lines << "    p${cnPred.id} -->|False| p${cn.id}"
                    break
                default:
                    lines << "    p${cnPred.id} --> p${cn.id}"
                }
            }
        }

        return lines.join('\n')
    }

    @Override
    void visitBlockStatement(BlockStatement block) {
        for( def statement : block.getStatements() )
            statement.visit(this)
    }

    @Override
    void visitClass(ClassNode node) {
        // enter class body
        stackClass << node.getName()
        stackPreds << ([] as Set)

        // append definition node
        addNode("class ${node.getName()}", Node.Type.DEFINITION)

        // visit statement in class body
        // TODO: ???

        // exit class body
        stackClass.removeLast()
        stackPreds.removeLast()
    }

    @Override
    void visitIfElse(IfStatement statement) {
        // append entry node
        final testExpression = statement.getBooleanExpression()
        addNode("if ${testExpression.getText()}", Node.Type.IF)

        // visit test expression
        testExpression.visit(this)

        // visit each statement in the if branch
        stackPreds << stackPreds[-1]
        addNode("", Node.Type.IF_TRUE)

        statement.getIfBlock().visit(this)

        final cnIf = stackPreds.removeLast()

        // visit each statement in the else branch
        addNode("", Node.Type.IF_FALSE)

        statement.getElseBlock().visit(this)

        final cnElse = stackPreds.removeLast()

        // merge nodes from both branches
        stackPreds << (cnIf + cnElse)
    }

    @Override
    void visitMethod(MethodNode node) {
        // construct method name
        final methodName = node.getName()

        // enter method body
        stackMethod << methodName
        stackPreds << ([] as Set)

        // append definition node
        methods[methodName] = addNode("def ${methodName}", Node.Type.DEFINITION)

        // visit each statement in method body
        node.getCode().visit(this)

        // exit method body
        stackMethod.removeLast()
        stackPreds.removeLast()
    }

    @Override
    void visitStatement(Statement statement) {
        addNode(null, null, statement)
    }

    @Override
    protected SourceUnit getSourceUnit() {
        throw new UnsupportedOperationException()
    }

    @EqualsAndHashCode(includes=['id'])
    @TupleConstructor
    static class Node {
        enum Type {
            DEFINITION,
            IF,
            IF_TRUE,
            IF_FALSE,
            START,
            STOP
        }

        int id
        String label
        Type type
        Set<Node> preds

        void addPredecessors(Set preds) {
            preds.addAll(preds)
        }

        boolean isHidden() {
            return !label
        }

        @Override
        String toString() {
            return "${id}:\"${label ?: type}\""
        }
    }

}
