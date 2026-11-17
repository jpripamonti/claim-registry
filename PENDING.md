# Pending

- [ ] The version-bump check that docs/claim-format.md ("Versioning") promises: a change
      classified lower than the table requires fails validation.
- [ ] `check-quotes --save-sources` overwrites a page's snapshot even when one of its quotes is
      missing, which erases the record of what the page used to say. Skip those pages.
- [ ] `audit` report: name the claims filed as not relevant (advice about the calling code, such
      as how to parse the answer, hides there), and show a finding's `relations` when another
      applicable claim refines or contradicts it.
- [ ] Older Gemini evidence still cites ai.google.dev, which now redirects to
      aistudio.google.com; point it at the new addresses (patch-level).
- [ ] Claude Fable 5.2: the best-practices page now names it, but `vocab/` does not list it. Add
      it, widen `written-reasoning-declined-newest-models` to cover it, and ingest its own
      prompting page if Anthropic publishes one.
