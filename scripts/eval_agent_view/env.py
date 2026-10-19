#!/usr/bin/env python3
"""Environment manifest of one code state (protocol section 11 step 1, runs R00-A/B/C).

Writes tests/results/agent_view_eval/env/<STATE>.txt (with --round FILE: env/ under the
round's results root, for the round's states) with: state, venv path, python
version, `uv pip freeze` of the venv, git SHA and `git rev-parse HEAD:src` of the
state's checkout, FastMCP version, torch MPS availability, and the snapshot
directory names of the model cache (~/.cache/candlekeep/models).

    python scripts/eval_agent_view/env.py --state A
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

_PROBE = r"""
import json, platform, sys
import importlib.metadata as md
def version(name):
    try:
        return md.version(name)
    except md.PackageNotFoundError:
        return None
out = {"python": platform.python_version(), "executable": sys.executable, "prefix": sys.prefix,
       "fastmcp": version("fastmcp"), "chromadb": version("chromadb"), "torch": version("torch"),
       "sentence-transformers": version("sentence-transformers"), "spacy": version("spacy"),
       "en-core-web-sm": version("en-core-web-sm") or version("en_core_web_sm")}
try:
    import torch
    out["mps_available"] = bool(torch.backends.mps.is_available())
    out["mps_built"] = bool(torch.backends.mps.is_built())
except Exception as e:
    out["mps_available"] = "error: %s" % e
try:
    import importlib.util
    spec = importlib.util.find_spec("candlekeep")
    out["candlekeep_origin"] = spec.origin if spec else None
except Exception as e:
    out["candlekeep_origin"] = "error: %s" % e
print(json.dumps(out))
"""


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=C.base_env(), **kw)


def model_snapshots() -> list[str]:
    lines = []
    if not C.MODELS_DIR.is_dir():
        return [f"(missing: {C.MODELS_DIR})"]
    for d in sorted(C.MODELS_DIR.glob("models--*")):
        snaps = sorted(p.name for p in (d / "snapshots").iterdir()) if (d / "snapshots").is_dir() else []
        ref = d / "refs" / "main"
        main = ref.read_text().strip() if ref.is_file() else None
        lines.append(f"{d.name}: snapshots={','.join(snaps) or '-'} refs/main={main or '-'}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--state", required=True, choices=sorted(C.STATES))
    ap.add_argument("--out", help="output path (default env/<STATE>.txt under the results root)")
    C.add_hidden_args(ap)
    args = ap.parse_args()
    C.apply_overrides(args)
    if args.out:
        C.require_round_output(args.out)
    state = C.STATES[args.state]
    for p, what in ((state.checkout, "checkout"), (state.python, "venv python")):
        if not p.exists():
            raise SystemExit(f"state {state.name}: {what} {p} does not exist")

    probe = run([state.python, "-I", "-c", _PROBE])
    if probe.returncode:
        raise SystemExit(f"probe failed in {state.python}: {probe.stderr}")
    info = json.loads(probe.stdout)
    freeze = run([C.UV, "pip", "freeze", "--python", state.python]) if C.UV.exists() else None
    if freeze is None or freeze.returncode:
        freeze = run([state.python, "-m", "pip", "freeze"])
    prov = C.git_provenance(state.checkout)
    sha, src_tree = prov["git_sha"], prov["src_tree_sha"]
    branch = run(["git", "-C", state.checkout, "branch", "--show-current"]).stdout.strip() or "(detached)"

    checks = []
    if state.name == "A":
        expected = C.git(state.checkout, "rev-parse", f"{state.ref}^{{commit}}")
        checks.append(f"HEAD == {state.ref}: {sha == expected}")
    if state.name == "B":
        expected_tree = C.git(state.checkout, "rev-parse", f"{state.ref}:src")
        checks.append(f"HEAD:src == {state.ref}:src: {src_tree == expected_tree}")
    if state.name == "C":
        if state.ref:  # a round file pins C's exact commit (round 1: this file records it)
            expected = C.git(state.checkout, "rev-parse", f"{state.ref}^{{commit}}")
            checks.append(f"HEAD == {state.ref}: {sha == expected}")
        base = C.git(C.REPO, "rev-parse", f"{C.STATES['B'].ref}:src")
        checks.append(f"HEAD:src differs from {C.STATES['B'].ref}:src: {src_tree != base}")
    checks.append(f"fastmcp == {state.fastmcp}: {info.get('fastmcp') == state.fastmcp}")
    origin = info.get("candlekeep_origin") or ""
    checks.append(f"candlekeep imported from this checkout: "
                  f"{Path(origin).resolve().is_relative_to((state.checkout / 'src').resolve()) if origin else False}")
    checks.append(f"src/ and pyproject.toml clean: {not prov['status_porcelain']}")
    checks.append(f"no .env in checkout: {not prov['dotenv_present']}")

    lines = [
        f"state: {state.name}",
        f"generated_at: {C.now_iso()}",
        f"checkout: {state.checkout}",
        f"branch: {branch}",
        f"git_sha: {sha}",
        f"src_tree_sha (git rev-parse HEAD:src): {src_tree}",
        f"pyproject_sha (git rev-parse HEAD:pyproject.toml): {prov['pyproject_sha']}",
        f"status_porcelain (src, pyproject.toml): {prov['status_porcelain'] or 'clean'}",
        f"venv: {state.venv}",
        f"python: {info['python']} ({info['executable']})",
        f"fastmcp: {info.get('fastmcp')}",
        f"chromadb (client): {info.get('chromadb')}",
        f"torch: {info.get('torch')}",
        f"torch_mps_available: {info.get('mps_available')} (built: {info.get('mps_built')})",
        f"sentence-transformers: {info.get('sentence-transformers')}",
        f"spacy: {info.get('spacy')}; en_core_web_sm: {info.get('en-core-web-sm')}",
        f"candlekeep_origin: {origin}",
        f"device: {C.DEVICE} (CANDLEKEEP_DEVICE for every run)",
        f"chroma_server: {C.chroma_cli()} (venv B, used for every state)",
        f"pythonhashseed: {C.HASH_SEED} (every candlekeep process)",
        "",
        "checks:",
        *[f"  {c}" for c in checks],
        "",
        f"model_cache: {C.MODELS_DIR}",
        *[f"  {line}" for line in model_snapshots()],
        "",
        f"pip_freeze ({'uv pip freeze --python ' + str(state.python) if C.UV.exists() else 'pip freeze'}):",
        *[f"  {line}" for line in freeze.stdout.splitlines()],
        "",
    ]
    out = Path(args.out) if args.out else C.CONFIG.results_root / "env" / f"{state.name}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    for c in checks:
        print(f"  {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
