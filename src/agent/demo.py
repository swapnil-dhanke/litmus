"""
Live terminal demo for litmus — built for showing the project to someone in person.

It runs the LangGraph ReAct agent (graph_agent.py) against a few curated questions about the
18-paper self-correction corpus, pretty-prints the agent's real Thought -> Action -> Observation
trace as it happens, and ends with the final answer plus step/token stats.

Run (from anywhere):
    python3 src/agent/demo.py

Or ask a custom question live instead of the built-in ones:
    python3 src/agent/demo.py "Does prompting alone help without external feedback?"

Requires Ollama (localhost:11434) and Neo4j (bolt://127.0.0.1:7687) running locally, exactly like
the rest of the project — this makes no changes to the graph, it only reads from it.
"""
import re
import sys
import time
import requests

from graph_agent import app
from tools import driver as neo4j_driver

# --- terminal colors ---------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
BLUE = "\033[34m"
GRAY = "\033[90m"


def c(text, *codes):
    return "".join(codes) + text + RESET


# --- demo content -------------------------------------------------------------
BANNER = """================================================================
  LITMUS -- Cross-Paper Contradiction/Agreement Mapper
  18 arXiv papers on LLM self-correction research
================================================================"""

STATS = [
    "1,625 claims extracted across 18 papers",
    "482 AGREES_WITH relationships, 38 CONTRADICTS relationships",
    "96.7% of claims verified against real source text (hallucination guardrail)",
]

QUESTIONS = [
    "Does self-correction improve LLM reasoning without external feedback?",
    "What does the literature say about intrinsic self-correction ability in LLMs?",
    "Is there disagreement in the research about whether LLMs can self-correct their own reasoning?",
]


def preflight_check():
    print(c("Checking Ollama and Neo4j are running... ", DIM), end="", flush=True)
    try:
        requests.get("http://localhost:11434", timeout=3)
    except requests.exceptions.RequestException:
        print(c("FAILED", BOLD))
        print(c("Ollama doesn't seem to be running on localhost:11434. Start it and try again.", YELLOW))
        sys.exit(1)
    try:
        neo4j_driver.verify_connectivity()
    except Exception:
        print(c("FAILED", BOLD))
        print(c("Neo4j doesn't seem to be running on bolt://127.0.0.1:7687. Start it and try again.", YELLOW))
        sys.exit(1)
    print(c("OK", GREEN))


def print_history(history):
    """Pretty-print the agent's real Thought/Action/Observation trace with basic coloring.
    Only Thought/Action/Final-Answer lines are single-line by construction; everything else
    (including multi-line Observations) is treated as a continuation and printed dim/gray."""
    for line in history.strip().split("\n"):
        if line.startswith("Thought:"):
            print(c(line, BLUE))
        elif line.startswith("Action:"):
            print(c(line, YELLOW))
        elif line.startswith("Final Answer:") or line.startswith("Forced final answer:"):
            print()
            print(c(line, BOLD, GREEN))
        else:
            print(c(line, GRAY))


def extract_final_answer(final_state, history):
    if final_state.get("action") == "finish":
        return final_state.get("action_input", "")
    match = re.search(r"Forced final answer: (.*)", history)
    return match.group(1) if match else "(no final answer produced)"


def run_question(question, index, total):
    print()
    print(c(f"[{index}/{total}] QUESTION: ", BOLD, CYAN) + question)
    print(c("-" * 70, DIM))

    initial_state = {
        "question": question,
        "history": "",
        "seen_observations": set(),
        "action": "",
        "action_input": "",
        "steps": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }

    start = time.time()
    final_state = app.invoke(initial_state, {"recursion_limit": 25})
    elapsed = time.time() - start

    print_history(final_state["history"])

    answer = extract_final_answer(final_state, final_state["history"])
    total_tokens = final_state["prompt_tokens"] + final_state["completion_tokens"]
    print()
    print(c("FINAL ANSWER: ", BOLD, GREEN) + answer)
    print(c(f"({final_state['steps']} agent step(s), {total_tokens} tokens, {elapsed:.1f}s)", DIM))


def main():
    print(c(BANNER, BOLD))
    for stat in STATS:
        print(c("  " + stat, DIM))
    print()

    preflight_check()

    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else QUESTIONS

    for i, question in enumerate(questions, start=1):
        run_question(question, i, len(questions))
        if i < len(questions):
            input(c("\nPress Enter to continue to the next question...", DIM))

    print()
    print(c("=" * 70, BOLD))
    print(c("  That's litmus -- an agentic RAG system over a knowledge graph built from", BOLD))
    print(c("  18 papers, with hallucination guardrails and a measured, honestly-reported", BOLD))
    print(c("  accuracy evaluation.", BOLD))
    print(c("=" * 70, BOLD))


if __name__ == "__main__":
    main()
