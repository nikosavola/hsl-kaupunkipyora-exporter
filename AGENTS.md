# Agent notes for this repo

See also `CONTRIBUTING.md`'s AI Usage Policy: AI-assisted contributions are welcome, but no unreviewed "AI slop" —
verify, test, and keep output maintainable by a human.

## Translated READMEs must stay in sync

`README.md` is the source. `README.fi.md` mirrors it in full. `README.sv.md` is intentionally abbreviated — it covers
install/usage in brief and points to the English/Finnish versions for everything else
(`> För fullständig dokumentation, se...`).

Whenever `README.md` changes:

- Update `README.fi.md` to match (new sections, changed commands, changed flags — full parity).
- Update `README.sv.md` only if the change is significant enough to matter in a short overview (a new install method, a
  changed core command). Skip it for minor wording/detail changes that the "see full docs" pointer already covers.
- Finnish text should read like a native speaker wrote it — use the `finnish-humanizer`/`suomi-finnish` skills if
  unsure.

## Setup, tests, linting

Use `just` (see `justfile`) — `just install`, `just test`, `just pre-commit`. Python 3.13+, managed with `uv`.

- Pre-commit hooks run via `prek` (a Rust reimplementation), not the Python `pre-commit` CLI. Pin versions come from
  `.pre-commit-config.yaml`.
- **CI lints every file, not just changed ones** (`prek run --all-files`, see `.github/workflows/test.yml`). Touching an
  unrelated file can surface pre-existing lint debt elsewhere; that's not your regression, but it will still fail on
  this PR's run — check whether the failure predates your change before trying to fix it.
- `[tool.ruff] fix = true` in `pyproject.toml`: running `ruff check <path>` **writes**. Use `--no-fix` and explicit file
  paths when just checking, never a bare directory.
- `interrogate` requires 100% docstring coverage (Google style) on `src/`, excluding `tests/` and `__init__.py` files.
  Every new public function/class needs a docstring or CI fails.

## Runtime gotchas

- The CLI does **not** load `.env` files. `DIGITRANSIT_API_KEY` must be actually exported in the shell, or passed via
  `--api-key`. A key sitting unexported in a local `.env` does nothing.
- The station list is cached at `~/.cache/hsl-kaupunkipyora-exporter/stations.json`; `get_stations()` only hits the
  network if there's no cache yet, the cache is corrupt, or `--refresh-stations` is passed. A network failure there
  isn't necessarily a stale-cache problem — don't reach for `--refresh-stations` by reflex.

## Web app (`web/`)

Reuses the same Python modules as the CLI by installing the built wheel into Pyodide — it's not a separate
implementation. After changing anything under `src/`, rebuild before testing the web app: `just serve-web` (builds the
wheel via `just build-web`, then serves `http://localhost:8000/`).

## Agent skill (`skills/hsl-bike-export/`)

`skills/hsl-bike-export/SKILL.md` is the single source of truth for the Claude Code skill that drives this CLI from
natural language. Don't hand-edit a copy anywhere else — `.claude/skills/` and `skills-lock.json` are gitignored
local-install artifacts. To test a local install: `npx skills add . --skill hsl-bike-export --agent claude-code -y`.

## Releases

Bumping `version` in `pyproject.toml` on `main` auto-creates a `vX.Y.Z` tag and GitHub release
(`.github/workflows/release.yml`). Don't bump it as a side effect of an unrelated change.
