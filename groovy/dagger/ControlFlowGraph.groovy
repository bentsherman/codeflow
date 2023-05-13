
package dagger

import groovy.transform.CompileStatic
import groovy.transform.EqualsAndHashCode
import groovy.transform.TupleConstructor
import org.codehaus.groovy.ast.*
import org.codehaus.groovy.ast.builder.*
import org.codehaus.groovy.ast.expr.*
import org.codehaus.groovy.ast.stmt.*
import org.codehaus.groovy.control.*

@CompileStatic
class ControlFlowGraph extends ClassCodeVisitorSupport {
    private Map<Integer,Node> nodes = [:]
    private Map<String,Node> methods = [:]
    private List<String> stackClass = []
    private List<String> stackMethod = []
    private List<Node> stackLoop = []
    private List<Set<Node>> stackPreds

    void generate(String sourceText) {
        // initialize graph state
        this.stackPreds = [[] as Set]

        // append start node
        this.addNode('start', Node.Type.START)

        // build abstract syntax tree of source text
        final astBuilder = new AstBuilder()
        final astNodes = astBuilder.buildFromString(CompilePhase.CONVERSION, false, sourceText)

        // traverse abstract syntax tree
        astNodes.each { astNode ->
            if ( astNode instanceof ClassNode )
                astNode.visitContents(this)
            else
                astNode.visit(this)
        }

        // append stop node
        this.addNode('stop', Node.Type.STOP)
    }

    Node addNode(String label, Node.Type type, ASTNode astNode=null) {
        // create node
        final id = this.nodes.size()
        final cn = new Node(
            id,
            label != null ? label : astNode.getText(),
            type,
            this.stackPreds.removeLast())

        // add node to graph
        this.nodes[id] = cn

        // update graph state
        this.stackPreds << ([cn] as Set)

        return cn
    }

    String renderMmd() {
        // initialize diagram
        final lines = []
        lines << "flowchart TD"

        // iterate through each node
        final nodes = this.nodes.values()

        nodes.each { cn ->
            // sanitize label
            final label = cn.label.replaceAll('\"', '\\\\\"') ?: " "

            // add node to mmd graph
            switch ( cn.type ) {
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
            cn.preds.each { cnPred ->
                // connect node to predecessor
                switch ( cnPred.type ) {
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
        block.getStatements().each { statement ->
            statement.visit(this)
        }
    }

    @Override
    void visitClass(ClassNode node) {
        // enter class body
        this.stackClass << node.getName()
        this.stackPreds << ([] as Set)

        // append definition node
        this.addNode("class ${node.getName()}", Node.Type.DEFINITION)

        // visit statement in class body
        // TODO: ???

        // exit class body
        this.stackClass.removeLast()
        this.stackPreds.removeLast()
    }

    @Override
    void visitIfElse(IfStatement statement) {
        // append entry node
        final testExpression = statement.getBooleanExpression()
        this.addNode("if ${testExpression.getText()}", Node.Type.IF)

        // visit test expression
        testExpression.visit(this)

        // visit each statement in the if branch
        this.stackPreds << this.stackPreds[-1]
        this.addNode("", Node.Type.IF_TRUE)

        statement.getIfBlock().visit(this)

        final cnIf = this.stackPreds.removeLast()

        // visit each statement in the else branch
        this.addNode("", Node.Type.IF_FALSE)

        statement.getElseBlock().visit(this)

        final cnElse = this.stackPreds.removeLast()

        // merge nodes from both branches
        this.stackPreds << (cnIf + cnElse)
    }

    @Override
    void visitMethod(MethodNode node) {
        // construct method name
        final methodName = node.getName()

        // enter method body
        this.stackMethod << methodName
        this.stackPreds << ([] as Set)

        // append definition node
        this.methods[methodName] = this.addNode("def ${methodName}", Node.Type.DEFINITION)

        // visit each statement in method body
        node.getCode().visit(this)

        // exit method body
        this.stackMethod.removeLast()
        this.stackPreds.removeLast()
    }

    @Override
    void visitStatement(Statement statement) {
        this.addNode(null, null, statement)
    }

    @Override
    protected SourceUnit getSourceUnit() {
        throw new Exception("not implemented")
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
            this.preds.addAll(preds)
        }

        boolean isHidden() {
            return !this.label
        }

        @Override
        String toString() {
            return "${id}:\"${label ?: type}\""
        }
    }

}
