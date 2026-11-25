#!/usr/bin/env python3
"""Reescribe la sección <!-- REPOS:START --> … <!-- REPOS:END --> del README
con los repositorios públicos de mangrovex actualizados más recientemente.

Solo usa repos públicos, así que basta con el GITHUB_TOKEN de la Action.
"""
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "mangrovex")
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
LIMIT = int(os.environ.get("REPOS_LIMIT", "6"))
EXCLUDE = {USER, f"{USER}.github.io", "manex_odoo_repository"}
README = Path(__file__).resolve().parent.parent / "README.md"


def fetch():
    repos, page = [], 1
    while True:
        req = urllib.request.Request(
            f"https://api.github.com/users/{USER}/repos?type=owner&sort=pushed&per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": f"{USER}-readme",
                     **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {})})
        with urllib.request.urlopen(req, timeout=30) as r:
            batch = json.load(r)
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def ago(iso):
    d = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d < 1:
        return "hoy"
    if d < 2:
        return "ayer"
    if d < 31:
        return f"hace {d} días"
    if d < 365:
        m = d // 30
        return f"hace {m} {'mes' if m == 1 else 'meses'}"
    y = d // 365
    return f"hace {y} {'año' if y == 1 else 'años'}"


def main():
    repos = [r for r in fetch()
             if not r["private"] and not r["fork"] and not r.get("archived") and r["name"] not in EXCLUDE]
    repos.sort(key=lambda r: r.get("pushed_at") or "", reverse=True)
    rows = ["| Repositorio | Descripción | Lenguaje | Último push |", "|---|---|---|---|"]
    for r in repos[:LIMIT]:
        desc = (r.get("description") or "—").replace("|", "\\|")
        lang = r.get("language") or "—"
        rows.append(f"| [**{r['name']}**]({r['html_url']}) | {desc} | `{lang}` | {ago(r['pushed_at'])} |")
    block = "\n".join([
        "<!-- REPOS:START -->",
        "<!-- Esta sección la actualiza la Action \"Actualizar README\". No la edites a mano. -->",
        *rows,
        "",
        f"<sub>Actualizado automáticamente el {dt.date.today().isoformat()} · "
        f"[ver todos los desarrollos](https://{USER}.github.io)</sub>",
        "<!-- REPOS:END -->",
    ])
    text = README.read_text(encoding="utf-8")
    new = re.sub(r"<!-- REPOS:START -->.*?<!-- REPOS:END -->", block, text, flags=re.S)
    # Evita commits si solo cambió la fecha.
    strip = lambda s: re.sub(r"Actualizado automáticamente el \d{4}-\d{2}-\d{2}", "", s)
    if strip(new) == strip(text):
        print("Sin cambios en el README.")
        return
    README.write_text(new, encoding="utf-8")
    print(f"README actualizado con {min(LIMIT, len(repos))} repositorios.")


if __name__ == "__main__":
    main()
