# AgriGenomics India 2026 submission package

This directory contains the material needed for the abstract-submission stage of Genome Editing and AgriGenomics India 2026.

## Files

- `agrigenomics_india_2026_abstract.docx` — upload-ready conference abstract.
- `agrigenomics_india_2026_abstract.txt` — plain-text version for copying into the online form.
- `submission_metadata.md` — recommended form selections, author metadata, optional statements, and missing personal fields.
- `prepare_submission.py` — reproducibly regenerates the Word abstract and validates its structure and word count.

## Submission checklist

- [ ] Submit by **15 September 2026** through <https://glostem.in/conference/agrigenomics-india-2026>.
- [ ] Select **Poster Presentation**, unless the portal offers **Oral preferred / Poster acceptable**.
- [ ] Select **Functional Genomics & CRISPR Interventions for Biotic Stress and Crop Quality Traits**.
- [ ] Do not describe this study as using CRISPR, genome editing, artificial intelligence, or machine learning.
- [ ] Enter the author-supplied position/designation, street address, ZIP/postal code, phone, and mobile number identified in `submission_metadata.md`.
- [ ] Paste the single-paragraph 180-word abstract and upload the `.docx` if both are requested.
- [ ] Confirm that the presenting author can attend in Chandigarh, India, on **8-9 October 2026**.
- [ ] If accepted, complete presenter registration. The published US overseas-academic price is **US$236 including 18% tax**.
- [ ] Retain the terms **cross-context support** and **external evaluation**; do not change them to unqualified “validation.”

## Scope and publication status

The abstract satisfies the organizer's stated 200-word limit and required Objective/Methodology/Key Results/Conclusion structure. It fits the functional-genomics and host-pathogen-interactomics portions of the program, although the conference is weighted toward genome editing and AI. A poster is therefore the most conservative presentation choice.

Acceptance would result in a conference presentation and an abstract-book entry, not publication of the full manuscript as a peer-reviewed paper. Continue the journal-submission process independently.

## Rebuild and validate

From the repository root, run:

```bash
python3 docs/paper/unified_manuscript/agrigenomics_india/prepare_submission.py
```

The script stops if the abstract exceeds 200 words, omits a required structural label, contains paragraph breaks, or lacks the expected author metadata.
