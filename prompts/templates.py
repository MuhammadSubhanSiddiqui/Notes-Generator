"""
The prompt-loop: each topic goes through 3 chained content calls + 1
portfolio-relevance call + 1 merge/polish pass.
Chaining (instead of one giant prompt) keeps each call focused, so the model
doesn't skimp on ASCII diagrams to save room for interview questions, etc.
"""

STAGE_1A_FUNDAMENTALS = """You are writing a comprehensive textbook chapter on the fundamentals of: {topic}

Search Context:
{search_context}

Write an exhaustive, production-grade guide covering:
1. Historical Background & Core Motivation (Why was this built? What problems does it solve?)
2. Core Conceptual Model & Mental Model (In-depth breakdown of concepts with real-world analogies)
3. Architecture & Primitives (Detailed explanation of primitives, syntax, and base mechanics)
4. Hello World to Production Starter Code (Fully annotated, complete code blocks — not snippets)

Rules:
- Write in full technical depth with complete explanations.
- Aim for exhaustive detail (1,500+ words).
- Output ONLY Markdown."""

STAGE_1B_DEEP_DIVE = """You are writing an advanced internals and production guide for: {topic}

Explain in exhaustive technical detail:
1. Under-the-hood Internals (Memory management, execution cycles, engine/runtime mechanics)
2. Advanced Patterns & Real-world Architecture (Enterprise patterns with complete code implementations)
3. Concurrency, Scaling, and Bottlenecks (Throughput, caching, distributed patterns)
4. Comprehensive Configuration & API Reference (Production settings, flags, options with explanations)

Rules:
- Do not summarize; provide comprehensive explanations and functional code implementations.
- Aim for 2,000+ words. Output ONLY Markdown."""

STAGE_1C_SECURITY_PERFORMANCE = """You are writing an enterprise performance and security guide for: {topic}

Provide in-depth sections on:
1. Performance Optimization & Benchmarking (Profiling, memory leaks, metrics)
2. Hardening & Security Best Practices (Vulnerabilities, authentication, sanitization, secrets)
3. Comprehensive Testing Strategies (Unit, Integration, E2E examples)
4. Migration & Version Upgrade Traps

Rules:
- Include full code configurations and concrete tables.
- Aim for 1,500+ words. Output ONLY Markdown."""

STAGE_2_ASCII_ARCHITECTURE = """You are creating ASCII architecture diagrams for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create 4-5 ASCII diagrams that visualize the most important architectural
or conceptual flows for {topic} (e.g. data flow, component lifecycle,
request/response cycle, system architecture — whichever fit this topic).

Rules:
- Wrap every diagram in a markdown code block (```)
- Use box-drawing characters or simple +/-/| ASCII art — must render correctly
  in a monospace font
- Each diagram needs a one-line title (as a ### heading) and a 1-2 sentence
  caption explaining what it shows
- Keep diagrams under 25 lines each — clarity over completeness
- Output ONLY the diagrams section in markdown, starting with "## Architecture Diagrams"
- No preamble, no repeated theory text."""


STAGE_2_5_PORTFOLIO_RELEVANCE = """You are matching a study-notes topic against a developer's real portfolio projects and experience.

Topic: {topic}

Portfolio entries (projects and experience):
---
{portfolio_context}
---

Task: identify ONLY the portfolio projects that genuinely use or relate to
{topic}. Do NOT force-fit a project that isn't actually relevant just to
have something to show.

For each genuine match, write:
- Put project matches under `### Projects`.
- Put experience matches under `### Experience`.
- For each match, write:
  - **Project:** name, when the match is a project
  - **Experience:** role/company, when the match is an experience item
  - **How {topic} is used:** 1-2 sentences, specific to what that item actually does with it (not generic praise)

Output ONLY this section in markdown, starting with a
"## Where I've Used This" heading. If there are no genuine matches (or the
portfolio list is empty), output exactly:

## Where I've Used This
_No current portfolio project or experience uses {topic} yet._

No preamble, no repeated theory text."""


STAGE_3_INTERVIEW_QUESTIONS = """You are compiling the most commonly asked interview questions for: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create an interview questions section with 35-40 questions total, organized as:

## Interview Questions

### Beginner (10-12 questions)
### Intermediate (10-12 questions)
### Advanced (10-12 questions)
### Scenario (10-12 questions)

For each question:
- **Q:** the question
- **A:** a concise, correct answer (3-6 sentences — enough to actually answer
  it in an interview, not just a one-liner)

Pick the questions that are ACTUALLY most commonly asked for {topic} in real
technical interviews — not generic filler questions.

Output ONLY this section in markdown. No preamble."""


STAGE_2_7_PITFALLS = """You are writing a "Common Pitfalls & Debugging" section for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create 15-18 real mistakes, gotchas, failure modes, or debugging traps that
people commonly hit with {topic}.

For each item:
- State the pitfall clearly.
- Explain why it happens.
- Give a 2-3 sentence fix or debugging approach.

Output ONLY this section in markdown, starting with "## Common Pitfalls & Debugging".
No preamble."""


STAGE_2_8_CHEATSHEET = """You are writing a compact "Quick Reference Cheat Sheet" for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create a dense quick-reference section for rapid pre-exam scanning.

Requirements:
- Keep it compact, not prose-heavy.
- Use bullets, mini tables, or short grouped lists.
- Include syntax, commands, key terms, common patterns, key APIs, and any
  must-remember facts that help with recall.
- Prefer dense recall over explanation.

Output ONLY this section in markdown, starting with "## Quick Reference Cheat Sheet".
No preamble."""


STAGE_4_MERGE_POLISH = """You are finalizing a study notes document on: {topic}

You are given six sections generated separately. Merge them into ONE
clean, well-formatted markdown document. Fix any redundancy, inconsistent
terminology, or awkward transitions between sections, but do NOT shorten
or remove content — just polish the seams. This should read as a
comprehensive 15-20 page reference document — do not compress or drop
sections for brevity.

Add a single top-level title "# {topic} — Study Notes" and a short 2-3
line intro paragraph at the very top.

Place the "Where I've Used This" section right after the intro and before
the theory levels. Place the "Common Pitfalls & Debugging" section right
after Theory. Place the "Quick Reference Cheat Sheet" section near the end,
right before Interview Questions. If it says no project uses this topic
yet, keep that line as-is — do not invent a project to fill it.

--- THEORY SECTION ---
{stage1_output}

--- PITFALLS SECTION ---
{stage2_7_output}

--- WHERE I'VE USED THIS SECTION ---
{stage2_5_output}

--- ASCII DIAGRAMS SECTION ---
{stage2_output}

--- CHEAT SHEET SECTION ---
{stage2_8_output}

--- INTERVIEW QUESTIONS SECTION ---
{stage3_output}

Output ONLY the final merged markdown document, nothing else — no preamble,
no "Here's the final document" text."""


STAGE_5_REVISE_WITH_REFERENCES = """You are a senior editor polishing a study notes document on: {topic}.

Current draft:
---
{draft_output}
---

Reference notes from earlier generated files in this pipeline:
---
{reference_notes}
---

Task:
- Improve clarity, organization, and depth without reducing content quality.
- Preserve technical accuracy and any useful detail already present.
- Use the reference notes only as a quality/style benchmark.
- Do not copy unrelated topic-specific facts from the references.
- Do not shorten the document unless removing repetition makes it strictly better.
- Keep the same Markdown structure unless a small structural improvement clearly helps.

Return the improved markdown only. No preamble, no explanation."""
