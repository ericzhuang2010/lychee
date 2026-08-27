#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${root}"

discovery_complete=results/audit/discovery_main_workflow.complete
full_complete=results/audit/full_computational_plan.complete
log=analysis/logs/full_plan_continuation.log
mkdir -p results/audit analysis/logs
exec 8>results/audit/full_plan_continuation.lock
if ! flock -n 8; then
  echo "another full-plan continuation holds the lock" >&2
  exit 1
fi
exec > >(tee -a "${log}") 2>&1

while [[ ! -e ${discovery_complete} ]]; do
  echo "$(date --iso-8601=seconds) waiting for frozen discovery workflow"
  sleep 60
done

sha256sum -c results/discovery/frozen_results.sha256
sha256sum -c results/robustness/internal_results.sha256
sha256sum -c results/evidence/annotation/final_annotation.sha256
sha256sum -c results/evidence/motifs/results/motif_results.sha256
test -s results/discovery/external_outcomes_unlock_timestamp.txt

python3 analysis/scripts/22_cleanup_study.py \
  --study PRJNA830488 \
  --matrix-manifest results/quantification/PRJNA830488/discovery_matrix.sha256 \
  --qc-report results/audit/PRJNA830488_technical_qc.tsv \
  --completion-manifest results/robustness/internal_results.sha256

for study in PRJNA450886 PRJNA922966 PRJNA1090613; do
  matrix_manifest="results/quantification/${study}/matrix.sha256"
  completion_manifest="results/external/${study}/external_results.sha256"
  qc_report="results/audit/${study}_technical_qc.tsv"
  if [[ -s ${matrix_manifest} && -s ${completion_manifest} ]]; then
    echo "$(date --iso-8601=seconds) verifying completed external study ${study}"
    if ! sha256sum -c "${matrix_manifest}" || ! sha256sum -c "${completion_manifest}"; then
      echo "completed-study manifest verification failed for ${study}; refusing recomputation" >&2
      exit 1
    fi
    python3 analysis/scripts/22_cleanup_study.py \
      --study "${study}" \
      --matrix-manifest "${matrix_manifest}" \
      --qc-report "${qc_report}" \
      --completion-manifest "${completion_manifest}"
    echo "$(date --iso-8601=seconds) skipped verified completed external study ${study}"
    continue
  fi

  echo "$(date --iso-8601=seconds) starting external study ${study}"
  # Drain samples whose trimmed FASTQs are already staged through STAR and
  # featureCounts before allowing more downloads.  This keeps the 14-GB STAR
  # rule isolated from large concurrent transfers on the 15-GB host.
  ready_alignment_targets=()
  while IFS=$'\t' read -r sample _; do
    [[ ${sample} == sample_id ]] && continue
    trimmed_r1="data/active_external/${study}/trimmed/${sample}_R1.fastq.gz"
    trimmed_r2="data/active_external/${study}/trimmed/${sample}_R2.fastq.gz"
    sample_counts="results/quantification/${study}/featureCounts/${sample}.txt"
    if [[ -s ${trimmed_r1} && -s ${trimmed_r2} && ! -s ${sample_counts} ]]; then
      ready_alignment_targets+=("${sample_counts}")
    fi
  done < "analysis/metadata/${study}_samples.tsv"
  if (( ${#ready_alignment_targets[@]} > 0 )); then
    echo "$(date --iso-8601=seconds) prioritizing ${#ready_alignment_targets[@]} staged STAR/featureCounts sample(s) for ${study}"
    .tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
      --snakefile analysis/workflow/external_study.smk \
      --configfile analysis/config/release.yaml \
      --config study="${study}" \
      --cores 16 \
      --resources mem_mb=15000 alignment_slots=1 download_slots=1 \
      --set-resources download_external_sample:mem_mb=1500 \
      --notemp \
      --rerun-triggers mtime --rerun-incomplete --printshellcmds \
      "${ready_alignment_targets[@]}"
  fi

  echo "runtime memory safeguard: external downloads cannot overlap the 14-GB STAR rule"
  .tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
    --snakefile analysis/workflow/external_study.smk \
    --configfile analysis/config/release.yaml \
    --config study="${study}" \
    --cores 16 \
    --resources mem_mb=15000 alignment_slots=1 download_slots=1 \
    --set-resources download_external_sample:mem_mb=1500 \
    --rerun-triggers mtime --rerun-incomplete --printshellcmds

  sha256sum -c "${matrix_manifest}"
  sha256sum -c "${completion_manifest}"
  python3 analysis/scripts/22_cleanup_study.py \
    --study "${study}" \
    --matrix-manifest "${matrix_manifest}" \
    --qc-report "${qc_report}" \
    --completion-manifest "${completion_manifest}"
done

echo "$(date --iso-8601=seconds) starting final evidence/reporting workflow"
.tools/bin/micromamba run -p .conda/lychee-discovery snakemake \
  --snakefile analysis/workflow/finalize.smk \
  --configfile analysis/config/release.yaml \
  --cores 16 --resources mem_mb=15000 \
  --rerun-triggers mtime --printshellcmds

sha256sum -c results/release/release_bundle.sha256
touch "${full_complete}"
echo "$(date --iso-8601=seconds) full automated computational plan completed"
