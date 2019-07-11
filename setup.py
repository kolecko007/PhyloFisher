from setuptools import setup

setup(
    name='PhyloFisher',
    version='0.1dev',
    packages=['phylofisher'],
    scripts=['phylofisher/fisher.py',
             'phylofisher/config.py',
             'phylofisher/fishing_net.py',
             'phylofisher/forest.py',
             'phylofisher/forge.py',
             'phylofisher/informant.py',
             'phylofisher/lumberjack.py',
             'phylofisher/purge.py'],
    url='',
    license='MIT',
    author='david',
    author_email='zihaladavid@gmail.com',
    description='',
    install_requires=[
        'numpy==1.16.2',
        'matplotlib==3.0.2',
        'PyQt5==5.12.1',
        'ete3==3.1.1',
        'pandas==0.23.4',
        'biopython==1.70',]
    )
