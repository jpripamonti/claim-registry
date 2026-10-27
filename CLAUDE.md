# claim-registry

- Design docs: `docs/claim-format.md` (claim fields, versioning, how configs cite claims) and
  `docs/governance.md` (editorial rules). Keep code consistent with them; change the doc first.
- Registry data: `claims/<topic>/<id>.yaml` (seed claims, every quote checked against its live
  source) and `vocab/` (allowed model versions and task families).
- Tool: `claimreg/` (Python, needs only PyYAML). Run from the repo root:
  - `python3 -m claimreg validate` checks every claim against the format rules and vocab, and warns about stale claims.
  - `python3 -m claimreg check-quotes [ids]` fetches each source and confirms its quote is there.
  - `python3 -m claimreg applies --model claude-sonnet --version 5.5 [--context-size long]` lists the active claims that apply to that model.
  - Tests: `python3 -m pytest -q` (offline; quote tests use fake pages).
- CI (`.github/workflows/`) runs tests and validation on every push, and the quote check weekly,
  opening an issue on failure.
- Run both commands before committing claim changes.
- When auditing a project against the claims, check each condition (model, version, input size)
  against measured values, not limits or estimates from the code.
