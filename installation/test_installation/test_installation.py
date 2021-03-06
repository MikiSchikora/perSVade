#!/usr/bin/env python

######### define environment ##########

# this is to test that perSVade was properly installed. It takes ~45 minutes on a system of 4 cores, 32Gb of RAM

# module imports
import sys
import os

# get the cwd were all the scripts are 
test_dir = "/".join(__file__.split("/")[0:-1]); sys.path.insert(0, test_dir)
scripts_dir = "%s/../../scripts"%test_dir; sys.path.insert(0, scripts_dir)

# define the EnvDir where the environment is defined
EnvDir = "/".join(sys.executable.split("/")[0:-2])

# import functions
import test_functions as test_fun

# define the testing inputs (based on the first 2 genes of two chromosomes of Cglabrata)
testing_inputs_dir = "%s/testing_inputs"%test_dir
test_ref_genome = "%s/reduced_genome.fasta"%testing_inputs_dir
test_mutated_genome = "%s/reduced_genome_mutated.fasta"%testing_inputs_dir
test_gff = "%s/reduced_annotation.gff"%testing_inputs_dir

# load the functions (test if you can import python packages)
import sv_functions as fun
print("loading python packages worked successfully")

# define the testing inuts dir 
testing_outputs_dir = "%s/testing_outputs"%test_dir
test_output_perSVade = "%s/perSVade_output"%testing_outputs_dir
outdir_small_variantCalling = "%s/smallVars_CNV_output"%test_output_perSVade

# delete and cretae outdir
#fun.delete_folder(testing_outputs_dir)
fun.make_folder(testing_outputs_dir)
fun.make_folder(test_output_perSVade)

# redefine the reference genome location
ref_genome = "%s/reduced_genome.fasta"%testing_outputs_dir
if fun.file_is_empty(ref_genome): fun.run_cmd("cp %s %s"%(test_ref_genome, ref_genome))

# redefine the gff
gff = "%s/reduced_annotations.gff"%testing_outputs_dir
if fun.file_is_empty(gff): fun.run_cmd("cp %s %s"%(test_gff, gff))

# redefine the mutated genome location
mut_genome = "%s/mutated_genome.fasta"%testing_outputs_dir
if fun.file_is_empty(mut_genome): fun.run_cmd("cp %s %s"%(test_mutated_genome, mut_genome))

# define an example calbicans varCall_outout
Calbicans_varCall_outdir = "%s/varcalling_output_Calbicans_SRR2088862"%testing_inputs_dir

# define the Calbicans genome
inputs_Calbicans_genome = "%s/Candida_albicans.fasta"%testing_inputs_dir
Calbicans_genome = "%s/Candida_albicans.fasta"%testing_outputs_dir
fun.soft_link_files(inputs_Calbicans_genome, Calbicans_genome)

# define the Calbicans repeats
inputs_Calbicans_repeats = "%s/Candida_albicans.fasta.repeats.tab"%testing_inputs_dir
Calbicans_repeats = "%s/Candida_albicans.fasta.repeats.tab"%testing_outputs_dir
fun.soft_link_files(inputs_Calbicans_repeats, Calbicans_repeats)

# define the MERV genome
inputs_MERS_genome = "%s/MERS_CoV_genome.fasta"%testing_inputs_dir
MERS_genome = "%s/MERS_CoV_genome.fasta"%testing_outputs_dir
fun.soft_link_files(inputs_MERS_genome, MERS_genome)

########################################

# check that that the database has been created
repeat_masker_db = "%s/Libraries/RepeatMasker.lib.nsq"%(fun.repeatmasker_dir) 
if fun.file_is_empty(repeat_masker_db): raise ValueError("%s is missing. Check that you ran ./installation/setup_environment.sh"%repeat_masker_db)

# test that the environment can be recreated
test_fun.test_conda_env_generation(testing_outputs_dir, replace=False)

# test repeat masker obtention
test_fun.test_get_repeat_maskerDF(ref_genome, replace=False)

# test read simulation by simulating reads from the mutated genome
r1_mutGenome, r2_mutGenome = test_fun.test_read_simulation_and_get_reads(mut_genome)

# test bwa mem, samtools and picard
sorted_bam_mutGenome = test_fun.test_bwa_mem_and_get_bam(r1_mutGenome, r2_mutGenome, ref_genome)

# test the joining and unjoining of multiallleles. This is a test for bcftools 1.10
outdir_testing_CalbicansVarCall = "%s/testing_CalbicansVarCall"%testing_outputs_dir
test_fun.test_processing_varcalling(Calbicans_varCall_outdir, Calbicans_genome, outdir_testing_CalbicansVarCall, sorted_bam_mutGenome)

# test bcftools, freebayes, gatk4, mosdepth, vep by running the small variant calling pipeline
test_fun.test_smallVarCall_CNV_running(sorted_bam_mutGenome, outdir_small_variantCalling, ref_genome, gff, replace=False)

# test the querying of the SRA database and downloading, and trimming of reads and also gztool
outdir_SRAdb_query_downloading_and_readTrimming = "%s/testing_SRAdb_query_downloading_and_readTrimming_MERS"%testing_outputs_dir
test_fun.test_SRAdb_query_downloading_and_readTrimming(outdir_SRAdb_query_downloading_and_readTrimming, MERS_genome, 1335626)

# generate a genome that is rearranged 
rearranged_genome = test_fun.test_rearranging_genome_random(ref_genome, replace=False)

# generate simulated reads from this rearranged genome, and also a bam file
r1_svGenome, r2_svGenome = test_fun.test_read_simulation_and_get_reads(rearranged_genome, replace=False)
sorted_bam_svGenome = test_fun.test_bwa_mem_and_get_bam(r1_svGenome, r2_svGenome, ref_genome, replace=False)

# test whether you can run the gridss and clove pipeline
outdir_testing_gridss_clove = "%s/testing_gridss_clove_pipeline_default_parms"%(testing_outputs_dir)
test_fun.test_gridss_clove_pipeline(sorted_bam_svGenome, ref_genome, outdir_testing_gridss_clove, replace=False)

# test whether the parameter optimisation pipeline works well to find the rearrangements
outdir_testing_parameterOptimisation = "%s/testing_parameter_optimisation_pipeline"%(testing_outputs_dir)
test_fun.test_parameter_optimisation_perSVade(sorted_bam_svGenome, ref_genome, outdir_testing_parameterOptimisation, replace=False)

# test whether you can run greasy
test_fun.test_greasy()


print("\n\n---\nSUCCESS: perSVade was properly installed\n---\n\n")



