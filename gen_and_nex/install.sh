#!/bin/bash

# Colors for display
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

display_nexahub_banner() {
    echo -e "${GREEN}#################################################"
    echo -e "#                                               #"
    echo -e "#                 ${RED}Genarc${GREEN}                 #"
    echo -e "#                                               #"
    echo -e "#################################################${NC}"
    echo ""
}

install_mamba() {
    if ! conda list -n base | grep -q 'mamba'; then
        echo -e "${GREEN}Installing Mamba...${NC}"
        conda install mamba -c conda-forge -y
    else
        echo -e "${GREEN}Mamba is already installed.${NC}"
    fi
}

create_conda_env() {
    local env_name=$1
    local tool_name=$2

    display_nexahub_banner
    echo -e "${GREEN}Creating $env_name environment for $tool_name...${NC}"
    
    mamba create -n $env_name -y
    mamba activate $env_name
    
    # Retry mechanism for installations
    for attempt in {1..3}; do
        mamba install -n $env_name -c bioconda -c conda-forge -c defaults $tool_name -y
        if [ $? -eq 0 ]; then
            break
        elif [ $attempt -eq 3 ]; then
            echo -e "${RED}Failed to install $tool_name after $attempt attempts.${NC}"
            exit 1
        fi
        echo -e "${RED}Retrying installation of $tool_name... Attempt: $attempt${NC}"
        sleep 10  # sleep for 10 seconds before retrying
    done

    if [ $env_name == "rnaspades_env" ]; then
        mamba update -n $env_name pyyaml -y
    fi

    mamba deactivate

    echo -e "${GREEN}Installation of $tool_name in $env_name environment completed.${NC}"
    echo ""
}

# Display initial banner
display_nexahub_banner

# Ensure mamba is installed and update packages
install_mamba
mamba update -n base -c conda-forge mamba -y
mamba update --all -y

# Create and install conda environments and tools
create_conda_env "fastp_env" "fastp"
create_conda_env "fastqc_env" "fastqc"
create_conda_env "trimmomatic_env" "trimmomatic"
create_conda_env "rnaspades_env" "spades"
create_conda_env "transdecoder_env" "transdecoder"
create_conda_env "blast_env" "blast"
create_conda_env "trinity_env" "trinity=2.13.2"
create_conda_env "samtools_env" "samtools"
create_conda_env "gffread_env" "gffread"
create_conda_env "star_env" "star"
create_conda_env "bowtie_env" "bowtie2"
create_conda_env "hisat_env" "hisat2"
create_conda_env "featurecounts_env" "subread"
create_conda_env "busco_env" "busco"
create_conda_env "rsem_env" "rsem"
create_conda_env "splitter_env" "fasta-splitter"
create_conda_env "interproscan_env" "interproscan"
create_conda_env "spades_env" "spades"
create_conda_env "abyss-env" "abyss"
create_conda_env "freebayes_env" "freebayes"


# Clean cache
mamba clean --all -y

echo -e "${GREEN}All conda environments and tools have been created and installed successfully.${NC}"

