#!/bin/bash
#SBATCH -J gcda_sachs
#SBATCH -A l0003501            # Lichtenberg project the thesis runs were charged to; others: use your own (`csreport`)
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#SBATCH -n 1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1000
#SBATCH -t 00:10:00
# Sachs validation (Sec. 5.1): are the first 853 bundled rows the CD3/CD28 condition?
# Compute nodes have no internet: download the reference ON THE LOGIN NODE first:
#   cd ~/Graph-Conditioned-Causal-Data-Augmentation && wget https://www.bnlearn.com/book-crc/code/sachs.data.txt.gz && gunzip -f sachs.data.txt.gz
source slurm/env_lichtenberg.sh
test -f sachs.data.txt || { echo "sachs.data.txt missing - download it on the login node first"; exit 2; }
python scripts/verify_sachs_subset.py sachs.data.txt | tee "$GCDA_OUT/sachs_validation.txt"
