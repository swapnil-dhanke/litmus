# litmus

A cross-paper contradiction/agreement mapper for a narrow ML research subfield.

## Scope

Does prompting an LLM to review/revise its own reasoning (math, logic, QA tasks),
with little or no external feedback, actually improve accuracy? Where does the
literature agree/disagree, and why?

Corpus: 18 arXiv papers on LLM self-correction (see `data/corpus_candidates.md`).

## Roadmap

- [x] Phase 0 — Scope & corpus selection
- [x] Phase 1 — Ingestion & embeddings
- [x] Phase 2 — Structured claim extraction (Neo4j)
- [x] Phase 3 — Contradiction detection
- [x] Phase 4 — Agentic layer (ReAct from scratch, then LangGraph)
- [x] Phase 5 — Guardrails (every claim traces to a quoted source sentence)
- [x] Phase 6 — Evaluation suite (hand-labeled ground truth, precision/recall, RAGAS-style)
- [ ] Phase 7 — Token/cost optimization
- [ ] Phase 8 — Polish & GitHub

## Known limitations (to formally measure in Phase 6)

- **Citation/reference titles mistaken for claims.** Phase 2's extraction occasionally
  picks up a *cited* paper's title (mentioned in running text) as if it were a claim
  the source paper is making. Caught in Phase 3 spot-checks; caused a handful of
  spurious contradiction/agreement relationships between claims that are actually
  just two different citation references to other papers.
- **"Different wording, same conclusion" judgment errors.** The local 3B judgment
  model (llama3.2) occasionally flags two claims as contradicting when they actually
  reach the same conclusion via different specific mechanisms. Partially mitigated
  with an improved prompt (few-shot example + "state each claim's conclusion first"),
  which reduced false-positive contradictions substantially (93 → 49 → 38 across
  three prompt iterations), but not eliminated entirely.
- Both issues are logged here rather than further hand-tuned, since Phase 6's
  hand-labeled ground truth + precision/recall evaluation is the right tool to
  measure and address them systematically rather than manual spot-checking.

## Evaluation (Phase 6)

Built a blind, hand-labeled ground truth set to formally measure the contradiction/agreement
judge (Phase 3), rather than continuing to hand-tune from small ad-hoc spot-checks. Methodology:
sampled 25 pairs currently saved as `AGREES_WITH` and 25 as `CONTRADICTS`, shuffled them together,
and hand-labeled all 50 blind (the pipeline's actual answer was hidden in a separate file until
scoring, to avoid anchoring).

**Measured precision** (of pairs the pipeline flagged, how many were correct per hand-label):
- `agrees`: 13/25 correct — **52%**
- `contradicts`: 5/25 correct — **20%**

Note: this measures precision only, not full recall — Phase 3 never persisted "judged unrelated"
outcomes, so there's no record of candidate pairs the judge silently passed over that might have
actually been real agreements/contradictions it missed.

**Key finding:** of the 25 pairs flagged `contradicts`, 17 (68%) were judged `agrees` by hand —
a systematic bias, not noise. Despite three rounds of ad-hoc prompt tuning in Phase 3 (reducing
raw contradiction counts 93 → 49 → 38), the judge still confuses real agreement for contradiction
far more often than the reverse.

**Follow-up: one targeted, data-driven prompt fix was attempted and rejected.** Added a second
few-shot example plus a stricter "only choose contradicts if genuinely opposing" instruction,
aimed directly at the diagnosed bias. Re-checked (read-only, no writes to the graph) against the
5 pairs independently confirmed as genuinely contradicting: **0/5 still verified as `contradicts`**
— the fix overcorrected, trading false positives for false negatives. A softer version (dropping
the second example, keeping only the stricter instruction) improved this to 1/5, and 15/39 on the
full re-check — still not a clear win, and several of the reclassified pairs turned out to involve
claims that are actually paper titles or duplicate citations (the same Phase 5 extraction-quality
issues), meaning a real share of the remaining confusion traces back to noisy input to the judge
rather than the judgment prompt itself.

**Decision: stopped tuning the judge prompt further.** Same conclusion as Phase 3's original
"stop ad-hoc tuning" decision, now with harder evidence behind it — measurably, tightening
precision on a 3B local model's classification prompt degrades recall on the same class, and a
meaningful share of remaining errors are attributable to upstream claim-extraction quality (Phase
2), not the judge. The graph itself was left unmodified (both prompt attempts were tested
read-only against saved data, never applied to a live re-run), so the original Phase 3 numbers
(482 agrees, 38 contradicts) still stand. Fixing this properly would mean improving Phase 2
extraction quality first — logged as future work rather than continuing to chase judge-prompt
tuning with diminishing returns.

## Guardrails (Phase 5)

Every claim's `source_sentence` is checked against the real text of its paper (fuzzy match via
`difflib.SequenceMatcher`, with exact substring containment treated as a perfect match) and
tagged `verified`/`match_score` in the graph rather than filtered out, so the flag rate is a
measurable signal instead of silently discarded data. Current result: **1,571 / 1,625 verified
(96.7%)**, 54 flagged (3.3%). The agent's tools (`search_claims`, `find_relationships`) surface
this tag inline on every claim they return.

Spot-checking the flagged claims surfaced four distinct extraction failure modes from Phase 2,
each confirmed against real data:
- Paper titles/headings extracted as claims (never appear as real sentences in prose)
- Claim/source misattribution (claim text and its "quoted" source are about unrelated things)
- Prompt-instruction leakage (extraction model echoed its own instructions back as fake content
  on a garbled/formula-heavy chunk)
- Benchmark/case-study examples inside a paper mistaken for the paper's own claims (e.g. a worked
  trivia example the `confidence_matters` paper uses to illustrate its method)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
