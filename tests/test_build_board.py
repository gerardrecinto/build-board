import json
from pathlib import Path

import pytest

from build_board import coverage, graph, manifest, report
from build_board.cli import main

EX = Path(__file__).resolve().parent.parent / "examples"


def test_levels_group_parallel_work():
    deps = {"a": [], "b": ["a"], "c": ["a"], "d": ["b", "c"]}
    assert graph.levels(deps) == [["a"], ["b", "c"], ["d"]]
    assert graph.order(deps) == ["a", "b", "c", "d"]


def test_cycle_is_named():
    with pytest.raises(graph.GraphError, match="a -> b -> a"):
        graph.levels({"a": ["b"], "b": ["a"]})


def test_unknown_and_self_dependency():
    with pytest.raises(graph.GraphError, match="not a module"):
        graph.levels({"a": ["zzz"]})
    with pytest.raises(graph.GraphError, match="itself"):
        graph.levels({"a": ["a"]})


def test_affected_follows_indirect_users_and_leaves_the_rest():
    deps = {"a": [], "b": ["a"], "c": [], "d": ["b"]}
    assert graph.affected(deps, ["b"]) == ["b", "d"]
    assert graph.affected(deps, ["c"]) == ["c"]
    with pytest.raises(graph.GraphError, match="unknown module"):
        graph.affected(deps, ["nope"])


def test_cobertura_and_lcov_agree_with_known_values():
    assert coverage.read(str(EX / "coverage/hal.xml")) == (18, 20)
    assert coverage.read(str(EX / "coverage/profiler.info")) == (30, 50)
    assert coverage.pct(0, 0) is None


def test_coverage_rejects_garbage_and_bad_xml(tmp_path):
    bad = tmp_path / "x.txt"
    bad.write_text("hello")
    with pytest.raises(coverage.CoverageError):
        coverage.read(str(bad))
    xml = tmp_path / "x.xml"
    xml.write_text("<coverage><unclosed>")
    with pytest.raises(coverage.CoverageError, match="invalid XML"):
        coverage.read(str(xml))


def test_total_coverage_sums_lines_not_percentages():
    b = manifest.build(manifest.load(str(EX / "modules.json")), str(EX))
    assert b.total_cov == round((16 + 18 + 43 + 30 + 9) * 100 / (20 + 20 + 50 + 50 + 10), 1)


def test_bad_example_reports_every_planted_problem():
    b = manifest.build(manifest.load(str(EX / "modules.json")), str(EX))
    text = "\n".join(b.problems)
    for needle in ["profiler: coverage 60.0%", "pins v0.9.0 but the module is tagged v0.9.1", "profiler: build failed", "sdk_tools: passed, but its dependency profiler"]:
        assert needle in text
    assert len(b.problems) == 4


def test_good_example_is_clean():
    assert manifest.build(manifest.load(str(EX / "modules_ok.json")), str(EX)).problems == []


def test_non_semver_tag_and_unknown_status_and_missing_report(tmp_path):
    data = {"modules": {"a": {"tag": "latest", "coverage": "nope.xml", "build": {"status": "great"}}}}
    probs = "\n".join(manifest.build(data, str(tmp_path)).problems)
    assert "not semver" in probs and "unknown build status" in probs and "nope.xml" in probs


def test_sdk_pin_for_a_missing_module():
    data = {"sdk": {"tag": "x", "modules": {"ghost": "v1.0.0"}}, "modules": {"a": {}}}
    assert any("ghost" in p for p in manifest.build(data).problems)


def test_min_coverage_override():
    b = manifest.build(manifest.load(str(EX / "modules.json")), str(EX), min_coverage=50)
    assert not any("coverage" in p and "below" in p for p in b.problems)


def test_html_escapes_module_names():
    data = {"modules": {"<script>alert(1)</script>": {}}}
    html = report.render(manifest.build(data))
    assert "<script>alert" not in html and "&lt;script&gt;" in html


def test_cli_exit_codes_and_output(tmp_path, capsys):
    assert main(["check", str(EX / "modules_ok.json")]) == 0
    assert main(["check", str(EX / "modules.json")]) == 1
    assert main(["check", str(EX / "modules.json"), "--min-coverage", "50"]) == 1  # still failed build
    assert main(["plan", str(EX / "modules.json"), "--changed", "hal"]) == 0
    assert capsys.readouterr().out.count("\n") > 3
    assert main(["report", str(EX / "modules.json"), "--out", str(tmp_path)]) == 0
    assert "profiler" in (tmp_path / "index.html").read_text()


def test_cli_reports_a_cycle_without_a_traceback(tmp_path, capsys):
    f = tmp_path / "m.json"
    f.write_text(json.dumps({"modules": {"a": {"deps": ["b"]}, "b": {"deps": ["a"]}}}))
    assert main(["plan", str(f)]) == 2
    assert "cycle" in capsys.readouterr().err
