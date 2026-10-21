"""TASK 06B: sealed group split -> validation selection -> final test, offline.

All records/manifests/models stay under ignored data/experiments/classification/.
Only aggregate statistics and hashes are exported to docs/metadata/.
"""
import argparse
import csv
import hashlib
import io
import json
import platform
import sys
import time
import warnings
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
import threadpoolctl
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

import audit_classification_data as audit

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments" / "classification-v1.json"
SHARE = ROOT / "docs" / "metadata"
RUN_BASE = ROOT / "data" / "experiments" / "classification"
EXPECTED_REVISION = "3e8d052cb7b362fb1a04b6064d2331982553ea56"
EXPECTED_CSV_SHA = "0424aed6e76f74a5b3b1ff61ccec43bc321622e6806da353b910b3b2c8108f6e"


def sha(value):
    return hashlib.sha256(value).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb" if exclusive else "wb") as handle:
        handle.write(json_bytes(value))


def now():
    return datetime.now(timezone.utc).isoformat()


def event(run, name, **fields):
    with (run / "events.jsonl").open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps({"at_utc": now(), "event": name, **fields}, ensure_ascii=False) + "\n")


def runtime():
    return {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__,
            "threadpoolctl": threadpoolctl.__version__, "platform": platform.platform()}


def config():
    cfg = read_json(CONFIG)
    if cfg["revision"] != EXPECTED_REVISION or cfg["csv_sha256"] != EXPECTED_CSV_SHA:
        raise ValueError("Config does not match pinned source")
    if not 1 <= len(cfg["C_values"]) <= 3 or len(set(cfg["C_values"])) != len(cfg["C_values"]) or any(c <= 0 for c in cfg["C_values"]):
        raise ValueError("Each family must have 1-3 distinct positive C values")
    if cfg["refit_train_validation"]:
        raise ValueError("This protocol fits only train, never train+validation")
    if cfg["split"]["names"] != ["train", "validation", "test"] or len(cfg["split"]["ratios"]) != 3 or not np.isclose(sum(cfg["split"]["ratios"]), 1) or any(r <= 0 for r in cfg["split"]["ratios"]):
        raise ValueError("Invalid three-way split ratios")
    return cfg


def verify_original_graph(rows, groups, pairs, reference):
    """Validate the old component IDs without replacing them after filtering."""
    row_to_group = {}
    for group in groups:
        ids = group["record_ids"]
        if not ids or any(i < 1 or i > len(rows) for i in ids):
            raise ValueError("Invalid original group member")
        expected_id = sha(min(audit.body(rows[i - 1]["description"]) for i in ids).encode())
        if group["group_id"] != expected_id:
            raise ValueError("Original group ID does not match original component body")
        for record_id in ids:
            if record_id in row_to_group:
                raise ValueError("Duplicate original group membership")
            row_to_group[record_id] = group["group_id"]
    if set(row_to_group) != set(range(1, len(rows) + 1)):
        raise ValueError("Original group manifest does not cover all CSV records")
    uf = audit.UnionFind(len(rows))
    template_groups = defaultdict(list)
    bodies = defaultdict(list)
    for i, row in enumerate(rows):
        bodies[audit.body(row["description"])].append(i)
        template_groups[audit.template(row["description"])].append(i)
    for mapping in (bodies, template_groups):
        for ids in mapping.values():
            for other in ids[1:]:
                uf.union(ids[0], other)
    # Repeat the deterministic 06A near-candidate search; check cached evidence.
    candidates = set()
    for reverse in (False, True):
        order = sorted(template_groups, key=lambda value: value[::-1] if reverse else value)
        for index, left in enumerate(order):
            for right in order[index + 1:index + 3]:
                candidates.add(tuple(sorted((left, right))))
    reconstructed = []
    for left, right in sorted(candidates):
        if min(len(left), len(right)) / max(len(left), len(right), 1) < .80:
            continue
        a, b = set(left.split()), set(right.split())
        if len(a & b) / max(len(a | b), 1) < .60:
            continue
        similarity = SequenceMatcher(None, left, right, autojunk=False).ratio()
        if similarity >= .92:
            l_ids, r_ids = template_groups[left], template_groups[right]
            uf.union(l_ids[0], r_ids[0])
            reconstructed.append({"left_record_id": l_ids[0] + 1, "right_record_id": r_ids[0] + 1,
                                  "similarity": round(similarity, 6),
                                  "cross_label": len({rows[i]["category"] for i in l_ids + r_ids}) > 1})
    if reconstructed != pairs:
        raise ValueError("06A near-pair evidence differs from recomputation")
    components = defaultdict(list)
    for i in range(len(rows)):
        components[uf.find(i)].append(i + 1)
    component_sets = {frozenset(ids) for ids in components.values()}
    if component_sets != {frozenset(group["record_ids"]) for group in groups}:
        raise ValueError("06A original group components differ from recomputation")
    if len(groups) != reference["candidate_groups"]["count"]:
        raise ValueError("06A aggregate group count mismatch")
    return row_to_group


def filter_records(rows, row_to_group):
    by_body = defaultdict(list)
    for record_id, row in enumerate(rows, 1):
        if audit.direction(row["description"]) == "missing":
            raise ValueError("Missing expected leading direction prefix")
        by_body[audit.body(row["description"])].append(record_id)
    labels = sorted({row["category"] for row in rows})
    stats = {label: {"raw": 0, "quarantined_conflict": 0, "duplicate_removed": 0, "retained": 0} for label in labels}
    records, decisions = [], []
    conflict_groups = 0
    for text, ids in by_body.items():
        if len({row_to_group[i] for i in ids}) != 1:
            raise ValueError("Same normalized body spans original groups")
        conflict = len({rows[i - 1]["category"] for i in ids}) > 1
        conflict_groups += conflict
        representative = min(ids)
        for record_id in ids:
            label = rows[record_id - 1]["category"]
            status = "quarantined_conflict" if conflict else "retained" if record_id == representative else "duplicate_removed"
            stats[label]["raw"] += 1
            stats[label][status] += 1
            decisions.append({"record_id": record_id, "status": status, "group_id": row_to_group[record_id],
                              "body_sha256": sha(text.encode()), "representative_id": None if conflict else representative})
        if not conflict:
            records.append({"record_id": representative, "text": text, "label": rows[representative - 1]["category"],
                            "group_id": row_to_group[representative], "body_sha256": sha(text.encode())})
    stats_total = {name: sum(stats[label][name] for label in labels) for name in ["raw", "quarantined_conflict", "duplicate_removed", "retained"]}
    if stats_total["raw"] != sum(stats_total[name] for name in ["quarantined_conflict", "duplicate_removed", "retained"]):
        raise ValueError("Filtering accounting mismatch")
    return sorted(records, key=lambda record: record["record_id"]), sorted(decisions, key=lambda d: d["record_id"]), {
        "conflicting_body_groups": conflict_groups, "body_keys_before_filter": len(by_body),
        "totals": stats_total, "by_label": stats,
        "original_groups_with_survivors": len({r["group_id"] for r in records}),
    }


def stratified_group_split(records, cfg):
    labels = sorted({record["label"] for record in records})
    indices = {label: i for i, label in enumerate(labels)}
    grouped = defaultdict(list)
    for record in records:
        grouped[record["group_id"]].append(record)
    vectors = {}
    for group_id, members in grouped.items():
        vector = np.zeros(len(labels), dtype=np.int64)
        for record in members:
            vector[indices[record["label"]]] += 1
        vectors[group_id] = vector
    totals = np.sum(list(vectors.values()), axis=0)
    ratios = np.array(cfg["split"]["ratios"])
    targets = ratios[:, None] * totals[None, :]
    sizes_target = ratios * len(records)
    counts = np.zeros_like(targets)
    sizes = np.zeros(3)
    denominator = totals.astype(float) ** 2
    # Difficult/large groups first, ties fixed by a seed-derived SHA, no model scores.
    order = sorted(vectors, key=lambda gid: (-float(np.max(vectors[gid] / totals)), -int(vectors[gid].sum()),
                                            sha(f"{cfg['seed']}|{gid}".encode()), gid))
    assignment = {}
    for gid in order:
        vector = vectors[gid]
        size = int(vector.sum())
        change = np.mean((2 * (counts - targets) * vector + vector ** 2) / denominator, axis=1)
        change += cfg["split"]["global_size_weight"] * (2 * (sizes - sizes_target) * size + size ** 2) / len(records) ** 2
        chosen = min(range(3), key=lambda i: (float(change[i]), i))
        assignment[gid] = cfg["split"]["names"][chosen]
        counts[chosen] += vector
        sizes[chosen] += size
    # Fixed pre-fit refinement: move whole groups only when the same count-based
    # objective improves. No model features, validation/test predictions or seed search.
    names = cfg["split"]["names"]
    for _ in range(cfg["split"]["local_move_passes"]):
        for gid in order:
            vector = vectors[gid]
            size = int(vector.sum())
            old = names.index(assignment[gid])
            remove = np.mean((-2 * (counts[old] - targets[old]) * vector + vector ** 2) / denominator)
            remove += cfg["split"]["global_size_weight"] * (-2 * (sizes[old] - sizes_target[old]) * size + size ** 2) / len(records) ** 2
            alternatives = []
            for new in range(3):
                if new == old:
                    continue
                add = np.mean((2 * (counts[new] - targets[new]) * vector + vector ** 2) / denominator)
                add += cfg["split"]["global_size_weight"] * (2 * (sizes[new] - sizes_target[new]) * size + size ** 2) / len(records) ** 2
                alternatives.append((float(remove + add), new))
            improvement, chosen = min(alternatives)
            if improvement < -1e-15:
                counts[old] -= vector
                sizes[old] -= size
                counts[chosen] += vector
                sizes[chosen] += size
                assignment[gid] = names[chosen]
    if np.any(counts == 0):
        raise ValueError("A class is absent from a partition; do not silently retry seeds")
    return assignment


def leakage_checks(records, rows, groups, pairs, assignment):
    original_id_to_group = {record_id: group["group_id"] for group in groups for record_id in group["record_ids"]}
    result = {"retained": {}, "projected_original": {}}
    funcs = {"exact": lambda text: text, "normalized": audit.normalize, "body": audit.body, "template": audit.template}
    for name, func in funcs.items():
        retained_keys = defaultdict(set)
        original_keys = defaultdict(set)
        for record in records:
            text = rows[record["record_id"] - 1]["description"]
            retained_keys[func(text)].add(assignment[record["group_id"]])
        for record_id, row in enumerate(rows, 1):
            gid = original_id_to_group[record_id]
            if gid in assignment:
                original_keys[func(row["description"])].add(assignment[gid])
        result["retained"][name] = sum(len(parts) > 1 for parts in retained_keys.values())
        result["projected_original"][name] = sum(len(parts) > 1 for parts in original_keys.values())
    violations = 0
    checked = 0
    for pair in pairs:
        left_gid = original_id_to_group[pair["left_record_id"]]
        right_gid = original_id_to_group[pair["right_record_id"]]
        if left_gid in assignment and right_gid in assignment:
            checked += 1
            violations += assignment[left_gid] != assignment[right_gid]
    result["near_edges_checked"] = checked
    result["near_edges_crossing"] = violations
    partition_groups = defaultdict(set)
    for record in records:
        partition_groups[assignment[record["group_id"]]].add(record["group_id"])
    names = sorted(partition_groups)
    result["group_id_overlap"] = sum(len(partition_groups[left] & partition_groups[right]) for i, left in enumerate(names) for right in names[i + 1:])
    if any(result["retained"].values()) or any(result["projected_original"].values()) or violations or result["group_id_overlap"]:
        raise ValueError("Split leakage check failed")
    return result


def inputs_and_preparation(cfg):
    source_path = SHARE / "classification-source.json"
    audit_path = SHARE / "classification-audit.json"
    source, reference = read_json(source_path), read_json(audit_path)
    raw = ROOT / source["local_raw_directory"]
    csv_path = raw / "transactions-synthetic.csv"
    groups_path = raw / "audit" / "candidate-groups.json"
    pairs_path = raw / "audit" / "near-pairs.json"
    if source["revision"] != EXPECTED_REVISION or reference["dataset_revision"] != EXPECTED_REVISION or file_sha(csv_path) != EXPECTED_CSV_SHA:
        raise ValueError("Pinned revision/CSV SHA mismatch")
    if file_sha(Path(audit.__file__)) != reference["script_sha256"]:
        raise ValueError("06A audit script changed since its results were recorded")
    rows = list(csv.DictReader(io.StringIO(csv_path.read_bytes().decode("utf-8-sig"), newline=""), strict=True))
    if not rows or any(set(row) != {"description", "category"} or any(value is None or not value.strip() for value in row.values()) for row in rows):
        raise ValueError("Unexpected CSV schema/missing value")
    groups, pairs = read_json(groups_path), read_json(pairs_path)
    mapping = verify_original_graph(rows, groups, pairs, reference)
    records, decisions, filtering = filter_records(rows, mapping)
    # Comparison to previous evidence, not a forced count or special-case exclusion.
    previous = reference["duplicates"]["without_direction"]
    if filtering["conflicting_body_groups"] != previous["conflicting_groups"] or filtering["totals"]["quarantined_conflict"] != previous["rows_in_conflicting_groups"]:
        raise ValueError("Recomputed conflicts differ from 06A evidence")
    assignment = stratified_group_split(records, cfg)
    checks = leakage_checks(records, rows, groups, pairs, assignment)
    manifest = [{key: value for key, value in record.items() if key != "text"} | {"partition": assignment[record["group_id"]]} for record in records]
    partitions = {name: [record for record in records if assignment[record["group_id"]] == name] for name in cfg["split"]["names"]}
    input_hashes = {str(path.relative_to(ROOT).as_posix()): file_sha(path) for path in
                    [CONFIG, Path(__file__), Path(audit.__file__), source_path, audit_path, csv_path, groups_path, pairs_path]}
    summary = {"source_revision": EXPECTED_REVISION, "source_sha256": EXPECTED_CSV_SHA,
               "filtering": filtering, "original_candidate_groups": len(groups), "known_near_edges": len(pairs),
               "split": {name: {"samples": len(part), "groups": len({r["group_id"] for r in part}),
                                "by_label": dict(sorted(Counter(r["label"] for r in part).items()))} for name, part in partitions.items()},
               "leakage_checks": checks, "split_seed": cfg["seed"], "target_ratios": cfg["split"]["ratios"],
               "merchant_holdout": False}
    return partitions, manifest, decisions, summary, input_hashes


def verify_lock(run):
    lock = read_json(run / "split-lock.json")
    if file_sha(run / "split-lock.json") != (run / "split-lock.sha256").read_text().strip():
        raise ValueError("Split lock receipt changed")
    for relative, expected in lock["input_hashes"].items():
        if file_sha(ROOT / relative) != expected:
            raise ValueError(f"Sealed experiment input changed: {relative}")
    for relative, expected in lock["local_hashes"].items():
        if file_sha(run / relative) != expected:
            raise ValueError(f"Sealed local artifact changed: {relative}")
    if runtime() != lock["runtime"]:
        raise ValueError("Runtime differs from sealed experiment")
    return lock


def prepare(run):
    if (run / "split-lock.json").exists():
        verify_lock(run)
        print("Existing test/split lock verified; not replaced.", flush=True)
        return
    if run.exists() and any(run.iterdir()):
        raise ValueError("Unsealed nonempty run directory; use a fresh directory")
    cfg = config()
    parts, manifest, decisions, summary, input_hashes = inputs_and_preparation(cfg)
    run.mkdir(parents=True, exist_ok=True)
    write_json(run / "config.json", cfg, exclusive=True)
    write_json(run / "manifest.json", manifest, exclusive=True)
    write_json(run / "row-decisions.json", decisions, exclusive=True)
    write_json(run / "data-summary.json", summary, exclusive=True)
    for name, records in parts.items():
        write_json(run / f"{name}.json", records, exclusive=True)
    local_names = ["config.json", "manifest.json", "row-decisions.json", "data-summary.json", "train.json", "validation.json", "test.json"]
    lock = {"experiment_id": cfg["experiment_id"], "locked_at_utc": now(), "runtime": runtime(),
            "input_hashes": input_hashes, "local_hashes": {name: file_sha(run / name) for name in local_names},
            "labels": sorted(summary["filtering"]["by_label"]),
            "test_use_policy": "Do not read test records/predict/score until validation-selection is locked; no refit after selection"}
    write_json(run / "split-lock.json", lock, exclusive=True)
    (run / "split-lock.sha256").write_text(file_sha(run / "split-lock.json") + "\n", encoding="utf-8")
    event(run, "split_and_test_locked", manifest_sha256=file_sha(run / "manifest.json"), split_lock_sha256=file_sha(run / "split-lock.json"))
    write_json(SHARE / "classification-experiment-data.json", summary | {"manifest_sha256": file_sha(run / "manifest.json"),
               "split_lock_sha256": file_sha(run / "split-lock.json"), "locked_at_utc": lock["locked_at_utc"],
               "original_candidate_groups_sha256": input_hashes[next(key for key in input_hashes if key.endswith("candidate-groups.json"))],
               "local_run_directory": run.relative_to(ROOT).as_posix()})
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


def make_pipeline(family, c, cfg):
    if family == "dummy":
        return Pipeline([("classifier", DummyClassifier(**cfg["dummy"], random_state=cfg["seed"]))])
    vector_args = dict(cfg["word_tfidf"] if family == "word_logreg" else cfg["char_tfidf"])
    vector_args["ngram_range"] = tuple(vector_args["ngram_range"])
    if family == "word_logreg":
        classifier = LogisticRegression(C=c, random_state=cfg["seed"], **cfg["logreg"])
    elif family == "char_linearsvc":
        classifier = LinearSVC(C=c, random_state=cfg["seed"], **cfg["linearsvc"])
    else:
        raise ValueError("Unknown model family")
    return Pipeline([("tfidf", TfidfVectorizer(**vector_args)), ("classifier", classifier)])


def candidate_id(family, c):
    return family if c is None else family + "_C_" + str(c).replace(".", "p")


def choose_candidate(candidates, cfg):
    learned = [item for item in candidates if item["family"] != "dummy"]
    return min(learned, key=lambda item: (-item["validation_macro_f1"], item["C"], cfg["family_order"].index(item["family"])))


def train(run):
    lock = verify_lock(run)
    if (run / "test-opened.json").exists():
        raise ValueError("Test already opened; training/selection cannot be changed")
    if (run / "validation-selection.json").exists():
        verify_selection(run)
        print("Validation selection already sealed; no additional fits.", flush=True)
        return
    cfg = config()
    train_rows, val_rows = read_json(run / "train.json"), read_json(run / "validation.json")
    # Intentionally no read_json(test.json) in this phase.
    x_train, y_train = [r["text"] for r in train_rows], [r["label"] for r in train_rows]
    x_val, y_val = [r["text"] for r in val_rows], [r["label"] for r in val_rows]
    jobs = [("dummy", None)] + [(family, c) for family in cfg["family_order"] for c in cfg["C_values"]]
    candidates = []
    (run / "models").mkdir(exist_ok=True)
    (run / "candidates").mkdir(exist_ok=True)
    event(run, "validation_search_started", candidates=len(jobs), test_records_read=False)
    with threadpoolctl.threadpool_limits(limits=cfg["thread_limit"]):
        for family, c in jobs:
            identifier = candidate_id(family, c)
            checkpoint = run / "candidates" / f"{identifier}.json"
            model_path = run / "models" / f"{identifier}.joblib"
            if checkpoint.exists():
                result = read_json(checkpoint)
                if result["split_lock_sha256"] != file_sha(run / "split-lock.json") or file_sha(model_path) != result["model_sha256"]:
                    raise ValueError("Candidate checkpoint does not match sealed experiment")
                candidates.append(result)
                print("Resumed completed candidate", identifier, flush=True)
                continue
            estimator = make_pipeline(family, c, cfg)
            started = now()
            tick = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                estimator.fit(x_train, y_train)
            fit_seconds = time.perf_counter() - tick
            predictions = estimator.predict(x_val)
            classifier = estimator.named_steps["classifier"]
            iterations = getattr(classifier, "n_iter_", None)
            result = {"candidate_id": identifier, "family": family, "C": c,
                      "fit_started_at_utc": started, "fit_seconds": fit_seconds,
                      "validation_macro_f1": float(f1_score(y_val, predictions, labels=lock["labels"], average="macro", zero_division=0)),
                      "validation_accuracy": float(accuracy_score(y_val, predictions)),
                      "warnings": [{"category": type(w.message).__name__, "message": str(w.message)} for w in caught],
                      "iterations": None if iterations is None else np.asarray(iterations).tolist(),
                      "feature_count": len(estimator.named_steps["tfidf"].vocabulary_) if "tfidf" in estimator.named_steps else 0,
                      "model_path": model_path.relative_to(run).as_posix(),
                      "split_lock_sha256": file_sha(run / "split-lock.json")}
            joblib.dump(estimator, model_path, compress=3)
            result["model_sha256"] = file_sha(model_path)
            write_json(checkpoint, result, exclusive=True)
            candidates.append(result)
            event(run, "candidate_validation_complete", candidate=identifier, validation_macro_f1=result["validation_macro_f1"], fit_seconds=fit_seconds)
            print(json.dumps({key: result[key] for key in ["candidate_id", "fit_seconds", "validation_accuracy", "validation_macro_f1", "feature_count", "warnings"]}), flush=True)
    selected = choose_candidate(candidates, cfg)
    selection = {"selected_at_utc": now(), "split_lock_sha256": file_sha(run / "split-lock.json"),
                 "rule": cfg["selection"], "test_records_read_for_selection": False,
                 "refit_train_validation": False, "candidates": candidates,
                 "best_per_family": {family: choose_candidate([r for r in candidates if r["family"] == family], cfg)["candidate_id"] for family in cfg["family_order"]},
                 "selected_candidate_id": selected["candidate_id"], "selected_model_sha256": selected["model_sha256"]}
    write_json(run / "validation-selection.json", selection, exclusive=True)
    (run / "validation-selection.sha256").write_text(file_sha(run / "validation-selection.json") + "\n", encoding="utf-8")
    event(run, "validation_selection_locked", selected=selected["candidate_id"], selection_sha256=file_sha(run / "validation-selection.json"))
    print("Selected using validation only:", selected["candidate_id"], flush=True)


def verify_selection(run):
    selection = read_json(run / "validation-selection.json")
    if file_sha(run / "validation-selection.json") != (run / "validation-selection.sha256").read_text().strip():
        raise ValueError("Validation selection receipt changed")
    if selection["split_lock_sha256"] != file_sha(run / "split-lock.json"):
        raise ValueError("Selection/split mismatch")
    chosen = choose_candidate(selection["candidates"], config())
    if chosen["candidate_id"] != selection["selected_candidate_id"]:
        raise ValueError("Selection violates predeclared rule")
    for candidate in selection["candidates"]:
        if file_sha(run / candidate["model_path"]) != candidate["model_sha256"]:
            raise ValueError("Candidate model checksum mismatch")
    return selection


def evaluate(run):
    lock = verify_lock(run)
    selection = verify_selection(run)
    if (run / "test-results.json").exists():
        print("Final test results already exist; not predicting test again.", flush=True)
        return
    cfg = config()
    selected = selection["selected_candidate_id"]
    opening = {"opened_at_utc": now(), "selection_sha256": file_sha(run / "validation-selection.json"),
               "split_lock_sha256": file_sha(run / "split-lock.json"), "selected_candidate_id": selected}
    if (run / "test-opened.json").exists():
        previous = read_json(run / "test-opened.json")
        if previous["selection_sha256"] != opening["selection_sha256"]:
            raise ValueError("Cannot resume test with another selection")
        event(run, "fixed_selection_evaluation_resumed")
    else:
        write_json(run / "test-opened.json", opening, exclusive=True)
        event(run, "test_opened_after_selection", selection_sha256=opening["selection_sha256"])
    # The test records are first parsed here, after the immutable selection receipt.
    test_rows = read_json(run / "test.json")
    x_test, y_test = [r["text"] for r in test_rows], [r["label"] for r in test_rows]
    result = {"evaluated_at_utc": now(), "runtime": runtime(), "source_revision": EXPECTED_REVISION,
              "source_sha256": EXPECTED_CSV_SHA, "manifest_sha256": file_sha(run / "manifest.json"),
              "split_lock_sha256": file_sha(run / "split-lock.json"), "selection_sha256": opening["selection_sha256"],
              "selected_candidate_id": selected, "test_support": len(y_test), "labels": lock["labels"],
              "selection": selection, "models": {}, "merchant_holdout": False, "probability_calibration": "not performed; decision_function not used as probability"}
    local_predictions = {}
    with threadpoolctl.threadpool_limits(limits=cfg["thread_limit"]):
        for identifier in ["dummy", selected]:
            candidate = next(c for c in selection["candidates"] if c["candidate_id"] == identifier)
            estimator = joblib.load(run / candidate["model_path"])
            tick = time.perf_counter()
            predicted = estimator.predict(x_test)
            predict_seconds = time.perf_counter() - tick
            report = classification_report(y_test, predicted, labels=lock["labels"], output_dict=True, zero_division=0)
            result["models"][identifier] = {"accuracy": float(accuracy_score(y_test, predicted)),
                "macro_f1": float(f1_score(y_test, predicted, labels=lock["labels"], average="macro", zero_division=0)),
                "classification_report": report, "confusion_matrix": confusion_matrix(y_test, predicted, labels=lock["labels"]).tolist(),
                "fit_seconds": candidate["fit_seconds"], "predict_seconds": predict_seconds,
                "model_sha256": candidate["model_sha256"], "errors": int(np.sum(np.asarray(y_test) != predicted))}
            local_predictions[identifier] = [{"record_id": r["record_id"], "group_id": r["group_id"], "true": r["label"],
                                              "predicted": str(prediction), "text": r["text"]} for r, prediction in zip(test_rows, predicted)]
    selected_errors = [r for r in local_predictions[selected] if r["true"] != r["predicted"]]
    error_sample = sorted(selected_errors, key=lambda r: sha(f"{cfg['error_sample']['seed']}|{r['record_id']}".encode()))[:cfg["error_sample"]["count"]]
    write_json(run / "test-predictions.json", local_predictions, exclusive=True)
    write_json(run / "error-sample.json", error_sample, exclusive=True)
    # Public metadata contains error IDs/labels only, never a transaction dataset.
    result["error_sample"] = [{key: value for key, value in r.items() if key not in {"text", "group_id"}} for r in error_sample]
    write_json(run / "test-results.json", result, exclusive=True)
    (run / "test-results.sha256").write_text(file_sha(run / "test-results.json") + "\n", encoding="utf-8")
    event(run, "final_test_complete", selected=selected, test_support=len(y_test), results_sha256=file_sha(run / "test-results.json"))
    write_json(SHARE / "classification-experiment-results.json", result)
    lines = ["# TASK 06B — Ma trận nhầm lẫn trên test khóa trước huấn luyện", "",
             "Hàng = nhãn thật; cột = nhãn dự đoán. Ô là số mẫu, không phải xác suất. Chỉ đánh giá Dummy và mô hình đã chọn bằng validation.", "",
             "| Mã | Nhãn |", "|---|---|"]
    codes = [f"L{i + 1:02d}" for i in range(len(lock["labels"]))]
    lines += [f"| {code} | {label} |" for code, label in zip(codes, lock["labels"])]
    for identifier, scores in result["models"].items():
        lines += ["", f"## {identifier}", "", "| Thật / Dự đoán | " + " | ".join(codes) + " |",
                  "|---|" + "---:|" * len(codes)]
        lines += ["| " + code + " | " + " | ".join(str(n) for n in counts) + " |" for code, counts in zip(codes, scores["confusion_matrix"])]
    (SHARE / "classification-test-confusion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({identifier: {key: scores[key] for key in ["accuracy", "macro_f1", "errors", "fit_seconds"]} for identifier, scores in result["models"].items()}, indent=2), flush=True)


def verify(run):
    lock = verify_lock(run)
    parts, manifest, decisions, summary, hashes = inputs_and_preparation(config())
    if hashes != lock["input_hashes"] or json_bytes(manifest) != (run / "manifest.json").read_bytes() or json_bytes(decisions) != (run / "row-decisions.json").read_bytes():
        raise ValueError("Preparation is not deterministic")
    if json_bytes(summary) != (run / "data-summary.json").read_bytes():
        raise ValueError("Summary differs from sealed preparation")
    for name, records in parts.items():
        if json_bytes(records) != (run / f"{name}.json").read_bytes():
            raise ValueError("Partition changed")
    if (run / "validation-selection.json").exists():
        verify_selection(run)
    if (run / "test-results.json").exists():
        if file_sha(run / "test-results.json") != (run / "test-results.sha256").read_text().strip():
            raise ValueError("Final result receipt changed")
        result = read_json(run / "test-results.json")
        if result["manifest_sha256"] != file_sha(run / "manifest.json") or result["selection_sha256"] != file_sha(run / "validation-selection.json"):
            raise ValueError("Test result provenance mismatch")
        for scores in result["models"].values():
            matrix = np.array(scores["confusion_matrix"])
            if int(matrix.sum()) != result["test_support"] or not np.isclose(matrix.trace() / matrix.sum(), scores["accuracy"]):
                raise ValueError("Confusion matrix/metric mismatch")
    print("PASS: original groups, preparation, manifest, split integrity and provenance verified; no fitting or test prediction.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "train", "evaluate", "verify"])
    parser.add_argument("--run-dir", default="data/experiments/classification/task06b-v1-final")
    options = parser.parse_args()
    run_path = (ROOT / options.run_dir).resolve()
    if not run_path.is_relative_to(RUN_BASE.resolve()) or run_path == RUN_BASE.resolve():
        parser.error("Run directory must be a child of ignored data/experiments/classification/")
    {"prepare": prepare, "train": train, "evaluate": evaluate, "verify": verify}[options.phase](run_path)
