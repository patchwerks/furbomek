# Build Scout duplicate-title validation — 2026-10-30

Work: [issue 14](https://github.com/patchwerks/furbomek/issues/14).

## Proposed change and synthetic acceptance surface

The duplicate matcher retains literal `title_jaccard` and `shared_terms` and adds
explicit normalized title evidence. A finite lexical vocabulary broadens recall;
action, negation, platform/version and two-sided target mismatch guards narrow
false positives. Matching remains offline, deterministic and advisory. The body
does not supply matching evidence. Ranking, readiness gates and issue/PR overlap
semantics remain unchanged.

[duplicate-corpus.json](duplicate-corpus.json) supplies 20 synthetic title pairs
with expected outcomes and readable explanations. It includes six intended
positive cases and 14 conservative negatives, including one documented recall
limit. `baseline_candidate` entries identify cases suitable for comparison with
the previous three-word/0.6 literal Jaccard rule. They are synthetic expectations,
not claims of measured performance on real issues.

- “Verify offline character broker cancellation” / “Test offline character broker
  abort”: intended additional candidate despite changed wording.
- “Fix camera stream reconnection on Linux” / “… on Windows”: intended rejection
  despite the old rule's high literal overlap.
- “Enable camera stream reconnect retry” / “Disable camera stream reconnect
  retry”: intended rejection of opposite behavior.
- “Keep pending messages after restart” / “Persist queued events across reboot”:
  intentionally missed; this is not a semantic matcher.

Additional tests check literal-vs-normalized scores, explainable phrase mappings,
hostile body text not supplying or overriding evidence, closed-pair filtering,
deterministic pair ordering and unchanged input snapshots. Existing tests cover
issue/PR overlap and ranking/gate behavior.

## Verification status and limits

Observed local verification: the parent ran all 35 tests successfully in the
existing credential-free worker with network, device and host-home access denied.
The implementation worker performed source inspection and `git diff --check`;
it did not execute candidate code outside that boundary. The full suite command
inside the worker was:

```sh
python3 -m unittest discover -s tools/build-scout -p 'test_*.py' -v
```

The parent also compared the original `0734f9c` matcher with the new matcher
inside the isolated worker. All 20 cases matched their expected outcomes:

- Four previously missed paraphrase/inflection cases now produce candidates:
  cancellation, timeout, reconnection and retry.
- Nine previous false-positive cases are suppressed: different platforms,
  components, opposite behavior, negated behavior, versions, one-sided platform
  scope, generic exact titles, direction and add/remove actions.
- Two literal positive cases remain candidates. The unsupported arbitrary
  paraphrase remains missed, as documented.

This deliberately designed synthetic corpus is not a real-world precision/recall
benchmark. Independent review found no blocking issues. Hosted verification is
not yet recorded for this change; earlier hosted results in the historical
validation record do not establish verification of this new matcher.

Synthetic results do not establish precision/recall on the user's live tracker.
No live collection, provider call, runtime integration, hardware operation or
automatic issue closure forms part of this change. Human review remains required;
one-sided unknown qualifiers and identical titles with different body scope can
still generate false positives. Rollback is to return to the previously reviewed
matcher; there is no installed service or persistent state to migrate.
