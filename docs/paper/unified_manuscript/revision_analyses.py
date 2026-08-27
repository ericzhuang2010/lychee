#!/usr/bin/env python3
"""Light reviewer-response analyses computed from frozen result tables only.

Every input is a frozen, checksummed artifact. No model is refit here; the
script recomputes multiplicity adjustments, overlap statistics, and
concordance summaries that the reviewer requested, and prints the numbers
used in the revised manuscript text.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SUPP = ROOT / "results/supplement"
TABLES = ROOT / "results/tables"
LFC_MIN = math.log2(1.5)


def hr(title: str) -> None:
    print(f"\n=== {title} ===")


def bh(p: np.ndarray) -> np.ndarray:
    """Benjamini-Hochberg adjusted p-values."""
    n = len(p)
    order = np.argsort(p)
    ranked = p[order] * n / (np.arange(n) + 1)
    ranked = np.minimum.accumulate(ranked[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(ranked, 1.0)
    return out


def pearson_ci(r: float, n: int) -> tuple[float, float]:
    z = math.atanh(r)
    half = 1.959964 / math.sqrt(n - 3)
    return math.tanh(z - half), math.tanh(z + half)


s3 = pd.read_csv(SUPP / "S3_all_discovery_statistics.tsv", sep="\t")
s5 = pd.read_csv(SUPP / "S5_all_external_frozen_tests.tsv", sep="\t", low_memory=False)
t3 = pd.read_csv(TABLES / "Table3_internal_robustness.tsv", sep="\t")
t5 = pd.read_csv(TABLES / "Table5_orthogonal_final_status.tsv", sep="\t")
edger = pd.read_csv(ROOT / "results/robustness/genes/edgeR_all_genes.tsv", sep="\t")

hr("Discovery universe and threshold decomposition (minor comment 2)")
n_genes = len(s3)
q_pass = s3["interaction_q"] < 0.05
lfc_pass = s3["interaction_log2fc"].abs() >= LFC_MIN
both = q_pass & lfc_pass
print(f"expressed genes tested: {n_genes}")
print(f"q<0.05 alone: {q_pass.sum()}")
print(f"|log2FC|>=log2(1.5) alone: {lfc_pass.sum()}")
print(f"both (=262 expected): {both.sum()}")
assert n_genes == 19445 and both.sum() == 262

hr("BH recomputed over the QC-eligible universe (major comment 5)")
print("uniform_gene_qc_status values:", s3["uniform_gene_qc_status"].value_counts().to_dict())
eligible = s3[s3["uniform_gene_qc_status"] == "PASS"].copy()
print(f"QC-eligible genes: {len(eligible)} (removed {n_genes - len(eligible)})")
eligible["q_eligible"] = bh(eligible["interaction_p"].to_numpy())
redisc = eligible[(eligible["q_eligible"] < 0.05) & (eligible["interaction_log2fc"].abs() >= LFC_MIN)]
frozen206 = set(s3.loc[s3["primary_gene_status"] == "DISCOVERED", "gene_id"])
print(f"frozen 206 set size: {len(frozen206)}")
new_set = set(redisc["gene_id"])
print(f"QC-first rediscoveries (q<0.05 & effect): {len(new_set)}")
print(f"  in frozen 206: {len(new_set & frozen206)}")
print(f"  gained (new under QC-first BH): {len(new_set - frozen206)}")
print(f"  lost (frozen 206 not rediscovered): {len(frozen206 - new_set)}")

hr("edgeR vs DESeq2 concordance (major comment 4)")
m = s3.merge(edger, on="gene_id", how="inner")
print(f"merged genes: {len(m)} (edgeR table rows: {len(edger)}, genome-wide adjustment)")
pr_all = m["interaction_log2fc"].corr(m["edgeR_interaction_log2fc"])
sr_all = m["interaction_log2fc"].corr(m["edgeR_interaction_log2fc"], method="spearman")
print(f"all genes effect correlation: Pearson {pr_all:.3f}, Spearman {sr_all:.3f}")
cand = m[m["gene_id"].isin(frozen206)]
pr_c = cand["interaction_log2fc"].corr(cand["edgeR_interaction_log2fc"])
sign_agree = (np.sign(cand["interaction_log2fc"]) == np.sign(cand["edgeR_interaction_log2fc"])).mean()
print(f"206 candidates: effect Pearson {pr_c:.3f}, sign agreement {sign_agree:.1%}")
gate = cand[(cand["edgeR_q"] < 0.10) & (np.sign(cand["interaction_log2fc"]) == np.sign(cand["edgeR_interaction_log2fc"]))]
print(f"206 passing registered edgeR gate (genome-wide q<0.10 + sign agreement): {len(gate)}")
print(f"edgeR genome-wide q<0.05 among all genes: {(edger['edgeR_q'] < 0.05).sum()}")
print(f"edgeR genome-wide q<0.10 among all genes: {(edger['edgeR_q'] < 0.10).sum()}")
print(f"edgeR nominal p<0.05 among 206: {(cand['edgeR_p'] < 0.05).sum()}")

hr("Overlap of internally robust and externally supported sets (major comment 8)")
K, k, N = 16, 2, 206
expected = K * k / N
p_zero = math.comb(N - K, k) / math.comb(N, k)
print(f"expected overlap under independence: {expected:.3f}")
print(f"P(overlap = 0 | independence), hypergeometric: {p_zero:.3f}")

hr("Primary external contrast: continuous concordance (major comment 8, minor 3)")
prim = s5[(s5["evidence_type"] == "gene") & (s5["contrast"] == "primary_24h")].copy()
prim = prim[prim["gene_id"].isin(frozen206)]
print(f"primary_24h rows for frozen candidates: {len(prim)}")
meas = prim[prim["measurable"] == True]  # noqa: E712
print(f"measurable: {len(meas)}")
x = meas["discovery_interaction_log2fc"].astype(float)
y = meas["external_log2fc"].astype(float)
pr = x.corr(y)
sr = x.corr(y, method="spearman")
lo, hi = pearson_ci(pr, len(meas))
print(f"Pearson r = {pr:.3f} (95% CI {lo:.3f} to {hi:.3f}); Spearman rho = {sr:.3f}")
conc = (np.sign(x) == np.sign(y)).mean()
print(f"sign concordance: {conc:.1%} ({(np.sign(x) == np.sign(y)).sum()}/{len(meas)})")

hr("Supported and contradictory external genes (minor comment 4)")
status_cols = [c for c in prim.columns if "status" in c or "support" in c]
print("candidate status columns:", status_cols)
for col in status_cols:
    vals = prim[col].value_counts(dropna=False).to_dict()
    if 1 < len(vals) <= 8:
        print(f"  {col}: {vals}")

hr("Tier B external results for Table 3 (minor comment 5)")
print("final_tier values:", t5["final_tier"].value_counts(dropna=False).to_dict())
tierb = t5[t5["final_tier"].astype(str).str.contains("B", case=True, na=False)]["entity_id"].tolist()
print(f"Tier B genes: {len(tierb)}")
cols = ["gene_id", "external_log2fc", "confidence_lower", "confidence_upper",
        "external_q", "measurable", "direction_agrees", "confidence_excludes_zero",
        "threshold_pass"]
tb = prim[prim["gene_id"].isin(tierb)][cols].sort_values("gene_id")
print(tb.to_string(index=False))
