"""
The prompt-loop: each topic goes through a chain of focused content calls
+ 1 portfolio-relevance call. Chaining (instead of one giant prompt) keeps
each call focused so weaker models don't drop sections under one huge
instruction.

Model-agnostic by design: these prompts run against whatever model
`freellmapi` (or any other OpenAI-compatible local server) exposes, which
can be anything from a 3B instruct model to a 70B+ model. That means:

- No fixed word-count or question-count targets ("1,500+ words",
  "35-40 questions"). Targets like that just teach models — especially
  smaller/weaker ones — to pad with filler and invented "modern" trivia to
  hit a number, which is how you end up with generic textbook bloat
  instead of notes about your own experience. Instead prompts specify a
  maximum and explicitly allow "less than the max" as a good outcome.
  The exception is the fundamentals stage's core-theory checklist and the
  diagram stage's count guidance — those exist to guarantee *coverage*
  (don't skip closures/hoisting/event-loop-type basics; don't stop at 2-3
  diagrams when the topic has more genuinely diagram-worthy mechanics),
  not to force padding — they still explicitly forbid restating the same
  point twice just to look thorough.
- No externally-fixed "current year" framing ("as of 2026") — that's a
  training-data assumption a local model can't verify, and it goes stale.
  If recency matters, it comes from {search_context}, not from the model
  asserting a year.
- Every stage asks the model to stop when the topic is actually covered,
  not when a target is hit. A shorter, accurate section beats a padded one.
"""

STAGE_1A_FUNDAMENTALS = """You are writing a study-notes chapter on the fundamentals of: {topic}

Search Context (may be empty — if so, rely on your own knowledge and say
nothing about "current" versions/years you can't verify):
{search_context}

Cover, in this order:
1. Core motivation — what problem this solves and why it exists.
2. Core conceptual/mental model — the ideas someone needs before the syntax makes sense.
3. The essential theory every competent {topic} developer is expected to
   know — the core concepts that come up constantly in real code and in
   interviews (for a language, this typically includes things like:
   scoping rules, how the runtime/engine actually executes code, its
   concurrency/execution model, memory and reference semantics, its type
   system, and its most load-bearing built-in constructs). Do not skip a
   concept just because it's "basic" — basic-but-essential concepts
   belong here explicitly, explained concisely (a few sentences to a
   short paragraph each, not a full lecture), not left implicit or only
   touched in passing elsewhere in the notes.
4. Key primitives and mechanics — the actual building blocks, with short code examples.
5. One complete, realistic example that ties the primitives together (not a toy "hello world").

Rules:
- Section 3 is a checklist of concepts, covered concisely — not an
  invitation to pad. Each concept gets enough explanation to actually
  understand it, not a one-line definition and not an essay.
- Be as long as the topic genuinely needs and no longer — do not pad with
  restated definitions, invented history, or filler transitions to reach
  a length. A tight, concise section is preferred over a padded one, but
  "concise" means no wasted words, not "skip content."
- Do not state specific "latest version" or "as of <year>" facts unless
  they appear in the search context above — say "check current docs for
  the latest X" instead of guessing.
- Every code example must be complete enough to actually run, not a fragment.
- Output ONLY Markdown, no preamble."""

STAGE_1B_DEEP_DIVE = """You are writing an internals and real-world patterns section for: {topic}

Search Context (may be empty):
{search_context}

Fundamentals already covered elsewhere in these notes (for reference only,
don't repeat this content — build on it instead):
---
{stage1_output}
---

Cover:
1. Under-the-hood mechanics that actually change how someone writes code (not trivia) — go deeper than the fundamentals above, don't restate them.
2. 2-3 real architectural patterns people actually use this for, each with a working code example.
3. The most common way this breaks or scales badly in production, and how that's normally addressed.

Rules:
- Only include a pattern or fact if it would change how someone actually
  writes or debugs code — skip anything that's interesting-but-inert
  trivia included just to fill space.
- Do not invent benchmark numbers, specific version numbers, or "as of
  <year>" claims unless they're in the search context.
- Output ONLY Markdown, no preamble."""

STAGE_2_ASCII_ARCHITECTURE = """You are creating ASCII diagrams for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create diagrams for the {topic} concepts that genuinely benefit from a
picture — usually somewhere around 5-8 for a language/framework-sized
topic. Prioritize the CORE mechanics a working developer relies on daily
over incidental details from the one example in the theory context above:
things like the execution/runtime model, scoping or lifecycle, the
type/data model, the concurrency or async model, and the most important
architectural pattern(s) for this topic, in addition to anything specific
from the theory context that's genuinely clearer as a diagram. Do not
pad with a diagram that doesn't add understanding beyond what a single
sentence already conveys.

Rules:
- Wrap every diagram in a markdown code block (```)
- Use box-drawing characters or simple +/-/| ASCII art — must render
  correctly in a monospace font
- Each diagram needs a one-line title (as a ### heading) and a 1-2
  sentence caption
- Keep diagrams under 25 lines each — clarity over completeness
- Output ONLY the diagrams section, starting with "## Architecture Diagrams"
- No preamble, no repeated theory text."""


STAGE_2_5_PORTFOLIO_RELEVANCE = """You are matching a study-notes topic against a developer's real portfolio projects and experience.

Topic: {topic}

Portfolio entries (projects and experience):
---
{portfolio_context}
---

Task: identify ONLY the portfolio projects/experience that genuinely use
or relate to {topic}. Do NOT force-fit a project that isn't actually
relevant just to have something to show — an empty or short result is a
correct result if that's the truth.

For each genuine match, write:
- Put project matches under `### Projects`.
- Put experience matches under `### Experience`.
- For each match:
  - **Project:** name, when the match is a project
  - **Experience:** role/company, when the match is an experience item
  - **How {topic} is used:** 1-2 sentences, specific to what that item
    actually does with it (not generic praise, not restating the stack list)

Output ONLY this section in markdown, starting with a
"## Where I've Used This" heading. If there are no genuine matches (or the
portfolio list is empty), output exactly:

## Where I've Used This
_No current portfolio project or experience uses {topic} yet._

No preamble, no repeated theory text."""


STAGE_3_INTERVIEW_QUESTIONS = """You are compiling commonly asked interview questions for: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create an interview questions section, organized as:

## Interview Questions

### Beginner
### Intermediate
### Advanced
### Scenario

Include ONLY questions that are genuinely, commonly asked for {topic} in
real technical interviews — up to about 8-10 per section, but fewer is
fine if that's all that's genuinely common. Do not invent obscure
questions just to hit a count.

For each question:
- **Q:** the question
- **A:** a concise, correct answer (2-5 sentences — enough to actually
  answer it in an interview, not a one-liner, but not padded either)

Output ONLY this section in markdown. No preamble."""


STAGE_2_7_PITFALLS = """You are writing a "Common Pitfalls & Debugging" section for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

List the mistakes, gotchas, and failure modes people ACTUALLY commonly hit
with {topic} — as many as are genuinely common (often somewhere around
8-12), not padded to a target count.

For each item:
- State the pitfall clearly.
- Explain why it happens.
- Give a short (1-3 sentence) fix or debugging approach.

Output ONLY this section in markdown, starting with "## Common Pitfalls & Debugging".
No preamble."""


STAGE_2_8_CHEATSHEET = """You are writing a compact "Quick Reference Cheat Sheet" for study notes on: {topic}

Based on this theory context (for reference only, don't repeat it):
---
{stage1_output}
---

Create a dense quick-reference section for rapid scanning.

Requirements:
- Bullets, mini tables, or short grouped lists — not prose.
- Only include syntax, commands, key terms, and patterns that were
  actually covered above or are genuinely essential — don't introduce
  new unrelated trivia just to fill the section out.
- Prefer dense, accurate recall over padded explanation.

Output ONLY this section in markdown, starting with "## Quick Reference Cheat Sheet".
No preamble."""
