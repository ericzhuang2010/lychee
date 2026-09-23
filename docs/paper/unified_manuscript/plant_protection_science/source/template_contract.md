# Plant Protection Science template contract

This contract records the official 2026 CAAS templates used to create the Plant Protection Science submission documents. The retained templates remain unchanged under `source/templates/`.

## References

| Template | SHA-256 | Rendered pages | Intended output |
|---|---|---:|---|
| `Title_page_template_CAAS.docx` | `c1b99e632553710254a0df1df2ad312ce7be02f9b04ef1c734d71a112f1d688c` | 1 | title page |
| `Manuscript-file_template_CAAS.docx` | `ef8487774cbc138ef4199ffd9ce85ae01188f4c549fa4903147e794d5f490768` | 2 | blinded manuscript |
| `Acompanying-letter_template_CAAS.docx` | `ce87f6ec3f9e11b10f7a59c0a38600f5b187e910ed4a8dc936aad5cabb78f644` | 1 | initial cover letter using the CAAS letter visual system |
| `Authors_Declaration_2026.docx` | `9a99391298b3431351845750fb3191f7a7898213c1d55b610ace6bb2562b3200` | 1 | prefilled declaration requiring signature |

The reference renders and audit evidence were generated in `/tmp/pps_submission_work/`. Each template was visually inspected at full resolution.

## Page system

- All templates use one portrait A4 section, 21.0 × 29.7 cm, with 2.5 cm margins on every side.
- Each template has an unlinked header and footer. There is no special first-page or odd/even-page mode.
- The title, manuscript and letter templates use a CAAS logo in the header and a grey document label on the right. The manuscript footer contains a centred page number. The title and letter footers contain the CAAS web address.
- The declaration uses a floating CAAS logo and publisher address in the header and publisher contact information in the footer.

## Typography and paragraph system

- The title, manuscript and letter templates use Times New Roman 12 pt as the default body face. Main document titles use 14 pt bold. Template section titles are ordinary `Normal` paragraphs rather than Word heading styles.
- Manuscript body paragraphs are justified, 12 pt, and 1.5 spaced. Display labels and major headings are bold. Figure captions and table captions remain ordinary paragraphs.
- The declaration uses Arial 9–10 pt body text with a 14 pt bold centred title. Its compact spacing is required to retain the one-page form.
- All headings and body text remain black. Template instructional blue text is removed from final outputs.

## Tables and figures

- The title page contains a compact author-data table. Only one author row is needed; unused template rows may be removed.
- The manuscript includes editable Word tables. Header rows repeat and use a pale blue fill, black text and light grey borders. Narrative remains outside tables.
- Figures are inserted inline, centred, at no more than 6.0 inches wide. Captions follow the corresponding figures and remain attached where pagination permits.
- The official CAAS header logo, footer content and page geometry are preserve-only elements.

## Slot map

- Title page: manuscript type, title, author and affiliation, author-data table, corresponding-author line, prospective citation, abstract, character count, acknowledgement and AI disclosure, funding, conflict of interest, ethics, and data availability.
- Manuscript: manuscript type, title, abstract, keywords, Introduction, Material and Methods, Results, Discussion, Conclusion, editable tables, six main figures, captions and references. No author-identifying text is permitted.
- Cover letter: date, editor and journal, manuscript title, significance, novelty, journal fit, declarations and author sign-off. The official revision-letter instructional body is replaced because this is an initial submission.
- Declaration: manuscript title, author, journal, current AI-policy clause, corresponding-author name and e-mail. Date and handwritten signature remain blank.

## Content controls and package preservation

- The declaration contains six untagged content controls. The output fills visible field paragraphs while retaining the official header, footer and page system.
- The manuscript template contains a sample chart and sample table; these are editable examples and are removed. The official header logo and page-number footer are preserved.
- The title and letter template body placeholders are removed; the CAAS header/footer system is preserved.
- The final manuscript intentionally adds continuous line numbering in the left margin, as required by the journal instructions.

## Fidelity gates

- A4 geometry, 2.5 cm margins, header logo, right-side document labels and footer treatment must remain recognisably CAAS-derived.
- The blinded manuscript must have no author, affiliation, e-mail or author name in core properties.
- The manuscript must render with page and continuous line numbers; figures and tables must not clip or overlap.
- The declaration must remain legible on one page if possible; if the current AI-policy wording forces a second page, readability takes priority over compression.
- Every final DOCX must be rendered to PNG and inspected on every page after its latest edit.
