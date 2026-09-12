# Plant-Environment Interactions submission package

Prepared from `../manuscript_v2.tex` and journal-specific condensed source files in `source/`. The original manuscript and other journal packages were not modified.

## Upload these files

1. `PEI_manuscript.docx` — **Main Document**. Editable text with title page, continuous line and page numbering, five embedded figures, two editable tables and complete legends.
2. `PEI_cover_letter.docx` — **Cover Letter**.
3. `figures/PEI_Figure_1.pdf` through `figures/PEI_Figure_5.pdf` — original-quality vector copies. Upload individually as **Figure 1** through **Figure 5** if the portal provides or requires separate figure-file slots; the figures also remain embedded in the Main Document for review.
4. `supporting_information/PEI_Supporting_Information.docx` — **Supporting Information**. Contains detailed methods/results, Tables S19–S20 and Figures S1–S4.
5. `supporting_information/PEI_Supporting_Data_and_Code.zip` — **Supporting Information/Data**. Contains machine-readable Tables S1–S18, all figure source data, protocol, code, workflows, tests, metadata and environments.

Do not upload the Markdown source files or validation files. Tables 1–2 are already editable in the manuscript. Supporting Figures S1–S4 are embedded in the supporting-information DOCX and do not need separate uploads unless the portal requests them.

## Portal selections

- Journal: Plant-Environment Interactions
- Article type: Research Article
- Special issue/collection: Regular submission; the relevant Plant-Biotic Interactions call closed on 30 June 2026.
- Research data used or generated: Yes
- Third-party copyrighted material: No
- Licence: CC BY (journal requirement)

Copy the abstract, keywords, plain-language significance statement, author information and declarations from `submission_metadata.md`.

## Automated guideline checks

- Abstract: 223 words (maximum 250)
- Main body (Introduction, Results and Discussion): 2950 words (maximum 3,000)
- Materials and Methods: 830 words (reported separately from the main-body limit)
- Conclusions: 85 words (reported separately from the main-body limit)
- Total narrative, Introduction through Conclusions: 3865 words
- Running title: 39 characters (must be under 40)
- References: 27 (journal optimum 30)
- Main illustrations: five figures plus two tables (maximum 10)
- Spacing: 1.5 lines in the manuscript
- Line numbering: continuous
- Page numbering: included
- Figures: embedded in the Main Document, with separate original-quality vector PDFs retained
- Tables: editable Word tables

## Author checks before upload

- Confirm whether `NYU Langone Health, New York, New York, USA` needs a department/division and postal code.
- Confirm `eric.zhuang@nyulangone.org` and ORCID `0009-0001-9050-0214`.
- Confirm the manuscript is not under consideration elsewhere.
- Review the AI-use acknowledgement and revise it if it does not accurately describe the author's use.
- Open the DOCX files in Microsoft Word and inspect all tables, page breaks, mathematical symbols and supporting figures.
- Inspect the portal-generated proof before approving submission.
- The Zenodo record retains an earlier manuscript title. Update its metadata if possible, or confirm that retaining that historical title is acceptable.
- The journal's current APC is USD 2,940 / GBP 2,180 / EUR 2,520 if accepted. Check Wiley institutional coverage or waiver eligibility before submission.

## Rebuild

Run `python3 prepare_submission.py` from this directory. The builder regenerates the DOCX files, copies the figure PDFs and data/code archive, and repeats all structural checks and checksums.
