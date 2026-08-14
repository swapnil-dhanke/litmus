# litmus

A cross-paper contradiction/agreement mapper for a narrow ML research subfield.

## Scope

Does prompting an LLM to review/revise its own reasoning (math, logic, QA tasks),
with little or no external feedback, actually improve accuracy? Where does the
literature agree/disagree, and why?

Corpus: 18 arXiv papers on LLM self-correction (see `data/corpus_candidates.md`).

## Roadmap

- [x] Phase 0 — Scope & corpus selection
- [ ] Phase 1 — Ingestion & embeddings
- [ ] Phase 2 — Structured claim extraction (Neo4j)
- [ ] Phase 3 — Contradiction detection
- [ ] Phase 4 — Agentic layer (ReAct from scratch, then LangGraph)
- [ ] Phase 5 — Guardrails (every claim traces to a quoted source sentence)
- [ ] Phase 6 — Evaluation suite (hand-labeled ground truth, precision/recall, RAGAS-style)
- [ ] Phase 7 — Token/cost optimization
- [ ] Phase 8 — Polish & GitHub

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
