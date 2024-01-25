
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='codeflow',
    version='0.1',
    description='Flow groups for your code',
    entry_points={
        'console_scripts': ['codeflow=codeflow.cli:main'],
    },
    install_requires=required,
    packages=find_packages()
)
