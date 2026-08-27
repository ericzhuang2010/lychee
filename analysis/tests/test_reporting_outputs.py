#!/usr/bin/env python3
"""Production-shaped smoke test for figures, tables, manuscript, and exports."""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def write_tsv(root: Path, relative: str, fields: list[str], rows: list[dict[str, object]]) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def touch_text(root: Path, relative: str, text: str = "fixture\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def verify_manifest(root: Path, relative: str) -> None:
    import hashlib

    for raw in (root / relative).read_text().splitlines():
        expected, target = raw.split(None, 1)
        observed = hashlib.sha256((root / target.strip()).read_bytes()).hexdigest()
        assert observed == expected, target


def write_manifest(root: Path, relative: str, targets: list[str]) -> None:
    import hashlib

    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        for target in targets:
            digest = hashlib.sha256((root / target).read_bytes()).hexdigest()
            handle.write(f"{digest}  {target}\n")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lychee_reporting_test_") as temporary:
        root = Path(temporary)
        shutil.copytree(ROOT / "analysis/config", root / "analysis/config")
        (root / "analysis/preregistration").mkdir(parents=True)
        shutil.copyfile(
            ROOT / "analysis/preregistration/amendments.tsv",
            root / "analysis/preregistration/amendments.tsv",
        )
        write_tsv(root, "analysis/metadata/biological_unit_registry.tsv", ["study", "sample_id"], [
            {"study": "GSE201243", "sample_id": "s1"},
        ])
        write_tsv(root, "analysis/metadata/PRJNA830488_samples.tsv", ["sample_id", "cultivar", "treatment"], [
            {"sample_id": "s1", "cultivar": "Guiwei", "treatment": "mock"},
        ])
        write_tsv(root, "results/discovery/primary/pca_samples.tsv", ["sample_id", "cultivar", "treatment", "PC1", "PC2"], [
            {"sample_id": "s1", "cultivar": "Guiwei", "treatment": "mock", "PC1": 0, "PC2": 0},
        ])
        write_tsv(root, "results/audit/PRJNA830488_technical_qc.tsv", ["sample_id", "star_unique_percent", "technical_gate"], [
            {"sample_id": "s1", "star_unique_percent": 85, "technical_gate": "INCLUDE"},
        ])
        gene_fields = [
            "gene_id", "statistical_discovery", "primary_gene_status", "interaction_log2fc",
            "interaction_q", "uniform_gene_qc_status",
        ]
        write_tsv(root, "results/discovery/all_gene_discovery_status.tsv", gene_fields, [
            {"gene_id": "g1", "statistical_discovery": True, "primary_gene_status": "DISCOVERED", "interaction_log2fc": 1, "interaction_q": 0.01, "uniform_gene_qc_status": "PASS"},
            {"gene_id": "g2", "statistical_discovery": True, "primary_gene_status": "RETIRED_MAPPING_FAILURE", "interaction_log2fc": -1, "interaction_q": 0.02, "uniform_gene_qc_status": "FAIL"},
        ])
        write_tsv(root, "results/discovery/primary/within_cultivar_contrasts.tsv", ["gene_id", "contrast", "log2fc"], [
            {"gene_id": "g1", "contrast": "infection_in_Guiwei", "log2fc": 0.2},
            {"gene_id": "g1", "contrast": "infection_in_Yurong1", "log2fc": 1.2},
        ])
        write_tsv(root, "results/discovery/primary/normalized_counts.tsv", ["gene_id", "s1"], [
            {"gene_id": "g1", "s1": 100},
        ])
        write_tsv(root, "results/discovery/frozen_pathways.tsv", ["pathway", "NES", "padj"], [
            {"pathway": "P1", "NES": 2, "padj": 0.01},
        ])
        write_tsv(root, "results/discovery/dtu/all_dtu_results.tsv", ["gene_id", "gene_q", "maximum_absolute_delta_proportion"], [])
        write_tsv(root, "results/discovery/frozen_dtu.tsv", ["gene_id", "transcript_id"], [])
        write_tsv(root, "results/discovery/dtu/dtu_gate.tsv", ["gate", "status"], [
            {"gate": "genes_with_at_least_two_retained_isoforms", "status": "FAIL"},
        ])
        robustness_fields = [
            "gene_id", "primary_interaction_log2fc", "salmon_interaction_log2fc",
            "edgeR_interaction_log2fc", "internal_robustness_status",
            "loo_sign_agreement_count", "loo_q_below_threshold_count",
            "observed_mapping_sensitivity_status",
        ]
        write_tsv(root, "results/robustness/genes/frozen_gene_robustness.tsv", robustness_fields, [
            {"gene_id": "g1", "primary_interaction_log2fc": 1, "salmon_interaction_log2fc": 0.9, "edgeR_interaction_log2fc": 1.1, "internal_robustness_status": "PASS", "loo_sign_agreement_count": 12, "loo_q_below_threshold_count": 11, "observed_mapping_sensitivity_status": "PASS"},
        ])
        write_tsv(root, "results/robustness/pathways/frozen_pathway_robustness.tsv", ["pathway", "internal_pathway_robustness_status"], [
            {"pathway": "P1", "internal_pathway_robustness_status": "PASS"},
        ])

        external_gene_fields = [
            "study", "gene_id", "contrast", "external_q", "external_log2fc",
            "confidence_lower", "confidence_upper", "external_status",
        ]
        external_path_fields = [
            "study", "pathway", "discovery_NES", "fgsea_NES",
            "empirical_percentile", "external_pathway_status",
        ]
        signature_fields = ["study", "contrast", "estimate", "confidence_lower", "confidence_upper", "q"]
        for study in ("PRJNA450886", "PRJNA922966", "PRJNA1090613"):
            contrast = "primary_24h" if study == "PRJNA450886" else "primary"
            write_tsv(root, f"results/external/{study}/genes/frozen_gene_tests.tsv", external_gene_fields, [
                {"study": study, "gene_id": "g1", "contrast": contrast, "external_q": 0.01, "external_log2fc": 1, "confidence_lower": 0.5, "confidence_upper": 1.5, "external_status": "cross_context_supported"},
            ])
            write_tsv(root, f"results/external/{study}/genes/signature_contrasts.tsv", signature_fields, [
                {"study": study, "contrast": contrast, "estimate": 0.8, "confidence_lower": 0.2, "confidence_upper": 1.4, "q": 0.02},
            ])
            write_tsv(root, f"results/external/{study}/pathways/frozen_pathway_tests.tsv", external_path_fields, [
                {"study": study, "pathway": "P1", "discovery_NES": 2, "fgsea_NES": 1.5, "empirical_percentile": 0.98, "external_pathway_status": "cross_context_supported"},
            ])

        write_tsv(root, "results/evidence/annotation/final_candidate_annotations.tsv", ["gene_id", "annotation_status", "high_confidence_annotation"], [
            {"gene_id": "g1", "annotation_status": "HIGH_CONFIDENCE_COMPUTATIONAL_FUNCTION", "high_confidence_annotation": True},
        ])
        write_tsv(root, "results/evidence/small_rna/reference/small_rna_reference_gate.tsv", ["reference_gate_status"], [
            {"reference_gate_status": "NOT_TESTABLE_REFERENCE_ABSENT"},
        ])
        write_tsv(root, "results/evidence/motifs/results/robust_candidate_motifs.tsv", ["matrix_id", "discovery_motif_status"], [
            {"matrix_id": "M1", "discovery_motif_status": "ROBUST_CANDIDATE_MOTIF"},
        ])
        write_tsv(root, "results/evidence/motifs/results/ame_matched_background_replicates.tsv", ["matrix_id", "replicate", "q"], [
            {"matrix_id": "M1", "replicate": 1, "q": 0.01},
        ])
        write_tsv(root, "results/evidence/motifs/results/fimo_matched_background_sensitivity.tsv", ["matrix_id", "replicate", "q"], [
            {"matrix_id": "M1", "replicate": 1, "q": 0.01},
        ])
        write_tsv(root, "results/evidence/motifs/results/candidate_motif_site_presence.tsv", ["gene_id", "matrix_id", "site_present"], [
            {"gene_id": "g1", "matrix_id": "M1", "site_present": True},
        ])
        write_tsv(root, "results/external/PRJNA450886/motifs/transport/external_motif_transport.tsv", ["matrix_id", "external_motif_transport_status"], [
            {"matrix_id": "M1", "external_motif_transport_status": "cross_context_supported"},
        ])
        write_tsv(root, "results/external/PRJNA450886/motifs/transport/external_ame_replicates.tsv", ["matrix_id", "replicate", "q"], [
            {"matrix_id": "M1", "replicate": 1, "q": 0.01},
        ])
        write_tsv(root, "results/external/PRJNA450886/motifs/transport/external_fimo_sensitivity.tsv", ["matrix_id", "replicate", "q"], [
            {"matrix_id": "M1", "replicate": 1, "q": 0.01},
        ])
        write_tsv(root, "results/evidence/published_evidence_registry.tsv", ["DOI", "gene_or_pathway", "independent_of_current_datasets"], [
            {"DOI": "10.test/fixture", "gene_or_pathway": "P1", "independent_of_current_datasets": True},
        ])
        evidence_fields = [
            "entity_type", "entity_id", "discovery_status", "internal_robustness_status",
            "external_status", "orthogonal_class_count", "final_tier",
        ]
        write_tsv(root, "results/candidates/final_evidence_matrix.tsv", evidence_fields, [
            {"entity_type": "gene", "entity_id": "g1", "discovery_status": "DISCOVERED", "internal_robustness_status": "PASS", "external_status": "cross_context_supported", "orthogonal_class_count": 2, "final_tier": "Tier A"},
            {"entity_type": "pathway", "entity_id": "P1", "discovery_status": "FROZEN_PATHWAY", "internal_robustness_status": "PASS", "external_status": "cross_context_supported", "orthogonal_class_count": 0, "final_tier": "Exploratory"},
        ])
        write_tsv(root, "results/candidates/contradictory_results.tsv", ["entity_type", "entity_id", "reason"], [])
        touch_text(root, "results/audit/software_sessionInfo.txt")
        touch_text(root, "results/test_fixture_source.tsv")
        for relative in (
            "results/discovery/frozen_results.sha256",
            "results/robustness/internal_results.sha256",
            "results/external/PRJNA450886/external_results.sha256",
            "results/candidates/final_evidence_matrix.sha256",
        ):
            write_manifest(root, relative, ["results/test_fixture_source.tsv"])
        for relative in (
            "analysis/preregistration/protocol_bundle.sha256",
            "analysis/preregistration/external_validation_bundle.sha256",
            "analysis/preregistration/orthogonal_validation_bundle.sha256",
        ):
            write_manifest(root, relative, ["results/test_fixture_source.tsv"])
        touch_text(
            root, "results/discovery/external_outcomes_unlock_timestamp.txt",
            "2099-01-01T00:00:00-05:00\n",
        )

        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/35_generate_figures_tables.py"),
            "--root", str(root),
        ], check=True)
        verify_manifest(root, "results/figures/figures.sha256")
        verify_manifest(root, "results/tables/tables_supplements.sha256")
        assert (root / "results/figures/Figure6_OMITTED.txt").is_file()
        assert not (root / "results/figures/Figure6_conditional_dtu.svg").exists()
        assert len(list((root / "results/figures").glob("*.tiff"))) == 7
        assert len(list((root / "results/tables").glob("Table*.tsv"))) == 5
        assert len(list((root / "results/supplement").glob("S*.tsv"))) == 13

        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/36_write_manuscript.py"),
            "--root", str(root),
        ], check=True)
        manuscript_dir = root / "docs/paper/discovery_validation_manuscript"
        verify_manifest(root, "docs/paper/discovery_validation_manuscript/manuscript_sources.sha256")
        manuscript = (manuscript_dir / "manuscript.md").read_text()
        assert "with cross-context support" in manuscript.splitlines()[0]
        for relative in re.findall(r"\((\.\./\.\./\.\./results/figures/[^)]+)\)", manuscript):
            assert (manuscript_dir / relative).resolve().is_file(), relative

        libreoffice = shutil.which("libreoffice")
        if libreoffice:
            for extension in ("pdf", "docx"):
                profile = root / f"lo_{extension}_profile"
                command = [
                    libreoffice, f"-env:UserInstallation={profile.as_uri()}", "--headless",
                ]
                if extension == "docx":
                    command.extend([
                        "--infilter=HTML (StarWriter)",
                        "--convert-to", "docx:Office Open XML Text",
                    ])
                else:
                    command.extend(["--convert-to", extension])
                command.extend([
                    "--outdir", str(manuscript_dir),
                    str(manuscript_dir / "manuscript.html"),
                ])
                subprocess.run(command, check=True)
                assert (manuscript_dir / f"manuscript.{extension}").stat().st_size > 0

        write_manifest(root, "docs/paper/discovery_validation_manuscript/manuscript_release.sha256", [
            "docs/paper/discovery_validation_manuscript/manuscript.md",
            "docs/paper/discovery_validation_manuscript/manuscript.html",
            "docs/paper/discovery_validation_manuscript/manuscript.pdf",
            "docs/paper/discovery_validation_manuscript/manuscript.docx",
            "docs/paper/discovery_validation_manuscript/manuscript_metrics.tsv",
            "docs/paper/discovery_validation_manuscript/claim_sentence_audit.tsv",
            "docs/paper/discovery_validation_manuscript/manuscript_sources.sha256",
        ])
        subprocess.run([
            sys.executable, str(ROOT / "analysis/scripts/37_release_audit.py"),
            "--root", str(root),
        ], check=True)
        verify_manifest(root, "results/release/release_bundle.sha256")
        with (root / "results/release/submission_gate.tsv").open(newline="") as handle:
            gates = list(csv.DictReader(handle, delimiter="\t"))
        automated = [row for row in gates if row["responsibility"] == "automated"]
        pending = [row for row in gates if row["status"].startswith("PENDING")]
        assert all(row["status"] == "PASS" for row in automated), automated
        assert len(pending) == 6
        assert "Submission-ready: NO" in (root / "results/release/release_summary.md").read_text()
    print("reporting assets and manuscript synthetic test PASS")


if __name__ == "__main__":
    main()
