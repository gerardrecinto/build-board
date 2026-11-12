"""Load the manifest and compute the findings a build page should show."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import coverage, graph

TAG = re.compile(r"^v?\d+\.\d+\.\d+([-+][0-9A-Za-z.-]+)?$")
STATUSES = {"passed", "failed", "running", "unstable", "not_built"}


@dataclass
class Row:
    name: str
    level: int
    deps: list[str]
    status: str
    tag: str
    commit: str
    duration_s: int | None
    cov: float | None
    covered: int
    total: int
    notes: list[str] = field(default_factory=list)


@dataclass
class Board:
    sdk_tag: str
    rows: list[Row]
    problems: list[str]
    min_coverage: float

    @property
    def total_cov(self) -> float | None:
        return coverage.pct(sum(r.covered for r in self.rows), sum(r.total for r in self.rows))


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build(data: dict, base_dir: str = ".", min_coverage: float | None = None) -> Board:
    mods = data["modules"]
    deps = {m: list(v.get("deps", [])) for m, v in mods.items()}
    lv = graph.levels(deps)
    level_of = {m: i for i, group in enumerate(lv) for m in group}
    floor = data.get("min_coverage", 80.0) if min_coverage is None else min_coverage
    sdk = data.get("sdk", {})
    pins = sdk.get("modules", {})
    problems: list[str] = []
    rows: list[Row] = []
    for m in graph.order(deps):
        v = mods[m]
        b = v.get("build", {})
        status = b.get("status", "not_built")
        notes: list[str] = []
        if status not in STATUSES:
            problems.append(f"{m}: unknown build status {status!r}")
            status = "not_built"
        tag = v.get("tag", "")
        if tag and not TAG.match(tag):
            notes.append(f"tag {tag!r} is not semver")
            problems.append(f"{m}: tag {tag!r} is not semver")
        cov_path = v.get("coverage")
        covered = total = 0
        pc = None
        if cov_path:
            try:
                covered, total = coverage.read(os.path.join(base_dir, cov_path))
                pc = coverage.pct(covered, total)
            except (OSError, coverage.CoverageError) as e:
                problems.append(f"{m}: {e}")
        if pc is not None and pc < floor:
            problems.append(f"{m}: coverage {pc}% is below {floor}%")
        if pc is None and not cov_path:
            notes.append("no coverage report")
        if m in pins and pins[m] != tag:
            problems.append(f"{m}: SDK bundle pins {pins[m]} but the module is tagged {tag or 'nothing'}")
        if status == "passed":
            for d in deps[m]:
                ds = mods[d].get("build", {}).get("status", "not_built")
                if ds != "passed":
                    problems.append(f"{m}: passed, but its dependency {d} is {ds}")
        elif status == "failed":
            problems.append(f"{m}: build failed")
        rows.append(Row(m, level_of[m], deps[m], status, tag, b.get("commit", "")[:10], b.get("duration_s"), pc, covered, total, notes))
    for m in pins:
        if m not in mods:
            problems.append(f"SDK bundle pins {m}, which is not a module")
    return Board(sdk.get("tag", ""), rows, problems, float(floor))
