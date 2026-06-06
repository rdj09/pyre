# Contributing to pyRE

## Dev Setup

```bash
git clone https://github.com/rdj09/pyre
cd pyre
pip install hatch pre-commit
pre-commit install
hatch run test
```

## Running checks locally

```bash
hatch run lint          # ruff check
hatch run fmt           # ruff format (auto-fix)
hatch run typecheck     # mypy --strict
hatch run test          # pytest --cov --cov-fail-under=80
hatch run check-all     # all of the above
```

## Branch naming

- `feat/<short-description>` — new features
- `fix/<short-description>` — bug fixes
- `chore/<short-description>` — maintenance, deps, CI

## PR expectations

1. All CI checks must pass (ruff, mypy strict, pytest ≥80% coverage)
2. New public classes and methods must have Google-style docstrings
3. New behaviour must have tests
4. Update `CHANGELOG.md` under `[Unreleased]`

## PyPI release (maintainers only)

Releases are triggered by pushing a semver tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The `release.yml` workflow builds and publishes to PyPI using OIDC Trusted Publisher.
Before the first release, configure the Trusted Publisher on PyPI:
- Publisher: GitHub Actions
- Repository owner: `rdj09`
- Repository name: `pyre`
- Workflow name: `release.yml`
- Environment name: `release`

## Code style

- `ruff` with `line-length = 100`
- `double` quotes
- Type annotations required on all public API (mypy strict)
- No external runtime dependencies (stdlib only)
