# claim-registry

- Design docs: `docs/claim-format.md` (claim fields, versioning, how configs cite claims) and
  `docs/governance.md` (editorial rules). Keep code consistent with them; change the doc first.
- Registry data: `claims/<topic>/<id>.yaml` (seed claims, every quote checked against its live
  source) and `vocab/` (allowed model versions and task families).
- Tool: `claimreg/` (Python, needs only PyYAML). Run from the repo root:
  - `python3 -m claimreg validate` checks every claim against the format rules and vocab.
  - `python3 -m claimreg check-quotes [ids]` fetches each source and confirms its quote is there.
  - Tests: `python3 -m pytest -q` (offline; quote tests use fake pages).
- Run both commands before committing claim changes.
- Next: commands that check claims cited in a config, write `claims.lock`, and explain changes.
