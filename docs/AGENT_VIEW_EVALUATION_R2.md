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

C′ is B′'s `8e5846f` plus four commits: the two round-1 C commits, cherry-picked (`ae8e22d`, `3dc7b7a`), and `f74b23f`. B′'s checkout may sit on a later commit that changes only documentation or the harness; V-02 checks that `git diff 8e5846f -- src/` is empty for every B′ output. The venvs of B′ and C′ have identical package lists.

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
| J1D | B/C | — | — | L3 info | C-11 discordant queries (R2-3) | `rejudge_discordant.py build/analyse --round …` | `…/judges/pack_J1D_part*.json`, `keymap_J1D.json`, `results_J1D.json` | — | pending | |
| CI-A | A | 6519cc7 | venv-A | CI | — | `pytest -m "unit or (benchmark and not slow)" -p mps_serial` (MPS) | `…/verification/ci_A.txt` | — | done: 214 passed, 12 skipped (1 attempt) | |
| CI-B | B | 8e5846f | venv-B | CI | — | `pytest -m "unit or (benchmark and not slow)"` (MPS) | `…/verification/ci_B.txt` | — | done: 275 passed, 12 skipped (1 attempt); 0 red flags vs A | |
| CI-C | C | f74b23f | venv-Cprime | CI | — | ″ | `…/verification/ci_C.txt` | — | done: 307 passed, 12 skipped (1 attempt); 0 red flags vs A | |
| V-ALL | — | — | — | verify | all | `drive.py verify --all --check-doc --round …` | `…/verification/checks.json`, `…/summary.json` | — | pending | |

The key maps of J1, J1R and J2 are byte-identical to round 1's. They depend only on the seed, the 76 CEN-A queries and the states, so an item id names the same query and state in both rounds. The judges see only their own part.

## 15. Results (filled from `summary.json` after V-ALL passes)

To be filled by `verify.py --round scripts/eval_agent_view/rounds/r2.json --render`.

## 16. Deviations log

| Date | Section | Deviation | Reason | Effect on criteria |
|---|---|---|---|---|

## 17. Change log

- 2026-10-19 — Round 2 written and frozen before any round-2 run.
