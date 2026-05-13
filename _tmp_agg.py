from pathlib import Path
from collections import Counter, defaultdict

root = Path(__file__).resolve().parent
reports = root / "repo_reports"
mds = [p for p in reports.glob("*.md") if not p.name.startswith("_")]

tier = Counter()
uc = Counter()
arch = Counter()
# filename prefix: usecase__tier__owner__repo.md
crosstab = defaultdict(int)
for p in mds:
    t = p.read_text(encoding="utf-8", errors="replace")
    parts = p.name.split("__")
    if len(parts) >= 2:
        slug_uc = parts[0].replace("-", " ").title()
        slug_tier = parts[1].replace("-", " ").title()
        # normalize tier slug to match LaTeX labels
        tier_map = {"Mainstream": "Mainstream", "Mid Tier": "Mid-Tier", "Niche": "Niche"}
        tm = tier_map.get(slug_tier, slug_tier)
        crosstab[(slug_uc, tm)] += 1

    if not t.startswith("---\n"):
        continue
    e = t.find("\n---\n", 4)
    if e < 0:
        continue
    d = {}
    for ln in t[4:e].splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    tier[d.get("user_tier", "")] += 1
    uc[d.get("primary_use_case", "")] += 1
    al = d.get("architecture_labels", "")
    if al.startswith("[") and al.endswith("]"):
        for it in [x.strip() for x in al[1:-1].split(",") if x.strip()]:
            arch[it] += 1

print("md_count", len(mds))
print("tier", dict(tier))
print("primary_uc", dict(uc))
print("arch_top", arch.most_common(15))
print("--- crosstab filename slug -> count ---")
for (a, b), n in sorted(crosstab.items()):
    print(n, a, b)

# architecture x tier (focused labels)
focus = {"LangGraph", "LangChain", "AutoGen", "CrewAI", "Custom/Other"}
xt = defaultdict(lambda: defaultdict(int))
for p in mds:
    t = p.read_text(encoding="utf-8", errors="replace")
    if not t.startswith("---\n"):
        continue
    e = t.find("\n---\n", 4)
    if e < 0:
        continue
    d = {}
    for ln in t[4:e].splitlines():
        if ":" in ln:
            k, v = ln.split(":", 1)
            d[k.strip()] = v.strip().strip('"')
    utier = d.get("user_tier", "")
    al = d.get("architecture_labels", "")
    if al.startswith("[") and al.endswith("]"):
        for it in [x.strip() for x in al[1:-1].split(",") if x.strip()]:
            if it in focus:
                xt[it][utier] += 1
print("--- arch x tier ---")
for lbl in sorted(focus):
    print(lbl, dict(xt[lbl]))
