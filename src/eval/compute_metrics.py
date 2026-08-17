import csv
import json

with open("data/eval_labeling_sheet.csv") as f:
    reader = csv.DictReader(f)
    human_labels = {row["pair_id"]: row["human_label"].strip().lower() for row in reader}

with open("data/eval_pipeline_labels.json") as f:
    pipeline_labels = json.load(f)

confusion = {}
correct = 0
total = 0

for pair_id, pipeline_label in pipeline_labels.items():
    human_label = human_labels.get(pair_id)
    if not human_label:
        continue
    total += 1
    if human_label == pipeline_label:
        correct += 1
    key = (pipeline_label, human_label)
    confusion[key] = confusion.get(key, 0) + 1

print(f"Overall agreement with human labels: {correct}/{total} ({correct/total:.1%})\n")

for label in ["agrees", "contradicts"]:
    label_total = sum(v for (p, h), v in confusion.items() if p == label)
    label_correct = confusion.get((label, label), 0)
    precision = label_correct / label_total if label_total else 0
    print(f"{label}: {label_correct}/{label_total} correct — precision {precision:.1%}")

print("\nFull breakdown (pipeline said → human said → count):")
for (pipeline_label, human_label), count in sorted(confusion.items()):
    print(f"  {pipeline_label} → {human_label}: {count}")