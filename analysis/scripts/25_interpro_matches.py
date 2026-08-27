#!/usr/bin/env python3
"""Retrieve targeted precomputed InterPro/Pfam matches by candidate protein MD5."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from pathlib import Path


API = "https://www.ebi.ac.uk/interpro/matches/api/matches"
MAX_MD5_PER_REQUEST = 100


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def post_md5(md5_values: list[str], timeout: int) -> dict:
    body = json.dumps({"md5": md5_values}).encode()
    request = urllib.request.Request(
        API, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"InterPro Matches API returned HTTP {response.status}")
        return json.load(response)


def post_md5_batches(md5_values: list[str], timeout: int) -> dict:
    results: list[dict] = []
    for start in range(0, len(md5_values), MAX_MD5_PER_REQUEST):
        batch = md5_values[start:start + MAX_MD5_PER_REQUEST]
        payload = post_md5(batch, timeout)
        batch_results = payload.get("results")
        if not isinstance(batch_results, list):
            raise ValueError("InterPro response lacks results array")
        results.extend(batch_results)
    return {"results": results}


def union_coverage(intervals: list[tuple[int, int]], length: int) -> float:
    if not intervals or length <= 0:
        return 0.0
    merged: list[list[int]] = []
    for start, end in sorted(intervals):
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start + 1 for start, end in merged) / length


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--representatives", required=True, type=Path)
    parser.add_argument("--outdir", required=True, type=Path)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    representatives = read_tsv(args.representatives)
    required = {"gene_id", "canonical_transcript_id", "protein_length", "protein_md5"}
    if representatives and not required.issubset(representatives[0]):
        raise ValueError("representative table lacks required columns")
    if len({row["protein_md5"].lower() for row in representatives}) != len(representatives):
        raise ValueError("candidate representative proteins have duplicate MD5 values")

    args.outdir.mkdir(parents=True, exist_ok=True)
    raw_path = args.outdir / "interpro_matches_raw.json"
    match_path = args.outdir / "interpro_matches.tsv"
    summary_path = args.outdir / "interpro_candidate_summary.tsv"
    report_path = args.outdir / "interpro_summary.md"
    manifest_path = args.outdir / "interpro_results.sha256"

    payload = post_md5_batches(
        [row["protein_md5"].upper() for row in representatives], args.timeout
    )
    raw_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results = payload.get("results")
    if not isinstance(results, list):
        raise ValueError("InterPro response lacks results array")
    by_md5 = {str(item.get("md5", "")).lower(): item for item in results}
    expected = {row["protein_md5"].lower() for row in representatives}
    if set(by_md5) != expected:
        raise ValueError(f"InterPro response MD5 set differs: expected={expected}, observed={set(by_md5)}")

    match_fields = [
        "gene_id", "canonical_transcript_id", "protein_md5", "found", "source",
        "library", "library_version", "signature_accession", "signature_name",
        "signature_description", "signature_type", "interpro_accession", "interpro_name",
        "interpro_description", "interpro_type", "location_start", "location_end",
        "match_evalue", "location_evalue", "site_descriptions",
    ]
    match_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    for representative in representatives:
        md5 = representative["protein_md5"].lower()
        result = by_md5[md5]
        found = bool(result.get("found"))
        matches = result.get("matches") or []
        pfam: set[str] = set()
        interpro: set[str] = set()
        sources: set[str] = set()
        intervals: list[tuple[int, int]] = []
        for match in matches:
            signature = match.get("signature") or {}
            release = signature.get("signatureLibraryRelease") or {}
            entry = signature.get("entry") or {}
            source = str(match.get("source") or release.get("library") or "")
            sources.add(source)
            if source.lower() == "pfam":
                pfam.add(str(signature.get("accession", "")))
            if entry.get("accession"):
                interpro.add(str(entry["accession"]))
            locations = match.get("locations") or [{}]
            for location in locations:
                start = location.get("start")
                end = location.get("end")
                if isinstance(start, int) and isinstance(end, int):
                    intervals.append((start, end))
                sites = location.get("sites") or []
                match_rows.append({
                    "gene_id": representative["gene_id"],
                    "canonical_transcript_id": representative["canonical_transcript_id"],
                    "protein_md5": md5,
                    "found": found,
                    "source": source,
                    "library": release.get("library", ""),
                    "library_version": release.get("version", ""),
                    "signature_accession": signature.get("accession", ""),
                    "signature_name": signature.get("name", ""),
                    "signature_description": signature.get("description", ""),
                    "signature_type": signature.get("type", ""),
                    "interpro_accession": entry.get("accession", ""),
                    "interpro_name": entry.get("name", ""),
                    "interpro_description": entry.get("description", ""),
                    "interpro_type": entry.get("type", ""),
                    "location_start": start if start is not None else "",
                    "location_end": end if end is not None else "",
                    "match_evalue": match.get("evalue", ""),
                    "location_evalue": location.get("evalue", ""),
                    "site_descriptions": ";".join(
                        sorted({str(site.get("description", "")) for site in sites})
                    ),
                })
        status = (
            "PRECOMPUTED_MATCHES_FOUND" if found and matches
            else "NO_PRECOMPUTED_MATCH_SUBMIT_INTERPROSCAN"
        )
        candidate_rows.append({
            "gene_id": representative["gene_id"],
            "canonical_transcript_id": representative["canonical_transcript_id"],
            "protein_md5": md5,
            "protein_length": representative["protein_length"],
            "found": found,
            "match_count": len(matches),
            "sources": ";".join(sorted(sources)),
            "pfam_accessions": ";".join(sorted(pfam)),
            "interpro_accessions": ";".join(sorted(interpro)),
            "architecture_union_coverage": union_coverage(
                intervals, int(representative["protein_length"])
            ),
            "interpro_status": status,
        })

    write_tsv(match_path, match_fields, match_rows)
    candidate_fields = [
        "gene_id", "canonical_transcript_id", "protein_md5", "protein_length", "found",
        "match_count", "sources", "pfam_accessions", "interpro_accessions",
        "architecture_union_coverage", "interpro_status",
    ]
    write_tsv(summary_path, candidate_fields, candidate_rows)
    report_path.write_text(
        "\n".join([
            "# Targeted InterPro/Pfam match lookup",
            "",
            f"- Frozen candidate proteins: {len(representatives)}",
            f"- Proteins with precomputed matches: {sum(row['interpro_status'] == 'PRECOMPUTED_MATCHES_FOUND' for row in candidate_rows)}",
            f"- Proteins requiring targeted InterProScan: {sum(row['interpro_status'] == 'NO_PRECOMPUTED_MATCH_SUBMIT_INTERPROSCAN' for row in candidate_rows)}",
            "- A precomputed match is annotation evidence, not functional validation.",
            "",
        ]),
        encoding="utf-8",
    )
    with manifest_path.open("w") as handle:
        for path in (args.representatives, raw_path, match_path, summary_path, report_path):
            handle.write(f"{sha256(path)}  {path}\n")
    print(f"InterPro lookup: {len(representatives)} proteins, {len(match_rows)} location rows")


if __name__ == "__main__":
    main()
