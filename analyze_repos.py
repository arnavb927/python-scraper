"""Autonomous repo analyzer for the MAS shortlist.

Walks every entry in `mas_repos_balanced_sample.json`, shallow-clones each
repository, asks Cursor's headless agent CLI to produce a structured Markdown
report inside the cloned workspace, saves the report to `repo_reports/`, and
deletes the clone before moving on to the next entry. Resumable via a JSON
state ledger plus on-disk `.md` checks.

Prerequisites (one-time):
    # Install Cursor CLI on native Windows (PowerShell):
    irm 'https://cursor.com/install?win32=true' | iex
    # Authenticate (interactive, one-time) OR set CURSOR_API_KEY:
    agent login
    # Verify:
    agent --version

Then run:
    python analyze_repos.py                     # process everything, resumable
    python analyze_repos.py --limit 10          # smoke test on 10 repos
    python analyze_repos.py --retry-failed      # only re-attempt failed entries
    python analyze_repos.py --use-cases "Code Generation,Simulation"
    python analyze_repos.py --tier Mainstream
    python analyze_repos.py --dry-run           # print plan, don't clone/run

Override the model with `CURSOR_MODEL` env var (default: `auto`).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Paths + constants
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
SHORTLIST_PATH = ROOT / "mas_repos_balanced_sample.json"
PROMPT_TEMPLATE_PATH = ROOT / "analysis_prompt.md"
REPORTS_DIR = ROOT / "repo_reports"
CLONES_DIR = ROOT / "repo_clones"
STATE_PATH = REPORTS_DIR / "_state.json"
SUMMARY_PATH = REPORTS_DIR / "_summary.md"
CLASSIFICATIONS_CSV_PATH = REPORTS_DIR / "_classifications.csv"

AGENT_TIMEOUT_S = 600                  # 10-minute hard cap per repo
CLONE_TIMEOUT_S = 300                  # 5-minute clone cap (mostly for size guards)
MAX_REPO_SIZE_KB = 500 * 1024          # ~500 MB clone-size guard
DEFAULT_MODEL = os.environ.get("CURSOR_MODEL", "auto")

VALID_TIERS = {"Mainstream", "Mid-Tier", "Niche"}
VALID_USE_CASES = {
    "Workflow Automation",
    "Code Generation",
    "RAG + Agents",
    "Browser / Terminal Use",
    "Simulation",
}


# ---------------------------------------------------------------------------
# Slug + filename helpers
# ---------------------------------------------------------------------------

_SLUG_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug_part(value: str) -> str:
    """Make a single path component filesystem-safe and lowercase-stable."""
    cleaned = _SLUG_SAFE_RE.sub("-", value.strip())
    return cleaned.strip("-_.") or "unknown"


def report_filename(entry: Dict[str, Any]) -> str:
    """Build a sortable, identifiable filename from repo metadata.

    Format: `<usecase>__<tier>__<owner>__<repo>.md`. The double underscore
    delimiter makes it trivial to split downstream and unambiguous even when
    repo names contain dashes.
    """
    use_case = _slug_part((entry.get("primary_use_case") or "uncategorised").lower())
    tier = _slug_part((entry.get("user_tier") or "unknown").lower())
    repo_name = entry.get("repo_name") or ""
    if "/" in repo_name:
        owner, repo = repo_name.split("/", 1)
    else:
        owner, repo = "unknown", repo_name or "unknown"
    return f"{use_case}__{tier}__{_slug_part(owner)}__{_slug_part(repo)}.md"


# ---------------------------------------------------------------------------
# Prereq checks
# ---------------------------------------------------------------------------


def _which(exe: str) -> Optional[str]:
    return shutil.which(exe)


def _agent_install_paths() -> List[Path]:
    """Known absolute install locations for the Cursor agent CLI.

    The Windows installer drops the binary into `%LOCALAPPDATA%\\cursor-agent\\`
    and adds that folder to the user PATH. Existing shell sessions don't see
    the new PATH entry until they restart, so we also probe the install dir
    directly to keep the pipeline runnable from a stale terminal.
    """
    candidates: List[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "cursor-agent")
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / ".local" / "bin")
    return candidates


_VERSION_DIR_RE = re.compile(r"^\d{4}\.\d{1,2}\.\d{1,2}-[a-f0-9]+$")


def _find_node_entrypoint() -> Optional[List[str]]:
    """Locate `node.exe` + `index.js` from the cursor-agent install.

    The Windows wrappers (`agent.cmd` -> `agent.ps1` -> node) re-parse argv
    through PowerShell, which mangles multi-line prompts and chokes on bare
    `-` markers. Bypassing them lets us pass a multi-line prompt as a single
    argv element straight to node, exactly like the Linux agent binary.
    """
    for base in _agent_install_paths():
        # Direct (non-versioned) install: node.exe + index.js next to wrapper
        node = base / "node.exe"
        idx = base / "index.js"
        if node.exists() and idx.exists():
            return [str(node), str(idx)]

        versions = base / "versions"
        if not versions.is_dir():
            continue
        # Pick the newest version directory by name (the .ps1 wrapper does
        # the same, sorting YYYY.MM.DD-hash descending).
        version_dirs = sorted(
            (d for d in versions.iterdir()
             if d.is_dir() and _VERSION_DIR_RE.match(d.name)),
            key=lambda d: d.name,
            reverse=True,
        )
        for vd in version_dirs:
            node = vd / "node.exe"
            idx = vd / "index.js"
            if node.exists() and idx.exists():
                return [str(node), str(idx)]
    return None


def _find_agent_path() -> Optional[Path]:
    """Resolve the agent CLI either from PATH or from known install dirs.

    Used only for the prereq check display message; actual invocation goes
    through `_find_node_entrypoint` to bypass the PowerShell wrapper.
    """
    for cand in ("agent", "agent.cmd", "cursor-agent", "cursor-agent.cmd"):
        hit = _which(cand)
        if hit:
            return Path(hit)
    for base in _agent_install_paths():
        for name in ("agent.cmd", "agent.exe", "agent",
                     "cursor-agent.cmd", "cursor-agent.exe", "cursor-agent"):
            cand = base / name
            if cand.exists():
                return cand
    return None


def check_prereqs(require_runtime: bool = True) -> None:
    """Fail fast with actionable messages if the environment is incomplete.

    `require_runtime=False` skips the runtime-only checks (agent CLI, git)
    so `--dry-run` can preview a plan before tooling is installed.
    """
    problems: List[str] = []

    if not SHORTLIST_PATH.exists():
        problems.append(f"shortlist not found: {SHORTLIST_PATH}")
    if not PROMPT_TEMPLATE_PATH.exists():
        problems.append(f"prompt template not found: {PROMPT_TEMPLATE_PATH}")

    if require_runtime:
        if _which("git") is None:
            problems.append("`git` is not on PATH. Install Git for Windows.")

        if _find_agent_path() is None:
            problems.append(
                "Cursor agent CLI not found on PATH or in known install "
                "locations. Install with:\n"
                "    irm 'https://cursor.com/install?win32=true' | iex\n"
                "then restart your shell so PATH picks it up."
            )

        # Auth: either CURSOR_API_KEY or a prior `agent login`. We can only
        # cheaply check the env var; missing-login surfaces as a runtime
        # error which the per-repo loop will mark as failed.
        if not os.environ.get("CURSOR_API_KEY"):
            print("[note] CURSOR_API_KEY is not set; assuming `agent login` "
                  "session exists. If runs fail with auth errors, run "
                  "`agent login` once.", file=sys.stderr)

    if problems:
        print("Prerequisite check failed:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(2)


def agent_executable() -> List[str]:
    """Return the agent invocation prefix.

    Prefers calling `node.exe index.js ...` directly so that multi-line
    prompts and bare `-` arguments survive argv handling. Falls back to the
    `agent` wrapper if we can't locate the bundled node entrypoint.
    """
    direct = _find_node_entrypoint()
    if direct is not None:
        return direct
    found = _find_agent_path()
    if found is not None:
        return [str(found)]
    return ["agent"]  # caller will surface the error


# ---------------------------------------------------------------------------
# State ledger
# ---------------------------------------------------------------------------

@dataclass
class StateLedger:
    path: Path
    data: Dict[str, Dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "StateLedger":
        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as fh:
                    return cls(path=path, data=json.load(fh))
            except (OSError, ValueError) as exc:
                print(f"[warn] could not read {path}: {exc}; starting fresh",
                      file=sys.stderr)
        return cls(path=path, data={})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self.data, fh, indent=2, ensure_ascii=False)
        tmp.replace(self.path)

    def status(self, repo_name: str) -> Optional[str]:
        rec = self.data.get(repo_name)
        return rec.get("status") if rec else None

    def is_done(self, repo_name: str) -> bool:
        return self.status(repo_name) == "done"

    def mark(self, repo_name: str, **fields: Any) -> None:
        existing = self.data.get(repo_name, {})
        existing.update(fields)
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.data[repo_name] = existing
        self.save()


# ---------------------------------------------------------------------------
# Filesystem helpers (Windows-safe rmtree, shallow clone with size guard)
# ---------------------------------------------------------------------------


def _on_rmtree_error(func, path, exc_info) -> None:
    """rmtree onerror handler that strips read-only bits Git leaves behind.

    Windows packs `.git/objects/pack/*.idx` and friends as read-only, which
    makes `shutil.rmtree` raise PermissionError. Re-chmod and retry.
    """
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        # Last-ditch: ignore so the pipeline can continue. The caller's
        # idempotent loop will re-attempt the clone next run.
        pass


def rmtree_force(path: Path) -> None:
    if not path.exists():
        return
    shutil.rmtree(path, onerror=_on_rmtree_error)


def git_clone_shallow(url: str, dest: Path) -> None:
    """Shallow-clone (depth 1, no submodules) with a wall-clock timeout."""
    rmtree_force(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "git", "clone",
        "--depth", "1",
        "--single-branch",
        "--no-tags",
        "--filter=blob:limit=10m",   # skip individual blobs > 10 MB
        url, str(dest),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        timeout=CLONE_TIMEOUT_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git clone failed (exit {proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )


def directory_size_kb(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total // 1024


# ---------------------------------------------------------------------------
# Cursor agent runner
# ---------------------------------------------------------------------------


def render_prompt(template: str, entry: Dict[str, Any]) -> str:
    """Substitute repo metadata into the prompt template.

    Uses `str.format_map` with a defaultdict-like fallback so unexpected
    keys don't crash the run.
    """
    arch_labels = ", ".join(entry.get("architecture_labels") or []) or "none"
    use_labels = ", ignored" if not entry.get("use_case_labels") \
        else ", ".join(entry["use_case_labels"])

    fields = {
        "repo_name": entry.get("repo_name", ""),
        "url": entry.get("url", ""),
        "stars": entry.get("stars", 0),
        "forks": entry.get("forks", 0),
        "contributors_count": entry.get("contributors_count", 0),
        "last_commit_date": entry.get("last_commit_date", ""),
        "primary_use_case": entry.get("primary_use_case", ""),
        "user_tier": entry.get("user_tier", ""),
        "architecture_labels": arch_labels,
        "use_case_labels": use_labels,
        "description": (entry.get("description") or "").replace("\n", " "),
    }

    class _SafeDict(dict):
        def __missing__(self, key: str) -> str:  # type: ignore[override]
            return f"{{{key}}}"

    return template.format_map(_SafeDict(fields))


def run_cursor_agent(prompt: str, cwd: Path,
                     timeout_s: int = AGENT_TIMEOUT_S) -> str:
    """Invoke `agent -p --force` with the prompt; return stdout (the report).

    Raises RuntimeError on timeout, non-zero exit, or empty output.
    """
    cmd = agent_executable() + [
        "-p", "--force", "--trust",
        "--output-format", "text",
        "--model", DEFAULT_MODEL,
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"agent timed out after {timeout_s}s") from exc

    if proc.returncode != 0:
        snippet = (proc.stderr or proc.stdout or "").strip()[:600]
        raise RuntimeError(f"agent exit {proc.returncode}: {snippet}")

    output = (proc.stdout or "").strip()
    if not output:
        snippet = (proc.stderr or "").strip()[:300]
        raise RuntimeError(f"agent produced empty output. stderr: {snippet}")
    return output


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _yaml_escape(value: Any) -> str:
    """Quote-escape a value for safe inclusion in YAML frontmatter."""
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_escape(v) for v in value) + "]"
    s = str(value if value is not None else "")
    if any(ch in s for ch in ":#\n\"'") or s == "":
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def yaml_frontmatter(entry: Dict[str, Any], extra: Dict[str, Any]) -> str:
    """Build a YAML frontmatter block placed at the top of every report."""
    items = {
        "repo_name": entry.get("repo_name", ""),
        "url": entry.get("url", ""),
        "stars": entry.get("stars", 0),
        "forks": entry.get("forks", 0),
        "contributors_count": entry.get("contributors_count", 0),
        "last_commit_date": entry.get("last_commit_date", ""),
        "primary_use_case": entry.get("primary_use_case", ""),
        "user_tier": entry.get("user_tier", ""),
        "total_score": entry.get("total_score", 0),
        "architecture_labels": entry.get("architecture_labels") or [],
        "use_case_labels": entry.get("use_case_labels") or [],
        **extra,
    }
    lines = ["---"]
    for k, v in items.items():
        lines.append(f"{k}: {_yaml_escape(v)}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def write_report(md_path: Path, entry: Dict[str, Any],
                 body: str, extra: Dict[str, Any]) -> None:
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(
        yaml_frontmatter(entry, extra) + body.rstrip() + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Classification extraction + CSV
# ---------------------------------------------------------------------------

CSV_USE_CASES = {
    "Workflow Automation",
    "Code Generation",
    "RAG + Agents",
    "Browser / Terminal Use",
    "Simulation",
    "None",
}

_USES_MAS_RE = re.compile(r"^\s*USES_MAS\s*:\s*(yes|no)\b",
                          re.IGNORECASE | re.MULTILINE)
_FINAL_UC_RE = re.compile(r"^\s*FINAL_USE_CASE\s*:\s*(.+?)\s*$",
                          re.IGNORECASE | re.MULTILINE)


def parse_classification(report_text: str) -> Dict[str, str]:
    """Pull `uses_mas` and `final_use_case` out of the agent's report body.

    Returns a dict with `uses_mas` ("yes"|"no"|"") and `final_use_case`
    (one of CSV_USE_CASES, or "" if the agent didn't emit a recognizable
    value). Empty strings let the CSV writer surface "needs review" rows
    rather than silently mislabel anything.
    """
    out = {"uses_mas": "", "final_use_case": ""}

    m = _USES_MAS_RE.search(report_text)
    if m:
        out["uses_mas"] = m.group(1).lower()

    m = _FINAL_UC_RE.search(report_text)
    if m:
        # Strip surrounding quotes/backticks the agent sometimes adds.
        raw = m.group(1).strip().strip("`'\"")
        # Match against the canonical set case-insensitively, then return
        # the canonical capitalization so the CSV is consistent.
        norm = raw.lower()
        for canonical in CSV_USE_CASES:
            if canonical.lower() == norm:
                out["final_use_case"] = canonical
                break

    return out


def write_classifications_csv(state: StateLedger,
                              path: Path = CLASSIFICATIONS_CSV_PATH) -> None:
    """Emit a 3-column CSV summarizing every repo we have a record for.

    Columns: repo_name, uses_mas, use_case. Rows are sorted by repo_name
    for stable diffs. Repos that were processed but failed (or are missing
    a classification) get blank cells so they're easy to grep for.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["repo_name", "uses_mas", "use_case"])
        for repo_name in sorted(state.data.keys()):
            rec = state.data[repo_name]
            if rec.get("status") != "done":
                writer.writerow([repo_name, "", ""])
                continue
            writer.writerow([
                repo_name,
                rec.get("uses_mas", "") or "",
                rec.get("final_use_case", "") or "",
            ])


# ---------------------------------------------------------------------------
# Filtering + ordering
# ---------------------------------------------------------------------------


def _parse_csv(arg: Optional[str]) -> List[str]:
    if not arg:
        return []
    return [s.strip() for s in arg.split(",") if s.strip()]


def filter_entries(entries: List[Dict[str, Any]],
                   args: argparse.Namespace,
                   state: StateLedger) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = list(entries)

    if args.use_cases:
        wanted = set(args.use_cases)
        selected = [e for e in selected
                    if e.get("primary_use_case") in wanted]

    if args.tier:
        wanted_t = set(args.tier)
        selected = [e for e in selected if e.get("user_tier") in wanted_t]

    # Process highest-score / most-popular first so partial runs are
    # weighted toward the best candidates.
    selected.sort(key=lambda e: (
        -(e.get("total_score") or 0),
        -(e.get("stars") or 0),
        e.get("repo_name") or "",
    ))

    if args.start_from:
        selected = [e for e in selected
                    if (e.get("repo_name") or "") >= args.start_from]

    if args.retry_failed:
        selected = [e for e in selected
                    if state.status(e.get("repo_name", "")) == "failed"]

    if args.limit and args.limit > 0:
        selected = selected[: args.limit]

    return selected


# ---------------------------------------------------------------------------
# Summary writer
# ---------------------------------------------------------------------------


def write_summary(state: StateLedger, total_input: int,
                  wall_seconds: float) -> None:
    by_status: Dict[str, int] = {}
    by_uc_status: Dict[str, Dict[str, int]] = {}
    by_tier_status: Dict[str, Dict[str, int]] = {}
    failures: List[Dict[str, Any]] = []
    durations: List[float] = []

    for repo_name, rec in state.data.items():
        status = rec.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        uc = rec.get("primary_use_case", "?")
        by_uc_status.setdefault(uc, {}).setdefault(status, 0)
        by_uc_status[uc][status] += 1

        tier = rec.get("user_tier", "?")
        by_tier_status.setdefault(tier, {}).setdefault(status, 0)
        by_tier_status[tier][status] += 1

        if status == "failed":
            failures.append({
                "repo_name": repo_name,
                "error": rec.get("error", ""),
            })
        if isinstance(rec.get("duration_s"), (int, float)):
            durations.append(float(rec["duration_s"]))

    avg = sum(durations) / len(durations) if durations else 0.0

    lines: List[str] = []
    lines.append("# Repo analysis run summary")
    lines.append("")
    lines.append(f"- generated_at: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- total_input_entries: {total_input}")
    lines.append(f"- wall_clock_seconds: {wall_seconds:.1f}")
    lines.append(f"- average_per_repo_seconds: {avg:.1f}")
    lines.append("")
    lines.append("## Status counts")
    for status, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
        lines.append(f"- {status}: {n}")
    lines.append("")

    lines.append("## By primary use case")
    for uc in sorted(by_uc_status):
        parts = ", ".join(f"{s}={n}"
                          for s, n in sorted(by_uc_status[uc].items()))
        lines.append(f"- {uc}: {parts}")
    lines.append("")

    lines.append("## By tier")
    for tier in sorted(by_tier_status):
        parts = ", ".join(f"{s}={n}"
                          for s, n in sorted(by_tier_status[tier].items()))
        lines.append(f"- {tier}: {parts}")
    lines.append("")

    if failures:
        lines.append("## Failures")
        for f in failures:
            err = f["error"].replace("\n", " ")[:300]
            lines.append(f"- `{f['repo_name']}`: {err}")
        lines.append("")

    SUMMARY_PATH.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Console progress
# ---------------------------------------------------------------------------


def _fmt_eta(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Autonomous Cursor-agent analysis of MAS shortlist repos."
    )
    p.add_argument("--limit", type=int, default=0,
                   help="Process at most N repos (0 = no limit).")
    p.add_argument("--use-cases", type=_parse_csv, default=[],
                   help="Comma-separated primary_use_case filter, e.g. "
                        "'Code Generation,Simulation'.")
    p.add_argument("--tier", type=_parse_csv, default=[],
                   help="Comma-separated tier filter, e.g. 'Mainstream,Mid-Tier'.")
    p.add_argument("--start-from", default="",
                   help="Skip repos whose name sorts before this owner/repo.")
    p.add_argument("--retry-failed", action="store_true",
                   help="Only re-process entries marked 'failed' in state.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the planned work and exit without cloning.")
    p.add_argument("--max-size-kb", type=int, default=MAX_REPO_SIZE_KB,
                   help="Skip repos whose clone exceeds this size in KB.")
    p.add_argument("--agent-timeout", type=int, default=AGENT_TIMEOUT_S,
                   help="Per-repo agent timeout in seconds.")
    p.add_argument("--csv-only", action="store_true",
                   help="Rebuild repo_reports/_classifications.csv from "
                        "existing reports + state, then exit. No clones, "
                        "no agent calls.")
    args = p.parse_args(argv)

    bad_uc = [u for u in args.use_cases if u not in VALID_USE_CASES]
    if bad_uc:
        p.error(f"unknown --use-cases: {bad_uc}. "
                f"Valid: {sorted(VALID_USE_CASES)}")
    bad_tier = [t for t in args.tier if t not in VALID_TIERS]
    if bad_tier:
        p.error(f"unknown --tier: {bad_tier}. Valid: {sorted(VALID_TIERS)}")

    return args


def load_shortlist() -> List[Dict[str, Any]]:
    with SHORTLIST_PATH.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise RuntimeError(f"{SHORTLIST_PATH} is not a JSON list")
    return data


def backfill_classifications_from_reports(state: StateLedger) -> int:
    """Populate `uses_mas` / `final_use_case` in state from existing .md
    files when those fields are missing. Returns count of records updated.

    Useful after upgrading the prompt: re-runs aren't required for any
    report whose body already contains the machine-readable block.
    """
    updated = 0
    if not REPORTS_DIR.exists():
        return 0
    for md_file in REPORTS_DIR.glob("*.md"):
        if md_file.name.startswith("_"):
            continue
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        clf = parse_classification(text)
        # Look up the state record by md filename rather than by repo name,
        # since the state may not have been touched if user moved files.
        for repo_name, rec in state.data.items():
            if rec.get("md_path", "").endswith(md_file.name):
                changed = False
                if clf.get("uses_mas") and not rec.get("uses_mas"):
                    rec["uses_mas"] = clf["uses_mas"]
                    changed = True
                if clf.get("final_use_case") and not rec.get("final_use_case"):
                    rec["final_use_case"] = clf["final_use_case"]
                    changed = True
                if changed:
                    updated += 1
                break
    if updated:
        state.save()
    return updated


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.csv_only:
        check_prereqs(require_runtime=False)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        state = StateLedger.load(STATE_PATH)
        n = backfill_classifications_from_reports(state)
        write_classifications_csv(state)
        print(f"[csv-only] backfilled {n} record(s) from existing reports")
        print(f"[csv-only] wrote {CLASSIFICATIONS_CSV_PATH.relative_to(ROOT)}")
        return 0

    check_prereqs(require_runtime=not args.dry_run)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CLONES_DIR.mkdir(parents=True, exist_ok=True)

    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    entries = load_shortlist()
    state = StateLedger.load(STATE_PATH)
    work = filter_entries(entries, args, state)

    print(f"[plan] shortlist={len(entries)} selected={len(work)} "
          f"reports_dir={REPORTS_DIR}")
    if args.dry_run:
        for i, entry in enumerate(work, 1):
            print(f"  {i:>4}. {entry.get('repo_name')} "
                  f"[{entry.get('primary_use_case')}/{entry.get('user_tier')}] "
                  f"score={entry.get('total_score')}")
        return 0

    run_start = time.monotonic()
    durations: List[float] = []

    for idx, entry in enumerate(work, 1):
        repo_name = entry.get("repo_name", "")
        if not repo_name or "/" not in repo_name:
            print(f"[skip] entry {idx}: malformed repo_name={repo_name!r}")
            continue

        md_path = REPORTS_DIR / report_filename(entry)
        if md_path.exists() or state.is_done(repo_name):
            print(f"[ {idx:>3}/{len(work)}] {repo_name} ... already done, "
                  f"skipping")
            state.mark(repo_name,
                       status="done",
                       md_path=str(md_path.relative_to(ROOT)),
                       primary_use_case=entry.get("primary_use_case"),
                       user_tier=entry.get("user_tier"))
            continue

        avg = sum(durations) / len(durations) if durations else 0.0
        eta = avg * (len(work) - idx + 1)
        eta_str = _fmt_eta(eta) if avg else "?"
        prefix = (f"[ {idx:>3}/{len(work)}] "
                  f"{entry.get('primary_use_case','?')}/"
                  f"{entry.get('user_tier','?')} {repo_name}")
        print(f"{prefix} ... cloning (eta {eta_str})", flush=True)

        clone_dir = CLONES_DIR / report_filename(entry).rsplit(".", 1)[0]
        repo_start = time.monotonic()
        try:
            git_clone_shallow(entry["url"], clone_dir)

            size_kb = directory_size_kb(clone_dir)
            if size_kb > args.max_size_kb:
                raise RuntimeError(
                    f"clone too large: {size_kb} KB > {args.max_size_kb} KB"
                )

            prompt = render_prompt(template, entry)
            print(f"{prefix} ... analyzing ({size_kb} KB on disk)", flush=True)
            body = run_cursor_agent(
                prompt, cwd=clone_dir, timeout_s=args.agent_timeout,
            )

            duration = time.monotonic() - repo_start
            classification = parse_classification(body)
            write_report(md_path, entry, body, extra={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "model": DEFAULT_MODEL,
                "duration_s": round(duration, 1),
                "clone_size_kb": size_kb,
                "uses_mas": classification.get("uses_mas") or "unknown",
                "final_use_case": classification.get("final_use_case")
                                  or "unknown",
            })
            state.mark(repo_name,
                       status="done",
                       md_path=str(md_path.relative_to(ROOT)),
                       primary_use_case=entry.get("primary_use_case"),
                       user_tier=entry.get("user_tier"),
                       duration_s=round(duration, 1),
                       clone_size_kb=size_kb,
                       uses_mas=classification.get("uses_mas", ""),
                       final_use_case=classification.get("final_use_case", ""),
                       error="")
            write_classifications_csv(state)
            durations.append(duration)
            tag = ""
            if not classification.get("uses_mas") \
                    or not classification.get("final_use_case"):
                tag = " (classification incomplete)"
            print(f"{prefix} ... done in {duration:.1f}s -> "
                  f"{md_path.name}{tag}", flush=True)
        except Exception as exc:
            duration = time.monotonic() - repo_start
            err_msg = str(exc)[:600]
            print(f"{prefix} ... FAILED in {duration:.1f}s: {err_msg}",
                  file=sys.stderr, flush=True)
            state.mark(repo_name,
                       status="failed",
                       primary_use_case=entry.get("primary_use_case"),
                       user_tier=entry.get("user_tier"),
                       duration_s=round(duration, 1),
                       error=err_msg)
        finally:
            rmtree_force(clone_dir)

    wall = time.monotonic() - run_start
    write_summary(state, total_input=len(entries), wall_seconds=wall)
    write_classifications_csv(state)

    done = sum(1 for r in state.data.values() if r.get("status") == "done")
    failed = sum(1 for r in state.data.values() if r.get("status") == "failed")
    print(f"\n[summary] done={done} failed={failed} "
          f"wall={_fmt_eta(wall)} -> {SUMMARY_PATH.relative_to(ROOT)}")
    print(f"[csv]     {CLASSIFICATIONS_CSV_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
