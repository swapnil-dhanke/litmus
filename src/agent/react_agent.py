import json
import requests
from tools import search_claims, find_relationships


def format_observation(action, result):
    if action == "search_claims":
        return "\n".join(f"- ({score:.3f}) [{paper}] {text}" for score, text, paper in result)
    elif action == "find_relationships":
        lines = [f"Matched claim: {result['matched_claim']} ({result['matched_paper']})", "Agrees with:"]
        lines += [f"  - [{a['paper_name']}] {a['text']}" for a in result["agreements"]]
        lines.append("Contradicts:")
        lines += [f"  - [{c['paper_name']}] {c['text']}" for c in result["contradictions"]]
        return "\n".join(lines)


# def run_agent(question, max_steps=5):
#     history = f"Question: {question}\n"

#     for step in range(max_steps):
#         prompt = f"""You are a research assistant answering questions about LLM self-correction research.

#         You have two tools:
#         - search_claims: search for claims relevant to a topic. Input: a search query.
#         - find_relationships: given a claim description, find what agrees with or contradicts it. Input: a claim description.

#         {history}

#         Decide your next step. Respond with JSON in this exact shape:
#         {{"thought": "your reasoning", "action": "search_claims", "input": "your search query"}}
#         or
#         {{"thought": "your reasoning", "action": "find_relationships", "input": "claim description"}}
#         or
#         {{"thought": "your reasoning", "action": "finish", "input": "your final answer to the question"}}"""

#         url = "http://localhost:11434/api/chat"
#         payload = {
#             "model": "llama3.2",
#             "messages": [{"role": "user", "content": prompt}],
#             "format": "json",
#             "stream": False,
#             "options": {"num_predict": 300},
#         }
#         response = requests.post(url, json=payload, timeout=60)
#         content = response.json()["message"]["content"]

#         try:
#             decision = json.loads(content)
#         except json.JSONDecodeError:
#             print("Failed to parse response, stopping.")
#             break

#         thought = decision.get("thought", "")
#         action = decision.get("action")
#         action_input = decision.get("input", "")

#         print(f"Thought: {thought}")
#         print(f"Action: {action}({action_input})")

#         if action == "finish":
#             return action_input

#         if action == "search_claims":
#             tool_result = search_claims(action_input)
#         elif action == "find_relationships":
#             tool_result = find_relationships(action_input)
#         else:
#             print(f"Unknown action: {action}")
#             break

#         observation = format_observation(action, tool_result)
#         print(f"Observation: {observation}\n")
#         history += f"Thought: {thought}\nAction: {action}({action_input})\nObservation: {observation}\n"

#     return "Could not reach a final answer within the step limit."

# def run_agent(question, max_steps=6):
#     history = f"Question: {question}\n"
#     tried_actions = set()

#     for step in range(max_steps):
#         prompt = f"""You are a research assistant answering questions about LLM self-correction research.

#         You have two tools:
#         - search_claims: search for claims relevant to a topic. Input: a search query.
#         - find_relationships: given a claim description, find what agrees with or contradicts it. Input: a claim description.

#         {history}

#         If you already have enough information from the observations above, use action "finish" now
#         rather than repeating a search. Do not repeat an action you've already tried.

#         Decide your next step. Respond with JSON in this exact shape:
#         {{"thought": "your reasoning", "action": "search_claims", "input": "your search query"}}
#         or
#         {{"thought": "your reasoning", "action": "find_relationships", "input": "claim description"}}
#         or
#         {{"thought": "your reasoning", "action": "finish", "input": "your final answer to the question"}}"""

#         url = "http://localhost:11434/api/chat"
#         payload = {
#             "model": "llama3.2",
#             "messages": [{"role": "user", "content": prompt}],
#             "format": "json",
#             "stream": False,
#             "options": {"num_predict": 300},
#         }
#         response = requests.post(url, json=payload, timeout=60)
#         content = response.json()["message"]["content"]

#         try:
#             decision = json.loads(content)
#         except json.JSONDecodeError:
#             print("Failed to parse response, stopping.")
#             break

#         thought = decision.get("thought", "")
#         action = decision.get("action")
#         action_input = decision.get("input", "")

#         print(f"Thought: {thought}")
#         print(f"Action: {action}({action_input})")

#         if action == "finish":
#             return action_input

#         action_key = (action, action_input)
#         if action_key in tried_actions:
#             print("Blocked repeat action, forcing a nudge.\n")
#             history += (f"Thought: {thought}\nAction: {action}({action_input})\n"
#                         f"Observation: You already tried this exact action. Try something "
#                         f"different, or use action \"finish\" to answer with what you know.\n")
#             continue
#         tried_actions.add(action_key)

#         if action == "search_claims":
#             tool_result = search_claims(action_input)
#         elif action == "find_relationships":
#             tool_result = find_relationships(action_input)
#         else:
#             print(f"Unknown action: {action}")
#             break

#         observation = format_observation(action, tool_result)
#         print(f"Observation: {observation}\n")
#         history += f"Thought: {thought}\nAction: {action}({action_input})\nObservation: {observation}\n"

#     return "Could not reach a final answer within the step limit."

def run_agent(question, max_steps=6):
    history = f"Question: {question}\n"
    seen_observations = set()

    for step in range(max_steps):
        prompt = f"""You are a research assistant answering questions about LLM self-correction research.

        You have two tools:
        - search_claims: search for claims relevant to a topic. Input: a search query.
        - find_relationships: given a claim description, find what agrees with or contradicts it. Input: a claim description.

        {history}

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
        content = response.json()["message"]["content"]

        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            print("Failed to parse response, stopping.")
            break

        thought = decision.get("thought", "")
        action = decision.get("action")
        action_input = decision.get("input", "")

        print(f"Thought: {thought}")
        print(f"Action: {action}({action_input})")

        if action == "finish":
            return action_input

        if action == "search_claims":
            tool_result = search_claims(action_input)
        elif action == "find_relationships":
            tool_result = find_relationships(action_input)
        else:
            print(f"Unknown action: {action}")
            break

        observation = format_observation(action, tool_result)

        if observation in seen_observations:
            print("Blocked repeat observation, forcing a nudge.\n")
            history += (f"Thought: {thought}\nAction: {action}({action_input})\n"
                        f"Observation: You already saw this exact result. You have enough "
                        f"information — use action \"finish\" now.\n")
            continue
        seen_observations.add(observation)

        print(f"Observation: {observation}\n")
        history += f"Thought: {thought}\nAction: {action}({action_input})\nObservation: {observation}\n"

    print("Step limit reached, forcing final answer from gathered context...")
    final_prompt = f"""Based on everything gathered below, answer the original question directly.
Do not call any tools. Just answer using what's already here.

{history}

Question: {question}

Respond with JSON: {{"answer": "your final answer"}}"""
    payload = {
        "model": "llama3.2",
        "messages": [{"role": "user", "content": final_prompt}],
        "format": "json",
        "stream": False,
        "options": {"num_predict": 300},
    }
    response = requests.post(url, json=payload, timeout=60)
    content = response.json()["message"]["content"]
    try:
        return json.loads(content).get("answer", "Unable to produce a final answer.")
    except json.JSONDecodeError:
        return "Unable to produce a final answer."


if __name__ == "__main__":
    answer = run_agent("Does self-correction improve LLM reasoning without external feedback?")
    print("\nFINAL ANSWER:", answer)