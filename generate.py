#!/usr/bin/env python3
"""Generate dark_mode.svg / light_mode.svg for the profile README.

Fetches live stats from the GitHub GraphQL API (stdlib only) and renders a
neofetch-style card: Pac-Man chase ASCII art on the left, dotted-leader info
and stats on the right. Fails loudly on any fetch or render problem so CI
never commits a broken SVG.

Usage:  GH_TOKEN=$(gh auth token) python3 generate.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape

# --- EDIT ME: profile content -------------------------------------------------

LOGIN = os.environ.get("USER_LOGIN", "WaterMenon09")
EXTRA_REPOS = ["lf-connectivity/maveric"]        # external repos counted in LOC
EXTRA_AUTHOR_EMAILS = ["menonpranto@gmail.com"]  # extra commit-author emails for LOC

# --- Layout constants ----------------------------------------------------------

WIDTH, HEIGHT = 1000, 580
ART_X, INFO_X = 15, 385
Y0, PITCH = 35, 20
ROWS = 27
W = 62  # info column width in characters; all dot leaders right-align to this

# --- Palettes (GitHub-native colors) --------------------------------------------

DARK = {
    "bg": "#0d1117", "border": "#30363d", "fg": "#c9d1d9",
    "key": "#79c0ff", "value": "#a5d6ff", "cc": "#616e7f",
    "add": "#3fb950", "del": "#f85149",
    "pac": "#e3b341", "g1": "#ff7b72", "g2": "#f778ba",
    "g3": "#56d4dd", "g4": "#ffa657", "eye": "#e6edf3",
}
LIGHT = {
    "bg": "#ffffff", "border": "#d0d7de", "fg": "#24292f",
    "key": "#0969da", "value": "#0a3069", "cc": "#6e7781",
    "add": "#1a7f37", "del": "#cf222e",
    "pac": "#9a6700", "g1": "#cf222e", "g2": "#bf3989",
    "g3": "#1b7c83", "g4": "#bc4c00", "eye": "#57606a",
}

# --- ASCII art: Pac-Man chase ---------------------------------------------------
# Each row is a list of (class, text) segments. 27 rows, <= 36 visible chars.

GHOST_TOP = " .-'''-.  "
GHOST_UPR = "/       \\ "
GHOST_EYE = ("| ", "o   o", " | ")
GHOST_BODY = "|       | "
GHOST_HEM = "'\\/\\/\\/\\' "


def ghost_band(c_left, c_right, indent="       "):
    """Five rows of two side-by-side ghosts in the given color classes."""
    pad = [("fg", indent)]
    rows = [
        pad + [(c_left, GHOST_TOP), ("fg", " "), (c_right, GHOST_TOP)],
        pad + [(c_left, GHOST_UPR), ("fg", " "), (c_right, GHOST_UPR)],
        pad
        + [(c_left, GHOST_EYE[0]), ("eye", GHOST_EYE[1]), (c_left, GHOST_EYE[2])]
        + [("fg", " ")]
        + [(c_right, GHOST_EYE[0]), ("eye", GHOST_EYE[1]), (c_right, GHOST_EYE[2])],
        pad + [(c_left, GHOST_BODY), ("fg", " "), (c_right, GHOST_BODY)],
        pad + [(c_left, GHOST_HEM), ("fg", " "), (c_right, GHOST_HEM)],
    ]
    return rows


def build_art():
    rows = []
    rows.append([])  # 1
    rows.append([("pac", "        .--\"\"\"--.")])  # 2
    rows.append([("pac", "       /  o      \\")])  # 3
    rows.append([("pac", "      |      ,----'"), ("cc", "  . . . . .")])  # 4
    rows.append([("pac", "      |      '----."), ("cc", "  . . . . .")])  # 5
    rows.append([("pac", "       \\          /")])  # 6
    rows.append([("pac", "        '--...--'")])  # 7
    rows.append([])  # 8
    rows.append([("cc", "             .    .    .")])  # 9
    rows.append([])  # 10
    rows.extend(ghost_band("g1", "g2"))  # 11-15  Blinky, Pinky
    rows.append([])  # 16
    rows.extend(ghost_band("g3", "g4"))  # 17-21  Inky, Clyde
    rows.append([])  # 22
    rows.append([("cc", "     . . . . "), ("pac", "O"), ("cc", " . . . .")])  # 23
    rows.append([])  # 24
    rows.append([("pac", "            R E A D Y !")])  # 25
    rows.append([])  # 26
    rows.append([])  # 27
    assert len(rows) == ROWS, f"art has {len(rows)} rows, want {ROWS}"
    for r in rows:
        assert seg_len(r) <= 36, f"art row too wide: {seg_len(r)} {r}"
    return rows


# --- Info column builders --------------------------------------------------------


def seg_len(segs):
    return sum(len(t) for _, t in segs)


def kv(label, value, value_cls="value"):
    dots = W - len(label) - 1 - 2 - len(value)
    assert dots >= 2, f"line too long: {label}: {value} (over by {2 - dots})"
    return [
        ("key", label), ("fg", ":"),
        ("cc", " " + "." * dots + " "), (value_cls, value),
    ]


def cont(value):
    """Continuation line: value right-aligned to the shared right edge."""
    return [("fg", " " * (W - len(value))), ("value", value)]


def header(user, host):
    rule = W - len(user) - len(host) - 2
    return [("key", user), ("fg", "@"), ("key", host), ("cc", " " + "─" * rule)]


def section(title):
    return [("cc", "─ "), ("key", title), ("cc", " " + "─" * (W - len(title) - 3))]


def build_info(s):
    rows = [
        header("menon", "pranto"),
        kv("OS", "macOS, Ubuntu, Windows"),
        kv("Uptime", s["uptime"]),
        kv("Host", "Cloudly IO"),
        kv("Kernel", "AI/ML Engineer"),
        kv("IDE", "VS Code, Claude Code"),
        kv("Location", "Dhaka, Bangladesh (UTC+6)"),
        [],
        kv("OSS", "Maveric (Linux Foundation Connectivity)"),
        [],
        kv("Languages.Programming", "Python, C/C++, Java, JavaScript, SQL"),
        kv("Languages.ML", "PyTorch, TensorFlow, scikit-learn,"),
        cont("Stable-Baselines3, GPyTorch"),
        kv("Languages.Agents", "LangGraph, LangChain, MCP, RAG, pgvector"),
        kv("Languages.Infra", "FastAPI, Kafka, Docker, Kubernetes, AWS,"),
        cont("PostgreSQL, Redis, Prometheus"),
        kv("Domain", "O-RAN, 3GPP, Bayesian digital twins, RL/PPO"),
        [],
        section("Contact"),
        kv("Email", "menonpranto@gmail.com"),
        kv("LinkedIn", "in/menon-pranto-9789871a1"),
        kv("LeetCode", "WaterMenon"),
        kv("Web", "watermenon09.github.io/Personal-Portfolio"),
        [],
        section("GitHub Stats"),
        stats_row(s),
        loc_row(s),
    ]
    assert len(rows) == ROWS, f"info has {len(rows)} rows, want {ROWS}"
    for r in rows:
        assert seg_len(r) <= W, f"info row too wide ({seg_len(r)}): {r}"
    return rows


def stats_row(s):
    left = [
        ("key", "Repos"), ("fg", ":"), ("cc", " .... "),
        ("value", str(s["repos"])),
        ("fg", " {"), ("key", "Contributed"), ("fg", ": "),
        ("value", str(s["contributed"])), ("fg", "} | "),
        ("key", "Contributions"), ("fg", ":"),
    ]
    contribs = f"{s['contributions']:,}"
    dots = W - seg_len(left) - 2 - len(contribs)
    assert dots >= 2
    return left + [("cc", " " + "." * dots + " "), ("value", contribs)]


def loc_row(s):
    net, add, dele = f"{s['net']:,}", f"{s['additions']:,}", f"{s['deletions']:,}"
    left = [("key", "Lines of Code"), ("fg", ":")]
    tail_len = len(net) + len(" ( ") + len(add) + 2 + len(", ") + len(dele) + 2 + len(" )")
    dots = W - seg_len(left) - 2 - tail_len
    assert dots >= 2
    return left + [
        ("cc", " " + "." * dots + " "), ("value", net),
        ("fg", " ( "), ("add", add + "++"), ("fg", ", "),
        ("del", dele + "--"), ("fg", " )"),
    ]


# --- Uptime ----------------------------------------------------------------------


def format_uptime(created_at, now):
    years = now.year - created_at.year
    months = now.month - created_at.month
    days = now.day - created_at.day
    if days < 0:
        months -= 1
        prev_month_end = now.replace(day=1) - timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12

    def unit(n, word):
        return f"{n} {word}" + ("" if n == 1 else "s")

    return ", ".join([unit(years, "year"), unit(months, "month"), unit(days, "day")])


# --- GitHub GraphQL client ---------------------------------------------------------

API = "https://api.github.com/graphql"


def gql(query, variables=None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    last_err = None
    for attempt in range(3):
        req = urllib.request.Request(
            API,
            data=payload,
            headers={
                "Authorization": f"bearer {os.environ['GH_TOKEN']}",
                "Content-Type": "application/json",
                "User-Agent": f"{LOGIN}-profile-readme",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.load(resp)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code in (403, 429):
                raise RuntimeError(
                    f"rate limited ({e.code}), Retry-After={e.headers.get('Retry-After')}: {detail}"
                ) from e
            last_err = RuntimeError(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            last_err = RuntimeError(f"network error: {e}")
        else:
            if body.get("errors"):
                raise RuntimeError(f"GraphQL errors: {json.dumps(body['errors'])[:1000]}")
            if body.get("data") is None:
                raise RuntimeError(f"empty GraphQL data: {json.dumps(body)[:500]}")
            return body["data"]
        time.sleep(2 ** (attempt + 1))
    raise last_err


BOOTSTRAP_QUERY = """
query($login: String!) {
  user(login: $login) {
    id
    createdAt
    contributionsCollection { contributionYears }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes { nameWithOwner }
    }
    repositoriesContributedTo(
      first: 1,
      contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW],
      includeUserRepositories: false
    ) { totalCount }
  }
}
"""

LOC_QUERY = """
query($owner: String!, $name: String!, $authorId: ID!, $emails: [String!], $cursor: String) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef {
      target {
        ... on Commit {
          history(first: 100, author: {id: $authorId, emails: $emails}, after: $cursor) {
            totalCount
            pageInfo { hasNextPage endCursor }
            nodes { additions deletions }
          }
        }
      }
    }
  }
}
"""


def fetch_contribution_total(years):
    """All-time contributions as GitHub counts them for the profile heatmap
    (commits + PRs + issues + reviews), summed over calendar-year windows."""
    aliases = []
    for y in years:
        aliases.append(
            f'y{y}: contributionsCollection('
            f'from: "{y}-01-01T00:00:00Z", to: "{y + 1}-01-01T00:00:00Z")'
            " { contributionCalendar { totalContributions } }"
        )
    query = 'query($login: String!) { user(login: $login) { ' + " ".join(aliases) + " } }"
    data = gql(query, {"login": LOGIN})
    return sum(v["contributionCalendar"]["totalContributions"] for v in data["user"].values())


def fetch_repo_loc(owner, name, author_id):
    additions = deletions = commits = 0
    cursor = None
    while True:
        data = gql(
            LOC_QUERY,
            {
                "owner": owner, "name": name, "authorId": author_id,
                "emails": EXTRA_AUTHOR_EMAILS, "cursor": cursor,
            },
        )
        repo = data["repository"]
        if repo is None:
            raise RuntimeError(f"repository {owner}/{name} not found")
        ref = repo["defaultBranchRef"]
        if ref is None:  # empty repository
            return 0, 0, 0
        history = ref["target"]["history"]
        for node in history["nodes"]:
            additions += node["additions"]
            deletions += node["deletions"]
            commits += 1
        if not history["pageInfo"]["hasNextPage"]:
            return additions, deletions, commits
        cursor = history["pageInfo"]["endCursor"]


def fetch_stats():
    data = gql(BOOTSTRAP_QUERY, {"login": LOGIN})
    user = data["user"]
    created_at = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))

    contributions = fetch_contribution_total(user["contributionsCollection"]["contributionYears"])

    repo_names = [n["nameWithOwner"] for n in user["repositories"]["nodes"]]
    additions = deletions = 0
    print(f"{'repository':<44} {'adds':>9} {'dels':>9} {'commits':>7}")
    for full_name in repo_names + EXTRA_REPOS:
        owner, name = full_name.split("/")
        a, d, c = fetch_repo_loc(owner, name, user["id"])
        additions += a
        deletions += d
        print(f"{full_name:<44} {a:>9,} {d:>9,} {c:>7,}")

    now = datetime.now(timezone.utc)
    return {
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "contributions": contributions,
        "additions": additions,
        "deletions": deletions,
        "net": additions - deletions,
        "uptime": format_uptime(created_at, now),
    }


# --- SVG rendering ------------------------------------------------------------------


def render_svg(art, info, pal):
    style = "\n".join(
        f"    .{cls} {{fill: {color};}}"
        for cls, color in pal.items()
        if cls not in ("bg", "border", "fg")
    )
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        'font-family="ConsolasFallback,Consolas,Menlo,monospace" font-size="16px">',
        "  <style>",
        "    @font-face {",
        "      font-family: 'ConsolasFallback';",
        "      src: local('Consolas');",
        "      font-display: swap;",
        "      size-adjust: 109%;",
        "    }",
        style,
        "    text, tspan {white-space: pre;}",
        "  </style>",
        f'  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="15" '
        f'fill="{pal["bg"]}" stroke="{pal["border"]}"/>',
    ]
    for x, rows in ((ART_X, art), (INFO_X, info)):
        parts.append(f'  <text x="{x}" y="{Y0}" fill="{pal["fg"]}">')
        for i, segs in enumerate(rows):
            if not segs:
                continue
            y = Y0 + i * PITCH
            inner = "".join(
                escape(text) if cls == "fg"
                else f'<tspan class="{cls}">{escape(text)}</tspan>'
                for cls, text in segs
            )
            parts.append(f'    <tspan x="{x}" y="{y}">{inner}</tspan>')
        parts.append("  </text>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    if not os.environ.get("GH_TOKEN"):
        sys.exit("GH_TOKEN is not set")

    stats = fetch_stats()
    print()
    for k in ("repos", "contributed", "contributions", "additions", "deletions", "net", "uptime"):
        print(f"{k:>12}: {stats[k] if not isinstance(stats[k], int) else format(stats[k], ',')}")

    # sanity gate: a structurally-valid-but-empty result must never overwrite good SVGs
    assert stats["repos"] > 0 and stats["contributions"] > 0 and stats["additions"] > 0

    art = build_art()
    info = build_info(stats)
    for path, pal in (("dark_mode.svg", DARK), ("light_mode.svg", LIGHT)):
        svg = render_svg(art, info, pal)
        assert len(svg) > 5000, f"{path} suspiciously small"
        parseString(svg)  # raises on malformed XML
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(svg)
        os.replace(tmp, path)
        print(f"wrote {path} ({len(svg):,} bytes)")


if __name__ == "__main__":
    main()
