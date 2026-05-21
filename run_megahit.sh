#!/bin/bash
conda run -n megahit_env megahit -1 /home/altschul/backup/exampledata/metagenome/SRR11131033_1.fastq -2 /home/altschul/backup/exampledata/metagenome/SRR11131033_2.fastq -o /home/altschul/backup/exampledata/output/MEGAHIT_GUI --min-contig-len 500 -t 1
