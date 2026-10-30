# Governance

Rules for who may add or change claims, how disagreements are settled, and what is published. The
claim fields and version rules referred to here are defined in [claim-format.md](claim-format.md).

## Principles

1. **Describe, don't prescribe.** A claim says what a source or a measurement shows under stated
   conditions. Editors do not pick winners between contradictory claims.
2. **Nothing is deleted.** Claim ids are permanent. A wrong claim is withdrawn with a reason; its
   file and history stay.
3. **Evidence carries the weight, not the contributor.** A maintainer's claim needs the same evidence
   as anyone else's.
4. **Everything is public.** Claims, history, disputes and their outcomes are in the repository.

## Roles

- **Contributor**: anyone. Proposes claims, evidence and disputes through pull requests.
- **Editor**: reviews and merges changes, cuts registry versions, rules on disputes. While the
  project is small, the owner is the only editor. More editors are added by the existing editors,
  and their names are listed in `EDITORS.md` (created with the first registry version).
- **Vendor staff** (people working for a model provider) may contribute, but must say so in the
  pull request. They cannot add observed evidence about their own employer's models.

## Admitting a claim

An editor merges a new claim when:

- every evidence item meets its tier's requirements (see the evidence table in claim-format.md);
- for asserted evidence, the editor has opened the source and found the quoted text;
- the conditions say no more than the evidence supports: if the source does not name a task type,
  the claim says `unspecified`, not `any`;
- the claim is not a duplicate. If it says the same thing as an existing claim, the evidence is
  added to that claim instead.

A single observed report is enough to admit a claim. The number of independent reports is shown
alongside it, so readers can weigh it.

## Changing a claim

- Every change is a pull request that states the version bump it makes. Validation rejects a bump
  lower than the version table requires.
- Breaking changes (major bumps) need a written reason in the pull request and a line in
  `CHANGELOG.md`, because they trigger update notices for every config pinned to the claim.
- Asserted claims are re-checked when their source page changes, or by `review_by` at the latest.
  A claim past `review_by` is shown as stale. It is not removed.
- When an editor re-checks a claim, they refresh its source snapshot with
  `python3 -m claimreg check-quotes <id> --save-sources` and commit it with the change.

## Disputes

Anyone can dispute a claim by opening an issue that names the claim and says what is wrong. An
editor resolves it within 30 days with one of these outcomes:

| Finding | Outcome |
|---|---|
| The disputer has contrary evidence | A new claim is added with that evidence, linked as `contradicts` when it meets the definition in claim-format.md. The original stays. |
| The claim's conditions are broader than its evidence | Conditions are narrowed (a major bump). |
| The evidence is misquoted, unreachable or does not say what the claim says | The dispute is recorded on the claim as `upheld` for that item, which stops counting toward the tier. If no evidence remains, the claim is withdrawn. |
| No problem found | The dispute is closed with the reasons written in the issue. |

An editor does not rule on a dispute about a claim they wrote or a source they are connected to.
Another editor does, or, while there is only one editor, the dispute stays open and is recorded
on the claim with status `open`.

## Releases

- An editor tags a registry version after merging changes, at most once a day.
- `CHANGELOG.md` (created with the first registry version) lists, for each version, every claim
  that changed, its bump and a one-line reason.

## Open data

- Claim data is published under CC BY 4.0, so anyone can copy and reuse it with attribution.
- The tooling code (`claimreg/`) is published under the MIT license, see `LICENSE`.
- The registry has no private claims, private evidence or paid tiers of data.

## Open decisions

- How many editors are needed before the single-editor rule for disputes is dropped.
- Whether opt-in telemetry from users can count as observed evidence, and under what privacy rules.
