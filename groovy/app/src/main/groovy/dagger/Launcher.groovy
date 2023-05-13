
package dagger

import java.nio.file.Paths

import picocli.CommandLine
import picocli.CommandLine.Command
import picocli.CommandLine.Option
import picocli.CommandLine.Parameters

@Command(
    name = 'dg',
    mixinStandardHelpOptions = true,
    description = 'Generate flow graphs of Groovy code'
)
class Launcher implements Runnable {

    @Parameters(description = 'Groovy source files')
    List<String> sourceFiles

    @Option(names = ['--source'], description = 'Groovy source string')
    String source

    @Override
    void run() {
        // print flow graph for source string if specified
        if( source != null ) {
            createCfg(sourceText)
        }

        // print flow graph for each source file
        for( String sourceFile : sourceFiles ) {
            println(sourceFile)

            final sourceText = Paths.get('..').resolve(sourceFile).text
            createCfg(sourceText)
        }
    }

    protected void createCfg(String sourceText) {
        // build control flow graph
        final cfg = new ControlFlowGraph()
        cfg.build(sourceText)

        // print mermaid diagram
        final mmd = cfg.renderDiagram()

        println(mmd)
    }

    static void main(String[] args) {
        System.exit(new CommandLine(new Launcher()).execute(args))
    }

}
