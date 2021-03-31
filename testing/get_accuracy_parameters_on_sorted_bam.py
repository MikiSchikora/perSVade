#!/usr/bin/env python

# This runs gridss and clove on some parameteres and a sorted bam and writes the accuracy on some SVs


# module imports
import sys
import argparse, os
import pandas as pd
import numpy as np
from argparse import RawTextHelpFormatter

# get the cwd were all the scripts are 

# define the parent dir of the cluster or not
ParentDir = "%s/samba"%(os.getenv("HOME")); # local
if not os.path.exists(ParentDir): ParentDir = "/gpfs/projects/bsc40/mschikora"

# define the functions
perSVade_scripts_dir = "%s/scripts/perSVade/perSVade_repository/scripts"%ParentDir
sys.path.insert(0, perSVade_scripts_dir)
import sv_functions as fun

### CMD LINE ###

description = """
This runs gridss and clove on some parameteres and a sorted bam and writes the accuracy on some SVs. All the inputs should be put under outdir
"""
              
parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
parser.add_argument("--reference_genome", dest="reference_genome", required=True, help="Reference genome. Has to end with .fasta.")
parser.add_argument("--mitochondrial_chromosome", dest="mitochondrial_chromosome", required=True, help="mitochondrial_chromosome")
parser.add_argument("--df_benchmarking_file", dest="df_benchmarking_file", required=True, help="The df_benchmarking_file. All files will be written here")
parser.add_argument("--sorted_bam", dest="sorted_bam", required=True, help="The sorted_bam")
parser.add_argument("--parameters_json", dest="parameters_json", required=True, help="The sorted_bam")
parser.add_argument("--gridss_vcf", dest="gridss_vcf", required=True, help="The gridss_vcf")
parser.add_argument("--svtables_prefix", dest="svtables_prefix", required=True, help="The svtables_prefix")
parser.add_argument("--threads", dest="threads", default=4, type=int, help="Number of threads, Default: 4")
parser.add_argument("--verbose", dest="verbose", action="store_true", help="verbosity mode")
opt = parser.parse_args()

################

# exit if df_benchmarking_file exists
if not fun.file_is_empty(opt.df_benchmarking_file): sys.exit(0)

# define the outdir
outdir = "%s_generatingDir"%opt.df_benchmarking_file
#fun.delete_folder(outdir)
fun.make_folder(outdir)

# define the print mode
fun.printing_verbose_mode = opt.verbose

# softlink single files
sorted_bam = "%s/aligned_reads.sorted.bam"%(outdir)
fun.soft_link_files(opt.sorted_bam, sorted_bam)
fun.soft_link_files(opt.sorted_bam+".bai", sorted_bam+".bai")
fun.soft_link_files(opt.sorted_bam+".CollectInsertSizeMetrics.out", sorted_bam+".CollectInsertSizeMetrics.out")
fun.soft_link_files(opt.sorted_bam+".coverage_per_window.tab", sorted_bam+".coverage_per_window.tab")

gridss_vcf = "%s/gridss_vcf.vcf"%outdir
fun.soft_link_files(opt.gridss_vcf, gridss_vcf)

reference_genome = "%s/reference_genome.fasta"%outdir
fun.soft_link_files(opt.reference_genome, reference_genome)
fun.soft_link_files(opt.reference_genome+".repeats.tab", reference_genome+".repeats.tab")

# softlink the svfiles

# define the median coverage
windows_file_dir = "%s.calculating_windowcoverage"%opt.sorted_bam
windows_files = ["%s/%s"%(windows_file_dir, x) for x in os.listdir(windows_file_dir)]
if len(windows_files)!=1: raise ValueError("there has to be one windws_file")
median_coverage = fun.get_median_coverage(fun.get_tab_as_df_or_empty_df(windows_files[0]), opt.mitochondrial_chromosome)

# get the parameters
gridss_blacklisted_regions, gridss_maxcoverage, gridss_filters_dict, max_rel_coverage_to_consider_del, min_rel_coverage_to_consider_dup = fun.get_parameters_from_json(opt.parameters_json)

# calculate the median insert sizes
median_insert_size, median_insert_size_sd  = fun.get_insert_size_distribution(sorted_bam, replace=False, threads=opt.threads)

# run with the provided parms
sv_dict, df_gridss = fun.run_gridssClove_given_filters(sorted_bam, reference_genome, outdir, median_coverage, replace=False, threads=opt.threads, gridss_blacklisted_regions=gridss_blacklisted_regions, gridss_VCFoutput=gridss_vcf, gridss_maxcoverage=gridss_maxcoverage, median_insert_size=median_insert_size, median_insert_size_sd=median_insert_size_sd, gridss_filters_dict=gridss_filters_dict, run_in_parallel=True, max_rel_coverage_to_consider_del=max_rel_coverage_to_consider_del, min_rel_coverage_to_consider_dup=min_rel_coverage_to_consider_dup, replace_FromGridssRun=False)


# get the known SV dict
known_sv_dict = {}
for svtype in {"insertions", "deletions", "translocations", "inversions", "tandemDuplications"}:

	origin_svfile = "%s_%s.tab"%(opt.svtables_prefix, svtype)
	dest_svfile = "%s/%s.tab"%(outdir, svtype)
	fun.soft_link_files(origin_svfile, dest_svfile)

	known_sv_dict[svtype] = dest_svfile

# get the benchmarking
fileprefix = "%s/benchmarking"%outdir
df_benchmark = fun.benchmark_processedSVs_against_knownSVs_inHouse(sv_dict, known_sv_dict, fileprefix, replace=False, add_integrated_benchmarking=True, consider_all_svtypes=False, tol_bp=50, fast_mode=True, pct_overlap=0.75)

# save
fun.delete_folder(outdir)
fun.save_df_as_tab(df_benchmark, opt.df_benchmarking_file)
