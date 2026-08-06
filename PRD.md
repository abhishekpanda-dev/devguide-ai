# Product Requirements Document

## Product

**Name:** DevGuide AI  
**Tagline:** Understand, improve, and ship unfamiliar codebases with confidence.

## Problem

Developers joining or reviewing unfamiliar repositories spend significant time locating important modules, reconstructing architecture, assessing health, and validating answers against source code.

## Product goal

Given a public GitHub repository, DevGuide AI should produce a repository overview, architecture summary, health report, important-module explanations, and evidence-backed chat responses.

## Intended users

- Developers onboarding to an unfamiliar codebase
- Maintainers assessing repository health
- Reviewers preparing to contribute or audit changes

## Initial scope

- Accept a public GitHub repository reference
- Analyze repository structure and selected source content
- Present repository, architecture, and health summaries
- Explain important modules with source evidence
- Answer repository questions with citations to analyzed content

## Out of scope for bootstrap

No ingestion, analysis, chat, authentication, UI, API, or worker functionality is implemented in this repository state.

## Success criteria

TODO: Define measurable accuracy, latency, reliability, and usability targets before implementation.

## Open decisions

TODO: Confirm technology stack, model/provider policy, storage and retention, GitHub access strategy, deployment target, privacy controls, and evaluation methodology.
