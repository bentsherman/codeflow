# codeflow

Visualize your code to fail faster. Originally inspired by [this blog post](https://rahul.gopinath.org/post/2019/12/08/python-controlflow/).

Currently planned languages include:
- Groovy
- Python

Currently planned visualizations include:
- control flow graph
- data flow graph
- sequence diagram

For the language-specific tool, visit the corresponding subdirectory for further instructions.

## Usage

To install Mermaid:
```bash
npm install -g @mermaid-js/mermaid-cli
```

To use the watcher script to automatically generate diagrams:
```bash
../watch.sh example.py 'codeflow example.py | mmdc -q -i- -o example.png'
```
