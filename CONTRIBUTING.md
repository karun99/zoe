# Contributing to Project Zoe

Thanks for your interest in contributing. This document explains how to report
bugs, propose changes, and get a change merged.

## Where to get help

- **Bug reports & feature requests:** open a GitHub issue at
  <https://github.com/karun99/zoe/issues>. Please include the command you ran,
  the observed output, and your Python version.
- **Security issues:** please do **not** file a public issue for security
  vulnerabilities. Email the maintainer (see `LICENSE` / the repository owner)
  with a description and reproduction steps so it can be fixed before disclosure.

## Development setup

```bash
git clone https://github.com/karun99/zoe.git
cd zoe
pip install -e ".[dev]"
```

## Running the tests

```bash
pytest -q                 # the full suite (103 tests)
python -m zoe report      # the 7-tier evaluation harness
```

The suite must pass before a change can be merged. `python -m zoe report`
prints the active premortem warnings; a regression in any guarded failure mode
shows up as a tagged `[§n]` line.

## Pull request guidelines

1. **One change per PR.** Keep diffs focused; open separate PRs for unrelated
   work.
2. **Add or update tests.** A behavioural change should come with a test that
   fails without it.
3. **Keep the honesty contract.** If you add a capability, wire it into the run
   path and the 7-tier harness — do not leave mechanisms as dead code that the
   metrics score vacuously. If something is a metaphor or a mock, label it as
   such in the code and the README.
4. **Match the existing style.** The codebase is type-annotated Python with a
   deterministic mock fallback so everything runs without a GPU or model.
5. **Update docs.** If you change a requirement or a layer's responsibility,
   update `docs/` (SRS / REQUIREMENTS traceability) in the same PR.

## Reporting a change to the evaluation metrics

The 7-tier harness (`python -m zoe report`) is the source of truth for
capability claims. If your change affects a metric, report the before/after
value in the PR description so the effect is visible.
