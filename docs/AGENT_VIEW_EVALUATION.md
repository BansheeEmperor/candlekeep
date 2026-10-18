# Evaluating Agent-Visible Retrieval Quality: Protocol and Results Registry

**Status:** Pre-registered protocol, frozen 2026-10-18 before any protocol run. Sections 1–12 are frozen. Any later change goes in the [Deviations Log](#16-deviations-log) with its reason. Sections 14–15 are filled in as runs complete. Section 13 is the verification checklist that must pass before any result is reported.

**Scope:** Public data only (the repository's test fixtures and the public BEIR sets).

---

## Abstract

Candlekeep's established benchmarks (`eval/runner.py`, the Centurion Set, the cross-domain suites) score the **full text of each result**: ranking metrics over result sources, and token counts over the full result text. An agent using the MCP server never sees that text. It sees what the `search` tool returns: a fixed-length view of each result. Changes to that view are invisible to the existing benchmarks, and so are failures that sit only in that view.

This document pre-registers an evaluation with three parts:

- **Code states:** the current baseline, the current branch, and the branch plus a proposed presentation change.
- **Measurement layers:** retrieval quality measured in-process the project's way, agent-visible quality measured through the MCP tool, and blind LLM judgement.
- **Decision rules:** fixed before any run. The changes must not regress overall Candlekeep quality on any public corpus, and any improvement must not be specific to one corpus.

Section 14 records the runs, with output paths, so that every reported number can be recomputed and checked.

---

## 1. Research questions

- **RQ1 — No regression from the branch.** Does state B (current branch) match or beat state A (baseline) on the project's own retrieval metrics, across every public corpus and every search path?
- **RQ2 — Benefit without regression from the proposal.** Does state C (B plus the result-view change) increase the share of answer evidence an agent actually sees, while:
  - leaving retrieval rankings unchanged,
  - keeping output growth within budget,
  - keeping latency unchanged, and
  - not getting worse on any corpus?
- **RQ3 — Generality.** Is any effect of C explained by a structural property of the data (how often a result window contains more than one matched chunk), rather than by one particular corpus?

## 2. Background and hypotheses

How a result is built today (state B):

1. **Retrieval.** Each search path (hybrid, precise, explore) produces a ranked list of candidate chunks.
2. **Arcane Recall expansion** (`rag/arcane_recall.py::expand_results`) widens each candidate into a window of neighbouring chunks. Arcane Coalescence then merges every overlapping or adjacent window of the same document, so **one result window can contain several matched candidate chunks**.
3. **Stitching** keeps the Bardic Knowledge prefix once and removes chunk overlaps. The window records the position of its single best-scoring matched chunk (`_match_offset`).
4. **The `search` tool** (`mcp/server.py::_format_result`) returns a title line plus `CANDLEKEEP_RESULT_CHARS` (default 1000) characters starting at that one position.

Matched chunks other than the best one are therefore never shown when they lie outside that span. The proposal (state C) keeps today's view and adds, from one shared per-query budget, each window's other matched chunks.

**Hypotheses:**

- **H1.** C increases agent-visible answer evidence (gold-passage visibility, multi-hop support visibility, and judge-rated completeness) relative to B.
- **H2.** C changes no ranking: the ordered result list is identical to B for every query, path and suite. B changes rankings only where its changes intend to.
- **H3.** The size of C's gain across corpora rises with the share of results whose window contains two or more matched chunks. On corpora of single-chunk documents (BEIR) the effect is close to zero.
- **H0.** The negation of H1–H3, together with any regression beyond the margins in Section 10, means rejection.

## 3. Code states

| State | Definition | Git ref | FastMCP | Notes |
|---|---|---|---|---|
| **A** | Project baseline | `development` @ `6519cc7` | 2.14.5 (pinned by A) | Includes A's known defects: unpaginated full-collection reads, the post-ingest graph rebuild never scheduled, and a 500-character un-stitched view. |
| **B** | Current branch | `feat/large-collections-and-result-context` @ `d524652` | 3.4.9 | Paginated reads, graph rebuild fix, faster co-occurrence query, stitching and match-anchored 1000-character view, FastMCP 3 with the BM25 lock, rate-limit keying. |
| **C** | B + proposal | `feat/show-matched-passages` @ `ade2365` (two commits on top of `c43016f`: `d5b8895`, `ade2365`) | 3.4.9 | Defined in §3.1, as resolved in the Deviations Log. |

### 3.1 Definition of C (frozen)

Per query, with results `r_1..r_n` in the order the path returns them:

1. **Primary view.** Each result keeps today's view: a title line plus `CANDLEKEEP_RESULT_CHARS` = 1000 characters starting at its best match.
2. **Claims.** Each window's matched candidate chunks, with their spans in the stitched text and their rank in the path's own candidate order (the input order of `expand_results`), are recorded during stitching. Spans fully inside the primary view are dropped.
3. **Extra budget.** One per-query budget, `CANDLEKEEP_RESULT_EXTRA_CHARS` = 2500 characters, is spent on claims in ascending rank across all results. Each claim takes `min(span length, remaining budget)` characters, and stops once fewer than 120 would remain. The gap marker `"\n[…]\n"` counts against the budget.
4. **Rendering.** Within a result, the primary view and claimed spans are shown in document order, joined by the gap marker.
5. **Leftover.** Any unspent budget extends the first result's primary view forward.
6. **Kill switch.** `CANDLEKEEP_RESULT_EXTRA_CHARS=0` must reproduce B's output byte for byte. This is verified as V-04 in Section 13.

A pilot prototype (a runtime wrapper, not committed) may be used to debug the harness. Pilot results are labelled `P*` and never count toward any criterion.

## 4. Controls

| Control | Setting | Reason |
|---|---|---|
| Same data across states | Each corpus is ingested **once**, by state B through the MCP `ingest` tool. A, B and C all query that same Chroma collection and data directory. | HNSW construction is non-deterministic (DESIGN §8.6). Re-ingesting per state would confound code effects with index variance. Chunk text and embeddings are identical across states: the processor's output is unchanged by the branch. |
| Entity graph | After ingest, `rebuild_graph` is called explicitly through MCP. All states read the same `graph.db`. | Isolates query-time code. A's real-world empty graph is measured separately as an informational row (§7.5). |
| Chroma | chromadb 1.5.9 server, one server and port per corpus, run sequentially. | The collection name is hard-coded (`candlekeep`). |
| Chunking | Default 512 / 100. For graded-relevance metrics only, a separate Centurion ingest at overlap 50. | The graded labels (`source:chunk_index`) were produced on 2026-02-26 with overlap 50; chunk indices differ at 100. |
| Device | `CANDLEKEEP_DEVICE=mps` for every state. | With sentence-transformers 6.x, the precise path's CPU float64 workaround raises `AttributeError` in A and B alike. CPU results are out of scope (§12). |
| Models | `BAAI/bge-small-en-v1.5` and `cross-encoder/ms-marco-MiniLM-L-6-v2` from the same local cache. Cache path and revision hashes are recorded in the environment manifest. | Identical inference across states. |
| Dependencies | One venv per state, Python 3.11. A is installed with a constraints file equal to B's `pip freeze`, minus `fastmcp` and `py-key-value-aio`. | Only intended differences remain. |
| Code checkout | A and C run from `git worktree` checkouts. B runs from the main checkout at `d524652`. | No branch switching mid-run. |
| Rate limiting | `CANDLEKEEP_RATE_LIMIT_SEARCH=0` and `CANDLEKEEP_RATE_LIMIT_WRITE=0` for Layer 2. | As in the project's scale benchmark; keeps runs fast and pacing-independent. |
| Other | `n_results=5` (BEIR: 10). No category filter. Default Relevance Ward thresholds. Graph augment on. ColBERT off. No LLM or VLM providers. | Recommended configuration. |
| Determinism | B runs twice on Centurion (L1 and L2); outputs must be identical (§13, V-01). | Separates code effects from run-to-run noise. |
| Randomness | Every sampled or shuffled step uses seed `20261018`. | Reproducibility. |

## 5. Datasets

| ID | Suite | Corpus path | Queries | n | Gold | Layers |
|---|---|---|---|---|---|---|
| CEN | Centurion Set | `tests/fixtures/sample_docs` + `tests/fixtures/scale_docs` (89 docs: 88 `.md` + 1 `.txt`) | `tests/fixtures/eval_suite_100.json` | 108 (48 semantic / 30 lexical / 30 adversarial) | `expected_sources` | L1, L2 |
| CEN-G | Centurion, graded (overlap 50) | same corpus, separate ingest at overlap 50 | same, `graded_relevance` | 108, of which non-adversarial with grade ≥ 2 counted in §14 | chunk grades 0–3 | L1 (graded nDCG@5), L2 (gold-passage visibility) |
| CEN-A | Centurion answers | as CEN | `tests/fixtures/eval_suite_with_answers.json` | 78 non-adversarial | `reference_answer` | L3 judges |
| MH | Multi-hop (track 2) | as CEN | `tests/fixtures/track2_multi_hop_queries.json` | 30 (26 with 3 supporting docs, 4 with 2) | `supporting_docs` (all 86 present in the corpus) | L1, L2 |
| CD-LEG | Cross-domain legal | `tests/fixtures/cross_domain/legal_docs` (90) | `eval_suite_legal.json` | 107 | `expected_sources` | L1, L2 |
| CD-MED | Cross-domain medical | `.../medical_docs` (91) | `eval_suite_medical.json` | 108 | ″ | L1, L2 |
| CD-NAR | Cross-domain narrative | `.../narrative_docs` (89) | `eval_suite_narrative.json` | 108 | ″ | L1, L2 |
| CD-API | Cross-domain API reference | `.../api_ref_docs` (95) | `eval_suite_api_ref.json` | 108 | ″ | L1, L2 |
| CD-ALT | Cross-domain alternating | `.../alternating_docs` (88) | `eval_suite_alternating.json` | 104 | ″ | L1, L2 |
| BEIR-SF | BEIR SciFact (test) | `tests/fixtures/beir/scifact` (5,183 docs) | `queries.jsonl` + `qrels/test.tsv` | 300 | graded qrels | L1, L2 (null-effect control) |
| BEIR-NF | BEIR NFCorpus (test) | `tests/fixtures/beir/nfcorpus` (3,633 docs) | `queries.jsonl` + `qrels/test.tsv` | 323 | graded qrels | L1, L2 (null-effect control) |

**BEIR conversion (frozen).** Each document becomes `<_id>.md` with frontmatter `title: <title>` and `description: ""`, and the body text, ingested as a directory. Query IDs map to qrels. The conversion is identical for every state.

## 6. Layer 1 — retrieval, in-process

**Procedure.** For each state, suite and path, call `candlekeep.rag.router.search_with_routing(store, query, n_results, query_type=path)` against the shared collection. This is the call the project's runner wraps. Record per query: the ordered list of `(source, chunk_index, score)`, the full result texts, and latency.

**Metrics.** Document-level metrics follow `eval/metrics.py`, with `retrieved_ids` being result sources in order:

| Metric | Definition |
|---|---|
| MRR@5 | `calculate_reciprocal_rank` over the first 5 sources |
| nDCG@5 | `calculate_ndcg(retrieved, gold, 5)` |
| Hit@1, Hit@5 | `calculate_hit_rate(retrieved, gold, k)` |
| P@5 | `calculate_precision_at_k(retrieved, gold, 5)` |
| Graded nDCG@5 (CEN-G only) | `calculate_ndcg_graded(retrieved_chunk_ids, graded_relevance, 5)`, with chunk IDs `source:chunk_index` from the overlap-50 collection |
| SupportAll@5 (MH) | 1 if every supporting doc is among the first 5 sources, else 0 |
| nDCG@10, Recall@10 (BEIR) | Standard BEIR definitions over doc IDs with graded qrels, `n_results=10` |
| Adversarial leak (adversarial queries) | 1 if any result is returned, else 0 |
| Full-text tokens | `sum(len(text)) // 4` (the runner's `avg_tokens`; reported, not judged) |
| Latency | Wall time of `search_with_routing`, in ms; p50 and p95 |
| Ranking identity (C vs B) | Per query and path, equality of the ordered `(source, chunk_index)` lists |

## 7. Layer 2 — agent-visible quality, through MCP

**Procedure.** Start the state's server in HTTP mode on the shared collection. Use one MCP session per suite, with the client harness `scripts/eval_agent_view/run_layer2.py` (to be written). Call the `search` tool for every query and path and save the **raw tool output string** per query. Every Layer 2 metric is computed from that string alone.

**Normalisation (frozen).** Remove backslash escapes before punctuation, collapse whitespace, lowercase.

**Shingles.** A text's shingles are its normalised substrings of length 150 taken at offsets that are multiples of 25, plus the whole text if it is shorter than 150.

### 7.1 Metrics

| Metric | Suites | Definition |
|---|---|---|
| SrcVis@5 | all | Hit@5 over the `Source:` lines of the output (sanity check; must equal L1 for the same state) |
| **GPV** (gold-passage visible) | CEN-G | Gold chunks are those with grade ≥ 2 under overlap 50, prefix stripped. GPV = 1 if at least one shingle of at least one gold chunk occurs in the output. Queries with no gold chunk of grade ≥ 2 are excluded; the count is reported. |
| **GPC** (gold-passage coverage) | CEN-G | Mean over gold chunks of the fraction of that chunk's shingles occurring in the output |
| **SupportVisible** | MH | 1 if, for every supporting doc, at least one shingle of that doc's text occurs in the output |
| **GoldText** | CEN, CD-*, BEIR | Number of distinct gold-document shingles in the output (evidence volume) |
| **GoldShare** | CEN, CD-*, BEIR | Visible characters inside results whose source is gold, divided by all visible characters |
| Output size | all | Characters of the tool output per query: mean, p95, and mean on adversarial queries |
| Adversarial leak | CEN, CD-* | As in L1, from the output |
| Latency | all | Client-side round-trip of the `search` call; p50 and p95 |
| Multi-match frequency (RQ3) | all | Share of returned results whose window contains two or more matched candidate chunks (from C's recorded claims, logged by the harness) |

### 7.2 Informational rows (not criteria)

- **A-as-shipped:** A run against a copy of the data directory whose `entity_cooccurrence` table is empty, as A leaves it after a normal ingest. It quantifies the graph fix's effect on explore.
- **B with `RESULT_CHARS=500`:** isolates stitching plus match-anchoring from the budget increase.

## 8. Layer 3 — blind judgement

| Step | Specification |
|---|---|
| Items | CEN-A (78 non-adversarial queries) × states {A, B, C}, hybrid path: 234 items. Optional second pack: precise path, {B, C}: 156 items. |
| Content | Question, reference answer, raw tool output. No state, path or source labels. |
| Blinding | Items are shuffled (seed 20261018) and given random IDs `J####`. The key map is saved, and its SHA-256 is written in §14 **before** judging starts. |
| Judges | Independent LLM sub-agents, 25–30 items each. They must not read any file other than their input. |
| Rubric | **full**: the output alone lets an agent answer correctly and completely. **partial**: some needed facts are missing, or too fragmentary to be confident. **none**: the answer is absent. Judges must quote verbatim evidence. Strictness: they must not infer facts that are not visible. |
| Reliability | A random 20% of items is judged a second time by a different judge. Report exact agreement and Cohen's κ on the 3-class verdict. |
| Validity checks | Every evidence snippet must occur verbatim in its tool output (V-06). If κ < 0.6, the judge criteria are reported but count as unconfirmed. |

## 9. Statistical analysis

| Purpose | Method |
|---|---|
| Paired binary outcomes per query (GPV, SupportVisible, Hit@k, judge "full") | Counts `b` (only the reference succeeds) and `c` (only the candidate succeeds). Exact McNemar (binomial on `b + c`), two-sided α = 0.05. |
| Paired continuous metrics (MRR, nDCG, GPC, latency) | Paired bootstrap of the mean difference: 10,000 resamples, seed 20261018, percentile 95% CI. |
| Non-inferiority (RQ1) | Pass if the lower bound of the 95% CI of (B − A) is above −δ. δ = 0.02 absolute for MRR, nDCG, Hit and P. |
| Multiplicity | Holm–Bonferroni across the RQ2 superiority endpoints C-08, C-09 and C-11. Non-inferiority criteria are not adjusted. |
| Pooled cross-domain | Queries from the five CD suites are pooled (n = 535), and per-suite values are also reported. |
| RQ3 | Spearman correlation between per-suite multi-match frequency and the per-suite C − B change in the primary visibility metric (GPV for CEN-G, SupportVisible for MH, GoldText per query elsewhere). Descriptive only, not a pass/fail criterion. |

## 10. Pre-registered pass criteria

| ID | RQ | Comparison | Metric and scope | Pass rule |
|---|---|---|---|---|
| C-01 | 1 | B vs A | L1 MRR@5 and nDCG@5, CEN, each path | non-inferior (δ = 0.02) |
| C-02 | 1 | B vs A | L1 MRR@5, CD pooled, each path | non-inferior (δ = 0.02); no single CD suite drops by more than 0.03 |
| C-03 | 1 | B vs A | L1 nDCG@10, BEIR-SF and BEIR-NF, hybrid and precise | non-inferior (δ = 0.02) |
| C-04 | 1 | B vs A | L1 graded nDCG@5, CEN-G, each path | non-inferior (δ = 0.02) |
| C-05 | 1 | B vs A | Adversarial leak, CEN + CD, each path | B leaks ≤ A leaks + 2 queries per suite |
| C-06 | 1 | B vs A | L1 latency p50, CEN, each path | B / A ≤ 1.10 |
| C-07 | 2 | C vs B | Ranking identity, every suite and path | 0 differing queries |
| C-08 | 2 | C vs B | GPV, CEN-G, hybrid | net (c − b) ≥ 0 with no significant decrease. Superiority is claimed only if Holm-adjusted p < 0.05. |
| C-09 | 2 | C vs B | SupportVisible, MH, hybrid | as C-08 |
| C-10 | 2 | C vs B | Primary visibility metric per suite and path (GPV, SupportVisible, or GoldText per query) | no suite or path with a net loss of more than 1 query (binary) or a lower 95% bound below 0 for a paired-mean decrease (GoldText) |
| C-11 | 2 | C vs B | Judge "full" rate, CEN-A, hybrid | net (C-full − B-full) ≥ 0; at most 1 query goes from B-full to C-not-full; κ ≥ 0.6 |
| C-12 | 2 | C vs B | L2 output size | mean chars per query, C / B ≤ 1.5 for every suite and path; adversarial mean chars, C / B ≤ 1.5 |
| C-13 | 2 | C vs B | L2 latency p50, each path | within ±5% or ±15 ms, whichever is larger |
| C-14 | 1, 2 | B and C | CI gates | `pytest -m "unit or (benchmark and not slow)"` passes on MPS; `scripts/compare_benchmarks.py` shows no drop outside the archived CI |
| C-15 | 2 | C (kill switch) | `CANDLEKEEP_RESULT_EXTRA_CHARS=0` vs B | byte-identical outputs on CEN, all paths |

**Decisions.**

- **RQ1 passes** if C-01 to C-06 and C-14 (for B) pass.
- **RQ2 passes** if C-07 to C-15 pass.
- **Failures.** A failed criterion is reported as a failure. It may be investigated and explained, but it may not be re-defined afterwards. Any fix produces a new state (e.g. B′), which re-enters the protocol and is recorded in the Deviations Log.

## 11. Execution plan

1. **Environment** (R00).
   - Create worktrees and venvs for A and C.
   - Write `tests/results/agent_view_eval/env/{A,B,C}.txt`: `pip freeze`, model cache hashes, git SHA, device.
2. **Harness.** Write and commit `scripts/eval_agent_view/` before the first protocol run:
   - `ingest.py`, `run_layer1.py`, `run_layer2.py`, `judge_pack.py`, `verify.py`.
   - Optional pilot P01 using the prototype.
3. **Ingest** (I01–I09). Use state B's server through MCP `ingest`, then `rebuild_graph`. Record chunk and entity counts.
4. **Determinism check** (R01). Run B twice on CEN (L1 and L2).
5. **Layer 1.** Run L1-{A,B,C}-{suite}.
6. **Layer 2.** Run L2-{A,B,C}-{suite}, plus the informational rows (§7.2).
7. **Layer 3.** Build the judge packs, record the key-map hash, run the judges, double-judge 20%, unblind.
8. **Analysis and verification.** Run `verify.py`, which recomputes every number from raw outputs (§13). Fill in §14–15.
9. **Report.** Report RQ1, RQ2 and RQ3 against §10.

**Output layout:**

```
tests/results/agent_view_eval/
  env/{A,B,C}.txt
  ingest/I0x_<suite>.json             # chunk/entity/edge counts, timings
  L1/{A,B,C}_<suite>.json             # per-query rankings, texts, latency, metrics
  L2/{A,B,C}_<suite>.json             # per-query raw tool outputs, metrics
  L2/info_*.json                      # informational rows
  judges/pack_*.json, keymap_*.json (+ .sha256), out_*.json
  verification/recomputed_*.json, checks.json
  summary.json                        # every number in §15, written by verify.py
```

## 12. Threats to validity

- **Judge bias.** LLM judges may share blind spots. Mitigated by strict blinding, verbatim evidence, double judging with κ, and deterministic metrics that don't depend on the judges.
- **Proxy metrics.**
  - Shingle visibility is a lower bound: it misses paraphrase, but it is the same rule for every state.
  - GoldText counts evidence volume, not correctness, so it is paired with GoldShare (noise) and output size.
- **Graded labels.** Produced by heuristics plus a second LLM rater, with reported κ_binary 0.53. Used only for CEN-G and only at the annotation chunking (overlap 50).
- **Corpus character.** The public corpora are short to medium-length markdown documents. H3 predicts small C effects there; a small effect is consistent with H1–H3, not a failure, provided C-10 holds.
- **Small n per suite** (about 100). Pooling and paired tests are used; one query is about 1 point.
- **Device.** MPS only. The CPU precise path is broken with the pinned-at-runtime dependencies in both A and B, and is out of scope here.
- **Rosetta Seal.** The normalisation map is built but not applied in BM25 in any state, so it does not differ between states.
- **Rate limiting** is disabled. The effect of rate limits on agent behaviour is not measured.

## 13. Verification procedure (must pass before reporting)

| ID | Check | Method | Evidence |
|---|---|---|---|
| V-01 | Determinism | B-run-1 and B-run-2 on CEN have identical L1 rankings and identical L2 outputs | `verification/checks.json` |
| V-02 | Provenance | Every result file carries its git SHA, state, device, package versions and corpus ingest ID, and these match §14 | `verify.py` |
| V-03 | Counts | n per suite equals §5; no missing queries or paths; the CEN-G exclusion count is stated | `verify.py` |
| V-04 | Kill switch | C with extras = 0 equals B byte for byte (C-15) | `verify.py` |
| V-05 | Independent recomputation | `verify.py` recomputes every metric in §15 from raw per-query data, without importing harness metric code. Any mismatch over 1e-9 fails. | `verification/recomputed_*.json` |
| V-06 | Judge integrity | Key-map SHA-256 matches the value recorded before judging; every evidence snippet occurs verbatim; every item was judged exactly once (twice for the double-judged subset) | `judges/*`, `checks.json` |
| V-07 | L1/L2 consistency | SrcVis@5 (L2) equals Hit@5 (L1) per state, suite and path | `checks.json` |
| V-08 | Spot check | 10 random queries per state are inspected by hand against their metric values, and notes are recorded | `verification/spot_checks.md` |
| V-09 | Table ↔ JSON | Every number in §15 is diffed against `summary.json` by script | `verify.py --check-doc` |

## 14. Run registry (filled during execution)

Status values: `pending` · `running` · `done` · `verified` · `failed` · `void`.

| Run | State | Git SHA | Env | Layer | Suite | Command (abridged) | Output path | n | Status | Verified (V-ids) |
|---|---|---|---|---|---|---|---|---|---|---|
| R00-A | A | 6519cc7 | venv-A | env | — | `scripts/eval_agent_view/env.py --state A` | `tests/results/agent_view_eval/env/A.txt` | — | pending | |
| R00-B | B | d524652 | venv-B | env | — | `… --state B` | `…/env/B.txt` | — | pending | |
| R00-C | C | ade2365 | venv-C | env | — | `… --state C` | `…/env/C.txt` | — | pending | |
| I01 | B | d524652 | venv-B | ingest | CEN | `ingest.py --suite CEN` | `…/ingest/I01_CEN.json` | 89 docs | pending | |
| I02 | B | d524652 | venv-B | ingest | CEN-G (overlap 50) | `ingest.py --suite CEN --overlap 50` | `…/ingest/I02_CEN-G.json` | 89 docs | pending | |
| I03 | B | d524652 | venv-B | ingest | CD-LEG | `ingest.py --suite CD-LEG` | `…/ingest/I03_CD-LEG.json` | 90 docs | pending | |
| I04 | B | d524652 | venv-B | ingest | CD-MED | `… CD-MED` | `…/ingest/I04_CD-MED.json` | 91 docs | pending | |
| I05 | B | d524652 | venv-B | ingest | CD-NAR | `… CD-NAR` | `…/ingest/I05_CD-NAR.json` | 89 docs | pending | |
| I06 | B | d524652 | venv-B | ingest | CD-API | `… CD-API` | `…/ingest/I06_CD-API.json` | 95 docs | pending | |
| I07 | B | d524652 | venv-B | ingest | CD-ALT | `… CD-ALT` | `…/ingest/I07_CD-ALT.json` | 88 docs | pending | |
| I08 | B | d524652 | venv-B | ingest | BEIR-SF | `… BEIR-SF` | `…/ingest/I08_BEIR-SF.json` | 5,183 docs | pending | |
| I09 | B | d524652 | venv-B | ingest | BEIR-NF | `… BEIR-NF` | `…/ingest/I09_BEIR-NF.json` | 3,633 docs | pending | |
| R01 | B | d524652 | venv-B | L1+L2 | CEN (determinism, run 2) | `run_layer1.py / run_layer2.py --state B --suite CEN --tag rerun` | `…/L1/B_CEN_rerun.json`, `…/L2/B_CEN_rerun.json` | 108 | pending | |
| L1-A-* | A | 6519cc7 | venv-A | L1 | CEN, CEN-G, MH, CD×5, BEIR×2 | `run_layer1.py --state A --suite <s>` | `…/L1/A_<s>.json` | per §5 | pending | |
| L1-B-* | B | d524652 | venv-B | L1 | ″ | `… --state B …` | `…/L1/B_<s>.json` | per §5 | pending | |
| L1-C-* | C | ade2365 | venv-C | L1 | ″ | `… --state C …` | `…/L1/C_<s>.json` | per §5 | pending | |
| L2-A-* | A | 6519cc7 | venv-A | L2 | CEN, CEN-G, MH, CD×5, BEIR×2 | `run_layer2.py --state A --suite <s>` | `…/L2/A_<s>.json` | per §5 | pending | |
| L2-B-* | B | d524652 | venv-B | L2 | ″ | `… --state B …` | `…/L2/B_<s>.json` | per §5 | pending | |
| L2-C-* | C | ade2365 | venv-C | L2 | ″ | `… --state C …` | `…/L2/C_<s>.json` | per §5 | pending | |
| L2-C0 | C (extras = 0) | ade2365 | venv-C | L2 | CEN | `CANDLEKEEP_RESULT_EXTRA_CHARS=0 run_layer2.py --state C --suite CEN --tag killswitch` | `…/L2/C_CEN_killswitch.json` | 108 | pending | |
| L2-I1 | A (empty graph) | 6519cc7 | venv-A | L2 info | CEN, MH | `run_layer2.py --state A --graph empty` | `…/L2/info_A_emptygraph_<s>.json` | 108/30 | pending | |
| L2-I2 | B (500 chars) | d524652 | venv-B | L2 info | CEN, MH | `CANDLEKEEP_RESULT_CHARS=500 run_layer2.py --state B` | `…/L2/info_B_500_<s>.json` | 108/30 | pending | |
| J1 | A/B/C | — | — | L3 | CEN-A hybrid | `judge_pack.py --pack J1` | `…/judges/pack_J1.json`, `keymap_J1.json` (SHA-256: `b93e2d6a8d2c409b85c0ffb1986fe5b52f7cef8c40b72d3968e6702c00af8725`), `out_J1_*.json` | 228 | packs built | |
| J1-R | — | — | — | L3 | 20% re-judge | `judge_pack.py --pack J1R` | `…/judges/pack_J1R.json`, `keymap_J1R.json` (SHA-256: `2493f118148d3b5e52efec58bff3f0659d595ea38991141e6a439fedb95f38ab`), `out_J1R_*.json` | 46 | packs built | |
| J2 (opt.) | B/C | — | — | L3 | CEN-A precise | `judge_pack.py --pack J2` | `…/judges/pack_J2.json`, `keymap_J2.json` (SHA-256: `6d75632acefdc12c4c136af5a2ad3594ad565d82d58e22d268f82af6296df5e2`), `out_J2_*.json` | 152 | packs built | |
| CI-B | B | d524652 | venv-B | CI | — | `pytest -m "unit or (benchmark and not slow)"` (MPS) | `…/verification/ci_B.txt` | — | pending | |
| CI-C | C | ade2365 | venv-C | CI | — | ″ | `…/verification/ci_C.txt` | — | pending | |
| V-ALL | — | — | — | verify | all | `verify.py --all --check-doc` | `…/verification/checks.json`, `…/summary.json` | — | pending | |

## 15. Results (filled from `summary.json` after V-ALL passes)

### 15.1 Layer 1 — retrieval (values: A / B / C; Δ(B−A) with 95% CI)

| Suite | Path | MRR@5 | nDCG@5 | Hit@1 | Hit@5 | P@5 | Graded nDCG@5 | Adv. leak | Latency p50 (ms) | Ranking identical C=B | Source JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CEN | hybrid | | | | | | — | | | | `L1/{A,B,C}_CEN.json` |
| CEN | precise | | | | | | — | | | | ″ |
| CEN | explore | | | | | | — | | | | ″ |
| CEN-G | hybrid / precise / explore | — | — | — | — | — | | — | — | | `L1/{A,B,C}_CEN-G.json` |
| MH | each path | SupportAll@5: | | | | | — | — | | | `L1/{A,B,C}_MH.json` |
| CD-LEG … CD-ALT, pooled | each path | | | | | | — | | | | `L1/{A,B,C}_CD-*.json` |
| BEIR-SF / BEIR-NF | hybrid / precise | nDCG@10: | Recall@10: | | | | — | — | | | `L1/{A,B,C}_BEIR-*.json` |

### 15.2 Layer 2 — agent-visible (values: A / B / C; McNemar b, c, p for C vs B)

| Suite | Path | Primary visibility (GPV / SupportVisible / GoldText) | GPC | GoldShare | Chars/q mean (p95) | Adv. chars/q | Latency p50 | Multi-match freq. | Source JSON |
|---|---|---|---|---|---|---|---|---|---|
| CEN-G | each path | | | | | | | | `L2/{A,B,C}_CEN-G.json` |
| MH | each path | | — | | | — | | | `L2/{A,B,C}_MH.json` |
| CEN | each path | | — | | | | | | `L2/{A,B,C}_CEN.json` |
| CD-* (each), pooled | each path | | — | | | | | | `L2/{A,B,C}_CD-*.json` |
| BEIR-SF / BEIR-NF | hybrid / precise | | — | | | — | | | `L2/{A,B,C}_BEIR-*.json` |
| Informational | A empty graph; B at 500 chars | | | | | | | | `L2/info_*.json` |

### 15.3 Layer 3 — judges

| Pack | State | full | partial | none | Net vs B | B-full → not-full | κ (double-judged) | Source JSON |
|---|---|---|---|---|---|---|---|---|
| J1 (hybrid) | A | | | | | | | `judges/out_J1_*.json` |
| J1 (hybrid) | B | | | | — | — | | ″ |
| J1 (hybrid) | C | | | | | | | ″ |
| J2 (precise, opt.) | B / C | | | | | | | `judges/out_J2_*.json` |

### 15.4 Criteria outcome

| ID | Result (value, CI or p) | Pass / Fail | Evidence (run IDs → JSON) | Verified (V-ids) |
|---|---|---|---|---|
| C-01 | | | L1-A-CEN, L1-B-CEN | |
| C-02 | | | L1-A/B-CD-* | |
| C-03 | | | L1-A/B-BEIR-* | |
| C-04 | | | L1-A/B-CEN-G | |
| C-05 | | | L1-A/B-CEN, CD-* | |
| C-06 | | | L1-A/B-CEN | |
| C-07 | | | L1-B/C-* | |
| C-08 | | | L2-B/C-CEN-G | |
| C-09 | | | L2-B/C-MH | |
| C-10 | | | L2-B/C-* | |
| C-11 | | | J1, J1-R | |
| C-12 | | | L2-B/C-* | |
| C-13 | | | L2-B/C-* | |
| C-14 | | | CI-B, CI-C | |
| C-15 | | | L2-C0, L2-B-CEN | |

### 15.5 RQ3 — generality

| Suite | Multi-match frequency (C) | Δ primary visibility (C − B) | Notes |
|---|---|---|---|
| (one row per suite) | | | |
| **Spearman ρ (p)** | | | |

## 16. Deviations log

| Date | Section | Deviation | Reason | Effect on criteria |
|---|---|---|---|---|
| 2026-10-18 (pre-run) | §5 CEN | 4 lexical Centurion queries have gold documents under the repo's `docs/` (one, `docs/HARDWARE_ACCEL.md`, no longer exists). The corpus stays `sample_docs` + `scale_docs`, as in the project's `scripts/reproducibility_test.py`, so these queries are misses for every state. | Matches the project's own evaluation setup. | None: identical for all states. |
| 2026-10-18 (pre-run) | §6 | Document-level means follow the project's `BenchmarkRunner` convention: all queries are included. Adversarial queries (empty gold) score RR = 0, and Hit = 1 only when nothing is returned (`eval/metrics.py`). Non-adversarial-only means are reported alongside. | Clarifies query inclusion, which §6 left implicit. | None: same rule for all states. |
| 2026-10-18 (pre-run) | §7.1 | The multi-match frequency is computed in Layer 1 for state C from each result's recorded matched-chunk spans, not from Layer 2 output. | The MCP output does not expose window internals. | RQ3 is descriptive only. |
| 2026-10-18 (pre-run) | §3 | B runs from the branch commit that adds this protocol and the harness. `git diff d524652 -- src/` must be empty, which is checked as part of V-02. | The protocol requires the harness to be committed before the first run. | None: product code is identical to `d524652`. |
| 2026-10-18 (pre-run) | §10 C-10 | GoldText rule: a suite/path fails if and only if the paired mean difference (C − B) has a 95% bootstrap CI entirely below 0. The binary rule is unchanged: net loss (b − c) ≤ 1. | The original wording ("lower 95% bound below 0 for a paired-mean decrease") was ambiguous. | Removes interpretation after the fact. |
| 2026-10-18 (pre-run) | §10 C-12 | Adversarial output rule: pass if C's mean ≤ 1.5 × B's mean **or** C's mean − B's mean ≤ 100 characters. | The ratio is undefined or unstable when B returns (almost) nothing on adversarial queries. | Keeps the intent of the bound when B ≈ 0. |
| 2026-10-18 (pre-run) | §10 C-13 | Latency is evaluated per suite and path: \|C − B\| ≤ max(5% of B, 15 ms) on Layer 2 p50. | The original wording didn't say whether latency is pooled. | Stricter; nothing is averaged away. |
| 2026-10-18 (pre-run) | §10 C-14 | `scripts/compare_benchmarks.py` has no CI; it marks 🔴 for a precision drop over 1 point. Its archived baselines were produced by CI on CPU, while all protocol runs use MPS. The CI benchmark is therefore run for A, B and C on MPS. C-14 passes if the test suite passes for B and C, and `compare_benchmarks.py` shows no 🔴 for B or C against **A's run on the same environment**. Comparisons against the archive are reported for information. | Removes the environment confound and states the rule the script actually implements. | Decisive comparison is against the same-environment baseline. |
| 2026-10-18 (pre-run) | §3.1 | In C, a result with no claimed extra span and no leftover fill is rendered by B's formatter exactly, including its `...` marker. A result with extra spans or fill appends `...` when text continues after its last rendered span. | Keeps the kill-switch identity (C-15) exact and keeps the truncation signal. | C-15 is testable byte for byte. |
| 2026-10-18 (pre-run) | §3.1 | State C = branch `feat/show-matched-passages` @ `ade2365`. Step 3 is implemented as the literal text reads: each passage first pays for its gap marker, then takes `min(span, remaining)`, and claiming stops when fewer than 120 characters of budget would remain for the next passage. A matched chunk shorter than 120 is shown whole. Extras never exceed the budget. | The wording allowed two readings. The pre-protocol simulation that motivated the proposal applied the 120 minimum to the *passage* and charged the marker *after* it. The protocol evaluates the rule as written, not the simulation. | C is pinned before any run. |
| 2026-10-18 (pre-run) | §4 | One Chroma server process per corpus is started after ingest and kept alive for every run on that corpus (A, B, C, reruns). Each run records the process identity (pid and start time). A restart voids comparisons across it, and the affected runs are repeated. | Chroma rebuilds part of the HNSW graph on every load. Across processes, precise-path neighbour sets differed in smoke tests while distances were bit-identical. | Removes index variance between compared runs. Checked under V-02. |
| 2026-10-18 (pre-run) | §4 | Layer 2 servers are started through `scripts/eval_agent_view/serve.py`, which makes Candlekeep's startup write probe (add and delete `__auth_test__`) fail before it reaches Chroma. This applies identically to A, B and C. The ingest server keeps the probe. | The probe inserts and deletes a point in the shared HNSW index on every server start, which would change the index between compared runs. | Read-only servers; search is unaffected. |
| 2026-10-18 (pre-run) | §4 | `PYTHONHASHSEED=20261018` is set for every Candlekeep process (L1, ingest and L2 servers), but not for the CI run. | Fixes hash-dependent set and dict ordering across processes. | Identical for all states. |
| 2026-10-18 (pre-run) | §4 / §11 | Each corpus is ingested with a single MCP `ingest` call. I01 and I02 ingest a staging directory of symlinks to every file in `sample_docs` and `scale_docs`. Gold sources are matched by basename. | Back-to-back ingest calls can run the embedder concurrently with the background normalisation rebuild, which crashes MPS (a pre-existing issue in A and B). Basename matching differs from the project's path matching for one Centurion gold entry (`scale_docs/microservices.md` does not exist; `sample_docs/microservices.md` does). | Identical for all states. |
| 2026-10-18 (pre-run) | §5 / §7.1 | CEN-G gold chunks are rebuilt from the product's own parsed body (`DocumentProcessor._parse_frontmatter`). Six CEN documents have invalid YAML frontmatter, which the product keeps in the body, exactly as when the labels were made (0 of 709 graded keys out of range). Gold-document text for shingle metrics still uses regex frontmatter removal. | The contract's regex body would misalign 17 gold chunks in 7 queries. | Labels now align with the annotation. |
| 2026-10-18 (pre-run) | §8 | CEN-014 and CEN-038 have empty reference answers in the fixture and are excluded from judging. CEN-A therefore has 76 queries: J1 = 228 items, J1-R ≈ 46, J2 = 152. Re-judge parts may hold fewer than 25 items. | No ground truth to judge against. | C-11 n = 76. |
| 2026-10-18 (pre-run) | §6 / §7 / §9 | Conventions adopted from the harness and verifier (both agree, cross-checked with 0 mismatches):<br>• means over empty sets are null;<br>• BEIR queries have category `beir`;<br>• the BEIR ideal DCG is cut at 10;<br>• graded nDCG@5 includes CEN-G adversarial queries;<br>• an empty normalised text has no shingles;<br>• a tool error is stored as `raw_output = ""`;<br>• C-07, C-10, C-12 and C-13 are evaluated on all three paths of every suite, including BEIR explore;<br>• RQ3 uses the hybrid path;<br>• κ is computed over the whole re-judged subset. | Points the data contract left open. | None. |
| 2026-10-18 (pre-run) | §7.2 | Finding: explore's graph expansion never adds documents in any state. It fetches chunks by `collection.get(ids=<source paths>)`, but chunk ids are hashes. The A-with-empty-graph informational row is therefore expected to equal A. | Found by the harness review. A product issue, not part of this evaluation. | None. |

## 17. Change log

- 2026-10-18 — Protocol written and frozen; no protocol runs started.
