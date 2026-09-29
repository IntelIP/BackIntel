# Code cleanup

- Install `requirements-dev.txt` and run `vulture runtime scripts tests --min-confidence 90` after Python removals. Pull-request CI runs the same check.
- For cross-file removals, refresh Graphify and inspect callers before deleting. Verify current source and framework registrations.
