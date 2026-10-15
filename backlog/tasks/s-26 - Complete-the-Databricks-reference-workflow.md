---
id: S-26
title: Complete the Databricks reference workflow
status: To Do
assignee: []
created_date: '2026-10-14 22:59'
updated_date: '2026-10-15 00:21'
labels:
  - needs-refinement
  - platform
milestone: m-2
dependencies:
  - S-19
  - S-22
documentation:
  - docs/ROADMAP.md
  - docs/roadmap/README.md
  - docs/roadmap/agile-backlog.md#shared-delivery-contract
priority: high
type: task
ordinal: 15
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Original roadmap story: S26. Original priority: P0. Work type: implementation.

## Business outcome

As a business owner, I need to connect Databricks and receive an answer to my business question, so I do not commission a separate pipeline for every analysis.

## Scope

Integrate discovery, collection, unfamiliar-data preparation, checks, analysis, and saved execution for the S-12 scenario. Reuse the existing runtime where its contracts fit. Keep source access, data movement, and any source-side execution within the agreed scope.

## Owned surface

One Databricks integration and the end-to-end reference workflow. Live access is a prerequisite of this story, not of all independent planning or local development.

## Prerequisites

S-19, S-22; requires the selected permitted Databricks environment.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 On an actually permitted Databricks source, the owner supplies the objective and connection; the agent identifies the relevant data, builds the pipeline, processes the complete selected workload, and returns a checkable answer and rerunnable workflow. Demonstrate interruption recovery and insufficient-access handling. A fixture supports development but cannot close this live-source acceptance. No manual importer, transformation script, or repeated user-created batches are required.
<!-- AC:END -->
