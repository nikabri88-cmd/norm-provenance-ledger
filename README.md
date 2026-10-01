# Norm Provenance Ledger

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23067248.svg)](https://doi.org/10.5281/zenodo.23067248)

Whose rule is an AI agent following? A pre-registered measurement of how LLM agents receive, keep, break, yield on, and invent behavioural norms, tested on customer-service dialogues with policy conflicts (τ²-bench) and on multi-agent software teams (MAST-Data).

Author: Julia Ryzhkova (Siriona, siriona.one), ORCID 0009-0005-4194-6059. Status: study complete, 30 September 2026. Archived on Zenodo: https://doi.org/10.5281/zenodo.23067248. Everything needed to check the results is in this repository; the source transcripts are downloaded from their public hosts and verified by SHA-256.

## What is measured

For every norm in an agent log the rubric records, block by block: where the norm was stated to the agent (operator, user, environment, or another agent), where the agent complied near to or far from the last reminder, where it violated the norm, where a customer pressured it to break the norm, and which rules the agent introduced on its own. An agent-authored rule is counted as *contradicted by the record* only when a specific block of the transcript positively contradicts it; absence of evidence is recorded separately as *unsupported*. An LLM judge only locates events; classification is done by scripts with windows fixed in advance.

## Main results (101 traces: 54 τ² dialogues, 47 MAST traces; two judges)

| | Judge 1 (GPT-5.6 Terra) | Judge 2 (GPT-5.6 Sol) | Consensus |
|---|---|---|---|
| Inter-judge agreement on compliance at distance (Spearman, n = 78) | | | 0.83 [0.75; 0.89] |
| Inter-judge agreement on record-contradicted agent rules (κ, 7 vs 7 cases) | | | 0.85 |
| H1: violations occur farther from the last reminder than compliance (median distance, blocks) | 20 vs 17, p = 2e-7 | 18 vs 13, p = 3e-15 | 27 vs 17, p = 1e-15 |
| H5: violations per agent turn after customer pressure vs dialogues without pressure | 0.50 vs 0.17, p = 0.003 | 0.65 vs 0.28, p = 0.005 | 0.24 vs 0.12, p = 0.066 |
| H2: record-contradicted rules more frequent in failed dialogues | p = 0.50 (3 cases) | p = 0.49 (3 cases) | not supported |

Eight of 101 traces contain an agent-stated rule that the transcript directly contradicts; in five of them both judges flagged the same block. Three patterns: customer-service agents inventing policy exceptions in the customer's favour, often right after pressure; agents in a multi-agent team resolving a conflict between requirements by declaring one of them void ("the GUI is not required"), against the written specification; and a technical claim contradicted by the documentation. The sample is stratified by task outcome and MAST labels, so counts describe this sample, not prevalence. H3, H4 and the overall count of agent-authored rules are reported descriptively; the overall count does not replicate across judges (Spearman 0.42). Full report: `results/final/results_report_v0.4.4.md`.

## Post-hoc robustness checks (v0.4.5)

After an external methodological review, six objections were tested on the same published judge outputs; these analyses are not pre-registered and are reported in `results/robustness/robustness_report_v0.4.5.md` (scripts in `scripts/robustness/`). In short: H1 holds with applied-only compliance, within traces, in the τ² corpus alone, after controlling for relative position in the dialogue, with norm-matched consensus, and on the 71 traces not seen before the final amendment; within the same norm it holds for one judge (40 of 58 norms) and is underpowered for the other. H5 holds on the 71 unseen traces and in a Poisson model adjusted for model, domain and dialogue length (rate ratio 2.1–2.5), stays in the same direction under norm-matched consensus with unstable significance, and remains an association. Block-level agreement is moderate (violations κ = 0.44, pressure κ = 0.55); trace-level agreement on record-contradicted rules is κ = 0.85 [0.49; 1.00].

Precise wording of the findings: (1) violations of recorded norms occur farther from the last reminder than their application – a decay mechanism is suggested, not established; (2) after observed customer pressure, violations per agent turn are about twice as frequent as in dialogues without observed pressure – an association; (3) in 8 of 101 traces agents state rules the transcript directly contradicts – an existence result that replicates across judges.

## Reproduce

```
pip install -r requirements.txt
python scripts/00_fetch_sources.py sources_root          # 6 τ² files + MAST-Data, SHA-256 verified
cp data/selection/B_index.json sources_root/
python scripts/01_build_inputs.py sources_root build     # judge inputs, byte-identical to the study
python scripts/02_segment.py build build/corpus          # numbered corpora, checked against pre-registered hashes
NPL_BUILD=build NPL_OUT=reproduced python scripts/05_normalize.py   # raw judge exports -> ledgers, checked against results/final
NPL_BUILD=build NPL_OUT=reproduced python scripts/04_analysis.py    # all pre-registered analyses
NPL_BUILD=build NPL_OUT=reproduced python scripts/robustness/h1_robust.py   # post-hoc checks (v0.4.5); likewise h1_within_norm.py, h5_robust.py, consensus_rel.py
```

Each step was run from scratch before release and reproduced the published files exactly: 112 judge inputs byte-identical, all three corpora matching the pre-registered SHA-256, ledgers and results identical to `results/final`. Re-running the judges themselves requires a Docent account (`scripts/03_docent_run.py`, notebooks in `notebooks/`); judge outputs are model samples and will not reproduce byte for byte, which is why the raw exports are published.

## Pre-registration

The plan, the pre-registration v0.4 and every amendment were written before the data they govern were coded and were posted with timestamps in the author's Telegram channel; SHA-256 of each frozen file is in `preregistration/SHA256SUMS.txt`. Order of events: corpus plan and selection (v0.4.0) → pre-registration v0.4 → technical pilot → amendment v0.4.1 (rubric fixes) → second pilot → v0.4.2 (second judge from the same provider) → pilot reliability → v0.4.3 (reliability sample and analysis rules) → reliability on 30 traces → v0.4.4 (double coding of the full set) → full coding. Pilot traces and pilot tasks are excluded from all confirmatory analyses. The rubric was calibrated earlier on SWE-bench Verified trajectories (`swebench_calibration/`), which are not part of the confirmatory study.

## Limitations

Both judges come from one provider (OpenAI); cross-provider reliability was pre-registered but not run, so all results carry this caveat. τ² trajectory files contain no tool definitions. H1 cannot separate norm decay from dialogue length. H5 is an association: dialogues with pressure differ in the request itself. FM-1.2 comparison is untestable (one positive MAST label in the sample, no role violations found). Record-contradicted rules are eight cases – a signal, not a rate.

## Contents

`preregistration/` plan, pre-registration, amendments, hashes · `rubric/` rubric v0.4.1 and output schema, full version history · `data/` source URLs and hashes, selection indexes, MAST labels · `scripts/` fetch, build, segment, judge launcher, validation, metrics, analysis · `results/` pilots, reliability, final ledgers, raw judge exports, reports · `notebooks/` the Colab notebooks used to run the judges · `swebench_calibration/` earlier calibration pilots.

## Licences and attribution

Code: MIT (`LICENSE`). Rubric, reports, annotations and judge outputs: CC BY 4.0 (`LICENSE-CONTENT`, https://creativecommons.org/licenses/by/4.0/). Path-by-path table: `LICENSES.md`. Source data are not redistributed: τ²-bench (Sierra Research, MIT; leaderboard trajectories from the public bucket sierra-tau-bench-public) and MAST-Data (Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", NeurIPS 2025, CC BY 4.0). Judge outputs quote short excerpts of those transcripts. Corpus retrieval and parts of the tooling were prepared with AI assistants (Claude, Anthropic; another assistant for corpus retrieval); judge models were used as instruments.
