# Plant Direct submission package

Prepared on 5 September 2026 from `../manuscript.md` and `../manuscript.pdf`.

## Decision on author identification

Do **not** remove the author name. Plant Direct uses single-anonymous peer review for
Original Research Articles: reviewers are anonymous, but author identities are visible.
The journal's title-page checklist explicitly requests author names, affiliations, and
contact information. The Word manuscript therefore retains Eric Zhuang's name and
contact email.

The title page identifies the affiliation as **NYU Langone Health, New York, NY, USA**
and gives the institutional corresponding-author email and ORCID iD supplied by the
author.

## Upload set

Upload these files to the Plant Direct Research Exchange submission portal:

1. `Plant_Direct_manuscript.docx` as the manuscript text file.
2. `Plant_Direct_cover_letter.docx` as the cover letter.
3. The six PDFs in `figures/`, each as its corresponding figure number.
4. `supporting_information/Plant_Direct_supporting_figures.pdf` as supporting
   information.

The complete machine-readable tables and source data are already permanently archived
at <https://doi.org/10.5281/zenodo.22240717>. The local
`supporting_information/lychee_unified_manuscript_supplement.zip` is the exact archive
in that Zenodo record (matching MD5 `544c7bb34bb77db7837a37e2381e2186`). Upload the ZIP
only if the portal/editor requests the large machine-readable supplement in addition to
the DOI; it is about 18 MB and is not a replacement for the under-10-MB supporting-
figures PDF.

`UPLOAD_FILE_MANIFEST_SHA256.tsv` records byte sizes and SHA-256 checksums for every
potential upload file. `prepare_submission.py` reproducibly rebuilds the package and is
not an upload file.

## Required checks before submission

- [x] Affiliation set to **NYU Langone Health, New York, NY, USA**.
- [x] Corresponding-author email set to `eric.zhuang@nyulangone.org`.
- [x] ORCID iD set to `0009-0001-9050-0214`; its public record resolves to Eric Zhuang.
      Authenticate it in the submission portal when prompted.
- [ ] Add a department, division, laboratory, or hospital-campus name if NYU Langone or
      the journal requires a more specific affiliation.
- [ ] Confirm that the manuscript is not currently under consideration at another
      journal. The cover letter includes this standard declaration.
- [ ] Select **Original Research Article**, not Registered Report. The completed study
      contains a prospectively registered confirmatory stage, but it is not a Stage 1
      Registered Report submission.
- [ ] Copy the title, abstract, six keywords, declarations, and accession numbers from
      `submission_metadata.md` into the portal fields.
- [ ] Review the portal's generated submission PDF before final approval, especially the
      tables, scientific symbols, italics, and figure order.

## Current official pages

- Author guidelines: <https://onlinelibrary.wiley.com/page/journal/24754455/homepage/forauthors.html>
- Submission portal: <https://authors.wiley.com/journal/PLD3>
- Editorial office: `plantdirect@wiley.com`
- ORCID record: <https://orcid.org/0009-0001-9050-0214>

## Formatting changes made for Plant Direct

- Produced an editable `.docx` in Times New Roman, double spaced, with continuous line
  numbering and page numbers.
- Added a complete title page with author, affiliation, and contact email.
- Reduced the keyword list from seven to the journal's maximum of six.
- Added distinct Acknowledgments, Funding, Author Contributions, Conflict of Interest,
  Data and Code Availability, Accession Numbers, and Supplemental Data sections.
- Kept tables in the Word manuscript, moved all main-figure legends to a separate legend
  section, and supplied the six main figures as separate vector PDFs.
- Combined Figures S1-S3 with complete legends into one three-page PDF under 10 MB.
