import csv
import json
from judge_claims import judge_pair

with open("data/eval_labeling_sheet.csv") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

with open("data/eval_pipeline_labels.json") as f:
    pipeline_labels = json.load(f)

confirmed_real = [
    row for row in rows
    if row["human_label"].strip().lower() == "contradicts"
    and pipeline_labels.get(row["pair_id"]) == "contradicts"
]

print(f"Checking {len(confirmed_real)} pairs you confirmed as genuinely contradicting\n")

for row in confirmed_real:
    claim_a = {"text": row["text_a"], "paper_name": row["paper_a"]}
    claim_b = {"text": row["text_b"], "paper_name": row["paper_b"]}
    new_relationship = judge_pair(claim_a, claim_b)
    print(f"New verdict: {new_relationship}")
    print(f"  [{row['paper_a']}] {row['text_a']}")
    print(f"  [{row['paper_b']}] {row['text_b']}\n")