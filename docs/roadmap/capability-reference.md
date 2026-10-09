> Detailed reference retained from the previous roadmap. Follow the [focused roadmap](v0.1.0-development-roadmap.md) for current next steps. Earlier sequences and historical status below are not the current work queue. The full capability acceptance contract remains applicable.

# BackIntel capability roadmap — synthetic data, real model execution

**Active direction, corrected 2026-09-26.** Complete the reusable technology capabilities using synthetic source records and known synthetic historical outcomes, with real Jev interpretation and real CatBoost/TabICLv2 execution in the final demonstration. Deterministic simulated responses remain development fixtures and cannot satisfy the final model-execution requirements. Olist is an optional integration example. It does not define the platform user, schema, analysis task, or release sequence. This active plan supersedes the historical Olist release plan retained below.

**Saved-goal correction:** The goal tool supports status changes but does not support editing the saved objective text. Its original simulation-only objective has not been edited or marked complete. This roadmap records the product owner's superseding finish line; real semantic and predictive model execution is required within this same unfinished goal.

## Problem we are trying to solve

**Problem hypothesis for customer validation:** an operations team has records of what is happening, but turning them into a current, defensible decision requires repeated human preparation. Evidence is distributed across structured records and free-text notes. Someone has to assemble context, interpret meaning, reconcile revisions, identify what deserves attention, and explain the result. The repository demonstrates parts of that processing; it does not establish how frequently a real team experiences this pain or what the pain costs.

**The core burden is repeatedly reconstructing decision context.** A supervisor needs to know which cases deserve attention, what changed since the last review, what might happen next, and whether the supporting information is trustworthy. An analyst must first turn scattered inputs into those answers. If a source changes after the report is prepared, some of that work must be repeated. If nobody repeats it, the review can describe an earlier situation while people act on the current one.

This creates three related costs to investigate: **preparation effort** spent gathering and reconciling information; **decision delay** while usable context is assembled; and **follow-up effort** spent checking whether concerns remain open, were corrected, or actually resolved. Mistaken classifications, unsupported predictions, or excessive alerts can add more work than automation removes. The value hypothesis must account for that total burden.

The person doing the preparation and the person accountable for the decision may differ. The analyst needs less repeated assembly and fewer corrections. The supervisor needs a reliable, explainable priority list before the opportunity to act passes. The team lead needs a process that continues when the usual report preparer is unavailable. The economic buyer and the size of each pain remain unvalidated.

### Current workflow and where it hurts

The following is the target workflow to investigate with a real team. Consequences are hypotheses, not observed customer outcomes. Capability numbers refer to the full roadmap below.

| Work people perform | Pain or failure point | Why it matters to the decision | Roadmap response |
| --- | --- | --- | --- |
| Decide what to monitor and what counts as a problem. | Definitions live in a person's judgment or differ between reviewers; the prediction target and time horizon may be unclear. | Two reviewers can prioritize the same case differently, and a model can optimize the wrong outcome. | 1: explicit task, question, target, audience, and policy contracts. |
| Collect and reconcile records. | Exports, identifiers, duplicates, late records, and corrections need manual reconciliation. | Cases can be missed or counted twice; a new export can silently change the basis of a finding. | 2–3: source admission, revisions, and preserved evidence links. |
| Read notes to understand what happened. | Important meaning is buried in text; classification consumes attention and varies between people. | A status field or count can omit the reason a case deserves attention. Ambiguous language can be mistaken for a fact. | 4: typed interpretation, distributions, correction history, and required uncertainty handling. |
| Combine findings with historical facts and outcomes. | Analysts reconstruct which information was available when; outcome labels may be incomplete or arrive later. | A convincing retrospective explanation can become an invalid prediction if it uses information from the future. | 5–6: time-safe features, separately available outcomes, and reproducible predictor preparation. |
| Decide whether a prediction is useful enough to rely on. | A plausible score can be accepted without a fair baseline comparison or a recorded approval decision. | The team may spend time on an inferior model or treat experimental output as operational guidance. | 7–8: comparable evaluation and controlled model activation, fallback, and rollback. |
| Reassess cases as information changes. | Someone must notice the change, remember to rerun the right work, and identify which earlier results are affected. | Decisions can use stale inputs; indiscriminate reruns can duplicate work, retrain needlessly, or repeat charges. | 9–11: targeted updates, durable jobs, and persistent triggers. |
| Prepare and defend the review. | Findings, calculations, source excerpts, and report versions must be assembled again for different audiences. | Review time is spent reconstructing the evidence; users cannot readily tell facts, estimates, and unknowns apart. | 13–14: scoped reports, traceable outputs, and restricted execution for generated artifacts. |
| Keep concerns open until they are actually resolved. | Repeated alerts obscure new information; acknowledgment, silence, and missing data can be mistaken for resolution. | A case can be neglected, repeatedly escalated, or closed without evidence that its condition changed. | 12: persistent attention state, deadlines, staleness, and controlled local delivery. |
| Operate the process through interruptions and increasing workload. | Failed runs, restarts, and unmeasured costs require manual checking and recovery. | The team cannot depend on the review arriving complete, once, and within agreed limits. | 15–16: operational controls and a repeatable integrated demonstration. |

### Worked use case: preparing a support operations review

**Illustrative workflow using the existing support domain; not a deployed customer process or a commitment to a first customer.** A supervisor must decide which unresolved service problems require investigation. The raw material includes ticket notes and approved structured facts. Prediction is relevant only if a specific future outcome, usable historical labels, and an action the team can take are defined.

1. **Before the review, an analyst rebuilds the case context.** A ticket says a problem is resolved, but a later note says the problem returned. The analyst must distinguish the old state from the new statement and connect both to the right case. Counting tickets or copying the latest status does not settle the contradiction. The desired automation preserves both versions, extracts the relevant finding, and makes its evidence and uncertainty visible.
2. **The analyst determines whether the change deserves attention.** The note must be considered alongside current facts and the agreed review policy. If prediction is justified, a model estimates the defined future outcome. The desired result separates the observed change, the model's estimate, and the policy condition that caused the flag. It does not present a prediction as an observed incident or proof of its cause.
3. **The supervisor checks the finding and decides what to do.** A flag without usable source evidence transfers the preparation burden to the supervisor. The review therefore needs the changed condition, supporting records, freshness, uncertainty, and current attention state together. Investigation, assignment, and intervention remain human decisions.
4. **Another correction arrives after the review.** The earlier finding may no longer be valid. The desired workflow identifies affected results, retains the prior explanation, recomputes what changed, and updates the review. It avoids treating every refresh as a new reason to interrupt someone.
5. **At the next review, the concern still needs a disposition.** Acknowledgment means someone saw it; resolution needs evidence under the agreed policy. New outcomes, overdue responses, and stale inputs need distinct treatment. Maintaining that continuity is part of the product, rather than leaving the next analyst to reconstruct it again.

The intended unit of value is **one current, defensible case in an operational review**, not a model response or a generated report file. A useful case tells a reviewer what changed, which inputs support it, which parts are estimates or unknown, why it meets the attention policy, and whether it is new, ongoing, acknowledged, stale, or resolved. The complete review also makes coverage and missing inputs visible so an empty queue cannot be confused with proof that nothing is wrong.

### Where the value hypothesis is strongest

The strongest candidate workflow repeats, uses stable questions, depends partly on text that existing fields do not capture, and requires follow-up as conditions change. The team must have access to the relevant sources and a practical response when a finding matters. Prediction additionally needs a meaningful target, reliable outcomes, and sufficient evaluation data.

The likely value is less repeated preparation, earlier access to reviewable information, and more consistent follow-up. These are intended outcomes, not measured benefits. Classification accuracy alone is insufficient if verification takes longer than reading the original notes. Prediction accuracy alone is insufficient if the team cannot act on the estimate. More alerts are not evidence of better prioritization.

The full capability may be unnecessary when the job is a one-time summary or an existing structured report already supports the decision reliably. Missing identifiers, inaccessible sources, unclear ownership, or absent outcome labels can be upstream blockers that interpretation and prediction do not solve. A simpler rule may outperform a model for a particular decision; the comparison must allow that result.

### Validate the problem with the workflow owner

Before claiming business value, observe a real review from source collection through follow-up. Ask the preparer to show the last completed review, trace one difficult case to its original records, and show what happened when a source changed or the usual preparer was absent. Identify the decision owner, action deadline, actual intervention, and recorded outcome. Record observed steps separately from interview opinions and product assumptions. Do not infer demand or willingness to pay from the synthetic demonstration.

| Question to test | Evidence and measurement |
| --- | --- |
| Is repeated preparation a material burden? | Record human minutes spent gathering, reading, reconciling, preparing, checking, correcting, and following up per comparable batch. Include the checking and correction effort required by automation. |
| Does usable information arrive too late? | Measure time from relevant source availability to a reviewable finding and then to human review. Keep source-delivery delay separate from BackIntel processing delay. |
| Are extracted findings trustworthy enough? | Compare a declared sample with independently adjudicated meanings; record incorrect answers, unknowns, and human corrections. Valid JSON alone does not answer this question. |
| Does the queue improve prioritization? | Review flagged and unflagged cases for unnecessary flags and missed cases, using agreed definitions and available outcomes. Separate a correct policy flag from a useful business intervention. |
| Does follow-up remain accurate? | Trace reopened, corrected, acknowledged, stale, and resolved cases across reviews; check duplicate interruptions and cases closed without supporting evidence. |
| Is the total burden lower? | Compare human effort and measured provider/compute costs for the same work and quality requirements. Keep unknown costs explicit; avoid counting shifted review work as savings. |

Agree on success thresholds with the workflow owner before a pilot. A comparison can use the same frozen inputs for manual and assisted preparation; a live pilot must also examine late arrivals, corrections, and response timing. If the problem is rare, current preparation is already cheap and reliable, or automation adds more checking than it removes, narrow or reject the use case. Improved downstream outcomes require separate evidence about interventions and their effects; a before/after report alone does not establish causation.

This discovery and pilot work evaluates the business hypothesis. It does not replace or silently expand the existing synthetic-data, real-model technical acceptance contract.

### Researched next experiment: public issue response-gap review

**Selected by the user for action planning on 2026-09-28; execution remains pending.** Use public software issue triage as the first real-data evaluation of the support-review pattern. This selection does not approve a dataset/model run or replace the existing release contract. Keep the two synthetic scenarios for controlled capability acceptance. This experiment adds a concrete external example; it does not make GitHub the platform's domain model.

**User and decision:** a repository's rotating inbox reviewer decides which new issues warrant a closer look before they remain open without a recorded maintainer response. BackIntel prepares a local review queue and evidence packet. It does not assign, label, comment on, or close live issues.

**Documented process:** VS Code describes a rotating inbox tracker, feature-area owners, and automated classification; people handle issues the bot does not correctly triage. Its automation also manages requests for more information and follow-up. Therefore, the hypothesis is an improvement to evidence preparation and response-gap review alongside existing automation, not replacement of an entirely manual process. These documents establish a real workflow, not measured demand for BackIntel or proof that Microsoft needs this product. See [Issue Tracking](https://github.com/microsoft/vscode/wiki/Issue-Tracking), [Issues Triaging](https://github.com/microsoft/vscode/wiki/Issues-Triaging), and [Automated Issue Triaging](https://github.com/microsoft/vscode/wiki/Automated-Issue-Triaging).

**Pain to test:** the reviewer must read a new issue, determine whether it describes a failure, check whether reproduction steps and environment details are present, distinguish a reported regression from a general request, and reconstruct subsequent comments and state changes. A bare count, label, or risk score does not provide that decision context. The intended benefit is a review packet that reduces reading and reconstruction while maintaining correction quality and follow-up accuracy. Preparation effort and prioritization benefit remain unmeasured.

#### Dataset and bounded cohort

- **Primary source:** [GH Archive](https://www.gharchive.org/) creation-time `IssuesEvent` records for `microsoft/vscode`, with comment and issue-state events. Preserve raw event IDs, timestamps, source locations, and hashes. GH Archive supplies hourly JSON event archives and a BigQuery representation; no paid query or bulk download was performed during this research.
- **Cross-check:** paginate the GitHub issue comments and issue-event APIs for selected records. Present-day issue bodies, labels, assignments, reactions, and comment counts must not substitute for creation-time feature snapshots. Missing event coverage or unavailable records become unknown/excluded cases, not invented negative outcomes.
- **Proposed cohort:** 112 non-pull-request issues with nonempty initial text and a complete observable seven-day outcome window: 64 training issues opened January 1–24, 2024; 16 calibration issues opened February 1–21; 32 held-out issues opened March 1–24. Follow outcomes through March 31. These are target counts, not a completed data profile. Within each window, select the earliest eligible records in `(created_at, issue_id)` order. Freeze the manifest before model execution; do not select on whether a prediction succeeds.
- **Feasibility gate:** first reconstruct 20 creation snapshots and outcome histories. Require both target classes in the proposed training cohort. If coverage, fields, or class balance are inadequate, record the reason and revise the cohort before freezing it. Keep the initial training/context set at 64 rows; a later larger study is separate.
- **Why a 2024 cohort:** GitHub [announced removal of author-association fields from several Events API payloads in 2025](https://github.blog/changelog/2025-08-08-upcoming-changes-to-github-events-api-payloads/). Historical and current schemas cannot be assumed interchangeable. Verify the actual archived schema before relying on association fields.
- **Rights and access:** public visibility is not a blanket redistribution license. Verify applicable source and contribution terms before model use or redistribution; see [GitHub's user-generated content terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#d-user-generated-content). Ship authored synthetic examples and a permitted retrieval/manifest path by default, rather than embedding third-party issue text in an open-source release. The previous model-use approval covers synthetic data, so it does not authorize this real-data experiment or its provider calls.

**Small source check completed:** GitHub's issue search returned 226 non-PR issues opened January 1–7, 2024. Three records were inspected; two comment histories were checked. [Issue #201650](https://github.com/microsoft/vscode/issues/201650) was created January 1 at 00:54:06 UTC; its first currently visible collaborator comment is January 17 at 09:03:15 UTC, and its returned issue-event history contains no close/reopen events. [Issue #201652](https://github.com/microsoft/vscode/issues/201652) was closed as a duplicate on January 2. This confirms accessible text/timestamps and contrasting histories in a small sample. It does not establish archive completeness, initial-text integrity, cohort label distribution, or model performance. Deleted or otherwise unobservable activity remains a limitation.

#### Exact prediction question and allowed inputs

**Proposed target:** at issue creation, estimate whether the issue will be open seven days later without a recorded, non-bot maintainer comment during that interval. This is an observable response-gap proxy. It is not bug severity, customer harm, an official service-level violation, or proof that nobody worked on the issue through another channel.

Define a qualifying maintainer comment using the archived comment's `OWNER`, `MEMBER`, or `COLLABORATOR` association, excluding the issue author and a frozen bot-account list. Do not rely only on the account `type`: automation can use ordinary user accounts. A contributor outside those roles does not automatically count as a maintainer. Unknown historical association or incomplete required coverage blocks that record's label.

For `deadline = issue_created_at + 7 days`, label a case `1` only when reconstructed state is open at the deadline and no qualifying comment is recorded by that deadline; label `0` when an observed qualifying response exists or reconstructed state is closed at the deadline. Replay close and reopen events in order. Freeze the treatment of ambiguous histories and exclusions before training. Record outcome availability at the deadline so training cannot use an immature outcome.

Use two feature sets on identical cases:

- **Facts only:** creation hour/weekday and deterministic measurements of the initial title/body, such as length, code-block presence, and link count. Exclude usernames and all future comments, labels, assignments, closure fields, and final reaction totals.
- **Facts plus Jev findings:** fixed questions about whether the initial text reports a failure, includes reproduction steps, states expected versus observed behavior, provides environment/version information, and claims something previously worked. Preserve the source text reference, returned distributions, unknowns, and model/request identity. These are claims in the issue text, not verified technical diagnoses.

Fit the baseline, CatBoost, and TabICLv2 on the same chronological data. Compare facts-only and facts-plus-findings routes. Evaluate probability quality with Brier score and response-gap retrieval at a fixed review capacity, alongside a simple oldest-open-unanswered review policy. The model estimates response-gap likelihood; it must not silently become an urgency or severity score. If semantic findings do not improve prediction, retain the stronger baseline and assess whether the structured review packet still helps the reviewer.

#### Action plan: testing and visible demonstration

**Business result to demonstrate:** a rotating inbox reviewer can move from an unread issue to an evidence-linked review decision, then see the packet update when a response or state change arrives. The pain being tested is repeated reading, checking, and reconstruction of the same case. A prediction alone does not satisfy this result.

**Delivery status:** this is a plan, not an implemented or validated GitHub demo. Existing local reports, audience views, background jobs, and evidence storage provide starting points. The GitHub adapter, historical cohort, uncertainty handling, and scenario-specific views still need work. The current validation manifest also needs complete visual, operational, and security coverage before integrated acceptance can pass. Existing fixture checks and isolated model runs do not prove this new journey.

**Authority and ownership:** the user owns product tradeoffs, the pilot target, and execution approval. A single implementation owner should integrate the adapter, views, and evidence; a named repository reviewer should adjudicate interpretation examples and run the usefulness pilot. Those people are not yet assigned. This request authorizes the plan only. No Plane changes, provider calls, dataset ingestion, live GitHub changes, deployment, or publication are part of preparing it. The prior synthetic-data model approval does not cover public issue content. Keep at most three work items active; split each milestone into bounded implementation sessions when execution is authorized.

##### What the audience will see

Use the existing local audience viewer and report packaging, extending them for this workflow. Keep engineering diagnostics in a separate operator view.

| View | What it shows | What the reviewer should understand |
| --- | --- | --- |
| Review overview | Repository, cohort dates, replay clock, cases ready for review, incomplete cases, last update, and execution mode. | What information is available now and what is still missing. Progress reflects recorded work, not an animated simulation of live processing. |
| Original issue and findings | Creation-time title/body alongside the five structured questions, source references, supported answers, and explicit unknowns. | What the text actually says, what the model inferred, and what needs checking. Missing reproduction steps must remain missing. |
| Prediction comparison | Creation-time feature cutoff, response-gap definition, five comparable routes, sample counts, probability scores, and fixed-capacity results. | Whether semantic findings add value over simpler methods. Outcome labels stay hidden in the walkthrough until the replay clock reaches their availability time. |
| Review queue and case detail | Source link, review reason, predicted seven-day response-gap likelihood, current observed state, uncertainty, and a local reviewer decision/note. | Where closer review may help. The queue must not present the probability as severity or urgency. No assignment or message is sent to GitHub. |
| Case timeline | Initial snapshot, original prediction, actual recorded comments and close/reopen events, deadline, packet updates, and local attention changes. | How the standing workflow keeps the packet current. Later facts never overwrite the original prediction. |
| Operator evidence | Run and candidate identity, source/model versions, stage results, failures, retries, measured usage, and evidence links. | Which checks passed, failed, or remain blocked, without cluttering the business-facing review. |

Every screen must distinguish **authored fixture**, **replay of recorded actual model output**, and **new model execution**. Historical source events and deliberately injected test faults must also be visibly different. Replaying stored output does not incur or imply a new provider call.

##### Milestones and dependency order

| Milestone | Bounded deliverable and owned surface | Completion check and stop condition |
| --- | --- | --- |
| 1. Establish usable evidence | Data owner reconstructs 20 histories, then freezes the proposed 112-case manifest, exclusions, source rights/access decision, cutoff rules, and label policy described above. No model fitting. | Every admitted case has its original snapshot and sufficient observable outcome coverage; hashes and ordering reproduce. Unknown coverage is excluded with a reason. Stop if trustworthy creation text or outcome labels cannot be recovered; revise the cohort before continuing. |
| 2. Define trustworthy interpretation | Workflow reviewer adjudicates a small development set for the five questions, including absent and ambiguous information. Implementation owner defines the output schema, unknown policy, and deterministic truth fixtures. Repair the validation manifest's missing required coverage in a separate bounded task. | Freeze scoring and acceptance thresholds before held-out model results are inspected. Missing evidence cannot silently become a confident answer. Unsupported outputs fail validation; required validator entries must actually execute checks. |
| 3. Build one complete fixture journey | Implementation owner adds the issue adapter/task contract, explicitly extends the current support/equipment allowlists, and connects normalized sources to findings, prediction, local review, timeline, and artifacts. Use authored fixtures first. Depends on milestone 2; real adapter inputs depend on milestone 1. | One command can produce a clearly labelled fixture package. The reviewer can follow a case across all audience views. Negative-case checks below pass. No fixture output is represented as a real model result. |
| 4. Run the frozen real-data comparison | After separate data/model-use and capped provider approval, run baseline, CatBoost facts, CatBoost facts plus Jev, TabICLv2 facts, and TabICLv2 facts plus Jev. Preserve actual replies, usage, identities, and identical split manifests. Depends on milestones 1–3. | All routes report on the same 32 held-out cases or report the entire comparison blocked; do not silently drop failures. Record Brier score, retrieval at the agreed capacity, and comparison with oldest-open-unanswered. Show losses as well as gains. Missing required usage telemetry blocks completion. |
| 5. Deliver a repeatable demonstration | Package actual outputs and historical replay locally, with an exact candidate identity, operator evidence, starting-state reset, walkthrough, and fixture fault cases. Depends on milestone 4 for a real-data demo; milestone 3 supports a separately labelled fixture preview. | Complete the walkthrough twice from reset without new model calls; predictions and substantive state transitions agree, excluding run IDs and timestamps. Required exact-candidate checks end as passed, failed, or blocked. No missing check counts as passed. |
| 6. Measure reviewer usefulness | Named reviewer compares source-only preparation against the assisted packet on comparable disjoint cases, with counterbalanced order. Record reading, checking, and correction time plus material mistakes. Depends on milestone 5. | Report measured results and limitations. Proposed target: at least 30% less preparation time with no increase in material errors; workflow owner must agree before the pilot. A failed target is an informative result, not a reason to alter cases or claim success. |

The critical sequence is evidence → interpretation contract → complete fixture journey → approved real comparison → repeatable demonstration → human usefulness pilot. Validation-manifest repair can run alongside data feasibility. Do not begin model experiments while the target, feature cutoff, or interpretation contract is unsettled.

##### Repeatable walkthrough: approximately ten minutes

Select cases by a frozen rule before looking at model success: earliest eligible held-out case with an observed qualifying response, earliest observed response-gap case, and earliest closed-at-deadline case. Add the first extraction failure or disagreement in cohort order if one exists. If a category is absent, disclose it and use an authored fixture solely for the missing behavior. The researched public examples above are candidates for explanation, not accepted ground truth until their histories are reconstructed.

1. **Start at the frozen clock (one minute).** Show the reviewer’s job, source dates, mode badge, and initial queue. State the exact prediction question and the human decision still required.
2. **Inspect the original text (two minutes).** Open a case. Compare its five structured observations with the source. Show one missing or ambiguous field and how the packet asks for human checking.
3. **Explain the prediction (two minutes).** Show only creation-time inputs, the selected route, and its response-gap estimate. Explain selection using calibration data; do not tune the model on the holdout. Reveal the aggregate comparison as a separate retrospective evaluation, not future information available to the simulated reviewer.
4. **Record a local review decision (one minute).** Mark the case as needing investigation or no further local review and add a note. Show that this is a human decision and that GitHub remains unchanged.
5. **Advance historical events (two minutes).** Replay a recorded response or close/reopen sequence and then the seven-day deadline. Show updated current state, attention, and packet freshness beside the unchanged original prediction. Closing a duplicate does not mean the underlying bug was fixed.
6. **Show recovery and the result (two minutes).** In the labelled fixture fault lane, deliver an event twice and interrupt a worker. Resume it and show one accepted result and no duplicate local notification. Finish with the operator’s passed/failed/blocked evidence and measured usage.

The presentation uses stored actual results by default so a meeting does not depend on provider latency or authorize fresh spending. A new model run is a separate, explicitly approved execution mode. Reset only run-owned demo state; retain source manifests and evidence. No live repository cleanup is needed because no live issue changes are permitted.

##### Verification matrix: what can be checked deterministically

| Check | Required direct verification | Expected result |
| --- | --- | --- |
| Source integrity | Rebuild normalized cases from the frozen source manifest; compare hashes and joins. | Identical case inputs; unknown coverage is explicit. Hashes verify replay identity, not completeness of all real-world activity. |
| Seven-day label | Fixture histories cover before/at/after deadline comments, author comments, excluded bots, missing association, and ordered close/reopen events. | Labels follow the frozen rule; uncertain histories stay unknown. Deadline inclusion and simultaneous-event ordering are specified in the contract. |
| Future-data exclusion | Change later comments, final labels, assignments, and outcome fields while holding the creation snapshot fixed. | Creation-time feature hashes and stored original predictions remain unchanged. Later operational state can change. |
| Interpretation | Validate recorded responses against schema and the adjudicated examples; include absent, contradictory, and malformed answers. | Invalid data is rejected; unknowns survive into the UI. Report semantic accuracy against frozen thresholds; deterministic parsing alone does not prove semantic correctness. |
| Fair comparison | Check split membership, outcome availability, identical cases, fixed review capacity, and hand-calculated metric fixtures. | No train/calibration/holdout overlap or unavailable labels; metric calculations agree. Selection uses calibration only. |
| Durable workflow | Replay duplicate events, same request with conflicting input, out-of-order delivery, failure, and interruption around result persistence. | No duplicate accepted result or local notification; conflicts fail clearly; state reconstructs in event order and resumes safely. |
| Paid-call uncertainty | Simulate interruption after provider submission but before acknowledgement. | Mark the result unresolved and stop automatic paid retries; do not claim exactly-once provider execution. |
| Review UI | Browser check and human walkthrough of all six views, including keyboard use, unknowns, loading, failed stages, source links, and local notes. | A reviewer can distinguish evidence, inference, later outcome, and their own decision. Failed or incomplete work is visible. |
| Scope and cost | Verify read-only source access, blocked mutation paths, configured limits, and ledger reconciliation. | No GitHub writes; approved limits hold; missing required cost/usage evidence yields blocked. A post-handler timeout is not a hard execution cap. |
| Repeatability | Replay the same stored replies and events twice from reset; compare substantive artifact fields and state. | Matching results apart from declared volatile fields. New model calls are assessed against frozen quality thresholds, not promised byte-for-byte identical. |

Run the required static, schema, semantic, workflow, visual, operational, and security checks against the candidate used for the demonstration. Reuse and extend the existing report/viewer paths (`runtime/artifacts.py`, `runtime/audience_server.py`, `scripts/package_capabilities.py`) and package/browser/runtime validators; do not create a second demo platform. No new issue-specific runner or validator is claimed to exist yet.

Once implementation and a committed candidate are authorized and ready, use the existing validation entrypoint with the repaired manifest:

```sh
node scripts/validation/run.mjs \
  --manifest tabellio.validation.json \
  --expected-commit "$release_sha" \
  --output artifacts/validation/ReleaseCandidate
```

`release_sha` must identify the exact candidate being demonstrated. The package must include its run manifest, replay instructions, metric table, screen captures, and required validator evidence. Local working-tree checks cannot substitute for exact-commit acceptance.

**Done for the demonstration:** a reviewer can complete the walkthrough, inspect the original evidence and actual model outputs, see a correct update and recovery, and inspect all required results without hidden fixtures or fresh provider calls. This proves a bounded historical review workflow. It does not prove saved time, intervention benefit, broad market demand, or production readiness. Those need the separate human pilot and later prospective evaluation. The existing all-16-capability release contract below remains unchanged.

#### Why this experiment instead of the other candidates

| Candidate | Useful capability | Reason not to use it as the first prospective text-to-outcome demonstration |
| --- | --- | --- |
| Existing synthetic support/equipment fixtures | Deterministic software, interruption, and permission checks. | Outcomes are generated by known formulas; they do not validate naturally occurring predictive relationships or real preparation pain. Retain them for technical acceptance. |
| Olist orders and reviews | Commerce facts, review interpretation, and historical operational analysis. | Olist says surveys are sent after receipt or when the estimated delivery date is due. Using that order's later review as an earlier predictor of its delivery outcome leaks information. Earlier reviews could support a different future-window task, but that needs its own contract. See the [publisher's dataset description](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). |
| CFPB consumer complaints | Complaint-theme extraction and response monitoring. | Complaints are published after the company responds or after 15 days, whichever comes first; narratives also require consent and scrubbing. A public narrative cannot automatically be treated as available at initial submission to predict the same response. See [CFPB publication rules](https://www.consumerfinance.gov/data-research/consumer-complaints/) and [data-use definitions](https://www.consumerfinance.gov/complaint/data-use/). |

GH Archive is selected for feasibility assessment because event snapshots can separate initial text from later outcomes, subject to the feasibility and rights gates above. The user has selected this developer-support workflow for planning. Customer demand, commercial clearance, model accuracy, and business improvement remain unproven.

## Product objective

Give operations teams a current, evidence-linked review of changed conditions and predicted outcomes, with less repeated preparation and clearer follow-up as the intended benefits. Turn approved heterogeneous data into traceable information and stakeholder outputs through background workflows that do not require a chat prompt for every batch. Keep business decisions and operational interventions with people.

Develop against varied synthetic scenarios. Interpret their relevant text with real Jev, retain its actual returned findings and request/model identity, build prediction-ready information using facts and findings available at each cutoff, execute real predictors, and feed their predictions into further analysis, attention tracking and useful stakeholder outputs. Dataset adapters, extraction definitions, analysis policies, and audience requirements may vary; the core execution, provenance, result lifecycle, and artifact contracts remain reusable.

### Workflow and process we automate

BackIntel automates preparation and follow-up for **recurring operational review and exception management**: assembling scattered records, identifying emerging problems, prioritizing items for review, preparing useful reports, and keeping open concerns current. An exception is a case that meets an agreed condition for human attention. The primary users are operations analysts, reporting coordinators, and team supervisors.

The standing assignment is: **watch approved information, reassess predefined questions, and surface changes that deserve attention**. New records, corrections, schedules, deadlines, or stale information can start agreed work without another chat prompt. Models run when the workflow calls them; there is no continuously thinking model choosing its own goals.

People define the entities, input mappings, questions, prediction targets and horizons, attention rules, audiences, and permitted actions. The workflow produces a review package containing what changed, predicted outcomes, supporting evidence, freshness, uncertainty, and unresolved concerns. People investigate, assign work, authorize interventions, and assess actual outcomes. Demonstrated delivery stays within the local inbox/outbox simulator.

### Where the capability sits in the data lifecycle

| Stage | Work automated or assisted | Who controls the decision |
| --- | --- | --- |
| Admit and validate | Accept approved batches; identify duplicates, invalid records, late arrivals, and corrections; preserve sources. | Written validation and admission rules. Live source-system integration is a separate requirement for each workflow. |
| Interpret unstructured information | Ask fixed questions about relevant text and convert returned answers into structured observations. | Jev makes a learned interpretation; people define the questions and acceptable interpretation quality. |
| Prepare prediction inputs | Combine facts and observations into versioned, entity-level inputs using only information available at the declared cutoff. | Written mapping, missing-value, versioning, and time-cutoff rules. |
| Compare and predict | Compare the baseline, CatBoost, and TabICLv2 on shared eligible cases; score new inputs with the selected model. | Models supply estimates; code applies evaluation and selection rules. The demo simulates operator approval for activation. |
| Analyze and prioritize | Compare findings and predictions with the configured policy; create or update attention episodes. | Written business rules. The current risk-combination policy is explicitly synthetic. |
| Prepare the operational review | Produce audience-scoped reports and exports with source links, freshness, uncertainty, and simulation labels. | Written report and access rules; people judge usefulness and decide action. |
| Follow up and reassess | Record acknowledgment and resolution, react to deadlines and staleness, admit observed outcomes, and refresh affected results. | Recorded events and written scheduling/update rules; people remain responsible for real operational interventions. |

For fixed inputs, state, and policies, admission, routing, joins, cutoff checks, and attention rules are deterministic. Interpretation and prediction use learned models. Fixed-model inference may be repeatable, but that does not establish correctness or remove uncertainty; training and live-provider responses require controlled evaluation.

The main LangGraph graph currently wraps a single operation-dispatch node. BackIntel's Python functions and persisted jobs choose the stages. There is no model planner that independently chooses new questions, retrieves additional sources, selects tools, or changes the analysis strategy. Adding that investigative behavior would be an explicit capability decision. It is not required merely to run the agreed workflow in the background.

### Roles and tasks affected

| Role | Routine work the capability could take over | Human responsibility retained |
| --- | --- | --- |
| Operations analyst or reporting coordinator | Assemble records, refresh calculations, maintain review queues, and prepare recurring reports. | Define useful questions, investigate findings, and recommend action. |
| Data classification or review specialist | Read routine text and assign predefined structured findings. | Define categories, adjudicate ambiguity, and check interpretation quality. |
| Support or maintenance triage coordinator | Surface cases meeting attention rules and maintain their review state. | Set priorities, assign owners, handle exceptions, and authorize intervention. |
| Business intelligence analyst | Refresh recurring views and trace displayed results to evidence. | Define metrics, explain causes, and assess business meaning. |
| Data engineer or data scientist | Execute established transformations, model comparisons, and scoring. | Design integrations and targets, validate models, prevent leakage, and maintain the system. |

These are task-level automation opportunities, not demonstrated replacement of whole jobs. The strongest initial fit is preparing and maintaining an operational review. Engineering and data-science work gains reusable execution machinery, while expert design and judgment remain necessary.

The support-review example above illustrates this division of work. Equipment maintenance can use the same process shape with different inputs, questions, targets, and policies; transfer to other workflows must be demonstrated rather than assumed.

### What the PoC proves and what remains unproven

The capability is being demonstrated across **admitted data → structured findings → time-safe prediction inputs → predictions → an operational review**, with evidence history and background execution around that flow. Synthetic fixtures have exercised admission, corrections, feature preparation, reports, and attention transitions. Actual CatBoost and TabICLv2 have run locally; integrated predictor journeys used simulated Jev findings. One actual Jev request passed, while the complete two-scenario real-Jev journey and exact-candidate acceptance remain unfinished. The capability table below owns the detailed evidence status and release conditions.

Broad live integrations, representative interpretation quality, real-world predictive accuracy, continuously operating production service, operational interventions, staff time saved, and improved business outcomes are not established by this PoC. The demonstration uses synthetic data, bounded execution windows, a fictional attention policy, simulated model-activation approval, and simulated code-generation input to an actual restricted sandbox. Open-ended investigation and autonomous operational action are outside the current implementation.

The problem-validation plan above defines the evidence to collect in a real-workflow pilot. Those observations can support a business-value assessment and changes to job duties; passing software checks alone does not. This business framing preserves all 16 capabilities and the real-model finish line below.

## Full capability list — one technology roadmap

The platform machinery and the selected models must execute. Synthetic records, deterministic provider fixtures and captured outbound messages support development without coupling it to one dataset. Final acceptance requires actual returned Jev findings and actual CatBoost/TabICLv2 predictions. A configured adapter name or a stored simulated response does not prove model execution. Synthetic-data performance does not establish real-world accuracy or business value.

| Step | Business objective | Capability and completion condition | Current evidence |
| --- | --- | --- | --- |
| 1. Portable task contracts | Reuse the platform for different decisions. | Configure entities, input mappings, units, questions, measures, targets, prediction horizons, audiences, and policies. Two unrelated scenarios share the same core code. | Implemented and checked for two unrelated synthetic source mappings and task contracts. |
| 2. Source admission and revisions | Keep information current without manual reconciliation. | Admit synthetic CSV/JSON/text batches; identify duplicates, late arrivals, corrections, and schema failures; expose accepted/quarantined dispositions. | Implemented admission, quarantine, duplicate handling and source corrections; direct checks passed. |
| 3. Evidence and lineage | Make every finding explainable and correctable. | Preserve immutable source facts, observations, feature rows, outcomes, predictions, policies, and artifacts as distinct versioned records. Trace outputs to their inputs and retain correction history. | Immutable PostgreSQL evidence and correction history implemented; direct checks passed. |
| 4. Semantic observations | Make unstructured information usable. | Run real Jev against relevant synthetic text through a configurable typed boundary with distributions, unknowns, abstention, retries, caching, provenance and separate corrections. Preserve actual responses and request/model identity. | Typed real-provider boundary checked; one approved actual Jev request now retains its returned finding, request ID, resolved model and measured charge. Complete history/follow-up execution remains unapproved. |
| 5. Point-in-time features and outcomes | Support credible prediction without future information leaking in. | Generate versioned feature snapshots and separately available outcomes from synthetic histories. Enforce cutoff, target eligibility, null, entity-grain, and chronological split rules. | Cutoff-safe feature snapshots, separate outcomes and chronological eligibility checked. |
| 6. Predictor preparation | Support interchangeable predictive approaches. | Execute a native baseline, real CatBoost training/preparation and real TabICLv2 context preparation through common prepare/score interfaces. Retain model/package/weight identities and preparation inputs. | Actual structured-only CatBoost/TabICLv2 classification and regression checked on the host and in the CPU container under local approval; real semantic preparation pending Jev. |
| 7. Predictor evaluation | Determine whether a candidate improves a decision on the supplied data. | Compare real CatBoost and real TabICLv2 using ordinary facts alone and facts plus real Jev findings, alongside the baseline. Use identical eligible cases/cutoffs and actual synthetic historical outcomes; calculate classification/regression metrics, calibration, latency and resources. | All four actual predictor routes ran with fixture Jev features in both domains; metrics remain synthetic. Required facts-plus-real-Jev comparison is pending paid approval. |
| 8. Model lifecycle | Control which predictor influences results. | Persist prepared → evaluated → approved → active → retired states, one active version per task, explicit fallback/shadow behavior, compatibility checks, and rollback. Failed/blocked evidence prevents activation. Approval transitions use a simulated operator in the demo. | Lifecycle controls and actual predictor updates checked with fixture Jev; actual-Jev integrated lifecycle remains unverified. |
| 9. Scoring and controlled updates | Keep predictions current without unnecessary retraining. | Score new eligible feature rows, version predictions, invalidate/recompute affected results after corrections, and distinguish feature refresh, scoring, model preparation, artifact refresh, and notification. Measure synthetic drift and test a bounded update path. | Real predictor follow-ups, correction invalidation, scoring and bounded retraining checked with fixture Jev. Retraining excludes superseded sources; actual Jev remains pending. |
| 10. Durable background jobs | Finish work without constant supervision. | Submit through the generic Aegra API; preserve state after client disconnect; support bounded retry, cancellation, restart, concurrent replay, and conflict rejection. Keep one scheduling owner. | Both fixture journeys completed 45 jobs with actual local predictors. Scoped native-clock preparation survived restart with unrelated work excluded; full paid journey remains unverified. |
| 11. Persistent triggers | Start work when information or deadlines change. | Store event, schedule, deadline, staleness, and on-demand triggers. Recover due work after restart without a sleep loop occupying a worker or repeated manual submissions. | Native Aegra cron and persisted due triggers checked, including retry and resumed work. |
| 12. Attention and local delivery | Surface important changes without duplicate interruptions. | Persist episodes with policy-based entry, updates, acknowledgment, investigation, unknown/stale, resolution and clear rules. Exercise cooldown/hysteresis and response deadlines. Refreshing an artifact need not notify a person. Deliver to a local inbox/outbox simulator only. | Persistent forecast analysis drives attention and local delivery in both real-predictor fixture journeys; actual Jev remains pending. |
| 13. Stakeholder artifacts and access | Give each user a useful view of the same evidence. | Publish versioned briefings, analytical views and exports from accepted result bundles; show actuals/predictions/hypotheses, freshness, coverage, uncertainty and source links. Enforce configured local audience scope and correction/review actions. | Scoped reports, corrections and exports checked. Explicit real/predictor-fixture packaging implemented; actual-predictor fixture reports passed desktop/mobile browser checks. |
| 14. Restricted artifact execution | Safely create new presentations and analyses. | Feed a simulated code-generation response into a real restricted local sandbox: allowlisted input snapshot, protected source/dependencies, bounded resources/time, no host secrets or external network. Build/run/inspect a candidate; retain source, logs, preview and review outcome. Prohibited operations must actually be denied. | Actual sandbox execution, constrained layouts and local reviews are included in the development command and retained report package. |
| 15. Operational controls | Make background operation understandable and bounded. | Track run/stage status, lineage, errors, retries, provider calls, local duration/resources, limits and stop reasons. Exercise backpressure and budget enforcement using synthetic provider usage. Distinguish simulated charges, measured provider charges, and unpriced local compute. | Request admission, limits, leases, backpressure and receipts implemented; full real-provider cost/rate/resource acceptance remains unfinished. |
| 16. Integrated demonstration and cleanup | Deliver one repeatable capability platform. | Run both unrelated scenarios through real Jev interpretation, real prediction methods, further analysis, attention and useful reports, alongside the other workflow and sandbox capabilities. Inject failures/restarts/replays, verify outputs, document one-command operation, and safely retire superseded goal-owned scaffolding. | Real driver and explicit packaging modes implemented. Unpaid preparation, denial gates and native-clock restart passed. Combined fixture database/model recovery reproduced 50 predictions and replayed 90 jobs. The actual single Jev probe passed; full paid execution and approved exact-commit acceptance remain pending. |


## Long-running goal contract

**Outcome:** a reusable local background-intelligence platform that completes synthetic source → immutable evidence → real Jev findings → time-safe features → real CatBoost/TabICLv2 preparation, evaluation and selection → actual predictions → further analysis → attention → useful stakeholder outputs, with durable scheduling and restricted artifact execution. Complete all 16 steps together. Deterministic model fixtures or an isolated subsystem cannot establish completion.

**Acceptance source:** product-owner direction on 2026-09-26 to pursue all technology capabilities in one long-running goal, corrected the same day to require real Jev and real predictor execution while retaining synthetic source records and historical outcomes.

**Business scope:** source onboarding, interpretation, prediction, background orchestration, stakeholder artifacts, local attention and oversight, operational controls, and repeatable packaging. Olist remains a preserved optional integration example. Amazon Reviews remains a later real-data scale option. Neither defines the platform's domain model.

**Real versus simulated:** implement real parsing, storage, lineage, feature construction, metrics, candidate registry, workflow state, timers, local inbox, artifacts and sandbox enforcement. Synthetic source records and known synthetic historical outcomes are allowed. Real Jev must interpret the relevant text and preserve actual returned outputs with request/model identity. Real CatBoost and real TabICLv2 must execute against facts alone and facts plus those Jev findings. Every simulated route retains `implementation_mode=simulated` and cannot satisfy final model acceptance. Simulated code-generation responses may still exercise the actual sandbox. Google TabFM is a distinct research/model choice; do not call TabICLv2 TabFM or claim Google's model executed.

**Model work remains explicit:** Jev-style observations, point-in-time features, target/outcome contracts, train/context preparation, comparable evaluation, model version approval/activation, scoring, monitoring, corrections, update and rollback all remain required. The current linear projection is insufficient. Classification and regression contracts should be covered by the synthetic scenarios; accuracy thresholds are not business claims.

**Owned surface:** the existing canonical BackIntel repository, its current runtime stack and application schema, scenario/adaptor configuration, local artifact/sandbox implementation, tests and validation contracts. Reuse existing components before adding abstractions or dependencies. Keep one maintained roadmap and repository map; update their status rather than adding parallel plans or ticket worktrees.

**Invariants:** unknown is distinct from false; source, model interpretation and observed outcome remain distinguishable; future evidence cannot enter earlier snapshots; an accepted result cannot be silently overwritten; acknowledgment does not clear a condition; stale does not mean resolved; source changes do not automatically retrain or notify; retries cannot duplicate accepted results or deliveries; every material output identifies its source/feature/model/policy versions. Source text/code is untrusted. Model, data, execution and publication authority stay separate.

**Authority:** local implementation and synthetic-data development authorized. Prefer isolated local test services/databases over modifying the preserved Olist demonstration stack. Paid inference and model-use rights retain separate approval boundaries; prepare concrete bounded runs and obtain approval at the relevant execution boundary. No real external messages, public publication, cloud deployment, production writes, new licensed datasets or unrelated deletion. Preserve credentials, live data and recovery copies. Local commits and pushes still require explicit confirmation; none is approved. No autonomous subagent fan-out is authorized.

**Required direct checks:** contract/schema failures; point-in-time feature/label isolation; actual evaluation calculations; candidate activation/fallback/rollback; generic server submit/disconnect/restart; persistent due-trigger recovery; replay and concurrent conflict handling; episode and delivery deduplication; output/source consistency; local audience boundaries; rendered desktop/mobile and keyboard journeys; actual sandbox rejection of prohibited reads/network/resource use; budget/rate/resource-stop behavior; one integrated run across both scenarios. Record each required result as passed, failed or blocked on the approved exact candidate, with artifact hashes. Tests serve these outcomes; do not add repeated reviews or proof infrastructure for confidence alone.

**Cost treatment:** record real execution duration/resource observations and provider usage. Keep simulated billing clearly separate. Zero external model calls means zero provider charges; unpriced local compute remains unknown. Human baseline, representative accuracy and total cost savings remain outside this simulated-technology goal. They must not become prerequisites for coding the simulator, and no savings claim is permitted without later evidence.

**Done condition:** one documented local command starts a bounded demonstration across both unrelated scenarios. Real Jev interprets synthetic text; actual CatBoost and TabICLv2 run comparable facts-only and facts-plus-Jev evaluations; their predictions drive further analysis, attention and useful stakeholder outputs. Subsequent arrivals, corrections and due events run without repeated manual submissions. All other capability requirements, recovery, portability, audience access, restricted execution and rendered-output checks pass on the approved committed candidate. A blocked provider/model step remains unfinished. Evidence identifies actual requests, models, packages, weights and outputs. No real-world accuracy, time-saving or representative business-value claim follows from synthetic data. Obsolete goal-owned scaffolding is safely retired while user work, live services and recovery evidence remain intact.

## Dependency-ordered implementation packages

1. **Portable contracts and evidence:** steps 1–4. Retain reusable source, observation and revision contracts; connect real Jev to the typed boundary and preserve actual requests/responses. Simulated responses remain fast test fixtures.
2. **Prediction lifecycle:** steps 5–9. Retain time-safe feature/outcome histories, evaluation calculations and registry controls; execute actual CatBoost and TabICLv2 adapters with facts-only and facts-plus-real-Jev comparisons. Keep CatBoost training and TabICLv2 context preparation distinct. A model/provider approval boundary blocks only its dependent execution.
3. **Unattended operation:** steps 10–12 and operational controls from step 15. Connect the generic API journey, persistent triggers, durable local episodes and delivery deduplication around the existing runtime.
4. **Stakeholder outputs and execution:** steps 13–14. Add configured local views/access and run simulated generated candidates inside an actual bounded sandbox.
5. **Integrated completion:** finish steps 15–16 with real model execution flowing into further analysis, attention and useful reports. Run affected direct checks, save exact-candidate evidence, document startup, and clean up superseded goal-owned material. Do not substitute deterministic responses for final model execution.

Build as bounded slices inside this one goal. At each checkpoint record implemented outcome, changed surfaces, direct-check result and remaining dependency. Resume from that checkpoint rather than restarting investigation. Do not stop for non-material uncertainty, human labeling worksheets, or accounting inputs unrelated to the current simulated capability. Stop dependent work only for failed material checks, missing external-action/commit authority, or an actual isolation/data-loss risk; continue independent authorized work where available.

## Current implementation checkpoint

The initial uncommitted capability slice runs two synthetic source shapes through one shared engine. It covers parsers, rule-based simulated extraction, basic summaries, a virtual failure/retry/duplicate timeline, missing/stale handling, and HTML/JSON evidence artifacts. The graph wrapper uses the existing PostgreSQL ledger; direct graph/ledger and preserved regression tests passed. Desktop/mobile and keyboard checks passed. Generic source revisions, the predictive lifecycle, persistent triggers, durable local attention, scoped user access, and generated-code sandboxing remain incomplete. Existing installed Olist services have not been updated.

The former Olist recovery goal remains recorded separately; completion of cleanup and the recorded-data demo is not completion of this new platform goal. Goal registration status must come from the goal tool, not a prose statement in this file.

**2026-09-26, package 1 implementation:** Added portable typed task contracts to both existing scenarios; immutable PostgreSQL evidence with content hashes and parent links; synthetic CSV/JSON/text-envelope admission with accepted, duplicate, correction, late-revision and quarantine outcomes; typed simulated Jev-style responses with distributions, unknown/abstention, bounded retries and persistent caching; authorized correction chains and historical reads. Original source/observation records remain unchanged. Four direct PostgreSQL checks passed in the isolated `backintel-capability-test` database on localhost:55436. These are working-tree checks, not exact-commit acceptance. The installed Olist stack remains unchanged. Package 2 is next: time-safe features/outcomes, distinct simulated predictor preparation, comparison, activation, scoring and updates. API integration, persistent triggers, audience artifacts and sandbox execution remain unfinished.

**2026-09-26, package 2 implementation:** Added cutoff-safe feature snapshots and separately available versioned outcomes; chronological train/holdout separation; native empirical baseline plus explicitly simulated CatBoost training-style and TabICLv2 context-style adapters; real classification/regression and calibration calculations on identical holdout cases; persisted preparation/evaluation/approval/activation/retirement/rollback; compatible fallback and shadow scoring; prediction invalidation after corrections, drift measurements and a bounded update plan. Fourteen direct checks passed, including preserved offline simulation behavior. Evidence: `artifacts/validation/CapabilityPackages/checks.json` and `checks.log` (source hashes, no provider calls; local compute unpriced). Exact-commit acceptance remains blocked. Package 3 is next: real generic API jobs, restart recovery, persistent triggers and durable local attention/delivery. Model-update execution must be exercised during integration; a saved update plan alone is insufficient.

**2026-09-27, current checkpoint:** Packages 1–3 now have a working development journey through the actual generic Aegra API on isolated localhost:2027. Both scenario streams complete bootstrap plus 13 saved follow-ups, including source revisions, outcomes, retry, deadline/acknowledgment/investigation/staleness/resolution, preparation and activation of an updated simulated predictor, and result refresh. Aegra's native persistent cron is the sole scheduler; jobs never wait asleep for due events. Job leases, cancellation, bounded repair, backpressure, per-scenario ordering, immutable attempt history and local delivery deduplication are implemented. Nineteen direct checks passed; the actual background journey passed after repairing two integration failures. An overdue-job ordering failure is preserved in `artifacts/validation/CapabilityDemo/ordering-failure-trial.json`; a negative-zero JSONB hash failure is preserved in `negative-zero-failure-trial.json`. The corrected stream resumed its failed job without discarding prior accepted results. Current receipts: `submission.json`, `background-check.json`; direct-check evidence: `artifacts/validation/CapabilityPackages/checks.json`. These remain working-tree results, not approved exact-commit acceptance. Original Olist service at :2026, data and recovery set remain unchanged.

**2026-09-27, approved local models and sandbox checkpoint:** The user approved CatBoost and TabICLv2 on synthetic data, with at most 64 training rows and two CPU threads. The two pinned TabICLv2 checkpoints (224,692,632 bytes total) downloaded and passed SHA-256 checks. Actual CatBoost 1.2.10 and TabICL 2.2.0 classifier/regressor paths fit, saved, loaded, and predicted on both scenarios: 18 training rows and six held-out rows per scenario. These are structured-only results, not the required facts-plus-real-Jev comparison or evidence of real-world quality. Receipt: `artifacts/validation/RealPredictors/3a7906ed0bd440d2b2817c280d245bcc.json`. Weights, model packages and local approval records stay ignored under `artifacts/Models/`; the host `.venv` is also ignored. The running isolated API image has not yet received these model changes.

The generic Jev boundary now has committed request admission, scoped and expiring approval, response caching, retained raw responses, request/model identity and measured-charge requirements. Uncertain requests are never automatically retried. Its fixture checks make no paid calls. A separate one-request paid probe is prepared for `jev-1.13`, using only “Service working” and one question. The existing Keychain credential has not been retrieved. Public pricing is unknown; there is no enforceable dollar cap. Paid approval was requested separately and remains pending. One probe would not authorize a larger batch. Local model approval does not authorize Jev.

Actual Docker sandbox execution now accepts an allowlisted snapshot and generated Python, with no network, no writable host output, protected source/dependencies, an unprivileged user, and CPU/memory/process/file/time/output limits. The direct check accepted the intended calculation and denied nine prohibited operations, including host reads, protected writes, network, and resource misuse. Container cleanup passed. Source, bounded logs, result, stop reason and image identity are retained in `artifacts/validation/Sandbox/aa673f3e7ced4cb8bbef7956c3bb480c.json`. This proves the host runner; integration with stakeholder artifact review/publication remains unfinished. Generated code in these checks is a fixture. Thirty-four capability/provider-boundary/regression checks passed in `artifacts/validation/CapabilityPackages/checks.json`; all evidence is working-tree evidence. Exact-commit acceptance is still blocked until the complete candidate and commit authority exist.

**2026-09-27, audience reports and generated-view checkpoint:** `refresh` now creates immutable audience projections from each accepted result bundle. A loopback-only HTTP service binds short-lived private tokens to one task version and audience; HTML, CSV, JSON, historical reports, source references and generated candidates enforce that scope. Operators can record review decisions and correct typed observations. Corrections preserve the original source, invalidate affected predictions and create a refreshed report. Read-only audiences cannot invoke those actions. Cross-origin changes, expired tokens, cross-entity evidence reads and stale forms are denied. Accepted facts, latest recorded outcomes, future predictions, missing observations, staleness and uncertainty are shown separately. Actual model execution status is displayed rather than inferred from an adapter name.

Generated Python now runs in the actual host sandbox against an approved audience snapshot and returns a constrained layout. Values are rendered from accepted evidence; invented source references and failed runs cannot be accepted. Source code, bounded logs, snapshot identity, pinned container image, candidate preview and local review decisions remain durable. Development code generation and operator approvals are explicitly simulated. The final scope check passed 59 checks in `artifacts/validation/Audiences/e64d6a3c2be4.json`. A real Chromium journey passed 84 checks with 24 desktop/mobile captures in `artifacts/validation/AudienceUI/8b06b63f-612c-4f36-87f0-ea92c8652785/checks.json`; rendered critique and the resolved mobile-table finding are in `review.json` beside it. The initial browser failure exposed a same-origin form issue caused by the referrer policy; the policy was corrected while foreign origins remain denied. Thirty-four existing regression checks also passed. Temporary audience HTTP processes were stopped after verification; test records and receipts remain available. No paid provider calls, commits, push, public publication or Olist changes occurred.

These are working-tree subsystem checks on model fixtures. The running isolated development API image still predates the audience changes. Actual Jev interpretation, the complete real-model comparison and predictive attention flow, refreshed runtime packaging, full operational/recovery checks and exact-commit acceptance remain unfinished. The existing paid one-request probe question is still pending; do not infer approval from this checkpoint.

**2026-09-27, integrated development and recovery checkpoint:** One development command now runs both unrelated scenarios through the isolated Aegra service, automatic follow-ups, forecast analysis, attention, audience artifacts and actual host sandbox execution. Each invocation preserves its own logs and receipts. `--verify-recovery` restarts only the isolated runtime after bootstrap while follow-ups remain pending, then waits for durable completion. Replay uses the real generic API and must leave accepted evidence, attempts and delivery history unchanged. `--serve` can start the scoped local viewer after completion. Generated-code responses and local operator reviews are explicitly simulated; they do not imply external publication.

The `integrated-v2` stream completed 14 jobs per scenario after restarting with 26 pending triggers. Its 738 accepted records survived that restart and API replay was unchanged. The development package contains 26 scoped report/export/source/review files. Receipt: `artifacts/validation/CapabilityDemo/integrated-v2/Attempta413833c830f/Integration.json`. The image was then rebuilt directly from the repository's canonical `Dockerfile.runtime`, without inheriting the preserved Olist image; the obsolete goal-owned `Dockerfile.capabilities` was removed. Resuming `integrated-v2` passed replay and produced another retained package in `Attemptde75e0dc8381`. The original Olist container ID, image and start timestamp were unchanged; its receipt is `PreservedOlist.json` in that attempt.

Forecasts now feed a persisted analysis record and the attention decision. This is an explicit fictional policy for synthetic scenarios: normalize classification forecasts by 1 and synthetic equipment outcomes by 5, then take the larger known interpretation/forecast risk. Missing interpretation remains unknown, even with a forecast. Older task versions without a configured prediction scale retain interpretation-only attention. Reports show the two contributing risks. A direct check proves that a high forecast can open an episode despite a false text finding, preserves forecast lineage, and keeps missing interpretation unknown. Model activation now refreshes attention; a presentation-only refresh still does not notify. Thirty-five regression checks passed. The packaged forecast explanation passed desktop/mobile rendering checks in `Attemptde75e0dc8381/Package/VisualCheck/Checks.json`.

A database backup was restored into a newly created isolated test database. The restored task evidence, audience artifacts and job state matched exactly; all 28 completed jobs replayed without changes. The temporary clone was removed. Receipt: `artifacts/validation/CapabilityRestore/Attempt2465d4a5f71a/Restore.json` (746 records after retained generated candidates/reviews, 624,970-byte backup). This verifies the two fixture task streams, not actual model-file/checkpoint recovery or a second live Aegra deployment. No paid calls, commits, push, public deployment, or Olist data changes occurred.

The final offline-export correction is retained in `artifacts/validation/CapabilityDemo/integrated-v2/Attempt907d51817dc2`. That replay passed and produced 36 packaged files, including audience-specific source JSON. All eight HTML exports have local links and no live forms. Chromium opened an exported source record and returned from the generated view to its report without a server. Evidence: `Package/OfflineExports.json` and `Package/OfflineBrowser.json`. Interactive corrections and reviews remain available through the authenticated local viewer; exported copies are read-only.

**Previous checkpoint dependency (updated below):** Run the single Jev probe only after explicit paid approval; inspect actual response identity and cost before proposing any larger batch. Integrate real extraction as a separately committed stage before preparation and scoring, because paid admission cannot depend on uncommitted source rows. Integrate real extraction through committed admission stages, then real predictor preparation/scoring into the now-packaged background workflow. Finish real-model file recovery, remaining operational acceptance and the approved exact-commit checks. The development restore checker currently depends on the separately provisioned isolated validation PostgreSQL service. Preserve the original Olist service and data. Do not complete the goal at this checkpoint.

**2026-09-27, real-stage and model-container checkpoint:** The optional model-enabled `Dockerfile.runtime` installs the pinned CPU model dependencies. The isolated Compose service mounts the existing approved weights, runs one worker with two CPU threads and disables automatic checkpoint downloads. No provider credential is configured. Actual CatBoost and TabICLv2 classification and regression passed inside that image with 18 training and six holdout records per scenario. Receipt: `artifacts/validation/RealPredictorsLinux/3d97e37762a6415fa5df9408a9270be1.json`. Synthetic metrics do not establish real-world prediction quality.

`real_pipeline.py` now separates committed source admission, authorized interpretation and real comparison. The preparation stage makes no paid request. The interpretation stage requires a source in its immutable saved plan and a matching named authorization. The comparison stage rejects missing, simulated, late or untraceable observations and unknown actual billing before using real predictors and refreshing analysis, attention and reports. The paid stages have boundary checks but have not executed real Jev. Follow-up arrivals/corrections and scheduled updates still require integration into this real path.

The new `scripts.real_capabilities` command submits those stages through the actual generic API. Both scenarios admitted 24 sources and 24 outcomes; replay left their domain records and job attempts unchanged. Receipt: `artifacts/validation/RealPipeline/Attempt5753ef17653e/Preparation.json`. Job attempts now record newly admitted provider requests and measured charges; cache reuse adds zero charge, and uncertain execution or missing prices stay unknown. A missing runtime credential cannot consume an approved request slot. Provider fixtures verify these controls and are not actual Jev evidence.

Actual model-file recovery retained an 11-file backup, restored it into a temporary directory, and reproduced all 24 holdout predictions across both model families and scenarios. The temporary directory was removed. Receipt: `artifacts/validation/RealModelRecovery/Attempt46687ef81fab/Restore.json`. This check used the existing isolated evidence database. It proves model-package/checkpoint recovery, while combined restoration of the final real-Jev task database and model files remains pending. The original Olist container, image and start time remain unchanged. All new evidence is from an uncommitted working tree.

Fifty regression checks passed inside the final model-enabled image, using separate isolated databases for the generic and older Olist fixtures. After replacing only the development runtime with that image, both prepared histories replayed unchanged. No paid request was recorded. The final runtime identity, preserved Olist identity, test groups and setup corrections are recorded in `artifacts/validation/RealPipeline/Attempt5753ef17653e/Checkpoint.json`.

**Prior checkpoint dependency (updated below):** The existing single paid Jev probe question remains pending. Its original exact scope cannot authorize these new history tasks or a full batch. After that approval, run only the matching probe and inspect its actual model identity and charge before seeking broader authority. Complete real follow-up integration, the real facts-only/facts-plus-Jev comparison and operational acceptance; obtain commit authority only for a concrete complete candidate. The goal remains active.

**2026-09-27, durable real-path follow-up checkpoint:** History and future source admission now complete before paid extraction. Future revisions carry their own synthetic availability times and remain outside earlier feature cutoffs. A single `real_start` request persists the history interpretation sequence, comparison and follow-up start; the latter persists extraction, correction application, outcome arrival, attention actions, bounded retraining and report refresh. Each provider request retains its separate scope and budget checks. Queue admission now defers due triggers when a task already has 20 pending jobs, preserving them for the next dispatch instead of failing the dispatch transaction.

Both unrelated scenarios completed 45 durable jobs using actual local CatBoost/TabICLv2 and explicitly deterministic Jev fixtures. All four predictor/feature routes executed; corrections invalidated prior predictions and excluded superseded source features from the update's 24 training rows. Accepted task contracts retained their real-provider settings throughout scheduled actions. Replaying every completed job left domain evidence unchanged and added no provider-fixture calls. Receipt: `artifacts/validation/RealFollowups/Attempt333bb285ed2d/Followups.json`. Due timestamps and retry delays were advanced in the isolated test database. This is not actual Jev or native-clock proof of the real journey. Injected provider responses now carry a fixture marker, and result bundles identify fixture semantics rather than presenting them as real Jev.

The actual generic API prepared both future-source plans without any paid request or paid schedule. Each added three source versions while keeping the original 24 records visible at the history cutoff; replay made no changes. Receipt: `artifacts/validation/RealFollowups/Attemptc0aa7e84b6f8/Preparation.json`. The original Olist container, image and start time remain unchanged. Forty-seven regression checks passed inside the model-enabled image. Failed-request accounting now tolerates missing metadata, and failures before the handler starts cannot count earlier jobs' charges as new spending.

**2026-09-27, real driver, packaging and combined recovery checkpoint:** The one-command driver now prepares both source scopes, checks both approved authorizations before credential access, owns an expiring task-bound tmpfs credential, dispatches only its two tasks through native cron, preserves pending work across a safe restart, replays completed work and packages explicitly real results. Preparation and deliberately unauthorized execution were checked without provider access. A dummy non-provider credential verified native-clock source preparation, restart, task isolation and cleanup on the current isolated image. Full paid execution remains unverified.

Packaging rejects mode mismatches and unknown real-provider cost. Actual local predictors with fixture Jev produced scoped ordinary and sandbox-generated offline reports; eight browser checks and representative desktop/mobile visual inspection passed. Fictional fixture charges remain separate from actual spending. Fifty-one regression tests passed in the model image before the later recovery-checker extension.

Combined recovery restored a separate database and approved model files, reproduced all 50 recorded predictions across 10 model packages, and replayed 90 completed jobs without changing evidence, triggers or provider requests. Temporary database and model restores were removed. The host attempt correctly rejected mismatched predictor-library versions; the successful check used the pinned Linux model image. These streams contain fixture Jev and do not establish actual-Jev or live scheduler/broker restoration. Receipt: `artifacts/validation/RealModelRecovery/Attempt6bd517aa6298/Restore.json`.

The README documents preparation, approved execution, authorization-file shape, `--no-start`, credential lifetime and combined recovery. Current checkpoint: `artifacts/validation/RealDemo/real-driver-v1/Attempt93d646ff65d1/Checkpoint.json`. The isolated service is healthy on its rebuilt image; the original Olist container, image and start timestamp remain unchanged. No paid Jev calls, commits, push or publication occurred.

**Current next dependency:** The single paid Jev probe has passed. The remaining two-scenario run covers 54 exact synthetic source versions and requires separate approval. Its scope is retained in `artifacts/validation/RealModelPreparation/FullRunProposal.json`; pricing and a batch cost ceiling remain unresolved. The public router endpoint returned no concrete rates, and one observed charge does not establish a future price ceiling. Current controls block unpriced multi-request execution. Once pricing and scoped execution authority are resolved, run the full comparisons, background workflow, operational/recovery checks and approved exact committed-candidate validation. No full-batch execution, commit or publication is authorized.

**2026-09-28, paid-probe proposal refreshed:** Renewed the same unused, unapproved one-request authorization after its previous expiry. The exact synthetic input remains `Service working`; the single boolean question asks whether it reports a service failure. Requested model remains `jev-1.13`, with no automatic retry and at most 5,000 input characters (15 actual characters). Pricing remains unverified and no dollar cap is enforceable. Refreshed authorization expires **2026-09-29 at 12:48 PM Eastern**. Read-back confirmed zero requests and `approved=false`; no provider credential was retrieved. Existing local-model approval remains intact. Reviewable proposal and receipt: `artifacts/validation/RealModelPreparation/proposal.json` and `Refresh.json`. This refresh authorizes no paid execution or full batch.

**2026-09-28, approved actual Jev probe:** The user approved the refreshed one-request scope. Existing Keychain authentication passed using the application's HTTP client; the earlier standard-library network check failed without making an inference request. Exactly one paid request sent `Service working` and asked whether it reported a service failure. Jev returned false with a true-answer score of `0.03`, request `gen-dec-1790626111-8cZAkuk9tSKCvScgFee0`, actual model `typesafe/jev-1.13-20260917`, and measured charge **$0.000011592**. Local compute remains unpriced.

The request response and billing were preserved before the local model-name check rejected the provider's dated alias resolution. The check now permits this exact observed revision; other dated revisions, different model versions, missing identity and unknown cost remain rejected. Eleven focused regression checks passed. Acceptance then reused the saved response with provider construction explicitly disabled; the request ledger remained unchanged and no second paid call occurred. `ProbeExecution.json` preserves the initial local failure; `ProbeAcceptance.json` and `probe-result.json` retain the successful acceptance and actual finding under `artifacts/validation/RealModelPreparation`.

The original Olist container, image and start timestamp remain unchanged. The isolated runtime has not been rebuilt for this host-side compatibility fix; the real-run command rebuilds it when a later run is authorized. The single-call approval is consumed and does not approve the separate 54-source batch. This remains working-tree evidence, not final committed-candidate acceptance.

## Run the simulation

No Olist dataset, database, model key, package installation, or running server is required for the deterministic simulation:

```sh
python3 -m scripts.simulate
```

Outputs default to `~/Library/Application Support/BackIntel/Evidence/Simulation`. Use `--scenario support` or `--scenario equipment` for one scenario, or `--output /absolute/path` for another artifact directory. Each scenario emits a content-addressed HTML briefing and JSON result with all source records and state transitions.

The virtual clock advances through arrival, duplicate arrival, injected transient failure, retry, acknowledgment, staleness, duplicate replay, missing observations, and recovery. This exercises behavior deterministically; it does not install a scheduler.

For an approved local runtime containing the new `capability_simulation` graph:

```sh
python3 -m scripts.simulate --scenario support \
  --base-url http://127.0.0.1:2026 \
  --receipt /absolute/path/simulation-receipt.json
python3 -m scripts.poc inspect --receipt /absolute/path/simulation-receipt.json --wait
```

The existing installed runtime still contains the previous Olist candidate until explicitly updated. Offline simulation works independently of that update. Both paths use the same simulation functions; the runtime path adds actual LangGraph execution and PostgreSQL admission/result protection.

## Immediate next package

Resume at the current dependency above. Actual local predictors, real-path follow-ups, report packaging and combined fixture recovery are implemented. The remaining provider-dependent work requires actual Jev under separate paid approval, followed by operational and exact-commit acceptance. All 16 capabilities remain in scope.

---

# Historical Olist release plan — retained reference, superseded sequence

The following preserves the earlier domain-specific contract and rationale. Its sprint ordering, immediate Sprint 1 heading, must-have release gates, and approval statements describe that historical Olist release. They do not override the active simulation-first capability roadmap above. Existing source-correctness and data-use restrictions still apply when running the Olist example.

# v0.1.0 Development Roadmap — Background Intelligence Refinery

**Status:** Release plan; business contract confirmed by the product owner on 2026-09-23; technical execution decisions remain open  
**Release type:** Local-first technical product demonstrator  
**Planning basis:** One small cross-functional team; sequence is dependency-based, not a calendar commitment  
**Implementation authority:** The product owner authorized local Sprint 1 execution with approved Kaggle Olist v2 under the non-commercial local-prototype boundary. Paid inference, additional dataset acquisition, persistent infrastructure provisioning, external notifications, cloud deployment, push/PR, and merge remain separately gated.

## 1. Release goal

> Help a Marketplace Seller Performance Analyst prepare a trustworthy recurring seller-performance review—with delivery metrics, customer-feedback themes, and evidence-backed findings—faster and with less repetitive data preparation, so a Seller Operations Manager can decide what merits investigation.

v0.1.0 demonstrates this process locally using Olist's historical Brazilian multi-seller marketplace data. Jev, predictors, background execution, and generated artifacts are implementation mechanisms serving that business goal, not the goal themselves. Orders are evidence and drill-downs; the business-level review concerns seller/category patterns. The demo does not claim to reproduce Olist's internal organization.

A successful v0.1.0 proves this chain:

```text
Kaggle Olist v2 source manifest
  -> reconciled orders, items, sellers, products, and reviews
  -> seller/category metrics with explicit coverage and attribution rules
  -> versioned review-text observations where available
  -> dated evidence-backed findings and a manager briefing
  -> human-vs-system effort and quality comparison
  -> optional, separately evaluated delivery prediction
  -> local presentation and review; no external operational action
```

This is a historical simulation, not a live commerce system. It has no true source-arrival stream, carrier-exception workflow, or intervention history.

## 2. Business process and human baseline

### Human process being improved

The simulated team is Marketplace Seller Performance. The primary user is a Marketplace Seller Performance Analyst; the recipient is a Seller Operations Manager. For a reporting period, the analyst:

1. Obtains order, item, seller, product, delivery, and review exports.
2. Checks completeness, identifiers, join grain, and date coverage.
3. Calculates delivery and customer-experience measures with explicit numerators, denominators, period, and eligible population.
4. Reviews feedback themes and keeps missing or ambiguous text distinct from negative feedback.
5. Compares seller/category patterns across comparable periods, noting sample sizes and attribution limits.
6. Selects evidence-backed findings for a concise management review, linking each to source records.
7. Answers follow-up questions or corrects the report when a join, classification, or source record is disputed.

The recurring manual burden is data reconciliation, repeated calculation, review-text reading/categorization, evidence collection, and briefing preparation. This Kaggle demo models that work; it does not claim that any named real company currently performs this exact process.

### Process established by v0.1.0

For a selected historical reporting cutoff, the system should:

```text
load approved Olist snapshot
  -> validate source rows and join grains
  -> calculate seller/category delivery and feedback measures
  -> interpret available review text with traceable, bounded questions
  -> assemble findings with denominators, coverage, and source evidence
  -> render a Seller Performance review for the manager
  -> preserve reviewer corrections and the exact data/definition versions
```

A generated finding is a seller/category observation to review—not a customer-support ticket or a claim that a seller caused an outcome. People define metrics, verify uncertain findings, investigate causes, and decide any business action. No seller/customer contact or external escalation occurs in v0.1.0.

### Business hypothesis

Given the same frozen source snapshot and the same review-package specification, BackIntel can produce an independently accepted Seller Performance review with less repetitive analyst effort than the manual workflow, without reducing metric correctness, useful coverage, or traceability. We will measure elapsed time, hands-on analyst/reviewer time, reconciliation defects, coverage, correction/rework, finding validity, traceability, freshness, and total cost. Numeric improvement targets will be set after the manual baseline and before final evaluation.

A separate experiment may compare human/rule/model ranking at an equal investigation capacity. That secondary top-K evaluation concerns **seller/category findings**, not a fixed number of orders, and is not required to prove the primary reporting workflow. The demo is not successful merely because it uses AI.

### Baseline comparison

BINT-1 defines the assignment and acceptance rubric. The revised BINT-5 first produces a reproducible monthly seller-performance report from reconciled Olist facts, without requiring a timed human exercise. A later release-evaluation task measures the human baseline against the same frozen files, historical cutoff, and required report outline. A human analyst and the automated workflow must receive the same information for that later comparison. The report covers all eligible data in the selected slice; **there is no arbitrary 20-order queue cap**. If we later evaluate investigative prioritization, its seller/category finding capacity is a separate value derived from observed reviewer workload and frozen before holdout scoring.

| Measure | Human baseline | Automated comparison |
|---|---|---|
| Elapsed cycle time | Input release to independently accepted review | Same boundaries; include queue/wait time |
| Active effort | Analyst and independent-review minutes, separated | Human checking/correction plus runtime/provider processing |
| Data correctness | Join/reconciliation defects and metric recomputation | Same checks against the same source manifest |
| Coverage | Eligible orders, sellers, categories, and available reviews represented; show denominators | Same definitions plus processed/blocked/missing dispositions |
| Finding quality | Independent reviewer rates supported and useful findings using an agreed rubric | Blindly reviewed findings, unsupported-claim and correction rates |
| Feedback quality | Adjudicated review-theme sample and ambiguity disposition | Jev agreement/abstention against that same sample |
| Traceability | Share of checked claims verifiable to source records | Same measure, with source-to-artifact lineage |
| Cost | Loaded human-time assumption and tooling | Human review plus measured compute/provider/runtime cost |

Set numeric success thresholds before final evaluation, after the data profile and human baseline show what is measurable. Do not tune against the final holdout.

### Manual-baseline protocol (BINT-1; timed comparison deferred to release evaluation)

**Assignment.** “Using the frozen Olist reporting slice, prepare a Seller Performance review for the Seller Operations Manager. Reconcile eligible orders and items; report delivery performance with counts and denominators; summarize available customer ratings/review themes; identify seller/category patterns that merit human investigation; and provide source-linked examples, coverage, unknowns, and limitations.” The output is a full-period summary plus evidence-backed findings—not a predetermined number of order cases.

**Source and freeze.** Use Kaggle's Olist Brazilian E-Commerce Public Dataset v2 under the product-owner-approved non-commercial local prototype/demo boundary (CC BY-NC-SA 4.0; retain attribution; no commercial incorporation/redistribution). BINT-3's source manifest contains archive/file hashes. BINT-5 freezes the report period, eligible population, source-file manifest, and historical cutoff for the initial descriptive report. Before any later timed human or model evaluation, also freeze the comparison protocol and chronological development/holdout split. Humans and automation receive the same information. Do not let post-cutoff reviews or outcomes support claims about what was knowable at the cutoff.

**Attribution rules.** Order delivery can be associated with a seller only when all items in that order identify exactly one seller; report multi-seller orders separately at marketplace level. Associate review text with a category only when the order's item-category set is unambiguous; otherwise use marketplace-level feedback or mark attribution unknown. Describe associations, not causes. Always show denominators, missing coverage, and the eligibility rule. Do not interpret missing comments as no complaint.

**Human exercise.** A Marketplace Seller Performance Analyst uses ordinary spreadsheet/SQL tools, but no Jev labels, generated findings, or predictor scores. Start elapsed time when the frozen input package is released; record active analyst minutes separately. The analyst produces the assignment above and submits it for independent acceptance. A second reviewer checks metric recomputation, joins, evidence links, unsupported attribution/causal claims, and usefulness of findings; record reviewer time, corrections, and acceptance disposition. Preserve the exact sample, instructions, report, and timing log.

**Comparison.** Run the automated workflow over the same frozen inputs and report specification. Compare elapsed time, hands-on human effort, reconciliation correctness, eligible-record/feedback coverage, finding validity/usefulness, correction burden, traceability, freshness, and measured total cost. Reviewers should assess human and automated findings without seeing which produced them where practical. This primary report comparison has no fixed findings cap. If a later predictor experiment needs equal-capacity ranking, set capacity from measured analyst workload and freeze it before the held-out evaluation; the unit is seller/category findings, never “20 orders.”

**Confirmed demo cadence (product-owner approval: 2026-09-23).** Use a calendar-month Seller Performance review, comparing the selected month with the immediately preceding comparable month. The data replay can then reveal orders/reviews as historical dates advance. This is a demo convention, not a claim about Olist's internal cadence; eBay documents monthly seller-performance evaluation, while Walmart uses rolling 30/60-day windows. After the source profile, select periods by a fixed chronological rule and confirm sufficient eligible volume before examining holdout findings. Sources: [eBay seller-performance monitoring](https://www.ebay.co.uk/help/selling/selling/monitor-service-metrics?id=4785); [Walmart Marketplace performance standards](https://marketplacelearn.walmart.com/guides/Policies%20&%20standards/Performance/Seller-performance-standards).

**Draft independent acceptance rubric.** Mark each check pass/correction/reject: (1) source totals and joins reconcile; (2) every KPI has correct formula, unit, period, eligible denominator, and missingness; (3) seller/category attribution obeys the single-seller/single-category rules; (4) each finding has verifiable evidence and makes no unsupported causal claim; (5) coverage, ambiguity, and limitations are explicit; (6) the manager can identify a justified follow-up from the report. Overall disposition is accepted, accepted after correction, or rejected, with reviewer time and reason recorded. Name the independent reviewer before the timed baseline.

**BINT-1 decision record.** The product owner confirmed the Marketplace Seller Performance Analyst, Seller Operations Manager recipient, seller/category report, monthly demo cadence, no fixed finding cap for the primary report, and conditional prediction boundary. The baseline protocol and acceptance rubric are specified. BINT-5 implements the first descriptive report; name an independent reviewer and freeze the human exercise and chronological holdout rule before the later timed comparison. Numeric win thresholds are set only after the human baseline and before holdout evaluation. Provider spend, model licensing beyond approved Olist use, cloud deployment, and external notifications remain separately gated; none is authorized by this protocol.

### Business output

The v0.1.0 output is a **Seller Performance review package**:

1. Period-level delivery and customer-experience metrics with definitions, denominators, and coverage.
2. Seller/category findings that merit review, without unsupported causal claims.
3. Source-linked order and review evidence, with ambiguous multi-seller/category attribution visible.
4. A concise manager briefing that distinguishes actuals, interpreted feedback, hypotheses, and optional predictions.
5. A reproducible record of source versions, calculations, questions, and reviewer corrections.

Delivery-risk prediction is a separate experiment. If it does not improve an agreed prioritization baseline, disclose that result; the descriptive review package remains the primary business deliverable.

## 3. Principal brief

### Outcome

A Marketplace Seller Performance Analyst can submit a historical Olist reporting slice to a durable local workflow, return after processing, and receive an evidence-linked seller/category review for the Seller Operations Manager. The analyst can verify calculations, inspect review-text interpretations, correct uncertain findings, and trace displayed claims back to source rows and definition versions.

### Primary user

Marketplace Seller Performance Analyst at an Olist-like multi-seller marketplace. The analyst prepares a recurring review of seller/category delivery performance and customer-feedback patterns, then investigates supported changes with evidence. The Seller Operations Manager is the primary recipient of the briefing. This emulates a marketplace operations function; it does not claim to reproduce Olist's internal organization or workflow.

### Secondary users

- Data/model analyst reviewing data quality and predictor evidence.
- Seller Operations Manager receiving a point-in-time summary with drill-down links.

### Acceptance sources

- Olist source manifests and audited table contracts.
- Approved Jev question/rubric definitions and independently reviewed examples.
- Versioned target and feature definitions.
- Chronological predictor evaluation manifests.
- Deterministic replay fixtures and expected outcomes.
- Exact-candidate product-validation evidence.

### Owned surface

- Local source ingestion and replay.
- Durable job admission and execution.
- Application relational data and artifact manifests.
- Jev adapter and semantic observation contracts.
- Feature and target construction.
- CatBoost and TabICLv2 preparation, evaluation, and scoring.
- Local seller/category finding views, review records, and downloadable snapshots.
- Restricted artifact-code execution and review.

### Invariants

1. Source facts, model observations, actual outcomes, predictions, and narratives remain distinguishable.
2. Every result identifies its exact source, schema, question, feature, model, and policy versions.
3. Future evidence and labels cannot enter earlier feature rows or model context.
4. A completed workflow is not automatically an accepted output.
5. Retries cannot duplicate accepted rows, episodes, publications, or simulated deliveries.
6. Stale or missing data is unknown, not false, zero, on-time, or resolved.
7. Predictions are not presented as facts or causal explanations.
8. Generated code receives no production credentials or unrestricted host access.
9. External notifications and business actions are not authorized in v0.1.0.
10. Required evidence ends as `passed`, `failed`, or `blocked`.

### Forbidden outcomes

- Using an order's eventual review to predict that same order at approval time.
- Treating missing delivery as on-time delivery.
- Inflating revenue or counts through unsafe one-to-many joins.
- Treating Jev confidence as delivery-risk probability.
- Attributing a multi-seller order review to every seller.
- Publishing incomplete refreshes as complete.
- Allowing generated code to alter protected application code, dependencies, policies, or recipients.
- Presenting mocked classifications as Jev output.
- Silently substituting one predictor for another.
- Sending real email, Slack, Teams, or seller/customer communications.

### Primary risks

- Olist's historical availability timestamps may not support every intended feature.
- Portuguese review interpretation may not meet quality requirements.
- Aegra is beta and its recovery semantics are not yet locally validated.
- Jev service availability, cost, and terms may block a real adapter test.
- TabICLv2 checkpoint/dependency licensing or local resource use may be unsuitable.
- Delivery-risk prediction may not improve over a simple baseline.
- Generated-code execution can expand security and validation scope rapidly.

### Stop conditions

Stop and return to design when:

- Source profiling invalidates the target or point-in-time assumptions.
- Required provider/model licensing is unresolved.
- Reviewed Jev quality is below the threshold agreed before the experiment.
- Durable admission or replay-safe publication cannot be demonstrated.
- Required cost telemetry is unknown.
- Sandbox isolation tests expose host secrets, credentials, or unauthorized networking.
- Product validation is not bound to the exact candidate commit.

### External-action authority

v0.1.0 may autonomously create and update **local seller/category review records** under approved demo policies. These are not customer-support tickets and do not imply seller fault. New policies, generated executable artifacts, predictor promotion, recipients, cloud deployment, and every outward notification require explicit approval.

## 4. Confirmed business contract and proposed technical decisions

The product owner confirmed the business contract and core user on 2026-09-23:

- **Primary user:** Marketplace Seller Performance Analyst; Seller Operations Manager receives the briefing.
- **Process to improve:** Manually reconciling marketplace order/delivery data, reviewing customer feedback, identifying seller/category trends, and preparing a supported performance briefing.
- **v0.1 output:** An evidence-linked seller/category review and management briefing, compared with a measured human baseline. Orders are supporting drill-down evidence, not assumed to be pre-existing support cases.
- **Prediction boundary:** Test late delivery at order approval only if Olist supports a valid point-in-time target; otherwise deliver descriptive triage and report prediction as blocked, not as a claimed capability.
- **Baseline comparison:** Same frozen sample and report specification; compare elapsed time, human effort, data/claim quality, coverage, correction burden, traceability, and total cost. A capped ranking comparison is a separate optional experiment.

The following implementation choices remain proposals subject to source profiling, license review, and validation.

| Decision | Proposed v0.1.0 choice |
|---|---|
| Dataset | Olist Brazilian E-Commerce Public Dataset on Kaggle: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce. Kaggle's public metadata API checked 2026-09-23 reports version 2, 126,186,995 bytes, and CC BY-NC-SA 4.0. Product owner approved use strictly for a non-commercial local prototype/demo on 2026-09-23; no commercial incorporation or redistribution is authorized. Record attribution and observe share-alike terms for any covered adaptations; revisit rights before public/commercial use. |
| Replay mode | Historical simulation using explicit business and wall clocks |
| Primary prediction | Conditional experiment: late delivery among eligible orders, only if point-in-time validity is established |
| Prediction time | Order approval, subject to source timestamp audit |
| Primary stakeholder | Marketplace Seller Performance Analyst; briefing recipient: Seller Operations Manager |
| Jev scope | Fixed, reviewed questions over review text; no automatic feature discovery |
| Predictors | CatBoost baseline and TabICLv2 candidate behind one feature contract |
| Runtime | Aegra candidate in worker-backed local mode, subject to proof |
| Application store | PostgreSQL logical application database separate from Aegra-owned tables |
| Bulk/artifact storage | Local content-addressed files initially |
| Review authority | Local attention episodes only |
| Artifact authority | Approved templates plus restricted generated-code surface |
| Sandbox | Hardened local provider behind a provider-neutral interface |
| Delivery | Local authenticated application links and downloadable snapshots |
| Cloud execution | Not required for v0.1.0; evaluation follows local proof |

### BINT-3 source profile (Kaggle v2; non-commercial local prototype)

**Acquisition and provenance:** Kaggle public dataset `olistbr/brazilian-ecommerce`, version 2, current as checked 2026-09-23; license `CC BY-NC-SA 4.0`. The product owner approved strictly non-commercial local prototype/demo use. No commercial incorporation or redistribution is authorized; retain attribution and observe applicable share-alike terms, and revisit rights before any public/commercial use. The ZIP is stored outside the Git checkout at `~/Library/Application Support/BackIntel/Datasets/OlistV2/brazilian-ecommerce.zip`; the source-only profile and reproducible local profiler are alongside it. ZIP size is 44,717,580 bytes; SHA-256 is `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`. Dataset files are not in Git.

**Measured rows and relationships:**

| CSV | Rows |
|---|---:|
| Customers | 99,441 |
| Geolocation | 1,000,163 |
| Order items | 112,650 |
| Payments | 103,886 |
| Reviews | 99,224 |
| Orders | 99,441 |
| Products | 32,951 |
| Sellers | 3,095 |
| Product-category translations | 71 |

- `order_id` is unique across 99,441 order rows. The observed order/customer, item/order, item/seller, item/product, and review/order joins have no unmatched foreign IDs under the measured keys. 775 orders have no item rows (603 unavailable, 164 canceled, 5 created, 2 invoiced, 1 shipped); eligibility and reporting must handle these statuses explicitly.
- The item key `(order_id, order_item_id)` is unique. 1,278 orders contain items from multiple sellers; order-level feedback must not be assigned to every seller in such orders.
- Reviews cover 98,673 distinct orders; 547 orders have multiple review rows. `review_id` is not a safe unique key here: 789 review IDs occur across multiple orders. Preserve a source-row identity and audit those anomalies before choosing a canonical review grain.
- There are 40,950 nonblank review comments out of 99,224 review rows; missing free text is common. Two non-null product categories are absent from the English translation mapping.

**Time and target feasibility:** order purchases range from 2016-09-04 to 2018-10-17; approval timestamps range from 2016-09-15 to 2018-09-03, with 160 missing; delivered-customer timestamps range from 2016-10-11 to 2018-10-17; estimated delivery dates range from 2016-09-30 to 2018-11-12. Review creation ranges from 2016-10-02 to 2018-08-31 and review-answer timestamps through 2018-10-29. `shipping_limit_date` has four rows in 2020 despite the main order period ending in 2018; flag/exclude or explain these before feature use.

A **retrospective outcome candidate** is computable as delivered orders whose actual customer-delivery timestamp is after estimated delivery: 96,456 delivered orders have approval plus both outcome timestamps; 7,826 meet that late definition (8.11%). This is a descriptive base rate, not evidence of predictive performance or a validated production target. There are 96,478 delivered orders total; eight lack one of the two outcome timestamps. The approval-time experiment remains conditional: this historical extract does not contain source-ingestion/availability history, and later reviews cannot be inputs for the same order's approval-time prediction. Only a timestamp-respecting replay using features demonstrably available by the prediction cutoff can test that hypothesis.

**Emulation boundary:** this is Olist's historical multi-seller marketplace dataset, not Amazon, Walmart, or a standalone Shopify merchant; it has no per-order marketplace-channel field, live update stream, seller-contact/intervention log, or carrier-exception feed. It can support a simulated seller/category performance review with order/review drill-downs, but cannot prove live incident handling, seller accountability, or intervention impact.

**Reproducible evidence:** local manifest/profile: `~/Library/Application Support/BackIntel/Datasets/OlistV2/source-manifest-profile.json`; profiler: `~/Library/Application Support/BackIntel/Datasets/OlistV2/profile_olist.py`. Both are outside the repository for now; add repository-managed profiling code after the validation bootstrap. The profiler verifies the exact nine-file archive inventory and expected sizes, extracts safely, computes SHA-256, streams CSV row/schema/null/key/date profiles, and checks joins/target counts.

Sources: [Kaggle dataset page](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce); [Kaggle metadata API](https://www.kaggle.com/api/v1/datasets/view/olistbr/brazilian-ecommerce); [Kaggle file-list API](https://www.kaggle.com/api/v1/datasets/list/olistbr/brazilian-ecommerce); [Olist marketplace integrations](https://olist.com/integracao-com-marketplaces/).

If the delivered-late target proves analytically unsound, the release retains descriptive customer-experience intelligence but cannot claim predictive capability until a replacement target is approved.

## 5. Release scope

### Must have

1. Documented and measured human baseline for producing the defined operations review package from a bounded Olist sample.
2. Reproducible Olist acquisition manifest and data profile.
3. Validated core relational tables with reconciled joins and counts.
4. Durable partition-job lifecycle with restart and duplicate protection.
5. Fixed Jev questions with provenance, distributions, and human correction history.
6. Point-in-time feature snapshots and separately versioned outcomes.
7. CatBoost structured-only and structured-plus-Jev comparison.
8. TabICLv2 structured-only and structured-plus-Jev comparison, unless blocked by a recorded license/resource gate.
9. Versioned predictor evaluation and explicit activation decision.
10. Seller/category findings view and evidence drill-down for the Seller Performance review.
11. Executive point-in-time snapshot separating actuals and predictions.
12. One policy-governed local attention episode with enter, update, acknowledgment, and clear behavior.
13. One restricted generated-artifact candidate executed and reviewed in a local sandbox.
14. Exact-candidate validation evidence covering behavior, recovery, data, model, UI, cost, and safety.

### Should have

- Analyst/model-health view.
- PDF or workbook export.
- Portuguese-direct versus translated Jev comparison.
- Shadow predictions from the non-active model.
- Demonstration of source correction and targeted downstream invalidation.

### Explicitly out of scope

- Amazon Reviews scale processing.
- Live enterprise connectors.
- Excel, Word, Slack, or Teams production integrations.
- Real external notifications.
- Cloud deployment or cloud sandbox selection.
- General-purpose schema discovery.
- Automatic Jev question generation.
- TabICL weight fine-tuning.
- Predictor ensembles.
- Kubernetes, distributed compute, vector databases, or a generic ontology platform.
- Multi-tenant public execution of arbitrary code.

## 6. Sub-objectives and epics

## Epic 0 — Release contracts and validation foundation

**Objective:** Turn the research into approved, testable product contracts before implementation begins.

Deliverables:

- Confirm primary user, target, prediction time, and historical replay limitations.
- Define the manual operations-intelligence baseline protocol and acceptance points.
- Define v0.1.0 success measures and threshold-setting process.
- Create the repository validation bootstrap required by workspace policy.
- Define durable evidence output bound to the exact commit.
- Pin decision owners and external-action boundaries.
- Establish initial threat model and data/license register.

Exit criteria:

- Principal brief approved.
- Required acceptance outcomes are unambiguous.
- Product-validation configuration and CI proof mechanism exist.
- No unresolved decision prevents the first vertical slice.

## Epic 1 — Olist source and relational foundation

**Objective:** Establish trustworthy source records and core business facts.

Deliverables:

- Acquire the approved Olist files and record hashes, rights, schemas, and row counts.
- Profile key uniqueness, duplicates, nulls, review language, and timestamps.
- Produce a minimal reproducible monthly seller/category calculation and source-linked readout from a frozen source slice, as a correctness fixture for the later pipeline—not a finished manager dashboard. Defer the timed human exercise to release evaluation.
- Implement immutable source batches and records.
- Build canonical orders, items, sellers, products, payments, customers, and reviews.
- Add reconciliation checks preventing row multiplication and monetary inflation.
- Document historical availability assumptions and exclusions.

Exit criteria:

- Source and curated counts reconcile.
- Join cardinalities are measured, not assumed.
- One displayed source row traces to its immutable input.
- One minimal seller/category readout states its period, eligibility, counts, denominators, missingness, attribution rules, and source-linked examples. Its calculations and limitations are checked; presentation quality and manager usefulness belong to the later stakeholder-experience work.
- Target feasibility is confirmed or explicitly rejected.

## Epic 2 — Durable local background execution

**Objective:** Prove that accepted work survives disconnection and recoverable failures.

Deliverables:

- Pin and inspect an Aegra candidate and dependencies.
- Run worker-backed local topology with PostgreSQL and broker infrastructure.
- Define stable partition and operation identities.
- Implement job admission, status, cancellation, retry, and final disposition.
- Keep bulk data outside graph checkpoints.
- Build a deterministic mock partition workflow before connecting models.

Required tests:

- Submit and disconnect.
- Duplicate and concurrent submission.
- Lost HTTP response after admission.
- Worker termination before checkpoint and after application write.
- Redis/broker and full-stack restart.
- Interrupt/resume without repeated effects.

Exit criteria:

- Acknowledged work is durable.
- Accepted domain rows and artifacts are not duplicated.
- Failed, blocked, partial, and published states remain distinguishable.
- Aegra is selected, conditionally accepted, or rejected with evidence.

## Epic 3 — Jev semantic evidence pipeline

**Objective:** Convert review language into bounded, traceable semantic observations.

Initial question set:

- Delivery complaint expressed — Noul.
- Packaging damage mentioned — Noul.
- Product functionality mentioned — Noul.
- Primary issue — Choice with explicit none/other.
- Described impact severity — Score with approved rubric.

Deliverables:

- Versioned question definitions and interpretation notes.
- Jev adapter with pinned package/model behavior.
- Bounded batching, retry, caching, cost, and rate controls.
- Original text preservation and language/translation provenance.
- Immutable model answers plus separate resolution/correction history.
- Independently reviewed benchmark sample including ambiguity and adversarial text.

Exit criteria:

- Response shapes and probability constraints validate.
- Unsupported or uncertain cases route to review rather than forced facts.
- Quality and cost results meet pre-agreed gates or are marked blocked.
- Every accepted signal traces to the source text and exact question version.

## Epic 4 — Point-in-time features and target

**Objective:** Produce leakage-resistant model-ready rows with separately observed outcomes.

Deliverables:

- Versioned delivered-late target and eligibility/censoring rules.
- Approval-time feature recipe.
- Historical seller performance features using only available prior outcomes.
- Prior Jev-derived review features using only previously available reviews.
- Multi-seller attribution and aggregation policy.
- Immutable feature and outcome manifests.
- Automated leakage, missingness, and grain checks.

Exit criteria:

- Every feature has formula, grain, units, cutoff, denominator, and null policy.
- No future source or label enters a prediction row or context.
- Missing and ineligible outcomes are not silently converted to negatives.
- Rebuilding from the same manifest produces the same table.

## Epic 5 — Predictor comparison and activation

**Objective:** Determine whether Jev-derived features and TabICLv2 add value beyond conventional structured prediction.

Required experiment matrix:

| Predictor | Structured features | Jev features |
|---|---:|---:|
| CatBoost | Yes | No |
| CatBoost | Yes | Yes |
| TabICLv2 | Yes | No |
| TabICLv2 | Yes | Yes |

Deliverables:

- Simple base-rate reference.
- Chronological train/development/test manifests.
- CatBoost training and bounded tuning.
- TabICLv2 context preparation and inference.
- Shared evaluation cases and disclosed resource differences.
- Calibration, review-capacity, latency, memory, and cost assessment.
- Versioned predictor registry and activation record.

Exit criteria:

- Final holdout did not guide question, feature, or threshold revisions.
- The value of Jev features is separable from predictor choice.
- One predictor is explicitly activated, or a no-predictor decision is recorded.
- Poor performance cannot be hidden by the artifact layer.

## Epic 6 — Stakeholder artifacts and local attention episodes

**Objective:** Turn accepted results into differentiated, useful stakeholder views.

Required artifacts:

1. **Seller Performance review:** period metrics, eligible denominators, coverage, supported seller/category findings, and linked order/review evidence.
2. **Manager snapshot:** actual delivery/customer-experience measures, separately labeled optional forecast, material changes, and drill-down links.
3. **Analyst evidence view:** source, feature, outcome, model, cost, and quality lineage.

Required local episode behavior:

```text
normal -> watch -> active -> unknown/stale -> cleared
                 |
                 +-> acknowledged -> investigating -> resolved
```

Deliverables:

- Versioned artifact definitions and immutable artifact versions.
- Deterministic metric and chart generation from accepted result bundles.
- Fixed demo escalation policy with evidence gates, persistence, hysteresis, cooldown, and clear rules.
- Local inbox only; simulated delivery audit.
- Scheduled, event-driven, and deadline-driven replay triggers.

Exit criteria:

- Displayed values reconcile exactly to accepted results.
- Actuals, predictions, and hypotheses are visibly distinct.
- Duplicate events do not create duplicate episodes.
- Acknowledgment does not clear the underlying condition.
- Stale data changes the case to unknown rather than resolved.

## Epic 7 — Restricted artifact-generation execution plane

**Objective:** Demonstrate that an agent can create a new presentation safely without obtaining production authority.

Deliverables:

- Versioned starter project and owned design-system components.
- Protected and writable source boundaries.
- Provider-neutral sandbox broker contract.
- Hardened local sandbox provider.
- Pinned dependencies and dependency allowlist.
- Build, type, lint, test, browser, accessibility, and screenshot checks.
- Temporary localhost preview and review page.
- Candidate source bundle, build manifest, logs, screenshots, and review decision.

Exit criteria:

- Generated code cannot read host secrets, broad host files, or production data.
- Network, resource, process, filesystem, and lifetime limits are demonstrated.
- New dependencies and protected-file changes are rejected.
- Sandbox disappearance can be reconstructed from the durable job record.
- Publication requires explicit approval and a clean rebuild.

## Epic 8 — Integrated validation and release

**Objective:** Prove the whole system on one exact v0.1.0 candidate.

Deliverables:

- End-to-end Olist replay scenario.
- Fault-injection and replay test report.
- Jev quality and cost evidence.
- Data reconciliation and leakage evidence.
- Predictor comparison report.
- Rendered UI and artifact review evidence.
- Sandbox safety evidence.
- Known limitations and blocked outcomes.
- Reproducible local operator instructions.

Exit criteria:

- Every must-have acceptance outcome is passed or the release is blocked.
- Evidence identifies the exact candidate commit, data manifest, model versions, question set, feature recipe, policy, and sandbox image.
- A fresh local run reproduces the published demonstration.
- No cloud, external notification, or production action is required to demonstrate v0.1.0.

## 7. Suggested sprint sequence

The durations below are planning increments, not delivery commitments. Re-estimate after Epic 1 profiles the actual data and Epic 2 proves the runtime.

| Sprint | Sprint goal | Primary epics | Demonstrable increment |
|---|---|---|---|
| 0 | Confirm release contracts and validation foundation | Epic 0 | Approved brief, acceptance map, validation bootstrap |
| 1 | Make Olist facts trustworthy and preserve a checked output | Epic 1 | Reconciled source-to-core data plus one minimal monthly seller/category correctness fixture |
| 2 | Make background work durable | Epic 2 | Submit/disconnect/restart mock partition demo |
| 3 | Turn reviews into traceable observations | Epic 3 | Reviewed Jev signals and correction trace |
| 4 | Build one leakage-safe prediction dataset | Epic 4 | Immutable approval-time feature/outcome snapshot |
| 5 | Compare predictors honestly | Epic 5 | Four-way model evidence and activation decision |
| 6 | Deliver the Seller Performance review | Epic 6 | Local seller/category findings view, manager snapshot, and review-record lifecycle |
| 7 | Generate and review executable artifacts safely | Epic 7 | Sandboxed candidate with preview and validation evidence |
| 8 | Prove the integrated release | Epic 8 | Exact-candidate replay, failure recovery, and release review |

A single small team should expect roughly nine planning increments. Parallel work is appropriate only after contracts stabilize—for example, artifact component design can proceed alongside model evaluation once result schemas are frozen.

### Immediate execution goal — finish Sprint 1

**Outcome:** A checked, source-linked historical calculation is available as an input/output fixture. Sprint 1 does not deliver an accepted manager experience, a background agent, or AI interpretation.

1. **Review BINT-4's facts contract.** Accept only after reviewing the migration, source lineage, synthetic join tests, and full Olist reconciliation; tests alone are not business acceptance.
2. **Keep BINT-5 as a narrow correctness fixture.** Retain the committed February–March seller/category calculation, source links, and independent checks. Reviewer acceptance of a manager-facing report is deferred to the stakeholder-experience stage. A locally overwritten HTML/JSON preview from uncommitted code must not be described as an exact-commit artifact.
3. **Move to the defining demo loop.** Sprint 2 proves durable admission, processing, restart, and replay of a bounded new Olist batch; Sprint 3 produces versioned Jev observations from review text. The first integrated demo shows which checked finding changed because of the new batch and links back to source evidence. No model or inference spend without separate authorization.
4. **Return to presentation when the loop works.** Define the manager's question, verified change-result contract, and audience views before building the permanent dashboard or generated artifacts. The experimental Reflex screen is not a Sprint 1 exit gate. No human time saving is claimed without a measured baseline.

**Stop conditions:** source terms or reconciliation invalid; period eligibility cannot be defined without inventing business rules; unsupported seller/category attribution; missing reviewer acceptance; or missing/failed exact-candidate evidence. No paid calls, persistent infrastructure provisioning, push/PR, external messages, or deployment are authorized by this goal.

## 8. Critical path and dependencies

```text
Epic 0
  -> Epic 1
      -> Epic 3
      -> Epic 4
          -> Epic 5
              -> Epic 6
                  -> Epic 8

Epic 0 -> Epic 2 -------------------------> Epic 8
Epic 0 -> design-system contract -> Epic 7 -> Epic 8
Epic 6 result contracts -----------------> Epic 7
```

Critical dependency rules:

- Real Jev work waits for source profiling, rubric approval, budget, and provider authorization.
- Predictor work waits for accepted point-in-time features and labels.
- Risk-based escalation waits for evaluated model outputs; deterministic data-health cases do not.
- Executable artifact generation waits for stable analytical-result and design-system contracts.
- External integrations wait until after local delivery is validated.
- Amazon scale work waits until unit economics and partition recovery are measured on Olist.

## 9. Scrum execution model

### Backlog hierarchy

```text
Release goal
  -> Epic
      -> Thin vertical story
          -> Acceptance checks
              -> Durable evidence
```

Stories should produce observable behavior rather than horizontal infrastructure alone. Example:

> As a Marketplace Seller Performance Analyst, I can inspect a seller/category finding with its period, denominator, coverage, and source-linked order/review evidence, so that I can verify whether it merits follow-up before briefing the Seller Operations Manager.

### Definition of Ready

A story is ready only when it has:

- User or operator outcome.
- Acceptance source and observable criteria.
- Owned data/code surface.
- Dependencies and blockers.
- Forbidden outcomes.
- Required evidence.
- External-action authority.

### Definition of Done

A story is done only when:

- Acceptance behavior is demonstrated.
- Automated and required product validation passes.
- Data and model lineage is recorded where applicable.
- Failure and retry behavior is covered for durable workflows.
- Security and permissions are verified for changed surfaces.
- Evidence is non-empty and bound to the exact candidate commit.
- Documentation and operational contracts are updated.
- No unresolved required evidence remains unknown.

### Sprint review questions

1. What can a stakeholder do now that they could not do before?
2. Which evidence proves it?
3. What remains simulated or mocked?
4. What failed or is blocked?
5. Did cost, latency, or reviewer burden change?
6. Which assumption should be retired or converted into a deterministic test?

## 10. Release success measures

Numeric thresholds should be set after the Olist profile and before evaluating final holdouts. The categories are fixed now.

### Data integrity

- Source-to-curated count reconciliation.
- Duplicate and join-inflation defects.
- Feature completeness and historical availability coverage.
- Provenance trace success rate.

### Semantic interpretation

- Per-question reviewed quality.
- Ambiguity/abstention handling.
- Portuguese-direct versus translation difference where tested.
- Cost, latency, retry rate, and provider failure rate.

### Prediction

- Base-rate, CatBoost, and TabICL comparison.
- PR-AUC/ROC-AUC as appropriate.
- Log loss/Brier score and calibration.
- For the optional prioritization experiment only: precision/recall among seller/category findings at a predeclared reviewer capacity.
- Coverage, warning lead time, latency, memory, and cost.

### Workflow reliability

- Durable admission success.
- Recovery without duplicate accepted effects.
- Queue lag, retries, cancellation, and blocked dispositions.
- Reproducible artifact publication.

### Stakeholder usefulness

- Artifact values matching authoritative results.
- Time to trace a finding to evidence.
- Seller/category finding usefulness, correction burden, and simulated attention volume in replay.
- Correct handling of stale data, acknowledgment, and resolution.

### Execution-plane safety

- Unauthorized file, secret, and network access blocked.
- Resource and lifetime limits enforced.
- Dependency and protected-file policy enforced.
- Preview and cleanup lifecycle reconciled.

## 11. Risk register and mitigations

| Risk | Impact | Early mitigation |
|---|---|---|
| Olist timing cannot support target | Predictive slice invalid | Profile timestamps and availability in Sprint 1; permit explicit no-go |
| Jev Portuguese quality is weak | Semantic features unreliable | Review benchmark; compare direct and translation paths; preserve unknown |
| Jev access or spend blocked | Core named capability unavailable | Deterministic adapter/mocks for plumbing; release remains blocked for real Jev claim |
| Aegra recovery differs from claims | Background durability unreliable | Failure injection before model integration; preserve fallback runtime boundary |
| TabICL resource or license issue | Four-way comparison incomplete | Verify exact checkpoint first; keep CatBoost production-capable baseline |
| Predictor adds no value | Predictive prioritization is not defensible | Treat no-predictor outcome as valid; the descriptive Seller Performance review remains the primary deliverable |
| Alert fatigue | Stakeholder rejects capability | Local replay, explicit capacity, hysteresis, cooldown, and measured false-alert burden |
| Generated code escapes intended surface | Host/data security risk | Restricted starter, isolated execution, deny-by-default access, and safety tests |
| Artifact scope delays release | No integrated demo | Require three fixed artifacts; new formats and integrations remain out of scope |
| Cost telemetry incomplete | Scale claim cannot be trusted | Cost/status required at every provider and execution attempt; unknown means blocked |

## 12. Release review

v0.1.0 is ready only if the team can demonstrate, from a clean local environment:

1. Produce the defined review package through the documented human baseline and record its effort, coverage, quality, freshness, and cost.
2. Submit the same bounded Olist replay to the automated workflow and disconnect.
3. Observe durable, restart-safe progress.
4. Inspect accepted source facts and Jev observations.
5. Reproduce a point-in-time feature row and outcome.
6. Compare CatBoost and TabICL evidence without temporal leakage.
7. Open an operations artifact and trace every displayed claim.
8. Compare automated cycle time, effort, coverage, quality, freshness, and total cost with the frozen human baseline.
9. Watch an approved local policy create, update, and clear one attention episode.
10. Review one agent-generated executable artifact inside a sandbox.
11. Re-run duplicate and failure scenarios without duplicate accepted effects.
12. Retrieve complete exact-candidate validation evidence.

If any required step lacks evidence, the release disposition is `blocked`, not "mostly done."

## 13. Post-v0.1.0 direction

Only after the release gate:

- Select and validate a cloud execution provider by workload.
- Add an authenticated remote preview path.
- Evaluate one Amazon Reviews category for partition scale and unit economics.
- Define an Amazon-specific prediction or descriptive target.
- Add one workplace delivery adapter after permission and revocation design.
- Consider automatic question discovery, rolling-risk models, or TabICL fine-tuning only when measured limitations justify them.
