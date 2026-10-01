# Corrections log

## v0.4.6 (2026-10-01) – second external review round

No pre-registered (confirmatory) result changes. All corrections concern post-hoc analyses.

| Item | Before | After | File |
|---|---|---|---|
| Block-level pressure κ | 0.552, MAST blocks counted as joint negatives | 0.548, τ² dialogues only | scripts/robustness/consensus_rel.py |
| Norm-matched consensus | many-to-one (best J2 match per J1 event, reusable) | one-to-one maximum-weight matching within (block, kind, norm type) | scripts/robustness/consensus_rel.py |
| Consensus H1, threshold 0.2 | 467 compliance / 137 violation events | 459 / 135; medians and within-trace result unchanged | results/robustness/consensus_rel.json |
| Consensus H1, threshold 0.3 | medians 19 / 27 | 19 / 26; within-trace unchanged (27 of 35) | results/robustness/consensus_rel.json |
| Within-trace ties | exact comparison with zero | np.isclose; removes a floating-point artefact (J2 normalised check 43 of 54 → 43 of 53) | scripts/robustness/h1_robust.py, h1_within_norm.py |
| Post-hoc trace-level H1 in the v0.4.4 report | upper median: 38 of 48 (J1), 44 of 53 (J2) | standard median: 41 of 52, 44 of 55 | scripts/04_analysis.py, results/final/results_extra_v0.4.4.json |
| README wording | "underpowered" (J1 within-norm); "H5 holds on the 71 unseen traces" | "does not reach significance, only 15 non-tied norms"; "τ² subset of the 71 untouched traces (n = 39 and 38)" | README.md |

Checked and found already correct on main: `requirements.txt` includes pandas and statsmodels; `.zenodo.json` is valid strict JSON (line breaks occur between keys, not inside strings); the main H1 median in `04_analysis.py` was already the standard median.
