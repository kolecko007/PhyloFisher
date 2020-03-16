#!/usr/bin/env python
import os
import argparse
import sys
import textwrap
import subprocess
from Bio import SeqIO
from pathlib import Path
from multiprocessing import Pool
from phylofisher import help_formatter


def bash_command(cmd):
    """Function to run bash commands in a shell"""
    my_p = subprocess.Popen(cmd, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return my_p.communicate()


def delete_gaps_stars(file):
    """Removes -'s and *'s from alignments"""
    file_name = f'{file.split(".")[0]}.aa'
    with open(file_name, 'w') as res:
        for record in SeqIO.parse(file, 'fasta'):
            res.write(f'>{record.name}\n{str(record.seq).replace("-", "").replace("*", "")}\n')


def add_length(root, length):
    """Adds length to the file name"""
    os.rename(f'RAxML_bipartitions.{root}.tre', f'RAxML_bipartitions.{root}_{length}.tre')


def x_to_dash(file):
    """Replaces X's in alignments with -'s"""
    file_name = f'{file.split(".")[0]}.pre_bmge'
    with open(file_name, 'w') as res:
        for record in SeqIO.parse(file, 'fasta'):
            res.write(f'>{record.name}\n{str(record.seq).replace("X", "-")}\n')


def read_full_proteins(core):
    full_prots = {}
    for record in SeqIO.parse(f'{core}.aa.filtered', 'fasta'):
        full_prots[record.name] = record.seq
    return full_prots


def good_length(trimmed_aln, threshold):
    core = trimmed_aln.split('.')[0]
    full_proteins = read_full_proteins(core)
    original_name = f'{core}.length_filtered'
    length = None
    with open(original_name, 'w') as res:
        for record in SeqIO.parse(trimmed_aln, 'fasta'):
            if length is None:
                length = len(record.seq)
            coverage = len(str(record.seq).replace('-', '').replace('X', '')) / len(record.seq)
            if coverage > threshold:
                res.write(f'>{record.description}_{round(coverage, 2)}\n{full_proteins[record.name]}\n')
            else:
                print('deleted:', record.name, coverage)
    return length


def prepare_analyses(dataset):
    threads = int(args.threads / file_count)
    root = dataset.split('/')[-1].split('.')[0]

    delete_gaps_stars(dataset)

    # Runs Prequal, MAFFT and Divvier
    cmds1 = [f'prequal {root}.aa',
             f'mafft --thread {threads} --globalpair --maxiterate 1000 --unalignlevel 0.6 {root}.aa.filtered > {root}.aln',
             f'divvier -mincol 4 -divvygap {root}.aln'
             ]
    output1 = [bash_command(cmd) for cmd in cmds1]
    x_to_dash(f'{root}.aln.divvy.fas')  # outputs pre_bmge

    output2 = bash_command(f'BMGE -t AA -g 0.3 -i {root}.pre_bmge -of {root}.bmge')
    length = good_length(trimmed_aln=f'{root}.bmge', threshold=0.5)

    # Runs MAFFT, Divvier, trimal, and raxml
    cmds2 = [f'mafft --thread {threads} --globalpair --maxiterate 1000 --unalignlevel 0.6 {root}.length_filtered > {root}.aln2',
             f'divvier -mincol 4 -divvygap {root}.aln2',
             f'trimal -in {root}.aln2.divvy.fas -gt 0.01 -out {root}.final',
             f'raxmlHPC-PTHREADS-AVX2 -T {threads} -m PROTGAMMALG4XF -f a -s {root}.final -n {root}.tre -x 123 -N 100 -p 12345'
             ]
    output3 = [bash_command(cmd) for cmd in cmds2]

    add_length(root, length=length)

    output = output1.append(output2) + output3

    for err, out in output:
        print(out, file=sys.stdout)
        print(err, file=sys.stderr)


if __name__ == '__main__':
    formatter = lambda prog: help_formatter.MyHelpFormatter(prog, max_help_position=100)

    parser = argparse.ArgumentParser(prog='single_gene_tree_constructor.py',
                                     description='description',
                                     usage='single_gene_tree_constructor.py -i path/to/input/ [OPTIONS]',
                                     formatter_class=formatter,
                                     add_help=False,
                                     epilog=textwrap.dedent("""\
                                     additional information:
                                        stuff
                                        """))
    optional = parser._action_groups.pop()
    required = parser.add_argument_group('required arguments')

    # Required Arguments
    required.add_argument('-i', '--input_folder', required=True, type=str, metavar='path/to/input/',
                          help=textwrap.dedent("""\
                          Path to input directory
                          """))

    # Optional Arguments
    optional.add_argument('-s', '--suffix', metavar='"suffix"', type=str,
                          help=textwrap.dedent("""\
                              Suffix of input files
                              Default: NONE
                              Example: path/to/input/*.suffix 
                              """))
    optional.add_argument('-t', '--threads', metavar='N', type=int, default=1,
                          help=textwrap.dedent("""\
                          Desired number of threads to be utilized.
                          Default: 1
                          """))
    optional.add_argument('-h', '--help', action='help', default=argparse.SUPPRESS,
                          help=textwrap.dedent("""\
                          Show this help message and exit.
                          """))

    parser._action_groups.append(optional)
    args = parser.parse_args()

    os.chdir(args.input_folder)

    # Parallelization of prepare_analyses function
    files = [file for file in os.listdir(".") if file.endswith('.fas')]
    file_count = len(files)
    processes = args.threads
    if file_count < args.threads:
        processes = file_count

    with Pool(processes) as p:
        p.map(prepare_analyses, files)
