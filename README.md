# dagger

Generate control flow and data flow graphs of your Python code. Originally inspired by [this blog post](https://rahul.gopinath.org/post/2019/12/08/python-controlflow/).

## Installation

```bash
# install dependencies
sudo apt install graphviz
pip install -r requirements.txt

# (optional) install as package
pip install -e .
```

## Usage

Generate example flow graphs:
```bash
./cli examples/*.py
```

Run unit tests:
```bash
python -m pytest
```
