"""Pinned, read-only CSV audit. No Django/database access or model training.

Run with project .venv Python; only the Python standard library is required.
Raw data, row-level results and sample texts stay in ignored data/.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REPO = "DoDataThings/us-bank-transaction-categories-v2"
REVISION = "3e8d052cb7b362fb1a04b6064d2331982553ea56"
BASE = f"https://huggingface.co/datasets/{REPO}"
TREE_URL = f"https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}"
RAW = ROOT / "data" / "external" / "dodatathings-v2" / REVISION
META = ROOT / "docs" / "metadata"
SEED = "task06a-manual-v1"
PREFIX = re.compile(r"^\s*\[(debit|credit)\]\s*", re.I)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def direction(text):
    found = PREFIX.match(text)
    return found.group(1).lower() if found else "missing"


def body(text):
    return normalize(PREFIX.sub("", text, count=1))


def template(text):
    """Heuristic, not a merchant extractor. Keep words; mask reference/digit runs."""
    value = body(text)
    # Explicit bank reference fields, including all-letter randomized codes.
    value = re.sub(r"((?:ppd|web)\s+id\s*:\s*)[a-z0-9-]+", r"\1 <ref>", value)
    # Mixed alphanumeric references after '*' (PayPal/Square/etc.).
    value = re.sub(r"(?<=\*)\s*[a-z0-9-]*\d[a-z0-9-]*", " <ref>", value)
    # Every digit run, including dates, card digits, address/zip and IDs.
    value = re.sub(r"\d+", " <n> ", value)
    value = re.sub(r"[^\w<>]+", " ", value)
    return " ".join(value.split())


def fetch(url, limit):
    with urlopen(Request(url, headers={"User-Agent": "ThesisDataAudit/1.0"}), timeout=60) as response:
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("Source larger than allowed download limit")
        return content


def download():
    manifest_path = META / "classification-source.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    tree = json.loads(fetch(TREE_URL, 100_000))
    entries = {entry["path"]: entry for entry in tree if entry["type"] == "file"}
    files = {}
    for filename in ("transactions-synthetic.csv", "README.md"):
        url = f"{BASE}/resolve/{REVISION}/{filename}"
        content = fetch(url, 10_000_000)
        git_oid = hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()
        expected = entries[filename]
        if len(content) != expected["size"] or git_oid != expected["oid"]:
            raise ValueError(f"Pinned Git blob verification failed: {filename}")
        if previous and digest(content) != previous["files"][filename]["sha256"]:
            raise ValueError("Downloaded content differs from recorded SHA-256")
        destination = RAW / filename
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError(f"Refusing to overwrite different local file: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            destination.write_bytes(content)
        files[filename] = {"url": url, "bytes": len(content), "sha256": digest(content), "git_blob_sha1": git_oid}
    card = (RAW / "README.md").read_text(encoding="utf-8")
    if not re.search(r"^license:\s*mit\s*$", card, re.M):
        raise ValueError("Expected MIT declaration not found in pinned source card")
    if previous is None:
        write_json(manifest_path, {
            "dataset": REPO, "revision": REVISION,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "tree_url": TREE_URL, "tree_files": sorted(entries), "files": files,
            "local_raw_directory": RAW.relative_to(ROOT).as_posix(),
            "license": {"declared": "MIT", "evidence": f"{BASE}/blob/{REVISION}/README.md",
                        "terms": "https://opensource.org/license/mit",
                        "standalone_license_in_tree": "LICENSE" in entries,
                        "rights_independently_audited": False},
        })
    print("Pinned downloads verified; original acquisition timestamp preserved.")


def duplicate_stats(keys, labels):
    groups = defaultdict(list)
    for index, key in enumerate(keys):
        groups[key].append(index)
    duplicates = [ids for ids in groups.values() if len(ids) > 1]
    conflicts = [ids for ids in groups.values() if len({labels[i] for i in ids}) > 1]
    return {
        "unique_keys": len(groups), "duplicate_groups": len(duplicates),
        "rows_in_duplicate_groups": sum(map(len, duplicates)),
        "excess_rows": len(keys) - len(groups), "max_group_rows": max(map(len, groups.values()), default=0),
        "conflicting_groups": len(conflicts), "rows_in_conflicting_groups": sum(map(len, conflicts)),
    }, groups, conflicts


class UnionFind:
    def __init__(self, size):
        self.parents = list(range(size))

    def find(self, index):
        while self.parents[index] != index:
            self.parents[index] = self.parents[self.parents[index]]
            index = self.parents[index]
        return index

    def union(self, left, right):
        self.parents[self.find(right)] = self.find(left)


def fixed_samples(rows, count=5):
    by_label = defaultdict(dict)
    for record_id, row in enumerate(rows, 1):
        by_label[row["category"]].setdefault(normalize(row["description"]), record_id)
    result = {}
    for label, descriptions in sorted(by_label.items()):
        ordered = sorted(descriptions, key=lambda value: (digest(f"{SEED}|{label}|{value}".encode()), value))
        result[label] = [{"record_id": descriptions[value], "description": rows[descriptions[value] - 1]["description"]}
                         for value in ordered[:count]]
    return result


def audit():
    provenance = json.loads((META / "classification-source.json").read_text(encoding="utf-8"))
    if provenance["revision"] != REVISION or provenance["dataset"] != REPO:
        raise ValueError("Unexpected dataset/revision in provenance")
    for filename, info in provenance["files"].items():
        if digest((RAW / filename).read_bytes()) != info["sha256"]:
            raise ValueError(f"Local SHA-256 mismatch: {filename}")
    content = (RAW / "transactions-synthetic.csv").read_bytes()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""), strict=True)
    columns = reader.fieldnames
    rows = list(reader)
    if columns != ["description", "category"] or not rows or any(None in row or None in row.values() for row in rows):
        raise ValueError("Unexpected CSV schema/row width")
    labels = [row["category"] for row in rows]
    descriptions = [row["description"] for row in rows]
    keys = {"exact": descriptions, "normalized": list(map(normalize, descriptions)),
            "without_direction": list(map(body, descriptions)), "template": list(map(template, descriptions))}
    result = {
        "audit_version": 1,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "methods": {"normalization": "NFC + casefold + collapse/strip Unicode whitespace; keep punctuation",
                    "template": "strip direction; mask PPD/WEB ID codes and digit-bearing tokens after *; mask digit runs; fold punctuation; retain words",
                    "manual_sample_seed": SEED, "manual_samples_per_label": 5,
                    "manual_sample_selection": "SHA256(seed|category|normalized_description), first 5 unique keys per category; representative = first CSV record",
                    "split_seed": "task06a-split-v1", "split_target_percent": [70, 15, 15]},
        "dataset_revision": REVISION, "csv_sha256": digest(content), "rows": len(rows), "columns": columns,
        "blank_or_whitespace": {col: sum(not row[col].strip() for row in rows) for col in columns},
        "literal_null_like": {col: dict(Counter(row[col] for row in rows if row[col].strip().casefold() in {"null", "none", "nan", "n/a"})) for col in columns},
        "label_counts": dict(sorted(Counter(labels).items())), "duplicates": {},
        "direction_counts": dict(Counter(map(direction, descriptions))),
        "direction_by_label": {label: dict(Counter(direction(row["description"]) for row in rows if row["category"] == label)) for label in sorted(set(labels))},
    }
    group_maps = {}
    local_conflicts = {}
    uf = UnionFind(len(rows))
    for name, values in keys.items():
        stats, groups, conflicts = duplicate_stats(values, labels)
        result["duplicates"][name] = stats
        group_maps[name] = groups
        local_conflicts[name] = [[i + 1 for i in ids] for ids in conflicts]
        if name in {"without_direction", "template"}:
            for ids in groups.values():
                for other in ids[1:]:
                    uf.union(ids[0], other)
    result["normalization_changed_rows"] = sum(a != b for a, b in zip(descriptions, keys["normalized"]))
    result["duplicate_excess_by_label"] = {
        name: {label: len([i for i, value in enumerate(labels) if value == label]) -
                      len({values[i] for i, value in enumerate(labels) if value == label})
               for label in sorted(set(labels))}
        for name, values in keys.items()}
    body_groups = group_maps["without_direction"]
    opposite = [ids for ids in body_groups.values() if len({direction(descriptions[i]) for i in ids}) > 1]
    result["body_groups_with_multiple_directions"] = {"groups": len(opposite), "rows": sum(map(len, opposite))}
    # Diagnostic majority label using direction only, not a fitted classifier or test score.
    cross = defaultdict(Counter)
    for text, label in zip(descriptions, labels):
        cross[direction(text)][label] += 1
    result["direction_only_majority_correct_rows_in_same_dataset"] = sum(max(counts.values()) for counts in cross.values())
    # Deterministic non-exhaustive near-match candidate search on unique templates.
    # Two sorted orders, next two neighbours in each; >=.80 length ratio,
    # >=.60 token Jaccard, then SequenceMatcher >=.92 (autojunk disabled).
    templates = list(group_maps["template"])
    pairs = set()
    for reverse in (False, True):
        order = sorted(templates, key=lambda value: value[::-1] if reverse else value)
        for position, left in enumerate(order):
            for right in order[position + 1:position + 3]:
                pairs.add(tuple(sorted((left, right))))
    near = []
    eligible = 0
    for left, right in sorted(pairs):
        if min(len(left), len(right)) / max(len(left), len(right), 1) < .80:
            continue
        a, b = set(left.split()), set(right.split())
        if len(a & b) / max(len(a | b), 1) < .60:
            continue
        eligible += 1
        similarity = SequenceMatcher(None, left, right, autojunk=False).ratio()
        if similarity >= .92:
            left_ids, right_ids = group_maps["template"][left], group_maps["template"][right]
            uf.union(left_ids[0], right_ids[0])
            near.append({"left_record_id": left_ids[0] + 1, "right_record_id": right_ids[0] + 1,
                         "similarity": round(similarity, 6), "cross_label": len({labels[i] for i in left_ids + right_ids}) > 1})
    result["near_match"] = {"candidate_pairs": len(pairs), "sequence_comparisons": eligible,
                            "accepted_template_pairs": len(near), "cross_label_pairs": sum(pair["cross_label"] for pair in near),
                            "threshold": .92, "exhaustive": False, "sorted_orders": ["forward", "reversed"], "neighbours": 2}
    components = defaultdict(list)
    for i in range(len(rows)):
        components[uf.find(i)].append(i)
    sizes = Counter(map(len, components.values()))
    result["candidate_groups"] = {"count": len(components), "largest": max(sizes),
                                  "size_histogram": dict(sorted(sizes.items())),
                                  "multi_label_groups": sum(len({labels[i] for i in ids}) > 1 for ids in components.values())}
    # Illustrative hash allocation only, not a frozen training split; labels are not used.
    split_counts = Counter()
    split_labels = defaultdict(Counter)
    assignments = []
    for ids in components.values():
        component_key = min(keys["without_direction"][i] for i in ids)
        slot = int(digest(("task06a-split-v1|" + component_key).encode())[:16], 16) % 100
        split = "train" if slot < 70 else "validation" if slot < 85 else "test"
        split_counts[split] += len(ids)
        split_labels[split].update(labels[i] for i in ids)
        assignments.append({"group_id": digest(component_key.encode()), "partition": split, "record_ids": [i + 1 for i in ids]})
    result["illustrative_split"] = {"counts": dict(split_counts), "labels": {split: dict(counts) for split, counts in split_labels.items()}, "trained": False}
    result["illustrative_split"]["overlap_keys"] = {}
    partition_by_row = {i - 1: assignment["partition"] for assignment in assignments for i in assignment["record_ids"]}
    for name, groups in group_maps.items():
        result["illustrative_split"]["overlap_keys"][name] = sum(len({partition_by_row[i] for i in ids}) > 1 for ids in groups.values())
    naive_partitions = []
    for i in range(len(rows)):
        slot = int(digest(f"task06a-naive-v1|{i + 1}".encode())[:16], 16) % 100
        naive_partitions.append("train" if slot < 70 else "validation" if slot < 85 else "test")
    result["naive_row_hash_split_overlap_keys"] = {
        name: sum(len({naive_partitions[i] for i in ids}) > 1 for ids in groups.values())
        for name, groups in group_maps.items()}
    write_json(META / "classification-audit.json", result)
    write_json(RAW / "audit" / "manual-samples.json", {"seed": SEED, "samples_per_label": 5, "samples": fixed_samples(rows)})
    write_json(RAW / "audit" / "conflicting-records.json", local_conflicts)
    write_json(RAW / "audit" / "near-pairs.json", near)
    write_json(RAW / "audit" / "candidate-groups.json", assignments)
    print(json.dumps({"rows": len(rows), "labels": len(set(labels)), "duplicates": result["duplicates"],
                      "near_match": result["near_match"], "candidate_groups": {key: value for key, value in result["candidate_groups"].items() if key != "size_histogram"}}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download pinned official files, verify Git blobs and persist provenance")
    parser.add_argument("--download-only", action="store_true", help="Only acquisition (requires --download)")
    options = parser.parse_args()
    if options.download_only and not options.download:
        parser.error("--download-only requires --download")
    if options.download:
        download()
    if not options.download_only:
        audit()
