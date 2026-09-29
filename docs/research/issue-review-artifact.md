# Issue-review workspace prototype

**Purpose:** let a reviewer inspect an original issue, decide what needs follow-up, and keep a portable record of that decision.

The local prototype uses the seven real cases and saved predictions from the [first prediction test](issue-prediction-results.md). It does not run new models or change GitHub.

## What the artifact contains

- An oldest-first queue, search, and reviewed count. Unproven predictions do not determine order.
- Original opening text and a GitHub source link. Current source text may differ from the archived snapshot.
- Collapsed experimental estimates, with the failed baseline comparison explained.
- A human decision and reason/next step, saved in browser storage. Export produces JSON with all seven decisions and source identities.
- A deliberate reveal of later outcomes and recorded events. Later history stays hidden during the initial review.

**Local files:** `~/Library/Application Support/BackIntel/Evidence/IssueReviewWorkspace/Review.html` is the workspace. `build.py` rebuilds it from saved evidence; `check.cjs` exercises the browser interactions. `BrowserChecks.json` and desktop/mobile screenshots retain the observed results.

The visual direction reuses the preceding report: light surfaces, system fonts, blue controls, and an amber experimental notice. Native controls and plain-text source rendering keep the prototype small. The reference and required states are recorded in `reference-lock.json` alongside the artifact.

## Verified boundary

Browser checks passed for the seven original texts, saved notes after reload, decision export, hidden/revealed outcomes, search/empty states, keyboard navigation, desktop/mobile overflow, and a visible storage-failure path with export recovery. No automatic external requests or runtime errors occurred. Test decisions were made only in an isolated browser context.

This is a local artifact prototype, not the integrated background application or exact-commit release acceptance. Browser notes can be lost if browser storage is cleared; export is the portable copy. Text interpretation, automated recommendations, shared ownership, and live notifications are not implemented here. No production visual baseline is being approved.

**Next review:** use one case to judge whether the evidence and decision fields support the actual reviewer’s work. That feedback should shape the final artifact before broader integration.
