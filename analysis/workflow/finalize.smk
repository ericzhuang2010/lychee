configfile: "analysis/config/release.yaml"


rule all:
    input:
        "results/release/release_bundle.sha256",


rule finalize_evidence:
    input:
        discovery_manifest="results/discovery/frozen_results.sha256",
        all_gene_discovery="results/discovery/all_gene_discovery_status.tsv",
        gene_robustness="results/robustness/genes/frozen_gene_robustness.tsv",
        frozen_pathways="results/discovery/frozen_pathways.tsv",
        pathway_members="results/discovery/frozen_pathway_gene_statistics.tsv",
        pathway_robustness="results/robustness/pathways/frozen_pathway_robustness.tsv",
        external_manifest="results/external/PRJNA450886/external_results.sha256",
        external_genes="results/external/PRJNA450886/genes/frozen_gene_tests.tsv",
        external_pathways="results/external/PRJNA450886/pathways/frozen_pathway_tests.tsv",
        annotations="results/evidence/annotation/final_candidate_annotations.tsv",
        small_rna_gate="results/evidence/small_rna/reference/small_rna_reference_gate.tsv",
        discovery_motifs="results/evidence/motifs/results/robust_candidate_motifs.tsv",
        candidate_motif_sites="results/evidence/motifs/results/candidate_motif_site_presence.tsv",
        external_motif_manifest="results/external/PRJNA450886/motifs/transport/external_motif_transport.sha256",
        external_motifs="results/external/PRJNA450886/motifs/transport/external_motif_transport.tsv",
        published_manifest="results/evidence/published/published_evidence.sha256",
        published_registry="results/evidence/published_evidence_registry.tsv",
        config="analysis/config/orthogonal_validation.yaml",
    output:
        matrix="results/candidates/final_evidence_matrix.tsv",
        claims="results/candidates/final_claims.md",
        contradictions="results/candidates/contradictory_results.tsv",
        summary="results/candidates/tier_summary.tsv",
        manifest="results/candidates/final_evidence_matrix.sha256",
    threads: 1
    resources:
        mem_mb=1000
    shell:
        """
        python analysis/scripts/34_finalize_evidence.py \
          --all-gene-discovery {input.all_gene_discovery} \
          --gene-robustness {input.gene_robustness} \
          --frozen-pathways {input.frozen_pathways} --pathway-members {input.pathway_members} \
          --pathway-robustness {input.pathway_robustness} \
          --external-genes {input.external_genes} --external-pathways {input.external_pathways} \
          --annotations {input.annotations} --small-rna-gate {input.small_rna_gate} \
          --discovery-motifs {input.discovery_motifs} \
          --candidate-motif-sites {input.candidate_motif_sites} \
          --external-motifs {input.external_motifs} \
          --published-registry {input.published_registry} --config {input.config} \
          --outdir results/candidates
        sha256sum -c {output.manifest}
        """


rule generate_figures_tables:
    input:
        evidence=rules.finalize_evidence.output.manifest,
        discovery="results/discovery/frozen_results.sha256",
        internal="results/robustness/internal_results.sha256",
        primary_external="results/external/PRJNA450886/external_results.sha256",
        transfer_external="results/external/PRJNA922966/external_results.sha256",
        exploratory_external="results/external/PRJNA1090613/external_results.sha256",
        primary_motifs="results/external/PRJNA450886/motifs/transport/external_motif_transport.sha256",
        annotation="results/evidence/annotation/final_annotation.sha256",
        small_rna="results/evidence/small_rna/reference/small_rna_reference.sha256",
        published="results/evidence/published/published_evidence.sha256",
    output:
        figures="results/figures/figures.sha256",
        tables="results/tables/tables_supplements.sha256",
    threads: 1
    resources:
        mem_mb=4000
    shell:
        """
        python analysis/scripts/35_generate_figures_tables.py --root .
        sha256sum -c {output.figures}
        sha256sum -c {output.tables}
        """


rule write_manuscript:
    input:
        evidence=rules.finalize_evidence.output.manifest,
        figures=rules.generate_figures_tables.output.figures,
        tables=rules.generate_figures_tables.output.tables,
    output:
        md="docs/paper/discovery_validation_manuscript/manuscript.md",
        html="docs/paper/discovery_validation_manuscript/manuscript.html",
        pdf="docs/paper/discovery_validation_manuscript/manuscript.pdf",
        docx="docs/paper/discovery_validation_manuscript/manuscript.docx",
        metrics="docs/paper/discovery_validation_manuscript/manuscript_metrics.tsv",
        claims="docs/paper/discovery_validation_manuscript/claim_sentence_audit.tsv",
        sources_manifest="docs/paper/discovery_validation_manuscript/manuscript_sources.sha256",
        release_manifest="docs/paper/discovery_validation_manuscript/manuscript_release.sha256",
    threads: 1
    resources:
        mem_mb=2000
    shell:
        """
        python analysis/scripts/36_write_manuscript.py --root .
        mkdir -p /tmp/lychee_lo_pdf_profile /tmp/lychee_lo_docx_profile
        libreoffice -env:UserInstallation=file:///tmp/lychee_lo_pdf_profile \
          --headless --convert-to pdf --outdir docs/paper/discovery_validation_manuscript \
          {output.html}
        libreoffice -env:UserInstallation=file:///tmp/lychee_lo_docx_profile \
          --headless --infilter="HTML (StarWriter)" \
          --convert-to 'docx:Office Open XML Text' \
          --outdir docs/paper/discovery_validation_manuscript \
          {output.html}
        test -s {output.pdf}
        test -s {output.docx}
        sha256sum {output.md} {output.html} {output.pdf} {output.docx} \
          {output.metrics} {output.claims} {output.sources_manifest} > {output.release_manifest}
        sha256sum -c {output.release_manifest}
        """


rule release_audit:
    input:
        manuscript=rules.write_manuscript.output.release_manifest,
        evidence=rules.finalize_evidence.output.manifest,
        figures=rules.generate_figures_tables.output.figures,
        tables=rules.generate_figures_tables.output.tables,
    output:
        inventory="results/release/release_manifest.tsv",
        gates="results/release/submission_gate.tsv",
        language="results/release/claim_language_audit.tsv",
        reproduction="results/release/reproduction_report.md",
        summary="results/release/release_summary.md",
        bundle="results/release/release_bundle.sha256",
    threads: 1
    resources:
        mem_mb=1000
    shell:
        """
        python analysis/scripts/37_release_audit.py --root .
        sha256sum -c {output.bundle}
        """
