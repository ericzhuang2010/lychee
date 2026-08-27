#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 SAMPLE_ID RUN_ACCESSION [--preprocess-only]" >&2
  exit 2
fi

sample_id=$1
run_accession=$2
mode=${3:-full}
if [[ ${mode} != full && ${mode} != --preprocess-only ]]; then
  echo "unsupported mode: ${mode}" >&2
  exit 2
fi
raw_dir=data/active_discovery/PRJNA830488/fastq
trim_dir=data/active_discovery/PRJNA830488/trimmed
qc_dir=results/qc/PRJNA830488
align_dir=results/alignment/PRJNA830488
salmon_dir=results/quantification/PRJNA830488/salmon
r1=${raw_dir}/${run_accession}_1.fastq.gz
r2=${raw_dir}/${run_accession}_2.fastq.gz
trim_r1=${trim_dir}/${sample_id}_R1.fastq.gz
trim_r2=${trim_dir}/${sample_id}_R2.fastq.gz

if [[ ! -s ${r1} || ! -s ${r2} ]]; then
  echo "validated FASTQ pair is not present for ${sample_id}/${run_accession}" >&2
  exit 1
fi

mkdir -p "${qc_dir}/raw" "${qc_dir}/fastp" "${qc_dir}/trimmed" "${trim_dir}"
if [[ ! -s ${qc_dir}/raw/${sample_id}_R1_fastqc.zip || ! -s ${qc_dir}/raw/${sample_id}_R2_fastqc.zip ]]; then
  fastqc -t 2 -o "${qc_dir}/raw" "${r1}" "${r2}"
  mv "${qc_dir}/raw/${run_accession}_1_fastqc.html" "${qc_dir}/raw/${sample_id}_R1_fastqc.html"
  mv "${qc_dir}/raw/${run_accession}_1_fastqc.zip" "${qc_dir}/raw/${sample_id}_R1_fastqc.zip"
  mv "${qc_dir}/raw/${run_accession}_2_fastqc.html" "${qc_dir}/raw/${sample_id}_R2_fastqc.html"
  mv "${qc_dir}/raw/${run_accession}_2_fastqc.zip" "${qc_dir}/raw/${sample_id}_R2_fastqc.zip"
fi

if [[ ! -s ${trim_r1} || ! -s ${trim_r2} || ! -s ${qc_dir}/fastp/${sample_id}.json ]]; then
  fastp --thread 8 --detect_adapter_for_pe \
    --qualified_quality_phred 15 --length_required 30 \
    --in1 "${r1}" --in2 "${r2}" \
    --out1 "${trim_r1}" --out2 "${trim_r2}" \
    --json "${qc_dir}/fastp/${sample_id}.json" \
    --html "${qc_dir}/fastp/${sample_id}.html"
fi

if [[ ! -s ${qc_dir}/trimmed/${sample_id}_R1_fastqc.zip || ! -s ${qc_dir}/trimmed/${sample_id}_R2_fastqc.zip ]]; then
  fastqc -t 2 -o "${qc_dir}/trimmed" "${trim_r1}" "${trim_r2}"
fi

if [[ ${mode} == --preprocess-only ]]; then
  echo "completed preprocessing ${sample_id} ${run_accession}"
  exit 0
fi

sample_align=${align_dir}/${sample_id}
mkdir -p "${sample_align}"
bam=${sample_align}/Aligned.sortedByCoord.out.bam
if [[ ! -s ${bam} || ! -s ${sample_align}/Log.final.out ]]; then
  STAR --runThreadN 12 --genomeDir data/reference/indexes/star \
    --readFilesIn "${trim_r1}" "${trim_r2}" --readFilesCommand zcat \
    --twopassMode Basic --outFileNamePrefix "${sample_align}/" \
    --outSAMtype BAM SortedByCoordinate --outSAMattributes NH HI AS nM MD \
    --outSAMunmapped Within --quantMode GeneCounts \
    --outFilterMultimapNmax 20 --outFilterMismatchNoverReadLmax 0.04 \
    --limitBAMsortRAM 4000000000
fi
if [[ ! -s ${bam}.bai ]]; then
  samtools index -@ 8 "${bam}"
fi
samtools idxstats "${bam}" > "${sample_align}/idxstats.tsv"

if [[ ! -s ${salmon_dir}/${sample_id}/quant.sf ]]; then
  salmon quant -i data/reference/indexes/salmon/index -l A \
    -1 "${trim_r1}" -2 "${trim_r2}" -p 8 \
    --geneMap data/reference/combined/transcript_to_gene.tsv \
    --deterministic --seqBias --gcBias --numBootstraps 30 \
    -o "${salmon_dir}/${sample_id}"
fi

echo "completed ${sample_id} ${run_accession}"
