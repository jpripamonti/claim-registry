# Claim format

A claim states: *technique T, under conditions C, has effect E, supported by evidence of tier X, as
of date D.* This document defines how a claim is written down, how it is versioned, and how configs
cite it. Who may change claims, and how, is in [governance.md](governance.md).

## Storage

The registry is a git repository. Each claim is one YAML file:

```
claims/<topic>/<id>.yaml
vocab/model-families.yaml
vocab/task-families.yaml
CHANGELOG.md
```

- A **registry version** is a git tag named by date, e.g. `2026-10-25`. Tags are only cut by an
  editor (see governance).
- `vocab/` holds the controlled lists that conditions may use. A value outside the vocabulary is a
  validation error; adding a value is an ordinary registry change.

## Fields

```yaml
id: xml-tags-structure            # stable, kebab-case, never reused, never renamed
version: 1.0.0                    # this claim's own version (see "Versioning")
title: Wrapping prompt sections in XML tags improves instruction following
status: active                    # active | superseded | withdrawn

technique:
  summary: >
    Separate instructions, context and examples into named XML-style tags
    (<instructions>, <document>, <example>).
  example: |                      # optional, a minimal concrete instance
    <instructions>Summarise the document.</instructions>
    <document>...</document>

conditions:                       # where the claim holds; see "Conditions"
  model_family: [claude]
  model_versions: ">=3"           # version range within the family, or "any"
  task_family: [any]
  tool_use: any                   # required | none | any
  context_size: any               # short | long | any  (long = over ~20k tokens)

effect:
  direction: helps                # helps | hurts | no_effect | mixed
  outcome: instruction following and parse reliability
  magnitude: null                 # free text for asserted/observed; numbers only for measured

evidence:                         # one or more items; see "Evidence"
  - tier: asserted
    source: https://example.com/vendor-docs/xml-tags
    retrieved: 2026-10-25
    quote: "..."                  # the exact sentence(s) the claim rests on

as_of: 2026-10-25                 # date the claim was last checked against its evidence
review_by: 2027-04-25             # after this date the claim shows as stale

relations:                        # optional links to other claims, by id
  contradicts: []
  refines: []                     # this claim is a narrower case of another
  superseded_by: null

history:                          # one line per version, newest first
  - 1.0.0 2026-10-25 created
```

### Derived fields

These are computed by the tooling, never written by hand:

- **tier** of the claim: the highest tier among its evidence items that are not under an upheld
  dispute. Order: measured > observed > asserted.
- **stale**: true when today is past `review_by`.

## Conditions

Conditions are what make a claim precise. Rules:

- `any` means the claim is meant to hold everywhere in that dimension.
- `unspecified` means the source did not say. It is different from `any`: an asserted claim from a
  doc that never mentions task type gets `task_family: [unspecified]`, not `[any]`.
- A claim never becomes "deprecated". When a technique stops working on newer models, the existing
  claim's conditions are narrowed (e.g. `model_versions: "<4"`) and a new claim records the new
  behaviour (`direction: no_effect` or `hurts` for `">=4"`).

## Evidence

Every claim needs at least one evidence item. What each tier requires:

| Tier | Required fields | Meaning |
|---|---|---|
| asserted | `source`, `retrieved`, `quote` | A vendor's own documentation says so. |
| observed | `source`, `reported_by`, `config`, `model`, `outcome` | A practitioner reports it, showing the config they used and what happened. |
| measured | `harness_run`, `effect_size`, `interval`, `n` | The registry's eval harness re-ran it. Empty until the harness exists. |

An observed item without a config is not accepted: "it works for me" with nothing to reproduce is
not evidence.

## Contradictions

Contradictory claims coexist. If source A says a technique helps and source B says it does not, the
registry holds two claims, each with its own evidence, linked by `contradicts`. Tools that cite one
of them always show the other.

## Versioning

Each claim has its own semantic version. The kind of change decides the bump:

| Change | Bump | Notifies pinned configs? |
|---|---|---|
| Effect `direction` changes | major | yes, as breaking |
| Conditions narrowed (a setup that matched before no longer matches) | major | yes, as breaking |
| Tier goes down (evidence removed or discredited) | major | yes, as breaking |
| Status becomes `superseded` or `withdrawn` | major | yes, as breaking |
| New evidence at the same or a higher tier | minor | yes, informational |
| Conditions widened | minor | yes, informational |
| A new claim links to this one as `contradicts` | minor | yes, informational |
| `magnitude` refined without changing direction | minor | yes, informational |
| Wording, typos, fixed links, `as_of` / `review_by` dates | patch | no |

The tooling checks this: a change classified lower than the table requires fails validation.

## Citing claims from a config

A config (CLAUDE.md, AGENTS.md, a system prompt) cites a claim with an HTML comment on the line it
depends on, pinned to a major version:

```markdown
Wrap the user's documents in <document> tags. <!-- claim: xml-tags-structure@1 -->
```

A lock file next to the config, `claims.lock`, records what the config was built against:

```yaml
registry: 2026-10-25
claims:
  xml-tags-structure: 1.0.0
```

A config is up to date when every cited claim's current version has the same major number as its
pin and is not withdrawn. A minor or major change produces an update notice explaining what changed,
with the evidence. Major changes are flagged as breaking.

## Worked examples

Sources below are placeholders. The real seed claims will carry verified links and quotes.

**1. Scoped by model version.** Emphatic wording ("CRITICAL: you MUST…") was once advised to make
models follow a rule. A vendor later says newer models follow instructions closely enough that such
wording causes over-application.

```yaml
id: emphatic-caps-older-models
title: Emphatic capitalised instructions improve rule adherence on older models
conditions: { model_family: [claude], model_versions: "<4", task_family: [any],
              tool_use: any, context_size: any }
effect: { direction: helps, outcome: adherence to the emphasised rule }
---
id: emphatic-caps-newer-models
title: Emphatic capitalised instructions cause over-application on newer models
conditions: { model_family: [claude], model_versions: ">=4", task_family: [any],
              tool_use: any, context_size: any }
effect: { direction: hurts, outcome: rule applied where it should not be }
```

**2. Contradiction.** One source reports that "You are an expert X" personas improve factual
answers; another reports no measurable effect. The registry keeps both, linked:

```yaml
id: expert-persona-accuracy
effect: { direction: helps, outcome: factual accuracy }
evidence: [ { tier: observed, ... } ]
relations: { contradicts: [expert-persona-no-effect] }
---
id: expert-persona-no-effect
effect: { direction: no_effect, outcome: factual accuracy }
evidence: [ { tier: observed, ... } ]
relations: { contradicts: [expert-persona-accuracy] }
```
