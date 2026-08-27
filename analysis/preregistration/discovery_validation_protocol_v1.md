# Time-stamped prospective protocol for a retrospective lychee reanalysis

Protocol version: 1.0.0  
Frozen on: 2026-08-18 (America/New_York)  
Execution plan: `docs/lychee_revised_discovery_validation_plan.md`

## Scope and prior knowledge

This protocol is prospective with respect to the revised genome-wide discovery
analysis, but retrospective with respect to data collection and the prior
manuscript. Known before the freeze:

- the prior manuscript reported 17 Guiwei and 117 Yurong infection DEGs;
- 18 genes were selected post hoc for structural/promoter work;
- the old selected-gene effect contrast highlighted LITCHI019519,
  LITCHI001510, LITCHI028401, LITCHI017676, LITCHI028104, and LITCHI019183;
- WRKY and CDPK family papers used or interpreted the same cultivar system;
- PRJNA450886, GSE222650/651, and GSE262200 were known public datasets;
- the public GSE262200 page and sample names were viewed, but its expression
  matrix and biological outcomes were not opened during this revised execution;
- the existing viXra manuscript and reviewer reports were read.

The narrow novelty claim is that no located accession-linked publication has
reported a genome-wide, multiplicity-controlled cultivar-by-infection test in
GSE201243. The claim is not that lychee defense pathways, WRKY/CDPK biology, or
the cultivars are newly described.

## Locked discovery question

Discovery dataset: GSE201243 / PRJNA830488 only.

Primary estimand: the 24-hour infection effect in Yurong1 minus the 24-hour
infection effect in Guiwei, using gene-level counts and
`~ cultivar + treatment + cultivar:treatment` with Guiwei and mock as reference
levels. Positive effects mean a stronger induced response in Yurong1.

Primary gene filter: at least 10 counts in at least 3 libraries. Primary method:
DESeq2 Wald interaction test. The full-versus-reduced DESeq2 LRT is an omnibus
supporting test. Within-cultivar contrasts are interpretive, not selection tests.
Effects may be shrunken for display, never for primary significance testing.

Discovery requires BH q < 0.05, absolute interaction log2 fold change at least
log2(1.5), a uniquely interpretable gene model, and no severe mapping-bias flag.
The complete tested universe will be released.

## Locked pathway fallback

The primary collection is the Plant Reactome snapshot retrieved on 2026-08-18.
Lychee proteins will be mapped to rice pathway members only through one-to-one
reciprocal-best DIAMOND hits with E-value <= 1e-5 and at least 70% coverage in
both directions. Sets of 10--500 mapped lychee genes are eligible.
fgseaMultilevel on signed DESeq2 Wald statistics is primary. camera, roast,
leading-edge deletion, and 1,000 expression/size-matched random sets are
robustness analyses.

If no gene passes, the frozen gene signature is empty. The manuscript will
report the null and use only the locked pathway fallback; no raw-P or top-N gene
list will be created.

## Conditional transcript-usage analysis

DTU proceeds only if transcript/gene hierarchy is consistent, at least 1,000
expressed genes have at least two expressed isoforms, Salmon mapping rate is at
least 60% for every retained library, and no material transcript-mappability
failure is present. DRIMSeq plus stageR at OFDR < 0.05 is primary; DEXSeq is
sensitivity. Failing the gate produces an omitted DTU branch, not a replacement
analysis.

## Dataset roles and external tests

- PRJNA450886: primary cross-context evaluation. The locked primary external
  contrast is the 24-hour Guiwei-by-Heiye infection interaction; 6 and 48 hours
  and the three-way interaction are secondary. Heiye is resistant and Guiwei is
  susceptible in the source study, which reverses the resistant-comparator
  coding relative to discovery; all external signs will be standardized so
  positive means stronger response in the resistant comparator.
- GSE222651 / PRJNA922966: generic infection and tissue transfer in Feizixiao;
  never described as cultivar-interaction replication.
- GSE222650 / PRJNA922965: orthogonal small-RNA modality from the same cohort as
  GSE222651 and therefore not an independent study.
- GSE262200 / PRJNA1090613: exploratory only. Public metadata do not resolve
  sampling time, SFZ resistance phenotype, or biological-unit independence.
  Its outcomes cannot promote a discovery candidate.

External gene support requires the prespecified sign, BH q < 0.05 across the
frozen candidate-by-primary-contrast family, absolute log2 fold change at least
log2(1.5), and a 95% confidence interval excluding zero. Cross-context pathway
support requires the frozen set and direction, q < 0.05 in at least two
independent studies, q < 0.10 after removal of the largest leading-edge gene,
and a score above 95% of 1,000 matched random sets.

## Robustness and candidate status

Robustness thresholds and the deterministic headline rule are stored verbatim
in `analysis/config/discovery.yaml`. Alternative quantification or statistical
methods on the same samples are called robustness, not validation. A Tier A
headline candidate may be absent.

## Provenance limitation

GEO/SRA describe three deposited libraries per cell but do not identify source
trees, pooling, harvest units, or independent extractions for GSE201243. Unless
submitter clarification is archived, q values will be labeled model-based
evidence conditional on deposited-library independence; population-level
generalization is prohibited.

## Outcome firewall

External expression matrices, FASTQ-derived counts, and outcome summaries may
be opened only after all discovery files under `results/discovery/frozen_*` and
their SHA-256 manifest exist. Metadata, accessions, file sizes, and experimental
design were allowed before the freeze. Any correction after outcome access must
be entered in `analysis/preregistration/amendments.tsv` and labeled pre- or
post-outcome.

