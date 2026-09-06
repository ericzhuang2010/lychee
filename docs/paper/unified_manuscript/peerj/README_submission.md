# PeerJ submission package

Prepared September 6, 2026 for:

> Cultivar-dependent transcriptional responses of lychee to *Peronophythora litchii*: a registered genome-wide analysis

## Article-type decision

Choose **Research Article**.

This is an original bioinformatics research study: it poses a new biological question, applies inferential models to public RNA-sequencing cohorts, performs prespecified external evaluation, and reports new results and conclusions. It is not a Systematic Review/Meta-analysis, Method Paper, Data Report, or PeerJ Stage 1 Registered Report. A fuller comparison is in `submission_metadata.md`.

## Files to upload

Upload these 12 files:

1. `PeerJ_manuscript.docx` — manuscript; select the main-manuscript designation.
2. `figures/Figure_1.png` through `figures/Figure_6.png` — six separate main figures, in order.
3. `tables_odt/Table1.odt` through `tables_odt/Table4.odt` — four separate editable tables, in order. These are the alternate ODT upload set selected after the portal rejected DOCX in the attempted upload control.
4. `supplemental_information/PeerJ_supplemental_data_S1.zip` — select the Supplemental Data/Supplemental Information designation and publish with the article.

Do not upload `PeerJ-research-manuscript-template.docx`, `README_submission.md`, `submission_metadata.md`, `prepare_submission.py`, or `UPLOAD_FILE_MANIFEST_SHA256.tsv`; these are preparation aids. The `tables/Table_1.docx` through `Table_4.docx` files are retained as the preferred-format originals and fallback copies. Upload either the ODT set or the DOCX set, never both.

PeerJ currently says that no cover letter is needed, so none is included. The source `manuscript.pdf` is also not part of the upload package because PeerJ prefers an editable DOCX main manuscript and requests figures and tables as separate files.

## What was adapted for PeerJ

- The manuscript is built directly from `PeerJ-research-manuscript-template.docx`, preserving its US Letter page, 2.5-cm margins, 12-point Times body text, 1.15 line spacing, continuous line numbers, blank header/footer, and manually formatted heading conventions.
- The abstract is structured as Background, Methods, Results, and Conclusions and is below PeerJ's limits of 500 words and 3,000 characters.
- Keywords remain in `submission_metadata.md` for entry in the submission portal because the supplied manuscript template proceeds directly from the abstract to the Introduction.
- The section order is Introduction, Materials & Methods, Results, Discussion, and Conclusions.
- Main figures and editable main tables are separate upload files. Both preferred DOCX and alternative ODT table sets are generated; the upload manifest currently selects ODT. The manuscript cites the tables in ascending numerical order but does not contain figures, tables, or placement callouts. Figure titles and legends are supplied in `submission_metadata.md` for entry during upload.
- The supplement is a single compressed, machine-readable archive below the 30-MB individual-file limit. It contains all supplementary tables, supplementary figures, figure source data, analysis code, workflows, configurations, tests, and environment specifications.
- The Acknowledgements include the current PeerJ-required details for generative-AI-assisted language editing.

## Important PeerJ scope risk

PeerJ's current discipline-specific standard for bioinformatics studies based on previously published datasets requires both a new biological question or a substantively different conclusion and comprehensive, robust validation using at least two listed sources: independent public data, previously unreported clinical data, and/or new experimental data.

The manuscript clearly asks a new question and uses several independent public cohorts, as well as independent statistical and quantification checks. However, it contains no new wet-lab or clinical data. The policy wording may be interpreted as requiring two categories of validation rather than multiple independent public datasets. This creates a real editorial-screening risk even though the article type is still Research Article. The supplied confidential note to staff states the design accurately without claiming experimental validation.

## Final author checks

- [ ] Confirm that `NYU Langone Health, New York, NY, USA` is the complete affiliation; add a department or division if appropriate.
- [ ] Replace `CORRESPONDENCE_ADDRESS` in `prepare_submission.py` with the full street address and ZIP/postal code requested by the template, then rebuild. The current source files provide only the institutional affiliation, city, state, and country.
- [ ] Confirm the email `eric.zhuang@nyulangone.org` and ORCID `0009-0001-9050-0214`.
- [ ] Choose Research Article and the Bioinformatics and Genomics section.
- [ ] Select subject areas in this order where available: Plant Science, Genomics, Bioinformatics, Agricultural Science, Molecular Biology.
- [ ] Paste the structured abstract, keywords, declarations, data-availability text, and confidential scope note from `submission_metadata.md`.
- [ ] Verify every clause of the generative-AI disclosure, especially the model/version label and confirmation that the applicable terms of use were checked.
- [ ] Publish a new Zenodo version containing the exact `PeerJ_supplemental_data_S1.zip`, replace `10.5281/zenodo.22240717` with the new version-specific DOI in `prepare_submission.py` and `submission_metadata.md`, and rebuild the package. The current DOI was checked through the public Zenodo API on September 6, 2026: it resolves to a September 1 archive containing the supplementary tables, figures, and figure source data, but no analysis-code directory, and it is not byte-identical to the current PeerJ supplement.
- [ ] Review the CRediT roles and remove any that do not accurately describe the work.
- [ ] Confirm that no human, animal, or field permits were required.
- [ ] Add editors or reviewers only after checking subject fit and conflicts; do not invent names or contact details.
- [ ] Confirm that the manuscript is not under simultaneous consideration elsewhere.
- [ ] Inspect the submission system's generated PDF proof, especially symbols, italics, tables, line numbers, figure order, and hyperlinks.
- [ ] Review PeerJ's current payment route before submission. Publication requires either the applicable article processing charge, an eligible institutional plan, or the required individual lifetime membership arrangement after acceptance.

## Current official requirements used

- PeerJ author instructions: <https://peerj.com/about/author-instructions/>
- PeerJ policies and discipline-specific standards: <https://peerj.com/about/policies-and-procedures/#discipline-standards>
- PeerJ aims and scope: <https://peerj.com/about/aims-and-scope/>
- PeerJ pricing: <https://peerj.com/pricing/>
- PeerJ submission portal: <https://peerj.com/new/>
- OpenAI model documentation used to identify the Codex/GPT-5 product label: <https://developers.openai.com/api/docs/models/gpt-5-codex>

Requirements were checked on September 6, 2026. Recheck the live portal if its options differ from these instructions.

## Rebuilding and integrity checking

From this directory, run:

```bash
python3 prepare_submission.py
```

This rebuilds the manuscript from the PeerJ template, along with four DOCX source tables and four ODT upload alternatives, six figure files, the supplemental archive, and the SHA-256 upload manifest. ODT conversion uses the macOS `textutil` utility. `UPLOAD_FILE_MANIFEST_SHA256.tsv` lists exactly the files intended for upload.
