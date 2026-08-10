"""
The prompt-loop: each topic goes through 3 chained content calls + 1
portfolio-relevance call + 1 merge/polish pass.
Chaining (instead of one giant prompt) keeps each call focused, so the model
doesn't skimp on ASCII diagrams to save room for interview questions, etc.
"""

STAGE_1_THEORY = """You are writing beginner-to-advanced study notes on: {topic}

Recent web search context (use ONLY to keep version numbers, current best
practices, or recent changes accurate — do NOT quote or dump this raw into
the notes, weave relevant bits in naturally, ignore anything irrelevant or
if it says no results were available):
---
{search_context}
---

Write CONCISE theory notes structured in 3 clear levels:

## Beginner
- Core definitions and "why this exists" — assume zero prior knowledge
- 3-5 key concepts, each explained in 2-3 sentences max

## Intermediate
- How it's used in real projects
- Common patterns, gotchas, and best practices
- 3-5 key concepts

## Advanced
- Internals / how it works under the hood
- Performance, scaling, and edge-case considerations
- 3-5 key concepts

Rules:
- Be CONCISE. No filler, no repeated explanations across levels.
- Use bullet points and short paragraphs, not long prose blocks.
- Use proper Markdown headers (##, ###).
- Do NOT include ASCII diagrams or interview questions here — those come later.
- Output ONLY the markdown notes, no preamble like "Here are the notes"."""


STAGE_2_ASCII_ARCHITECTURE = """You are creating ASCII architecture diagrams for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create 2-4 ASCII diagrams that visualize the most important architectural
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


STAGE_2_5_PORTFOLIO_RELEVANCE = """You are matching a study-notes topic against a developer's real portfolio projects.

Topic: {topic}

Portfolio projects (name, description, tech stack):
---
{portfolio_context}
---

Task: identify ONLY the portfolio projects that genuinely use or relate to
{topic}. Do NOT force-fit a project that isn't actually relevant just to
have something to show.

For each genuine match, write:
- **Project:** name
- **How {topic} is used:** 1-2 sentences, specific to what that project
  actually does with it (not generic praise)

Output ONLY this section in markdown, starting with a
"## Where I've Used This" heading. If there are no genuine matches (or the
portfolio list is empty), output exactly:

## Where I've Used This
_No current portfolio project uses {topic} yet._

No preamble, no repeated theory text."""


STAGE_3_INTERVIEW_QUESTIONS = """You are compiling the most commonly asked interview questions for: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create an interview questions section with 12-15 questions total, organized as:

## Interview Questions

### Beginner (4-5 questions)
### Intermediate (4-5 questions)
### Advanced (4-5 questions)

For each question:
- **Q:** the question
- **A:** a concise, correct answer (2-5 sentences — enough to actually answer
  it in an interview, not just a one-liner)

Pick the questions that are ACTUALLY most commonly asked for {topic} in real
technical interviews — not generic filler questions.

Output ONLY this section in markdown. No preamble."""


STAGE_4_MERGE_POLISH = """You are finalizing a study notes document on: {topic}

You are given four sections generated separately. Merge them into ONE
clean, well-formatted markdown document. Fix any redundancy, inconsistent
terminology, or awkward transitions between sections, but do NOT shorten
or remove content — just polish the seams.

Add a single top-level title "# {topic} — Study Notes" and a short 2-3
line intro paragraph at the very top.

Place the "Where I've Used This" section right after the intro and before
the theory levels. If it says no project uses this topic yet, keep that
line as-is — do not invent a project to fill it.

--- THEORY SECTION ---
{stage1_output}

--- WHERE I'VE USED THIS SECTION ---
{stage2_5_output}

--- ASCII DIAGRAMS SECTION ---
{stage2_output}

--- INTERVIEW QUESTIONS SECTION ---
{stage3_output}

Output ONLY the final merged markdown document, nothing else — no preamble,
no "Here's the final document" text."""
