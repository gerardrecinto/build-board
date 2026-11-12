"""Line coverage from Cobertura XML or lcov. Returns (covered, total) so modules can be summed correctly."""

from __future__ import annotations

import xml.etree.ElementTree as ET


class CoverageError(ValueError):
    pass


def read(path: str) -> tuple[int, int]:
    with open(path, encoding="utf-8", errors="replace") as f:
        head = f.read(2048)
    if head.lstrip().startswith("<"):
        return cobertura(path)
    if "SF:" in head or "TN:" in head:
        return lcov(path)
    raise CoverageError(f"{path}: not Cobertura XML or lcov")


def cobertura(path: str) -> tuple[int, int]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        raise CoverageError(f"{path}: invalid XML ({e})") from e
    covered = total = 0
    for line in root.iter("line"):
        total += 1
        if int(line.get("hits", "0")) > 0:
            covered += 1
    if total == 0 and root.get("lines-valid"):
        total, covered = int(root.get("lines-valid")), int(root.get("lines-covered", "0"))
    return covered, total


def lcov(path: str) -> tuple[int, int]:
    covered = total = 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            if raw.startswith("DA:"):
                parts = raw[3:].strip().split(",")
                if len(parts) >= 2 and parts[1].isdigit():
                    total += 1
                    covered += int(parts[1]) > 0
    return covered, total


def pct(covered: int, total: int) -> float | None:
    return None if total == 0 else round(covered * 100.0 / total, 1)
