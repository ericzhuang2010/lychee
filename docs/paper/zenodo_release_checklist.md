# Zenodo release checklist for the revised lychee manuscript

The machine-generated draft release is:

- `results/release/lychee_paper_revision_doi_bundle_2026-08-27.tar.gz`
- `results/release/lychee_paper_revision_doi_bundle_2026-08-27.tar.gz.sha256`
- `results/release/lychee_paper_revision_manifest_2026-08-27.tsv`

The archive is intentionally limited to paper-facing reproducibility artifacts. It excludes raw
sequencing reads, alignments, downloaded software environments, caches, and workflow intermediates.
The large S10 TSV is stored only inside the compressed archive and remains excluded from Git.

## Author-authenticated steps

1. Sign in to Zenodo and create a new upload.
2. Reserve a DOI before publishing the record.
3. Send the reserved DOI back for insertion into the manuscript's **Data and code availability**
   section, or replace the pending-DOI sentence there directly.
4. Regenerate the integrated DOCX/PDF and DOI bundle so that the archived manuscript contains the
   reserved DOI. Recheck the bundle SHA-256 after regeneration.
5. Upload the final `.tar.gz`; use the manifest and `.sha256` sidecar to verify the local artifact.
6. Complete the Zenodo metadata. Suggested fields:
   - Resource type: Dataset (or Software, if the journal's convention favors workflow code)
   - Publication date: the actual release date
   - Version: `1.0.0-revision`
   - Creator: Eric Zhuang (confirm spelling, affiliation, and ORCID)
   - Related identifiers: PRJNA830488/GSE201243, PRJNA450886, PRJNA922966/GSE222651,
     PRJNA922965/GSE222650, and PRJNA1090613/GSE262200
   - License: choose only after confirming that it is compatible with every redistributed artifact
7. Preview the record, verify that the title matches the final manuscript, and publish it.
8. Open the public DOI URL in a logged-out browser and confirm that the archive downloads and its
   SHA-256 matches the sidecar.

## Submission decisions still requiring author confirmation

- Funding statement, conflict-of-interest statement, single-author contribution wording, and ORCID
- Final manuscript title and target journal
- License and embargo/publication timing for the Zenodo record

