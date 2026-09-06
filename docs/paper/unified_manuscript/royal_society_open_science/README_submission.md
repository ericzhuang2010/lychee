# Royal Society Open Science submission package

Prepared 5 September 2026 for the submission of:

> Cultivar-dependent transcriptional responses of lychee to *Peronophythora litchii*: a registered genome-wide analysis

## Author-name decision

Keep Eric Zhuang's name, affiliation, email and ORCID in the manuscript. Royal Society science journals normally use **single-anonymized peer review**: authors are visible to reviewers, while reviewer identities are concealed. Royal Society Open Science is not one of the journals for which the title page must be anonymized.

## Files to upload

Upload these files in ScholarOne:

1. `RSOS_manuscript.docx` — main editable manuscript; use the manuscript/main-document designation.
2. `RSOS_cover_letter.docx` — cover letter.
3. `figures/Figure_1_study_design_and_QC.png` through `figures/Figure_6_orthogonal_evidence_and_tiers.png` — separate main figures. All are approximately 300 DPI and exceed 1,000 pixels in each dimension.
4. `supporting_information/RSOS_supporting_figures.pdf` — reviewer-friendly PDF containing Figures S1–S3.
5. `supporting_information/RSOS_supplementary_tables_and_source_data.zip` — complete supplementary archive containing Tables S1–S18, Figures S1–S3, figure source data, the supplement README and its internal manifest.
6. `supporting_information/RSOS_analysis_code.zip` — analysis source code, Snakemake workflows, configuration files, tests, metadata and environment specifications, with its own README and integrity manifest.

Do **not** upload `README_submission.md`, `submission_metadata.md`, `prepare_submission.py` or `UPLOAD_FILE_MANIFEST_SHA256.tsv`; these are preparation aids.

The supplementary-figure PDF and supplementary-data ZIP deliberately overlap for Figures S1–S3: the PDF is the readable figure file, while the ZIP is the complete data archive. The separate code ZIP fulfils the journal's requirement that analysis code be available to editors and reviewers at submission. Use the file descriptions supplied in `submission_metadata.md`.

## Current journal requirements used

- Initial submission is format-free, but a `.doc` or `.docx` file supports ScholarOne metadata prefill. After acceptance, the main manuscript must be editable.
- The title page includes full author names and affiliations for this journal.
- The abstract must be no more than 200 words and should not contain references or unexplained abbreviations. The supplied abstract is 186 words.
- The portal asks for one Royal Society Open Science discipline, up to six subject areas and three to six keywords.
- Tables must be editable. The Word manuscript contains editable tables.
- Initial figures may be embedded or separate. Final figures must be separate, at least 300 DPI, and supplied as PNG, EPS, TIFF or JPEG. The package uses separate 300-DPI PNG files.
- The submitting author must provide an ORCID in the portal.
- The portal collects a cover letter, funding, ethics, competing-interests, data-accessibility and CRediT-contribution statements.
- Data and code needed to support the paper must be available at submission and public on publication. “Available on request” is not accepted; the manuscript gives public accessions and a permanent Zenodo DOI, and the submission includes a code archive as electronic supplementary material.
- Royal Society Open Science requires transparent peer review if the article is accepted; anonymous review reports, decision letters and author responses are published with the article.
- The journal is gold open access under a CC BY licence.

## Cost

There is no submission fee. If the paper is accepted, the listed Royal Society Open Science article processing charge is **£1,400 / US$1,960 / €1,680**, with VAT potentially applicable. A qualifying Read & Publish agreement can cover the charge; Open Access Membership gives a 25% discount, and the journal offers discretionary waivers where funds are unavailable. Confirm eligibility with the NYU/NYU Langone library or research office and in the portal before arranging payment. If no funds are available, select the discretionary-waiver option during submission.

## Final checks before clicking Submit

- [ ] Confirm whether a department, institute or division should be added to `NYU Langone Health, New York, NY, USA`.
- [ ] Sign in as Eric Zhuang and select the exact institutional record offered by ScholarOne.
- [ ] Confirm the corresponding-author email `eric.zhuang@nyulangone.org` and ORCID `0009-0001-9050-0214`.
- [ ] Confirm the article type `Research Article` and choose the closest available discipline/subject terms.
- [ ] Paste the title, 186-word abstract, six keywords and all statements from `submission_metadata.md`.
- [ ] Review the CRediT roles and remove any role that does not accurately describe the work.
- [ ] Review the ethics statement and confirm that no new human, animal or field-sampling approval was required.
- [ ] Review the AI-use statement. It discloses the language-editing and journal-formatting assistance used to prepare this package, as required by current Royal Society policy.
- [ ] Confirm that the Zenodo DOI resolves publicly and that its archive is the version intended for peer review. It was successfully resolved during package preparation on 5 September 2026.
- [ ] Add preferred/non-preferred reviewers only after checking expertise, recent collaboration, institutional overlap and other conflicts. Do not invent reviewer details.
- [ ] Confirm that the manuscript is not under simultaneous consideration and approve the mandatory transparent-review and open-access declarations.
- [ ] Decide whether to request a waiver or seek institutional APC support.
- [ ] Inspect every page of ScholarOne's generated PDF proof, especially equations, tables, figure order, symbols and hyperlinks.

## Official links checked

- Journal: <https://royalsocietypublishing.org/journal/rsos>
- Submission information: <https://royalsocietypublishing.org/rsos/pages/submit>
- Royal Society author guidelines: <https://www.royalsociety.org/journals/authors/author-guidelines/>
- Open-access charges and waiver information: <https://www.royalsociety.org/journals/open-access/>
- Read & Publish eligibility: <https://www.royalsociety.org/journals/open-access/read-publish-agreements/>
- Data-sharing policy: <https://www.royalsociety.org/journals/ethics-policies/data-sharing-mining/>
- AI policy: <https://www.royalsociety.org/journals/ethics-policies/artificial-intelligence/>
- Editorial office: `openscience@royalsociety.org`

## Rebuilding and integrity checking

Run `python3 prepare_submission.py` from this directory to rebuild the Word files and payload copies. The script checks the abstract length and main-figure dimensions/DPI, then writes `UPLOAD_FILE_MANIFEST_SHA256.tsv`. To verify an individual file later, calculate its SHA-256 checksum and compare it with the manifest.
