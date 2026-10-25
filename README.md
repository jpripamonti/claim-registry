# claim-registry

A **package registry for AI working knowledge**, built with the mechanics software uses for
dependencies: versioned claims, pinning, diffs, and automatic update notices. Not a site, and not
primarily a knowledge base — a dependency system that prompts and agent configs can declare against.

## The unit is a claim, not a practice

A claim: *technique T, under conditions C (model family, version, task family, reasoning, tool use, context
size), has effect E, supported by evidence of tier X, as of date D.* Conditions are first-class, so
nothing is ever simply "deprecated" — it's "no measurable effect on model Y for task family Z."
Contradictory claims coexist with their evidence; the system records disagreement rather than forcing
a verdict.

## Three evidence tiers, kept visibly separate

- **Asserted** — a vendor doc says so.
- **Observed** — practitioners report it, with their configs and outcomes.
- **Measured** — a standing eval harness re-ran it.

The harness is a long-term research program, not a phase: a curated set of task families, re-executed
on every model release, publishing effect sizes with intervals and the task set itself, so nobody has
to trust the number blind. Its main job isn't ranking techniques — it's catching the moment a
technique stops working.

## Ingestion

Goes well beyond lab docs. Provider guidance is one feed with a diff engine on it. Richer feeds:
changelogs, GitHub issues, and agent configs in the wild (CLAUDE.md, AGENTS.md, system prompts in
public repos) — what people actually do and what they abandon. Opt-in telemetry closes the loop:
user outcomes flow back as observed evidence.

## Execution: a compiler plus a dependency manager

- Describe a project (model, tools, task family, priorities) → it emits a config block where every
  line carries a claim id.
- Existing configs can be linted against the current registry.
- **The real product:** a config declares which registry version it compiled against; when a claim
  it depends on changes, you get a pull request explaining what changed and why, with the evidence.
  Dependabot for prompts.
- A runtime MCP tool exists too, but budgeted and scoped — an agent that fetches advice mid-task is
  the weakest interface.

## Governance (designed first)

An editorial model for who can assert claims, how disputes resolve, a public changelog, open data.
See [docs/governance.md](docs/governance.md) and [docs/claim-format.md](docs/claim-format.md).
Without that, the registry is just one more opinionated blog with a schema.
