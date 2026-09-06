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
4. `supporting_information/RSOS_supporting_information.zip` — the single supporting-information upload. It contains Figures S1–S3 in one PDF, twelve key result tables, the analysis-code archive, a README and an integrity manifest.

Do **not** upload `README_submission.md`, `submission_metadata.md`, `prepare_submission.py` or `UPLOAD_FILE_MANIFEST_SHA256.tsv`; these are preparation aids.

Only one file is retained in `supporting_information/`. The larger collection of all supplementary tables, individual supplementary figures, figure source data and analysis code is consolidated into one ZIP in `zenodo_deposit/`; that file is intended for Zenodo and is not a separate journal upload.

## Current journal requirements used

- Initial submission is format-free, but a `.doc` or `.docx` file supports ScholarOne metadata prefill. After acceptance, the main manuscript must be editable.
- The title page includes full author names and affiliations for this journal.
- The abstract must be no more than 200 words and should not contain references or unexplained abbreviations. The supplied abstract is 186 words.
- The portal asks for one Royal Society Open Science discipline, up to six subject areas and three to six keywords.
- Tables must be editable. The Word manuscript contains editable tables.
- Initial figures may be embedded or separate. Final figures must be separate, at least 300 DPI, and supplied as PNG, EPS, TIFF or JPEG. The package uses separate 300-DPI PNG files.
- The submitting author must provide an ORCID in the portal.
- The portal collects a cover letter, funding, ethics, competing-interests, data-accessibility and CRediT-contribution statements.
- Data and code needed to support the paper must be available at submission and public on publication. “Available on request” is not accepted; the manuscript gives public accessions and a permanent Zenodo DOI, and the single supporting-information ZIP includes the analysis code needed by editors and reviewers.
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
- [ ] The Zenodo DOI resolves publicly and already contains the comprehensive data/figure-source archive. Upload the single staged complete archive as a new Zenodo version before submission so the remote record also contains the analysis code; see `zenodo_deposit/README_ZENODO_UPLOAD.md`.
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

Run `python3 prepare_submission.py` from this directory to rebuild the Word files, the single concise supporting-information ZIP and the comprehensive Zenodo files. The script checks the abstract length and main-figure dimensions/DPI, then writes separate journal-upload and Zenodo checksum manifests.
