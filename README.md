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
- [ ] Phase 4 — Agentic layer (ReAct from scratch, then LangGraph)
- [ ] Phase 5 — Guardrails (every claim traces to a quoted source sentence)
- [ ] Phase 6 — Evaluation suite (hand-labeled ground truth, precision/recall, RAGAS-style)
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

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
