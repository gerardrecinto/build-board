"""Module dependency graph: build order, parallel levels, and the rebuild set for a change."""

from __future__ import annotations


class GraphError(ValueError):
    pass


def validate(deps: dict[str, list[str]]) -> None:
    for mod, ds in deps.items():
        for d in ds:
            if d not in deps:
                raise GraphError(f"{mod} depends on {d}, which is not a module in the manifest")
            if d == mod:
                raise GraphError(f"{mod} depends on itself")


def levels(deps: dict[str, list[str]]) -> list[list[str]]:
    """Groups of modules that can build in parallel. Raises GraphError, naming the cycle, if there is one."""
    validate(deps)
    remaining = {m: set(d) for m, d in deps.items()}
    out: list[list[str]] = []
    while remaining:
        ready = sorted(m for m, d in remaining.items() if not d)
        if not ready:
            raise GraphError("dependency cycle: " + " -> ".join(_find_cycle(remaining)))
        out.append(ready)
        for m in ready:
            del remaining[m]
        for d in remaining.values():
            d.difference_update(ready)
    return out


def _find_cycle(remaining: dict[str, set[str]]) -> list[str]:
    node = sorted(remaining)[0]
    seen: list[str] = []
    while node not in seen:
        seen.append(node)
        node = sorted(remaining[node])[0]
    start = seen.index(node)
    return seen[start:] + [node]


def order(deps: dict[str, list[str]]) -> list[str]:
    return [m for level in levels(deps) for m in level]


def affected(deps: dict[str, list[str]], changed: list[str]) -> list[str]:
    """Changed modules plus everything that depends on them, directly or not, in build order."""
    validate(deps)
    unknown = [c for c in changed if c not in deps]
    if unknown:
        raise GraphError("unknown module: " + ", ".join(unknown))
    users: dict[str, list[str]] = {m: [] for m in deps}
    for m, ds in deps.items():
        for d in ds:
            users[d].append(m)
    hit, stack = set(changed), list(changed)
    while stack:
        for u in users[stack.pop()]:
            if u not in hit:
                hit.add(u)
                stack.append(u)
    return [m for m in order(deps) if m in hit]
