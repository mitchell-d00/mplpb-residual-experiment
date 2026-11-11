# mplpb-residual-experiment
Reproducible protocol testing whether a self-describing ledger preserves enforceable revisability after recovery. Compares raw retrieval, versioned history, and ownership/status/refusal checks on retired pages, competing owners, hash mismatches, and self-application. Measures stop/refuse behavior without claiming truth.

This repository includes an executed exploratory pilot and the rewritten paper.
See [the paper folder](paper/) for [Markdown](paper/The_Residual_of_Logic.md),
[plain text](paper/The_Residual_of_Logic.txt), and [PDF](paper/The_Residual_of_Logic.pdf).
See `RESULTS.txt` and `results/pilot-1/summary.json` for the measured counts.

## Reproduce

Use Python 3.10+ and a clean checkout of Combined MPLPB pinned to
`257e54a51edac272eb6b2441457f38a40485ee4d`. No third-party dependencies are needed.

```sh
git clone https://github.com/mitchell-d00/Combined-MPLPB-A-closed-local-ledger-of-pages-that-answers-only-from-those-pages.git ../combined-mplpb
git -C ../combined-mplpb checkout 257e54a51edac272eb6b2441457f38a40485ee4d
python3 run.py --source ../combined-mplpb --out results/reproduction
python3 check.py results/reproduction
```

The output directory must be empty. Every read runs in a fresh subprocess;
fixture setup uses the pinned writer API. Labels and fixture hashes are saved
before any read. `commands.jsonl` retains commands, exit codes, stdout and stderr.
Generated activity-log times and absolute paths can differ across runs; compare
labels, fixture page seals and decisions after normalizing root paths, rather
than demanding byte-identical full logs. Source and script hashes are recorded.

## Conditions

- A: exact declared-scope lookup, first file order, no eligibility enforcement;
  the constructed answer consumer promotes retrieved prose to an answer.
- B: same available pages and history/status metadata, newest timestamp/ID
  selection, no enforced gate; same constructed promotion behavior.
- C: MPLPB provenance-gated `retrieve` and strict `mplpb_answers ask` interfaces.
- D: conventional reference gate in `baseline.py`, with independent HTML parsing,
  seal calculation, pinned graph checks, status/withdrawal checks, ambiguity stop,
  and a deliberately small affirmative color grammar. No MPLPB imports.

A and B are precisely specified ablations, not claims about all raw readers,
Git users, databases, or existing retrieval products. All arms receive the same
corpus bytes and questions. D shares the published seal serialization contract
and was developed with knowledge of these fixtures. It has not been independently
validated and covers neither all MPLPB policies nor general natural language.

The included `public-system` corpus is copied unmodified from Combined MPLPB's
MIT-licensed source; its license is retained in `UPSTREAM_LICENSE.txt`. Its page
origins and ownership are declarations, not authenticated authorship.
