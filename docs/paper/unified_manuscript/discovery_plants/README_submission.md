# Discover Plants submission package

Prepared for the Springer Nature Snapp submission system from `../manuscript_v2.tex`.

## Recommended upload files (Word route)

1. `Discover_Plants_manuscript.docx` — **Manuscript**. This editable Word file contains the complete article, Figures 1–6, Tables 1–4, references, and declarations.
2. `Discover_Plants_cover_letter.docx` — **Cover letter**.
3. `supplementary_information/Discover_Plants_Supplementary_Information.docx` — **Supplementary Information 1**. It contains the supplement inventory and Figures S1–S3.
4. `supplementary_information/Discover_Plants_Data_and_Code.zip` — **Supplementary Data 2**. It contains Tables S1–S18, figure source data, the protocol, code, workflows, tests, metadata, and environments.

Do not upload both Word and LaTeX/PDF versions of the same item unless the portal explicitly asks. The matching PDFs and `Discover_Plants_LaTeX_source.zip` remain in this directory as visual previews and alternate source files.

## Portal selections

- Journal: Discover Plants
- Article type: Research
- Publishing model: Open access
- Suggested licence: CC BY 4.0 unless another licence is required

Copy title, abstract, keywords, author details, declarations, and scope terms from `submission_metadata.md`.

## Author checks before upload

- Confirm that the affiliation `NYU Langone Health, New York, New York, USA` is sufficiently complete. Add department/division and postal code if desired.
- Confirm the corresponding-author email `eric.zhuang@nyulangone.org` and ORCID `0009-0001-9050-0214`.
- Confirm that the manuscript is no longer under consideration at any other journal.
- Review the AI-use disclosure and revise it if it does not accurately describe the author's use.
- Inspect every DOCX in Microsoft Word or the submission portal's converted proof, especially figure labels, wide tables, mathematical symbols, and page breaks.
- Confirm the current APC waiver in the live portal. The published journal page says the waiver applies only if the article is accepted by 31 December 2026.
- Do not describe this submission as a Registered Report. It is a Research article containing a prospectively registered confirmatory analysis.

## Source-package notes

- The recommended manuscript and supplementary-information uploads are editable Word files. Both contain embedded high-resolution figures; no separate figure upload should be needed unless the portal requests one.
- The Word manuscript uses continuous line numbering (displayed every five lines), double-spaced body text, Word heading styles, editable Word tables, numbered references, and accessible figure descriptions.
- The package uses Springer Nature's official `sn-jnl.cls` version 3.1 (December 2024) in `pdflatex` mode.
- Snapp requires all LaTeX files and figures in one ZIP directory; the generated ZIP is flat.
- References are included directly in the TeX source to avoid bibliography-conversion failures.
- Main and supplementary materials cite the current Zenodo record: <https://zenodo.org/records/22436625>.
- The Zenodo record retains an earlier manuscript title. Before submission, either update its metadata to the current title or confirm that retaining the earlier title is acceptable; the DOI and archived contents are otherwise current and verified.
- `VALIDATION_REPORT.txt` records automated compilation and package checks.
- `UPLOAD_FILE_MANIFEST_SHA256.tsv` records exact checksums for the recommended Word-route upload files.
