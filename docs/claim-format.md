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
CHANGELOG.md        # created with the first registry version
EDITORS.md          # created with the first registry version
```

- A **registry version** is a git tag named by date, e.g. `2026-10-25`. Tags are only cut by an
  editor (see governance).
- `vocab/` holds the controlled lists that conditions may use. A value outside the vocabulary is a
  validation error; adding a value is an ordinary registry change.

## Fields

The real claim `claims/long-context/long-context-query-at-end.yaml`, annotated:

```yaml
id: long-context-query-at-end     # stable, kebab-case, never reused, never renamed
version: 1.0.0                    # this claim's own version (see "Versioning")
title: Placing long documents first and the query last improves response quality on long inputs
status: active                    # active | superseded | withdrawn

technique:
  summary: >
    With large inputs (20k+ tokens), put the long documents near the top of the prompt, above the
    query, instructions and examples, so the query comes last.
  example: |                      # optional, a minimal concrete instance
    <documents>...</documents>
    Analyze the annual report and competitor analysis. Identify strategic advantages.

conditions:                       # where the claim holds; see "Conditions"
  model_family: [claude]
  model_versions: any             # any | unspecified | range | list | map (see "Conditions")
  task_family: [unspecified]      # values from vocab/task-families.yaml
  reasoning: unspecified          # enabled | disabled | any | unspecified  (thinking / reasoning models)
  tool_use: unspecified           # required | none | any | unspecified
  context_size: long              # short | long | any | unspecified  (long = over ~20k tokens)

effect:
  direction: helps                # helps | hurts | no_effect | mixed
  outcome: response quality, especially with complex multidocument inputs
  magnitude: up to 30 percent in Anthropic's tests   # free text, or null; numbers only for measured

evidence:                         # one or more items; see "Evidence"
  - tier: asserted
    source: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
    retrieved: 2026-10-25
    quote: >-                     # the exact sentence(s) the claim rests on
      Queries at the end can improve response quality by up to 30 percent in tests, ...

as_of: 2026-10-25                 # date the claim was last checked against its evidence
review_by: 2027-04-25             # after this date the claim shows as stale

relations:                        # links to other claims, by id
  contradicts: []                 # see "Contradictions"
  refines: []                     # this claim is a narrower case of the listed one
  superseded_by: null

disputes: []                      # optional; see "Disputes"

history:                          # one line per version, newest first
  - 1.0.0 2026-10-25 created
```

### Derived fields

These are computed by the tooling, never written by hand:

- **tier** of the claim: the highest tier among its evidence items that have no upheld dispute
  against them. Order: measured > observed > asserted.
- **stale**: true when today is past `review_by`.

## Conditions

Conditions are what make a claim precise. Rules:

- `any` means the claim is meant to hold everywhere in that dimension.
- `model_family` is either a vendor family (`claude`, `gpt`, `openai-o`, `gemini`, …) or one line
  within it (`claude-opus`, `claude-sonnet`, …) when the source names a specific line. Version
  numbers are shared across Claude lines, but not every line has every version (there is an Opus
  4.8 and no Sonnet 4.8), so a claim about "Claude Opus 4.5" uses `claude-opus`, not `claude`.
- `model_versions` is `any`, `unspecified`, a range such as `">=4.6"` or `"<4"`, or a list of exact
  versions such as `["4.5", "4.6"]`. Ranges compare against the ordered version list in
  `vocab/model-families.yaml` and match only versions listed there for that family or line.
  When `model_family` lists several families (typical for a study that tested many models),
  `model_versions` is a map from each family to its own value, e.g.
  `{claude-sonnet: ["3.5"], gpt: ["4o"]}`. A YAML comment names the exact models tested.
- Family `other` holds models outside the vocabulary; its versions are free text.
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
| observed | `source`, `retrieved`, `reported_by`, `config`, `model`, `outcome`, `quote` | A practitioner or study reports it, showing the setup they used and what happened. |
| measured | `harness_run`, `effect_size`, `interval`, `n` | The registry's eval harness re-ran it. Empty until the harness exists. |

An observed item without a config is not accepted: "it works for me" with nothing to reproduce is
not evidence.

## Contradictions

Contradictory claims coexist. If source A says a technique helps and source B says it does not, the
registry holds two claims, each with its own evidence, linked by `contradicts`. Tools that cite one
of them always show the other.

Two claims contradict when they describe the same technique and outcome, at least one model
version falls under both (same family or line, and an overlapping version), and they give
different effect directions. Otherwise they are separate claims with separate conditions:

- Results on different versions of the same family are not a contradiction. A study finding no
  effect on GPT-4o does not contradict one finding an effect on GPT-4; the technique may have
  stopped working.
- Different vendors giving opposite advice for their own models (Google: always use examples;
  OpenAI: try reasoning models without examples first) is not a contradiction either.
- When one source states a rule and an exception to it ("this helps, except on model X"), the
  exception is its own claim with `refines` pointing at the general one. Where both match a
  setup, the narrower claim applies.

## Disputes

An open or decided dispute (see governance) is recorded on the claim:

```yaml
disputes:
  - issue: https://github.com/<org>/claim-registry/issues/12
    evidence: 0          # index of the disputed evidence item, or "claim" for the claim as a whole
    status: open         # open | upheld | rejected
```

An evidence item with an upheld dispute stays in the file but no longer counts toward the tier.

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
| A new claim links to this one as `contradicts` or `refines` | minor | yes, informational |
| `magnitude` refined without changing direction | minor | yes, informational |
| Wording, typos, fixed links, `as_of` / `review_by` dates | patch | no |

The tooling checks this: a change classified lower than the table requires fails validation.

## Citing claims from a config

A config (CLAUDE.md, AGENTS.md, a system prompt) cites a claim with an HTML comment on the line it
depends on, pinned to a major version:

```markdown
Put the documents first and the question last. <!-- claim: long-context-query-at-end@1 -->
```

A lock file next to the config, `claims.lock`, records what the config was built against:

```yaml
registry: 2026-10-25
claims:
  long-context-query-at-end: 1.0.0
```

A config is up to date when every cited claim's current version has the same major number as its
pin and is not withdrawn. A minor or major change produces an update notice explaining what changed,
with the evidence. Major changes are flagged as breaking.

## Finding the claims that apply to a model

`python3 -m claimreg applies --model <family or line> --version <v> [--context-size short|long]`
lists the claims that apply to one model, sorted by id, with each claim's effect direction and the
conditions the user still has to check (task family, reasoning, tool use, and input size when
`--context-size` is not given). A claim applies when:

- its status is `active` (superseded and withdrawn claims are no longer followed);
- one of its `model_family` entries is the given family or line, or the parent family of the given
  line (a claim on `claude` covers `claude-sonnet`; a claim on `claude-opus` covers only Opus);
- the version falls within that entry's `model_versions` (`any` and `unspecified` match every
  version; `unspecified` is shown as a condition to check);
- with `--context-size`, its `context_size` is that size, `any` or `unspecified`.

The family and version must be in `vocab/model-families.yaml`; anything else is an error.

## Examples in the registry

- **Scoped to one model line and version:** `claims/instructions/aggressive-tool-language-overtriggers.yaml`
  (emphatic tool instructions overtrigger on Claude Opus 4.5 and 4.6 only).
- **A rule and its exception:** `claims/reasoning/self-check-instruction-over-verifies-opus-5.yaml`
  refines `self-check-instruction-catches-errors.yaml` (verification instructions help, except on
  Claude Opus 5).
- **Many models from one study:** `claims/reasoning/cot-no-gain-non-symbolic-tasks.yaml` (map form
  of `model_versions`).
