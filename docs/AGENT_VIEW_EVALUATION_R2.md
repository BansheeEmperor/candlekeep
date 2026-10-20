# Agent-View Evaluation, Round 2

Round 2 of the protocol in [AGENT_VIEW_EVALUATION.md](AGENT_VIEW_EVALUATION.md) (the protocol). It runs the same research questions, layers, metrics, statistics and criteria (C-01 to C-15) on new code states. Round 1 failed RQ1 on C-14 and RQ2 on C-12 and C-14. The fixes that followed are the states compared here. Everything below is fixed before the first round-2 run. Anything not listed here is exactly as in the protocol, including the pre-run entries of its §16.

## 1. What round 1 found and what changed

| Round-1 finding | Change | Commit |
|---|---|---|
| C-14 failed closed: A's CI run aborted on MPS in 3 of 3 attempts | PyTorch's MPS backend crashes when two threads run a model at once. One first-come, first-served lock now covers every model call on MPS, with long calls sliced (diary Entry 62). | `408654f` |
| Informational CI: B's precise path lost 5.1 points of precision on the router benchmark | Stitching changed the text the cross-encoder scores. The reranker now scores each window's unstitched join (diary Entry 61). | `72c233f` |
| C-12 failed: C's output reached 1.97× B's (bound 1.5×) | The extra budget default is now 1,000, down from 2,500. | `f74b23f` |
| A third of C's `[…]` markers hid only whitespace | Passages separated only by whitespace no longer than the marker are joined. | `f74b23f` |
| The processor silently dropped frontmatter it could not parse | The quality gate parses frontmatter and checks every file of a directory ingest. 38 fixture documents were repaired, and the Centurion graded labels re-pointed (version 1.3) (diary Entry 60). | `244518e`, `f7c2964`, `494a30d` |
| A search during an ingest could fail on a record deleted mid-query | Such rows are skipped and such queries retried. | `ebc2900`, `4ab25c1` |

## 2. States

| State | Definition | Git ref | Checkout and venv | FastMCP |
|---|---|---|---|---|
| **A** | Project baseline, unchanged from round 1 | `development` @ `6519cc7` | `~/.cache/candlekeep-eval/worktrees/A`, `venvs/A` | 2.14.5 |
| **B′** | Round-1 B plus the fixes in §1 | `feat/large-collections-and-result-context`; `src/` = `8e5846f` | this repository, `.venv` | 3.4.9 |
| **C′** | B′ plus matched passages (budget 1,000, whitespace-joined gaps) | `feat/show-matched-passages-v2` @ `f74b23f` | `~/.cache/candlekeep-eval/worktrees/Cprime`, `venvs/Cprime` | 3.4.9 |

C′ is B′'s `8e5846f` plus three commits: the two round-1 C commits, cherry-picked (`ae8e22d`, `3dc7b7a`), and `f74b23f`. B′'s checkout may sit on a later commit that changes only documentation or the harness; V-02 checks that `git diff 8e5846f -- src/` is empty for every B′ output. The venvs of B′ and C′ have identical package lists.

## 3. Data

- **Fixtures** are those after the repair (`f7c2964`). The Centurion graded labels are version 1.3 (`494a30d`). The query sets are unchanged, so the §5 query counts hold.
- **Corpora** I01 to I09 are re-ingested from scratch with B′'s server, one MCP `ingest` call each, into new data under `~/.cache/candlekeep-eval/r2/`. Each corpus gets its own new Chroma process on ports 8221 to 8229. The ingest server uses port 8230, and Layer 2 servers 8231.
- **Expected document counts:** I01 to I07 are unchanged (89, 89, 90, 91, 89, 95, 88).
  - B′'s quality gate skips the 1 SciFact and 10 NFCorpus documents under 50 words, so BEIR-SF has 5,182 documents and BEIR-NF 3,623.
  - The SciFact document is no query's gold. The 10 NFCorpus documents appear in 46 qrels of 34 of the 323 test queries, and none of those queries loses all its gold.
  - The skipped documents are the same for every state.
- **Results** go to `tests/results/agent_view_eval_r2/`. Round 1's results and data are not read or written.
- **Selection:** the harness and the verifier select all of this from `scripts/eval_agent_view/rounds/r2.json` (`--round`), as well as R2-1's CI plugin and R2-4's informational runs (§4).

## 4. Amendments to the protocol for round 2

| ID | Section | Amendment | Reason |
|---|---|---|---|
| R2-1 | §10 C-14 | A's CI baseline runs the command with `-p mps_serial`, which serialises model calls. B′ and C′ run `pytest -m "unit or (benchmark and not slow)"` as written, on MPS. The rest of the rule is as in round 1: tests pass for B′ and C′, and `compare_benchmarks.py` shows no red flag (a drop of more than 1 point in precision or recall) for B′ or C′ against A's run. Each state gets one attempt. A run that aborts counts as failed. | A's code still crashes on MPS without the plugin; B′ and C′ have the lock. The plugin changes no result. |
| R2-2 | §5 / §11 | Expected BEIR document counts are 5,182 and 3,623 (§3). | The quality gate. |
| R2-3 | §8 | The informational re-judge of C-11's discordant queries, run after round 1, is pre-registered as a sensitivity analysis. Every query whose B′ and C′ J1 verdicts differ on `full` gets two new judges per item, with no part holding both states of one query. An item counts as full when at least 2 of its 3 verdicts say full, and b, c, McNemar and Holm are reported next to C-11. C-11 itself is decided on the J1 verdicts as registered. | Round 1 showed that C-11's superiority rested on single-judge verdicts. |
| R2-4 | §7.2 | One more informational Layer 2 row: B′ with `CANDLEKEEP_RESULT_CHARS=1700` on CEN, CEN-G and MH. It is a length-matched control for C′ (round-1 exploratory runs put C at budget 1,000 between B at 1,500 and B at 2,000). It decides nothing. | It shows whether C′'s visibility gain comes from choosing passages or from showing more text. |
| R2-5 | §8 | Judges read the plain-text renderings of their parts, and their outputs are extracted from the workflow journal, as in round 1 (`render_pack.py`, `judges_from_journal.py`). | As round 1's §16. |

## 5. Predictions (recorded before the run)

- **RQ1 passes.** B′'s rankings equal A's on every query of round 1's corpora (protocol §16, B′ entry), so C-01 to C-04 should show zero differences, C-05 should show no new leaks, and C-06 latency should match. C-14: B′'s tests pass and its router benchmark equals A's, so expect 0 red flags. The repaired fixtures change absolute values for all states alike.
- **RQ2:**
  - C-07, C-13 and C-15 pass.
  - C-12 passes: the largest exploratory ratio at budget 1,000 was 1.44.
  - C-08 shows a GPV gain over B′ smaller than round 1's.
  - C-09 stays at its ceiling.
  - C-10 passes.
  - C-11: C′'s net `full` gain over B′ is positive and smaller than round 1's +9.
  - C-14 as for RQ1.

## 14. Run registry (filled during execution)

Status values: `pending` · `running` · `done` · `verified` · `failed` · `void`.

| Run | State | Git SHA | Env | Layer | Suite | Command (abridged) | Output path | n | Status | Verified (V-ids) |
|---|---|---|---|---|---|---|---|---|---|---|
| R00-A | A | 6519cc7 | venv-A | env | — | `drive.py env --state A --round rounds/r2.json` | `tests/results/agent_view_eval_r2/env/A.txt` | — | done | |
| R00-B | B | 8e5846f | venv-B | env | — | `… --state B …` | `…/env/B.txt` | — | done | |
| R00-C | C | f74b23f | venv-Cprime | env | — | `… --state C …` | `…/env/C.txt` | — | done | |
| I01 | B | 8e5846f | venv-B | ingest | CEN | `drive.py ingest --corpus I01 --round rounds/r2.json` | `…/ingest/I01_*.json` | 89 docs | done | |
| I02 | B | 8e5846f | venv-B | ingest | CEN-G (overlap 50) | `drive.py ingest --corpus I02 --round rounds/r2.json` | `…/ingest/I02_*.json` | 89 docs | done | |
| I03 | B | 8e5846f | venv-B | ingest | CD-LEG | `drive.py ingest --corpus I03 --round rounds/r2.json` | `…/ingest/I03_*.json` | 90 docs | done | |
| I04 | B | 8e5846f | venv-B | ingest | CD-MED | `drive.py ingest --corpus I04 --round rounds/r2.json` | `…/ingest/I04_*.json` | 91 docs | done | |
| I05 | B | 8e5846f | venv-B | ingest | CD-NAR | `drive.py ingest --corpus I05 --round rounds/r2.json` | `…/ingest/I05_*.json` | 89 docs | done | |
| I06 | B | 8e5846f | venv-B | ingest | CD-API | `drive.py ingest --corpus I06 --round rounds/r2.json` | `…/ingest/I06_*.json` | 95 docs | done | |
| I07 | B | 8e5846f | venv-B | ingest | CD-ALT | `drive.py ingest --corpus I07 --round rounds/r2.json` | `…/ingest/I07_*.json` | 88 docs | done | |
| I08 | B | 8e5846f | venv-B | ingest | BEIR-SF | `drive.py ingest --corpus I08 --round rounds/r2.json` | `…/ingest/I08_*.json` | 5,182 docs | done | |
| I09 | B | 8e5846f | venv-B | ingest | BEIR-NF | `drive.py ingest --corpus I09 --round rounds/r2.json` | `…/ingest/I09_*.json` | 3,623 docs | done | |
| R01 | B | 8e5846f | venv-B | L1+L2 | CEN (determinism, run 2) | `drive.py all` (B rerun) | `…/L1/B_CEN_rerun.json`, `…/L2/B_CEN_rerun.json` | 108 | done | |
| L1-A-* | A | 6519cc7 | venv-A | L1 | CEN, CEN-G, MH, CD×5, BEIR×2 | `drive.py l1 --state A --suite <s> --round …` | `…/L1/A_<s>.json` | per §5 | done | |
| L1-B-* | B | 8e5846f | venv-B | L1 | ″ | `… --state B …` | `…/L1/B_<s>.json` | per §5 | done | |
| L1-C-* | C | f74b23f | venv-Cprime | L1 | ″ | `… --state C …` | `…/L1/C_<s>.json` | per §5 | done | |
| L2-A-* | A | 6519cc7 | venv-A | L2 | CEN, CEN-G, MH, CD×5, BEIR×2 | `drive.py l2 --state A --suite <s> --round …` | `…/L2/A_<s>.json` | per §5 | done | |
| L2-B-* | B | 8e5846f | venv-B | L2 | ″ | `… --state B …` | `…/L2/B_<s>.json` | per §5 | done | |
| L2-C-* | C | f74b23f | venv-Cprime | L2 | ″ | `… --state C …` | `…/L2/C_<s>.json` | per §5 | done | |
| L2-C0 | C (extras = 0) | f74b23f | venv-Cprime | L2 | CEN | `… --state C --extra-chars 0 …` | `…/L2/C_CEN_killswitch.json` | 108 | done | |
| L2-I1 | A (empty graph) | 6519cc7 | venv-A | L2 info | CEN, MH | `… --state A --graph-empty …` | `…/L2/info_A_emptygraph_<s>.json` | 108/30 | done | |
| L2-I2 | B (500 chars) | 8e5846f | venv-B | L2 info | CEN, MH | `… --state B --result-chars 500 …` | `…/L2/info_B_500_<s>.json` | 108/30 | done | |
| L2-I3 | B (1,700 chars) | 8e5846f | venv-B | L2 info | CEN, CEN-G, MH | `… --state B --result-chars 1700 …` | `…/L2/info_B_1700_<s>.json` | 108/108/30 | done | |
| J1 | A/B/C | — | — | L3 | CEN-A hybrid | `judge_pack.py build --pack J1 --round …` | `…/judges/pack_J1.json`, `keymap_J1.json` (SHA-256: `b93e2d6a8d2c409b85c0ffb1986fe5b52f7cef8c40b72d3968e6702c00af8725`), `out_J1_*.json` | 228 | pending | |
| J1-R | — | — | — | L3 | 20% re-judge | `judge_pack.py build --pack J1R --round …` | `…/judges/pack_J1R.json`, `keymap_J1R.json` (SHA-256: `2493f118148d3b5e52efec58bff3f0659d595ea38991141e6a439fedb95f38ab`), `out_J1R_*.json` | 46 | pending | |
| J2 (opt.) | B/C | — | — | L3 | CEN-A precise | `judge_pack.py build --pack J2 --round …` | `…/judges/pack_J2.json`, `keymap_J2.json` (SHA-256: `6d75632acefdc12c4c136af5a2ad3594ad565d82d58e22d268f82af6296df5e2`), `out_J2_*.json` | 152 | pending | |
| J1D | B/C | — | — | L3 info | C-11 discordant queries (R2-3) | `rejudge_discordant.py build/analyse --round …` | `…/judges/pack_J1D_part*.json`, `keymap_J1D.json` (SHA-256: `1d37e88f7d44b059dbfdd155ca6436438255555cf240531338b8322fbdc6bd8f`), `results_J1D.json` | 7 queries, 14 items | pending | |
| CI-A | A | 6519cc7 | venv-A | CI | — | `pytest -m "unit or (benchmark and not slow)" -p mps_serial` (MPS) | `…/verification/ci_A.txt` | — | done: 214 passed, 12 skipped (1 attempt) | |
| CI-B | B | 8e5846f | venv-B | CI | — | `pytest -m "unit or (benchmark and not slow)"` (MPS) | `…/verification/ci_B.txt` | — | done: 275 passed, 12 skipped (1 attempt); 0 red flags vs A | |
| CI-C | C | f74b23f | venv-Cprime | CI | — | ″ | `…/verification/ci_C.txt` | — | done: 307 passed, 12 skipped (1 attempt); 0 red flags vs A | |
| V-ALL | — | — | — | verify | all | `drive.py verify --all --check-doc --round …` | `…/verification/checks.json`, `…/summary.json` | — | pending | |

The key maps of J1, J1R and J2 are byte-identical to round 1's. They depend only on the seed, the 76 CEN-A queries and the states, so an item id names the same query and state in both rounds. The judges see only their own part.

## 15. Results (filled from `summary.json` after V-ALL passes)

### 15.1 Layer 1 — retrieval (values: A / B / C; Δ(B−A) with 95% CI)

| Suite | Path | MRR@5 | nDCG@5 | Hit@1 | Hit@5 | P@5 | Graded nDCG@5 | Adv. leak | Latency p50 (ms) | Ranking identical C=B | Source JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CEN | hybrid | 0.555 / 0.555 / 0.555; Δ +0.000 [+0.000, +0.000] | 0.569 / 0.569 / 0.569; Δ +0.000 [+0.000, +0.000] | 0.528 / 0.528 / 0.528; Δ +0.000 [+0.000, +0.000] | 0.602 / 0.602 / 0.602; Δ +0.000 [+0.000, +0.000] | 0.483 / 0.483 / 0.483; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 37.5 / 38.4 / 38.3; B/A 1.023 | 108/108 | `L1/{A,B,C}_CEN.json` |
| CEN | precise | 0.556 / 0.556 / 0.556; Δ +0.000 [+0.000, +0.000] | 0.562 / 0.562 / 0.562; Δ +0.000 [+0.000, +0.000] | 0.741 / 0.741 / 0.741; Δ +0.000 [+0.000, +0.000] | 0.769 / 0.769 / 0.769; Δ +0.000 [+0.000, +0.000] | 0.611 / 0.611 / 0.611; Δ +0.000 [+0.000, +0.000] | — | 9 / 9 / 9 (of 30) | 39.7 / 38.3 / 40.3; B/A 0.966 | 108/108 | ″ |
| CEN | explore | 0.554 / 0.554 / 0.554; Δ +0.000 [+0.000, +0.000] | 0.564 / 0.564 / 0.564; Δ +0.000 [+0.000, +0.000] | 0.528 / 0.528 / 0.528; Δ +0.000 [+0.000, +0.000] | 0.593 / 0.593 / 0.593; Δ +0.000 [+0.000, +0.000] | 0.529 / 0.529 / 0.529; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 23.7 / 24.2 / 23.8; B/A 1.021 | 108/108 | ″ |
| CEN-G | hybrid | — | — | — | — | — | 0.460 / 0.460 / 0.460; Δ +0.000 [+0.000, +0.000] | — | — | 108/108 | `L1/{A,B,C}_CEN-G.json` |
| CEN-G | precise | — | — | — | — | — | 0.379 / 0.379 / 0.379; Δ +0.000 [+0.000, +0.000] | — | — | 108/108 | ″ |
| CEN-G | explore | — | — | — | — | — | 0.384 / 0.384 / 0.384; Δ +0.000 [+0.000, +0.000] | — | — | 108/108 | ″ |
| MH | hybrid | SupportAll@5: 0.133 / 0.133 / 0.133; Δ +0.000 [+0.000, +0.000] | 0.494 / 0.494 / 0.494; Δ +0.000 [+0.000, +0.000] | 0.567 / 0.567 / 0.567; Δ +0.000 [+0.000, +0.000] | 0.867 / 0.867 / 0.867; Δ +0.000 [+0.000, +0.000] | 0.433 / 0.433 / 0.433; Δ +0.000 [+0.000, +0.000] | — | — | 60.9 / 60.6 / 59.8; B/A 0.995 | 30/30 | `L1/{A,B,C}_MH.json` |
| MH | precise | SupportAll@5: 0.100 / 0.100 / 0.100; Δ +0.000 [+0.000, +0.000] | 0.462 / 0.462 / 0.462; Δ +0.000 [+0.000, +0.000] | 0.533 / 0.533 / 0.533; Δ +0.000 [+0.000, +0.000] | 0.900 / 0.900 / 0.900; Δ +0.000 [+0.000, +0.000] | 0.521 / 0.521 / 0.521; Δ +0.000 [+0.000, +0.000] | — | — | 59.0 / 60.0 / 60.5; B/A 1.017 | 30/30 | ″ |
| MH | explore | SupportAll@5: 0.067 / 0.067 / 0.067; Δ +0.000 [+0.000, +0.000] | 0.449 / 0.449 / 0.449; Δ +0.000 [+0.000, +0.000] | 0.567 / 0.567 / 0.567; Δ +0.000 [+0.000, +0.000] | 0.833 / 0.833 / 0.833; Δ +0.000 [+0.000, +0.000] | 0.524 / 0.524 / 0.524; Δ +0.000 [+0.000, +0.000] | — | — | 35.5 / 35.6 / 36.2; B/A 1.002 | 30/30 | ″ |
| CD-LEG | hybrid | 0.678 / 0.678 / 0.678; Δ +0.000 [+0.000, +0.000] | 0.686 / 0.686 / 0.686; Δ +0.000 [+0.000, +0.000] | 0.664 / 0.664 / 0.664; Δ +0.000 [+0.000, +0.000] | 0.701 / 0.701 / 0.701; Δ +0.000 [+0.000, +0.000] | 0.536 / 0.536 / 0.536; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 33.5 / 34.1 / 34.2; B/A 1.017 | 107/107 | `L1/{A,B,C}_CD-LEG.json` |
| CD-LEG | precise | 0.687 / 0.687 / 0.687; Δ +0.000 [+0.000, +0.000] | 0.688 / 0.688 / 0.688; Δ +0.000 [+0.000, +0.000] | 0.953 / 0.953 / 0.953; Δ +0.000 [+0.000, +0.000] | 0.963 / 0.963 / 0.963; Δ +0.000 [+0.000, +0.000] | 0.553 / 0.553 / 0.553; Δ +0.000 [+0.000, +0.000] | — | 1 / 1 / 1 (of 30) | 35.6 / 35.9 / 36.7; B/A 1.008 | 107/107 | ″ |
| CD-LEG | explore | 0.671 / 0.671 / 0.671; Δ +0.000 [+0.000, +0.000] | 0.675 / 0.675 / 0.675; Δ +0.000 [+0.000, +0.000] | 0.664 / 0.664 / 0.664; Δ +0.000 [+0.000, +0.000] | 0.682 / 0.682 / 0.682; Δ +0.000 [+0.000, +0.000] | 0.662 / 0.662 / 0.662; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 20.8 / 20.8 / 21.0; B/A 1.001 | 107/107 | ″ |
| CD-MED | hybrid | 0.696 / 0.696 / 0.696; Δ +0.000 [+0.000, +0.000] | 0.699 / 0.699 / 0.699; Δ +0.000 [+0.000, +0.000] | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.704 / 0.704 / 0.704; Δ +0.000 [+0.000, +0.000] | 0.419 / 0.419 / 0.419; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 35.4 / 35.4 / 37.3; B/A 0.998 | 108/108 | `L1/{A,B,C}_CD-MED.json` |
| CD-MED | precise | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.695 / 0.695 / 0.695; Δ +0.000 [+0.000, +0.000] | 0.926 / 0.926 / 0.926; Δ +0.000 [+0.000, +0.000] | 0.972 / 0.972 / 0.972; Δ +0.000 [+0.000, +0.000] | 0.519 / 0.519 / 0.519; Δ +0.000 [+0.000, +0.000] | — | 2 / 2 / 2 (of 30) | 36.5 / 36.5 / 37.5; B/A 0.999 | 108/108 | ″ |
| CD-MED | explore | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.652 / 0.652 / 0.652; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 20.4 / 20.6 / 21.4; B/A 1.007 | 108/108 | ″ |
| CD-NAR | hybrid | 0.698 / 0.698 / 0.698; Δ +0.000 [+0.000, +0.000] | 0.703 / 0.703 / 0.703; Δ +0.000 [+0.000, +0.000] | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.713 / 0.713 / 0.713; Δ +0.000 [+0.000, +0.000] | 0.519 / 0.519 / 0.519; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 34.1 / 33.8 / 34.2; B/A 0.992 | 108/108 | `L1/{A,B,C}_CD-NAR.json` |
| CD-NAR | precise | 0.707 / 0.707 / 0.707; Δ +0.000 [+0.000, +0.000] | 0.710 / 0.710 / 0.710; Δ +0.000 [+0.000, +0.000] | 0.981 / 0.981 / 0.981; Δ +0.000 [+0.000, +0.000] | 0.991 / 0.991 / 0.991; Δ +0.000 [+0.000, +0.000] | 0.593 / 0.593 / 0.593; Δ +0.000 [+0.000, +0.000] | — | 0 / 0 / 0 (of 30) | 33.4 / 34.4 / 34.6; B/A 1.030 | 108/108 | ″ |
| CD-NAR | explore | 0.698 / 0.698 / 0.698; Δ +0.000 [+0.000, +0.000] | 0.703 / 0.703 / 0.703; Δ +0.000 [+0.000, +0.000] | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.713 / 0.713 / 0.713; Δ +0.000 [+0.000, +0.000] | 0.662 / 0.662 / 0.662; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 20.5 / 20.4 / 20.4; B/A 0.999 | 108/108 | ″ |
| CD-API | hybrid | 0.613 / 0.613 / 0.613; Δ +0.000 [+0.000, +0.000] | 0.622 / 0.622 / 0.622; Δ +0.000 [+0.000, +0.000] | 0.583 / 0.583 / 0.583; Δ +0.000 [+0.000, +0.000] | 0.648 / 0.648 / 0.648; Δ +0.000 [+0.000, +0.000] | 0.510 / 0.510 / 0.510; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 30.2 / 29.9 / 29.8; B/A 0.993 | 108/108 | `L1/{A,B,C}_CD-API.json` |
| CD-API | precise | 0.599 / 0.599 / 0.599; Δ +0.000 [+0.000, +0.000] | 0.609 / 0.609 / 0.609; Δ +0.000 [+0.000, +0.000] | 0.852 / 0.852 / 0.852; Δ +0.000 [+0.000, +0.000] | 0.907 / 0.907 / 0.907; Δ +0.000 [+0.000, +0.000] | 0.607 / 0.607 / 0.607; Δ +0.000 [+0.000, +0.000] | — | 0 / 0 / 0 (of 30) | 27.6 / 28.4 / 27.1; B/A 1.028 | 108/108 | ″ |
| CD-API | explore | 0.597 / 0.597 / 0.597; Δ +0.000 [+0.000, +0.000] | 0.601 / 0.601 / 0.601; Δ +0.000 [+0.000, +0.000] | 0.583 / 0.583 / 0.583; Δ +0.000 [+0.000, +0.000] | 0.611 / 0.611 / 0.611; Δ +0.000 [+0.000, +0.000] | 0.579 / 0.579 / 0.579; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 20.0 / 20.1 / 20.1; B/A 1.006 | 108/108 | ″ |
| CD-ALT | hybrid | 0.584 / 0.584 / 0.584; Δ +0.000 [+0.000, +0.000] | 0.595 / 0.595 / 0.595; Δ +0.000 [+0.000, +0.000] | 0.558 / 0.558 / 0.558; Δ +0.000 [+0.000, +0.000] | 0.625 / 0.625 / 0.625; Δ +0.000 [+0.000, +0.000] | 0.340 / 0.340 / 0.340; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 34.1 / 34.7 / 35.2; B/A 1.018 | 104/104 | `L1/{A,B,C}_CD-ALT.json` |
| CD-ALT | precise | 0.588 / 0.588 / 0.588; Δ +0.000 [+0.000, +0.000] | 0.598 / 0.598 / 0.598; Δ +0.000 [+0.000, +0.000] | 0.721 / 0.721 / 0.721; Δ +0.000 [+0.000, +0.000] | 0.788 / 0.788 / 0.788; Δ +0.000 [+0.000, +0.000] | 0.443 / 0.443 / 0.443; Δ +0.000 [+0.000, +0.000] | — | 13 / 13 / 13 (of 30) | 51.5 / 51.7 / 51.8; B/A 1.004 | 104/104 | ″ |
| CD-ALT | explore | 0.578 / 0.578 / 0.578; Δ +0.000 [+0.000, +0.000] | 0.589 / 0.589 / 0.589; Δ +0.000 [+0.000, +0.000] | 0.558 / 0.558 / 0.558; Δ +0.000 [+0.000, +0.000] | 0.615 / 0.615 / 0.615; Δ +0.000 [+0.000, +0.000] | 0.561 / 0.561 / 0.561; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 19.9 / 20.1 / 20.1; B/A 1.011 | 104/104 | ″ |
| CD pooled | hybrid | 0.654 / 0.654 / 0.654; Δ +0.000 [+0.000, +0.000] | 0.662 / 0.662 / 0.662; Δ +0.000 [+0.000, +0.000] | 0.637 / 0.637 / 0.637; Δ +0.000 [+0.000, +0.000] | 0.679 / 0.679 / 0.679; Δ +0.000 [+0.000, +0.000] | 0.465 / 0.465 / 0.465; Δ +0.000 [+0.000, +0.000] | — | 150 / 150 / 150 (of 150) | 33.4 / 33.7 / 33.9; B/A 1.007 | 535/535 | `L1/{A,B,C}_CD-*.json` |
| CD pooled | precise | 0.654 / 0.654 / 0.654; Δ +0.000 [+0.000, +0.000] | 0.660 / 0.660 / 0.660; Δ +0.000 [+0.000, +0.000] | 0.888 / 0.888 / 0.888; Δ +0.000 [+0.000, +0.000] | 0.925 / 0.925 / 0.925; Δ +0.000 [+0.000, +0.000] | 0.544 / 0.544 / 0.544; Δ +0.000 [+0.000, +0.000] | — | 16 / 16 / 16 (of 150) | 36.0 / 36.2 / 36.9; B/A 1.004 | 535/535 | ″ |
| CD pooled | explore | 0.648 / 0.648 / 0.648; Δ +0.000 [+0.000, +0.000] | 0.653 / 0.653 / 0.653; Δ +0.000 [+0.000, +0.000] | 0.637 / 0.637 / 0.637; Δ +0.000 [+0.000, +0.000] | 0.664 / 0.664 / 0.664; Δ +0.000 [+0.000, +0.000] | 0.624 / 0.624 / 0.624; Δ +0.000 [+0.000, +0.000] | — | 150 / 150 / 150 (of 150) | 20.3 / 20.4 / 20.5; B/A 1.008 | 535/535 | ″ |
| BEIR-SF | hybrid | nDCG@10: 0.597 / 0.597 / 0.597; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.729 / 0.729 / 0.729; Δ +0.000 [+0.000, +0.000] | 0.487 / 0.487 / 0.487; Δ +0.000 [+0.000, +0.000] | 0.650 / 0.650 / 0.650; Δ +0.000 [+0.000, +0.000] | 0.144 / 0.144 / 0.144; Δ +0.000 [+0.000, +0.000] | — | — | 112.1 / 111.2 / 111.7; B/A 0.992 | 300/300 | `L1/{A,B,C}_BEIR-SF.json` |
| BEIR-SF | precise | nDCG@10: 0.606 / 0.606 / 0.606; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.689 / 0.689 / 0.689; Δ +0.000 [+0.000, +0.000] | 0.520 / 0.520 / 0.520; Δ +0.000 [+0.000, +0.000] | 0.670 / 0.670 / 0.670; Δ +0.000 [+0.000, +0.000] | 0.151 / 0.151 / 0.151; Δ +0.000 [+0.000, +0.000] | — | — | 168.2 / 167.3 / 168.8; B/A 0.995 | 300/300 | ″ |
| BEIR-NF | hybrid | nDCG@10: 0.302 / 0.302 / 0.302; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.146 / 0.146 / 0.146; Δ +0.000 [+0.000, +0.000] | 0.430 / 0.430 / 0.430; Δ +0.000 [+0.000, +0.000] | 0.628 / 0.628 / 0.628; Δ +0.000 [+0.000, +0.000] | 0.314 / 0.314 / 0.314; Δ +0.000 [+0.000, +0.000] | — | — | 85.0 / 84.4 / 83.9; B/A 0.993 | 323/323 | `L1/{A,B,C}_BEIR-NF.json` |
| BEIR-NF | precise | nDCG@10: 0.289 / 0.289 / 0.289; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.130 / 0.130 / 0.130; Δ +0.000 [+0.000, +0.000] | 0.461 / 0.461 / 0.461; Δ +0.000 [+0.000, +0.000] | 0.594 / 0.594 / 0.594; Δ +0.000 [+0.000, +0.000] | 0.334 / 0.334 / 0.334; Δ +0.000 [+0.000, +0.000] | — | — | 126.0 / 125.6 / 127.3; B/A 0.997 | 323/323 | ″ |

### 15.2 Layer 2 — agent-visible (values: A / B / C; McNemar b, c, p for C vs B)

| Suite | Path | Primary visibility (GPV / SupportVisible / GoldText) | GPC | GoldShare | Chars/q mean (p95) | Adv. chars/q | Latency p50 | Multi-match freq. | Source JSON |
|---|---|---|---|---|---|---|---|---|---|
| CEN-G | hybrid | GPV 0.761 / 0.716 / 0.866 (n=67); b=0, c=10, p=0.0020 | 0.234 / 0.389 / 0.541; Δ(C−B) +0.152 [+0.100, +0.207] | 0.671 / 0.679 / 0.686 | 1969 (2828) / 2903 (4670) / 3661 (5457); C/B 1.261 | 2651 / 3796 / 4424; C/B 1.165, C−B +628 | 41.6 / 40.7 / 41.5; C−B +0.8 | 0.602 (233/387) | `L2/{A,B,C}_CEN-G.json` |
| CEN-G | precise | GPV 0.687 / 0.642 / 0.821 (n=67); b=0, c=12, p=0.0005 | 0.204 / 0.302 / 0.483; Δ(C−B) +0.181 [+0.127, +0.240] | 0.611 / 0.614 / 0.647 | 1231 (2826) / 1940 (4531) / 2587 (5495); C/B 1.334 | 625 / 1004 / 1254; C/B 1.248, C−B +249 | 42.0 / 41.7 / 43.2; C−B +1.5 | 0.726 (172/237) | ″ |
| CEN-G | explore | GPV 0.687 / 0.731 / 0.836 (n=67); b=0, c=7, p=0.0156 | 0.212 / 0.400 / 0.473; Δ(C−B) +0.073 [+0.034, +0.120] | 0.731 / 0.725 / 0.724 | 1899 (2809) / 2669 (3744) / 3096 (4168); C/B 1.160 | 2296 / 2999 / 3214; C/B 1.071, C−B +214 | 27.7 / 27.7 / 27.4; C−B -0.3 | 0.271 (101/373) | ″ |
| MH | hybrid | SupportVisible 0.067 / 0.100 / 0.100 (n=30); b=0, c=0, p=1.0000 | — | 0.437 / 0.471 / 0.512 | 2716 (2832) / 4199 (5239) / 5002 (6181); C/B 1.191 | — | 64.0 / 65.1 / 67.2; C−B +2.1 | 0.537 (79/147) | `L2/{A,B,C}_MH.json` |
| MH | precise | SupportVisible 0.033 / 0.067 / 0.067 (n=30); b=0, c=0, p=1.0000 | — | 0.521 / 0.525 / 0.554 | 2503 (2836) / 3867 (4889) / 4745 (5721); C/B 1.227 | — | 64.4 / 65.1 / 65.5; C−B +0.3 | 0.590 (79/134) | ″ |
| MH | explore | SupportVisible 0.033 / 0.067 / 0.067 (n=30); b=0, c=0, p=1.0000 | — | 0.531 / 0.547 / 0.568 | 2076 (2822) / 3146 (4337) / 3535 (4962); C/B 1.124 | — | 38.7 / 39.6 / 39.0; C−B -0.6 | 0.250 (28/112) | ″ |
| CEN | hybrid | GoldText 7.19 / 44.10 / 59.86; Δ(C−B) +15.76 [+13.41, +18.13] | — | 0.671 / 0.688 / 0.696 | 1963 (2825) / 2889 (4565) / 3673 (5449); C/B 1.271 | 2626 / 3739 / 4390; C/B 1.174, C−B +652 | 42.2 / 41.8 / 41.4; C−B -0.4 | 0.636 (245/385) | `L2/{A,B,C}_CEN.json` |
| CEN | precise | GoldText 5.87 / 33.87 / 49.68; Δ(C−B) +15.81 [+13.32, +18.24] | — | 0.608 / 0.619 / 0.651 | 1267 (2831) / 1907 (4546) / 2566 (5452); C/B 1.346 | 594 / 826 / 1061; C/B 1.284, C−B +235 | 42.7 / 43.3 / 43.6; C−B +0.3 | 0.738 (180/244) | ″ |
| CEN | explore | GoldText 9.68 / 51.50 / 63.68; Δ(C−B) +12.18 [+9.50, +14.96] | — | 0.732 / 0.733 / 0.733 | 1898 (2813) / 2726 (4068) / 3145 (4329); C/B 1.154 | 2151 / 2860 / 3140; C/B 1.098, C−B +280 | 27.8 / 27.9 / 28.1; C−B +0.1 | 0.293 (109/372) | ″ |
| CD-LEG | hybrid | GoldText 8.23 / 33.10 / 56.03; Δ(C−B) +22.92 [+20.91, +24.73] | — | 0.745 / 0.759 / 0.808 | 1462 (2866) / 2452 (5247) / 3345 (6152); C/B 1.364 | 2456 / 4078 / 4952; C/B 1.214, C−B +874 | 38.2 / 38.4 / 38.6; C−B +0.1 | 0.679 (186/274) | `L2/{A,B,C}_CD-LEG.json` |
| CD-LEG | precise | GoldText 7.81 / 29.90 / 51.83; Δ(C−B) +21.94 [+19.86, +23.87] | — | 0.392 / 0.398 / 0.504 | 1467 (2873) / 2465 (5126) / 3135 (5958); C/B 1.272 | 36 / 52 / 81; C/B 1.549, C−B +29 | 39.3 / 40.4 / 40.7; C−B +0.4 | 0.762 (208/273) | ″ |
| CD-LEG | explore | GoldText 13.38 / 49.17 / 72.87; Δ(C−B) +23.70 [+21.52, +25.68] | — | 0.920 / 0.919 / 0.917 | 1452 (2301) / 2354 (4116) / 3091 (4480); C/B 1.313 | 2093 / 3400 / 3949; C/B 1.161, C−B +549 | 24.8 / 25.0 / 24.9; C−B -0.1 | 0.493 (134/272) | ″ |
| CD-MED | hybrid | GoldText 8.05 / 29.46 / 52.65; Δ(C−B) +23.19 [+21.50, +24.73] | — | 0.582 / 0.604 / 0.699 | 1708 (2880) / 2604 (4682) / 3477 (5602); C/B 1.335 | 2608 / 3711 / 4465; C/B 1.203, C−B +754 | 39.5 / 39.1 / 39.6; C−B +0.5 | 0.603 (196/325) | `L2/{A,B,C}_CD-MED.json` |
| CD-MED | precise | GoldText 7.78 / 28.32 / 53.19; Δ(C−B) +24.87 [+23.32, +26.27] | — | 0.360 / 0.368 / 0.502 | 1509 (2888) / 2425 (4842) / 3125 (5780); C/B 1.289 | 73 / 123 / 183; C/B 1.484, C−B +60 | 40.7 / 40.5 / 40.3; C−B -0.2 | 0.731 (207/283) | ″ |
| CD-MED | explore | GoldText 11.87 / 45.03 / 68.04; Δ(C−B) +23.01 [+21.08, +24.85] | — | 0.904 / 0.909 / 0.916 | 1499 (2867) / 2201 (3897) / 2846 (4288); C/B 1.293 | 2377 / 3182 / 3413; C/B 1.073, C−B +231 | 24.4 / 24.4 / 24.3; C−B +0.0 | 0.451 (128/284) | ″ |
| CD-NAR | hybrid | GoldText 7.32 / 30.53 / 55.96; Δ(C−B) +25.44 [+23.96, +26.76] | — | 0.718 / 0.720 / 0.786 | 1563 (2864) / 2491 (4907) / 3365 (5714); C/B 1.351 | 2701 / 4026 / 4753; C/B 1.181, C−B +727 | 37.5 / 38.4 / 37.7; C−B -0.7 | 0.632 (187/296) | `L2/{A,B,C}_CD-NAR.json` |
| CD-NAR | precise | GoldText 6.96 / 29.47 / 53.09; Δ(C−B) +23.62 [+21.96, +25.05] | — | 0.442 / 0.455 / 0.575 | 1276 (2860) / 2076 (4862) / 2736 (5716); C/B 1.318 | 17 / 17 / 17; C/B 1.000, C−B +0 | 37.6 / 38.4 / 38.0; C−B -0.3 | 0.826 (199/241) | ″ |
| CD-NAR | explore | GoldText 10.56 / 42.28 / 66.73; Δ(C−B) +24.45 [+22.74, +26.05] | — | 0.917 / 0.917 / 0.927 | 1456 (2855) / 2213 (4178) / 2910 (4338); C/B 1.315 | 2358 / 3431 / 3762; C/B 1.097, C−B +331 | 24.0 / 24.4 / 24.2; C−B -0.2 | 0.453 (125/276) | ″ |
| CD-API | hybrid | GoldText 2.38 / 26.49 / 39.77; Δ(C−B) +13.28 [+11.44, +15.17] | — | 0.712 / 0.737 / 0.765 | 1317 (2812) / 1796 (3540) / 2617 (4238); C/B 1.457 | 2165 / 2567 / 3215; C/B 1.252, C−B +648 | 33.6 / 33.8 / 34.2; C−B +0.4 | 0.676 (177/262) | `L2/{A,B,C}_CD-API.json` |
| CD-API | precise | GoldText 2.23 / 25.82 / 40.01; Δ(C−B) +14.19 [+12.19, +16.10] | — | 0.459 / 0.497 / 0.587 | 1102 (2824) / 1629 (3814) / 2270 (4733); C/B 1.394 | 17 / 17 / 17; C/B 1.000, C−B +0 | 31.6 / 32.4 / 32.1; C−B -0.3 | 0.757 (162/214) | ″ |
| CD-API | explore | GoldText 4.51 / 26.46 / 34.38; Δ(C−B) +7.92 [+5.64, +10.33] | — | 0.803 / 0.811 / 0.813 | 1334 (2704) / 1568 (2745) / 1882 (2880); C/B 1.200 | 2039 / 2212 / 2353; C/B 1.064, C−B +141 | 23.9 / 23.8 / 23.8; C−B +0.0 | 0.441 (116/263) | ″ |
| CD-ALT | hybrid | GoldText 7.92 / 27.16 / 46.11; Δ(C−B) +18.95 [+16.50, +21.28] | — | 0.478 / 0.522 / 0.601 | 2072 (2849) / 2695 (4370) / 3465 (5226); C/B 1.286 | 2817 / 3641 / 4069; C/B 1.117, C−B +427 | 39.4 / 39.6 / 39.2; C−B -0.4 | 0.508 (194/382) | `L2/{A,B,C}_CD-ALT.json` |
| CD-ALT | precise | GoldText 8.84 / 29.47 / 48.00; Δ(C−B) +18.53 [+16.04, +20.84] | — | 0.404 / 0.446 / 0.536 | 1757 (2856) / 2302 (4369) / 2980 (5273); C/B 1.295 | 819 / 1089 / 1334; C/B 1.226, C−B +246 | 54.6 / 56.4 / 55.4; C−B -1.0 | 0.687 (222/323) | ″ |
| CD-ALT | explore | GoldText 15.22 / 40.74 / 50.91; Δ(C−B) +10.16 [+7.55, +12.85] | — | 0.789 / 0.784 / 0.786 | 2080 (2840) / 2514 (3929) / 2789 (4009); C/B 1.110 | 2466 / 3090 / 3208; C/B 1.038, C−B +118 | 23.7 / 23.7 / 24.1; C−B +0.4 | 0.252 (97/385) | ″ |
| CD pooled | hybrid | GoldText 6.77 / 29.36 / 50.13; Δ(C−B) +20.77 [+19.83, +21.70] | — | 0.648 / 0.670 / 0.733 | 1621 (2865) / 2405 (4820) / 3252 (5641); C/B 1.352 | 2549 / 3604 / 4291; C/B 1.190, C−B +686 | 37.3 / 37.8 / 37.7; C−B -0.1 | 0.611 (940/1539) | `L2/{A,B,C}_CD-*.json` |
| CD pooled | precise | GoldText 6.70 / 28.58 / 49.23; Δ(C−B) +20.65 [+19.72, +21.58] | — | 0.412 / 0.432 / 0.541 | 1420 (2873) / 2178 (4851) / 2848 (5744); C/B 1.308 | 192 / 260 / 326; C/B 1.257, C−B +67 | 40.4 / 40.2 / 40.4; C−B +0.1 | 0.748 (998/1334) | ″ |
| CD pooled | explore | GoldText 11.06 / 40.71 / 58.63; Δ(C−B) +17.91 [+16.71, +19.13] | — | 0.867 / 0.869 / 0.873 | 1561 (2839) / 2167 (3943) / 2702 (4249); C/B 1.247 | 2267 / 3063 / 3337; C/B 1.090, C−B +274 | 24.2 / 24.3 / 24.2; C−B +0.0 | 0.405 (600/1480) | ″ |
| BEIR-SF | hybrid | GoldText 7.53 / 18.58 / 28.58; Δ(C−B) +10.00 [+8.67, +11.41] | — | 0.111 / 0.112 / 0.144 | 4489 (5517) / 7119 (9713) / 7805 (10341); C/B 1.096 | — | 118.4 / 116.4 / 116.7; C−B +0.2 | 0.673 (1644/2444) | `L2/{A,B,C}_BEIR-SF.json` |
| BEIR-SF | precise | GoldText 7.39 / 17.96 / 27.90; Δ(C−B) +9.94 [+8.58, +11.33] | — | 0.084 / 0.080 / 0.104 | 5352 (5527) / 8857 (10128) / 9548 (10949); C/B 1.078 | — | 175.3 / 172.3 / 177.1; C−B +4.8 | 0.730 (2124/2909) | ″ |
| BEIR-NF | hybrid | GoldText 20.34 / 48.41 / 57.77; Δ(C−B) +9.36 [+8.03, +10.72] | — | 0.284 / 0.285 / 0.299 | 4159 (5519) / 6496 (9612) / 7186 (10264); C/B 1.106 | — | 89.2 / 89.1 / 88.8; C−B -0.2 | 0.703 (1716/2440) | `L2/{A,B,C}_BEIR-NF.json` |
| BEIR-NF | precise | GoldText 19.40 / 47.78 / 57.21; Δ(C−B) +9.43 [+8.06, +10.85] | — | 0.342 / 0.341 / 0.350 | 3788 (5529) / 6216 (10085) / 6799 (10803); C/B 1.094 | — | 130.5 / 130.3 / 130.2; C−B -0.1 | 0.777 (1720/2215) | ″ |
| Informational | A empty graph, CEN, hybrid | GoldText 7.19 (A: 7.19); Δ vs A +0.00 [+0.00, +0.00] | — | 0.671 | 1963 (2825) | 2626 | 42.6 | — | `L2/info_*.json` |
| Informational | A empty graph, CEN, precise | GoldText 5.87 (A: 5.87); Δ vs A +0.00 [+0.00, +0.00] | — | 0.608 | 1267 (2831) | 594 | 42.2 | — | ″ |
| Informational | A empty graph, CEN, explore | GoldText 9.68 (A: 9.68); Δ vs A +0.00 [+0.00, +0.00] | — | 0.732 | 1898 (2813) | 2151 | 28.1 | — | ″ |
| Informational | A empty graph, MH, hybrid | SupportVisible 0.067 (A: 0.067); vs A: b=0, c=0, p=1.0000 | — | 0.437 | 2716 (2832) | — | 64.2 | — | ″ |
| Informational | A empty graph, MH, precise | SupportVisible 0.033 (A: 0.033); vs A: b=0, c=0, p=1.0000 | — | 0.521 | 2503 (2836) | — | 63.7 | — | ″ |
| Informational | A empty graph, MH, explore | SupportVisible 0.033 (A: 0.033); vs A: b=0, c=0, p=1.0000 | — | 0.531 | 2076 (2822) | — | 37.9 | — | ″ |
| Informational | B at 500 chars, CEN, hybrid | GoldText 18.47 (A: 7.19, B: 44.10); Δ vs A +11.28 [+9.24, +13.45] | — | 0.677 | 1834 (2821) | 2444 | 42.9 | — | ″ |
| Informational | B at 500 chars, CEN, precise | GoldText 14.10 (A: 5.87, B: 33.87); Δ vs A +8.23 [+6.60, +9.97] | — | 0.611 | 1194 (2805) | 556 | 42.4 | — | ″ |
| Informational | B at 500 chars, CEN, explore | GoldText 23.14 (A: 9.68, B: 51.50); Δ vs A +13.46 [+11.22, +15.73] | — | 0.733 | 1772 (2629) | 1984 | 28.0 | — | ″ |
| Informational | B at 500 chars, MH, hybrid | SupportVisible 0.100 (A: 0.067, B: 0.100); vs A: b=0, c=1, p=1.0000 | — | 0.451 | 2589 (2819) | — | 63.8 | — | ″ |
| Informational | B at 500 chars, MH, precise | SupportVisible 0.067 (A: 0.033, B: 0.067); vs A: b=0, c=1, p=1.0000 | — | 0.523 | 2409 (2826) | — | 64.8 | — | ″ |
| Informational | B at 500 chars, MH, explore | SupportVisible 0.067 (A: 0.033, B: 0.067); vs A: b=0, c=1, p=1.0000 | — | 0.539 | 1991 (2822) | — | 38.1 | — | ″ |
| Informational | B at 1,700 chars, CEN, hybrid | GoldText 71.04 (C: 59.86, B: 44.10); Δ vs C +11.18 [+6.69, +15.97] | — | 0.691 | 3751 (6136) | 4479 | 43.1 | — | ″ |
| Informational | B at 1,700 chars, CEN, precise | GoldText 56.21 (C: 49.68, B: 33.87); Δ vs C +6.53 [+2.54, +10.95] | — | 0.629 | 2565 (5894) | 970 | 43.2 | — | ″ |
| Informational | B at 1,700 chars, CEN, explore | GoldText 67.62 (C: 63.68, B: 51.50); Δ vs C +3.94 [+1.05, +6.94] | — | 0.732 | 3211 (4807) | 3229 | 28.1 | — | ″ |
| Informational | B at 1,700 chars, CEN-G, hybrid | GPV 0.716 (C: 0.866, B: 0.716); vs C: b=10, c=0, p=0.0020 | — | 0.681 | 3749 (6373) | — | 40.8 | — | ″ |
| Informational | B at 1,700 chars, CEN-G, precise | GPV 0.642 (C: 0.821, B: 0.642); vs C: b=12, c=0, p=0.0005 | — | 0.622 | 2636 (6211) | — | 43.3 | — | ″ |
| Informational | B at 1,700 chars, CEN-G, explore | GPV 0.746 (C: 0.836, B: 0.731); vs C: b=6, c=0, p=0.0312 | — | 0.722 | 3170 (4551) | — | 27.5 | — | ″ |
| Informational | B at 1,700 chars, MH, hybrid | SupportVisible 0.100 (C: 0.100, B: 0.100); vs C: b=0, c=0, p=1.0000 | — | 0.490 | 5119 (6709) | — | 64.0 | — | ″ |
| Informational | B at 1,700 chars, MH, precise | SupportVisible 0.067 (C: 0.067, B: 0.067); vs C: b=0, c=0, p=1.0000 | — | 0.525 | 5047 (6767) | — | 63.8 | — | ″ |
| Informational | B at 1,700 chars, MH, explore | SupportVisible 0.067 (C: 0.067, B: 0.067); vs C: b=0, c=0, p=1.0000 | — | 0.555 | 3655 (5389) | — | 38.7 | — | ″ |

### 15.3 Layer 3 — judges

| Pack | State | full | partial | none | Net vs B | B-full → not-full | κ (double-judged) | Source JSON |
|---|---|---|---|---|---|---|---|---|
| J1 (hybrid) | A | 1 | 47 | 28 | -9 | 9 | pack 0.880 (n=46, agreement 0.935); this state 0.778 (n=17) | `judges/out_J1_*.json` |
| J1 (hybrid) | B | 10 | 46 | 20 | — | — | pack 0.880 (n=46, agreement 0.935); this state 0.903 (n=18) | ″ |
| J1 (hybrid) | C | 13 | 47 | 16 | +3 | 2 | pack 0.880 (n=46, agreement 0.935); this state 1.000 (n=11) | ″ |
| J2 (precise, opt.) | B / C | 11 / 14 | 41 / 40 | 24 / 22 | +3 | 2 | not double-judged | `judges/out_J2_*.json` |

### 15.4 Criteria outcome

| ID | Result (value, CI or p) | Pass / Fail | Evidence (run IDs → JSON) | Verified (V-ids) |
|---|---|---|---|---|
| C-01 | MRR@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.000 [+0.000, +0.000], explore +0.000 [+0.000, +0.000]; nDCG@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.000 [+0.000, +0.000], explore +0.000 [+0.000, +0.000]; pass if lower bound > -0.02 | Pass | L1-A-CEN, L1-B-CEN | V-01 pass, V-02 pass, V-03 pass, V-05 pass |
| C-02 | pooled MRR@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.000 [+0.000, +0.000], explore +0.000 [+0.000, +0.000]; largest per-suite drop +0.000 (CD-ALT explore), limit -0.03 | Pass | L1-A/B-CD-* | V-02 pass, V-03 pass, V-05 pass |
| C-03 | nDCG@10 Δ(B−A): BEIR-SF hybrid +0.000 [+0.000, +0.000], BEIR-SF precise +0.000 [+0.000, +0.000], BEIR-NF hybrid +0.000 [+0.000, +0.000], BEIR-NF precise +0.000 [+0.000, +0.000] | Pass | L1-A/B-BEIR-* | V-02 pass, V-03 pass, V-05 pass |
| C-04 | graded nDCG@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.000 [+0.000, +0.000], explore +0.000 [+0.000, +0.000] | Pass | L1-A/B-CEN-G | V-02 pass, V-03 pass, V-05 pass |
| C-05 | B ≤ A + 2 in every CEN/CD suite and path; largest B − A +0 (CEN hybrid) | Pass | L1-A/B-CEN, CD-* | V-02 pass, V-03 pass, V-05 pass |
| C-06 | L1 p50 B/A: hybrid 1.023, precise 0.966, explore 1.021; limit 1.10 | Pass | L1-A/B-CEN | V-01 pass, V-02 pass, V-03 pass, V-05 pass |
| C-07 | 0 differing of 4212 query-path pairs compared | Pass | L1-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-08 | GPV CEN-G hybrid: b=0, c=10, net +10, n=67, p=0.0020, Holm p=0.0059; superiority claimed | Pass | L2-B/C-CEN-G | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-09 | SupportVisible MH hybrid: b=0, c=0, net +0, n=30, p=1.0000, Holm p=1.0000; superiority not claimed | Pass | L2-B/C-MH | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-10 | no suite/path fails; largest binary net loss b−c +0 (MH hybrid); smallest GoldText upper bound +10.33 (CD-API explore) | Pass | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-11 | net C−B full +3; B-full→C-not-full 2; b=2, c=5, p=0.4531, Holm p=0.9062; κ=0.880 (n=46); superiority not claimed | Fail | J1, J1-R | V-06 pass |
| C-12 | max mean-chars ratio C/B 1.457 (CD-API hybrid); adversarial rule holds everywhere, largest C−B +874 chars (C/B 1.214, CD-LEG hybrid) | Pass | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-13 | abs(C−B) ≤ max(5% of B, 15 ms) everywhere; closest +4.8 ms of ±15.0 (BEIR-SF precise) | Pass | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-14 | pytest -m "unit or (benchmark and not slow)" on MPS: B pass, C pass; compare_benchmarks.py rule vs A's MPS run (hybrid, precise, explore): B pass (0 red), C pass (0 red) (A's baseline run: pass, exit 0); vs archive (information): B 0 red, C 0 red | Pass | CI-B, CI-C | — |
| C-15 | 324 of 324 outputs byte-identical | Pass | L2-C0, L2-B-CEN | V-02 pass, V-04 pass |

R2-3 sensitivity (informational; C-11 is decided on the J1 verdicts): the 7 CEN-A queries whose J1 verdicts for B and C differ on full, each B and C item with two more judges, full when 2 of 3 verdicts say full: b=0, c=4, net +4, p=0.1250, Holm p=0.2500 (`judges/out_J1D_*.json`).

Decisions: RQ1 Pass (C-01 to C-06 and C-14 for B; criteria Pass); RQ2 Fail (C-07 to C-15; criteria Fail).

### 15.5 RQ3 — generality

| Suite | Multi-match frequency (C) | Δ primary visibility (C − B) | Notes |
|---|---|---|---|
| CEN | 0.636 | +15.76 | hybrid; GoldText |
| CEN-G | 0.602 | +0.149 | hybrid; GPV; GoldText Δ +14.97 |
| MH | 0.537 | +0.000 | hybrid; SupportVisible; GoldText Δ +17.60 |
| CD-LEG | 0.679 | +22.92 | hybrid; GoldText |
| CD-MED | 0.603 | +23.19 | hybrid; GoldText |
| CD-NAR | 0.632 | +25.44 | hybrid; GoldText |
| CD-API | 0.676 | +13.28 | hybrid; GoldText |
| CD-ALT | 0.508 | +18.95 | hybrid; GoldText |
| BEIR-SF | 0.673 | +10.00 | hybrid; GoldText |
| BEIR-NF | 0.703 | +9.36 | hybrid; GoldText |
| **Spearman ρ (p)** | 0.055 (p=0.8810, n=10) | | descriptive only; registered metrics |
| Spearman ρ (p), GoldText for every suite | -0.430 (p=0.2145, n=10) | | secondary, not pre-registered: one unit across suites |

## 16. Deviations log

| Date | Section | Deviation | Reason | Effect on criteria |
|---|---|---|---|---|
| 2026-10-19 | §8, R2-3, R2-5 | Before the J1D judges ran, `judges_from_journal.py` learned a judge letter per part: a label `judge:J1D:part<k>:<j>` writes `out_J1D_part<k>_<j>.json`. A `--record` option names the extraction record and will not overwrite one. Round 1 extracted J1D with a one-off script. | The J1D extraction is reproducible, and it cannot overwrite J1's record. | None: outputs are written unchanged. |
| 2026-10-19 | §8, R2-3, §15 | After the J1 judges and before the final verification, `verify.py` gained an independent recomputation of R2-3, run only with `--round`. It covers the discordant queries from J1's verdicts, the J1D key map, parts and judge outputs, the majority of three, McNemar, and Holm with C-08 and C-09. Its checks join V-06 as pass or warn. Its result appears in §15.4 below the criteria table. On round 1's files it reproduces round 1's J1D result exactly (11 queries, b = 0, c = 7, p = 0.0156). | R2-3 reports the analysis next to C-11, and §15 must equal the verifier's rendering (V-09). | None: C-11 is decided on the J1 verdicts, and round 1's rendering is unchanged. |
| 2026-10-19 | §3 | During round 2, the round-1 results root `tests/results/agent_view_eval/verification/` was partly rewritten. 67 `recomputed_*.json` files were regenerated at 18:21:51–18:22:09Z, most likely by a verifier probe run against round 1's root while the R2-3 code was being tested (the cause is not confirmed). 13 of them differed from round 1's recorded values, and 10 now record a comparison `fail` against the repaired fixtures. Round 1's `checks.json` and §14 still record V-05 `pass`. No drive-log entry records it. The 13 changed files were restored byte-for-byte from a backup taken before round 2 (`ci_check/results_backup`, 89 files, all matching). Round 2's values are not affected. | Round 1's root is meant to be read-only for round 2 (§3). Round 1's root was not meant to be written during round 2. | None on round 2. Round 1's recorded V-05 stands: the restored files equal its recorded values. |
| 2026-10-19 | §16 (entry 2), §8 | The R2-3 recomputation was committed in e5b773b (18:24:11Z), after the J1D judges had finished (18:17–18:23Z) and `results_J1D.json` had been written (18:23Z). The earlier entry said it was added before the final verification, which is true, but it omitted this ordering. | Accuracy of the log. | None: the code was written with the J1D outcome known. An independent recomputation from the files gives the same J1D result (b = 0, c = 4, p = 0.125, Holm p = 0.25). |
| 2026-10-19 | §2 | C′ is 8e5846f plus three commits (ae8e22d, 3dc7b7a, f74b23f), not four. | Counting error. | None. |
| 2026-10-19 | §8 (judging) | Post-run audit of the J2 judges: two J2 `full` verdicts for B′ (K0150 on CEN-018 and K0121 on CEN-023) credit outputs that state none of the reference answer's facts, which says the source does not cover the topic. The judges' outputs are kept as recorded. J2 is informational and decides nothing. With those two verdicts corrected, J2 gives B′ 9 and C′ 14 full, b = 0, c = 5, p = 0.0625. | Audit finding; the rubric (§8) requires strict reading. | None on C-11 or RQ2. Three CEN-A queries have negative reference answers (CEN-018, CEN-023, CEN-059); see the threats note. |
| 2026-10-19 | §15.4 / C-11 | Audit of C-11: C′'s tool output contains all of B′'s text for all 76 CEN-A queries on hybrid and on precise. The two C-11 losses (CEN-004 and CEN-059) are single-judge disagreements on identical evidence. C-11 fails as registered, and RQ2 fails with it. The registered outcome stands. | Interpretation for the report: C-11's 'at most one loss' clause measures judge variance when C′ contains B′. | None on the registered outcome. The report must not describe the two losses as content loss. |
| 2026-10-19 | §15.2 / C-12 | Audit of C-12: it passes under the registered aggregation (ratio of all-query means, as in round 1) with a margin of 76.7 characters on CD-API hybrid. Per-query averaging, or dropping the adversarial queries, would fail it (non-adversarial ratio 1.59 on CD-API hybrid). The result is reported with that margin. | Transparency about how narrow the pass is. | None under the registered rule. |
| 2026-10-19 | §15.1 / C-05 | Audit: C-05 cannot fail on hybrid or explore, because A already leaks on every adversarial query there (B′ = A = 30 of 30). The substantive evidence for no leak regression on those paths is the ranking identity (4,212 of 4,212 query-path pairs identical). | Interpretation. | None. |
| 2026-10-19 | §16 (threats) | Threats not in the registered plan: (1) run order was not counterbalanced (B′, B′ rerun, A, C′ on CEN), which for C-06 works against B′; (2) the bootstrap depends on the order of paired differences, which the protocol does not fix (round 1's BEIR-SF CI shifts in the third decimal under sorting); (3) formatting reveals the state for 97.4% of J1 items (A by its Description prefix, C′ by its `[…]` marker or windows over 1,000 characters), and the judge pack has no length-matched B′ arm; (4) the key maps are byte-identical to round 1's, so the analyst knew each item's state before judging (the commitment shows the map was not edited afterwards, not that the analyst was blind). | Audit findings. | None on the registered outcomes. These are recorded as threats. |
| 2026-10-19 | env/C.txt | The C′ venv was made by copying round 1's `venvs/C` and repointing its editable `.pth` by hand to `worktrees/Cprime/src`. The dist-info still describes an editable install of `worktrees/C`, so `env/C.txt`'s `pip freeze` line names round 1's worktree. The code that ran is the Cprime checkout (shown by the L1 `candlekeep_file` and the L2 server log). Not reinstalled, to keep the run's environment unchanged. | Audit finding. | None on results. The venv should be reinstalled from `worktrees/Cprime` before any further run. |

## 17. Change log

- 2026-10-19 — Round 2 written and frozen before any round-2 run.
