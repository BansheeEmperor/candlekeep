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
- **Formatting reveals the state** (added after the run). A three-rule classifier recovers the state from J1 formatting alone for 97.4% of items: C's `[…]` marker, A's per-chunk `Document: … Description:` prefix, and the B/C title line. Judges were blind to labels, not to format. Their notes never refer to a system.
- **Output length in Layer 3** (added after the run). On judged items, C's output is 1.7× B's, and no length-matched B was judged. Within a state, `full` verdicts do not correlate with length. The exploratory length-matched Layer 2 runs (§16) address the deterministic metrics only.

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
| R00-A | A | 6519cc7 | venv-A | env | — | `scripts/eval_agent_view/env.py --state A` | `tests/results/agent_view_eval/env/A.txt` | — | verified | V-02 |
| R00-B | B | d524652 | venv-B | env | — | `… --state B` | `…/env/B.txt` | — | verified | V-02 |
| R00-C | C | ade2365 | venv-C | env | — | `… --state C` | `…/env/C.txt` | — | verified | V-02 |
| I01 | B | d524652 | venv-B | ingest | CEN | `ingest.py --suite CEN` | `…/ingest/I01_CEN.json` | 89 docs | verified: 2,970 chunks, 2,945 entities, 3,351 edges | V-02, V-03 |
| I02 | B | d524652 | venv-B | ingest | CEN-G (overlap 50) | `ingest.py --suite CEN --overlap 50` | `…/ingest/I02_CEN-G.json` | 89 docs | verified: 2,868 chunks, 2,939 entities, 2,906 edges | V-02, V-03 |
| I03 | B | d524652 | venv-B | ingest | CD-LEG | `ingest.py --suite CD-LEG` | `…/ingest/I03_CD-LEG.json` | 90 docs | verified: 1,520 chunks, 2,667 entities, 3,211 edges | V-02, V-03 |
| I04 | B | d524652 | venv-B | ingest | CD-MED | `… CD-MED` | `…/ingest/I04_CD-MED.json` | 91 docs | verified: 1,433 chunks, 1,734 entities, 523 edges | V-02, V-03 |
| I05 | B | d524652 | venv-B | ingest | CD-NAR | `… CD-NAR` | `…/ingest/I05_CD-NAR.json` | 89 docs | verified: 1,408 chunks, 1,535 entities, 1,009 edges | V-02, V-03 |
| I06 | B | d524652 | venv-B | ingest | CD-API | `… CD-API` | `…/ingest/I06_CD-API.json` | 95 docs | verified: 1,735 chunks, 741 entities, 1,403 edges | V-02, V-03 |
| I07 | B | d524652 | venv-B | ingest | CD-ALT | `… CD-ALT` | `…/ingest/I07_CD-ALT.json` | 88 docs | verified: 1,205 chunks, 898 entities, 394 edges | V-02, V-03 |
| I08 | B | d524652 | venv-B | ingest | BEIR-SF | `… BEIR-SF` | `…/ingest/I08_BEIR-SF.json` | 5,183 docs | verified: 19,040 chunks, 22,374 entities, 26,379 edges | V-02, V-03 |
| I09 | B | d524652 | venv-B | ingest | BEIR-NF | `… BEIR-NF` | `…/ingest/I09_BEIR-NF.json` | 3,633 docs | verified: 14,140 chunks, 17,853 entities, 26,866 edges | V-02, V-03 |
| R01 | B | d524652 | venv-B | L1+L2 | CEN (determinism, run 2) | `run_layer1.py / run_layer2.py --state B --suite CEN --tag rerun` | `…/L1/B_CEN_rerun.json`, `…/L2/B_CEN_rerun.json` | 108 | verified: identical rankings and outputs | V-01 |
| L1-A-* | A | 6519cc7 | venv-A | L1 | CEN, CEN-G, MH, CD×5, BEIR×2 | `run_layer1.py --state A --suite <s>` | `…/L1/A_<s>.json` | per §5 | verified | V-02, V-03, V-05, V-07 |
| L1-B-* | B | d524652 | venv-B | L1 | ″ | `… --state B …` | `…/L1/B_<s>.json` | per §5 | verified | V-02, V-03, V-05, V-07 |
| L1-C-* | C | ade2365 | venv-C | L1 | ″ | `… --state C …` | `…/L1/C_<s>.json` | per §5 | verified | V-02, V-03, V-05, V-07 |
| L2-A-* | A | 6519cc7 | venv-A | L2 | CEN, CEN-G, MH, CD×5, BEIR×2 | `run_layer2.py --state A --suite <s>` | `…/L2/A_<s>.json` | per §5 | verified | V-02, V-03, V-05, V-07 |
| L2-B-* | B | d524652 | venv-B | L2 | ″ | `… --state B …` | `…/L2/B_<s>.json` | per §5 | verified (first CEN-G run void: HEAD changed mid-run, repeated, §16) | V-02, V-03, V-05, V-07 |
| L2-C-* | C | ade2365 | venv-C | L2 | ″ | `… --state C …` | `…/L2/C_<s>.json` | per §5 | verified | V-02, V-03, V-05, V-07 |
| L2-C0 | C (extras = 0) | ade2365 | venv-C | L2 | CEN | `CANDLEKEEP_RESULT_EXTRA_CHARS=0 run_layer2.py --state C --suite CEN --tag killswitch` | `…/L2/C_CEN_killswitch.json` | 108 | verified: 324/324 byte-identical | V-04 |
| L2-I1 | A (empty graph) | 6519cc7 | venv-A | L2 info | CEN, MH | `run_layer2.py --state A --graph empty` | `…/L2/info_A_emptygraph_<s>.json` | 108/30 | verified | V-02, V-05 |
| L2-I2 | B (500 chars) | d524652 | venv-B | L2 info | CEN, MH | `CANDLEKEEP_RESULT_CHARS=500 run_layer2.py --state B` | `…/L2/info_B_500_<s>.json` | 108/30 | verified | V-02, V-05 |
| J1 | A/B/C | — | — | L3 | CEN-A hybrid | `judge_pack.py --pack J1` | `…/judges/pack_J1.json`, `keymap_J1.json` (SHA-256: `b93e2d6a8d2c409b85c0ffb1986fe5b52f7cef8c40b72d3968e6702c00af8725`), `out_J1_*.json` | 228 | verified | V-06 |
| J1-R | — | — | — | L3 | 20% re-judge | `judge_pack.py --pack J1R` | `…/judges/pack_J1R.json`, `keymap_J1R.json` (SHA-256: `2493f118148d3b5e52efec58bff3f0659d595ea38991141e6a439fedb95f38ab`), `out_J1R_*.json` | 46 | verified: κ 0.927 | V-06 |
| J2 (opt.) | B/C | — | — | L3 | CEN-A precise | `judge_pack.py --pack J2` | `…/judges/pack_J2.json`, `keymap_J2.json` (SHA-256: `6d75632acefdc12c4c136af5a2ad3594ad565d82d58e22d268f82af6296df5e2`), `out_J2_*.json` | 152 | verified | V-06 |
| CI-B | B | d524652 | venv-B | CI | — | `pytest -m "unit or (benchmark and not slow)"` (MPS) | `…/verification/ci_B.txt` | — | done: 240 passed (1 of 1 attempts); comparison vs A failed closed (no baseline) | verify.py C-14 |
| CI-C | C | ade2365 | venv-C | CI | — | ″ | `…/verification/ci_C.txt` | — | done: 270 passed (attempt 2 of 2; attempt 1 aborted, void); comparison vs A failed closed | verify.py C-14 |
| CI-A | A | 6519cc7 | venv-A | CI | — | ″ | `…/verification/ci_A.txt`, attempts in `…/verification/previous/` | — | failed: aborted 3 of 3 attempts (MPS race, §16) | verify.py C-14 |
| CI-info-{A,B,C} | A/B/C | — | venv-A/B/C | CI info | — | `drive.py ci --serialize-models --results-root …/ci_info` | `…/ci_info/verification/ci_<S>.*` | — | done, informational: tests pass; B and C 2 red vs A (precise) | verify.py C-14 (info) |
| EXP-* | B, C | d524652, ade2365 | venv-B/C | L2 exploratory | CEN, CEN-G, MH, CD×5 | `drive.py l2 … --result-chars 2000/3000` (B), `--extra-chars 1000/1500` (C), `--results-root …/exploratory` | `…/exploratory/L2/*.json`, `…/exploratory/summary_table.md` | 32 runs | done, exploratory (§16) | `verify.py --metrics-of` |
| V-ALL | — | — | — | verify | all | `verify.py --all --check-doc` | `…/verification/checks.json`, `…/summary.json` | — | verified: V-01 to V-09 pass | V-01 to V-09 |

## 15. Results (filled from `summary.json` after V-ALL passes)

### 15.1 Layer 1 — retrieval (values: A / B / C; Δ(B−A) with 95% CI)

| Suite | Path | MRR@5 | nDCG@5 | Hit@1 | Hit@5 | P@5 | Graded nDCG@5 | Adv. leak | Latency p50 (ms) | Ranking identical C=B | Source JSON |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CEN | hybrid | 0.534 / 0.534 / 0.534; Δ +0.000 [+0.000, +0.000] | 0.554 / 0.554 / 0.554; Δ +0.000 [+0.000, +0.000] | 0.491 / 0.491 / 0.491; Δ +0.000 [+0.000, +0.000] | 0.602 / 0.602 / 0.602; Δ +0.000 [+0.000, +0.000] | 0.460 / 0.460 / 0.460; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 37.3 / 38.2 / 37.0; B/A 1.023 | 108/108 | `L1/{A,B,C}_CEN.json` |
| CEN | precise | 0.515 / 0.522 / 0.522; Δ +0.007 [-0.002, +0.019] | 0.522 / 0.530 / 0.530; Δ +0.008 [+0.000, +0.021] | 0.685 / 0.685 / 0.685; Δ +0.000 [-0.037, +0.037] | 0.722 / 0.722 / 0.722; Δ +0.000 [-0.037, +0.037] | 0.578 / 0.573 / 0.573; Δ -0.005 [-0.037, +0.026] | — | 10 / 11 / 11 (of 30) | 37.4 / 37.2 / 38.5; B/A 0.996 | 108/108 | ″ |
| CEN | explore | 0.525 / 0.525 / 0.525; Δ +0.000 [+0.000, +0.000] | 0.538 / 0.538 / 0.538; Δ +0.000 [+0.000, +0.000] | 0.491 / 0.491 / 0.491; Δ +0.000 [+0.000, +0.000] | 0.574 / 0.574 / 0.574; Δ +0.000 [+0.000, +0.000] | 0.496 / 0.496 / 0.496; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 23.0 / 23.1 / 23.3; B/A 1.002 | 108/108 | ″ |
| CEN-G | hybrid | — | — | — | — | — | 0.466 / 0.466 / 0.466; Δ +0.000 [+0.000, +0.000] | — | — | 108/108 | `L1/{A,B,C}_CEN-G.json` |
| CEN-G | precise | — | — | — | — | — | 0.384 / 0.375 / 0.375; Δ -0.009 [-0.019, -0.001] | — | — | 108/108 | ″ |
| CEN-G | explore | — | — | — | — | — | 0.368 / 0.368 / 0.368; Δ +0.000 [+0.000, +0.000] | — | — | 108/108 | ″ |
| MH | hybrid | SupportAll@5: 0.133 / 0.133 / 0.133; Δ +0.000 [+0.000, +0.000] | 0.499 / 0.499 / 0.499; Δ +0.000 [+0.000, +0.000] | 0.567 / 0.567 / 0.567; Δ +0.000 [+0.000, +0.000] | 0.900 / 0.900 / 0.900; Δ +0.000 [+0.000, +0.000] | 0.440 / 0.440 / 0.440; Δ +0.000 [+0.000, +0.000] | — | — | 58.3 / 58.6 / 58.2; B/A 1.004 | 30/30 | `L1/{A,B,C}_MH.json` |
| MH | precise | SupportAll@5: 0.067 / 0.033 / 0.033; Δ -0.033 [-0.100, +0.000] | 0.425 / 0.409 / 0.409; Δ -0.016 [-0.040, +0.001] | 0.533 / 0.533 / 0.533; Δ +0.000 [+0.000, +0.000] | 0.800 / 0.767 / 0.767; Δ -0.033 [-0.100, +0.000] | 0.463 / 0.463 / 0.463; Δ +0.000 [-0.027, +0.027] | — | — | 66.9 / 65.9 / 66.1; B/A 0.986 | 30/30 | ″ |
| MH | explore | SupportAll@5: 0.067 / 0.067 / 0.067; Δ +0.000 [+0.000, +0.000] | 0.433 / 0.433 / 0.433; Δ +0.000 [+0.000, +0.000] | 0.567 / 0.567 / 0.567; Δ +0.000 [+0.000, +0.000] | 0.833 / 0.833 / 0.833; Δ +0.000 [+0.000, +0.000] | 0.513 / 0.513 / 0.513; Δ +0.000 [+0.000, +0.000] | — | — | 33.6 / 33.8 / 33.9; B/A 1.006 | 30/30 | ″ |
| CD-LEG | hybrid | 0.678 / 0.678 / 0.678; Δ +0.000 [+0.000, +0.000] | 0.686 / 0.686 / 0.686; Δ +0.000 [+0.000, +0.000] | 0.664 / 0.664 / 0.664; Δ +0.000 [+0.000, +0.000] | 0.701 / 0.701 / 0.701; Δ +0.000 [+0.000, +0.000] | 0.536 / 0.536 / 0.536; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 33.7 / 33.8 / 33.3; B/A 1.003 | 107/107 | `L1/{A,B,C}_CD-LEG.json` |
| CD-LEG | precise | 0.687 / 0.687 / 0.687; Δ +0.000 [-0.014, +0.014] | 0.688 / 0.688 / 0.688; Δ +0.000 [-0.010, +0.010] | 0.953 / 0.953 / 0.953; Δ +0.000 [-0.028, +0.028] | 0.963 / 0.963 / 0.963; Δ +0.000 [+0.000, +0.000] | 0.553 / 0.563 / 0.563; Δ +0.010 [+0.000, +0.025] | — | 1 / 1 / 1 (of 30) | 34.6 / 34.5 / 35.0; B/A 0.994 | 107/107 | ″ |
| CD-LEG | explore | 0.671 / 0.671 / 0.671; Δ +0.000 [+0.000, +0.000] | 0.675 / 0.675 / 0.675; Δ +0.000 [+0.000, +0.000] | 0.664 / 0.664 / 0.664; Δ +0.000 [+0.000, +0.000] | 0.682 / 0.682 / 0.682; Δ +0.000 [+0.000, +0.000] | 0.662 / 0.662 / 0.662; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 20.5 / 20.3 / 20.5; B/A 0.995 | 107/107 | ″ |
| CD-MED | hybrid | 0.692 / 0.692 / 0.692; Δ +0.000 [+0.000, +0.000] | 0.696 / 0.696 / 0.696; Δ +0.000 [+0.000, +0.000] | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.704 / 0.704 / 0.704; Δ +0.000 [+0.000, +0.000] | 0.412 / 0.412 / 0.412; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 33.8 / 34.3 / 34.7; B/A 1.016 | 108/108 | `L1/{A,B,C}_CD-MED.json` |
| CD-MED | precise | 0.685 / 0.679 / 0.679; Δ -0.006 [-0.022, +0.006] | 0.695 / 0.688 / 0.688; Δ -0.007 [-0.018, +0.001] | 0.926 / 0.898 / 0.898; Δ -0.028 [-0.065, +0.000] | 0.972 / 0.963 / 0.963; Δ -0.009 [-0.028, +0.000] | 0.523 / 0.516 / 0.516; Δ -0.007 [-0.027, +0.005] | — | 2 / 3 / 3 (of 30) | 35.9 / 35.6 / 35.7; B/A 0.992 | 108/108 | ″ |
| CD-MED | explore | 0.690 / 0.690 / 0.690; Δ +0.000 [+0.000, +0.000] | 0.691 / 0.691 / 0.691; Δ +0.000 [+0.000, +0.000] | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.694 / 0.694 / 0.694; Δ +0.000 [+0.000, +0.000] | 0.645 / 0.645 / 0.645; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 19.6 / 19.9 / 19.9; B/A 1.012 | 108/108 | ″ |
| CD-NAR | hybrid | 0.675 / 0.675 / 0.675; Δ +0.000 [+0.000, +0.000] | 0.689 / 0.689 / 0.689; Δ +0.000 [+0.000, +0.000] | 0.648 / 0.648 / 0.648; Δ +0.000 [+0.000, +0.000] | 0.722 / 0.722 / 0.722; Δ +0.000 [+0.000, +0.000] | 0.516 / 0.516 / 0.516; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 33.3 / 33.4 / 33.4; B/A 1.005 | 108/108 | `L1/{A,B,C}_CD-NAR.json` |
| CD-NAR | precise | 0.660 / 0.656 / 0.656; Δ -0.005 [-0.014, +0.000] | 0.663 / 0.660 / 0.660; Δ -0.003 [-0.010, +0.000] | 0.935 / 0.926 / 0.926; Δ -0.009 [-0.028, +0.000] | 0.944 / 0.944 / 0.944; Δ +0.000 [+0.000, +0.000] | 0.577 / 0.576 / 0.576; Δ -0.001 [-0.013, +0.008] | — | 0 / 0 / 0 (of 30) | 34.6 / 33.9 / 33.9; B/A 0.981 | 108/108 | ″ |
| CD-NAR | explore | 0.663 / 0.663 / 0.663; Δ +0.000 [+0.000, +0.000] | 0.670 / 0.670 / 0.670; Δ +0.000 [+0.000, +0.000] | 0.648 / 0.648 / 0.648; Δ +0.000 [+0.000, +0.000] | 0.685 / 0.685 / 0.685; Δ +0.000 [+0.000, +0.000] | 0.627 / 0.627 / 0.627; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 19.9 / 20.1 / 19.9; B/A 1.010 | 108/108 | ″ |
| CD-API | hybrid | 0.612 / 0.612 / 0.612; Δ +0.000 [+0.000, +0.000] | 0.621 / 0.621 / 0.621; Δ +0.000 [+0.000, +0.000] | 0.583 / 0.583 / 0.583; Δ +0.000 [+0.000, +0.000] | 0.648 / 0.648 / 0.648; Δ +0.000 [+0.000, +0.000] | 0.510 / 0.510 / 0.510; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 29.5 / 29.8 / 29.7; B/A 1.011 | 108/108 | `L1/{A,B,C}_CD-API.json` |
| CD-API | precise | 0.599 / 0.599 / 0.599; Δ +0.000 [-0.014, +0.014] | 0.609 / 0.609 / 0.609; Δ +0.000 [-0.010, +0.010] | 0.852 / 0.852 / 0.852; Δ +0.000 [-0.028, +0.028] | 0.907 / 0.907 / 0.907; Δ +0.000 [+0.000, +0.000] | 0.608 / 0.612 / 0.612; Δ +0.004 [-0.002, +0.011] | — | 0 / 0 / 0 (of 30) | 28.2 / 28.4 / 28.2; B/A 1.007 | 108/108 | ″ |
| CD-API | explore | 0.596 / 0.596 / 0.596; Δ +0.000 [+0.000, +0.000] | 0.600 / 0.600 / 0.600; Δ +0.000 [+0.000, +0.000] | 0.583 / 0.583 / 0.583; Δ +0.000 [+0.000, +0.000] | 0.611 / 0.611 / 0.611; Δ +0.000 [+0.000, +0.000] | 0.578 / 0.578 / 0.578; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 19.5 / 19.9 / 19.8; B/A 1.021 | 108/108 | ″ |
| CD-ALT | hybrid | 0.568 / 0.568 / 0.568; Δ +0.000 [+0.000, +0.000] | 0.585 / 0.585 / 0.585; Δ +0.000 [+0.000, +0.000] | 0.538 / 0.538 / 0.538; Δ +0.000 [+0.000, +0.000] | 0.625 / 0.625 / 0.625; Δ +0.000 [+0.000, +0.000] | 0.324 / 0.324 / 0.324; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 34.8 / 35.2 / 35.2; B/A 1.012 | 104/104 | `L1/{A,B,C}_CD-ALT.json` |
| CD-ALT | precise | 0.540 / 0.548 / 0.548; Δ +0.008 [-0.011, +0.029] | 0.550 / 0.555 / 0.555; Δ +0.006 [-0.008, +0.021] | 0.683 / 0.692 / 0.692; Δ +0.010 [-0.029, +0.048] | 0.750 / 0.740 / 0.740; Δ -0.010 [-0.029, +0.000] | 0.447 / 0.439 / 0.439; Δ -0.008 [-0.029, +0.003] | — | 12 / 13 / 13 (of 30) | 52.8 / 51.1 / 49.9; B/A 0.969 | 104/104 | ″ |
| CD-ALT | explore | 0.560 / 0.560 / 0.560; Δ +0.000 [+0.000, +0.000] | 0.574 / 0.574 / 0.574; Δ +0.000 [+0.000, +0.000] | 0.538 / 0.538 / 0.538; Δ +0.000 [+0.000, +0.000] | 0.606 / 0.606 / 0.606; Δ +0.000 [+0.000, +0.000] | 0.527 / 0.527 / 0.527; Δ +0.000 [+0.000, +0.000] | — | 30 / 30 / 30 (of 30) | 19.6 / 19.6 / 19.7; B/A 1.000 | 104/104 | ″ |
| CD pooled | hybrid | 0.645 / 0.645 / 0.645; Δ +0.000 [+0.000, +0.000] | 0.656 / 0.656 / 0.656; Δ +0.000 [+0.000, +0.000] | 0.624 / 0.624 / 0.624; Δ +0.000 [+0.000, +0.000] | 0.680 / 0.680 / 0.680; Δ +0.000 [+0.000, +0.000] | 0.460 / 0.460 / 0.460; Δ +0.000 [+0.000, +0.000] | — | 150 / 150 / 150 (of 150) | 33.0 / 33.1 / 33.2; B/A 1.002 | 535/535 | `L1/{A,B,C}_CD-*.json` |
| CD pooled | precise | 0.635 / 0.634 / 0.634; Δ -0.001 [-0.007, +0.006] | 0.642 / 0.641 / 0.641; Δ -0.001 [-0.006, +0.004] | 0.871 / 0.865 / 0.865; Δ -0.006 [-0.019, +0.007] | 0.908 / 0.905 / 0.905; Δ -0.004 [-0.009, +0.000] | 0.542 / 0.542 / 0.542; Δ +0.000 [-0.007, +0.005] | — | 15 / 17 / 17 (of 150) | 35.5 / 35.5 / 35.6; B/A 0.998 | 535/535 | ″ |
| CD pooled | explore | 0.637 / 0.637 / 0.637; Δ +0.000 [+0.000, +0.000] | 0.643 / 0.643 / 0.643; Δ +0.000 [+0.000, +0.000] | 0.624 / 0.624 / 0.624; Δ +0.000 [+0.000, +0.000] | 0.656 / 0.656 / 0.656; Δ +0.000 [+0.000, +0.000] | 0.608 / 0.608 / 0.608; Δ +0.000 [+0.000, +0.000] | — | 150 / 150 / 150 (of 150) | 19.8 / 20.0 / 20.0; B/A 1.006 | 535/535 | ″ |
| BEIR-SF | hybrid | nDCG@10: 0.598 / 0.598 / 0.598; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.730 / 0.730 / 0.730; Δ +0.000 [+0.000, +0.000] | 0.487 / 0.487 / 0.487; Δ +0.000 [+0.000, +0.000] | 0.653 / 0.653 / 0.653; Δ +0.000 [+0.000, +0.000] | 0.145 / 0.145 / 0.145; Δ +0.000 [+0.000, +0.000] | — | — | 110.3 / 111.1 / 110.6; B/A 1.008 | 300/300 | `L1/{A,B,C}_BEIR-SF.json` |
| BEIR-SF | precise | nDCG@10: 0.606 / 0.612 / 0.612; Δ +0.006 [-0.007, +0.021] | Recall@10: 0.689 / 0.693 / 0.693; Δ +0.004 [-0.009, +0.018] | 0.520 / 0.530 / 0.530; Δ +0.010 [-0.017, +0.033] | 0.670 / 0.673 / 0.673; Δ +0.003 [-0.017, +0.023] | 0.151 / 0.151 / 0.151; Δ +0.000 [-0.004, +0.005] | — | — | 166.0 / 164.3 / 164.8; B/A 0.990 | 300/300 | ″ |
| BEIR-NF | hybrid | nDCG@10: 0.303 / 0.303 / 0.303; Δ +0.000 [+0.000, +0.000] | Recall@10: 0.147 / 0.147 / 0.147; Δ +0.000 [+0.000, +0.000] | 0.427 / 0.427 / 0.427; Δ +0.000 [+0.000, +0.000] | 0.628 / 0.628 / 0.628; Δ +0.000 [+0.000, +0.000] | 0.313 / 0.313 / 0.313; Δ +0.000 [+0.000, +0.000] | — | — | 83.9 / 83.5 / 83.8; B/A 0.995 | 323/323 | `L1/{A,B,C}_BEIR-NF.json` |
| BEIR-NF | precise | nDCG@10: 0.291 / 0.293 / 0.293; Δ +0.002 [-0.002, +0.006] | Recall@10: 0.132 / 0.130 / 0.130; Δ -0.002 [-0.006, +0.001] | 0.464 / 0.467 / 0.467; Δ +0.003 [-0.019, +0.025] | 0.601 / 0.604 / 0.604; Δ +0.003 [-0.019, +0.022] | 0.332 / 0.338 / 0.338; Δ +0.005 [-0.003, +0.013] | — | — | 121.2 / 120.5 / 120.7; B/A 0.994 | 323/323 | ″ |

### 15.2 Layer 2 — agent-visible (values: A / B / C; McNemar b, c, p for C vs B)

| Suite | Path | Primary visibility (GPV / SupportVisible / GoldText) | GPC | GoldShare | Chars/q mean (p95) | Adv. chars/q | Latency p50 | Multi-match freq. | Source JSON |
|---|---|---|---|---|---|---|---|---|---|
| CEN-G | hybrid | GPV 0.836 / 0.791 / 0.970 (n=67); b=0, c=12, p=0.0005 | 0.284 / 0.428 / 0.684; Δ(C−B) +0.256 [+0.189, +0.326] | 0.642 / 0.649 / 0.657 | 2048 (2829) / 3031 (4588) / 4733 (6723); C/B 1.561 | 2658 / 3763 / 4908; C/B 1.304, C−B +1146 | 43.5 / 42.5 / 43.2; C−B +0.7 | 0.600 (241/402) | `L2/{A,B,C}_CEN-G.json` |
| CEN-G | precise | GPV 0.731 / 0.657 / 0.881 (n=67); b=0, c=15, p=0.0001 | 0.228 / 0.307 / 0.633; Δ(C−B) +0.326 [+0.256, +0.400] | 0.564 / 0.575 / 0.626 | 1242 (2826) / 1913 (4417) / 3416 (6624); C/B 1.786 | 570 / 955 / 1424; C/B 1.490, C−B +469 | 42.8 / 43.1 / 44.0; C−B +0.9 | 0.700 (168/240) | ″ |
| CEN-G | explore | GPV 0.731 / 0.776 / 0.851 (n=67); b=0, c=5, p=0.0625 | 0.239 / 0.424 / 0.493; Δ(C−B) +0.068 [+0.031, +0.112] | 0.689 / 0.686 / 0.683 | 1970 (2816) / 2760 (3818) / 3321 (4742); C/B 1.203 | 2340 / 3075 / 3318; C/B 1.079, C−B +243 | 27.6 / 27.4 / 27.8; C−B +0.4 | 0.248 (96/387) | ″ |
| MH | hybrid | SupportVisible 0.067 / 0.100 / 0.133 (n=30); b=0, c=1, p=1.0000 | — | 0.442 / 0.464 / 0.506 | 2773 (2833) / 4226 (5239) / 5770 (7003); C/B 1.365 | — | 62.4 / 63.8 / 63.1; C−B -0.7 | 0.540 (81/150) | `L2/{A,B,C}_MH.json` |
| MH | precise | SupportVisible 0.033 / 0.033 / 0.033 (n=30); b=0, c=0, p=1.0000 | — | 0.463 / 0.465 / 0.475 | 2539 (2839) / 3978 (5040) / 5900 (6955); C/B 1.483 | — | 70.9 / 70.6 / 69.6; C−B -0.9 | 0.596 (81/136) | ″ |
| MH | explore | SupportVisible 0.033 / 0.067 / 0.067 (n=30); b=0, c=0, p=1.0000 | — | 0.519 / 0.528 / 0.549 | 2054 (2825) / 3104 (4337) / 3521 (5047); C/B 1.134 | — | 37.9 / 37.6 / 37.6; C−B +0.0 | 0.252 (28/111) | ″ |
| CEN | hybrid | GoldText 7.86 / 44.05 / 78.90; Δ(C−B) +34.85 [+28.97, +40.77] | — | 0.638 / 0.651 / 0.661 | 2050 (2827) / 2998 (4591) / 4712 (6751); C/B 1.571 | 2645 / 3750 / 4882; C/B 1.302, C−B +1131 | 41.2 / 42.1 / 41.8; C−B -0.3 | 0.623 (250/401) | `L2/{A,B,C}_CEN.json` |
| CEN | precise | GoldText 6.28 / 32.82 / 68.18; Δ(C−B) +35.36 [+29.19, +41.51] | — | 0.574 / 0.588 / 0.637 | 1292 (2829) / 1925 (4533) / 3469 (6810); C/B 1.802 | 574 / 787 / 1340; C/B 1.702, C−B +553 | 42.0 / 42.2 / 41.0; C−B -1.2 | 0.715 (176/246) | ″ |
| CEN | explore | GoldText 10.24 / 49.13 / 64.29; Δ(C−B) +15.17 [+10.76, +19.96] | — | 0.686 / 0.685 / 0.683 | 1910 (2814) / 2739 (4192) / 3257 (4519); C/B 1.189 | 2213 / 2986 / 3305; C/B 1.107, C−B +319 | 26.9 / 26.8 / 27.0; C−B +0.2 | 0.275 (103/374) | ″ |
| CD-LEG | hybrid | GoldText 8.23 / 33.10 / 90.74; Δ(C−B) +57.64 [+53.25, +61.42] | — | 0.745 / 0.759 / 0.839 | 1473 (2865) / 2465 (5247) / 4578 (7192); C/B 1.858 | 2494 / 4123 / 6028; C/B 1.462, C−B +1905 | 37.7 / 37.2 / 37.6; C−B +0.4 | 0.670 (185/276) | `L2/{A,B,C}_CD-LEG.json` |
| CD-LEG | precise | GoldText 7.81 / 29.87 / 86.31; Δ(C−B) +56.44 [+51.56, +60.75] | — | 0.392 / 0.412 / 0.600 | 1467 (2873) / 2429 (5229) / 4076 (7418); C/B 1.678 | 36 / 52 / 124; C/B 2.374, C−B +72 | 39.2 / 38.5 / 38.7; C−B +0.2 | 0.772 (207/268) | ″ |
| CD-LEG | explore | GoldText 13.38 / 49.17 / 93.92; Δ(C−B) +44.75 [+39.22, +50.12] | — | 0.920 / 0.919 / 0.916 | 1463 (2303) / 2370 (4172) / 3574 (4989); C/B 1.508 | 2131 / 3456 / 4158; C/B 1.203, C−B +701 | 23.9 / 24.0 / 24.1; C−B +0.1 | 0.485 (133/274) | ″ |
| CD-MED | hybrid | GoldText 8.03 / 29.09 / 84.97; Δ(C−B) +55.88 [+52.18, +59.28] | — | 0.571 / 0.594 / 0.755 | 1709 (2880) / 2595 (4682) / 4584 (6768); C/B 1.767 | 2565 / 3628 / 5049; C/B 1.392, C−B +1421 | 40.2 / 39.4 / 39.0; C−B -0.4 | 0.597 (197/330) | `L2/{A,B,C}_CD-MED.json` |
| CD-MED | precise | GoldText 8.04 / 28.10 / 87.33; Δ(C−B) +59.23 [+55.79, +62.26] | — | 0.365 / 0.371 / 0.607 | 1507 (2887) / 2419 (4932) / 4099 (7153); C/B 1.694 | 73 / 158 / 366; C/B 2.312, C−B +208 | 40.3 / 40.1 / 39.7; C−B -0.4 | 0.737 (207/281) | ″ |
| CD-MED | explore | GoldText 11.96 / 44.88 / 86.95; Δ(C−B) +42.06 [+36.69, +47.38] | — | 0.893 / 0.899 / 0.908 | 1489 (2826) / 2183 (3821) / 3191 (4288); C/B 1.462 | 2286 / 3060 / 3338; C/B 1.091, C−B +278 | 24.0 / 23.6 / 23.8; C−B +0.2 | 0.449 (129/287) | ″ |
| CD-NAR | hybrid | GoldText 8.42 / 31.13 / 88.62; Δ(C−B) +57.49 [+52.88, +61.54] | — | 0.713 / 0.713 / 0.799 | 1599 (2860) / 2505 (4782) / 4391 (6839); C/B 1.753 | 2587 / 3735 / 4730; C/B 1.266, C−B +995 | 37.3 / 37.7 / 37.9; C−B +0.2 | 0.589 (182/309) | `L2/{A,B,C}_CD-NAR.json` |
| CD-NAR | precise | GoldText 6.92 / 26.71 / 82.18; Δ(C−B) +55.47 [+50.49, +59.91] | — | 0.419 / 0.426 / 0.626 | 1272 (2855) / 2045 (4873) / 3631 (7055); C/B 1.775 | 17 / 17 / 17; C/B 1.000, C−B +0 | 38.4 / 37.6 / 38.4; C−B +0.8 | 0.807 (192/238) | ″ |
| CD-NAR | explore | GoldText 10.37 / 39.58 / 79.69; Δ(C−B) +40.12 [+34.86, +45.42] | — | 0.867 / 0.867 / 0.876 | 1452 (2852) / 2186 (4254) / 3210 (4398); C/B 1.469 | 2322 / 3283 / 3524; C/B 1.073, C−B +241 | 23.7 / 23.8 / 23.9; C−B +0.1 | 0.425 (119/280) | ″ |
| CD-API | hybrid | GoldText 2.38 / 26.32 / 53.04; Δ(C−B) +26.72 [+23.00, +30.45] | — | 0.711 / 0.737 / 0.768 | 1325 (2815) / 1828 (3663) / 3495 (5190); C/B 1.912 | 2185 / 2643 / 3631; C/B 1.374, C−B +988 | 33.2 / 33.2 / 33.2; C−B +0.0 | 0.677 (178/263) | `L2/{A,B,C}_CD-API.json` |
| CD-API | precise | GoldText 2.23 / 25.83 / 50.65; Δ(C−B) +24.82 [+21.49, +28.04] | — | 0.461 / 0.500 / 0.642 | 1096 (2822) / 1608 (3806) / 3169 (5896); C/B 1.970 | 17 / 17 / 17; C/B 1.000, C−B +0 | 31.7 / 31.2 / 31.5; C−B +0.3 | 0.751 (157/209) | ″ |
| CD-API | explore | GoldText 4.51 / 26.29 / 36.23; Δ(C−B) +9.94 [+6.64, +13.71] | — | 0.802 / 0.810 / 0.812 | 1345 (2704) / 1594 (2794) / 1948 (2984); C/B 1.222 | 2058 / 2292 / 2425; C/B 1.058, C−B +132 | 23.0 / 23.2 / 23.3; C−B +0.2 | 0.434 (115/265) | ″ |
| CD-ALT | hybrid | GoldText 9.23 / 26.64 / 68.18; Δ(C−B) +41.54 [+35.14, +47.76] | — | 0.455 / 0.498 / 0.612 | 2156 (2852) / 2730 (4070) / 4210 (6075); C/B 1.542 | 2795 / 3601 / 4269; C/B 1.186, C−B +669 | 39.9 / 39.0 / 39.7; C−B +0.8 | 0.459 (186/405) | `L2/{A,B,C}_CD-ALT.json` |
| CD-ALT | precise | GoldText 9.51 / 28.36 / 69.88; Δ(C−B) +41.51 [+34.92, +47.89] | — | 0.401 / 0.444 / 0.571 | 1755 (2856) / 2229 (4194) / 3643 (6377); C/B 1.635 | 798 / 1010 / 1516; C/B 1.502, C−B +506 | 57.1 / 55.6 / 54.9; C−B -0.6 | 0.668 (213/319) | ″ |
| CD-ALT | explore | GoldText 16.15 / 38.19 / 50.24; Δ(C−B) +12.05 [+7.92, +16.65] | — | 0.741 / 0.736 / 0.737 | 2123 (2839) / 2515 (3924) / 2826 (3927); C/B 1.124 | 2444 / 3044 / 3204; C/B 1.053, C−B +160 | 23.6 / 23.3 / 23.6; C−B +0.3 | 0.232 (92/397) | ″ |
| CD pooled | hybrid | GoldText 7.24 / 29.27 / 77.17; Δ(C−B) +47.89 [+45.58, +50.25] | — | 0.641 / 0.662 / 0.756 | 1649 (2863) / 2422 (4691) / 4251 (6723); C/B 1.755 | 2525 / 3546 / 4742; C/B 1.337, C−B +1195 | 37.2 / 37.2 / 37.2; C−B +0.0 | 0.586 (928/1583) | `L2/{A,B,C}_CD-*.json` |
| CD pooled | precise | GoldText 6.87 / 27.76 / 75.30; Δ(C−B) +47.54 [+45.13, +49.91] | — | 0.408 / 0.430 / 0.610 | 1417 (2871) / 2145 (4885) / 3724 (7091); C/B 1.736 | 188 / 251 / 408; C/B 1.627, C−B +157 | 39.9 / 39.9 / 39.6; C−B -0.4 | 0.742 (976/1315) | ″ |
| CD pooled | explore | GoldText 11.22 / 39.61 / 69.54; Δ(C−B) +29.93 [+27.28, +32.61] | — | 0.846 / 0.847 / 0.851 | 1570 (2836) / 2167 (3943) / 2950 (4289); C/B 1.361 | 2248 / 3027 / 3330; C/B 1.100, C−B +303 | 23.7 / 23.6 / 23.7; C−B +0.1 | 0.391 (588/1503) | ″ |
| BEIR-SF | hybrid | GoldText 7.56 / 18.62 / 35.89; Δ(C−B) +17.28 [+14.91, +19.85] | — | 0.112 / 0.112 / 0.151 | 4491 (5517) / 7125 (9714) / 8699 (11263); C/B 1.221 | — | 114.7 / 115.3 / 115.1; C−B -0.2 | 0.674 (1647/2445) | `L2/{A,B,C}_BEIR-SF.json` |
| BEIR-SF | precise | GoldText 7.39 / 18.00 / 36.53; Δ(C−B) +18.53 [+15.92, +21.31] | — | 0.085 / 0.080 / 0.116 | 5354 (5527) / 8856 (10198) / 10443 (11782); C/B 1.179 | — | 171.4 / 168.1 / 168.9; C−B +0.8 | 0.744 (2159/2903) | ″ |
| BEIR-NF | hybrid | GoldText 20.39 / 48.73 / 68.79; Δ(C−B) +20.06 [+17.35, +22.85] | — | 0.283 / 0.286 / 0.299 | 4169 (5519) / 6499 (9585) / 8107 (11154); C/B 1.248 | — | 89.5 / 89.7 / 89.0; C−B -0.7 | 0.697 (1706/2448) | `L2/{A,B,C}_BEIR-NF.json` |
| BEIR-NF | precise | GoldText 19.52 / 47.62 / 67.38; Δ(C−B) +19.76 [+17.16, +22.43] | — | 0.342 / 0.342 / 0.356 | 3799 (5529) / 6123 (10045) / 7430 (11659); C/B 1.213 | — | 127.2 / 125.7 / 125.7; C−B +0.0 | 0.778 (1708/2194) | ″ |
| Informational | A empty graph, CEN, hybrid | GoldText 7.86 (A: 7.86); Δ vs A +0.00 [+0.00, +0.00] | — | 0.638 | 2050 (2827) | 2645 | 41.6 | — | `L2/info_*.json` |
| Informational | A empty graph, CEN, precise | GoldText 6.28 (A: 6.28); Δ vs A +0.00 [+0.00, +0.00] | — | 0.574 | 1292 (2829) | 574 | 42.6 | — | ″ |
| Informational | A empty graph, CEN, explore | GoldText 10.24 (A: 10.24); Δ vs A +0.00 [+0.00, +0.00] | — | 0.686 | 1910 (2814) | 2213 | 27.0 | — | ″ |
| Informational | A empty graph, MH, hybrid | SupportVisible 0.067 (A: 0.067); vs A: b=0, c=0, p=1.0000 | — | 0.442 | 2773 (2833) | — | 62.3 | — | ″ |
| Informational | A empty graph, MH, precise | SupportVisible 0.033 (A: 0.033); vs A: b=0, c=0, p=1.0000 | — | 0.463 | 2539 (2839) | — | 69.7 | — | ″ |
| Informational | A empty graph, MH, explore | SupportVisible 0.033 (A: 0.033); vs A: b=0, c=0, p=1.0000 | — | 0.519 | 2054 (2825) | — | 36.9 | — | ″ |
| Informational | B at 500 chars, CEN, hybrid | GoldText 19.01 (A: 7.86, B: 44.05); Δ vs A +11.15 [+9.05, +13.40] | — | 0.646 | 1907 (2816) | 2459 | 42.4 | — | ″ |
| Informational | B at 500 chars, CEN, precise | GoldText 14.15 (A: 6.28, B: 32.82); Δ vs A +7.87 [+6.15, +9.69] | — | 0.583 | 1199 (2810) | 506 | 42.1 | — | ″ |
| Informational | B at 500 chars, CEN, explore | GoldText 22.62 (A: 10.24, B: 49.13); Δ vs A +12.37 [+10.12, +14.67] | — | 0.687 | 1789 (2731) | 2051 | 27.1 | — | ″ |
| Informational | B at 500 chars, MH, hybrid | SupportVisible 0.100 (A: 0.067, B: 0.100); vs A: b=0, c=1, p=1.0000 | — | 0.448 | 2632 (2826) | — | 61.4 | — | ″ |
| Informational | B at 500 chars, MH, precise | SupportVisible 0.033 (A: 0.033, B: 0.033); vs A: b=0, c=0, p=1.0000 | — | 0.467 | 2461 (2834) | — | 70.6 | — | ″ |
| Informational | B at 500 chars, MH, explore | SupportVisible 0.067 (A: 0.033, B: 0.067); vs A: b=0, c=1, p=1.0000 | — | 0.519 | 1971 (2825) | — | 37.2 | — | ″ |

### 15.3 Layer 3 — judges

| Pack | State | full | partial | none | Net vs B | B-full → not-full | κ (double-judged) | Source JSON |
|---|---|---|---|---|---|---|---|---|
| J1 (hybrid) | A | 1 | 46 | 29 | -10 | 10 | pack 0.927 (n=46, agreement 0.957); this state 0.894 (n=17) | `judges/out_J1_*.json` |
| J1 (hybrid) | B | 11 | 46 | 19 | — | — | pack 0.927 (n=46, agreement 0.957); this state 0.903 (n=18) | ″ |
| J1 (hybrid) | C | 20 | 39 | 17 | +9 | 1 | pack 0.927 (n=46, agreement 0.957); this state 1.000 (n=11) | ″ |
| J2 (precise, opt.) | B / C | 8 / 20 | 42 / 36 | 26 / 20 | +12 | 1 | not double-judged | `judges/out_J2_*.json` |

### 15.4 Criteria outcome

| ID | Result (value, CI or p) | Pass / Fail | Evidence (run IDs → JSON) | Verified (V-ids) |
|---|---|---|---|---|
| C-01 | MRR@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.007 [-0.002, +0.019], explore +0.000 [+0.000, +0.000]; nDCG@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise +0.008 [+0.000, +0.021], explore +0.000 [+0.000, +0.000]; pass if lower bound > -0.02 | Pass | L1-A-CEN, L1-B-CEN | V-01 pass, V-02 pass, V-03 pass, V-05 pass |
| C-02 | pooled MRR@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise -0.001 [-0.007, +0.006], explore +0.000 [+0.000, +0.000]; largest per-suite drop -0.006 (CD-MED precise), limit -0.03 | Pass | L1-A/B-CD-* | V-02 pass, V-03 pass, V-05 pass |
| C-03 | nDCG@10 Δ(B−A): BEIR-SF hybrid +0.000 [+0.000, +0.000], BEIR-SF precise +0.006 [-0.007, +0.021], BEIR-NF hybrid +0.000 [+0.000, +0.000], BEIR-NF precise +0.002 [-0.002, +0.006] | Pass | L1-A/B-BEIR-* | V-02 pass, V-03 pass, V-05 pass |
| C-04 | graded nDCG@5 Δ(B−A): hybrid +0.000 [+0.000, +0.000], precise -0.009 [-0.019, -0.001], explore +0.000 [+0.000, +0.000] | Pass | L1-A/B-CEN-G | V-02 pass, V-03 pass, V-05 pass |
| C-05 | B ≤ A + 2 in every CEN/CD suite and path; largest B − A +1 (CEN precise) | Pass | L1-A/B-CEN, CD-* | V-02 pass, V-03 pass, V-05 pass |
| C-06 | L1 p50 B/A: hybrid 1.023, precise 0.996, explore 1.002; limit 1.10 | Pass | L1-A/B-CEN | V-01 pass, V-02 pass, V-03 pass, V-05 pass |
| C-07 | 0 differing of 4212 query-path pairs compared | Pass | L1-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-08 | GPV CEN-G hybrid: b=0, c=12, net +12, n=67, p=0.0005, Holm p=0.0015; superiority claimed | Pass | L2-B/C-CEN-G | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-09 | SupportVisible MH hybrid: b=0, c=1, net +1, n=30, p=1.0000, Holm p=1.0000; superiority not claimed | Pass | L2-B/C-MH | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-10 | no suite/path fails; largest binary net loss b−c +0 (MH precise); smallest GoldText upper bound +13.71 (CD-API explore) | Pass | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass, V-07 pass |
| C-11 | net C−B full +9; B-full→C-not-full 1; b=1, c=10, p=0.0117, Holm p=0.0234; κ=0.927 (n=46); superiority claimed | Pass | J1, J1-R | V-06 pass |
| C-12 | failing: CEN hybrid C/B 1.571; CEN precise C/B 1.802; CEN precise adversarial C/B 1.702, C−B 552.5; CEN-G hybrid C/B 1.561; CEN-G precise C/B 1.786; CD-LEG hybrid C/B 1.858; CD-LEG precise C/B 1.678; CD-LEG explore C/B 1.508; CD-MED hybrid C/B 1.767; CD-MED precise C/B 1.694; CD-MED precise adversarial C/B 2.312, C−B 207.8; CD-NAR hybrid C/B 1.753; CD-NAR precise C/B 1.775; CD-API hybrid C/B 1.912; CD-API precise C/B 1.970; CD-ALT hybrid C/B 1.542; CD-ALT precise C/B 1.635; CD-ALT precise adversarial C/B 1.502, C−B 506.4 | Fail | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-13 | abs(C−B) ≤ max(5% of B, 15 ms) everywhere; closest -1.2 ms of ±15.0 (CEN precise) | Pass | L2-B/C-* | V-02 pass, V-03 pass, V-05 pass |
| C-14 | pytest -m "unit or (benchmark and not slow)" on MPS: B pass, C pass; compare_benchmarks.py rule vs A's MPS run (hybrid, precise, explore): B fail (not compared: baseline fail), C fail (not compared: baseline fail) (A's baseline run: fail, exit -6); informational run, model calls serialised (not a decision): tests A pass, B pass, C pass; vs A: B 2 red (precise precision 0.874→0.823; precise recall 0.768→0.732), C 2 red (precise precision 0.874→0.823; precise recall 0.768→0.732); vs archive (information): B 1 red, C 1 red | Fail | CI-B, CI-C | — |
| C-15 | 324 of 324 outputs byte-identical | Pass | L2-C0, L2-B-CEN | V-02 pass, V-04 pass |

Decisions: RQ1 Fail (C-01 to C-06 and C-14 for B; criteria Fail); RQ2 Fail (C-07 to C-15; criteria Fail).

### 15.5 RQ3 — generality

| Suite | Multi-match frequency (C) | Δ primary visibility (C − B) | Notes |
|---|---|---|---|
| CEN | 0.623 | +34.85 | hybrid; GoldText |
| CEN-G | 0.600 | +0.179 | hybrid; GPV; GoldText Δ +34.21 |
| MH | 0.540 | +0.033 | hybrid; SupportVisible; GoldText Δ +29.30 |
| CD-LEG | 0.670 | +57.64 | hybrid; GoldText |
| CD-MED | 0.597 | +55.88 | hybrid; GoldText |
| CD-NAR | 0.589 | +57.49 | hybrid; GoldText |
| CD-API | 0.677 | +26.72 | hybrid; GoldText |
| CD-ALT | 0.459 | +41.54 | hybrid; GoldText |
| BEIR-SF | 0.674 | +17.28 | hybrid; GoldText |
| BEIR-NF | 0.697 | +20.06 | hybrid; GoldText |
| **Spearman ρ (p)** | -0.115 (p=0.7514, n=10) | | descriptive only; registered metrics |
| Spearman ρ (p), GoldText for every suite | -0.515 (p=0.1276, n=10) | | secondary, not pre-registered: one unit across suites |

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
| 2026-10-18 (run) | §11 / §13 | The first Layer 2 run of B on CEN-G was invalidated by the harness and moved to `invalid/L2/B_CEN-G.20261018T180712Z.json`, because commit `5317ba1` (documentation only: the key-map hashes) changed HEAD while it ran. `drive.py all` was restarted and repeated that run against the same Chroma process. All other outputs were kept, since `src/` and `pyproject.toml` did not change. No commits are made while a run is in progress. | The harness compares HEAD before and after every run. | None: the repeated run uses the same code, ingest and Chroma process. |
| 2026-10-18 (run) | §8 | Judges read a plain-text rendering of their pack part, `judges/pack_<P>_part<k>.txt` (`scripts/eval_agent_view/render_pack.py`), instead of the JSON part. The rendering writes each field's line breaks out between `<<<…>>>` markers; `render_pack.py --check` parses it back and requires every item to equal the JSON part's, field for field (17/17 parts identical). Each judge returns `{id, verdict, evidence[], note}` as structured output, and `out_<P>_part<k>.json` is extracted from the workflow journal without editing. | The judges' file viewer truncates lines over 2,000 characters, and a JSON part keeps each tool output on a single line of up to ~8,000. | None: same items, same content. |
| 2026-10-18 (run) | §10 C-14 | The first CI runs of A and C aborted after 4.7 s, in the first selected test (`tests/test_arcane_recall.py`), with a Metal assertion (SIGABRT, exit −6). In both, the Rosetta Seal background rebuild (`token_normalisation._rebuild_worker`) and the test's query embedded on MPS at the same time; the code is the same in A, B and C. B's first run completed (240 passed). Rule, fixed before any repeat: a CI run that aborts this way has no test outcome and is repeated, up to 3 attempts per state. A run whose tests complete and fail counts as a failure and is not repeated. Every attempt is kept under `verification/previous/`. B's comparison against A is redone with `drive.py ci --state B --compare-only` once A has router results. | The abort is a pre-existing race between two embedder users on MPS, not a test result. | C-14 is decided on completed runs; the number of aborted attempts is reported per state. |
| 2026-10-18 (run) | §10 C-14 | Outcome of the repeat rule: A aborted 3 of 3 attempts, B completed 1 of 1, and C aborted once, then completed (270 passed). A therefore has no router results, and the decisive comparison against A's run fails closed for B and C. **C-14 is reported as failed.** An informational CI run, not part of any decision, is added for A, B and C: the same command plus `-p mps_serial` (`scripts/eval_agent_view/pytest_plugins/mps_serial.py`), which makes every `SentenceTransformer.encode` and `CrossEncoder.predict` call hold one lock. It is written under `ci_info/verification/` (`drive.py ci --serialize-models --results-root tests/results/agent_view_eval/ci_info`). | A cannot complete the pre-registered command on MPS. The informational run shows whether the code changes move the project's own benchmarks once the race is removed. | C-14 fails as pre-registered; RQ1 and RQ2 cannot pass. The informational run is reported next to it, labelled as such. |
| 2026-10-18 (run) | §7.2 | Exploratory Layer 2 runs, added after the results were known and not part of any decision. B with `CANDLEKEEP_RESULT_CHARS` 2000 and 3000 (a length-matched control for C's larger output) and C with `CANDLEKEEP_RESULT_EXTRA_CHARS` 1000 and 1500 (budgets that might satisfy C-12), on CEN, CEN-G, MH and the five CD suites. They use the same code, ingests and Chroma processes, and are written to a separate results root nested at `exploratory/` (holding copies of the ingest records), which `verify.py` does not read. Their requests also appear in the corpora's Chroma logs after 19:28Z. | C-12 failed, and C's judged gain cannot be separated from its extra output without a length-matched control. | None. They inform a follow-up state C′, which would have to re-enter the protocol. |
| 2026-10-18 (run) | §8 | The J1 part 6 judge read its file, then produced no output for 30 minutes and was stopped. The workflow was resumed: the 16 finished judges were replayed from cache, and a second agent with the identical prompt judged part 6. Its verdicts are the only part 6 verdicts that exist. `journal_extract.json` lists the stopped agent as agent 1 of 2 with no result. | The agent stalled without returning. | None: no verdicts were discarded or chosen between. |
| 2026-10-18 (run) | §8 / §9 | For the 46 double-judged items, the first (J1) verdict counts toward C-11; the J1-R verdict is used only for κ. Using J1-R where available would turn CEN-004's B verdict from full to partial (b = 0). | The protocol did not say which verdict counts. | None; the alternative only strengthens C-11. |
| 2026-10-18 (run) | §11 | Layer 3 judges (18:12–18:27Z) and the J1 part 6 re-run (18:43–18:52Z) ran while protocol runs were in progress (L2 for CD-MED through BEIR-SF, and the CI repeats). Judges call a remote model and read one file each, so local load is small. | Judging started once the CEN outputs existed. | Latency (C-06, C-13) could be slightly affected for those suites. C-06 uses CEN, which had finished; C-13 passes with a margin of ≥ 13.8 ms. |
| 2026-10-18 (run) | §13 / `verify.py` | After the results were known, `verify.py` was changed in reporting only:<br>(1) A's CI baseline must itself complete (exit 0 and a pytest summary line), so an aborted baseline fails C-14 closed, as this log already stated, instead of reporting it as missing;<br>(2) a comparison that never ran prints "not compared" instead of "(0 red)";<br>(3) the informational CI run under `ci_info/` is compared with the same rule and printed next to C-14.<br>No metric or other criterion changes; `summary.json` was diffed before and after. | The verifier reported C-14 as missing and omitted the informational run, which contradicted the previous entry. | C-14 reads "fail". The RQ1 and RQ2 outcomes do not change: neither could pass either way. |
| 2026-10-18 (run) | §10 C-14 (correction) | The pre-run C-14 entry says `compare_benchmarks.py` marks a precision drop over 1 point. It marks a drop over 1 point in **precision or recall**, and the harness and verifier apply that rule. | The wording was incomplete. | None. |
| 2026-10-18 (run) | §5 / §7.1 (correction) | The pre-run CEN-G entry says the labels align with the annotation. They mostly do: commit `69172ef` (2026-03-17, after the labels were made) added setext-header splitting, so 40 of 709 graded keys (16 of grade ≥ 2, in 7 queries) now point at a neighbouring chunk's text. This is the same for A, B and C. | Found by the RQ1 audit. | C-04 is unchanged when retrieved chunks are remapped to the labelling-time chunker: −0.009 [−0.019, −0.001]. With aligned gold text, C-08 is b = 0, c = 11 (Holm p = 0.003, not c = 12): the CENG-068 flip is an artefact of the shifted label. Superiority and C-10 are unchanged. |
| 2026-10-18 (run) | §6 / §7 (conventions) | Conventions the harness and the verifier share, recorded here:<br>• GoldText and GoldShare are null, not 0, for adversarial queries;<br>• backslashes are removed only before the markdown characters `_ * [ ] ( ) # . - < >`, the backtick and the pipe;<br>• GoldShare's denominator is the text inside each result's fence, including the title line and a trailing `...`;<br>• P@5 divides by min(results, 5) and counts duplicate windows of a gold document separately (`eval/metrics.py`). | The spot checks found them unwritten. | None: the same for all states. |
| 2026-10-18 (run) | §8 / C-11 | Informational re-judging of C-11's 11 discordant queries (`scripts/eval_agent_view/rejudge_discordant.py`): CEN-004, -006, -020, -035, -044, -048, -050, -067, -074, -076 and -078. Their B and C items are re-issued as `D####` in two parts, and no part holds both states of one query. Each part is judged by two new judges with the J1 prompt. Rule, fixed before judging: an item counts as full when at least 2 of its 3 verdicts (J1 plus two new) say full, and b, c, McNemar and Holm are recomputed. Key map `judges/keymap_J1D.json`, SHA-256 `3e49d32b793a127ec66bb1157f098ddd10b3dba4d2fe66f64ba0e5e2f254137e`. | The C-11 audit found that superiority rests on single-judge verdicts, two of them borderline. | None on C-11 as registered. It reports how robust the superiority claim is. |
| 2026-10-18 (run) | §8 / C-11 (result) | Informational re-judge result: the two new judges of each part agreed on 22 of 22 items, with different notes. Under the 2-of-3 rule, CEN-004's B and CEN-006, CEN-035 and CEN-067's C lose `full`: b = 0, c = 7, McNemar p = 0.016, Holm p = 0.031 (`judges/results_J1D.json`). | Pre-registered in the previous entry. | The C-11 superiority claim holds at α = 0.05 under majority verdicts; the registered C-11 result is unchanged. |
| 2026-10-18 (run) | §12 / §13 | §12 gained two threats after the run (marked there). V-08 was carried out by three independent agents. Each recomputed every metric of its state's 30 sampled rows with its own code and read the raw outputs, and two of them also swept all of their state's rows. Their notes are compiled in `verification/spot_checks.md`. | Threats found by the audits; the spot checks needed the same rigour as V-05. | None on criteria. |
| 2026-10-19 (after the evaluation) | §5 / §13 | The evaluation found that the processor silently drops frontmatter it cannot parse. Afterwards, the quality gate was made to parse frontmatter and to check every file of a directory ingest (`244518e`). The fixture documents were repaired (`f7c2964`): 12 CEN and 21 cross-domain documents changed. The Centurion graded labels were re-pointed at the repaired chunking (`eval_suite_100.json` 1.3, `494a30d`). See `docs/RESEARCH_DIARY.md` Entry 60 for the list and the measured effect. **This evaluation's results remain tied to the fixtures and labels at `26b97ab`.** To re-verify them, run `verify.py` from a worktree at `26b97ab` with `--root tests/results/agent_view_eval --repo <repository> --b-python <repository>/.venv/bin/python`; this reproduces `summary.json` exactly (checked: 0 differences). With the repaired fixtures, V-03 and V-05 fail by construction. A harness re-run would ingest different corpora: through MCP, the gate now also skips 11 BEIR documents under 50 words. | Repairs prompted by the evaluation's findings. | None on the recorded results. |

## 17. Change log

- 2026-10-18 — Protocol written and frozen; no protocol runs started.
- 2026-10-18 — Protocol executed. §14 and §15 filled from `summary.json` (V-01 to V-09 pass), run entries and corrections added to §16, two threats added to §12.
- 2026-10-19 — Fixtures repaired and graded labels re-pointed after the evaluation (§16, last entry); the recorded results stay tied to `26b97ab`.
