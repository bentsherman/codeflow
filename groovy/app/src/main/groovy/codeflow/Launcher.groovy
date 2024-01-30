
package codeflow

import java.nio.file.Paths

import groovy.transform.CompileStatic
import picocli.CommandLine
import picocli.CommandLine.Command
import picocli.CommandLine.Option
import picocli.CommandLine.Parameters

@Command(
    name = 'codeflow',
    mixinStandardHelpOptions = true,
    description = 'Generate flow graphs of Groovy code'
)
@CompileStatic
class Launcher implements Runnable {

    @Parameters(description = 'Groovy source files')
    List<String> sourceFiles

    @Option(names = ['--source'], description = 'Groovy source string')
    String source

    @Option(names = ['--type'], description = 'Type of graph to build')
    String type = 'dfg'

    @Override
    void run() {
        // print flow graph for source string if specified
        if( source != null ) {
            if( type == 'cfg' )
                renderCfg(source)

            if( type == 'dfg' )
                renderDfg(source)
        }

        // print flow graph for each source file
        for( String sourceFile : sourceFiles ) {
            System.err.println(sourceFile)

            // load source file
            final sourceText = Paths.get('..').resolve(sourceFile).text

            // render specified flow graph
            if( type == 'cfg' )
                renderCfg(sourceText)

            if( type == 'dfg' )
                renderDfg(sourceText)
        }
    }

    protected void renderCfg(String sourceText) {
        // build control flow graph
        final cfg = ControlFlowGraph.fromString(sourceText)

        // print mermaid diagram
        final mmd = cfg.render()

        println(mmd)
    }

    protected void renderDfg(String sourceText) {
        // build data flow graph
        final dfg = DataFlowGraph.fromString(sourceText)

        // print mermaid diagram
        final mmd = dfg.render()

        println(mmd)
    }

    static void main(String[] args) {
        System.exit(new CommandLine(new Launcher()).execute(args))
    }

}
