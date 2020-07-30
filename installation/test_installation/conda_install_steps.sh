#!/bin/bash

# This recapitulates all the steps to create the env (on conda 4.8.0)

# conda distribution 'Anaconda3-2019.03-Linux-x86_64.sh', followed by 'conda install conda=4.8.0'

# remove previous
#conda activate base
#conda remove --name perSVade_env_test --all

# create and activate the env
#conda create -n perSVade_env_test python=3.6
#conda activate perSVade_env_test 

# add channels
conda config --add channels conda-forge &&
conda config --add channels biocore &&
conda config --add channels bioconda &&
conda config --add channels etetoolkit &&

# install packages that should be loaded 
conda install -y pandas=0.24.2 &&
conda install -y biopython=1.73 &&
conda install -y scipy=1.4.1 &&
conda install -y scikit-learn=0.21.3 &&
conda install -c conda-forge -y igraph=0.7.1 && # updates openssl pkgs/main::openssl-1.1.1g-h7b6447c_0 --> conda-forge::openssl-1.1.1g-h516909a_1
conda install -c conda-forge -y python-igraph=0.7.1.post7 &&
conda install -c etetoolkit -y ete3=3.1.1 &&
conda install -c anaconda -y seaborn=0.9.0 && # updates: ca-certificates    conda-forge/label/cf201901::ca-certif~ --> anaconda::ca-certificates-2020.6.24-0, certifi  conda-forge/label/cf201901::certifi-2~ --> anaconda::certifi-2020.6.20-py36_0

# install packages related to software
conda install -c bioconda -y repeatmasker=4.0.9_p2 && # downgrades: gmp 6.2.0-he1b5a44_2 --> 6.1.2-hf484d3e_1000
conda install -c bioconda -y repeatmodeler=2.0.1 &&
conda install -c bioconda -y bwa=0.7.17 &&
conda install -c bioconda -y picard=2.18.26 &&
conda install -c bioconda -y bcftools=1.9 &&
conda install -c bioconda -y samtools=1.9 && # this will downgrade: ncurses.2-he1b5a44_1 --> 6.1-hf484d3e_1002 python 3.6.11-h425cb1d_1_cpython --> 3.6.10-h8356626_1011_cpython readline  8.0-he28a2e2_2 --> 8.0-h46ee950_1
conda install -c bioconda -y bedtools=2.29.0 &&
conda install -c bioconda -y wgsim=1.0 &&
conda install -c bioconda -y seqtk=1.3 &&
conda install -c bioconda -y gatk4=4.1.2.0 && # downgrades openjdk  11.0.1-hacce0ff_1021 --> 8.0.192-h516909a_1005 (the old openjdk was 8.0.152)
conda install -c bioconda -y freebayes=1.3.1 &&
conda install -c bioconda -y mosdepth=0.2.6 &&
conda install -c bioconda -y ensembl-vep=100.2 && # downgrades libtiff 4.1.0-hc7e4089_6 --> 4.1.0-hc3755c2_3. libwebp-base-1.1.0-h516909a_3 is removed
conda install -c bioconda -y vcflib=1.0.0_rc2 &&

#conda install -c bioconda libdeflate=1.0 && # libdeflate downgraded 1.2-h516909a_1 --> 1.0-h14c3975_1


# buggy packages:
#conda install -c bioconda -y qualimap=2.2.2d && (I can instead install 2.2.2, but it fails). I decide to skip this package

# GENERAL NOTES
# 



