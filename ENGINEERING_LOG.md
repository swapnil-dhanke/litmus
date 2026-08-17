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

### 30. Rebuilding the hand-built agent in LangGraph — first run "did nothing"
**Context:** After writing `AgentState` (a `TypedDict`) and a helper function in the new
LangGraph version, running the file produced no output and no error.
**Explanation (not a bug):** The file only contained type/function *definitions* at that point —
no node wiring, no graph compile, no entry point that actually invoked anything. Python reaching
the end of a file with nothing left to execute is expected, not a failure.
**Why it matters:** Worth being able to distinguish "silent because nothing runs yet" from
"silently failing" before spending time debugging — cheap to check, easy to misdiagnose under
time pressure.

### 31. LangGraph node silently returned `None`
**Context:** `tool_node` was left incomplete mid-edit (missing its `if/elif` tool dispatch and
`return` statement) but was still syntactically valid Python, so it imported and ran without
error.
**Root cause:** A function with no explicit `return` implicitly returns `None`. LangGraph expects
every node to return a dict of state updates; `None` broke the graph's state-merging step instead
of raising an obvious error at the source.
**Fix:** Completed the function body with its intended dispatch/repetition-guard logic and an
explicit `return {...}`.
**Why it matters:** A reminder that "the file parses and runs" is a much weaker guarantee than
"the file does what I meant" — especially for functions expected to always return a specific
shape (a common source of quiet framework-level failures).

### 32. `KeyError: 'steps'` on the very first graph run
**Context:** Added a `steps` field to `AgentState` (for a step-count safety net) and referenced
`state["steps"]` inside a node, but the very first invocation crashed.
**Root cause:** Declaring a field in a `TypedDict` only documents the *shape* state is expected
to have — it doesn't populate a default value. The actual `initial_state` dict passed to
`app.invoke(...)` still lacked a `"steps"` key.
**Fix:** Added `"steps": 0` to `initial_state`.
**Why it matters:** `TypedDict` is a type hint, not a runtime guarantee or an auto-initializer —
every field referenced inside a node must actually be present in whatever gets passed to
`invoke()`.

### 33. `GraphRecursionError` — the graph looped without ever finishing
**Context:** The LangGraph agent ran for 20 steps and was killed by LangGraph's built-in
`recursion_limit` safety net without producing an answer.
**Root cause:** Same underlying issue as the hand-built agent's original repetition problem
(a small local model not reliably choosing to stop) — but `recursion_limit` is a blunt cutoff
enforced *outside* the graph. By the time it fires, LangGraph has already abandoned the run, so
there's no way to gracefully produce a forced answer from inside a caught exception.
**Fix:** Replicated the hand-built agent's forced-finish fallback as an explicit third path
*inside* the graph itself: a `steps` counter incremented every agent turn, a routing function
that redirects to a dedicated `force_finish` node once the counter passes a threshold, and that
node making one last tool-free LLM call to produce a best-effort answer from whatever context
was already gathered.
**Why it matters:** A generic framework safety net (a recursion/step limit) and a
domain-appropriate graceful-degradation path are two different things — the former stops
disaster, the latter produces a usable result. Both are needed; neither substitutes for the
other.

### 34. Graph wiring mismatches caught at `compile()`/first-run time
**Context:** Adding the `force_finish` path took three attempts before it worked: first, the
conditional edge's routing dict didn't include a `"force_finish"` key at all (`ValueError:
unknown target`); then the key was added but pointed at a node that was never registered with
`graph.add_node(...)` (a second `ValueError`); then the node was registered but its own outgoing
edge to `END` was still missing.
**Fix:** Each error message named the exact missing piece; added them one at a time until the
graph's `validate()` step (run automatically inside `compile()`) passed cleanly.
**Why it matters:** LangGraph wiring has three parts that all have to agree with each other — a
registered node, a routing function's return value, and a mapping entry for that return value.
`compile()`'s validation catching this *before* runtime (rather than failing deep inside a graph
execution) is a good illustration of why frameworks like this validate structure eagerly.

### 35. Files became structurally tangled after many incremental patches
**Context:** After several rounds of "change this one function" edits to both `graph_agent.py`
and (later, in Phase 5) `verify_claims.py`, both files accumulated real structural damage: a
whole block of code left indented as though still inside the *previous* function (making it
part of that function's body instead of its own top-level logic), a function defined twice with
only the second definition actually taking effect, and print statements referencing variables
that were now out of scope — none of which raised an error immediately, since the code was still
syntactically valid Python.
**Fix:** Rather than continuing to patch piece by piece, rewrote each file's full contents from
scratch once the tangle was identified, restructuring loose top-level code into properly named
functions (e.g. `run_verification()`) and gating actual execution behind
`if __name__ == "__main__":`.
**Why it matters:** Small, isolated patches are usually the right call, but there's a point where
the cost of re-deriving full context from a diff exceeds the cost of just re-supplying the whole
file — recognizing that crossover point (rather than patching indefinitely) is itself a practical
skill.

### 36. `git push` reported "up to date" despite an unsaved fix
**Context:** After fixing a bug in the editor, `git status` reported "nothing to commit" and
`git push` said "up to date" — even though the fix was clearly visible on screen.
**Root cause:** The file's editor tab had unsaved changes (the fix existed only in the editor's
in-memory buffer). Git only ever sees what's actually written to disk, so as far as git was
concerned, nothing had changed.
**Fix:** Saved the file, re-checked `git status` (now showed the file as modified), then
committed and pushed.
**Why it matters:** A good reminder to verify "is this actually saved to disk" as a first check
whenever a fix visibly exists but git refuses to acknowledge it — cheap to check, easy to
overlook.

### 37. Computed value assigned but never actually used
**Context:** After fixing entry 31's bug, a follow-up fix built a `thought_line` variable meant
to include the agent's final answer text — but the function's actual `return` statement still
referenced the old, separately-reconstructed line instead of the new variable, so the fix had no
effect despite compiling and running without error.
**Verification:** Caught not by re-reading the local file (which "looked" fixed) but by fetching
the pushed version directly from GitHub's raw content and comparing it line by line.
**Why it matters:** A variable can be computed correctly and still never affect the program's
behavior if nothing downstream actually reads it — "the fix is in the file" and "the fix is in
the code path that runs" are different claims, and only the second one matters. Also reinforces
verifying pushed state independently rather than trusting a local visual check.

---

## Phase 5 — Guardrails

### 38. Design decision: fuzzy matching, flag-don't-delete
**Context:** Phase 2's claim extraction asked the model to include a `source_sentence` alongside
every claim, but nothing ever verified the model actually quoted the paper rather than inventing
a plausible-sounding sentence (a classic RAG/agent failure mode: hallucinated citation).
**Decisions made explicitly, before writing code:**
  - Fuzzy matching (allowing minor whitespace/punctuation drift) instead of strict exact-substring
    matching, since the pipeline's own upstream cleanup (hyphenation fixes, whitespace collapsing)
    could otherwise cause false flags on genuinely correct quotes.
  - Flagging unverified claims (`c.verified = false`, `c.match_score = ...`) rather than deleting
    them, so the false/flag rate becomes a measurable metric for Phase 6 instead of silently
    discarded data.
**Why it matters:** Making the strictness/severity tradeoffs explicit up front, rather than
picking defaults implicitly, made the later debugging (entry 41) much easier to reason about —
the threshold and matching method were known, deliberate choices, not accidents.

### 39. Reusing sentence-splitting logic across packages was more trouble than it was worth
**Context:** `src/ingestion/chunker.py` already had a `split_into_sentences` function that was
exactly what the new guardrail script needed.
**Root cause:** `chunker.py` has module-level code (a demo `extract_text(...)` call) that runs on
*any* import, not just when the file is run directly, and its own sibling imports
(`from clean_text import clean_text`) only resolve correctly when something inside
`src/ingestion/` is the directly-executed script — neither of which holds when importing it from
a file living in `src/graph/`.
**Fix:** Duplicated the 3-line function locally in the new file instead of importing it
cross-package.
**Why it matters:** Sometimes the pragmatic choice is small, deliberate duplication rather than
fighting an existing module's structural assumptions — worth being able to justify that tradeoff
explicitly rather than treating "never duplicate code" as an absolute rule. (Also surfaced
`chunker.py`'s module-level side effect as real tech debt, logged but not fixed, since it wasn't
blocking current work.)

### 40. High initial flag rate (31.4%) prompted investigation instead of acceptance
**Context:** First full run of the verification guardrail: 1,114 verified / 511 flagged out of
1,625 claims.
**Decision:** Rather than accepting or reporting that number at face value, spot-checked several
flagged claims side-by-side with their claimed source and closest real sentence — the same
instinct applied earlier in Phase 3 to the contradiction false-positive investigation.
**Why it matters:** A guardrail's own output can itself contain measurement bugs; treating a
guardrail's flags as automatically "ground truth" without spot-checking would have produced a
misleading number in the README/CV material.

### 41. Root cause of most flags: length-sensitive similarity scoring, not hallucination
**Context:** Spot-checking showed most flagged claims were genuine, word-for-word exact quotes —
just partial ones (missing a trailing citation list, or starting mid-sentence relative to the
real text).
**Root cause:** `difflib.SequenceMatcher.ratio()` computes similarity based on total string
length on both sides, so a short, 100%-accurate partial quote against a much longer real sentence
scores low (0.60–0.73) purely from the length mismatch — not from any actual content
disagreement.
**Fix:** Checked plain substring containment first (`normalized_source in normalized_sentence or
normalized_sentence in normalized_source`) and short-circuited to a perfect score (`1.0`) on a
match, only falling back to the fuzzy ratio when containment failed.
**Result:** Flagged claims dropped from 511 (31.4%) to 54 (3.3%) — verified count rose from 1,114
to 1,571.
**Why it matters:** A strong example of a metric-design bug masquerading as a data-quality
problem — the fix wasn't to the underlying data or the extraction pipeline at all, just to how
similarity was being measured.

### 42. Remaining flagged claims revealed real, distinct extraction failure modes
**Context:** With the scoring bug fixed, the remaining ~3% of flagged claims were spot-checked
again to confirm they were genuine issues rather than more scoring noise.
**Findings — four distinct categories, each confirmed with a concrete example:**
  - **Title/heading extracted as a claim** — a paper's own all-caps title, which never appears as
    a real sentence in flowing prose (titles have no sentence-ending punctuation), so it can never
    score well against real text no matter how good the matching method is.
  - **Claim/source misattribution** — the claim text and its "quoted" source sentence were about
    unrelated things (a claim about a refiner's decoding behavior, attached to a nearby math
    formula about weighted-voting aggregation) — the extraction step grabbed the wrong nearby
    sentence as "evidence."
  - **Prompt-instruction leakage** — on a garbled/formula-heavy chunk, the extraction model echoed
    a line from its own *extraction instructions* ("Do not include section headings...") back as
    if it were a claim and source quoted from the paper itself.
  - **Benchmark/case-study example mistaken for a real claim** — confirmed by reading the actual
    source chunk directly: the "confidence_matters" paper includes a worked trivia example
    ("Which restaurant chain's headquarters is further north, Pizza Inn or Papa Gino's?") used to
    illustrate its self-correction method across multiple prompting rounds; the extraction step
    read a sentence from that illustrative example as if it were a real claim about
    self-correction research.
**Why it matters:** Confirms the guardrail is functioning as intended — catching real, distinct
pipeline quality issues rather than just noise — and gives four concrete, well-evidenced examples
for discussing extraction/RAG failure modes in an interview, each traced back to an actual chunk
of real data rather than described abstractly.

---

## Phase 6 — Evaluation Suite

### 43. Circularity risk: an LLM can't grade its own homework
**Context:** Needed real ground truth to measure the Phase 3 contradiction/agreement judge
against, rather than continuing ad-hoc spot-checks.
**Decision:** Used a human-labeled sample as ground truth instead of a second (possibly larger or
"smarter") LLM judging the first — using another LLM to grade the judge would only prove the two
models agree with each other, not that either is actually correct.
**Fix:** Built a small blind-labeling workflow: sample 25 `AGREES_WITH` + 25 `CONTRADICTS` pairs
from Neo4j, shuffle them, hide the pipeline's actual answer in a separate file until scoring, and
hand-label all 50 pairs personally.
**Why it matters:** A genuinely important distinction in eval design — "ground truth" needs to
come from a source independent of the system being measured, or the measurement is circular
regardless of how sophisticated the judge doing the grading is.

### 44. Spreadsheet app silently saved edits to a different file
**Context:** Labeled all 50 pairs in Numbers, but the scoring script found every `human_label`
cell empty when reading `data/eval_labeling_sheet.csv`.
**Root cause:** Numbers' default save (Cmd+S) on an opened `.csv` file doesn't overwrite the CSV
in place — it created a new file, `eval_labeling_sheet.csv.numbers` (treating the entire original
name, `.csv` included, as the base filename and appending its own native extension), leaving the
original CSV untouched and still empty.
**Fix:** File → Export To → CSV in Numbers, explicitly overwriting the original path.
**Why it matters:** A reminder that GUI apps' "Save" can silently mean "save a copy in a different
format" rather than "overwrite this exact file" — worth verifying the actual file on disk (`head
-5 file.csv`) rather than trusting that an edit in an app necessarily landed where a script expects
it to.

### 45. Measured judge precision was much lower than raw counts suggested
**Context:** Phase 3's ad-hoc spot-checks (unstratified, small samples) had reduced raw
contradiction counts from 93 to 38 across three prompt-tuning rounds, which read as meaningful
progress.
**What the blind hand-labeled sample actually found:** precision on `agrees` was 52% (13/25
correct), and precision on `contradicts` was only 20% (5/25 correct) — with 17 of those 25
`contradicts` predictions (68%) being real agreements per hand-label, a systematic bias rather
than random noise.
**Why it matters:** A clear demonstration of why "the raw count went down" and "the precision is
actually good" are different claims — the earlier ad-hoc tuning had genuinely reduced *volume* of
flagged contradictions without necessarily fixing the underlying *rate* at which flagged
contradictions were wrong. Only a properly stratified, blind-labeled sample surfaced the real
number.

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
- **A guardrail's own numbers need the same scrutiny as the thing it's guarding** — the first
  guardrail run's 31.4% flag rate turned out to be mostly a scoring-method artifact, not a real
  data-quality problem; spot-checking the guardrail itself (not just trusting its output) is what
  surfaced that.
- **"It compiles/runs without error" is a weak guarantee** — several real bugs (a node silently
  returning `None`, a computed variable never actually used, a file edited but never saved)
  produced no error at all; only checking actual behavior against actual expectations (running
  it, or diffing the actually-pushed remote file) caught them.
