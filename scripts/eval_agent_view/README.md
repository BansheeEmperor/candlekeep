# Agent-view evaluation harness

Harness for the pre-registered protocol in
[`docs/AGENT_VIEW_EVALUATION.md`](../../docs/AGENT_VIEW_EVALUATION.md). The protocol
is frozen and authoritative; this directory implements its Sections 4 to 11.
`verify.py` (Section 13) is written separately and does not import this code.

| File | Role |
|---|---|
| `common.py` | Registries (states, corpora, suites), query records, normalisation, shingles, output parsing, gold text, CEN-G gold chunks, Layer 1/2 metrics, ingest identity, provenance, Chroma process identity, pre-flight check, process/MCP helpers |
| `env.py` | Environment manifest of one state (R00) |
| `ingest.py` | Ingest one corpus once, with a single MCP `ingest` call, through state B's server (I01-I09) |
| `run_layer1.py` | Layer 1: in-process retrieval with the state's own code |
| `serve.py` | Layer 2 server launcher: candlekeep's startup write probe never reaches Chroma |
| `run_layer2.py` | Layer 2: raw `search` tool output through MCP, fixed FastMCP 3 client |
| `judge_pack.py` | Layer 3: blind judge packs, key maps, unblinding |
| `drive.py` | Runs every step with the right venv, ports and environment |
| `answer_spans.py` | Exploratory: answer facts in the result vs shown to the agent (CEN-A; fixture `tests/fixtures/cen_answer_spans.json`, research diary Entry 63) |
| `rounds/r2.json` | Everything round 2 changes (results root, EVAL_HOME, ports, states, document counts, CI plugins, informational runs); see "Rounds" |

## Layout

```
EVAL_HOME = ~/.cache/candlekeep-eval        (override with CK_EVAL_HOME)
  worktrees/A   detached at 6519cc7          venvs/A  (FastMCP 2.14.5)
  worktrees/C   branch feat/show-matched-passages   venvs/C
  data/<I0x>/chroma    Chroma server data of corpus I0x
  data/<I0x>/ck_data   candlekeep data dir (graph.db, normalisation map)
  data/<I0x>/ingest_marker.json   ingest_uuid of the ingest that built this data
  data/<I0x>/ck_data_emptygraph   copy with an empty entity_cooccurrence table (A-as-shipped row)
  staging/I01/, staging/I02/      one symlink per file of sample_docs and scale_docs (the single ingest call's directory)
  staging/<I0x>/<doc_id>.md       staged BEIR documents (I08, I09)
  scratch/   throwaway data dirs and working directories
  run/       pid files of the Chroma servers started by drive.py chroma-up (or by `all`)
State B = this checkout with .venv (FastMCP 3.4.9).

tests/results/agent_view_eval/
  env/{A,B,C}.txt
  ingest/<I0x>_<name>.json            (a failed ingest: <I0x>_<name>.failed.json)
  L1/<STATE>_<SUITE>[_<TAG>].json
  L2/<STATE>_<SUITE>[_<TAG>].json, L2/info_<STATE>_<TAG>_<SUITE>.json
  judges/pack_*.json, pack_*_part<k>.json, keymap_*.json(.sha256), manifest_*.json, out_*.json, results_*.json
  verification/preflight.json, ci_<S>.txt, ci_<S>.json, ci_<S>_router_*_benchmark.json, ci_<S>_compare_*.md
  verification/previous/ci_<S>_<stamp>/   files of an earlier CI run of S (moved, never deleted)
  superseded/<I0x>_<stamp>/   old ingest record and the outputs of a replaced ingest (ingest --force --supersede)
  invalid/L1|L2/<name>.<stamp>.json (+ .reason.txt)   outputs whose run saw a code, ingest or Chroma process change
  logs/   server logs, run logs, chroma_<I0x>.log, L2_<run>_server_env.json, L2_<run>_provenance.json,
          drive.jsonl (every step, fingerprint and write-probe checks, server and Chroma start/stop, invalid outputs)
```

Ports: Chroma for I01..I09 = 8121..8129, ingest server 8130, Layer 2 server 8131.

Round 2 (`--round rounds/r2.json`, see "Rounds") has the same layout under its own roots:

```
EVAL_HOME = ~/.cache/candlekeep-eval/r2      data/, staging/, scratch/, run/ as above
State A = worktrees/A at 6519cc7 with venvs/A (shared with round 1, read only)
State B = this checkout (src/ = 8e5846f) with .venv
State C = worktrees/Cprime at f74b23f with venvs/Cprime     (worktrees/ and venvs/ under ~/.cache/candlekeep-eval)
tests/results/agent_view_eval_r2/            env/, ingest/, L1/, L2/, judges/, verification/, ... as above
Ports: Chroma for I01..I09 = 8221..8229, ingest server 8230, Layer 2 server 8231.
```

Port 65530 must stay unused: it is the dead `CHROMA_URL` used whenever candlekeep is
imported in-process (its import starts a background thread that connects to Chroma
and write-probes it), and in the CI run. Servers bind to 127.0.0.1 only.

Corpora and suites:

| Corpus | Directories | Ingested as | Overlap | Suites |
|---|---|---|---|---|
| I01 | `tests/fixtures/sample_docs`, `scale_docs` | `staging/I01/` (89 symlinks) | 100 | CEN, MH |
| I02 | same | `staging/I02/` | 50 | CEN-G |
| I03-I07 | `tests/fixtures/cross_domain/{legal,medical,narrative,api_ref,alternating}_docs` | the directory itself | 100 | CD-LEG, CD-MED, CD-NAR, CD-API, CD-ALT |
| I08, I09 | `tests/fixtures/beir/{scifact,nfcorpus}` | `staging/<I0x>/` (staged `.md` files) | 100 | BEIR-SF, BEIR-NF (`n_results` 10) |

Every corpus is ingested with a single MCP `ingest` call on one directory (protocol
Section 16): back-to-back calls can run the embedder concurrently with the background
normalisation rebuild, which crashes MPS. For I01/I02, `ingest.py` builds
`staging/<I0x>/` with one symlink per file of the two directories (basename to
absolute target; a basename collision fails the ingest) and records the directory and
the symlink map in the ingest record (`staging.links`). Gold text and the pre-flight
check still read the fixture directories.

## Running

Run `drive.py` with venv B's python (it uses only the standard library and starts
every other step with the right interpreter):

```bash
PY=.venv/bin/python
$PY scripts/eval_agent_view/drive.py preflight          # counts and consistency -> verification/preflight.json
$PY scripts/eval_agent_view/drive.py env                # R00: env/{A,B,C}.txt
$PY scripts/eval_agent_view/drive.py ingest --corpus I01   # I01..I09; refuses existing data unless --force
$PY scripts/eval_agent_view/drive.py chroma-up --corpus I01   # the one Chroma process for every run on I01
$PY scripts/eval_agent_view/drive.py l1 --state B --suite CEN               # L1-B-CEN
$PY scripts/eval_agent_view/drive.py l1 --state B --suite CEN --tag rerun   # R01 (L1)
$PY scripts/eval_agent_view/drive.py l2 --state A --suite CEN               # L2-A-CEN
$PY scripts/eval_agent_view/drive.py l2 --state B --suite CEN --tag rerun   # R01 (L2)
$PY scripts/eval_agent_view/drive.py l2 --state C --suite CEN --extra-chars 0   # L2-C0 -> L2/C_CEN_killswitch.json
$PY scripts/eval_agent_view/drive.py l2 --state A --suite MH --graph-empty      # L2-I1 -> L2/info_A_emptygraph_MH.json
$PY scripts/eval_agent_view/drive.py l2 --state B --suite CEN --result-chars 500  # L2-I2 -> L2/info_B_500_CEN.json
$PY scripts/eval_agent_view/drive.py ci --state A       # then B and C (C-14); A first: it is their baseline
$PY scripts/eval_agent_view/drive.py ci --state B --compare-only   # redo B's comparisons (e.g. after A's run)
$PY scripts/eval_agent_view/drive.py all                # everything above, resumable, except judging and verification
$PY scripts/eval_agent_view/drive.py status
$PY scripts/eval_agent_view/drive.py chroma-down --corpus I01   # only once every run on I01 is done
$PY scripts/eval_agent_view/drive.py verify --all --check-doc   # V-ALL, see "Verification" below
```

Every command takes `--round FILE` for a later round, e.g.
`$PY scripts/eval_agent_view/drive.py all --round rounds/r2.json` (see "Rounds").

`all` ingests every corpus that has no successful ingest, then runs, for each corpus in
turn: L1 for B (plus the CEN rerun), A and C, then L2 for B (plus the CEN rerun), A, C,
the CEN kill switch and the CEN/MH informational rows; finally CI for A, B and C. It
starts each corpus's Chroma server once, before the corpus's first run that is not
skipped (an already running one is reused), never stops it, and at the end lists the
servers it leaves running with the `chroma-down` command for each. It skips an output
that already exists only if it was computed on the corpus's current ingest and with the
state's current code (see "Guards"), refuses to skip an L2 file that contains tool
errors, and stops at the first failure.

**Chroma servers.** One Chroma server process per corpus, started after its ingest,
serves every L1/L2 run on that corpus (protocol Section 16: Chroma rebuilds part of the
HNSW graph whenever it loads a collection). Only `chroma-up` (also from `all`) starts it
and only `chroma-down` stops it. `l1` and `l2` refuse to run unless it is already
running; they never start or stop it.

`l1` runs `run_layer1.py` with the state's own python. `l2` starts the state's server
as `<state venv>/bin/python scripts/eval_agent_view/serve.py` on 8131 (same environment
as the ingest server, plus `CANDLEKEEP_RESULT_CHARS` / `CANDLEKEEP_RESULT_EXTRA_CHARS`
overrides), waits until `get_stats` stops reporting loading, and fails the step unless
this server's part of its log shows serve.py's `write probe neutralised` and `blocked
Collection.add(ids=['__auth_test__'])` lines and candlekeep's `Read-only mode (write
access denied)` line, and no `Write access enabled`: proof that the probe never reached
Chroma. Only then does it add `"write_probe": "neutralised"` to the server environment
it hands to `run_layer2.py` (stored as `meta.server_env`), run `run_layer2.py` with venv
B's python, stop the server, and check that the collection's chunk-id fingerprint still
equals the one in the ingest record. The ingest server is B's `candlekeep` command and
keeps the probe.

`serve.py` wraps chromadb's `Collection.add` and `Collection.delete` before importing
candlekeep: a call whose ids are exactly the probe's (`["__auth_test__"]` or
`"__auth_test__"`, positional or `ids=`) raises
`PermissionError("evaluation server: write probe disabled")` without contacting Chroma;
every other call is unchanged. It then calls `candlekeep.mcp.server`'s `main()`
(imported with `importlib.import_module`), as the console script does, and drops its
own directory from `sys.path` first. Candlekeep only logs the result of the probe, so
search behaves as on a writable server. It works with A's FastMCP 2.14.5 and B/C's 3.4.9.

The scripts can also be run directly:

```bash
.venv/bin/python scripts/eval_agent_view/env.py --state C
.venv/bin/python scripts/eval_agent_view/ingest.py --corpus I08
~/.cache/candlekeep-eval/venvs/A/bin/python scripts/eval_agent_view/run_layer1.py --state A --suite CD-LEG
.venv/bin/python scripts/eval_agent_view/run_layer2.py --state A --suite CEN --url http://127.0.0.1:8131/mcp \
    --server-env-file tests/results/agent_view_eval/logs/L2_A_CEN_server_env.json \
    --provenance-file tests/results/agent_view_eval/logs/L2_A_CEN_provenance.json
```

Run directly, `run_layer1.py` and `run_layer2.py` still need the corpus's Chroma server
from `chroma-up`; without `CK_EVAL_CHROMA_PROCESS` they record the identity of the
running server at their own start (`meta.chroma_process_source` says so). A Layer 2
server for a direct run is started with `serve.py`, and its environment file needs
`"write_probe": "neutralised"` (otherwise `run_layer2.py` warns and `verify.py` fails
the file).

Recomputing metrics from a stored file, without searching:

```bash
.venv/bin/python scripts/eval_agent_view/run_layer1.py --recompute tests/results/agent_view_eval/L1/B_CEN.json [--check]
.venv/bin/python scripts/eval_agent_view/run_layer2.py --recompute tests/results/agent_view_eval/L2/B_CEN.json [--check]
```

Both print `{"metrics": {...}}`; `--check` compares with the stored metrics instead
(exact equality). Layer 2 needs venv B because CEN-G gold chunks are rebuilt with the
product chunker; it uses the gold body recorded in the file (`meta.cen_g_gold_body`)
unless `--gold-body product|contract` overrides it.

## Guards (ingest identity, Chroma process identity and code provenance)

* **Ingest identity.** Chunk ids are deterministic, so two ingests of a corpus have the
  same chunk-id fingerprint while their HNSW graphs differ. Every ingest therefore gets
  a fresh uuid4, `ingest_uuid`, written to the ingest record and to
  `data/<I0x>/ingest_marker.json`. `run_layer1.py` and `run_layer2.py` refuse to run
  unless the record is ok, has a uuid and the data directory's marker names the same
  uuid, and they write `ingest_id` (the run id I0x), `ingest_uuid`, `ingest_record` and
  `ingest_record_sha256` into meta. `drive.py l1` / `l2` refuse to add an output while
  any L1/L2 output of the corpus (tagged and informational ones included) carries a
  different identity, and `all` refuses to skip on such an output. `judge_pack.py
  build` refuses L2 inputs of another ingest, and `unblind` reports inputs that
  changed after the pack was built.
* **Chroma process identity.** A run's Chroma process is `{pid, started, port}`: the pid
  from the corpus's pid file (`run/chroma_<I0x>.json`, checked against the live
  `chroma run` command line and the heartbeat), its start time from
  `ps -o lstart= -p <pid>` (run with a fixed environment, C locale and `TZ=UTC`, so the
  string does not depend on the caller), and the port.
  `drive.py l1` / `l2` capture it before the run (L2: before the server starts) and pass
  it as JSON in `CK_EVAL_CHROMA_PROCESS`; `run_layer1.py` / `run_layer2.py` check it at
  their start, store it as `meta.chroma_process`, capture it again at their end as
  `meta.chroma_process_end`, and write the output to `invalid/` (exit 4) if the two
  differ. drive captures it once more after the process (L2: the server) has stopped
  and moves the output to `invalid/` unless that capture and both meta values equal the
  first one. `l1` / `l2` refuse to add an output next to outputs of the corpus (tagged
  and informational ones included) that carry another process; after a Chroma restart
  the corpus's outputs must be moved aside and those runs repeated. `status` shows the
  running process and counts outputs of another one.
* **Re-ingest.** `ingest --force` refuses while outputs of the current ingest exist
  (L1/L2 of the corpus and, for I01, the judge packs). `ingest --force --supersede`
  moves them and the old record(s) to `superseded/<I0x>_<stamp>/` before deleting the
  data. A re-ingest is a deviation to log in protocol Section 16.
* **Code provenance.** Every L1/L2 step, the ingest and the CI run refuse a checkout
  with uncommitted changes under `src/` or in `pyproject.toml`, or with a `.env` file
  (candlekeep's `config.load_dotenv` would load it into the process). For L1, drive
  captures HEAD, `HEAD:src`, `HEAD:pyproject.toml`, that status and the `.env` check
  before starting the process, and `run_layer1.py` captures them again before it imports
  candlekeep. For L2, drive captures them before starting the server and passes them to
  `run_layer2.py` (`--provenance-file`), so meta carries the values from before the
  server loaded any code. Both scripts re-check at their end, and drive re-checks after
  the process (L2: the server) has stopped. If anything changed, or the output's
  recorded SHAs differ, the output is moved to `invalid/` (exit 4 from the scripts).
  `drive.py l1` / `l2` also refuse to add an output of a state next to outputs of the
  same state computed with another `src` tree or `pyproject.toml` (a changed state is
  a new state, protocol Section 10).

## Judges (Layer 3)

```bash
.venv/bin/python scripts/eval_agent_view/judge_pack.py build --pack J1    # 228 items, 9 parts (3 of 26, 6 of 25)
.venv/bin/python scripts/eval_agent_view/judge_pack.py build --pack J1R   # round(0.2 x 228) = 46 items, 2 parts of 23, ids R0001..
.venv/bin/python scripts/eval_agent_view/judge_pack.py build --pack J2    # optional: precise, B and C, 152 items
# record judges/keymap_J1.json.sha256 in Section 14, then give each judge one pack_<P>_part<k>.json;
# the judge returns a JSON array of {id, verdict, evidence, note} as judges/out_<P>_part<k>.json.
.venv/bin/python scripts/eval_agent_view/judge_pack.py unblind --pack J1
.venv/bin/python scripts/eval_agent_view/judge_pack.py unblind --pack J1R
```

CEN-A is the 78 non-adversarial CEN queries minus CEN-014 and CEN-038, whose reference
answer is empty in the fixture (protocol Section 16): 76 queries. `build` derives the
excluded qids from the fixture, refuses unless they are exactly these two, and records
them in `manifest_<P>.json` (`excluded_qids`). J1R samples its 46 ids with
`random.Random(20261018).sample` over the sorted J1 ids and refuses unless J1 has 228.

Items are `{id, question, reference_answer, tool_output}`, with no state, path or source
labels. `unblind` checks the key-map hash, that every item was judged exactly once, the
verdict values, that evidence occurs verbatim in the tool output, and that the pack's
L2 input files are unchanged. For the verbatim check each evidence string (or each
string of an evidence list) is split on `" ... "` and every non-blank part must occur in
the tool output, apart from surrounding whitespace, quote marks or a leading/trailing
ellipsis: the rule `verify.py` applies, so both flag the same items
(`evidence_not_verbatim`; per item `evidence_not_found`). J1R items must go to judges
other than the ones who judged their J1 counterparts (`results_J1R.json` lists the
source J id of each R id).

## Verification

`verify.py` is independent of this harness. The two must apply the same CEN-G gold
body and compare the same CI paths, so run it with both stated explicitly:

```bash
.venv/bin/python scripts/eval_agent_view/verify.py --all --check-doc --gold-body product --ci-paths hybrid,precise,explore
# or, equivalently (drive passes the harness's own values and the results root):
.venv/bin/python scripts/eval_agent_view/drive.py verify --all --check-doc
```

Besides protocol Section 13, `verify.py` checks the Section 16 controls:

* V-02: every L1/L2 file records `meta.chroma_process` (`{pid, started, port}`) and an
  equal `meta.chroma_process_end`; per corpus, every protocol run of states A, B and C
  (reruns, the kill switch and the informational rows included) records the same Chroma
  process, and a mismatch fails, listing the files of each process (files the protocol
  does not name are compared too, as warnings); every L2 file records
  `server_env.write_probe = "neutralised"`.
* V-03 / V-06: the fixtures give 76 CEN-A queries (CEN-014 and CEN-038 excluded), and
  the packs hold J1 228, J1R 46 (round(0.2 x 228)) and J2 152 items.

## Rounds

A later round of the protocol compares new states on the same suites. One round file,
`rounds/<name>.json`, selects everything that differs from round 1; without `--round`
every value is round 1's. Round 2 (`rounds/r2.json`, protocol
`docs/AGENT_VIEW_EVALUATION_R2.md`):

| Key | Meaning (round 2) |
|---|---|
| `name` | shown by `status` and recorded in `verify.py`'s `summary.json` / `checks.json` |
| `results_root` | replaces `tests/results/agent_view_eval` (`tests/results/agent_view_eval_r2`) |
| `eval_home` | holds `data/`, `staging/`, `scratch/`, `run/` as EVAL_HOME does (`~/.cache/candlekeep-eval/r2`); worktrees and venvs come from `states` |
| `doc` | the protocol document whose section 15 `verify.py --check-doc` compares |
| `ports` | `chroma`: one port per corpus, all nine (8221..8229); `ingest` (8230); `l2` (8231) |
| `states` | `checkout`, `venv`, `ref`, `fastmcp` of A, B and C. A's ref is the commit checked out (6519cc7); B's is the commit whose `src/` every B output must have (8e5846f; HEAD may be a later commit that changes only docs or the harness); C's is the exact commit of C's checkout (f74b23f, required like the others; round 1 has none and reads C's SHA from `env/C.txt`, a cross-check that stays). B's checkout must be this repository (the fixtures, the project's metrics module and B's ingest provenance are read from it); B's venv becomes venv B (Chroma CLI, ingest server, the interpreter of the scripts `drive.py` starts, and `verify.py`'s default `--b-python`) |
| `corpus_documents` | expected document counts that differ from the registry (I08 5182, I09 3623: the quality gate now skips 1 SciFact and 10 NFCorpus documents under 50 words) |
| `ci_plugins` | modules of `pytest_plugins/` added with `-p` to the CI command of the listed states only (A: `mps_serial`, since A's code still crashes on MPS when two threads call a model; B and C have a model-call lock and run the command as written) |
| `info_runs` | extra informational Layer 2 runs, each `{state, result_chars, suites, refs}`: `drive.py all` runs the state with `CANDLEKEEP_RESULT_CHARS=result_chars` on each suite (`L2/info_<state>_<chars>_<suite>.json`, as `drive.py l2 --result-chars`), and `verify.py` checks it like the other informational rows and reports it next to `refs`, paired against the first (round 2: B at 1,700 on CEN, CEN-G and MH, refs C then B; R2-4) |

Paths may start with `~` or be relative to the repository root. `corpus_documents`,
`ci_plugins` and `info_runs` may be left out (none); every other key is required.

* **Selection.** Every script takes `--round FILE`: the path as given, else relative to this
  directory, so `--round rounds/r2.json` works from the repository root. `drive.py`
  forwards it, as an absolute path, to every script it starts, and `drive.py verify`
  passes it to `verify.py`. `common.apply_overrides` applies it before the smoke-test
  options, which still apply on top of it. It must follow the subcommand
  (`drive.py <step> --round FILE`): before it, `drive.py` refuses it, as it does an
  abbreviated `--round` after `verify`. An empty value, or one that names no file, is
  refused by every script and by `verify.py`: it never means round 1.
* **Checks.** The file is checked before anything runs: missing or unknown keys, refs that
  are not commit SHAs (C's included), a checkout of B other than this repository, a
  corpus without a Chroma port and plugins that are not in `pytest_plugins/` are
  refused. A run with `--round` also refuses a final configuration whose data, staging,
  scratch, run or results directory overlaps (one inside the other) round 1's data,
  staging, scratch, run or results directory, round 1's B′ results
  (`tests/results/agent_view_bprime`), any other existing `tests/results/agent_view_*`
  tree, or a checkout or venv of round 1's states or the round's (of these directories,
  only the results root and `--out` files may lie in this repository, B's checkout), or
  that uses one of round 1's ports (8121..8131) or the dead port. Existing directories
  are also compared by identity (`os.path.samefile`), so another spelling of one (its
  case, on macOS) still counts. An explicit `--out` (`common.py preflight`, `env.py`,
  `run_layer1.py`, `run_layer2.py`) must avoid the same directories. So no step of a
  round reads or writes round 1's data, results, pid files or ports. Files named as
  read-only inputs (`--recompute`, `--journal`, `verify.py --metrics-of`) are not
  restricted. The round's own results root is exempt from the rule on existing results
  trees, so two round files must never name the same one. State A's checkout and venv
  are the ones round 1 used (read only).
* **CI.** `drive.py ci` adds the state's `ci_plugins` (plus `mps_serial` with
  `--serialize-models`) with `-p` and puts `pytest_plugins/` on `PYTHONPATH`. The plugins
  come from this checkout, not the state's, so the run records each plugin file's
  SHA-256: as `plugins` and `plugin_sha256` in `ci_<S>.json` (in a round for every state,
  `[]` and `{}` without plugins; in round 1 only when there are plugins) and in a
  `# plugins:` line of the `ci_<S>.txt` header. A plugin file that changes during the
  run makes the run invalid. The CI step never touches any `tests/results/agent_view_*`
  entry of the checkout (every round's results, also one created while the run goes
  on), nor the run's own results root when it lies in the checkout's `tests/results`.
* **Verification.** `verify.py --round FILE` reads the same file with its own code (data
  only) and sets: the refs of A and B, C's commit, each state's FastMCP version and the A
  and C checkouts, the defaults of `--root`, `--doc`, `--eval-home` and `--b-python` (B's
  venv), the expected document counts, and the CI rule (a state listed in `ci_plugins`
  must have loaded exactly those plugins and no others, every other state none, and the
  run must record each plugin file's SHA-256 in its json and header; a plugin file that
  differs from the recorded SHA-256 now leaves the run unverifiable; `-k` and
  `--deselect` stay forbidden; the informational `ci_info/` run is not subject to it).
  Every other expectation (query counts, CEN-A 76 with CEN-014 and CEN-038 excluded,
  seeds, criteria C-01..C-15, rendering) is round 1's. With `--round`, `verify.py`
  refuses a `--root`, or an `--eval-home` whose `data/` or `staging/`, that overlaps round
  1's results root, the `data/`, `staging/`, `scratch/`, `run/`, `worktrees/` or `venvs/`
  of round 1's EVAL_HOME, round 1's B′ results, another existing results tree or the A or
  C checkout, whether given directly or passed on by `drive.py verify`.
* **Abbreviated options.** `--round` makes some abbreviations ambiguous, and they now fail:
  `verify.py --ro` (`--round` or `--root`), `drive.py <step> --r` (`--results-root` or
  `--round`). `drive.py verify` passes abbreviated options to `verify.py` unchanged
  instead of taking them for its own. Spell options out.

```bash
$PY scripts/eval_agent_view/drive.py status --round rounds/r2.json       # the round's states, roots and ports
$PY scripts/eval_agent_view/drive.py preflight --round rounds/r2.json
$PY scripts/eval_agent_view/drive.py all --round rounds/r2.json
$PY scripts/eval_agent_view/drive.py verify --all --check-doc --round rounds/r2.json
$PY scripts/eval_agent_view/verify.py --round scripts/eval_agent_view/rounds/r2.json --render
```

## Conventions the harness fixes

These follow the data contract. The points the contract leaves open, or words
differently, are listed so that the contract can be amended and `verify.py` checked
against them.

* **Query records.** CEN/CD categories come from the suite file, MH is `multihop`,
  BEIR is `beir`. BEIR queries are the test-qrels query ids present in `queries.jsonl`,
  in qrels order. Gold basenames that are not in the corpus (four CEN `docs/*.md`) are kept.
* **Null rule.** A mean over an empty set is `null`; counts are integers (`adv_n`,
  `adv_leak_count`, `gpv_n`, `errors` are 0 when nothing qualifies; in particular
  `gpv_n` is 0, not null, outside CEN-G, while `gpv` and `gpc` are null there).
  Per-query values are `null` where a metric does not apply. `graded_ndcg_5` averages
  every query with a non-empty `graded_chunks` (as `BenchmarkRunner` does, so CEN-G
  adversarial queries are included). `multi_match_freq` is computed for state C only.
* **Project metrics** come from `src/candlekeep/eval/metrics.py`, loaded from this
  checkout as a plain module (the file is identical in A and B; its SHA-256 is in every
  file's meta). MRR@5 uses the first 5 sources; the other functions get the full list.
* **BEIR nDCG@10** truncates the ideal DCG at 10 (standard `ndcg_cut_10`); Recall@10
  counts relevant (grade > 0) documents among the first 10 de-duplicated sources.
* **CEN-G gold chunks (pending the lead's sign-off).** Gold chunk *i* of a document is
  `DocumentProcessor._chunk_text` at chunk size 512 / overlap 50 (product code, venv B)
  of a body chosen by `common.CEN_G_GOLD_BODY`:
  * `product` (the harness default) is the body `DocumentProcessor._parse_frontmatter`
    keeps, i.e. the text the product actually chunks and indexes. The graded labels'
    indices were taken from `DocumentProcessor.process()`. For the 6 CEN documents whose
    frontmatter is not valid YAML (`cloud-storage-options`, `container-security`,
    `elasticsearch-basics`, `helm-charts`, `owasp-top-10`, `zero-trust-architecture`)
    the product keeps the frontmatter in that body.
  * `contract` is the body after the contract's frontmatter regex. With it, those 6
    documents give 2,854 instead of 2,868 corpus chunks, one graded key falls out of
    range, and 17 of the 240 gold chunks (grade 2 or more) point at different text, in
    7 non-adversarial queries (CENG-012, 013, 032, 040, 051, 060, 068).

  The pre-flight report shows both (`cen_g.by_gold_body`, `cen_g.gold_body_differences`).
  Every L2 file records the mode in `meta.cen_g_gold_body`, `--recompute` uses it, and
  `drive.py verify` passes the same mode to `verify.py`. Switching modes is a one-line
  change of `CEN_G_GOLD_BODY` and needs no rerun: GPV/GPC are recomputed from the stored
  raw outputs. The definition still needs a Section 16 entry before any run.
* **Gold-document text** (GoldText, SupportVisible) is the file content with the
  frontmatter regex removed, as the contract states.
* **Normalisation escapes.** The backslash is removed before exactly these 13
  characters: `` _ * [ ] ( ) # . - ` | < > ``. The `;` that follows `>` in the contract
  sentence separates the next step; it is not a 14th character.
* **Shingles.** An empty normalised text has no shingles (instead of the empty string,
  which would match every output). The pre-flight check reports zero empty gold texts.
* **GoldShare** is 0.0 when a query has parsed blocks but every block body is empty (the
  contract leaves 0/0 open); queries with no parsed block have no GoldShare value. No
  state's formatter emits an empty body.
* **Raw output** is the concatenated text content of the tool result. A tool error is
  stored as `raw_output: ""` with the message in `error`; `run_layer2.py` exits 3 if any
  call failed.
* **PYTHONHASHSEED = 20261018** for every candlekeep process (L1 runs, ingest and L2
  servers; not the CI run). Some product code iterates over sets of strings, so a fixed
  hash seed gives every run and every state the same iteration order.
* **Server shutdown** uses SIGINT: uvicorn re-raises the captured signal after its
  graceful shutdown, and only SIGINT then lets the interpreter finish the non-daemon
  rebuild threads (a re-raised SIGTERM kills them mid-write).
* **CI run** (`drive.py ci`): `pytest -m "unit or (benchmark and not slow)" -v -s` in the
  state's checkout with `CANDLEKEEP_DEVICE=mps`, `PYTHONPATH=<checkout>/src`, a throwaway
  `CANDLEKEEP_DATA_DIR`, and `CHROMA_URL` at the dead port. These tests need no Chroma
  server; with a reachable one, candlekeep's import-time init loads the models on MPS
  concurrently with the tests and Metal aborts the process. `compare_benchmarks.py`
  then runs for hybrid, precise and explore, the three paths the project's CI compares
  (with CI's labels), once per path for per-path red-flag counts and once combined for
  the CI-identical table:
  * against the archive (informational; the archive has no explore baseline, which the
    script, like CI, compares against zeros);
  * for B and C, against A's run in this environment, the decisive comparison of the
    C-14 deviation. It fails closed: a missing or unreadable A or current file for any
    path marks it `failed`, as does any red flag. `ci_<S>.json` holds `compare` (per
    path) and a `c14` summary. Run A first; `ci --state S --compare-only` redoes the
    comparisons later from the saved results.

  Afterwards every file under the checkout's `tests/results` is restored from a pre-run
  backup and files the run created are deleted; every `tests/results/agent_view_*` entry
  (the results of every round: `agent_view_eval`, `agent_view_bprime`, a later round's),
  and the run's own results root when it lies there, are never touched. A round file can
  add pytest plugins to a state's command (`ci_plugins`, see "Rounds"); `ci_<S>.json`
  records them as `plugins`, with their files' SHA-256 as `plugin_sha256`. A state's
  earlier CI files in `verification/` are moved to `verification/previous/`, never
  deleted.
* **Seeds.** Protocol Section 4 fixes seed 20261018 for every shuffled or sampled step,
  so all judge packs default to it; `--seed` overrides it (a deviation to log if used).
* **Ingest record** `ok` is false (and the file is written as `.failed.json`) if any tool
  call fails, if there was not exactly one `ingest` call, if the document count, chunk
  count, collection fingerprint, graph edge count or data marker disagree, or if state
  B's checkout changed during the ingest. `dirs` / `ingest_path` name the directory the
  ingest call got, `source_dirs` where the documents live, and `staging` the staging
  directory (I01/I02: `kind` "symlinks", `links` {basename: absolute target},
  `links_sha256`; BEIR: `kind` "beir", file count and content hash).

## Smoke testing

Hidden options (accepted by every script, forwarded by `drive.py`) redirect all state
to a throwaway area: `--test-config FILE` (JSON with `data_root`, `staging_root`,
`scratch_root`, `run_root`, `results_root`, `ports`, extra `corpora`/`suites` with the
`records` loader, and `states` to repoint a state's checkout or venv; venv B, which runs
Chroma, the ingest server and the scripts `drive.py` starts, stays), `--data-root DIR`,
`--results-root DIR`, `--ports chroma=N,ingest=N,l2=N`. `drive.py ci --pytest-k EXPR`
restricts the test selection. They apply on top of `--round`, and with a round the
result must still avoid the directories and ports listed under "Rounds". Example config:

```json
{"data_root": "/tmp/ck_smoke/home/data", "staging_root": "/tmp/ck_smoke/home/staging",
 "scratch_root": "/tmp/ck_smoke/home/scratch", "run_root": "/tmp/ck_smoke/home/run",
 "results_root": "/tmp/ck_smoke/results", "ports": {"ingest": 8192, "l2": 8193},
 "corpora": {"T01": {"name": "TEST", "dirs": ["/tmp/ck_smoke/docs_a", "/tmp/ck_smoke/docs_b"],
                     "chunk_overlap": 100, "chroma_port": 8191, "n_docs": 3}},
 "suites": {"TEST": {"corpus": "T01", "loader": "records", "file": "/tmp/ck_smoke/suite.json",
                     "n_results": 5, "expected_n": 3}}}
```

where `suite.json` is a list of query records in the data-contract shape. A corpus
entry's `kind` defaults to `links` (symlink staging, one ingest call) when it lists
more than one directory, else `dirs`. An entry may also replace a protocol corpus
(e.g. `"I01"`), so that the real suites run against a small corpus. Every Chroma server
of a smoke run is started by `drive.py chroma-up` (or `all`) with the same hidden
options and stopped with `drive.py chroma-down`.
