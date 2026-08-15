# litmus — Candidate Corpus (Phase 0 draft)

**Scope:** Does prompting an LLM to review/revise its own reasoning (math, logic, QA
tasks), with little or no external feedback, actually improve accuracy? Where does
the literature agree/disagree, and why?

## Negative / "it doesn't really work" camp
- Huang et al., *Large Language Models Cannot Self-Correct Reasoning Yet* — arXiv:2310.01798
- *The Self-Correction Illusion: LLMs Correct Others but Not Themselves* — arXiv:2606.05976
- Kamoi et al., *When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey* — arXiv:2406.01297

## Positive / "it does work" camp
- Madaan et al., *Self-Refine: Iterative Refinement with Self-Feedback* — arXiv:2303.17651
- Shinn et al., *Reflexion: Language Agents with Verbal Reinforcement Learning* — arXiv:2303.11366
- Wu et al., *Large Language Models Can Self-Correct with Key Condition Verification* — EMNLP 2024 — arXiv:2405.14092
- Kumar et al., *Training Language Models to Self-Correct via Reinforcement Learning* (SCoRe) — ICLR 2025 — arXiv:2409.12917

## Nuanced / "it depends" camp
- Zhang et al., *Small Language Models Need Strong Verifiers to Self-Correct Reasoning* — ACL 2024 — arXiv:2404.17140
- Pan et al., *Automatically Correcting Large Language Models: Surveying self-correction strategies* — arXiv:2308.03188
- *Confidence Matters: Revisiting Intrinsic Self-Correction Capabilities of LLMs* — arXiv:2402.12563
- *Confidence v.s. Critique: A Decomposition of Self-Correction Capability for LLMs* — arXiv:2412.19513
- *Self-Reflective Generation at Test Time* — arXiv:2510.02919
- *Self-Correcting Large Language Models: Generation vs. Multiple Choice* — arXiv:2511.09381
- *CoRefine: Confidence-Guided Self-Refinement for Adaptive Test-Time Compute* — arXiv:2602.08948
- *Refining Over Resampling: Test-Time Self-Correction for LLM Reasoning* — arXiv:2608.05643
- *Beyond Output Critique: Self-Correction via Task Distillation* — arXiv:2602.00871

## Nuanced / "it depends" camp (cont.)
- *Lost at the Beginning of Reasoning* — arXiv:2506.22058 (verified: first CoT step disproportionately drives final answer; errors there degrade self-correction)
- *The Illusion of Insight in Reasoning Models* — arXiv:2601.00514 (verified: "aha moment" mid-reasoning shifts rarely improve accuracy intrinsically; extrinsic triggering helps)

## Status: LOCKED
18 papers confirmed. Phase 0 complete.
