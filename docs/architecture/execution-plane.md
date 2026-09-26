# Artifact Execution Plane

**Status:** Architecture working draft  
**Scope:** Generated code execution, validation, preview, export, promotion, and delivery  
**Implementation status:** No sandbox runtime or artifact application has been installed  
**Related research:**

- [`../research/background-agents-research.txt`](../research/background-agents-research.txt)
- [`../research/open-source-runtime-study.txt`](../research/open-source-runtime-study.txt)
- [`../research/model-to-relational-data-design.txt`](../research/model-to-relational-data-design.txt)
- [`../research/stakeholder-artifacts-and-escalation.txt`](../research/stakeholder-artifacts-and-escalation.txt)

## 1. Purpose

The execution plane provides controlled computing environments where an agent can create, build, run, inspect, and revise executable artifacts without receiving unrestricted access to the application host or production data.

An executable artifact may be:

- A React dashboard or focused case page.
- A generated chart or interactive visualization.
- A PDF, workbook, document, or image export.
- A bounded analytical script.
- A temporary data exploration interface.

The execution plane is not the system of record and is not the production publication environment. It is a disposable workbench between artifact planning and artifact approval.

## 2. Core architectural principle

> Agents may generate code, but generated code is untrusted until it has been isolated, built, tested, rendered, inspected, and explicitly promoted.

The system therefore separates four responsibilities:

1. **Control plane:** decides what work is due and records its lifecycle.
2. **Data plane:** supplies approved, point-in-time analytical results.
3. **Execution plane:** runs generated code in an isolated environment.
4. **Delivery plane:** publishes approved artifacts to authorized stakeholders.

```text
Sources and events
       |
       v
Evidence, observations, features, predictions
       |
       v
Validated analysis result -------------------------+
       |                                            |
       v                                            |
Artifact request and generation plan                |
       |                                            |
       v                                            |
Aegra + LangGraph control plane                     |
       |                                            |
       v                                            |
Sandbox broker                                      |
       |                                            |
       +--> Local provider                          |
       +--> Cloud sandbox provider                  |
       |                                            |
       v                                            |
Build -> test -> run -> render -> inspect           |
       |                                            |
       v                                            |
Candidate source, screenshots, logs, reports -------+
       |
       v
Human or policy approval
       |
       v
Clean rebuild and controlled publication
       |
       v
Authenticated link / dashboard / downloadable artifact
```

## 3. What requires a sandbox

A sandbox is required when the agent creates or executes code whose behavior is not already represented by approved application components.

| Activity | Sandbox? | Reason |
|---|---:|---|
| Refresh a dashboard using an approved query and component | Usually no | Trusted application code is only receiving new data. |
| Assemble an approved component specification | Usually no | Schema validation and ordinary rendering are sufficient. |
| Generate or modify React, TypeScript, Python, or shell code | Yes | The behavior is not trusted until executed and inspected. |
| Install a new package | Yes, plus dependency approval | Package installation changes the software supply chain. |
| Render a PDF from a trusted template | Isolated export worker recommended | Browser and document renderers process complex inputs. |
| Run an agent-written analytical script | Yes | It may consume resources, read files, or initiate network calls. |
| Train CatBoost or run heavy TabICL inference | Resource-isolated worker | Isolation protects service availability even when the code is trusted. |

The preferred default remains schema-driven composition from approved components. Executable generation is available when a stakeholder need cannot be satisfied by the approved catalog.

## 4. Functional components

### 4.1 Workflow control plane

**Candidate:** Aegra plus LangGraph.

Responsibilities:

- Receive scheduled, event-driven, and user-requested artifact jobs.
- Persist job state independently from any sandbox process.
- Route work through generation, execution, validation, review, and publication.
- Retry bounded operations without duplicating publications.
- Pause for review and resume from durable application state.
- Apply cost, concurrency, and authority limits.

A LangGraph checkpoint is not the artifact registry and is not a universal transaction across the sandbox, database, and notification services.

### 4.2 Artifact planner and code generator

Responsibilities:

- Consume an approved artifact request and data contract.
- Select an existing recipe or propose a candidate layout.
- Generate changes inside an approved starter project.
- Record assumptions and unresolved questions.
- Avoid direct access to production data and credentials.

The generator should receive:

- Stakeholder and decision objective.
- Approved metrics and evidence references.
- Representative or minimized data fixtures.
- Design-system components and tokens.
- Writable and protected file boundaries.
- Dependency allowlist.
- Acceptance checks.

### 4.3 Sandbox broker

The broker isolates provider-specific APIs from the workflow.

Proposed internal operations:

```text
create(template, resource_profile, timeout, network_policy)
write_files(files)
exec(argv, cwd, env, remote_timeout)
read_logs(cursor)
wait_for_exit(process_id)
wait_for_port(process_id, port)
expose_preview(port, access_policy, ttl)
download_outputs(paths)
snapshot_if_allowed()
destroy()
```

The application should persist the complete reproducible job, not only a sandbox or process identifier:

- Provider and sandbox ID.
- Base image or template digest.
- Source bundle and content hash.
- Command argv, working directory, and non-secret environment.
- Input fixture manifest.
- Resource and network policy.
- Current workflow step.
- Output and log locations.

### 4.4 Validation service

Automated validation should occur before human review:

1. Dependency and lockfile check.
2. Static type check.
3. Lint and prohibited-pattern checks.
4. Unit and contract tests.
5. Production build.
6. Start and readiness checks.
7. Browser console and network inspection.
8. Desktop and mobile rendering.
9. Accessibility checks.
10. Data-definition and provenance checks.
11. Resource-limit and timeout verification.
12. Screenshot, PDF, or workbook output verification where applicable.

Completion of the sandbox process does not mean the candidate passed validation. Required evidence ends as `passed`, `failed`, or `blocked`.

### 4.5 Review interface

A reviewer should receive one candidate page containing:

- Temporary live preview.
- Rendered desktop and mobile images.
- Source diff.
- Tests and build results.
- Dependency changes.
- Data sources and cutoff time.
- External requests attempted by the candidate.
- Known limitations.
- Approve, request revision, or reject controls.

### 4.6 Artifact registry

The registry records durable artifact identity and lineage. Candidate files and large outputs belong in object or artifact storage rather than ordinary database rows.

Proposed concepts:

```text
artifact_request
artifact_candidate
artifact_source_bundle
sandbox_execution
validation_run
review_decision
artifact_release
artifact_delivery
```

Every released artifact should identify:

- Recipe and design-system versions.
- Source and build hashes.
- Analytical result references.
- Data availability cutoff.
- Generator and execution environment versions.
- Validation result.
- Approver and approval time where required.
- Publication and retention policy.

### 4.7 Delivery plane

Delivery is separate from execution.

| Delivery form | Use | Access model |
|---|---|---|
| Authenticated application link | Interactive dashboard or review case | Authorization checked on every request. |
| Point-in-time PDF or workbook | Portable briefing or analysis | Download authorization; downloaded copies cannot reliably be revoked. |
| Slack or Teams message | Attention and concise status | Minimal content plus authenticated application link. |
| Localhost preview | Local development and review | Available only on the local machine unless deliberately proxied. |
| Temporary cloud preview | Remote candidate review | Short lifetime, authenticated proxy or signed URL, never permanent publication. |

A live dashboard and a historical snapshot are different products. A snapshot must not silently change after distribution.

## 5. Candidate execution providers

No provider has been selected. The provider interface should allow staged comparison.

### 5.1 Hardened local Docker or Podman

**Intended role:** First local, single-user architecture proof.

Advantages:

- Low setup burden.
- Familiar OCI images and build tooling.
- Local data can remain local.
- Fast iteration.

Limitations:

- Containers share the host kernel.
- Raw Docker is not the desired final boundary for public multi-tenant hostile code.
- Preview routing, leases, cleanup, and execution records remain our responsibility.

Minimum controls:

- Non-root user.
- Drop capabilities and set `no-new-privileges`.
- No Docker socket, home-directory, SSH, or credential mounts.
- Isolated writable workspace only.
- CPU, memory, PID, disk, and wall-clock limits.
- Network denied by default.
- Loopback-only preview binding.
- Pinned image and dependencies.
- Guaranteed cleanup and reconciliation of abandoned containers.

### 5.2 gVisor or VM-backed local execution

**Intended role:** Stronger isolation on a Linux sandbox host.

- gVisor adds a user-space kernel boundary while retaining much of the container workflow.
- Firecracker or Kata provides a stronger VM-backed boundary but requires Linux virtualization infrastructure.
- Firecracker does not run directly as the normal local runtime on macOS; it requires a Linux/KVM host.

This is an evolution path if generated code becomes multi-user or externally supplied.

### 5.3 Cloudflare Sandbox SDK 1.0 preview

**Status:** Candidate cloud execution provider; currently preview technology.

Cloudflare Sandbox runs isolated Linux environments on Cloudflare Containers, controlled from Workers. New applications are currently directed to the `@cloudflare/sandbox@next` package line. The Worker package and sandbox image must remain on the same preview line.

Relevant architecture characteristics:

- A stable sandbox ID maps to a Durable Object identity.
- The container behind that ID is not permanent.
- Processes and terminals belong to the current container only.
- Local files disappear on container stop or replacement unless backed up or mounted durably.
- The application must store complete job instructions and checkpoints outside the container.
- Public preview URLs require deliberate exposure and authentication; preview URLs are public by default in the documented flow.
- Production preview hostnames require wildcard DNS on a custom domain when using those URL patterns.
- Outbound traffic can be disabled or allowlisted.
- Trusted Worker-side outbound handlers can inject credentials without exposing them inside generated code.

The 1.0 preview process contract is important:

- `exec(argv)` resolves when the process starts and returns a handle.
- Output and completion are collected through handle methods.
- Shell syntax requires an explicit shell.
- Each launch has independent `cwd` and environment.
- Wait cancellation does not kill the remote process.
- Process IDs cannot be treated as durable job identities.

Cloudflare is especially relevant for temporary web previews because it combines execution, process readiness, port exposure, and Workers-based access control. Its preview status and platform-specific deployment model must be evaluated before adoption.

### 5.4 Modal

**Intended role:** Candidate for elastic build, render, analytical, and model-execution jobs.

Strengths:

- On-demand CPU, memory, and GPU resources.
- Prebuilt images and dependency layers.
- Bounded sandbox lifetimes.
- Filesystem snapshots and storage integrations.
- Encrypted port exposure for temporary services.
- Strong fit for parallel builds and heavy compute.

Questions to validate:

- Preview authentication architecture.
- Egress enforcement for generated code.
- Data-residency and sensitive-data constraints.
- Reconnect and recovery behavior for long reviews.
- Cost per candidate and idle preview.

### 5.5 E2B or Daytona

**Intended role:** Comparison candidates when interactive agent workspaces and long-lived previews become central.

These products expose workspace-oriented process, filesystem, lifecycle, and preview APIs. Daytona also documents private and expiring signed preview links and per-sandbox network controls. They should be compared only after the required interaction model is clear.

## 6. Provider selection by workload

One provider does not need to serve every workload.

| Workload | Initial candidate |
|---|---|
| Local single-user generated dashboard | Hardened Docker/Podman |
| Cloud temporary web preview | Cloudflare Sandbox candidate |
| Parallel PDF/image/build jobs | Modal candidate |
| Heavy CatBoost training or TabICL inference | Dedicated bounded model worker; Modal when elastic resources are useful |
| Long-lived interactive agent computer | E2B/Daytona comparison |
| Public multi-tenant arbitrary code | VM-backed or independently validated managed sandbox |

The orchestration graph should choose a provider through policy, not allow the model to select arbitrary infrastructure.

## 7. Artifact lifecycle

```text
requested
  -> planned
  -> generating
  -> executing
  -> validating
  -> ready_for_review
  -> revision_requested -> generating
  -> approved
  -> publishing
  -> published
  -> superseded | revoked

Any active state may end as failed, cancelled, expired, or blocked.
```

### Idempotency

Stable identities should prevent duplicate work and publication. A candidate key may include:

```text
artifact request ID
+ analytical result version
+ artifact recipe version
+ design-system version
+ generator configuration
+ source bundle hash
```

A publication key should identify the approved candidate and target destination. Retrying publication must not create duplicate dashboard versions or notifications.

### Recovery

If a sandbox or process disappears:

1. Read the durable execution record.
2. Determine whether outputs were already accepted.
3. Recreate from the exact template and source bundle.
4. Restart from the last valid application checkpoint.
5. Preserve prior attempt logs.
6. Never treat process disappearance as successful completion.

## 8. Security and authority boundaries

### Generated code must not receive

- Production database credentials.
- Raw cloud-provider credentials.
- Notification or deployment credentials.
- Docker socket or host control-plane access.
- Broad writable host mounts.
- Unrestricted network access by default.

### Preferred data-access pattern

```text
Production analytical store
       |
       v
Authorized result service
       |
       v
Minimized, versioned fixture or read-only result
       |
       v
Sandbox candidate
```

The candidate should normally render from a representative fixture. After approval, trusted production application code binds the artifact to authorized live data.

### Secret mediation

If generated code must call an external service, use a trusted proxy or outbound handler that:

- Verifies destination and operation.
- Injects credentials outside the sandbox.
- Applies per-job policy and rate limits.
- Records the request.
- Returns only authorized results.

### Network policy

Default posture:

- Deny outbound internet during ordinary build and runtime checks.
- Permit package registries only in controlled dependency-build jobs.
- Prefer dependencies preinstalled in versioned images.
- Allow preview ingress only through an authenticated or short-lived route.
- Block access to private networks and cloud metadata endpoints.

## 9. Starter project and design-system strategy

The agent should work from a versioned starter rather than an empty environment.

Candidate stack, subject to an explicit implementation decision:

- React and TypeScript.
- Vite or another selected application build tool.
- Owned design-system components, potentially based on shadcn/ui primitives.
- Recharts or another approved visualization library.
- Zod or generated types for artifact contracts.
- Playwright for rendered validation and exports.
- Unit, accessibility, and static-analysis tooling.

Dependency rules:

- Lock dependencies and base images.
- Install dependencies during image or template construction, not ad hoc during every generation.
- Allow only approved packages in normal artifact jobs.
- Treat any new package as a reviewed supply-chain change.
- Record exact package and image manifests with every candidate.

The design system should define analytical semantics as well as visual styling:

- Actuals versus forecasts.
- Unknown and stale data.
- Sample size and coverage.
- Severity and attention states.
- Evidence and methodology drill-downs.
- Accessible use of color and status.
- Print and responsive behavior.

## 10. Observability and cost controls

Record per execution:

- Queue time, startup time, build time, and validation time.
- CPU, memory, storage, and GPU allocation where available.
- Network destinations and transferred bytes.
- Model and generation cost.
- Exit status and termination reason.
- Preview lifetime.
- Outputs and their hashes.
- Cleanup confirmation.

Controls:

- Per-job and per-tenant concurrency.
- Maximum retries by error class.
- Build and preview time-to-live.
- Maximum output and log size.
- Daily and monthly provider budgets.
- Automatic expiry of previews and generated workspaces.

## 11. Architecture roadmap

### Phase 0 — Confirm contracts

Outcomes:

- Approve execution-plane boundaries.
- Define artifact request, candidate, validation, and release records.
- Define provider-neutral sandbox contract.
- Define external-action authority.
- Select the first three stakeholder artifact recipes.

No runtime is installed in this phase.

### Phase 1 — Deterministic local rendering

Outcomes:

- Render approved components from fixed Olist fixtures.
- Produce screenshots and one downloadable artifact.
- Record complete provenance and validation evidence.
- Prove that normal data refresh does not require generated code.

Exit gate: repeatable rendering from the same source and inputs.

### Phase 2 — Local generated-code sandbox

Outcomes:

- Allow the agent to modify a restricted starter-project surface.
- Run candidate code in a disposable local sandbox.
- Enforce resource, filesystem, dependency, and network controls.
- Present source diff, live preview, screenshots, and test evidence.
- Destroy and reconcile every sandbox.

Exit gate: generated code cannot access host secrets or production data, and approval is required before publication.

### Phase 3 — Background artifact workflow

Outcomes:

- Connect scheduled, event-driven, and attention-episode triggers.
- Generate and update artifact candidates without an open browser.
- Deduplicate retries and preserve previous valid publications.
- Support revision and approval through the review interface.

Exit gate: crash and replay tests demonstrate no duplicate publication or notification.

### Phase 4 — Cloud provider evaluation

Compare Cloudflare Sandbox, Modal, and one workspace-oriented provider using the same contract.

Measure:

- Startup and readiness time.
- Build and rendering duration.
- Interactive preview experience.
- Recovery after process or container loss.
- Network and secret controls.
- Data residency.
- Cost per candidate and preview hour.
- SDK stability and operational burden.

Exit gate: documented selection by workload, not one universal winner.

### Phase 5 — Olist stakeholder demonstration

Demonstrate:

- Scheduled executive snapshot.
- Live operations dashboard.
- Event-generated seller or order review case.
- Agent-generated candidate visualization reviewed in a sandbox.
- Evidence trace from artifact to analytical result and source.

Exit gate: stakeholders can distinguish facts, predictions, and hypotheses and can trace displayed claims to evidence.

### Phase 6 — Amazon scale test

Validate:

- Partition-level scheduling and backpressure.
- Concurrent artifact and analytical workloads.
- Cost controls and provider quotas.
- Artifact refresh without rebuilding unaffected views.
- Retention and cleanup at scale.

## 12. Open architecture decisions

| ID | Decision | Current position |
|---|---|---|
| EXE-01 | First local sandbox runtime | Hardened Docker/Podman is the leading prototype option; not approved. |
| EXE-02 | Cloud preview provider | Compare Cloudflare Sandbox with workspace-oriented alternatives. |
| EXE-03 | Elastic build/model provider | Evaluate Modal separately from interactive preview needs. |
| EXE-04 | Artifact frontend stack | React-based starter is proposed; not approved. |
| EXE-05 | Generated-code authority | Restrict writes to a generated surface; protected system code remains immutable. |
| EXE-06 | Dependency authority | Agent may use approved dependencies; new dependencies require review. |
| EXE-07 | Preview access | Authenticated application proxy preferred over public bearer URLs. |
| EXE-08 | Promotion authority | Human approval for executable artifacts during MVP. |
| EXE-09 | Data supplied to sandboxes | Minimized fixtures by default; no direct production database access. |
| EXE-10 | Strong isolation threshold | Define when local containers must be replaced by gVisor, Kata, microVMs, or managed isolation. |

## 13. Immediate next design decision

Before selecting a sandbox product, define the first artifact-generation authority level:

1. **Template assembly only:** agent chooses approved components.
2. **Restricted code modification:** agent may edit a bounded generated directory in a starter project.
3. **Open project generation:** agent may alter dependencies and application structure.

The current recommendation for the Olist MVP is **restricted code modification**, with dependency changes and publication requiring review.

## 14. Sources

- [Cloudflare Sandbox SDK 1.0 preview](https://developers.cloudflare.com/sandbox/1-0-preview/)
- [Cloudflare Sandbox lifecycle](https://developers.cloudflare.com/sandbox/1-0-preview/lifecycle/)
- [Cloudflare Sandbox process execution](https://developers.cloudflare.com/sandbox/1-0-preview/processes/)
- [Cloudflare Sandbox service exposure](https://developers.cloudflare.com/sandbox/guides/expose-services/)
- [Cloudflare Sandbox outbound traffic](https://developers.cloudflare.com/sandbox/guides/outbound-traffic/)
- [Modal Sandboxes](https://modal.com/docs/guide/sandbox)
- [E2B documentation](https://e2b.dev/docs)
- [Daytona documentation](https://www.daytona.io/docs/)

Provider behavior must be reconfirmed against current documentation and installed package types before implementation. Cloudflare stable and `@next` APIs must not be mixed.
