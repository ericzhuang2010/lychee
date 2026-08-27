#!/usr/bin/env python3
"""Build a transcriptome-plus-decoy gentrome for Salmon selective alignment."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def identifiers(path: Path) -> list[str]:
    result: list[str] = []
    with path.open() as handle:
        for line in handle:
            if line.startswith(">"):
                result.append(line[1:].split()[0])
    if not result or len(result) != len(set(result)):
        raise ValueError(f"{path}: missing or duplicate FASTA identifiers")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcripts", required=True)
    parser.add_argument("--genome", required=True)
    parser.add_argument("--gentrome", required=True)
    parser.add_argument("--decoys", required=True)
    args = parser.parse_args()

    transcripts = Path(args.transcripts)
    genome = Path(args.genome)
    gentrome = Path(args.gentrome)
    decoys = Path(args.decoys)
    gentrome.parent.mkdir(parents=True, exist_ok=True)
    decoys.parent.mkdir(parents=True, exist_ok=True)

    transcript_ids = identifiers(transcripts)
    genome_ids = identifiers(genome)
    overlap = sorted(set(transcript_ids) & set(genome_ids))
    if overlap:
        raise ValueError("Transcript/decoy identifiers overlap: " + ", ".join(overlap[:10]))

    with gentrome.open("wb") as writer:
        for path in (transcripts, genome):
            with path.open("rb") as reader:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
    decoys.write_text("\n".join(genome_ids) + "\n")


if __name__ == "__main__":
    main()
