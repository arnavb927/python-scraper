"""GitHub Repository Scraper for Multi-Agent Systems (MAS) Research.

Discovers, filters, scores, and classifies public GitHub repositories related
to Multi-Agent Systems and agentic AI. Produces a CSV and JSON export plus a
console summary suitable for downstream academic analysis.

Usage:
    export GITHUB_TOKEN=ghp_xxx           # PowerShell: $env:GITHUB_TOKEN="ghp_xxx"
    python mas_scraper.py
"""

from __future__ import annotations

import base64
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"

# Topic searches - GitHub's `topic:` qualifier matches curated repo topics.
TOPIC_QUERIES: List[str] = [
    "topic:multi-agent-systems",
    "topic:multi-agent-system",
    "topic:agentic-ai",
]

# Keyword searches - these target README / description content using the `in:readme`
# qualifier so we surface repos whose topics are not tagged but whose docs clearly
# describe multi-agent functionality.
KEYWORD_QUERIES: List[str] = [
    '"agent orchestration" in:readme',
    '"LLM agent framework" in:readme',
    '"swarm intelligence" in:readme',
    '"agent collaboration" in:readme',
    '"multi-agent workflow" in:readme',
    '"agent handoff" in:readme',
    '"tool use" in:readme',
]

MIN_STARS = 50                     # hard minimum applied at query time AND post-filter
MIN_CONTRIBUTORS = 3               # hard minimum contributors
MAX_COMMIT_AGE_DAYS = 182          # ~6 months
PER_PAGE = 100                     # GitHub max
MAX_PAGES_PER_QUERY = 10           # Search API caps at 1000 results (10 pages * 100)
INTER_CALL_SLEEP = 0.5             # avoid secondary rate limits
MAX_RETRIES = 3                    # for 403/429

OUTPUT_CSV = "mas_repos.csv"
OUTPUT_JSON = "mas_repos_summary.json"

# Architecture detection signals: label -> list of case-insensitive substrings/regexes
ARCHITECTURE_SIGNALS: Dict[str, List[str]] = {
    "LangGraph": [r"\bStateGraph\b", r"\badd_node\b", r"\badd_edge\b", r"\blanggraph\b"],
    "LangChain": [r"\blangchain\b", r"\bAgentExecutor\b", r"\binitialize_agent\b"],
    "AutoGen":   [r"\bautogen\b", r"\bAssistantAgent\b", r"\bUserProxyAgent\b"],
    "CrewAI":    [r"\bcrewai\b", r"\bCrew\b", r"\bAgent\b", r"\bTask\b"],
}

# LangGraph primitives used for the dedicated +2 score bonus
LANGGRAPH_PRIMITIVES = [r"\bStateGraph\b", r"\badd_node\b", r"\badd_edge\b"]

# Use case detection keywords (all matched case-insensitively).
USE_CASE_KEYWORDS: Dict[str, List[str]] = {
    "Workflow Automation": [
        "workflow", "pipeline", "automation", "orchestration",
        "report generation", "data processing",
    ],
    "Code Generation": [
        "code generation", "code review", "debugging",
        "software engineering", "developer agent",
    ],
    "RAG + Agents": [
        "retrieval", "rag", "vector store", "knowledge base", "document qa",
    ],
    "Browser / Terminal Use": [
        "browser", "web scraping", "terminal", "shell",
        "command execution", "computer use",
    ],
    "Simulation": [
        "simulation", "social simulation", "multi-agent simulation",
        "scenario modelling", "scenario modeling", "emergent",
    ],
}

# ---------------------------------------------------------------------------
# HTTP session + rate limit handling
# ---------------------------------------------------------------------------


def build_session(token: Optional[str]) -> requests.Session:
    """Create a requests Session pre-configured with auth + accept headers."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "User-Agent": "mas-research-scraper/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    return session


def _respect_rate_limit(resp: requests.Response) -> None:
    """If remaining quota is dangerously low, sleep until the quota resets.

    GitHub returns `X-RateLimit-Remaining` and `X-RateLimit-Reset` (unix seconds).
    We pad by +2s to avoid waking up a hair early.
    """
    remaining = resp.headers.get("X-RateLimit-Remaining")
    reset = resp.headers.get("X-RateLimit-Reset")
    if remaining is None or reset is None:
        return
    try:
        remaining_i = int(remaining)
        reset_i = int(reset)
    except ValueError:
        return
    if remaining_i <= 5:
        now = int(time.time())
        wait = max(0, reset_i - now) + 2
        if wait > 0:
            print(f"[rate-limit] Remaining={remaining_i}. Sleeping {wait}s "
                  f"until reset...", file=sys.stderr)
            time.sleep(wait)


def api_get(session: requests.Session, url: str,
            params: Optional[Dict[str, Any]] = None) -> Optional[requests.Response]:
    """GET with rate-limit awareness and exponential backoff on 403/429.

    Returns the Response on success, or None if the resource is missing (404)
    or repeatedly fails. Callers that need headers (e.g. Link) use the Response
    directly; others call `.json()`.
    """
    backoff = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            print(f"[warn] request error on {url}: {exc}", file=sys.stderr)
            time.sleep(backoff)
            backoff *= 2
            continue

        # Secondary rate limits come back as 403 (with a specific body) or 429.
        if resp.status_code in (403, 429):
            # Honour Retry-After if present, else exponential backoff.
            retry_after = resp.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = int(retry_after)
            else:
                wait = backoff
            print(f"[backoff] {resp.status_code} on {url} "
                  f"(attempt {attempt}/{MAX_RETRIES}); sleeping {wait}s",
                  file=sys.stderr)
            time.sleep(wait)
            backoff *= 2
            _respect_rate_limit(resp)
            continue

        if resp.status_code == 404:
            return None

        if not resp.ok:
            print(f"[warn] HTTP {resp.status_code} for {url}: "
                  f"{resp.text[:200]}", file=sys.stderr)
            return None

        _respect_rate_limit(resp)
        # Courtesy pause to stay under secondary limits.
        time.sleep(INTER_CALL_SLEEP)
        return resp

    return None


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def search_repositories(session: requests.Session, query: str) -> List[Dict[str, Any]]:
    """Run one Search API query, paginating up to MAX_PAGES_PER_QUERY.

    We append `stars:>=MIN_STARS` at query time as the spec requires and sort
    by stars descending to maximise useful hits inside the Search API's
    1000-result ceiling.
    """
    q = f"{query} stars:>={MIN_STARS}"
    results: List[Dict[str, Any]] = []
    for page in range(1, MAX_PAGES_PER_QUERY + 1):
        resp = api_get(session, f"{GITHUB_API}/search/repositories", params={
            "q": q,
            "sort": "stars",
            "order": "desc",
            "per_page": PER_PAGE,
            "page": page,
        })
        if resp is None:
            break
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        results.extend(items)
        if len(items) < PER_PAGE:
            break  # last page
    print(f"[discover] {query!r}: {len(results)} hits", file=sys.stderr)
    return results


def discover_repositories(session: requests.Session) -> List[Dict[str, Any]]:
    """Run all topic + keyword searches and deduplicate by full_name."""
    seen: Dict[str, Dict[str, Any]] = {}
    for q in TOPIC_QUERIES + KEYWORD_QUERIES:
        for repo in search_repositories(session, q):
            full_name = repo.get("full_name")
            if full_name and full_name not in seen:
                seen[full_name] = repo
    print(f"[discover] {len(seen)} unique repos across all queries",
          file=sys.stderr)
    return list(seen.values())


# ---------------------------------------------------------------------------
# Enrichment: README, contributors, last commit
# ---------------------------------------------------------------------------


def fetch_readme(session: requests.Session, owner: str, repo: str) -> str:
    """Return the decoded README text, or empty string if absent.

    The `/readme` endpoint returns a JSON blob with base64-encoded `content`.
    GitHub currently uses base64 with embedded newlines (RFC 2045), which
    `base64.b64decode` tolerates by default.
    """
    resp = api_get(session, f"{GITHUB_API}/repos/{owner}/{repo}/readme")
    if resp is None:
        return ""
    payload = resp.json()
    encoded = payload.get("content", "")
    encoding = payload.get("encoding", "base64")
    if not encoded or encoding != "base64":
        return ""
    try:
        raw = base64.b64decode(encoded)
        return raw.decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"[warn] README decode failed for {owner}/{repo}: {exc}",
              file=sys.stderr)
        return ""


_LINK_LAST_RE = re.compile(r'<[^>]*[?&]page=(\d+)[^>]*>;\s*rel="last"')


def fetch_contributors_count(session: requests.Session,
                             owner: str, repo: str) -> int:
    """Return approximate total contributors using the Link header trick.

    We request `per_page=1` so the `rel="last"` page number in the Link header
    *is* the total contributor count. Repos with zero or one contributor won't
    have a Link header at all; in that case we fall back to counting the single
    returned page.
    """
    resp = api_get(
        session,
        f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
        params={"per_page": 1, "anon": "true"},
    )
    if resp is None:
        return 0
    link = resp.headers.get("Link", "")
    match = _LINK_LAST_RE.search(link)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    # No Link header (< 1 full page): count what we got.
    try:
        body = resp.json()
    except ValueError:
        return 0
    if isinstance(body, list):
        return len(body)
    return 0


def fetch_last_commit_date(session: requests.Session,
                           owner: str, repo: str,
                           default_branch: Optional[str]) -> Optional[datetime]:
    """Return the authored datetime (UTC, tz-aware) of the latest commit."""
    params: Dict[str, Any] = {"per_page": 1}
    if default_branch:
        params["sha"] = default_branch
    resp = api_get(session, f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                   params=params)
    if resp is None:
        return None
    try:
        commits = resp.json()
    except ValueError:
        return None
    if not isinstance(commits, list) or not commits:
        return None
    commit_info = commits[0].get("commit", {})
    # Prefer committer date (reflects when commit landed), fall back to author.
    iso = (commit_info.get("committer", {}) or {}).get("date") \
        or (commit_info.get("author", {}) or {}).get("date")
    return _parse_github_datetime(iso)


def _parse_github_datetime(value: Optional[str]) -> Optional[datetime]:
    """GitHub returns ISO-8601 with a trailing 'Z'; fromisoformat needs offset."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def passes_quality_filters(repo: Dict[str, Any],
                           readme: str,
                           contributors: int,
                           last_commit: Optional[datetime],
                           now: datetime) -> Tuple[bool, str]:
    """Return (passes, reason). Reason is only meaningful on failure."""
    if (repo.get("stargazers_count") or 0) < MIN_STARS:
        return False, "stars<50"
    if contributors < MIN_CONTRIBUTORS:
        return False, "contributors<3"
    if not readme.strip():
        return False, "empty-readme"
    if last_commit is None:
        return False, "no-last-commit"
    if (now - last_commit) > timedelta(days=MAX_COMMIT_AGE_DAYS):
        return False, "stale"
    return True, ""


# ---------------------------------------------------------------------------
# Scoring + classification
# ---------------------------------------------------------------------------


def popularity_tier(stars: int) -> str:
    if stars > 5000:
        return "Mainstream"
    if stars >= 500:
        return "Mid-tier"
    if stars >= 100:
        return "Niche"
    return "Emerging"  # 50-99: below niche threshold but above hard cutoff


def _any_match(patterns: Iterable[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def score_repository(repo: Dict[str, Any], readme: str,
                     code_blob: str) -> Tuple[int, Dict[str, bool]]:
    """Compute total_score + signal flags used for both scoring and export."""
    score = 0
    stars = repo.get("stargazers_count") or 0
    forks = repo.get("forks_count") or 0
    issues = repo.get("open_issues_count") or 0
    watchers = repo.get("subscribers_count") or 0

    # Stars tier
    if stars > 5000:
        score += 3
    elif stars >= 500:
        score += 2
    elif stars >= 100:
        score += 1

    # Forks tier
    if forks > 500:
        score += 2
    elif forks >= 100:
        score += 1

    # Activity signals
    if issues > 10:
        score += 1
    if watchers > 100:
        score += 1

    combined_text = f"{readme}\n{code_blob}"
    has_architecture_section = bool(
        re.search(r"^\s*#{1,6}\s*(architecture|how it works)\b",
                  readme, re.IGNORECASE | re.MULTILINE)
    )
    if has_architecture_section:
        score += 1

    has_langgraph = _any_match(LANGGRAPH_PRIMITIVES, combined_text) \
        or re.search(r"\blanggraph\b", combined_text, re.IGNORECASE) is not None
    if has_langgraph:
        score += 2

    has_arxiv_link = re.search(r"https?://(?:www\.)?arxiv\.org/", readme,
                               re.IGNORECASE) is not None
    if has_arxiv_link:
        score += 1

    has_gaia_mention = re.search(r"\bGAIA\b", readme) is not None
    if has_gaia_mention:
        score += 1

    flags = {
        "has_langgraph": has_langgraph,
        "has_arxiv_link": has_arxiv_link,
        "has_gaia_mention": has_gaia_mention,
        "has_architecture_section": has_architecture_section,
    }
    return score, flags


def classify_architecture(readme: str, code_blob: str) -> List[str]:
    """Return all architecture labels whose signals appear in readme/code."""
    text = f"{readme}\n{code_blob}"
    labels: List[str] = []
    for label, patterns in ARCHITECTURE_SIGNALS.items():
        if _any_match(patterns, text):
            labels.append(label)
    if not labels:
        labels.append("Custom/Other")
    return labels


def classify_use_cases(readme: str) -> List[str]:
    """Return all use case labels whose keywords appear in the README."""
    lowered = readme.lower()
    labels: List[str] = []
    for label, keywords in USE_CASE_KEYWORDS.items():
        if any(kw.lower() in lowered for kw in keywords):
            labels.append(label)
    if not labels:
        labels.append("Uncategorised")
    return labels


# ---------------------------------------------------------------------------
# Code sampling (top-level Python files) for architecture detection
# ---------------------------------------------------------------------------


def sample_top_level_python(session: requests.Session,
                            owner: str, repo: str,
                            default_branch: Optional[str]) -> str:
    """Concatenate the raw text of up to a few top-level .py files.

    We only look at the repo root to keep the scraper fast; that's where most
    frameworks expose their entry point / top-level imports anyway.
    """
    params = {"ref": default_branch} if default_branch else None
    resp = api_get(session, f"{GITHUB_API}/repos/{owner}/{repo}/contents",
                   params=params)
    if resp is None:
        return ""
    try:
        entries = resp.json()
    except ValueError:
        return ""
    if not isinstance(entries, list):
        return ""

    chunks: List[str] = []
    py_files = [e for e in entries
                if isinstance(e, dict)
                and e.get("type") == "file"
                and isinstance(e.get("name"), str)
                and e["name"].endswith(".py")]
    # Cap to 3 files / ~200KB combined so we don't burn quota on huge repos.
    for entry in py_files[:3]:
        download_url = entry.get("download_url")
        if not download_url:
            continue
        raw = api_get(session, download_url)
        if raw is None:
            continue
        text = raw.text[:80_000]
        chunks.append(text)
    return "\n".join(chunks)


# ---------------------------------------------------------------------------
# Per-repo pipeline
# ---------------------------------------------------------------------------


def enrich_repo(session: requests.Session, repo: Dict[str, Any],
                now: datetime) -> Optional[Dict[str, Any]]:
    """Fetch extra data, run filters/scoring/classification, return a row dict.

    Returns None if the repo fails the hard quality filters.
    """
    full_name = repo.get("full_name", "")
    if "/" not in full_name:
        return None
    owner, name = full_name.split("/", 1)

    # The search endpoint omits `subscribers_count`, so we refetch the repo.
    detail_resp = api_get(session, f"{GITHUB_API}/repos/{owner}/{name}")
    detail = detail_resp.json() if detail_resp is not None else {}
    merged = {**repo, **detail} if isinstance(detail, dict) else repo

    readme = fetch_readme(session, owner, name)
    contributors = fetch_contributors_count(session, owner, name)
    last_commit = fetch_last_commit_date(session, owner, name,
                                         merged.get("default_branch"))

    passes, reason = passes_quality_filters(
        merged, readme, contributors, last_commit, now,
    )
    if not passes:
        print(f"[filter] drop {full_name}: {reason}", file=sys.stderr)
        return None

    code_blob = sample_top_level_python(
        session, owner, name, merged.get("default_branch"),
    )

    score, flags = score_repository(merged, readme, code_blob)
    arch_labels = classify_architecture(readme, code_blob)
    use_labels = classify_use_cases(readme)
    stars = merged.get("stargazers_count") or 0

    return {
        "repo_name": full_name,
        "url": merged.get("html_url", f"https://github.com/{full_name}"),
        "description": merged.get("description") or "",
        "stars": stars,
        "forks": merged.get("forks_count") or 0,
        "watchers": merged.get("subscribers_count") or 0,
        "open_issues": merged.get("open_issues_count") or 0,
        "contributors_count": contributors,
        "last_commit_date": last_commit.isoformat() if last_commit else "",
        "created_at": merged.get("created_at") or "",
        "topics": list(merged.get("topics") or []),
        "readme_excerpt": readme[:500],
        "architecture_labels": arch_labels,
        "use_case_labels": use_labels,
        "total_score": score,
        "popularity_tier": popularity_tier(stars),
        "has_langgraph": flags["has_langgraph"],
        "has_arxiv_link": flags["has_arxiv_link"],
        "has_gaia_mention": flags["has_gaia_mention"],
        "has_architecture_section": flags["has_architecture_section"],
    }


# ---------------------------------------------------------------------------
# Export + summary
# ---------------------------------------------------------------------------


CSV_COLUMNS = [
    "repo_name", "url", "description",
    "stars", "forks", "watchers", "open_issues",
    "contributors_count", "last_commit_date", "created_at",
    "topics", "readme_excerpt",
    "architecture_labels", "use_case_labels",
    "total_score", "popularity_tier",
    "has_langgraph", "has_arxiv_link",
    "has_gaia_mention", "has_architecture_section",
]


def export_csv(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS,
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for row in rows:
            flat = dict(row)
            # Lists -> pipe-joined strings for human-readable CSV cells.
            flat["topics"] = "|".join(row.get("topics") or [])
            flat["architecture_labels"] = "|".join(row.get("architecture_labels") or [])
            flat["use_case_labels"] = "|".join(row.get("use_case_labels") or [])
            # Collapse newlines in free text so Excel/Numbers don't split rows.
            flat["description"] = (row.get("description") or "").replace("\n", " ")
            flat["readme_excerpt"] = (row.get("readme_excerpt") or "").replace("\n", " ")
            writer.writerow(flat)


def export_json(rows: List[Dict[str, Any]], path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)


def print_summary(discovered: int, rows: List[Dict[str, Any]]) -> None:
    print()
    print("=" * 60)
    print("MAS Scraper Summary")
    print("=" * 60)
    print(f"Total repos discovered: {discovered}")
    print(f"Total repos after quality filtering: {len(rows)}")

    use_counter: Counter[str] = Counter()
    for r in rows:
        for lbl in r["use_case_labels"]:
            use_counter[lbl] += 1
    print("\nBreakdown by use case label:")
    for lbl, n in use_counter.most_common():
        print(f"  {lbl:<28} {n}")

    arch_counter: Counter[str] = Counter()
    for r in rows:
        for lbl in r["architecture_labels"]:
            arch_counter[lbl] += 1
    print("\nBreakdown by architecture label:")
    for lbl, n in arch_counter.most_common():
        print(f"  {lbl:<28} {n}")

    tier_counter = Counter(r["popularity_tier"] for r in rows)
    print("\nBreakdown by popularity tier:")
    for lbl, n in tier_counter.most_common():
        print(f"  {lbl:<28} {n}")

    print("\nTop 10 repos by score:")
    for r in rows[:10]:
        print(f"  {r['total_score']:>3}  {r['repo_name']}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("[warn] GITHUB_TOKEN not set - you will hit the 60 req/hr "
              "unauthenticated limit almost immediately.", file=sys.stderr)

    session = build_session(token)
    now = datetime.now(timezone.utc)

    discovered = discover_repositories(session)
    rows: List[Dict[str, Any]] = []
    for i, repo in enumerate(discovered, 1):
        full_name = repo.get("full_name", "?")
        print(f"[enrich] ({i}/{len(discovered)}) {full_name}", file=sys.stderr)
        try:
            row = enrich_repo(session, repo, now)
        except Exception as exc:  # keep the pipeline resilient
            print(f"[error] {full_name}: {exc}", file=sys.stderr)
            continue
        if row is not None:
            rows.append(row)

    rows.sort(key=lambda r: r["total_score"], reverse=True)

    export_csv(rows, OUTPUT_CSV)
    export_json(rows, OUTPUT_JSON)
    print_summary(len(discovered), rows)
    print(f"Wrote {OUTPUT_CSV} and {OUTPUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
