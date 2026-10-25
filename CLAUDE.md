# claim-registry

- Design docs: `docs/claim-format.md` (claim fields, versioning, how configs cite claims) and
  `docs/governance.md` (editorial rules). Keep code consistent with them; change the doc first.
- Registry data: `claims/<topic>/<id>.yaml` (seed claims, every quote checked against its live
  source) and `vocab/` (allowed model versions and task families).
- No code or dependencies yet. Next: a small command-line tool that validates claims, checks cited
  claims in a config, writes `claims.lock`, and explains changes.
