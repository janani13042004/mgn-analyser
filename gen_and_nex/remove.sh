#!/bin/bash

# List of environments to delete
environments=("blast_env" "bowtie_env" "busco_env" "fastp_env" "fastqc_env" "featurecounts_env" 
"gffread_env" "hisat_env" "rnaspades_env" "samtools_env" "star_env" "transdecoder_env" "rsem_env"
"trimmomatic_env" "trinity_env" "interproscan_env" "splitter_env")

# Loop through each environment and remove
for env in "${environments[@]}"; do
    echo "Removing environment: $env"
    conda env remove --name $env
done

echo "All specified environments have been removed."
