# Sprint 1 — Verify the demo and locate the alpha source

Updated October 10, 2026. Status: **closed; Hudson accepted the results and continuation**.

The recorded demo passed its browser journey, saved-review restart, and missing-file rejection checks. Alpha-source discovery found a precise retrieval blocker. Full S02 recovery remains **Blocked**. See the [Sprint 1 review](sprint-1-review.md).

## Sprint goal

A reviewer can launch the current recorded demonstration, inspect its evidence, and save a decision. The team has a trustworthy disposition of the reported toolkit alpha source: a recoverable candidate or a precise access blocker and next action.

This advances the toolkit-first roadmap without committing installation of an unavailable candidate.

**Timebox:** one focused working day. Cap alpha-source discovery at 60 minutes. These are proposed scope limits, not measured delivery estimates.

**Owners and capacity:** Codex owns execution and records; Hudson reviews the demo and next decision. Start one item at a time, with at most two started items including any started blocked recovery work.

**Boundary:** $0 new provider or infrastructure spending. Use the recorded demo and bounded source-location checks. This sprint does not include new live-model runs, tracker writes, publication, merge, or deployment.

## Start conditions checked

- Current source is `c6de6ae`; existing roadmap changes remain local and uncommitted.
- The recorded archive, trusted-checkout launcher, narration, and scope document are present. Python 3.11.9 and `/usr/bin/unzip` are available.
- The exact alpha filename was absent in the four checked locations: Downloads, Desktop, the GitHub parent folder, and this checkout. This does not establish absence everywhere on the machine.
- The cloud chat and reported artifact path are recovery leads. Candidate contents and current access remain unverified.

## Item 1 — Verify and explain the current demonstration

**Execution status:** Done. Codex verification is complete. Hudson accepted the documented results and continuation with “Proceed” on October 10, 2026. This does not claim independent human reproduction.

**Parent story:** S01. **Work type:** research/documentation. **Owner:** Codex. **Dependency:** the existing recorded package and launcher; both are present.

**User story:** As a reviewer or developer, I need a reproducible demo and accurate capability inventory, so that I can evaluate BackIntel and choose the right next step.

**Tasks, in order:**

1. Extract the package into a fresh sprint folder and verify it with the launcher from the trusted checkout.
2. Follow the support narration: original message, interpretation, prediction comparison, corrected result, evidence, and human decision.
3. Save a clearly identified sprint decision. Restart the demo and confirm the decision remains available for that extraction.
4. In a separate disposable copy, alter or remove one required package file. Confirm the trusted launcher rejects it; preserve the original archive and normal demo copy.
5. Update the capability inventory only where observations require it. Keep recorded, synthetic, simulated, historical, and live behavior distinct. Identify the current analysis-workspace entry point without claiming an unexecuted live run.

**Acceptance:** The documented launch works; a reviewer can inspect the stated evidence and retain a decision; the selected package-integrity failure is rejected; documentation accurately describes the execution boundary.

**Demo:** Hudson follows the documented journey, checks one finding, and sees the retained decision after restart. Label the inputs synthetic and the analytical results recorded.

**Owned surfaces and output:** Existing demo instructions, capability inventory, and a short sprint review record. Preserve source, private artifacts, and pre-existing review state. This verifies the recorded demonstration, not the separate alpha or live analyst quality.

## Item 2 — Locate the existing alpha within a bounded investigation

**Execution status:** Done for bounded discovery. The cloud artifact and expected identity are recorded; export or retrieval is needed before full S02 can continue.

**Parent story:** S02, source-discovery task only. **Work type:** manual-task. **Owner:** Codex. **Dependency:** the known cloud-chat/artifact locator, which is available as a lead.

**User need:** As a maintainer, I need the actual candidate location and access requirements, so that we continue preserved work rather than rebuild it from summaries.

**Tasks, in order:**

1. Inspect the reported artifact in “Review testing and demo workflows,” chat `01a10eb2-7340-7052-bf28-f16577c3901a`. Historical locator: `/workspace/backintel-agent-toolkit-0.1.0a2-candidate.zip`.
2. Check an exposed download or source attachment and the specific local paths it identifies. Avoid an unbounded whole-machine search. Do not message another chat or person without explicit authority.
3. If accessible, preserve the candidate separately and inspect its manifest, source identity, package, examples, and relevant run records. Keep credentials and private datasets out of the recovery copy.
4. If access is unavailable or contents conflict, record the exact missing source or access requirement, checked locator, resolution owner, and next retrieval action. Stop discovery at 60 minutes.

**Acceptance:** An alpha recovery record contains either a located and checked candidate or a precise unresolved source/access dependency. A chat report or matching filename alone does not verify contents.

**Parent-story status:** Full S02 is Done only after its original recovery and reconciliation criteria pass. The bounded discovery task may close with an actionable blocker while full S02 remains Blocked or in refinement. Do not claim the alpha recovered from a locator alone.

**Owned surfaces and output:** Bounded source checks, any separately preserved accessible bundle, and an alpha recovery record. Hudson reviews the next retrieval or integration decision. Missing source does not trigger recreation of the alpha.

## First execution commands

Run from `/Users/hudson/Documents/GitHub/BackIntel`. Use a fresh folder; do not overwrite a previous extraction or review.

```sh
backintel_sprint_demo_dir="$(mktemp -d /tmp/backintel-sprint-1-demo.XXXXXX)"
unzip docs/demo/Packages/BackIntelDemoBusinessV4.zip -d "$backintel_sprint_demo_dir"
python3 -m scripts.package_business_demo --package-root "$backintel_sprint_demo_dir/BackIntelDemo" --check
python3 -m scripts.package_business_demo --package-root "$backintel_sprint_demo_dir/BackIntelDemo"
```

Open `http://127.0.0.1:2053/`. Use another local port if occupied. Follow [SupportNarration.txt](../demo/SupportNarration.txt). Run the launcher from the trusted checkout, not Python code supplied by an extracted package.

## Sprint review, stop conditions, and next step

Review two outputs: the observed demo journey and capability inventory; the alpha source disposition with its next action.

Record each committed item as Done, Blocked, or Cancelled according to actual results, and record full S02 separately. A failed required demo check remains failed until understood. Refine any necessary code fix against this bounded outcome before pulling it; do not expand into unrelated cleanup.

Close after the planned review or timebox. Retain useful evidence, stop the sprint's demo server, and remove only disposable sprint copies after their useful records are preserved. Leave the canonical archive and earlier review state intact.

**Successful sprint:** The current demo is directly verified and the alpha source has a trustworthy, actionable disposition. An unresolved source blocker remains explicit and does not turn the demo pass into alpha qualification.

**Next:** Complete full S02 recovery/reconciliation if needed, then refine and pull S03 installation. S03 is not committed now: its candidate and prerequisites are unverified. Even if the bundle appears early, finish the recovery record and agree the next delivery slice rather than silently expanding this sprint.

## References

- [Ordered backlog](agile-backlog.md)
- [Product roadmap](README.md)
- [Current PoC scope](../demo/PoCStatus.txt)
- [Recorded package instructions](../demo/DemoPackage.txt)
