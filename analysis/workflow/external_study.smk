configfile: "analysis/config/release.yaml"

import csv


STUDY = config.get("study", "PRJNA450886")
SAMPLE_TABLES = {
    "PRJNA450886": "analysis/metadata/PRJNA450886_samples.tsv",
    "PRJNA922966": "analysis/metadata/PRJNA922966_samples.tsv",
    "PRJNA1090613": "analysis/metadata/PRJNA1090613_samples.tsv",
}
if STUDY not in SAMPLE_TABLES:
    raise ValueError(f"Unsupported frozen external study: {STUDY}")
SAMPLE_TABLE = SAMPLE_TABLES[STUDY]
with open(SAMPLE_TABLE) as handle:
    SAMPLE_ROWS = list(csv.DictReader(handle, delimiter="\t"))
if any(row["library_layout"] != "PAIRED" or row["modality"] != "mRNA" for row in SAMPLE_ROWS):
    raise ValueError("The external mRNA workflow requires paired long-RNA libraries")
SAMPLES = [row["sample_id"] for row in SAMPLE_ROWS]
ROW = {row["sample_id"]: row for row in SAMPLE_ROWS}
RUN = {sample: ROW[sample]["run"] for sample in SAMPLES}

RAW_DIR = f"data/active_external/{STUDY}/fastq"
TRIM_DIR = f"data/active_external/{STUDY}/trimmed"
ALIGN_DIR = f"results/alignment/{STUDY}"
QC_DIR = f"results/qc/{STUDY}"
QUANT_DIR = f"results/quantification/{STUDY}"
SALMON_DIR = f"{QUANT_DIR}/salmon"
EXTERNAL_DIR = f"results/external/{STUDY}"
DOWNLOAD_AUDIT_DIR = f"results/audit/{STUDY}_fastq_download"
PATHWAY_GMT = "data/reference/pathways/frozen_plant_reactome_UP000059680/plant_reactome_litchi.gmt"
ORTHOGONAL_TARGETS = (
    [f"{EXTERNAL_DIR}/motifs/transport/external_motif_transport.sha256"]
    if STUDY == "PRJNA450886" else []
)


rule all:
    input:
        f"{EXTERNAL_DIR}/external_results.sha256",
        f"{QC_DIR}/multiqc_report.html",
        f"{QUANT_DIR}/matrix.sha256",
        *ORTHOGONAL_TARGETS,


rule verify_external_unlock:
    input:
        discovery="results/discovery/frozen_results.sha256",
        unlock="results/discovery/external_outcomes_unlock_timestamp.txt",
        external="analysis/preregistration/external_validation_bundle.sha256",
        config="analysis/config/external_validation.yaml",
    output:
        f"{EXTERNAL_DIR}/external_analysis_lock.tsv"
    threads: 1
    resources:
        mem_mb=500
    shell:
        """
        python analysis/scripts/20_verify_external_unlock.py \
          --discovery-manifest {input.discovery} --unlock {input.unlock} \
          --external-manifest {input.external} --config {input.config} \
          --study {STUDY} --output {output}
        """


rule download_external_sample:
    input:
        gate=rules.verify_external_unlock.output,
    output:
        r1=f"{RAW_DIR}/{{sample}}_R1.fastq.gz",
        r2=f"{RAW_DIR}/{{sample}}_R2.fastq.gz",
        report=f"{DOWNLOAD_AUDIT_DIR}/{{sample}}.tsv",
        marker=f"{RAW_DIR}/.{{sample}}.download_complete",
    threads: 1
    resources:
        mem_mb=1000,
        download_slots=1
    shell:
        """
        python analysis/scripts/04_download_fastq.py \
          --samples {SAMPLE_TABLE} --sample-id {wildcards.sample} \
          --name-by-sample \
          --outdir {RAW_DIR} --report {output.report} --marker {output.marker} \
          --minimum-free-bytes {config[minimum_free_bytes_before_study]} \
          --connections 4
        """


rule raw_fastqc_external:
    input:
        r1=rules.download_external_sample.output.r1,
        r2=rules.download_external_sample.output.r2,
    output:
        html1=f"{QC_DIR}/raw/{{sample}}_R1_fastqc.html",
        zip1=f"{QC_DIR}/raw/{{sample}}_R1_fastqc.zip",
        html2=f"{QC_DIR}/raw/{{sample}}_R2_fastqc.html",
        zip2=f"{QC_DIR}/raw/{{sample}}_R2_fastqc.zip",
    threads: 2
    resources:
        mem_mb=2000
    shell:
        """
        mkdir -p {QC_DIR}/raw
        fastqc -t {threads} -o {QC_DIR}/raw {input.r1} {input.r2}
        """


rule fastp_external:
    input:
        r1=rules.download_external_sample.output.r1,
        r2=rules.download_external_sample.output.r2,
    output:
        r1=temp(f"{TRIM_DIR}/{{sample}}_R1.fastq.gz"),
        r2=temp(f"{TRIM_DIR}/{{sample}}_R2.fastq.gz"),
        json=f"{QC_DIR}/fastp/{{sample}}.json",
        html=f"{QC_DIR}/fastp/{{sample}}.html",
    threads: config["fastp_threads"]
    resources:
        mem_mb=4000
    shell:
        """
        mkdir -p {TRIM_DIR} {QC_DIR}/fastp
        fastp --thread {threads} --detect_adapter_for_pe \
          --qualified_quality_phred 15 --length_required 30 \
          --in1 {input.r1} --in2 {input.r2} \
          --out1 {output.r1} --out2 {output.r2} \
          --json {output.json} --html {output.html}
        """


rule trimmed_fastqc_external:
    input:
        r1=rules.fastp_external.output.r1,
        r2=rules.fastp_external.output.r2,
    output:
        html1=f"{QC_DIR}/trimmed/{{sample}}_R1_fastqc.html",
        zip1=f"{QC_DIR}/trimmed/{{sample}}_R1_fastqc.zip",
        html2=f"{QC_DIR}/trimmed/{{sample}}_R2_fastqc.html",
        zip2=f"{QC_DIR}/trimmed/{{sample}}_R2_fastqc.zip",
    threads: 2
    resources:
        mem_mb=2000
    shell:
        "mkdir -p {QC_DIR}/trimmed && fastqc -t {threads} -o {QC_DIR}/trimmed {input.r1} {input.r2}"


rule star_align_external:
    input:
        r1=rules.fastp_external.output.r1,
        r2=rules.fastp_external.output.r2,
        genome="data/reference/indexes/star/Genome",
        sa="data/reference/indexes/star/SA",
        saindex="data/reference/indexes/star/SAindex",
    output:
        bam=temp(f"{ALIGN_DIR}/{{sample}}/Aligned.out.bam"),
        log=f"{ALIGN_DIR}/{{sample}}/Log.final.out",
        gene_counts=f"{ALIGN_DIR}/{{sample}}/ReadsPerGene.out.tab",
        idxstats=f"{ALIGN_DIR}/{{sample}}/idxstats.tsv",
    threads: config["star_threads"]
    resources:
        mem_mb=14000,
        alignment_slots=1
    shell:
        """
        mkdir -p {ALIGN_DIR}/{wildcards.sample}
        STAR --runThreadN {threads} --genomeDir data/reference/indexes/star \
          --readFilesIn {input.r1} {input.r2} --readFilesCommand zcat \
          --twopassMode Basic --outFileNamePrefix {ALIGN_DIR}/{wildcards.sample}/ \
          --outSAMtype BAM Unsorted --outSAMattributes NH HI AS nM MD \
          --outSAMunmapped None --quantMode GeneCounts \
          --outFilterMultimapNmax 20 --outFilterMismatchNoverReadLmax 0.04 \
          --limitBAMsortRAM {config[star_sort_ram_bytes]}
        # samtools 1.24 no longer falls back to a sequential idxstats scan for
        # an unindexed, unsorted BAM. Reproduce idxstats' four columns in one
        # sequential pass while preserving the low-memory unsorted BAM.
        samtools view -@ {threads} -h {output.bam} | \
          awk 'BEGIN {{ OFS="\t" }}
               $1 == "@SQ" {{
                 sn=""; ln=0;
                 for (i=2; i<=NF; i++) {{
                   if ($i ~ /^SN:/) sn=substr($i,4);
                   else if ($i ~ /^LN:/) ln=substr($i,4);
                 }}
                 order[++n]=sn; seqlen[sn]=ln; next
               }}
               substr($1,1,1) == "@" {{ next }}
               {{
                 flag=$2+0; ref=$3;
                 if (int(flag/4)%2 == 1) {{
                   if (ref == "*") unplaced++;
                   else unmapped[ref]++;
                 }} else if (ref != "*") {{
                   mapped[ref]++;
                 }}
               }}
               END {{
                 for (i=1; i<=n; i++) {{
                   ref=order[i];
                   print ref, seqlen[ref], mapped[ref]+0, unmapped[ref]+0;
                 }}
                 print "*", 0, 0, unplaced+0;
               }}' > {output.idxstats}
        """


rule featurecounts_external_sample:
    input:
        bam=rules.star_align_external.output.bam,
        gtf="data/reference/combined/host.annotation.gtf",
    output:
        counts=f"{QUANT_DIR}/featureCounts/{{sample}}.txt",
        summary=f"{QUANT_DIR}/featureCounts/{{sample}}.txt.summary",
    threads: 4
    resources:
        mem_mb=4000
    shell:
        """
        mkdir -p {QUANT_DIR}/featureCounts
        featureCounts -T {threads} -p --countReadPairs -B -C -s 0 \
          -t exon -g gene_id -a {input.gtf} -o {output.counts} {input.bam}
        """


rule salmon_quant_external:
    input:
        r1=rules.fastp_external.output.r1,
        r2=rules.fastp_external.output.r2,
        index="data/reference/indexes/salmon/index/info.json",
        tx2gene="data/reference/combined/transcript_to_gene.tsv",
    output:
        quant=f"{SALMON_DIR}/{{sample}}/quant.sf",
        meta=f"{SALMON_DIR}/{{sample}}/aux_info/meta_info.json",
    threads: 8
    resources:
        mem_mb=6000
    shell:
        """
        salmon quant -i data/reference/indexes/salmon/index -l A \
          -1 {input.r1} -2 {input.r2} -p {threads} \
          --geneMap {input.tx2gene} --deterministic --seqBias --gcBias \
          --numBootstraps 30 -o {SALMON_DIR}/{wildcards.sample}
        """


rule merge_external_counts:
    input:
        counts=expand(f"{QUANT_DIR}/featureCounts/{{sample}}.txt", sample=SAMPLES),
        summaries=expand(f"{QUANT_DIR}/featureCounts/{{sample}}.txt.summary", sample=SAMPLES),
        samples=SAMPLE_TABLE,
    output:
        counts=f"{QUANT_DIR}/gene_counts.tsv",
        annotation=f"{QUANT_DIR}/gene_annotation.tsv",
        summary=f"{QUANT_DIR}/featureCounts_summary.tsv",
    threads: 1
    resources:
        mem_mb=3000
    shell:
        """
        python analysis/scripts/17_merge_external_counts.py \
          --samples {input.samples} --input-dir {QUANT_DIR}/featureCounts \
          --counts {output.counts} --annotation {output.annotation} \
          --summary {output.summary}
        """


rule collect_external_qc:
    input:
        fastp=expand(f"{QC_DIR}/fastp/{{sample}}.json", sample=SAMPLES),
        star=expand(f"{ALIGN_DIR}/{{sample}}/Log.final.out", sample=SAMPLES),
        idxstats=expand(f"{ALIGN_DIR}/{{sample}}/idxstats.tsv", sample=SAMPLES),
        salmon=expand(f"{SALMON_DIR}/{{sample}}/aux_info/meta_info.json", sample=SAMPLES),
    output:
        report=f"results/audit/{STUDY}_technical_qc.tsv",
        decisions=f"results/audit/{STUDY}_sample_decisions.tsv",
    threads: 1
    resources:
        mem_mb=1000
    shell:
        """
        python analysis/scripts/07_collect_discovery_qc.py \
          --samples {SAMPLE_TABLE} --qc-root {QC_DIR} \
          --alignment-root {ALIGN_DIR} --salmon-root {SALMON_DIR} \
          --report {output.report} --decisions {output.decisions}
        """


rule multiqc_external:
    input:
        raw=expand(f"{QC_DIR}/raw/{{sample}}_R{{mate}}_fastqc.zip", sample=SAMPLES, mate=[1, 2]),
        trimmed=expand(f"{QC_DIR}/trimmed/{{sample}}_R{{mate}}_fastqc.zip", sample=SAMPLES, mate=[1, 2]),
        fastp=expand(f"{QC_DIR}/fastp/{{sample}}.json", sample=SAMPLES),
        star=expand(f"{ALIGN_DIR}/{{sample}}/Log.final.out", sample=SAMPLES),
        salmon=expand(f"{SALMON_DIR}/{{sample}}/aux_info/meta_info.json", sample=SAMPLES),
        featurecounts=expand(f"{QUANT_DIR}/featureCounts/{{sample}}.txt.summary", sample=SAMPLES),
    output:
        html=f"{QC_DIR}/multiqc_report.html",
        data=directory(f"{QC_DIR}/multiqc_data"),
    threads: 2
    resources:
        mem_mb=3000
    shell:
        "multiqc -f -o {QC_DIR} {QC_DIR} {ALIGN_DIR} {SALMON_DIR} {QUANT_DIR}"


rule freeze_external_matrix:
    input:
        counts=rules.merge_external_counts.output.counts,
        annotation=rules.merge_external_counts.output.annotation,
        summary=rules.merge_external_counts.output.summary,
        metadata=SAMPLE_TABLE,
        qc=rules.collect_external_qc.output.report,
        decisions=rules.collect_external_qc.output.decisions,
    output:
        f"{QUANT_DIR}/matrix.sha256"
    threads: 1
    resources:
        mem_mb=500
    shell:
        "sha256sum {input.counts} {input.annotation} {input.summary} {input.metadata} {input.qc} {input.decisions} > {output}"


rule external_gene_signature:
    input:
        counts=rules.merge_external_counts.output.counts,
        metadata=SAMPLE_TABLE,
        decisions=rules.collect_external_qc.output.decisions,
        matrix=rules.freeze_external_matrix.output,
        frozen_genes="results/discovery/frozen_genes.tsv",
        signature="results/discovery/frozen_signature.tsv",
        config="analysis/config/external_validation.yaml",
    output:
        all=f"{EXTERNAL_DIR}/genes/all_gene_contrasts.tsv",
        frozen=f"{EXTERNAL_DIR}/genes/frozen_gene_tests.tsv",
        signature=f"{EXTERNAL_DIR}/genes/signature_contrasts.tsv",
        scores=f"{EXTERNAL_DIR}/genes/signature_sample_scores.tsv",
        normalized=f"{EXTERNAL_DIR}/genes/normalized_counts.tsv",
        summary=f"{EXTERNAL_DIR}/genes/external_gene_signature_summary.md",
    threads: 4
    resources:
        mem_mb=14000
    shell:
        """
        Rscript analysis/scripts/18_external_gene_signature.R \
          --counts {input.counts} --metadata {input.metadata} \
          --decisions {input.decisions} --frozen-genes {input.frozen_genes} \
          --frozen-signature {input.signature} --config {input.config} \
          --study {STUDY} --outdir {EXTERNAL_DIR}/genes
        """


rule external_pathways:
    input:
        counts=rules.merge_external_counts.output.counts,
        metadata=SAMPLE_TABLE,
        decisions=rules.collect_external_qc.output.decisions,
        external_genes=rules.external_gene_signature.output.all,
        frozen_pathways="results/discovery/frozen_pathways.tsv",
        frozen_pathway_genes="results/discovery/frozen_pathway_gene_statistics.tsv",
        gmt=PATHWAY_GMT,
        gene_qc="results/qc/PRJNA830488/uniform_gene_mappability.tsv",
        discovery_config="analysis/config/discovery.yaml",
        external_config="analysis/config/external_validation.yaml",
    output:
        tests=f"{EXTERNAL_DIR}/pathways/frozen_pathway_tests.tsv",
        camera=f"{EXTERNAL_DIR}/pathways/camera.tsv",
        fgsea=f"{EXTERNAL_DIR}/pathways/fgsea.tsv",
        roast=f"{EXTERNAL_DIR}/pathways/roast.tsv",
        deletion=f"{EXTERNAL_DIR}/pathways/leading_edge_deletion.tsv",
        matched=f"{EXTERNAL_DIR}/pathways/matched_random_summary.tsv",
        summary=f"{EXTERNAL_DIR}/pathways/external_pathway_summary.md",
    threads: 4
    resources:
        mem_mb=12000
    shell:
        """
        Rscript analysis/scripts/19_external_pathways.R \
          --counts {input.counts} --metadata {input.metadata} \
          --decisions {input.decisions} --external-genes {input.external_genes} \
          --frozen-pathways {input.frozen_pathways} \
          --frozen-pathway-genes {input.frozen_pathway_genes} \
          --gmt {input.gmt} --gene-qc {input.gene_qc} \
          --discovery-config {input.discovery_config} \
          --external-config {input.external_config} \
          --study {STUDY} --outdir {EXTERNAL_DIR}/pathways
        """


rule external_dtu:
    input:
        frozen="results/discovery/frozen_dtu.tsv",
        metadata=SAMPLE_TABLE,
        decisions=rules.collect_external_qc.output.decisions,
        quant=expand(f"{SALMON_DIR}/{{sample}}/quant.sf", sample=SAMPLES),
        meta=expand(f"{SALMON_DIR}/{{sample}}/aux_info/meta_info.json", sample=SAMPLES),
        tx2gene="data/reference/combined/transcript_to_gene.tsv",
        discovery_config="analysis/config/discovery.yaml",
        operational_config="analysis/config/operational_qc.yaml",
        external_config="analysis/config/external_validation.yaml",
    output:
        tests=f"{EXTERNAL_DIR}/dtu/frozen_dtu_external_tests.tsv",
        gate=f"{EXTERNAL_DIR}/dtu/external_dtu_gate.tsv",
        nontranscript=f"{EXTERNAL_DIR}/dtu/salmon_nontranscript_targets.tsv",
        summary=f"{EXTERNAL_DIR}/dtu/external_dtu_summary.md",
    threads: 2
    resources:
        mem_mb=8000
    shell:
        """
        Rscript analysis/scripts/21_external_dtu.R \
          --frozen-dtu {input.frozen} --metadata {input.metadata} \
          --decisions {input.decisions} --salmon-root {SALMON_DIR} \
          --tx2gene {input.tx2gene} --discovery-config {input.discovery_config} \
          --operational-config {input.operational_config} \
          --external-config {input.external_config} --study {STUDY} \
          --outdir {EXTERNAL_DIR}/dtu
        """


rule freeze_external_results:
    input:
        gate=rules.verify_external_unlock.output,
        matrix=rules.freeze_external_matrix.output,
        genes=rules.external_gene_signature.output.frozen,
        signature=rules.external_gene_signature.output.signature,
        normalized=rules.external_gene_signature.output.normalized,
        pathways=rules.external_pathways.output.tests,
        dtu=rules.external_dtu.output.tests,
        dtu_nontranscript=rules.external_dtu.output.nontranscript,
        gene_summary=rules.external_gene_signature.output.summary,
        pathway_summary=rules.external_pathways.output.summary,
    output:
        f"{EXTERNAL_DIR}/external_results.sha256"
    threads: 1
    resources:
        mem_mb=500
    shell:
        """
        sha256sum {input.gate} {input.matrix} {input.genes} {input.signature} \
          {input.normalized} \
          {input.pathways} {input.dtu} {input.dtu_nontranscript} \
          {input.gene_summary} {input.pathway_summary} > {output}
        sha256sum -c {output}
        """


rule select_external_motif_response:
    input:
        contrasts=rules.external_gene_signature.output.all,
        config="analysis/config/orthogonal_validation.yaml",
    output:
        genes=f"{EXTERNAL_DIR}/motifs/response/external_response_genes.tsv",
        gate=f"{EXTERNAL_DIR}/motifs/response/external_response_gate.tsv",
        summary=f"{EXTERNAL_DIR}/motifs/response/external_response_summary.md",
        manifest=f"{EXTERNAL_DIR}/motifs/response/external_response.sha256",
    threads: 1
    resources:
        mem_mb=1000
    shell:
        """
        python analysis/scripts/31_select_external_motif_genes.py \
          --all-contrasts {input.contrasts} --config {input.config} \
          --study {STUDY} --outdir {EXTERNAL_DIR}/motifs/response
        sha256sum -c {output.manifest}
        """


rule prepare_external_motif_inputs:
    input:
        response=rules.select_external_motif_response.output.genes,
        response_manifest=rules.select_external_motif_response.output.manifest,
        normalized=rules.external_gene_signature.output.normalized,
        gene_qc="results/qc/PRJNA830488/uniform_gene_mappability.tsv",
        canonical="data/reference/combined/canonical_transcripts.tsv",
        gtf="data/reference/combined/host.annotation.gtf",
        genome="data/reference/combined/host_pathogen.fa",
        fai="data/reference/combined/host_pathogen.fa.fai",
        config="analysis/config/orthogonal_validation.yaml",
    output:
        manifest=f"{EXTERNAL_DIR}/motifs/inputs/motif_inputs.sha256",
        gate=f"{EXTERNAL_DIR}/motifs/inputs/motif_gate.tsv",
        assignments=f"{EXTERNAL_DIR}/motifs/inputs/background_assignments.tsv",
        promoters=f"{EXTERNAL_DIR}/motifs/inputs/promoter_metadata.tsv",
        candidates_1kb=f"{EXTERNAL_DIR}/motifs/inputs/frozen_candidates_1000bp.fa",
        candidates_2kb=f"{EXTERNAL_DIR}/motifs/inputs/frozen_candidates_2000bp.fa",
    threads: 1
    resources:
        mem_mb=4000
    shell:
        """
        python analysis/scripts/26_prepare_motif_inputs.py \
          --frozen-genes {input.response} --normalized-counts {input.normalized} \
          --gene-qc {input.gene_qc} --canonical {input.canonical} \
          --gtf {input.gtf} --genome {input.genome} --config {input.config} \
          --outdir {EXTERNAL_DIR}/motifs/inputs
        sha256sum -c {output.manifest}
        """


rule external_motif_transport:
    input:
        motif_inputs=rules.prepare_external_motif_inputs.output.manifest,
        response_gate=rules.select_external_motif_response.output.gate,
        discovery="results/evidence/motifs/results/robust_candidate_motifs.tsv",
        motifs="data/reference/motifs/JASPAR2026_CORE_plants_non-redundant_pfms_meme.txt",
        config="analysis/config/orthogonal_validation.yaml",
    output:
        manifest=f"{EXTERNAL_DIR}/motifs/transport/external_motif_transport.sha256",
        tests=f"{EXTERNAL_DIR}/motifs/transport/external_motif_transport.tsv",
        ame=f"{EXTERNAL_DIR}/motifs/transport/external_ame_replicates.tsv",
        fimo=f"{EXTERNAL_DIR}/motifs/transport/external_fimo_sensitivity.tsv",
        summary=f"{EXTERNAL_DIR}/motifs/transport/external_motif_transport_summary.md",
        fixed=f"{EXTERNAL_DIR}/motifs/transport/frozen_discovery_motifs.meme",
    threads: 2
    resources:
        mem_mb=6000
    shell:
        """
        python analysis/scripts/32_external_motif_transport.py \
          --inputs {EXTERNAL_DIR}/motifs/inputs --response-gate {input.response_gate} \
          --discovery-motifs {input.discovery} --motifs {input.motifs} \
          --config {input.config} --outdir {EXTERNAL_DIR}/motifs/transport
        sha256sum -c {output.manifest}
        """
