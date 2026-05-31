# Contributing to Open Water Platform (OWP)

We want to make contributing to this project as easy and transparent as
possible. This document explains how to file issues, set up a local
development environment, run the test suite, and submit a pull request.
If anything is unclear, please open an
[issue](https://github.com/Open-Water-Platform/openwater-platform/issues).

## Issues

We use GitHub issues to track public bugs and feature requests. When
you click *New issue* on GitHub you'll be offered structured templates
defined under
[`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/):

- **Bug report** — for something that is not working as expected.
- **Feature request** — for proposing an enhancement or new capability.

Please pick the closest template and fill in the required fields.
Before filing, search existing issues to avoid duplicates.

For usage questions (*how do I…?*), please ask in
[Discussions](https://github.com/Open-Water-Platform/openwater-platform/discussions)
rather than filing an issue. If Discussions is not yet enabled on the
repository, a maintainer can turn it on in Settings → Features.

## Pull requests

All active development of OWP happens on GitHub. We actively welcome
[pull requests](https://help.github.com/articles/creating-a-pull-request).

### Considered changes

OWP is a reference implementation of the Open Water Platform spec.
Changes that comply with the spec are welcome. If your change requires
a change to the spec itself, please open an issue against the spec
first.

### Getting started

1. Fork this repository using the "Fork" button in the upper right.

2. Clone your fork.

   ```bash
   git clone git@github.com:<your-user>/openwater-platform.git
   cd openwater-platform
   ```

3. Install [uv](https://docs.astral.sh/uv/getting-started/installation/),
   the package manager used across the project's Python services.

4. Set up the Python services.

   ```bash
   cd ingestion
   uv sync --all-extras
   cd ../backend
   uv sync --all-extras
   ```

   This creates `ingestion/.venv/` and `backend/.venv/` and installs
   the locked versions of every runtime and dev dependency for each
   service.

   If you would rather use plain pip, each service still supports
   `pip install -e ".[dev]"` from its directory as a fallback.

5. Make your changes on a feature branch.

   ```bash
   git checkout -b <descriptive-branch-name>
   ```

   Add tests for new behaviour and update relevant documentation. See
   [Testing](#testing) below for how to run the suite.

## Testing

The test strategy, layout, and conventions live in
[`docs/testing.md`](docs/testing.md). The short version:

```bash
cd ingestion
uv run pytest tests/unit

cd ../backend
uv run pytest tests/unit
```

The full unit suite runs in well under a second. Continuous integration
runs the same command against Python 3.11 and 3.12 on every pull
request, defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

The contributor rule:

- **If you change behaviour, add or update a test.**
- **If you fix a bug, add a regression test that fails on the old
  code and passes on the new code.**

When integration tests, lint, and typechecking land (tracked in
`docs/testing.md`), this section will grow to mention them.

## Coding style

The project's Python services use type hints throughout and include
docstrings on public callables. Until a `ruff` configuration lands
(planned, see `docs/testing.md`), please follow what is already in
the codebase:

- [PEP 8](https://peps.python.org/pep-0008/) layout.
- Type hints on all public function and method signatures.
- Module and public-callable docstrings; prefer explaining *intent and
  trade-offs* over restating what the code does.
- Imports grouped standard library / third-party / local, separated by
  blank lines.
- `from __future__ import annotations` at the top of new modules so
  forward references work without quoting.

[`ingestion/owp_ingestion/db.py`](ingestion/owp_ingestion/db.py) is a
good reference for the style level we aim for.

## Pull request checklist

Before opening a PR, please confirm:

- [ ] Tests added or updated for any behaviour change.
- [ ] `uv run pytest tests/unit` passes locally from `ingestion/` and
      `backend/` as applicable.
- [ ] Relevant docs updated (`docs/`, service `README.md`, or
      `docs/testing.md` if you changed the test setup).
- [ ] Commit messages explain *why*, not just *what*.
- [ ] No secrets, credentials, or `.env` contents committed.

## License

By contributing to OWP, you agree that your contributions will be
licensed under the [Apache License 2.0](LICENSE).
