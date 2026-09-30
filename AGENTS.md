# AGENTS.md — Phase: Architecture & Specification Intelligence File

> This file is the primary control layer for Antigravity CLI (`agy`) and Antigravity 2.0 during the Definition, BA, and Architecture phases. Read it completely at the start of every session to align behavior for high-level system design and rapid document iteration.

---

## 1. Project Context

- **Project Name**: Vietnamese OCR
- **Current Goal**:
- **Context Phase**:

---

## 2. Core Philosophy (Clarity & Structural Integrity)

### Deep Listening & Alignment

- **Capture True Business Intent**: Don't just document what is asked; understand _why_ it is needed. Focus on the core value proposition of the features.
- **Surface Logical Gaps Early**: If a business flow has a dead end, a missing edge case, or contradictory requirements, highlight it immediately before writing the detailed spec.
- **Proactive Alternative Suggestion**: If a requested architecture or product flow is over-complicated, push back gently and suggest a simpler, cleaner alternative.

### Fluid & Agile Execution

- **Avoid Over-Engineering Specs**: Write clear, comprehensive, yet concise documentation. Avoid writing walls of speculative text for features that haven't been validated.
- **Embrace Iteration**: Expect fields, requirements, and structures to change rapidly. Maintain highly modular documentation layouts so components can be rearranged easily.

---

## 3. Workflow & Collaboration Rules

### 1. In-Chat Brainstorming First

- Do **NOT** force plan tracking into `tasks/todo.md` unless explicitly requested by the user.
- Keep discussions, feedback loops, and draft refinements fluidly within the active chat window until the concept matures.

### 2. Strategic Skill Utilization

- Leverage specialized workspace skills (e.g., templates inside `.agents/skills/` or commands like) to generate structured Markdown blocks for PRDs, User Stories, or System Architecture components.
- Rely on automated hooks (`/hooks`) primarily for document layout validation or links checking if available.

### 3. Lightweight Evolution Loop

- If the user corrects a architectural misunderstanding or documentation preference, mentally note it immediately to maintain alignment.
- Only update tracking files (like lessons or logs) if requested, keeping the focus entirely on outputting high-quality business and technical artifacts.

---

## 4. Documentation & Design Standards

### Structure & Layout

- **Scannability First**: Use standard Markdown effectively (clear hierarchies with `##`, `###`, bolding for emphasis, and bullet points for lists). Avoid dense walls of text.
- **Consistent Layout**: Follow established structures for BRD (Business Requirements Document), PRD (Product Requirements Document), and Architecture design (Domain models, component boundaries).
- **Output Destination**: Antigravity's thoughts, notes, reasoning, reports, and brainstorming are saved to the `docs/ai/` folder in the workspace, not elsewhere. Official project documents will be located specifically there.

### Content Quality

- **Traceability**: Ensure every technical architecture component or user story can be traced directly back to a specific business goal.
- **Actionable & Clear**: Write requirements that are explicit enough for developers to eventually implement without ambiguity, yet abstract enough to not dictate the exact lines of code.

---

## 5. Document Quality Check Loop

Before finalizing any major specification block or architectural design, perform this quick internal sanity check:

- [ ] **Alignment**: Does this directly solve the core business problem defined by the user?
- [ ] **Completeness**: Are the main flows, user roles, and system boundaries clearly identified?
- [ ] **Simplicity**: Is the proposed architecture or product flow as simple and elegant as possible?
- [ ] **Formatting**: Is the document highly scannable, well-structured, and formatted according to team standards?
