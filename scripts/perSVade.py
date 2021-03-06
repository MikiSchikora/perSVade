#!/usr/bin/env python

# This is the perSVade pipeline main script, which shoul dbe run on the perSVade conda environment


##### DEFINE ENVIRONMENT #######

# module imports
import argparse, os
import pandas as pd
import numpy as np
from argparse import RawTextHelpFormatter
import copy as cp
import pickle
import string
import shutil 
from Bio import SeqIO
import random
import sys
from shutil import copyfile

# get the cwd were all the scripts are 
CWD = "/".join(__file__.split("/")[0:-1]); sys.path.insert(0, CWD)

# define the EnvDir where the environment is defined
EnvDir = "/".join(sys.executable.split("/")[0:-2])

# import functions
import sv_functions as fun

# packages installed into the conda environment 
samtools = "%s/bin/samtools"%EnvDir
java = "%s/bin/java"%EnvDir
picard_exec = "%s/bin/picard"%EnvDir

# scripts that are installed under this software
varcall_cnv_pipeline = "%s/varcall_cnv_pipeline.py"%CWD

#######

description = """
Runs perSVade pipeline on an input set of paired end short ends. It is expected to be run on a coda environment and have several dependencies (see https://github.com/Gabaldonlab/perSVade). Some of these dependencies are included in the respository "installation/external_software". These are gridss (tested on version 2.8.1), clove (tested on version 0.17) and NINJA (we installed it from https://github.com/TravisWheelerLab/NINJA/releases/tag/0.95-cluster_only). If you have any trouble with these you can replace them from the source code.
"""
              
parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)

# general args
parser.add_argument("-r", "--ref", dest="ref", required=True, help="Reference genome. Has to end with .fasta.")
parser.add_argument("-thr", "--threads", dest="threads", default=16, type=int, help="Number of threads, Default: 16")
parser.add_argument("-o", "--outdir", dest="outdir", action="store", required=True, help="Directory where the data will be stored")
parser.add_argument("--replace", dest="replace", action="store_true", help="Replace existing files")
parser.add_argument("-p", "--ploidy", dest="ploidy", default=1, type=int, help="Ploidy, can be 1 or 2")

# different modules to be executed
parser.add_argument("--testSVgen_from_DefaulReads", dest="testSVgen_from_DefaulReads", default=False, action="store_true", help="This indicates whether to generate a report of how the generation of SV works with the default parameters on random simulations")

parser.add_argument("--close_shortReads_table", dest="close_shortReads_table", type=str, default=None, help="This is the path to a table that has 4 fields: sampleID,runID,short_reads1,short_reads2. These should be WGS runs of samples that are close to the reference genome and some expected SV. Whenever this argument is provided, the pipeline will find SVs in these samples and generate a folder <outdir>/findingRealSVs<>/SVs_compatible_to_insert that will contain one file for each SV, so that they are compatible and ready to insert in a simulated genome. This table will be used if --testAccuracy is specified, which will require at least 3 runs for each sample. It can be 'auto', in which case it will be inferred from the taxID provided by --target_taxID.")

parser.add_argument("--target_taxID", dest="target_taxID", type=int, default=None, help="This is the taxID (according to NCBI taxonomy) to which your reference genome belongs. If provided it is used to download genomes and reads.")

parser.add_argument("--n_close_samples", dest="n_close_samples", default=5, type=int, help="Number of close samples to search in case --target_taxID is provided")

parser.add_argument("--nruns_per_sample", dest="nruns_per_sample", default=3, type=int, help="Number of runs to download for each sample in the case that --target_taxID is specified. ")

parser.add_argument("--SVs_compatible_to_insert_dir", dest="SVs_compatible_to_insert_dir", type=str, default=None, help="A directory with one file for each SV that can be inserted into the reference genome in simulations. It may be created with --close_shortReads_table. If both --SVs_compatible_to_insert_dir and --close_shortReads_table are provided, --SVs_compatible_to_insert_dir will be used, and --close_shortReads_table will have no effect. If none of them are provided, this pipeline will base the parameter optimization on randomly inserted SVs (the default behavior). The coordinates have to be 1-based, as they are ready to insert into RSVsim.")

parser.add_argument("--fast_SVcalling", dest="fast_SVcalling", action="store_true", default=False, help="Run SV calling with a default set of parameters. There will not be any optimisation nor reporting of accuracy. This is expected to work almost as fast as gridss and clove together.")

# pipeline skipping options 
parser.add_argument("--skip_SVcalling", dest="skip_SVcalling", action="store_true", default=False, help="Do not run SV calling.")

# options of the long reads-based benchmarking
parser.add_argument("--goldenSet_dir", dest="goldenSet_dir", type=str, default=None, help="This is the path to a directory that has some oxford nanopore reads (should end with'long_reads.fasta') and some  short paired end reads (ending with '1.fastq.gz' and '2.fastq.gz'). These are assumed to be from the exact same sample. If provided, perSVade will call SVs from it using the --nanopore configuration of svim and validate each of the 'real' (if provided), 'uniform' and 'fast' versions from the short reads on it. If you state 'auto', it will look for samples of your --target_taxID in the SRA that are suited. We already provide some automated finding of reads in the SRA for several taxIDs: 3702 (Arabidopsis_thaliana). All the jobs will be run in an squeue as specified by --job_array_mode.")

# pipeline stopping options
parser.add_argument("--StopAfter_readObtentionFromSRA", dest="StopAfter_readObtentionFromSRA", action="store_true", default=False, help="Stop after obtaining reads from SRA.")
parser.add_argument("--StopAfter_sampleIndexingFromSRA", dest="StopAfter_sampleIndexingFromSRA", action="store_true", default=False, help="It will stop after indexing the samples of SRA. You can use this if, for example, your local machine has internet connection and your slurm cluster does not. You can first obtain the SRA indexes in the local machine. And then run again this pipeline without this option in the slurm cluster.")
parser.add_argument("--StopAfter_genomeObtention", dest="StopAfter_genomeObtention", action="store_true", default=False, help="Stop after genome obtention.")
parser.add_argument("--StopAfter_bamFileObtention", dest="StopAfter_bamFileObtention", action="store_true", default=False, help="Stop after obtaining the BAM file of aligned reads.")
parser.add_argument("--StopAfterPrefecth_of_reads", dest="StopAfterPrefecth_of_reads", action="store_true", default=False, help="Stop after obtaining the prefetched .srr file in case close_shortReads_table is 'auto'")
parser.add_argument("--StopAfterPrefecth_of_reads_goldenSet", dest="StopAfterPrefecth_of_reads_goldenSet", action="store_true", default=False, help="Stop after obtaining the prefetched .srr file in case --goldenSet_dir is specified.")
parser.add_argument("--StopAfter_obtentionOFcloseSVs", dest="StopAfter_obtentionOFcloseSVs", action="store_true", default=False, help="Stop after obtaining the SVs_compatible_to_insert_dir ")
parser.add_argument("--StopAfter_repeatsObtention", dest="StopAfter_repeatsObtention", action="store_true", default=False, help="Stop after obtaining  the repeats table")

parser.add_argument("--StopAfter_testAccuracy_perSVadeRunning", dest="StopAfter_testAccuracy_perSVadeRunning", action="store_true", default=False, help="When --testAccuracy is specified, the pipeline will stop after the running of perSVade on all the inputs of --close_shortReads_table with the different configurations.")

# testing options
parser.add_argument("--testAccuracy", dest="testAccuracy", action="store_true", default=False, help="Reports the accuracy  of your calling on the real data, simulations and fastSVcalling for all the WGS runs specified in --close_shortReads_table. ")


# simulation parameter args
parser.add_argument("--nvars", dest="nvars", default=50, type=int, help="Number of variants to simulate for each SVtype.")
parser.add_argument("--nsimulations", dest="nsimulations", default=2, type=int, help="The number of 'replicate' simulations that will be produced.")
parser.add_argument("--simulation_ploidies", dest="simulation_ploidies", type=str, default="haploid,diploid_hetero", help='A comma-sepparated string of the ploidies to simulate for parameter optimisation. It can have any of "haploid", "diploid_homo", "diploid_hetero", "ref:2_var:1", "ref:3_var:1", "ref:4_var:1", "ref:5_var:1", "ref:9_var:1", "ref:19_var:1", "ref:99_var:1" ')
parser.add_argument("--range_filtering_benchmark", dest="range_filtering_benchmark", type=str, default="theoretically_meaningful", help='The range of parameters that should be tested in the SV optimisation pipeline. It can be any of large, medium, small, theoretically_meaningful or single.')

# alignment args
parser.add_argument("-f1", "--fastq1", dest="fastq1", default=None, help="fastq_1 file. Option required to obtain bam files. It can be 'skip'")
parser.add_argument("-f2", "--fastq2", dest="fastq2", default=None, help="fastq_2 file. Option required to obtain bam files. It can be 'skip'")
parser.add_argument("-sbam", "--sortedbam", dest="sortedbam", default=None, help="The path to the sorted bam file, which should have a bam.bai file in the same dir. For example, if your bam file is called 'aligned_reads.bam', there should be an 'aligned_reads.bam.bai' as well. This is mutually exclusive with providing reads. By default, it is assumed that this bam has marked duplicates. If not, you can mark them with the option --markDuplicates_inBam.")

# machine options
parser.add_argument("--job_array_mode", dest="job_array_mode", type=str, default="local", help="It specifies in how to run the job arrays for,  --testAccuracy, the downloading of reads if  --close_shortReads_table is auto, and the SV calling for the table in --close_shortReads_table. It can be 'local' (runs one job after the other or 'greasy' (each job is run on a diferent node of a slurm cluster with the greasy system. It requires the machine to be able to run greasy jobs, as in https://user.cscs.ch/tools/high_throughput/). If 'greasy' is specified, this pipeline will stop with a warning everytime that unfinished jobs have to be submited, and you'll be able to track the job status with the squeue command.")

parser.add_argument("--queue_jobs", dest="queue_jobs", type=str, default="debug", help="The name of the queue were to submit the jobs when running with greasy")
parser.add_argument("--max_ncores_queue", dest="max_ncores_queue", type=int, default=768, help="The maximum number of cores that the queue can handle in a single job")

# timings of queues
parser.add_argument("--time_read_obtention", dest="time_read_obtention", type=str, default="02:00:00", help="The time that the fastqdumping and trimming of reads will take to perform this task")
parser.add_argument("--time_perSVade_running", dest="time_perSVade_running", type=str, default="48:00:00", help="The time that the running of perSVade in nodes of a cluster will take.")

# other args
parser.add_argument("-mchr", "--mitochondrial_chromosome", dest="mitochondrial_chromosome", default="mito_C_glabrata_CBS138", type=str, help="The name of the mitochondrial chromosome. This is important if you have mitochondrial proteins for which to annotate the impact of nonsynonymous variants, as the mitochondrial genetic code is different. This should be the same as in the gff. If there is no mitochondria just put 'no_mitochondria'. If there is more than one mitochindrial scaffold, provide them as comma-sepparated IDs.")

# do not clean the outdir
parser.add_argument("--skip_cleaning_outdir", dest="skip_cleaning_outdir", action="store_true", default=False, help="Will NOT remove all the unnecessary files of the perSVade outdir")

# arg to run the trimming of the reads
parser.add_argument("--QC_and_trimming_reads", dest="QC_and_trimming_reads", action="store_true", default=False, help="Will run fastq and trimmomatic of reads, and use the trimmed reads for downstream analysis. This option will generate files under the same dir as f1 and f2, so be aware of it.")

# small VarCalk and CNV args
parser.add_argument("--run_smallVarsCNV", dest="run_smallVarsCNV", action="store_true", default=False, help="Will call small variants and CNV.")
parser.add_argument("-gff", "--gff-file", dest="gff", default=None, help="path to the GFF3 annotation of the reference genome. Make sure that the IDs are completely unique for each 'gene' tag. This is necessary for both the CNV analysis (it will look at genes there) and the annotation of the variants.")
parser.add_argument("-caller", "--caller", dest="caller", required=False, default="all", help="SNP caller option to obtain vcf file. options: no/all/HaplotypeCaller/bcftools/freebayes. It can be a comma-sepparated string, like 'HaplotypeCaller,freebayes'")
parser.add_argument("-c", "--coverage", dest="coverage", default=20, type=int, help="minimum Coverage (int)")
parser.add_argument("--minAF_smallVars", dest="minAF_smallVars", default="infer", help="The minimum fraction of reads covering a variant to be called. The default is 'infer', which will set a threshold based on the ploidy. This is only relevant for the final vcfs, where only PASS vars are considered. It can be a number between 0 and 1.")


parser.add_argument("-mcode", "--mitochondrial_code", dest="mitochondrial_code", default=3, type=int, help="The code of the NCBI mitochondrial genetic code. For yeasts it is 3. You can find the numbers for your species here https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi")
parser.add_argument("-gcode", "--gDNA_code", dest="gDNA_code", default=1, type=int, help="The code of the NCBI gDNA genetic code. You can find the numbers for your species here https://www.ncbi.nlm.nih.gov/Taxonomy/Utils/wprintgc.cgi . For C. albicans it is 12. ")
parser.add_argument("--remove_smallVarsCNV_nonEssentialFiles", dest="remove_smallVarsCNV_nonEssentialFiles", action="store_true", default=False, help="Will remove all the varCall files except the integrated final file and the bam file.")
parser.add_argument("--markDuplicates_inBam", dest="markDuplicates_inBam", action="store_true", default=False, help="Will mark the duplicates in the bam file. This is only necessary if the input of the pipeline is a sorted bam (-sbam) instead of raw reads.")
parser.add_argument("--replace_var_integration", dest="replace_var_integration", action="store_true", help="Replace all the variant integration steps for smallVariantCalling.")

parser.add_argument("--pooled_sequencing", dest="pooled_sequencing", action="store_true", default=False, help="It is a pooled sequencing run, which means that the small variant calling is not done based on ploidy. If you are also running SV calling, check that the simulation_ploidies, resemble a population,")

# repeat obtention
parser.add_argument("--consider_repeats_smallVarCall", dest="consider_repeats_smallVarCall", action="store_true", default=False, help="If --run_smallVarsCNV, this option will imply that each small  variant will have an annotation of whether it overlaps a repeat region.")

parser.add_argument("--previous_repeats_table", dest="previous_repeats_table", default=None, help="This may be the path to a file that contains the processed output of RepeatMasker (such as the one output by the function get_repeat_maskerDF). This should be a table with the following header: 'SW_score, perc_div, perc_del, perc_ins, chromosome, begin_repeat, end_repeat, left_repeat, strand, repeat, type, position_inRepeat_begin, position_inRepeat_end, left_positionINrepeat, IDrepeat'. It is created by parsing the tabular output of RepeatMasker and putting into a real .tab format.")

# small varCall stop options
parser.add_argument("--StopAfter_smallVarCallSimpleRunning", dest="StopAfter_smallVarCallSimpleRunning", action="store_true", default=False, help="Stop after obtaining the filtered vcf outputs of each program.")


opt = parser.parse_args()

########################################
##### GENERAL PROCESSING OF INPUTS #####
########################################

# if replace is set remove the outdir, and then make it
if opt.replace is True: fun.delete_folder(opt.outdir)
fun.make_folder(opt.outdir)

# define the name as the sample as the first 10 characters of the outdir
name_sample = fun.get_file(opt.outdir)[0:10]
print("getting into %s"%opt.outdir)

#### REPLACE THE REF GENOME ####

# define where the reference genome will be stored
reference_genome_dir = "%s/reference_genome_dir"%(opt.outdir); fun.make_folder(reference_genome_dir)
new_reference_genome_file = "%s/reference_genome.fasta"%reference_genome_dir

# copy the reference genome were it should
if fun.file_is_empty(new_reference_genome_file) or opt.replace is True:

    # move the reference genome into the outdir, so that every file is written under outdir
    fun.soft_link_files(opt.ref, new_reference_genome_file)
   
opt.ref = new_reference_genome_file

# check that the mitoChromosomes are in the ref
all_chroms = {s.id for s in SeqIO.parse(opt.ref, "fasta")}
if any([x not in all_chroms for x in opt.mitochondrial_chromosome.split(",")]) and opt.mitochondrial_chromosome!="no_mitochondria":
    raise ValueError("The provided mitochondrial_chromosomes are not in the reference genome.")

# get the genome len
genome_length = sum(fun.get_chr_to_len(opt.ref).values())
print("The genome has %.2f Mb"%(genome_length/1000000 ))

##################################

#### REPLACE THE GFF ####
target_gff = "%s/reference_genome_features.gff"%reference_genome_dir

# copy the gff
if opt.gff is None: print("WARNING: gff was not provided. This will be a problem if you want to annotate small variant calls")
else:

    if fun.file_is_empty(target_gff): fun.soft_link_files(opt.gff, target_gff)

    # change the path
    opt.gff = target_gff

#########################

#### REPLACE THE REPEATS TABLE IF PROVIDED ####
if opt.previous_repeats_table is not None:
    print("using privided repeats %s"%opt.previous_repeats_table)

    # define the dest file
    repeats_table_file = "%s.repeats.tab"%opt.ref

    # softlink
    fun.soft_link_files(opt.previous_repeats_table, repeats_table_file)

###############################################

if opt.StopAfter_genomeObtention is True: 
    print("Stopping pipeline after the genome obtention.")
    sys.exit(0)

#### define misc args ####

# warn if you are running pooled_sequencing
if opt.pooled_sequencing is True: print("WARNING: If you are running SV calling, make sure that the pooled sequencing simulation is consistent with these simulated ploidies: %s. For example, you may want to optimise to detect pools of 1/100 of SVs."%(opt.simulation_ploidies))

# the simulation ploidies as a list
simulation_ploidies = opt.simulation_ploidies.split(",")

# the window length for all operations
fun.window_l = int(np.median([len_seq for chrom, len_seq  in fun.get_chr_to_len(opt.ref).items() if chrom not in opt.mitochondrial_chromosome.split(",")])*0.05) + 1

print("using a window length of %i"%fun.window_l)

# get the repeats table
print("getting repeats")
repeats_df, repeats_table_file = fun.get_repeat_maskerDF(opt.ref, threads=opt.threads, replace=opt.replace)

if opt.StopAfter_repeatsObtention is True:
	print("Stopping after the obtention of repeats")
	sys.exit(0)

#############################

########################################
########################################
########################################


#####################################
############# BAM FILE ##############
#####################################

if not any([x=="skip" for x in {opt.fastq1, opt.fastq2}]):

    ##### DEFINE THE SORTED BAM #####

    # define files that may be used in many steps of the pipeline
    if opt.sortedbam is None:

        bamfile = "%s/aligned_reads.bam"%opt.outdir
        sorted_bam = "%s.sorted"%bamfile
        index_bam = "%s.bai"%sorted_bam

    else:

        # debug the fact that you prvided reads and bam. You should just provide one
        if any([not x is None for x in {opt.fastq1, opt.fastq2}]): raise ValueError("You have provided reads and a bam, you should only provide one")

        # get the files
        sorted_bam = opt.sortedbam
        index_bam = "%s.bai"%sorted_bam

    ###################################

    # normal alignment of provided reads
    if all([not x is None for x in {opt.fastq1, opt.fastq2}]):

        # if the reads have to be QC and trimmed:
        if opt.QC_and_trimming_reads is True: 
            print("running trimming and QC of the reads")
            opt.fastq1, opt.fastq2 = fun.run_trimmomatic(opt.fastq1, opt.fastq2, replace=opt.replace, threads=opt.threads)

        print("WORKING ON ALIGNMENT")
        fun.run_bwa_mem(opt.fastq1, opt.fastq2, opt.ref, opt.outdir, bamfile, sorted_bam, index_bam, name_sample, threads=opt.threads, replace=opt.replace)


    else: print("Warning: No fastq file given, assuming that you provided a bam file")

    # mark duplicates if neccessary 
    if opt.markDuplicates_inBam is True: sorted_bam = fun.get_sortedBam_with_duplicatesMarked(sorted_bam, threads=opt.threads, replace=opt.replace)

    # check that all the important files exist
    if any([fun.file_is_empty(x) for x in {sorted_bam, index_bam}]): raise ValueError("You need the sorted and indexed bam files in ")

#####################################
#####################################
#####################################

###########################################
############# NECESSARY FILES #############
###########################################

# First create some files that are important for any program

# Create a reference dictionary
rstrip = opt.ref.split(".")[-1]
dictionary = "%sdict"%(opt.ref.rstrip(rstrip)); tmp_dictionary = "%s.tmp"%dictionary; 
if fun.file_is_empty(dictionary) or opt.replace is True:

    # remove any previously created tmp_file
    if not fun.file_is_empty(tmp_dictionary): os.unlink(tmp_dictionary)

    print("Creating picard dictionary")
    cmd_dict = "%s CreateSequenceDictionary R=%s O=%s TRUNCATE_NAMES_AT_WHITESPACE=true"%(picard_exec, opt.ref, tmp_dictionary); fun.run_cmd(cmd_dict)   
    os.rename(tmp_dictionary , dictionary)

# Index the reference
if fun.file_is_empty("%s.fai"%opt.ref) or opt.replace is True:
    print ("Indexing the reference...")
    cmd_indexRef = "%s faidx %s"%(samtools, opt.ref); fun.run_cmd(cmd_indexRef) # This creates a .bai file of the reference


#### calculate coverage per windows of window_l ####

if not any([x=="skip" for x in {opt.fastq1, opt.fastq2}]):

    destination_dir = "%s.calculating_windowcoverage"%sorted_bam
    coverage_file = fun.generate_coverage_per_window_file_parallel(opt.ref, destination_dir, sorted_bam, windows_file="none", replace=opt.replace, run_in_parallel=True, delete_bams=True)

####################################################



###########################################
###########################################
###########################################

if opt.StopAfter_bamFileObtention is True: 
    print("Stopping pipeline after the bamfile obtention.")
    sys.exit(0)

#####################################
##### STRUCTURAL VARIATION ##########
#####################################

#### test how well the finding of SVs in an assembly works ####
if opt.testSVgen_from_DefaulReads:

    outdir_test_FindSVinAssembly = "%s/test_FindSVfromDefaultSimulations"%opt.outdir
    if __name__ == '__main__': fun.test_SVgeneration_from_DefaultParms(opt.ref, outdir_test_FindSVinAssembly, sorted_bam, threads=opt.threads, replace=opt.replace, n_simulated_genomes=opt.nsimulations, mitochondrial_chromosome=opt.mitochondrial_chromosome, nvars=opt.nvars)

###############################################################

##### find a dict that maps each svtype to a file with a set of real SVs (real_svtype_to_file) #####
all_svs = {'translocations', 'insertions', 'deletions', 'inversions', 'tandemDuplications'}

if opt.SVs_compatible_to_insert_dir is not None and opt.fast_SVcalling is False: 
    print("using the set of real variants from %s"%opt.SVs_compatible_to_insert_dir)

    # if it is already predefined
    real_svtype_to_file = {svtype : "%s/%s.tab"%(opt.SVs_compatible_to_insert_dir, svtype) for svtype in all_svs if not fun.file_is_empty("%s/%s.tab"%(opt.SVs_compatible_to_insert_dir, svtype))}

elif opt.fast_SVcalling is False and opt.close_shortReads_table is not None:
    
    # the table was provided
    if opt.close_shortReads_table!="auto": 

        print("finding the set of compatible SVs from %s"%opt.close_shortReads_table)

        # define the outdir for the real vars
        outdir_finding_realVars = "%s/findingRealSVs_providedCloseReads"%opt.outdir

    # a taxID was provided, which overrides the value of opt.genomes_withSV_and_shortReads_table
    else:

        print("finding close genomes or reads for close taxIDs in the SRA database for taxID %s"%opt.target_taxID)

        # define the outdir for the real vars
        outdir_finding_realVars = "%s/findingRealSVs_automaticFindingOfCloseReads"%opt.outdir; fun.make_folder(outdir_finding_realVars)

        # define the outdir where the close genomes whould be downloaded
        outdir_getting_closeReads = "%s/getting_closeReads"%outdir_finding_realVars; fun.make_folder(outdir_getting_closeReads)

        opt.close_shortReads_table = fun.get_close_shortReads_table_close_to_taxID(opt.target_taxID, opt.ref, outdir_getting_closeReads, opt.ploidy, n_close_samples=opt.n_close_samples, nruns_per_sample=opt.nruns_per_sample, replace=opt.replace, threads=opt.threads, job_array_mode=opt.job_array_mode, StopAfter_sampleIndexingFromSRA=opt.StopAfter_sampleIndexingFromSRA, queue_jobs=opt.queue_jobs, max_ncores_queue=opt.max_ncores_queue, time_read_obtention=opt.time_read_obtention, StopAfterPrefecth_of_reads=opt.StopAfterPrefecth_of_reads)

    # skip the running of the pipeline 
    if opt.StopAfter_readObtentionFromSRA:
        print("Stopping pipeline after the reads obtention from SRA")
        sys.exit(0) 

    # skip pipeline running if you have to stop after prefetch of reads
    if opt.StopAfterPrefecth_of_reads:
        print("Stopping pipeline after the prefetch of reads")
        sys.exit(0) 

    # get the real SVs
    real_svtype_to_file = fun.get_compatible_real_svtype_to_file(opt.close_shortReads_table, opt.ref, outdir_finding_realVars, replace=opt.replace, threads=opt.threads, max_nvars=opt.nvars, mitochondrial_chromosome=opt.mitochondrial_chromosome, job_array_mode=opt.job_array_mode, max_ncores_queue=opt.max_ncores_queue, time_perSVade_running=opt.time_perSVade_running, queue_jobs=opt.queue_jobs)

    # redefine the SVs_compatible_to_insert_dir
    opt.SVs_compatible_to_insert_dir = "%s/SVs_compatible_to_insert"%outdir_finding_realVars

else: 
    print("Avoiding the simulation of real variants. Only inserting randomSV.")

    # define the set of vars as empty. This will trigger the random generation of vars
    real_svtype_to_file = {}


if opt.StopAfter_obtentionOFcloseSVs: 
    print("stopping pipeline after obtention of close SVs")
    sys.exit(0)



###################################################################################################

# test accuracy on real data
if opt.testAccuracy is True:  

    # test that you have provided a opt.close_shortReads_table
    if opt.close_shortReads_table is None or opt.fast_SVcalling is True: 
        raise ValueError("You have to specify a --close_shortReads_table and not run in --fast_SVcalling to test the accuracy of the pipeline on several datasets (--testAccuracy)")

    fun.report_accuracy_realSVs(opt.close_shortReads_table, opt.ref, "%s/testing_Accuracy"%opt.outdir, real_svtype_to_file, opt.SVs_compatible_to_insert_dir, threads=opt.threads, replace=opt.replace, n_simulated_genomes=opt.nsimulations, mitochondrial_chromosome=opt.mitochondrial_chromosome, simulation_ploidies=simulation_ploidies, range_filtering_benchmark=opt.range_filtering_benchmark, nvars=opt.nvars, job_array_mode=opt.job_array_mode, max_ncores_queue=opt.max_ncores_queue, time_perSVade_running=opt.time_perSVade_running, queue_jobs=opt.queue_jobs, StopAfter_testAccuracy_perSVadeRunning=opt.StopAfter_testAccuracy_perSVadeRunning)


# get the golden set
if opt.goldenSet_dir is not None:

    outdir_goldenSet = "%s/testing_goldenSetAccuracy"%opt.outdir
    fun.report_accuracy_golden_set(opt.goldenSet_dir, outdir_goldenSet, opt.ref, real_svtype_to_file, threads=opt.threads, replace=opt.replace, n_simulated_genomes=opt.nsimulations, mitochondrial_chromosome=opt.mitochondrial_chromosome, simulation_ploidies=simulation_ploidies, range_filtering_benchmark=opt.range_filtering_benchmark, nvars=opt.nvars, job_array_mode=opt.job_array_mode, StopAfter_sampleIndexingFromSRA=opt.StopAfter_sampleIndexingFromSRA, time_read_obtention=opt.time_read_obtention, StopAfterPrefecth_of_reads=opt.StopAfterPrefecth_of_reads_goldenSet, queue_jobs=opt.queue_jobs, max_ncores_queue=opt.max_ncores_queue, time_perSVade_running=opt.time_perSVade_running, target_taxID=opt.target_taxID)

# run the actual perSVade function optimising parameters
if opt.skip_SVcalling is False and not any([x=="skip" for x in {opt.fastq1, opt.fastq2}]):

    SVdetection_outdir = "%s/SVdetection_output"%opt.outdir
    fun.run_GridssClove_optimising_parameters(sorted_bam, opt.ref, SVdetection_outdir, threads=opt.threads, replace=opt.replace, n_simulated_genomes=opt.nsimulations, mitochondrial_chromosome=opt.mitochondrial_chromosome, simulation_ploidies=simulation_ploidies, range_filtering_benchmark=opt.range_filtering_benchmark, nvars=opt.nvars, fast_SVcalling=opt.fast_SVcalling, real_svtype_to_file=real_svtype_to_file)


print("structural variation analysis with perSVade finished")

#####################################
#####################################
#####################################


#####################################
###### SMALL VARS AND CNV ###########
#####################################

if opt.run_smallVarsCNV:

    # define an outdir
    outdir_varcall = "%s/smallVars_CNV_output"%opt.outdir

    # define the basic cmd
    varcall_cmd = "%s -r %s --threads %i --outdir %s -p %i -sbam %s --caller %s --coverage %i --mitochondrial_chromosome %s --mitochondrial_code %i --gDNA_code %i --minAF_smallVars %s"%(varcall_cnv_pipeline, opt.ref, opt.threads, outdir_varcall, opt.ploidy, sorted_bam, opt.caller, opt.coverage, opt.mitochondrial_chromosome, opt.mitochondrial_code, opt.gDNA_code, opt.minAF_smallVars)

    # add options
    if opt.replace is True: varcall_cmd += " --replace"
    if opt.gff is not None: varcall_cmd += " -gff %s"%opt.gff
    if opt.remove_smallVarsCNV_nonEssentialFiles is True: varcall_cmd += " --remove_smallVarsCNV_nonEssentialFiles"
    if opt.StopAfter_smallVarCallSimpleRunning is True: varcall_cmd += " --StopAfter_smallVarCallSimpleRunning"
    if opt.replace_var_integration is True: varcall_cmd += " --replace_var_integration"
    if opt.pooled_sequencing is True: varcall_cmd += " --pooled_sequencing"
    if opt.consider_repeats_smallVarCall is True: varcall_cmd += " --repeats_table %s"%repeats_table_file

    # run
    if __name__ == '__main__': fun.run_cmd(varcall_cmd)

#####################################
#####################################
#####################################

# at the end you want to clean the outdir to keep only the essential files
if opt.skip_cleaning_outdir is False: fun.clean_perSVade_outdir(opt.outdir)

# generate a file that indicates whether the gridss run is finished
final_file = "%s/perSVade_finished_file.txt"%opt.outdir
open(final_file, "w").write("perSVade_finished finished...")


print("perSVade Finished")


