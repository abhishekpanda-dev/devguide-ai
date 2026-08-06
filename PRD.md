# DevGuide AI Product Requirements Document

**Status:** Draft for product validation

**Project stage:** Repository bootstrap; no product functionality is implemented

**Tagline:** Understand, improve, and ship unfamiliar codebases with confidence.

## 1. Executive Summary

DevGuide AI is a planned AI-powered Repository Intelligence Platform for developers working with unfamiliar codebases. A user provides a supported public GitHub repository, and the product analyzes eligible repository content to produce a navigable overview, a grounded architecture explanation, a repository health report, important-module explanations, and repository question answering with citations.

The product is intended to shorten the time required to orient within a codebase while making uncertainty and source evidence visible. It will not claim complete understanding, replace expert review, or guarantee that maintainability or security findings are exhaustive or correct.

## 2. Problem Statement

Developers commonly spend hours locating entry points, identifying frameworks, tracing module relationships, assessing quality, and validating documentation when joining or reviewing a repository. Existing documentation may be incomplete or stale, while general-purpose AI responses can be difficult to trust when they lack repository-specific evidence.

DevGuide AI should reduce this discovery burden by organizing repository facts, explaining likely relationships, and linking material claims to source evidence. Users must remain able to distinguish observed facts, inferred conclusions, and unavailable information.

## 3. Product Vision

Enable developers to understand, improve, and ship unfamiliar codebases with greater confidence through evidence-backed repository intelligence.

The planned platform should help users:

- Understand project structure and important modules.
- Detect supported frameworks and languages from repository evidence.
- Parse supported source files and build a searchable repository knowledge base.
- Generate a qualified architecture explanation.
- Surface potential maintainability concerns and security risks for review.
- Produce a repository health report.
- Draft documentation and test suggestions.
- Answer repository questions with file-level or line-level citations when evidence is available.

## 4. Business Goals

- Demonstrate a credible end-to-end repository analysis workflow during the hackathon.
- Reduce time-to-first-useful-insight for a supported public repository.
- Establish user trust through citations, confidence language, and transparent limitations.
- Create a foundation that can support individual developers first and team workflows later.
- Collect sufficient product signals to determine which analysis outputs provide the most value.

TODO: Confirm commercial model, target adoption metrics, and post-hackathon ownership.

## 5. Non-Goals

- Guaranteeing complete understanding of every repository, language, framework, or build system.
- Guaranteeing discovery of all defects, maintainability problems, or security vulnerabilities.
- Replacing security audits, code review, testing, or professional engineering judgment.
- Modifying, committing, deploying, or executing repository code in the MVP.
- Supporting private repositories in the MVP.
- Providing a general-purpose coding assistant or autonomous software-development agent.
- Serving as an authoritative software bill of materials, compliance certification, or legal assessment.
- Real-time collaboration, organization administration, and billing in the MVP.

## 6. User Personas

### 6.1 Onboarding developer

Needs a rapid, evidence-backed map of an unfamiliar repository before making a first contribution.

### 6.2 Maintainer

Needs a concise view of repository structure, documentation gaps, quality signals, and areas that may warrant attention.

### 6.3 Reviewer or technical lead

Needs to identify important modules, likely architectural boundaries, and risks before planning or reviewing work.

### 6.4 Hackathon evaluator

Needs a short, reproducible demonstration that clearly distinguishes implemented behavior from planned behavior.

## 7. User Journey

1. The user opens DevGuide AI and sees supported repository constraints and data-use notices.
2. The user submits the URL of a supported public GitHub repository.
3. The product validates repository accessibility, size, and supported content.
4. The user sees analysis status, including actionable failure or timeout messages.
5. On completion, the user receives an overview of structure, detected technologies, important modules, and available evidence.
6. The user reviews the architecture explanation and repository health findings, including qualifications and citations.
7. The user asks a repository-specific question.
8. The product answers from indexed evidence, cites sources, and states when evidence is insufficient.
9. The user can start a new analysis or leave without assuming that submitted content is retained indefinitely.

## 8. MVP Scope

- Submit one supported public GitHub repository by URL.
- Validate accessibility and configured repository limits before analysis.
- Inventory supported files and summarize repository structure.
- Detect supported languages and frameworks using repository evidence.
- Identify likely entry points and important modules with rationale.
- Produce a qualified repository overview and architecture summary.
- Produce a basic health report using explicitly defined signals.
- Ask repository questions and receive evidence-backed answers.
- Show analysis progress, completion, partial-result, timeout, and failure states.
- Provide citations that identify the source file and location when available.
- Expose clear limitations and avoid presenting uncertain inferences as facts.

TODO: Confirm the exact language, framework, repository-size, and file-count support matrix.

## 9. Strong Enhancements

These capabilities are high-value additions after the MVP path is stable:

- Potential security-risk detection with severity, evidence, confidence, and non-exhaustive disclaimers.
- Maintainability analysis for complexity, duplication, coupling, stale dependencies, and documentation gaps where measurable.
- Suggested tests linked to relevant modules and observed coverage gaps.
- Draft documentation for selected modules, onboarding, or architecture.
- Repository comparison between branches, tags, or analysis snapshots.
- Exportable reports in commonly used document formats.
- User feedback controls for incorrect, unsupported, or useful findings.

## 10. Nice to Have

- Shareable read-only analysis links with explicit access and expiry controls.
- Search and filters across files, modules, findings, and citations.
- Saved questions and reusable analysis views.
- Visual dependency or module maps.
- Theme and accessibility preferences beyond baseline compliance.
- Guided prompts for common onboarding and review tasks.

## 11. Future Roadmap

### Phase 1: Hackathon MVP

Deliver a bounded, evidence-backed analysis flow for selected public repositories and a reproducible demo.

### Phase 2: Reliability and coverage

Expand the supported-language matrix, introduce evaluation datasets, improve partial-analysis behavior, and calibrate confidence and citations.

### Phase 3: Developer workflows

Add report export, change comparison, feedback loops, documentation drafts, and test suggestions.

### Phase 4: Team and private-repository support

Evaluate authenticated private-repository access, team workspaces, integrations, administration, retention controls, and auditability after security and privacy review.

## 12. Functional Requirements

- **FR-001 — Repository submission:** The product shall accept a syntactically valid URL for a supported public GitHub repository.
- **FR-002 — Input validation:** The product shall reject unsupported hosts, malformed URLs, inaccessible repositories, and repositories exceeding configured limits with a specific user-facing reason.
- **FR-003 — Repository inventory:** The product shall inventory supported files and directories while identifying skipped, unsupported, binary, generated, or oversized content.
- **FR-004 — Technology detection:** The product shall report detected supported languages, frameworks, and package ecosystems with supporting file evidence.
- **FR-005 — Source processing:** The product shall extract analysis-ready content from supported text and source files without claiming coverage of skipped content.
- **FR-006 — Knowledge indexing:** The product shall create a repository-specific knowledge index from eligible content and associate indexed units with source locations.
- **FR-007 — Repository overview:** The product shall generate an overview containing repository purpose when evidenced, structure, detected technologies, likely entry points, and important modules.
- **FR-008 — Architecture explanation:** The product shall generate a qualified explanation of likely components, boundaries, and relationships, citing evidence and labeling material inferences.
- **FR-009 — Important-module explanation:** The product shall identify and explain important modules using transparent selection rationale and source citations.
- **FR-010 — Health report:** The product shall present defined repository health signals, findings, evidence, limitations, and recommended review actions without representing the report as exhaustive.
- **FR-011 — Maintainability findings:** Where supported by configured checks, the product shall surface potential maintainability concerns with evidence and non-deterministic findings labeled as suggestions for review.
- **FR-012 — Security findings:** Where supported by configured checks, the product shall surface potential security risks with evidence, severity rationale, confidence, and a statement that results are not a security audit.
- **FR-013 — Repository chat:** The product shall accept questions about the analyzed repository and answer using available indexed evidence.
- **FR-014 — Citations:** The product shall attach source citations to material repository claims and identify file paths plus line ranges or equivalent locations when available.
- **FR-015 — Insufficient evidence:** The product shall state when indexed evidence is insufficient instead of inventing a repository-specific answer.
- **FR-016 — Analysis status:** The product shall show queued, processing, completed, partially completed, timed out, and failed states as applicable.
- **FR-017 — Partial results:** The product shall distinguish completed, skipped, and failed analysis stages whenever partial results are displayed.
- **FR-018 — Documentation drafting:** After MVP, the product should allow users to request draft documentation grounded in selected repository evidence and clearly label it as generated content requiring review.
- **FR-019 — Test suggestions:** After MVP, the product should suggest tests tied to specific observed modules or behaviors and label suggestions as unverified until implemented and run.
- **FR-020 — Limit disclosure:** The product shall display applicable repository coverage, analysis limitations, and relevant AI uncertainty with each completed or partial analysis.

## 13. Non-Functional Requirements

- **NFR-001 — Availability:** The MVP demo environment shall successfully serve at least 95% of valid page requests during the scheduled demonstration window, excluding third-party outages.
- **NFR-002 — Accessibility:** The primary submit, status, results, and chat journeys shall be keyboard operable and have no critical automated accessibility violations under the selected audit tool.
- **NFR-003 — Compatibility:** The primary MVP journey shall pass acceptance testing on the latest stable desktop versions of Chrome and Firefox available at test time.
- **NFR-004 — Observability:** Every analysis shall have a correlation identifier and structured stage outcomes sufficient to diagnose validation, ingestion, indexing, and generation failures without logging repository contents by default.
- **NFR-005 — Resilience:** Failure of one non-critical analysis stage shall not erase completed stage results; the product shall report a partial outcome when safe and useful.
- **NFR-006 — Maintainability:** Product code introduced after bootstrap shall pass the repository's configured formatting, static checks, and automated tests in CI before merge.
- **NFR-007 — Scalability boundary:** Repository size, file count, concurrent analyses, and processing-time limits shall be configurable and visible in operational documentation.
- **NFR-008 — Portability:** The documented MVP setup shall be reproducible from a clean checkout using the supported environment and without undocumented local secrets.
- **NFR-009 — Data integrity:** Citations shall resolve to the same repository revision used for analysis, or the product shall mark them unavailable.
- **NFR-010 — Explainability:** Generated reports shall visually distinguish observed evidence, heuristic findings, and AI-generated inferences.

## 14. User Stories

- As an onboarding developer, I want a repository map so that I can find likely entry points and important modules quickly.
- As an onboarding developer, I want claims linked to source files so that I can validate explanations before relying on them.
- As a maintainer, I want a qualified health report so that I can prioritize areas for investigation.
- As a reviewer, I want likely component relationships explained so that I can begin review with an explicit architectural hypothesis.
- As a developer, I want to ask repository-specific questions so that I can explore beyond a static report.
- As a developer, I want the product to admit insufficient evidence so that uncertainty is not hidden.
- As a security-conscious user, I want potential risks presented as non-exhaustive findings so that I do not mistake them for an audit.
- As a user, I want clear failure and partial-result messages so that I know what was and was not analyzed.
- As a hackathon evaluator, I want a repeatable demo so that I can assess the product against stated criteria.

## 15. Acceptance Criteria

The MVP is acceptable when all of the following are demonstrated in a controlled test environment:

1. A valid, accessible repository within configured limits can be submitted and reaches a terminal state within the configured analysis timeout.
2. Each invalid test case—malformed URL, unsupported host, inaccessible repository, and configured-limit violation—produces a distinct actionable message and does not start analysis.
3. For each test repository, the output lists the analyzed revision and identifies all files skipped because of configured size, type, or support rules.
4. Detected technologies include at least one supporting repository citation each; unsupported or unconfirmed technologies are not presented as confirmed.
5. The overview includes repository structure, detected technologies, likely entry points, and important modules, or explicitly states that evidence for an item was not found.
6. Every material architecture or module claim in the demo report includes at least one resolvable citation or is visibly labeled as an inference without sufficient direct evidence.
7. At least 95% of sampled citations across the agreed evaluation set resolve to the analyzed revision, file, and cited line range or equivalent location.
8. Every health, maintainability, or security finding displayed in the demo includes evidence, a review recommendation, and a non-exhaustive-results disclaimer.
9. For a test question whose answer is absent from indexed content, repository chat responds with insufficient-evidence language and contains no fabricated repository citation.
10. For each of five predefined answerable questions across the demo repositories, the answer includes at least one resolvable citation and is rated factually supported by a human reviewer.
11. A forced non-critical stage failure produces a partial-result state that names the failed stage and preserves completed results.
12. A forced timeout reaches a timed-out state within 10 seconds after the configured deadline and presents a retry or recovery action.
13. The primary submission-to-chat journey passes the committed Playwright suite in the supported demo browser.
14. The default branch GitHub Actions pipeline completes successfully for the demo commit.
15. A new evaluator can complete the documented demo flow in 10 minutes or less using the prepared repository and instructions.

TODO: Confirm the configured analysis timeout and evaluation repository set before implementation.

## 16. Error Cases

- Malformed, non-GitHub, or unsupported repository URL.
- Repository does not exist, is private, is archived under an unsupported policy, or cannot be accessed.
- GitHub rate limit, transient outage, or download failure.
- Repository exceeds configured size, file-count, depth, or processing limits.
- Repository contains no supported analyzable files.
- Repository revision changes during acquisition or a cited revision becomes unavailable.
- Binary, generated, malformed, encrypted, vendored, or unsupported files are encountered.
- Source parsing succeeds only partially or encounters invalid syntax.
- Index construction fails, times out, or produces partial coverage.
- AI generation times out, is unavailable, violates an output constraint, or lacks sufficient evidence.
- A requested answer depends on skipped or unsupported content.
- Citations cannot be resolved to the analyzed revision.
- Potential prompt-injection instructions appear in repository content.
- Duplicate submissions or user retries occur while analysis is already in progress.
- Results expire or are removed under the configured retention policy.

Each error shall map to a safe terminal or retryable state, a user-facing explanation, and an internal diagnostic category without exposing secrets or sensitive operational details.

## 17. Security Requirements

- Treat all repository content, filenames, metadata, and embedded instructions as untrusted input.
- Prevent repository content from overriding system instructions, tool permissions, or evidence requirements.
- Do not execute submitted repository code during MVP analysis.
- Restrict repository retrieval to approved hosts, protocols, resource limits, and network destinations.
- Defend against path traversal, archive expansion, malicious links, oversized files, and resource-exhaustion attempts.
- Keep credentials server-side, least-privileged, rotated, and absent from source control, client output, logs, and generated reports.
- Sanitize rendered repository content to prevent script or markup injection.
- Apply dependency, secret, and static security checks to the product's own code in CI when implementation begins.
- Log security-relevant events without storing full repository contents by default.
- Present security findings as potential risks requiring validation, never as guaranteed vulnerability coverage.

TODO: Define the threat model, abuse controls, security contact, severity framework, and incident-response owner.

## 18. Privacy Requirements

- MVP input shall be limited to public repositories unless a later privacy and security decision authorizes private repositories.
- Before submission, users shall be informed what repository data is collected, why it is processed, and how long results are retained.
- Collect only content and metadata necessary for the stated analysis.
- Do not request or intentionally retain repository secrets; if suspected secrets are detected, redact them from user-visible AI prompts, logs, analytics, and reports where feasible.
- Repository content and prompts shall not be used for unrelated training or secondary purposes without an explicit policy and user notice.
- Access to stored analysis artifacts shall follow the approved authorization and expiry model.
- The product shall support deletion or expiry according to the approved retention policy.
- Analytics shall avoid source content, user questions, repository URLs, and file paths unless explicitly approved and appropriately minimized.

TODO: Confirm retention duration, deletion workflow, data regions, subprocessors, legal basis, and model-provider data handling.

## 19. AI Reliability Requirements

- Repository-specific factual claims shall be grounded in indexed content and cited when evidence is available.
- The product shall distinguish direct observations from heuristic or model-generated inferences.
- When evidence is missing, conflicting, skipped, or outside supported coverage, the product shall communicate uncertainty or decline to answer.
- Generated output shall not imply complete repository comprehension or exhaustive issue detection.
- Citations shall be validated against the analyzed revision before display when technically feasible.
- Prompt-injection resistance shall be evaluated using adversarial repository fixtures.
- A versioned evaluation set shall measure citation validity, factual support, refusal behavior, and false-positive rates before release claims are made.
- Material model, prompt, retrieval, or parsing changes shall rerun the agreed evaluation suite.
- Users shall be reminded that generated explanations, findings, documentation, and tests require human review.

TODO: Set minimum evaluation thresholds beyond MVP acceptance criteria and define the human-review rubric.

## 20. Analytics

Subject to privacy approval, the product should measure:

- Repository submissions started, rejected, completed, partially completed, timed out, and failed.
- Time from submission to first status and terminal result.
- Analysis-stage success and failure rates.
- Report sections viewed and citations opened.
- Repository questions submitted, answered with evidence, or declined for insufficient evidence.
- User feedback on useful, incorrect, or unsupported outputs.
- Repeat analyses and return usage using privacy-preserving identifiers.
- Demo completion rate and time to complete the scripted flow.

Analytics must not record source code, generated secrets, or full user questions by default. TODO: Define event schemas, consent requirements, retention, and success targets.

## 21. Performance Requirements

- Input validation shall return a success or actionable rejection within 2 seconds at the 95th percentile, excluding third-party availability checks that exceed the configured upstream timeout.
- The status view shall reflect a recorded analysis-state change within 5 seconds at the 95th percentile under the agreed MVP load profile.
- For repositories in the agreed demo set, analysis shall reach a terminal state within the configured timeout in at least 9 of 10 consecutive controlled runs.
- For an indexed demo repository, repository chat shall begin presenting a response or a clear processing state within 3 seconds at the 95th percentile and reach a terminal response within 20 seconds at the 95th percentile under the agreed MVP load profile.
- The primary results view shall become interactive within 3 seconds at the 75th percentile on the agreed test device and network profile after result data is available.
- Timeouts and size limits shall be configurable, documented, and enforced rather than allowing unbounded processing.

TODO: Confirm the load profile, test environment, repository classes, timeout values, and whether streaming responses are in scope.

## 22. Demo Success Criteria

- A fresh public demo repository is submitted successfully without manual database or state manipulation.
- The analysis reaches a completed or explicitly qualified partial state within the configured demo timeout.
- The evaluator can identify detected technologies, important modules, a repository overview, an architecture explanation, and a health report.
- At least three material report claims have citations opened and verified against the analyzed revision during the demo.
- One answerable repository question returns a supported answer with a resolvable citation.
- One intentionally unanswerable question produces an insufficient-evidence response without a fabricated citation.
- Limitations and non-exhaustive security language are visible during the demo.
- The scripted demo completes in 10 minutes or less.
- The default branch pipeline is green and the documented Playwright demo tests pass before presentation.

## 23. Hackathon Compliance

The repository is expected to contain the following by final submission:

| Requirement | Current PRD assessment |
| --- | --- |
| `architecture.md` | Present as a proposed placeholder; implementation decisions remain TODO |
| `AGENTS.md` | Present |
| `AGENTS_AND_SKILLS.md` | Present as a placeholder |
| Working application code | Not implemented |
| At least one custom agent | Not implemented |
| At least one custom skill | Not implemented |
| Green GitHub Actions pipeline | Bootstrap workflow exists; remote green status not asserted here |
| `PRD.md` | Present; this document |
| `API_DOCUMENTATION.md` | Present as a placeholder; no API is implemented |
| Playwright tests | Not implemented |
| Professional documentation | Foundational documentation exists; completion and review remain required |

Compliance shall be reassessed against the final commit and demonstrated behavior. File presence alone does not establish that a requirement is complete.

## 24. Risks

| Risk | Impact | Planned mitigation |
| --- | --- | --- |
| Hallucinated or weakly supported explanations | Users may act on incorrect guidance | Require citations, label inference, test refusal behavior, and retain human review |
| Invalid or misleading citations | Loss of trust and unverifiable claims | Bind results to a revision and validate citation targets |
| False positives or negatives in health/security findings | Misplaced effort or missed risk | Use qualified language, disclose coverage, measure error rates, and avoid audit claims |
| Prompt injection in repository content | Manipulated output or unsafe tool behavior | Treat content as data, isolate instructions, restrict tools, and test adversarial fixtures |
| Large or unusual repositories | Timeouts, cost growth, or partial coverage | Enforce configurable limits, exclusions, partial results, and clear coverage reporting |
| Unsupported languages or generated code | Incomplete or distorted analysis | Publish support matrix and expose skipped-content details |
| Third-party GitHub or AI-service failure | Unavailable or delayed analysis | Use bounded retries, timeouts, diagnostic states, and provider boundaries |
| Source-code privacy or secret exposure | Harm to repository owners and users | Limit MVP to public repositories, minimize retention, redact sensitive output, and avoid content analytics |
| Hackathon over-scoping | Incomplete core journey | Prioritize cited overview, architecture, health, and chat flow before enhancements |
| Unclear quality thresholds | Demo success without product reliability | Approve evaluation set, metrics, and release gates before implementation claims |

## 25. Future Improvements

- Expand language and framework support based on measured demand and evaluation coverage.
- Support authenticated private repositories after completing security, privacy, and access-control work.
- Add incremental re-analysis and revision comparisons.
- Improve deterministic code-graph and dependency analysis before relying on model inference.
- Add team workspaces, permissions, audit events, and controlled sharing.
- Integrate with developer workflows only after approval of write permissions and rollback behavior.
- Offer configurable organizational policies for retention, model use, and risk reporting.
- Build benchmark datasets and continuous evaluation for factual support, citations, refusals, and risk findings.
- Add user-confirmed corrections that improve subsequent results without silently rewriting evidence.

## Missing Product Decisions

- Exact MVP language, framework, file-type, and repository-size support matrix.
- Repository submission semantics: URL-only cloning versus any upload capability.
- GitHub authentication, rate-limit handling, revision selection, and archived/fork behavior.
- Health-score definition, included signals, weighting, and whether a composite score should exist.
- Security and maintainability analysis methods, severity system, and acceptable false-positive rates.
- AI model/provider policy, grounding strategy, fallback behavior, evaluation thresholds, and cost limits.
- Analysis timeout, concurrency limit, retry policy, and partial-result rules.
- Storage, indexing, retention, deletion, and result-sharing policies.
- User identity, authentication, authorization, and anonymous-use policy.
- Supported deployment environment, browser matrix, load profile, and operational ownership.
- Analytics consent, event schema, retention, and target business metrics.
- Accessibility target and formal compliance level.
- Final hackathon demo repositories and human-review rubric.
