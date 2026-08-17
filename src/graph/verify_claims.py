import re
import json
from difflib import SequenceMatcher
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "Swapnil@123"))

THRESHOLD = 0.8  # ratio for matches


def split_into_sentences(text):
    text = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.!?]) +", text)


def get_all_claims():
    query = """
    MATCH (c:Claim)-[:EXTRACTED_FROM]->(p:Paper)
    RETURN elementId(c) AS id, c.text AS text, c.source_sentence AS source_sentence, p.name AS paper_name
    """
    with driver.session() as session:
        result = session.run(query)
        return [dict(record) for record in result]


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def load_paper_sentences(paper_name):
    with open(f"data/processed/{paper_name}.json") as f:
        data = json.load(f)
    sentences = []
    for chunk in data["chunks"]:
        sentences.extend(split_into_sentences(chunk))
    return sentences


def best_match_score(source_sentence, sentences):
    normalized_source = normalize(source_sentence)
    best = 0.0
    for sentence in sentences:
        normalized_sentence = normalize(sentence)
        if normalized_source in normalized_sentence or normalized_sentence in normalized_source:
            return 1.0
        score = SequenceMatcher(None, normalized_source, normalized_sentence).ratio()
        if score > best:
            best = score
    return best


def best_match_sentence(source_sentence, sentences):
    normalized_source = normalize(source_sentence)
    best_score = 0.0
    best_sentence = ""
    for sentence in sentences:
        normalized_sentence = normalize(sentence)
        if normalized_source in normalized_sentence or normalized_sentence in normalized_source:
            return 1.0, sentence
        score = SequenceMatcher(None, normalized_source, normalized_sentence).ratio()
        if score > best_score:
            best_score = score
            best_sentence = sentence
    return best_score, best_sentence


def set_verification(claim_id, verified, score):
    query = """
    MATCH (c:Claim)
    WHERE elementId(c) = $claim_id
    SET c.verified = $verified, c.match_score = $score
    """
    with driver.session() as session:
        session.run(query, claim_id=claim_id, verified=verified, score=score)


def run_verification():
    claims = get_all_claims()

    claims_by_paper = {}
    for claim in claims:
        claims_by_paper.setdefault(claim["paper_name"], []).append(claim)

    verified_count = 0
    flagged_count = 0

    for paper_name, paper_claims in claims_by_paper.items():
        sentences = load_paper_sentences(paper_name)
        for claim in paper_claims:
            score = best_match_score(claim["source_sentence"], sentences)
            verified = score >= THRESHOLD
            set_verification(claim["id"], verified, score)
            if verified:
                verified_count += 1
            else:
                flagged_count += 1
        print(f"{paper_name}: done")

    print(f"\nVerified: {verified_count}")
    print(f"Flagged: {flagged_count}")


def spot_check(paper_name, limit=5):
    claims = [c for c in get_all_claims() if c["paper_name"] == paper_name]
    sentences = load_paper_sentences(paper_name)
    shown = 0
    for claim in claims:
        score, closest = best_match_sentence(claim["source_sentence"], sentences)
        if score < THRESHOLD:
            print(f"Claim: {claim['text']}")
            print(f"  Claimed source: {claim['source_sentence']}")
            print(f"  Closest real sentence ({score:.2f}): {closest}")
            print()
            shown += 1
        if shown >= limit:
            break


if __name__ == "__main__":
    # run_verification()
    spot_check("confidence_matters")