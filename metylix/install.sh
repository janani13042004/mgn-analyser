#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

display_metylix_banner() {
    echo -e "${GREEN}#################################################"
    echo -e "#                                               #"
    echo -e "#                 ${RED}Metylix${GREEN}                 #"
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
    local env_name="$1"
    local tool_name="$2"

    display_metylix_banner
    echo -e "${GREEN}Creating $env_name environment for $tool_name...${NC}"

    # Check if environment already exists
    if conda env list | grep -q "$env_name"; then
        echo -e "${GREEN}Environment $env_name already exists. Skipping creation.${NC}"
        return
    fi

    mamba create -n "$env_name" -y

    for attempt in {1..3}; do
        mamba install -n "$env_name" -c bioconda -c conda-forge -c defaults "$tool_name" -y
        if [ $? -eq 0 ]; then
            break
        elif [ $attempt -eq 3 ]; then
            echo -e "${RED}Failed to install $tool_name after $attempt attempts.${NC}"
            exit 1
        fi
        echo -e "${RED}Retrying installation of $tool_name... Attempt: $attempt${NC}"
        sleep 10
    done

    if [ "$env_name" == "rnaspades_env" ]; then
        mamba update -n "$env_name" pyyaml -y
    fi

    echo -e "${GREEN}Installation of $tool_name in $env_name environment completed.${NC}"
    echo ""
}

install_qiime2() {
    local qiime_env="qiime2-amplicon-2024.5"
    local yaml_url="https://data.qiime2.org/distro/core/qiime2-2024.5-py38-linux-conda.yml"
    local yaml_file="qiime2-2024.5.yml"

    echo -e "${GREEN}Downloading QIIME 2 environment YAML...${NC}"
    wget "$yaml_url" -O "$yaml_file"

    echo -e "${GREEN}Creating QIIME 2 environment: $qiime_env${NC}"
    
    if conda env list | grep -q "$qiime_env"; then
        echo -e "${GREEN}Environment $qiime_env already exists. Skipping creation.${NC}"
    else
        mamba env create -n "$qiime_env" --file "$yaml_file"
    fi

    echo -e "${GREEN}QIIME 2 ($qiime_env) environment is ready.${NC}"
    echo ""
}

# Main script starts here
display_metylix_banner
install_mamba

echo -e "${GREEN}Updating Mamba and base environment...${NC}"
mamba update -n base -c conda-forge mamba -y
mamba update --all -y

# Tool environments
create_conda_env "fastp_env" "fastp"
create_conda_env "fastqc_env" "fastqc"
create_conda_env "trimmomatic_env" "trimmomatic"
create_conda_env "trimgalore_env" "trim-galore"
create_conda_env "megahit_env" "megahit"
create_conda_env "metaspades_env" "metaspades"
create_conda_env "eggnog_env" "eggnog-mapper"
create_conda_env "kraken2_env" "kraken2"
create_conda_env "samtools_env" "samtools"
create_conda_env "gffread_env" "gffread"
create_conda_env "krona_env" "krona"

# QIIME2 installation
install_qiime2

# Clean up
echo -e "${GREEN}Cleaning up unused packages...${NC}"
mamba clean --all -y

# Activate and run pipeline
echo -e "${GREEN}Activating QIIME 2 environment and launching the pipeline...${NC}"
source ~/anaconda3/etc/profile.d/conda.sh
conda activate qiime2-amplicon-2024.5

echo -e "${GREEN}Pipeline execution completed.${NC}"

