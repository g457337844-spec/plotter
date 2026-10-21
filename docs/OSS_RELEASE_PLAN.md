# Open-source release readiness — Plotter

**Status: NOT APPROVED FOR PUBLICATION.** Prepared 2026-10-21 for an internal review. The existing GitHub repository remains private.

## Release architecture

A standalone Windows GUI and MCP front end for editable XPS/XRD charts in Origin, distinct from the general-purpose Origin Spectra MCP.

Keep the three repositories separate; use [ECOSYSTEM.md](ECOSYSTEM.md) to document the connections. The proposed primary Codex for OSS application repository is `origin-spectra-mcp`, contingent on an actual clean public release and real maintenance evidence.

## Mandatory publication gate

1. Inventory **all committed files and commit history**, including deleted files, commit messages and tags. Current-file redaction does not erase prior snapshots.
2. Inspect for secrets, keys, tokens, passwords, absolute machine paths, local network addresses, usernames, datasets, identifiable samples and unpublished internal project notes. Rotate any credential that has been exposed.
3. MIT has been selected by the repository owner (2026-10-21) and is included in this review branch. Preserve correct copyright attribution and resolve all separately owned assets and proprietary software obligations before distribution.
4. Create a **new clean-history public export** from an audited allowlist. Do not simply change the visibility of this historical private repository. Include no Git history, binary artifacts, local configuration or generated logs from the private workspace.
5. Validate setup on a clean Windows environment, run tests, issue a real signed/tagged release if applicable, and keep an accurate test-status statement.
6. Review GitHub Actions security (minimal permissions, no untrusted pull-request command execution), maintainers, contributions, issue templates and security reporting.
7. Publish only after a file-by-file review and a provenance/licensing decision. Record public URLs and releases only once they actually exist.

## Project-specific issues

- Remove machine-specific output directories and sample paths from `tools/prepare_release.py` and `tools/finalize_release.py` (including paths to private FTIR data).
- Review all diagnostic scripts in `tests/` and packaging logs for personal paths, machine details and fixture references.
- Confirm ownership and redistribution rights for `assets/` and icons, and check Origin dependencies.
- Publish reproducible source build steps and a clean sample release; ensure released ZIP excludes private data.

## Evidence for Codex for OSS

- Claim **primary maintainer** only if it accurately describes the applicant's role.
- Link the actual public repo, trustworthy release assets, recent substantive commits, CI and maintenance/issue discussions.
- Explain scientific interoperability and the work needed to review contributions, prevent destructive updates and keep Origin/Avantage compatibility.
- Never create fake stars, download counts, PRs or adoption claims.
- The program asks for the email on the applicant's ChatGPT account and an OpenAI Organization ID; neither is inferred from the GitHub profile.
- An application can be drafted in advance; submit it only after the linked repository is genuinely public and the applicant has reviewed the terms.
