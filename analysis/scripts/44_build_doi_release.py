#!/usr/bin/env python3
"""Build the curated, DOI-ready paper revision archive and checksum manifest."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import os
import tarfile
from datetime import date
from pathlib import Path


GIT_FILE_LIMIT = 100_000_000
ARCHIVE_ROOT = "lychee_paper_revision"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def selected_files(root: Path, integrated_docx: Path, integrated_pdf: Path | None) -> list[Path]:
    files: set[Path] = set()

    def include_tree(relative: str, allowed_suffixes: set[str] | None = None) -> None:
        directory = root / relative
        if not directory.is_dir():
            return
        for path in directory.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if allowed_suffixes is not None and path.suffix.lower() not in allowed_suffixes:
                continue
            files.add(path)

    include_tree("analysis/config")
    include_tree("analysis/metadata", {".tsv", ".md"})
    include_tree("analysis/preregistration")
    include_tree("analysis/workflow")
    include_tree("analysis/scripts", {".py", ".r", ".sh"})
    include_tree("analysis/tests", {".py", ".r", ".sh", ".tsv", ".yaml", ".yml", ".json"})
    include_tree("analysis/envs", {".yml", ".yaml", ".lock", ".r", ".md", ".sha256"})
    include_tree("results/tables", {".tsv", ".sha256"})
    include_tree("results/supplement", {".tsv", ".sha256"})
    include_tree("results/candidates", {".tsv", ".md", ".sha256"})
    include_tree("results/figures/source_data", {".tsv"})

    figure_dir = root / "results/figures"
    if figure_dir.is_dir():
        for path in figure_dir.iterdir():
            if path.is_file() and path.suffix.lower() in {".pdf", ".png", ".svg", ".sha256"}:
                files.add(path)

    unified = root / "docs/paper/unified_manuscript"
    for name in ("manuscript.md", "FIGURE_SOURCES.md", "build_figures.py", "h7_split_figures.py"):
        path = unified / name
        if path.is_file():
            files.add(path)
    include_tree("docs/paper/unified_manuscript/figures", {".pdf", ".png"})
    files = {path for path in files if path.stem != "figure5_dtu_orthogonal"}

    for relative in (
        "results/discovery/primary/legacy_18_audit.tsv",
        "results/evidence/motifs/inputs/promoter_metadata.tsv",
        "results/revision/H1_H2/H1_H2_R_sessionInfo.txt",
        "results/revision/H2_composite_null_summary.tsv",
        "results/revision/H5_controlled_motif/H5_manifest.sha256",
        "results/revision/H5_controlled_motif/foreground_recount_diagnostics.tsv",
        "results/revision/H3_power/simulation_design.tsv",
        "results/revision/H3_power/power_simulation_parameters.json",
        "results/revision/H3_power/H3_R_sessionInfo.txt",
        "README.md",
        "LICENSE",
        "docs/paper/revision_plan_heavy_machine.md",
        "docs/paper/revision_execution_report_2026-08-27.md",
        "docs/paper/heavy_revision_reproduction_commands.md",
        "docs/paper/review_commnets_for_unified_manuscript.md",
        "docs/paper/zenodo_release_checklist.md",
    ):
        path = root / relative
        if path.is_file():
            files.add(path)

    for manuscript_path in (integrated_docx, integrated_pdf):
        if manuscript_path is not None:
            manuscript_path = manuscript_path.resolve()
            if not manuscript_path.is_file():
                raise FileNotFoundError(manuscript_path)
            files.add(manuscript_path)

    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def manifest_bytes(root: Path, files: list[Path]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(["path", "bytes", "sha256"])
    for path in files:
        writer.writerow([path.relative_to(root).as_posix(), path.stat().st_size, sha256(path)])
    return output.getvalue().encode("utf-8")


def refresh_code_inventory(root: Path) -> Path:
    code_files: list[Path] = []
    for relative in ("analysis/scripts", "analysis/workflow", "analysis/envs", "analysis/config"):
        directory = root / relative
        if directory.is_dir():
            code_files.extend(path for path in directory.iterdir() if path.is_file())
    session = root / "results/audit/software_sessionInfo.txt"
    if session.is_file():
        code_files.append(session)
    destination = root / "results/supplement/S12_scripts_environments_commands.tsv"
    destination.parent.mkdir(parents=True, exist_ok=True)
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter="\t", lineterminator="\n")
    writer.writerow(["path", "sha256", "bytes"])
    for path in sorted(code_files):
        writer.writerow([path.relative_to(root).as_posix(), sha256(path), path.stat().st_size])
    destination.write_text(output.getvalue(), encoding="utf-8")
    return destination


def add_bytes(archive: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    info.mtime = 0
    archive.addfile(info, io.BytesIO(payload))


def add_file(archive: tarfile.TarFile, root: Path, path: Path) -> None:
    relative = path.relative_to(root).as_posix()
    info = archive.gettarinfo(str(path), arcname=f"{ARCHIVE_ROOT}/{relative}")
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    with path.open("rb") as handle:
        archive.addfile(info, handle)


def build_archive(root: Path, output: Path, files: list[Path], manifest: bytes) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    readme = (
        "Lychee paper revision reproducibility release\n\n"
        "This archive contains paper-facing protocol and amendment records, analysis code and "
        "configuration, environment specifications, frozen result tables, figure source data, "
        "generated figures, and the integrated manuscript. MANIFEST.tsv records the byte size "
        "and SHA-256 digest of every repository artifact. The archive does not contain raw "
        "sequencing reads, alignments, downloaded environments, or workflow caches.\n"
    ).encode("utf-8")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                add_bytes(archive, f"{ARCHIVE_ROOT}/RELEASE_README.txt", readme)
                add_bytes(archive, f"{ARCHIVE_ROOT}/MANIFEST.tsv", manifest)
                for path in files:
                    add_file(archive, root, path)
    os.replace(temporary, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--docx",
        type=Path,
        default=Path("docs/paper/lychee_plants_revised_vixra_format_integrated.docx"),
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("docs/paper/lychee_plants_revised_vixra_format_integrated.pdf"),
    )
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    root = args.root.resolve()
    docx = (root / args.docx).resolve() if not args.docx.is_absolute() else args.docx.resolve()
    pdf = (root / args.pdf).resolve() if not args.pdf.is_absolute() else args.pdf.resolve()
    refresh_code_inventory(root)
    files = selected_files(root, docx, pdf)
    manifest = manifest_bytes(root, files)
    release_dir = root / "results/release"
    manifest_path = release_dir / f"lychee_paper_revision_manifest_{args.date}.tsv"
    archive_path = release_dir / f"lychee_paper_revision_doi_bundle_{args.date}.tar.gz"
    release_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(manifest)
    build_archive(root, archive_path, files, manifest)

    archive_digest = sha256(archive_path)
    checksum_path = archive_path.with_suffix(archive_path.suffix + ".sha256")
    checksum_path.write_text(f"{archive_digest}  {archive_path.name}\n", encoding="utf-8")
    if archive_path.stat().st_size >= GIT_FILE_LIMIT:
        raise RuntimeError(
            f"Release archive is {archive_path.stat().st_size:,} bytes, exceeding the Git exposure limit"
        )

    print(f"files={len(files)}")
    print(f"archive={archive_path}")
    print(f"bytes={archive_path.stat().st_size}")
    print(f"sha256={archive_digest}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
