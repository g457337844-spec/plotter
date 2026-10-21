# Contributing to Plotter

Thank you for considering a contribution. This repository is being prepared for an independently reviewable open-source release; the private working branch is not itself a published release.

## Scope

A standalone Windows GUI and MCP front end for editable XPS/XRD charts in Origin, distinct from the general-purpose Origin Spectra MCP.

Before opening an issue or pull request, inspect [the project boundaries](docs/ECOSYSTEM.md), [the proposed public release scope](docs/OSS_RELEASE_PLAN.md) and [the security reporting policy](SECURITY.md).

## Development and verification

On Windows with Python 3.13 run `python -m pytest -q`; separately run `python tests/validate_mcp.py`. Real Origin and packaged UI validation requires a licensed Origin installation.

For patches, include a reproducible failing test or a before/after case where feasible. Report OS, software versions and whether verification used mocks, synthetic data or the actual vendor application. Never claim hardware/vendor integration passed when it was not run.

## PR checklist

- [ ] The change addresses an issue or a clearly reproducible problem.
- [ ] Scope and testing limitations are stated accurately.
- [ ] Private paths, credentials, proprietary binaries and user files are excluded.
- [ ] Attribution and licenses are maintained.
- [ ] Existing tests and relevant documentation are updated.
- [ ] Destructive writes to scientific source data are guarded, backed up and verified.

Do not submit private test materials or proprietary vendor SDK binaries. Maintainers review proposed changes for functional correctness, provenance and data safety.
