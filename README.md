# build-board

[![CI](https://github.com/gerardrecinto/build-board/actions/workflows/ci.yml/badge.svg)](https://github.com/gerardrecinto/build-board/actions/workflows/ci.yml)

A small command-line tool for SDK builds made of many modules that depend on each other. It tells you what order to build in, which modules a change forces you to rebuild, whether any build failed or coverage dropped, and writes one web page that shows all of it. Page and live example: https://gerardrecinto.github.io/build-board/

New here? You describe your modules in one JSON file. `build-board` answers the daily questions: what builds first, what do I rebuild after touching this, and is the SDK bundle pointing at the right tags.

## Try it in 60 seconds

You need Git and Python 3.10 or newer, available as `python3`.

```
git clone https://github.com/gerardrecinto/build-board && cd build-board
python3 -m venv .venv && . .venv/bin/activate
pip install .
build-board plan examples/modules.json
build-board plan examples/modules.json --changed hal
build-board check examples/modules.json
build-board report examples/modules.json --out site-out
```

Output:

```
level 0: driver
level 1: hal
level 2: runtime
level 3: profiler
level 4: sdk_tools

hal
runtime
profiler
sdk_tools

profiler: coverage 60.0% is below 80%
profiler: SDK bundle pins v0.9.0 but the module is tagged v0.9.1
profiler: build failed
sdk_tools: passed, but its dependency profiler is failed
4 problem(s) in 5 modules
```

`check` exits 1 because the sample is broken on purpose. `examples/modules_ok.json` exits 0. Open `site-out/index.html` for the page. The modules in `examples/` are made-up sample data.

## The manifest

```json
{
  "min_coverage": 80,
  "sdk": {"tag": "sdk-2.4.0", "modules": {"hal": "v1.3.2"}},
  "modules": {
    "hal": {"deps": ["driver"], "tag": "v1.3.2", "coverage": "coverage/hal.xml",
            "build": {"status": "passed", "duration_s": 148, "commit": "5be0c3a911"}}
  }
}
```

Build `status` is one of `passed`, `failed`, `running`, `unstable`, `not_built`. Coverage files are Cobertura XML or lcov, and paths are relative to the manifest. Fill the `build` block from your CI (a Jenkins post step can write it).

## What `check` flags

- A build that failed, or one that passed while a dependency did not.
- Line coverage below `min_coverage` (or `--min-coverage`), per module. The page total adds covered and total lines, it does not average percentages.
- A tag that is not semver, such as `latest`.
- An SDK bundle pin that differs from the module's current tag, or pins a module that does not exist.
- A dependency on an unknown module, a module that depends on itself, or a cycle, which is printed as `a -> b -> a`.

## What it does not do

- It does not run builds, fetch artifacts or talk to Jenkins, Gerrit or Perforce. It reads a manifest you write.
- It reads line coverage only. It does not run Klocwork or Parasoft, and it does not read their reports.
- The page is a static snapshot. Regenerate it after each build.
- The dependencies are the ones you list. It does not discover them from source.

## Development

```
pip install -e '.[dev]' && python -m pytest -q
```
