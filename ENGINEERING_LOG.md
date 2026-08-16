# litmus — Engineering Log

A chronological record of every real problem hit while building litmus, why it happened,
how it was fixed, and why that fix was the right call. Written for interview prep —
each entry is a real "tell me about a time you debugged X" story.

---

## Phase 1 — Ingestion & Embeddings

### 1. Sandbox network blocked direct PDF downloads
**Context:** Tried to download an arXiv PDF directly via `curl` in an isolated sandbox.
**What happened:** Request blocked by the sandbox's network allowlist (`blocked-by-allowlist`).
**Fix:** Used a web-fetch tool instead, which returned arXiv's HTML rendering of the paper
instead of the PDF.
**Why it matters:** Led to a genuinely useful practice: prefer a paper's HTML rendering over
PDF extraction when available, since it avoids PDF-specific text-extraction noise (though not
all papers have HTML versions, so PDF extraction was still needed for the full corpus).

### 2. `pip install` vs `python3 -m pip install`
**Context:** Installed `requests`/`pypdf` with `pip install`, then got `ModuleNotFoundError`
running the script.
**Root cause:** Multiple Python installations on the machine (conda + system Python) — `pip`
and `python3` didn't point to the same interpreter.
**Fix:** Used `python3 -m pip install ...` instead, which guarantees the install target matches
whichever Python will actually run the script.
**Why it matters:** Classic, very common real-world environment issue — worth being able to
diagnose quickly ("what does `which python3` vs `which pip` show").

### 3. VS Code's Run button used a different interpreter than the terminal
**Context:** Script ran fine from the terminal but failed with `ModuleNotFoundError` when run
via VS Code's Run button.
**Root cause:** VS Code had a different default interpreter (`/usr/bin/python3`, system Python)
selected than the terminal's active conda environment.
**Fix:** Ran from the integrated terminal explicitly, and/or selected the correct interpreter
in VS Code (Cmd+Shift+P → "Python: Select Interpreter").
**Why it matters:** IDEs and terminals can silently disagree about which environment is active —
worth checking explicitly when "it works in the terminal but not the IDE" (or vice versa).

### 4. PDF hyphenation breaking words across lines
**Context:** `pypdf`-extracted text showed words split mid-line where the original PDF had
hyphenated line-wraps, e.g. `"pro-\nposed"` instead of `"proposed"`.
**Fix:** Regex: `re.sub(r"-\n(?=[a-z])", "", text)` — removes a hyphen immediately followed by
a newline when a lowercase letter follows, rejoining the split word.
**Why it matters:** Real, common PDF-extraction artifact. Left unfixed, it would have polluted
every downstream step (chunking, claim extraction) with broken word fragments.

### 5. Paragraph splitting failed on PDF text
**Context:** Chunking logic split text on `"\n\n"` (double newline = paragraph break), which
worked on hand-typed test strings but returned only 1 "paragraph" per page on real PDF text.
**Root cause:** `pypdf` inserts a single `\n` per detected line, with no distinction between a
line-wrap and a real paragraph break — so there were no `\n\n` sequences to split on at all
within a page.
**Fix:** Pivoted to sentence-level chunking: collapse all whitespace to single spaces
(`re.sub(r"\s+", " ", text)`), then split into sentences with a regex lookbehind on
sentence-ending punctuation (`re.split(r"(?<=[.!?]) +", text)`).
**Why it matters:** A good example of a plan that seemed reasonable in theory failing on real
data, and adapting the approach based on what the data actually looked like. Sentence-level
chunking also turned out to directly serve Phase 5's guardrail requirement (citing exact source
sentences) — a nice example of a bug fix aligning with a future requirement.

### 6. `NameError` from cross-file variable scope confusion
**Context:** Tried to use a variable (`cleaned`) in `chunker.py` that was actually defined in
a different file, `extract.py`.
**Root cause:** Misunderstanding that each Python file only has access to variables it defines
or explicitly imports — running two separate scripts doesn't share their variables.
**Fix:** Moved the relevant code into the same file, or used proper imports.

### 7. `ModuleNotFoundError: No module named 'src'`
**Context:** A script doing a cross-package import (`from src.ingestion.papers import papers`)
failed when run directly (`python3 path/to/file.py`).
**Fix:** Ran it as a module instead: `python3 -m src.embeddings.embed_all` (dots, no `.py`,
run from the project root). The `-m` flag tells Python to resolve the import path relative to
the project root, rather than treating the file as a standalone script.
**Why it matters:** This distinction (`python3 file.py` vs `python3 -m package.module`) is a
genuinely common source of confusion — good to be able to explain clearly.

### 8. Neo4j `ServiceUnavailable` / `Connection refused`
**Context:** Python driver couldn't connect to the local Neo4j instance.
**Root cause:** The Neo4j Desktop database instance simply wasn't started yet (or was still
mid-startup).
**Fix:** Started the instance in Neo4j Desktop, waited for it to show "RUNNING," then retried.

### 9. Anxiety about a new Neo4j instance affecting an existing one
**Context:** Created a new `litmus` Neo4j instance alongside a pre-existing unrelated instance
(`CodeLens`, used for a prior project).
**Resolution:** Each Neo4j Desktop instance is a fully separate database with its own isolated
storage folder on disk — no shared state, no risk of cross-contamination.
**Why it matters:** Understanding instance/database isolation is a real, transferable concept —
worth being able to explain confidently rather than just trusting it blindly.

### 10. `AuthError: Unauthorized`
**Context:** Connecting to Neo4j from Python failed with an authentication error.
**Root cause:** Placeholder text (`"your_password"`) left in the code instead of the real
password, in a couple of different new files over the course of the project.
**Fix:** Replaced the placeholder with the actual password each time.
**Why it matters:** A reminder that copy-pasted template code needs to be actually adapted, not
just reused verbatim — an easy, recurring mistake.

---

## Phase 2 — Structured Claim Extraction

### 11. Stale git lock files blocking `git branch -M main`
**Context:** A prior `git commit` run in a restricted sandbox environment left behind stale
`.git/HEAD.lock`, `index.lock`, and `objects/maintenance.lock` files (the sandbox's filesystem
permissions prevented git from cleaning them up after the operation completed). These got
copied over when the project was moved to the real machine.
**Fix:** Manually deleted the stale lock/tmp files on the real filesystem, where normal
permissions applied.
**Why it matters:** Git lock files are a real safety mechanism (preventing two git processes
from writing simultaneously) that can get "stuck" if a process is interrupted or blocked
mid-operation — good to recognize and know it's generally safe to manually clear them once
you're sure no git process is actually running.

### 12. `git push` rejected — diverged histories
**Context:** First push to a freshly created GitHub repo was rejected ("fetch first").
**Root cause:** The GitHub repo wasn't actually empty — likely auto-initialized with a README
when created, giving it a commit history unrelated to the local repo's.
**Fix:** `git push --force` (safe here specifically because the remote had nothing of value yet
— a rule that does NOT generally apply once collaborating or once real work exists remotely).
**Why it matters:** Understanding *when* force-push is safe vs. dangerous is a genuinely
important git concept for interviews.

### 13. LLM extracted a section heading as a "claim"
**Context:** Structured claim extraction returned `"LLM S CANNOT SELF-CORRECT REASONING
INTRINSICALLY"` as if it were a real claim — actually a section header.
**Fix:** Refined the extraction prompt to explicitly instruct the model to exclude headings,
titles, author names, and citation markers.
**Why it matters:** First encounter with a recurring theme across the whole project: an LLM
told to do X will often mostly do X, but not perfectly — every extraction step needs both
better prompting AND downstream defensive handling, not one or the other.

### 14. `KeyError` from missing expected field in LLM JSON output
**Context:** `claim["source_sentence"]` crashed partway through a run.
**Root cause:** `"format": "json"` (Ollama's JSON mode) guarantees syntactically valid JSON,
but not that the JSON matches the *exact schema* requested — the model occasionally omitted
a field.
**Fix:** Added a defensive check before use: `if "claim" not in claim or "source_sentence" not
in claim: continue` — skip malformed individual items instead of crashing the whole run.
**Why it matters:** Core lesson: validating "is this valid JSON" is not the same as validating
"does this JSON have the shape I actually need." Both checks are necessary when consuming LLM
output.

### 15. A single chunk hung for 7+ minutes
**Context:** One extraction call appeared stuck; confirmed via Activity Monitor that the
`llama-server` process was genuinely at 95% GPU the whole time — not frozen, but not
finishing either.
**Root cause:** Likely a repetition loop — the model failing to find a clean way to close the
JSON structure and generating far more than necessary before (eventually) stopping.
**Fix:** Added `"options": {"num_predict": 500}` to cap the model's maximum output length, and
`timeout=60` on the HTTP request as an independent client-side safety net, catching the timeout
exception and treating it like any other failed chunk (skip, continue).
**Why it matters:** Any unattended loop calling a generative model needs both a
generation-length cap AND a request timeout — two independent layers of defense, since either
one alone can still leave a gap.

### 16. `TypeError: 'int' object is not iterable`
**Context:** `for claim in claims:` crashed because `claims` was an integer, not a list.
**Root cause:** The model responded with `{"claims": 0}` (a count) instead of `{"claims": []}`
(an empty list) for some chunk — valid JSON, correct key, wrong *type*.
**Fix:** Added `isinstance(claims, list)` type-checking before returning, on top of the
existing key-presence check.
**Why it matters:** A third, distinct layer of defensive parsing (valid JSON → right keys →
right types) — this incident specifically drove home that all three checks are genuinely
independent and each can fail separately.

### 17. Crash mid-run left the batch job partially complete
**Context:** An interrupted terminal session (VS Code restart) killed a multi-hour batch
extraction job partway through.
**Root cause / risk:** Since `Claim` nodes are created with `CREATE` (not `MERGE`), naively
rerunning from the start would create duplicate claims for already-processed papers.
**Fix (iterative):** Started with a hardcoded single-paper skip check, then generalized to
dynamically query Neo4j for which papers already have claims (`MATCH (c:Claim)-[:EXTRACTED_FROM]
->(p:Paper) RETURN DISTINCT p.name`) and skip those automatically — making the script safely
resumable regardless of when or how it's interrupted.
**Why it matters:** A strong example of designing for idempotency/resumability in long-running
jobs — very relevant to real production data pipelines, and a good "how would you make this
production-ready" interview answer.

### 18. Partially-processed papers hid inside "already done" data
**Context:** Two papers (`self_correction_illusion`, `confidence_matters`) had been cut off
mid-processing by earlier interruptions, but the "has any claims = fully done" skip logic
couldn't distinguish partial completion from full completion.
**How it was caught:** Compared claims-per-chunk ratio across all 18 papers — one was a clear
statistical outlier (0.43 claims/chunk vs. a normal range of 0.85–2.2 for every other paper).
**Fix:** Cleared that paper's claims (`MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper {name: ...})
DETACH DELETE c`) and let it reprocess from scratch.
**Why it matters:** A good example of using a simple statistical sanity check (a ratio, compared
across a population) to catch a data-quality bug that wouldn't be visible from looking at any
single data point in isolation.

### 19. Accidental duplicate for-loop while editing
**Context:** Intended to add one `print()` line but accidentally duplicated an entire loop
block instead.
**Impact if unnoticed:** Would have doubled runtime and created duplicate claims (again, no
dedup on `CREATE`).
**Fix:** Caught by reviewing the actual file content (via screenshot) before running, rather
than assuming the edit was applied as intended.
**Why it matters:** Reinforces "verify before running," especially for edits to files already
mid-way through a long-running, expensive process.

### 20. Overnight run risked being killed by sleep
**Context:** A multi-hour unattended batch job needed to survive the laptop going idle.
**Fix:** Wrapped the command with `caffeinate` (`caffeinate python3 -m ...`), a macOS utility
that prevents sleep only for the duration of the wrapped command, no manual cleanup needed
afterward.

---

## Phase 3 — Contradiction Detection

### 21. Naive all-pairs comparison was computationally infeasible
**Context:** 1,625 extracted claims → comparing every possible pair would be ~1.3 million
LLM calls.
**Fix:** Two-stage approach — cheap embedding-based cosine-similarity filtering first (find
plausible candidate pairs), expensive LLM judgment only on the much smaller candidate set.
**Why it matters:** This is the same core idea as RAG's retrieval step, applied to a different
problem — "filter cheaply, reason expensively only on what's left" is a broadly reusable
pattern, not just an embeddings-specific trick.

### 22. Similarity threshold tuning (0.75 → 0.85)
**Context:** A 0.75 similarity threshold produced 9,475 candidate pairs — roughly 8-13 hours
of LLM judgment time, impractical.
**Fix:** Raised the threshold to 0.85, reducing candidates to 803 pairs (~1 hour) — since all
1,625 claims already share a narrow topic, a looser threshold was catching "same general
subject" pairs rather than "actually comparable, specific" pairs.
**Why it matters:** A real precision/recall tradeoff made consciously, with the reasoning
stated explicitly, rather than picking a threshold arbitrarily.

### 23. Pairwise similarity computed via NumPy matrix multiplication instead of a Python loop
**Context:** Even after threshold filtering, computing similarity itself needed to happen
across many claim pairs.
**Key insight:** Ollama's `/api/embed` returns L2-normalized (unit-length) vectors, so cosine
similarity reduces to a plain dot product (no division needed). Computing every pairwise dot
product between many vectors is exactly what matrix multiplication does.
**Fix:** `embeddings @ embeddings.T` (a NumPy matrix multiply) computed the entire 1625×1625
similarity matrix in about a second, versus what would have been a much slower pure-Python
loop.
**Why it matters:** Strong, concrete example of vectorization — reformulating a "loop over many
items" problem as a single matrix operation for a large speedup. Very common interview topic.

### 24. False-positive contradictions, round 1
**Context:** Spot-checking the first batch of LLM-judged "contradictions" revealed several were
actually agreements — e.g., two different papers' definitions of "self-correction," or two
claims both independently saying LLMs struggle to self-correct, misclassified as opposing.
**Root cause:** The judgment prompt didn't clearly define what should NOT count as a
contradiction — the model appeared to pattern-match "worded differently" as "disagreeing."
**Fix:** Rewrote the prompt with explicit definitions distinguishing "agrees" (same conclusion,
possibly different wording) from "contradicts" (genuinely opposing conclusions about the same
specific question).
**Result:** False-positive contradictions dropped from 93 to 49.

### 25. False-positive contradictions, round 2 (partial fix + new issue found)
**Context:** A second spot-check after the round-1 prompt fix showed the same "different
wording, same conclusion" pattern persisting in some pairs, plus a distinct new issue: a
paper's own ALL-CAPS title had been extracted as a "claim" back in Phase 2.
**Fix (two parts):**
  - Filtered claims where `.isupper()` is true before judgment (catches all-caps headings).
  - Improved the prompt further with a concrete few-shot example of the exact failure pattern,
    plus asking the model to state each claim's conclusion explicitly before deciding
    (a lightweight chain-of-thought technique — forces explicit reasoning instead of pattern
    matching straight to an answer).
**Result:** Contradictions dropped further, 49 → 38.

### 26. False positives, round 3 — decided to stop manual tuning
**Context:** A third spot-check revealed a subtler variant of the heading problem: a *cited*
paper's title appearing in another paper's running text (a citation reference, e.g. "As CRITIC
showed...") got mistaken for a claim during extraction. Since it's normal title-case text (not
all-caps), the `.isupper()` filter didn't catch it.
**Decision:** Rather than continuing to hand-tune prompts and eyeball small samples
indefinitely (diminishing returns, no real measurement of actual accuracy), documented this as
a known limitation in the README and explicitly deferred it to Phase 6's formal hand-labeled
precision/recall evaluation.
**Why it matters:** Knowing when to stop ad-hoc iteration and switch to a properly measured
evaluation process is itself a mature engineering decision, not a failure to fix something —
a genuinely good thing to be able to articulate in an interview ("I identified the failure
mode, decided manual tuning without data was hitting diminishing returns, and built a formal
eval instead").

---

## Phase 4 — Agentic Layer (ReAct)

### 27. Relationship direction was arbitrary, not semantic
**Context:** Building the `find_relationships` tool required querying which claims a given
claim agrees/contradicts.
**Root cause:** Phase 3's relationships were saved in whichever direction the pairwise loop
happened to iterate (`claims[i] → claims[j]` where `i < j`), which is an implementation detail,
not a meaningful "source vs. target" semantic.
**Fix:** Queried relationships without a direction arrow in Cypher (`-[:CONTRADICTS]-` instead
of `-[:CONTRADICTS]->`), matching the relationship regardless of which "side" the claim is on.
**Why it matters:** A reminder to think about what a stored relationship's direction actually
*means* (or doesn't) before writing queries against it.

### 28. Agent stuck in an exact repetition loop
**Context:** First real ReAct agent test — the agent called the identical tool with the
identical input three times in a row, never reaching a "finish" action, and hit the step limit.
**Root cause:** Even with the full conversation history available in the prompt every time, a
small local model (3B parameters) doesn't reliably notice it's repeating itself — it kept
pattern-matching toward the same action rather than reasoning about prior attempts.
**Fix:** Added a repetition guard: tracked `(action, input)` tuples in a Python `set`; if the
model tried an exact repeat, blocked the tool call and injected a corrective observation
telling it to try something different or finish.
**Why it matters:** A textbook example of a well-known agentic AI failure mode (repetition
loops), and the standard fix (guard against it in code, don't rely on the model to self-correct).

### 29. Repetition guard caught exact repeats but missed reworded ones
**Context:** After the fix above, the agent avoided exact repeats but kept rewording the same
underlying query slightly each time, producing near-identical results without triggering the
exact-string-match guard.
**Fix (two parts):**
  - Changed the guard to track *observations* (the tool's actual output) instead of just the
    action's input text — catches "differently worded query, same underlying result," which is
    a more robust repetition signal than comparing input strings.
  - Added a forced final-answer fallback: if the step budget runs out without the agent
    naturally choosing to finish, one last LLM call explicitly disallows further tool use and
    forces an answer using whatever context was already gathered — so the agent degrades
    gracefully instead of just failing with no answer at all.
**Why it matters:** Distinguishes *syntactic* repetition (same text) from *semantic* repetition
(same underlying result, different wording) — the second is harder to detect and a genuinely
interesting problem. The forced-finish fallback is also a broadly important production pattern:
an agent should never just give up with nothing.

---

## Cross-cutting themes (good for a "what did you learn" interview answer)

- **LLM output needs defense in depth**: valid syntax ≠ right keys ≠ right types ≠ right
  semantics — each is a genuinely separate failure mode requiring its own check.
- **Unattended/long-running jobs need to be resumable and safe to interrupt** — assume they
  will be interrupted, and design for it from the start rather than discovering it the hard way.
- **Small local models are real, capable, but genuinely limited** — cheap and private, but they
  need more scaffolding (explicit definitions, few-shot examples, repetition guards, forced
  fallbacks) than a larger hosted model might need for the same task.
- **Know when to stop manual tuning and start measuring** — several rounds of "spot-check,
  find an issue, patch the prompt" hit diminishing returns; the right move was formalizing
  evaluation (Phase 6) rather than continuing to guess from small samples.
