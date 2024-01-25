
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

    @Override
    void run() {
        // print flow graph for source string if specified
        if( source != null ) {
            renderCfg(source)
        }

        // print flow graph for each source file
        for( String sourceFile : sourceFiles ) {
            System.err.println(sourceFile)

            // load source file
            final sourceText = Paths.get('..').resolve(sourceFile).text

            // render specified flow graph
            renderCfg(sourceText)
        }
    }

    protected void renderCfg(String sourceText) {
        // build control flow graph
        final cfg = ControlFlowGraph.build(sourceText)

        // print mermaid diagram
        final mmd = cfg.renderDiagram()

        println(mmd)
    }

    static void main(String[] args) {
        System.exit(new CommandLine(new Launcher()).execute(args))
    }

}
