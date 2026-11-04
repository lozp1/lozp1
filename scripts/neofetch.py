"""Genera dark_mode.svg y light_mode.svg: una ficha estilo neofetch para el perfil.

Solo usa la biblioteca estandar. Lee el token de GitHub de GH_TOKEN (o GITHUB_TOKEN).
Con el GITHUB_TOKEN de Actions las cifras son solo publicas; con un token personal
(secreto PROFILE_TOKEN) incluyen tambien repos y contribuciones privadas.

Uso:  python scripts/neofetch.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

USER = "lozp1"
ROOT = Path(__file__).resolve().parent.parent
ASCII = (ROOT / "scripts" / "ascii.txt").read_text(encoding="utf-8").rstrip("\n").split("\n")

WIDTH = 58  # caracteres de la columna de datos

THEMES = {
    "dark": dict(bg="#161b22", text="#c9d1d9", key="#ffa657", value="#a5d6ff", dots="#616e7f", art="#58a6ff"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", value="#0a3069", dots="#c2cfde", art="#0969da"),
}


def graphql(query: str, variables: dict, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "lozp1-profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(token: str) -> dict:
    base = graphql(
        """query($login:String!){ user(login:$login){
             createdAt followers{totalCount}
             repositories(ownerAffiliations:OWNER, first:100){ totalCount nodes{ stargazerCount } }
             repositoriesContributedTo(contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){ totalCount }
           } }""",
        {"login": USER},
        token,
    )["user"]
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    commits = 0
    start = created
    while start < now:  # contributionsCollection abarca como maximo un año
        end = min(start + dt.timedelta(days=365), now)
        cc = graphql(
            """query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
                 contributionsCollection(from:$from, to:$to){ totalCommitContributions restrictedContributionsCount }
               } }""",
            {"login": USER, "from": start.isoformat(), "to": end.isoformat()},
            token,
        )["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
        start = end
    return dict(
        created=created,
        repos=base["repositories"]["totalCount"],
        contributed=base["repositoriesContributedTo"]["totalCount"],
        stars=sum(n["stargazerCount"] for n in base["repositories"]["nodes"]),
        followers=base["followers"]["totalCount"],
        commits=commits,
    )


def uptime(since: dt.datetime) -> str:
    today = dt.date.today()
    d = since.date()
    years = today.year - d.year
    months = today.month - d.month
    days = today.day - d.day
    if days < 0:
        months -= 1
        prev_month_end = today.replace(day=1) - dt.timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(years, 'year')}, {plural(months, 'month')}, {plural(days, 'day')}"


def build_lines(s: dict) -> list:
    """Cada linea es una lista de (clase, texto). Clases: key, value, dots, text."""
    def kv(key: str, value: str, width: int = WIDTH):
        dots = width - len(key) - len(value) - 3
        return [("key", key), ("text", ":"), ("dots", " " + "." * max(dots, 1) + " "), ("value", value)]

    def two(k1, v1, k2, v2):
        half = WIDTH // 2 - 1
        return kv(k1, v1, half) + [("text", " | ")] + kv(k2, v2, WIDTH - half - 3)

    def header(title: str):
        return [("text", f"- {title} " + "—" * (WIDTH - len(title) - 3))]

    blank = [("text", "")]
    return [
        [("text", f"franco@{USER} " + "—" * (WIDTH - len(USER) - 8))],
        kv("OS", "Arch Linux, Debian, Windows"),
        kv("Uptime", uptime(s["created"])),
        kv("Host", "Guatemala"),
        kv("Kernel", "Backend · Automation · ERP integrations"),
        kv("WM", "Hyprland (Wayland)"),
        kv("IDE", "VS Code, Qt Designer"),
        kv("Hobbies", "porting PC games to the Switch"),
        blank,
        kv("Languages.Programming", "Python, C#, Rust, TypeScript, C++"),
        kv("Languages.Computer", "SQL, Bash, PowerShell, VBA, Lua"),
        kv("Languages.Real", "Spanish, English"),
        blank,
        kv("Stack.Backend", "FastAPI, .NET 8, PostgreSQL"),
        kv("Stack.Frontend", "Angular, Next.js, Tauri, Tailwind"),
        kv("Stack.ERP/RPA", "JDE Orchestrator, SAP GUI, Salesforce"),
        kv("Stack.Infra", "Docker, Azure, IIS, Power Platform"),
        blank,
        header("Contact"),
        kv("Email", "francopaolo_lg@outlook.com"),
        kv("LinkedIn", "in/franco-lopez"),
        blank,
        header("GitHub Stats"),
        two("Repos", str(s['repos']), "Stars", str(s["stars"])),
        two("Commits", f"{s['commits']:,}", "Followers", str(s["followers"])),
    ]


def render(theme: dict, lines: list) -> str:
    lh, top, pad = 20, 30, 15
    rows = max(len(ASCII), len(lines))
    height = top + (rows - 1) * lh + 25
    width = 985
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,\'DejaVu Sans Mono\',Menlo,monospace" '
        f'width="{width}px" height="{height}px" font-size="16px">',
        "<style>",
        f".key{{fill:{theme['key']}}} .value{{fill:{theme['value']}}} .dots{{fill:{theme['dots']}}} "
        f".text{{fill:{theme['text']}}} .art{{fill:{theme['art']}}} text,tspan{{white-space:pre}}",
        "</style>",
        f'<rect width="{width}px" height="{height}px" fill="{theme["bg"]}" rx="15"/>',
        f'<text x="{pad}" y="{top}" class="art">',
    ]
    for i, row in enumerate(ASCII):
        out.append(f'<tspan x="{pad}" y="{top + i * lh}">{escape(row)}</tspan>')
    out.append("</text>")
    x = 450
    out.append(f'<text x="{x}" y="{top}" class="text">')
    for i, parts in enumerate(lines):
        spans = "".join(f'<tspan class="{cls}">{escape(txt)}</tspan>' for cls, txt in parts)
        out.append(f'<tspan x="{x}" y="{top + i * lh}">{spans}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> int:
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Falta GH_TOKEN o GITHUB_TOKEN", file=sys.stderr)
        return 1
    stats = fetch_stats(token)
    lines = build_lines(stats)
    for name, theme in THEMES.items():
        (ROOT / f"{name}_mode.svg").write_text(render(theme, lines), encoding="utf-8")
    print(json.dumps({k: str(v) for k, v in stats.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
