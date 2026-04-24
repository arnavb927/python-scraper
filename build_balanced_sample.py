"""
Build a balanced sample of ~400-500 repositories from mas_repos_summary.json.

Balances across:
  - 5 use-case categories:
      Workflow Automation, Code Generation, RAG + Agents,
      Browser / Terminal Use, Simulation
  - 3 popularity tiers (per user-specified criteria):
      Mainstream : stars >= 5000 AND contributors > 10
      Mid-Tier   : stars >= 500  AND contributors > 3   (and not Mainstream)
      Niche      : everything else (anything < 500 stars, or higher-star repos
                   that fail the contributor thresholds)

No repos are skipped based on tier — Niche is a catch-all.

Each repo is assigned to exactly one primary use case (rarer categories first),
so no duplicates appear in the output.
"""

from __future__ import annotations

import json
import random
from collections import Counter, defaultdict
from pathlib import Path

INPUT_PATH = Path("mas_repos_summary.json")
OUTPUT_PATH = Path("mas_repos_balanced_sample.json")

TARGET_PER_BUCKET = 30  # 5 use cases x 3 tiers x 30 = 450 total
RANDOM_SEED = 42

TARGET_USE_CASES = [
    "Workflow Automation",
    "Code Generation",
    "RAG + Agents",
    "Browser / Terminal Use",
    "Simulation",
]

# Rarer categories first so repos that qualify for them are claimed there.
PRIMARY_PRIORITY = [
    "Simulation",
    "Code Generation",
    "Browser / Terminal Use",
    "RAG + Agents",
    "Workflow Automation",
]

TIERS = ["Mainstream", "Mid-Tier", "Niche"]


def compute_tier(repo: dict) -> str:
    stars = repo.get("stars") or 0
    contribs = repo.get("contributors_count") or 0
    if stars >= 5000 and contribs > 10:
        return "Mainstream"
    if stars >= 500 and contribs > 3:
        return "Mid-Tier"
    return "Niche"


def pick_primary_use_case(labels: list[str]) -> str | None:
    label_set = {l for l in labels if l in TARGET_USE_CASES}
    if not label_set:
        return None
    for candidate in PRIMARY_PRIORITY:
        if candidate in label_set:
            return candidate
    return None


def rank_key(repo: dict) -> tuple:
    # Higher is "better". Sort by total_score, then stars, then contributors.
    return (
        repo.get("total_score") or 0,
        repo.get("stars") or 0,
        repo.get("contributors_count") or 0,
    )


def main() -> None:
    random.seed(RANDOM_SEED)

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        repos = json.load(f)

    buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
    skipped_no_use_case = 0

    for repo in repos:
        tier = compute_tier(repo)

        primary = pick_primary_use_case(repo.get("use_case_labels") or [])
        if primary is None:
            skipped_no_use_case += 1
            continue

        enriched = dict(repo)
        enriched["user_tier"] = tier
        enriched["primary_use_case"] = primary
        buckets[(primary, tier)].append(enriched)

    pool_counts = {k: len(v) for k, v in buckets.items()}

    sampled: list[dict] = []
    sample_counts: Counter = Counter()

    for use_case in TARGET_USE_CASES:
        for tier in TIERS:
            key = (use_case, tier)
            candidates = buckets.get(key, [])
            candidates_sorted = sorted(candidates, key=rank_key, reverse=True)

            if len(candidates_sorted) <= TARGET_PER_BUCKET:
                chosen = candidates_sorted
            else:
                # Take top half by score, then randomly sample the rest
                # from the full ranked list to keep mix of quality + variety.
                top_slice = candidates_sorted[: TARGET_PER_BUCKET * 2]
                chosen = random.sample(top_slice, TARGET_PER_BUCKET)

            sampled.extend(chosen)
            sample_counts[key] = len(chosen)

    # Stable order: group by use case, then tier, then by score desc.
    tier_order = {t: i for i, t in enumerate(TIERS)}
    use_case_order = {u: i for i, u in enumerate(TARGET_USE_CASES)}
    sampled.sort(
        key=lambda r: (
            use_case_order[r["primary_use_case"]],
            tier_order[r["user_tier"]],
            -(r.get("total_score") or 0),
            -(r.get("stars") or 0),
        )
    )

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(sampled, f, indent=2, ensure_ascii=False)

    print(f"Total input repos: {len(repos)}")
    print(f"Skipped (no target use case label): {skipped_no_use_case}")
    print(f"Total sampled: {len(sampled)}")
    print(f"Wrote: {OUTPUT_PATH}\n")

    print("Bucket distribution (use_case, tier) -> sampled / pool")
    print("-" * 70)
    for use_case in TARGET_USE_CASES:
        for tier in TIERS:
            key = (use_case, tier)
            pool = pool_counts.get(key, 0)
            print(f"  {use_case:<24} {tier:<10} {sample_counts[key]:>4} / {pool}")

    print("\nTotals by use case:")
    by_uc = Counter(r["primary_use_case"] for r in sampled)
    for u in TARGET_USE_CASES:
        print(f"  {u:<24} {by_uc[u]}")

    print("\nTotals by tier:")
    by_tier = Counter(r["user_tier"] for r in sampled)
    for t in TIERS:
        print(f"  {t:<12} {by_tier[t]}")


if __name__ == "__main__":
    main()
