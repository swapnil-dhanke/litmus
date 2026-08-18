from typing import TypedDict
import json
import requests
from langgraph.graph import StateGraph, END
from tools import search_claims, find_relationships


class AgentState(TypedDict):
    question: str
    history: str
    seen_observations: set
    action: str
    action_input: str
    steps: int
    prompt_tokens: int
    completion_tokens: int


def format_observation(action, result):
    if action == "search_claims":
        lines = []
        for score, text, paper, verified, match_score in result:
            tag = "verified" if verified else f"UNVERIFIED match={match_score:.2f}"
            lines.append(f"- ({score:.3f}) [{paper}] [{tag}] {text}")
        return "\n".join(lines)
    elif action == "find_relationships":
        matched_tag = "verified" if result["matched_verified"] else "UNVERIFIED"
        lines = [f"Matched claim: {result['matched_claim']} ({result['matched_paper']}) [{matched_tag}]", "Agrees with:"]
        lines += [f"  - [{a['paper_name']}] [{'verified' if a['verified'] else 'UNVERIFIED'}] {a['text']}" for a in result["agreements"]]
        lines.append("Contradicts:")
        lines += [f"  - [{c['paper_name']}] [{'verified' if c['verified'] else 'UNVERIFIED'}] {c['text']}" for c in result["contradictions"]]
        return "\n".join(lines)


def windowed_history(history, max_lines=12):
    lines = history.strip().split("\n")
    if len(lines) <= max_lines:
        return history
    return "...(earlier steps omitted)...\n" + "\n".join(lines[-max_lines:])


def agent_node(state: AgentState) -> dict:
    prompt = f"""You are a research assistant answering questions about LLM self-correction research.

    You have two tools:
    - search_claims: search for claims relevant to a topic. Input: a search query.
    - find_relationships: given a claim description, find what agrees with or contradicts it. Input: a claim description.

    Question: {state['question']}

    {windowed_history(state['history'])}

    If you already have enough information from the observations above, use action "finish" now.

    Decide your next step. Respond with JSON in this exact shape:
    {{"thought": "your reasoning", "action": "search_claims", "input": "your search query"}}
    or
    {{"thought": "your reasoning", "action": "find_relationships", "input": "claim description"}}
    or
    {{"thought": "your reasoning", "action": "finish", "input": "your final answer to the question"}}"""

    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_predict": 300},
    }
    response = requests.post(url, json=payload, timeout=60)
    result = response.json()
    content = result["message"]["content"]

    try:
        decision = json.loads(content)
    except json.JSONDecodeError:
        decision = {"thought": "parse error", "action": "finish", "input": "Unable to process."}

    thought_line = f"Thought: {decision.get('thought', '')}\n"
    if decision.get("action") == "finish":
        thought_line += f"Final Answer: {decision.get('input', '')}\n"

    return {
        "action": decision.get("action", "finish"),
        "action_input": decision.get("input", ""),
        "history": state["history"] + thought_line,
        "steps": state["steps"] + 1,
        "prompt_tokens": state["prompt_tokens"] + result.get("prompt_eval_count", 0),
        "completion_tokens": state["completion_tokens"] + result.get("eval_count", 0),
    }


def tool_node(state: AgentState) -> dict:
    action = state["action"]
    action_input = state["action_input"]

    if action == "search_claims":
        result = search_claims(action_input)
    elif action == "find_relationships":
        result = find_relationships(action_input)
    else:
        return {"history": state["history"]}

    observation = format_observation(action, result)

    if observation in state["seen_observations"]:
        note = "You already saw this exact result. Use action \"finish\" now."
        new_history = state["history"] + f"Action: {action}({action_input})\nObservation: {note}\n"
        return {"history": new_history}

    new_seen = state["seen_observations"] | {observation}
    new_history = state["history"] + f"Action: {action}({action_input})\nObservation: {observation}\n"
    return {"history": new_history, "seen_observations": new_seen}


MAX_STEPS = 6


def route_after_agent(state: AgentState) -> str:
    if state["action"] == "finish":
        return "finish"
    if state["steps"] >= MAX_STEPS:
        return "force_finish"
    return "use_tool"


def force_finish_node(state: AgentState) -> dict:
    prompt = f"""Based on everything below, give your best final answer to the question. Do not use any tools.

    Question: {state['question']}

    {state['history']}

    Respond with JSON in this exact shape:
    {{"answer": "your final answer"}}"""

    url = "http://localhost:11434/api/chat"
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_predict": 300},
    }
    response = requests.post(url, json=payload, timeout=60)
    result = response.json()
    content = result["message"]["content"]

    try:
        answer = json.loads(content).get("answer", "Unable to produce a final answer.")
    except json.JSONDecodeError:
        answer = "Unable to produce a final answer."

    return {
        "history": state["history"] + f"Forced final answer: {answer}\n",
        "prompt_tokens": state["prompt_tokens"] + result.get("prompt_eval_count", 0),
        "completion_tokens": state["completion_tokens"] + result.get("eval_count", 0),
    }


graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tool", tool_node)
graph.add_node("force_finish", force_finish_node)

graph.set_entry_point("agent")

graph.add_conditional_edges(
    "agent",
    route_after_agent,
    {"use_tool": "tool", "finish": END, "force_finish": "force_finish"},
)
graph.add_edge("tool", "agent")
graph.add_edge("force_finish", END)

app = graph.compile()


if __name__ == "__main__":

    initial_state = {
        "question": "Does self-correction via prompting improve LLM reasoning without external feedback?",
        "history": "",
        "seen_observations": set(),
        "action": "",
        "action_input": "",
        "steps": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }
    final_state = app.invoke(initial_state, {"recursion_limit": 25})
    print(final_state["history"])
    print(f"\nTotal prompt tokens: {final_state['prompt_tokens']}")
    print(f"Total completion tokens: {final_state['completion_tokens']}")
    print(f"Total tokens: {final_state['prompt_tokens'] + final_state['completion_tokens']}")