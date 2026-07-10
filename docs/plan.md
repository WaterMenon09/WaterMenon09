# Self-Updating GitHub Profile README — WaterMenon09/WaterMenon09

## Context

Menon wants a neofetch-style GitHub profile README modeled on Andrew6rant/Andrew6rant: ASCII art on the left, dotted-leader info/stats column on the right. The screenshot he referenced is **not** markdown ASCII — it's two SVGs (dark/light) regenerated daily by a GitHub Action pulling live stats from the GraphQL API. We build the same engine, written clean from scratch (no code copied), with three improvements over Andrew's: server-side author-filtered LOC queries (no cache dir, no PAT), stdlib-only Python, and fail-loud error handling so a rate-limit can never commit a broken SVG.

The profile repo `WaterMenon09/WaterMenon09` does not exist yet — creating it is part of the job. Nothing in Personal-Portfolio changes (it's the read-only content source).

## User decisions (locked)

- **Engine:** self-updating SVG — Python generator + GitHub Actions daily cron
- **Art:** water theme (~25 lines, waves/droplet, cyan/blue color bands), nod to "WaterMenon"
- **Uptime:** GitHub account age, live from `user.createdAt` (2022-04-10T17:00:55Z), rendered "X years, Y months, Z days"
- **Stats block (growth stats only):** Repos {Contributed: N} | Commits | Lines of Code (net, with additions++/deletions--). **NO stars, NO followers.**
- **OS line:** `macOS, Ubuntu, Windows`
- **IDE line:** `VS Code, Claude Code`
- **Hobbies line:** `Volleyball, Gaming, making weird little apps`
- **Maveric LOC email filter:** `menonpranto@gmail.com` (in `EXTRA_AUTHOR_EMAILS`; already public in git history)

## Content (canonical, from Personal-Portfolio `src/data/`)

- Header: `menon@pranto`
- Host: Cloudly IO — AI/ML Engineer · Location: Dhaka, Bangladesh (UTC+6)
- OSS: **"Maveric (Linux Foundation Connectivity)"** — this exact phrasing ONLY. Banned anywhere: "Meta-backed", "Nvidia-partnered", Copilot contribution claims, "ping-pong reduction".
- Languages.Programming: Python, C/C++, Java, JavaScript, SQL
- Languages.ML: PyTorch, TensorFlow, scikit-learn, Stable-Baselines3, GPyTorch
- Languages.Agents: LangGraph, LangChain, MCP, RAG, pgvector
- Languages.Infra: FastAPI, Kafka, Docker, Kubernetes, AWS, PostgreSQL, Redis, Prometheus
- Domain: O-RAN, 3GPP, Bayesian digital twins, RL/PPO, xApp/rApp
- Contact: menonpranto@gmail.com · LinkedIn `menon-pranto-9789871a1` · LeetCode `WaterMenon` · Web `watermenon09.github.io/Personal-Portfolio`

## Repo layout (all new, in WaterMenon09/WaterMenon09)

```
README.md                     # <picture> prefers-color-scheme embed of raw SVG URLs + one-line footer
generate.py                   # single stdlib-only script (~300 lines)
dark_mode.svg / light_mode.svg  # generated, committed
.github/workflows/build.yml   # daily cron + workflow_dispatch + push
docs/plan.md                  # this plan, checkbox-tracked (durable-implementation-docs convention)
```

## Technical design

### generate.py (stdlib only: urllib, json, datetime, xml.sax.saxutils, xml.dom.minidom, os)

Structure: `# --- EDIT ME ---` constants block (ART lines, right-column line specs, `EXTRA_REPOS=["lf-connectivity/maveric"]`, `EXTRA_AUTHOR_EMAILS=["menonpranto@gmail.com"]`) → `gql()` helper → `fetch_stats()` → `format_uptime()` → `build_lines()` → `render_svg(palette)` → atomic writes.

**GraphQL (POST api.github.com/graphql, `Authorization: bearer $GH_TOKEN`):**
1. Bootstrap: `user { id, createdAt, contributionsCollection{contributionYears}, repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){totalCount nodes{nameWithOwner}}, repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY,PULL_REQUEST_REVIEW], includeUserRepositories:false){totalCount} }`
2. Commits: one aliased query, `contributionsCollection(from:, to:)` per contribution year (window must be ≤1yr), sum `totalCommitContributions`. This includes Maveric commits automatically.
3. LOC per repo (own 12 + EXTRA_REPOS): `defaultBranchRef { target { ... on Commit { history(first:100, author:{id:$authorId, emails:$emails}, after:$cursor) { pageInfo{hasNextPage endCursor} nodes{additions deletions} } } } }` — server-side author filter means Maveric's size is irrelevant (~16 requests total, ~16 rate-limit points of 1000/hr). Guard null `defaultBranchRef`. **No cache — recompute every run** (13 small repos).

**Token:** default Actions `GITHUB_TOKEN` should suffice (all public data). Verify on first `workflow_dispatch`; fallback = no-scope classic PAT as `ACCESS_TOKEN` secret (script reads generic `GH_TOKEN` env either way).

**Fail-loud rules:** all fetching completes before any file I/O. `gql()` raises on HTTP≠200, on GraphQL `errors` array (API returns 200+errors!), on null `data.user`; 3 retries w/ backoff for transient 502s. Sanity gate before writing: `commits>0 and repos>0 and additions>0 and len(svg)>5000`. Parse-check both SVGs with minidom, write `*.tmp`, `os.replace()`.

**Uptime:** pure-stdlib y/m/d delta with day-borrowing (previous month's length), singular/plural handling.

### SVG (one Python template string + DARK/LIGHT palette dicts → two files)

- `<svg width="980" height="530" font-family="ConsolasFallback,Consolas,Menlo,monospace" font-size="16px">`
- `@font-face { font-family:'ConsolasFallback'; src: local('Consolas'); size-adjust:109%; }` — the only safe font trick; camo blocks all external resources
- **`text, tspan { white-space: pre; }` is mandatory** — alignment dies without it
- Two column-parent `<text>` elements; per-line `<tspan x= y=>` (explicit coords, no `dy` chaining). Art col x=18, info col x=400, 20px line pitch, 25 lines (y=30…510)
- Dot leaders computed in Python: `dots = INNER_WIDTH(≈58) - len(label) - len(value) - punctuation` → all values right-align by construction. Long lines (Languages.*) wrap to indented continuation lines with no leaders
- ASCII art: `ART=[...]` equal-width strings, color-banded art1 (crest, bright cyan) → art2 (mid) → art3 (deep). ASCII + `─` only (no tofu). **Escape everything injected** (`xml.sax.saxutils.escape`) — one raw `<`/`&` kills the whole render
- Palettes (GitHub-native): dark bg `#0d1117` border `#21262d` key `#79c0ff` value `#a5d6ff` leaders `#616e7f` add `#3fb950` del `#f85149` art `#39c5cf/#58a6ff/#1f6feb`; light bg `#ffffff` border `#d0d7de` key `#0969da` value `#0a3069` leaders `#6e7781` add `#1a7f37` del `#cf222e` art `#1b7c83/#0969da/#0550ae`

### Right-column line map (~25 lines)

`menon@pranto` / rule / OS / Uptime (live) / Host / Location / IDE / blank / OSS: Maveric (Linux Foundation Connectivity) / blank / Languages.Programming / .ML (wraps) / .Agents / .Infra (wraps) / Domain / blank / Hobbies: Volleyball, Gaming, making weird little apps / blank / Contact: Email · LinkedIn / LeetCode · Web / blank / `— GitHub Stats —` / Repos: 12 {Contributed: N} | Commits: N / Lines of Code: N (A++, D--). Exact packing settled during the alignment pass.

### .github/workflows/build.yml

```yaml
on:
  schedule: [{cron: "17 2 * * *"}]   # off-hour to dodge cron congestion
  workflow_dispatch:
  push: {branches: [main]}
permissions: {contents: write}       # new repos default token to read-only
```
Steps: checkout@v4 → setup-python@v5 (3.12) → `GH_TOKEN=${{secrets.GITHUB_TOKEN}} python generate.py` (no pip step) → commit-if-changed guarded by `git diff --quiet -- dark_mode.svg light_mode.svg`, author `github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>`, message `chore: refresh profile stats`. **No Claude co-author trailer.** No push recursion (GITHUB_TOKEN pushes don't retrigger). Daily Uptime diff keeps the 60-day cron auto-disable away.

## Steps (checkbox-tracked; commit docs/plan.md first per durable-implementation-docs)

- [x] 1. **Scaffold**: `gh repo create WaterMenon09/WaterMenon09 --public --description "..."`; clone to `~/Desktop/Repositories/WaterMenon09`; commit `docs/plan.md` (this file) + `README.md` with the `<picture>` block (raw URLs will 404 until step 4 — fine)
- [x] 2. **Stats engine**: `generate.py` constants + `gql()` + 3 queries + `fetch_stats()` + uptime fn; run locally `GH_TOKEN=$(gh auth token) python generate.py` — verify printed table: Repos 12, Contributed ≥1, Maveric LOC row present (email filter should lift it above the 2-commit baseline)
- [x] 3. **Renderer**: author water ASCII art, `build_lines()` dot math, `render_svg()`, palettes, sanity gate, atomic writes
- [x] 4. **Visual verification loop** (Playwright): screenshot both SVGs at 980×530; check (a) all leader values right-align, (b) art never crosses x=400, (c) reads as water in both palettes; plus a scratch HTML harness with the README's `<picture>` block under `emulate_media` dark/light to prove source selection. Iterate art/geometry until clean
- [x] 5. **First publish**: commit `generate.py` + both SVGs; check github.com/WaterMenon09 in both GitHub themes (camo caches ~5 min — don't panic-debug staleness)
- [x] 6. **Automation**: add `build.yml`; run via `workflow_dispatch`; verify GITHUB_TOKEN handled all queries (fallback: no-scope PAT as `ACCESS_TOKEN`), bot commit identity correct, immediate re-run hits "No changes" path
- [x] 7. **Wrap-up**: tick checkboxes in committed plan; log worklog entry to Vault hub `01-Projects/personal-portfolio/personal-portfolio.md` (profile README is portfolio-adjacent work); note next-day cron check as follow-up

## Verification

- Local: script prints stats table; minidom parse-check; Playwright screenshots dark+light match alignment rules above
- Live: profile page renders correct variant in both GitHub themes; Action run green; second run no-ops; (next day) exactly one bot commit with rolled Uptime day

## Known limits (accepted)

- LOC counts primary-author + email-filtered commits only; co-authored-by credits still missed. Contributions counter is immune (contributionsCollection).
- Stats numbers today are modest by design choice — growth stats only; stars/followers deliberately excluded until worth showing.

## Deviations from the approved plan (all user-directed or found during execution)

- **Art is a Pac-Man chase, not water waves** — user corrected mid-build: the handle is a watermelon pun, not water, then chose a gaming theme (Pac-Man + four ghosts in canonical arcade colors) from a second option round.
- **"Commits" became "Contributions"** — user asked for GitHub's heatmap metric (`contributionCalendar.totalContributions` summed per calendar year: commits + PRs + issues + reviews). Shows 539 vs 160 raw commits.
- **Workflow race fixes** — the first push-triggered run collided with a concurrent dispatch run (both committed SVGs). Fixed with a `concurrency` group and `checkout ref: main` so queued runs see the previous run's bot commit and no-op via the diff guard. Verified: dispatch ✓, push ✓, idempotent re-run "No changes" ✓.
- **`{Contributed: N}` is public-only under `GITHUB_TOKEN`** (shows 2; the real count incl. private CloudlyIO repos is 10). Workflow reads `secrets.ACCESS_TOKEN || secrets.GITHUB_TOKEN` — adding a repo-scoped PAT as the `ACCESS_TOKEN` secret upgrades the number, no code change needed. Contributions (539) already includes private activity because the account has "include private contributions" enabled.
- **Playwright MCP was unresponsive** during the visual pass; used headless Chrome screenshots instead (same verification, different tool).
