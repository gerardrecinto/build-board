"""One self-contained HTML page: build status, coverage and SDK tag consistency per module."""

from __future__ import annotations

from html import escape

from .manifest import Board

CSS = """
:root{--bg:#fff;--fg:#111827;--mut:#4b5563;--card:#f3f4f6;--line:#d1d5db;--ok:#15803d;--bad:#b91c1c;--warn:#b45309;--bar:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#0f172a;--fg:#e5e7eb;--mut:#9ca3af;--card:#1e293b;--line:#334155;--ok:#4ade80;--bad:#f87171;--warn:#fbbf24;--bar:#60a5fa}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:64rem;margin:0 auto;padding:1.5rem 16px 3rem}h1{margin:.2rem 0}.sub{color:var(--mut);margin-top:0}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:1rem 0}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 14px;min-width:8rem}
.card b{display:block;font-size:1.4rem}.tw{overflow-x:auto}table{border-collapse:collapse;width:100%}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:middle;white-space:nowrap}th{color:var(--mut);font-weight:600}
.st{font-weight:600}.passed{color:var(--ok)}.failed{color:var(--bad)}.unstable,.running,.not_built{color:var(--warn)}
.bar{display:inline-block;width:80px;height:8px;background:var(--line);border-radius:4px;vertical-align:middle;margin-right:6px}
.bar i{display:block;height:100%;background:var(--bar);border-radius:4px}.bar.low i{background:var(--bad)}
ul.p{padding-left:1.1rem}ul.p li{margin:.2rem 0}.none{color:var(--ok)}
"""


def render(board: Board, title: str = "Build board") -> str:
    ok = sum(r.status == "passed" for r in board.rows)
    total_cov = board.total_cov
    rows = []
    for r in board.rows:
        if r.cov is None:
            cov = '<span class="sub">none</span>'
        else:
            low = " low" if r.cov < board.min_coverage else ""
            cov = f'<span class="bar{low}"><i style="width:{min(r.cov, 100)}%"></i></span>{r.cov}%'
        rows.append(
            "<tr>"
            f"<td>{escape(r.name)}</td><td>{r.level}</td>"
            f'<td class="st {escape(r.status)}">{escape(r.status.replace("_", " "))}</td>'
            f"<td>{cov}</td><td>{escape(r.tag or '-')}</td>"
            f"<td>{escape(', '.join(r.deps) or '-')}</td>"
            f"<td>{'-' if r.duration_s is None else str(r.duration_s) + 's'}</td><td>{escape(r.commit or '-')}</td></tr>"
        )
    problems = (
        '<p class="none">No problems found.</p>'
        if not board.problems
        else '<ul class="p">' + "".join(f"<li>{escape(p)}</li>" for p in board.problems) + "</ul>"
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><link rel="icon" href="data:,"><style>{CSS}</style></head><body><main>
<h1>{escape(title)}</h1>
<p class="sub">SDK bundle {escape(board.sdk_tag or 'not set')}. Level is the build stage: modules in the same level can build in parallel.</p>
<div class="cards">
<div class="card"><b>{ok} of {len(board.rows)}</b>modules passed</div>
<div class="card"><b>{'n/a' if total_cov is None else str(total_cov) + '%'}</b>line coverage, all modules</div>
<div class="card"><b>{len(board.problems)}</b>problems</div></div>
<div class="tw"><table><thead><tr><th>Module</th><th>Level</th><th>Build</th><th>Coverage</th><th>Tag</th><th>Depends on</th><th>Time</th><th>Commit</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<h2>Problems</h2>{problems}
</main></body></html>
"""
