"""Unit fixtures only: normalization/filtering/group split/selection/leakage.

No real data access, model fitting, network or website modifications.
"""
import unittest
from copy import deepcopy

from run_classification_experiment import (
    choose_candidate, config, filter_records, leakage_checks, make_pipeline,
    sha, stratified_group_split,
)
import audit_classification_data as audit
from run_classification_windows import handles_only


class ClassificationExperimentTests(unittest.TestCase):
    def test_unicode_adapter_keeps_handles_and_discards_only_snapshot_paths(self):
        modules = [(123, "broken path"), (456, "another path")]
        self.assertEqual(handles_only(modules), [(123, ""), (456, "")])
        self.assertEqual(modules[0][1], "broken path")

    def test_unicode_adapter_preserves_snapshot_failure_fallback(self):
        self.assertIsNone(handles_only(None))
    def test_prefix_is_removed_only_at_start(self):
        self.assertEqual(audit.body(" [CREDIT]  A  B "), "a b")
        self.assertEqual(audit.body("A [credit] B"), "a [credit] b")

    def test_filter_quarantines_all_conflict_rows_before_dedup(self):
        rows = [{"description": d, "category": c} for d, c in [
            ("[debit] A", "X"), ("[credit] a", "Y"), ("[debit] A", "X"),
            ("[credit] B", "Y"), ("[debit] b ", "Y"), ("[debit] C", "X")]]
        mapping = {1: "original-A", 2: "original-A", 3: "original-A",
                   4: "original-B", 5: "original-B", 6: "original-C"}
        kept, decisions, stats = filter_records(rows, mapping)
        self.assertEqual(stats["conflicting_body_groups"], 1)
        self.assertEqual(stats["totals"], {"raw": 6, "quarantined_conflict": 3, "duplicate_removed": 1, "retained": 2})
        self.assertEqual([r["record_id"] for r in kept], [4, 6])
        self.assertEqual([r["group_id"] for r in kept], ["original-B", "original-C"])
        self.assertEqual([r["text"] for r in kept], ["b", "c"])
        self.assertTrue(all(d["representative_id"] is None for d in decisions[:3]))

    def test_same_body_cannot_get_rebuilt_group_ids(self):
        rows = [{"description": "[debit] A", "category": "X"}, {"description": "[credit] a", "category": "X"}]
        with self.assertRaises(ValueError):
            filter_records(rows, {1: "a", 2: "different"})

    def test_group_split_is_deterministic_and_approximately_stratified(self):
        records = [{"record_id": i * 2 + j + 1, "text": str(i), "label": label, "group_id": f"g-{i}"}
                   for i in range(100) for j, label in enumerate(["X", "Y"])]
        cfg = config()
        first = stratified_group_split(records, cfg)
        second = stratified_group_split(list(reversed(records)), cfg)
        self.assertEqual(first, second)
        for label in ["X", "Y"]:
            counts = {part: sum(r["label"] == label and first[r["group_id"]] == part for r in records) for part in cfg["split"]["names"]}
            self.assertEqual(counts, {"train": 70, "validation": 15, "test": 15})

    def test_selection_uses_macro_f1_then_fixed_ties(self):
        cfg = config()
        candidates = [
            {"candidate_id": "dummy", "family": "dummy", "C": None, "validation_macro_f1": 1.0},
            {"candidate_id": "word1", "family": "word_logreg", "C": 1., "validation_macro_f1": .8},
            {"candidate_id": "char1", "family": "char_linearsvc", "C": 1., "validation_macro_f1": .8},
            {"candidate_id": "char01", "family": "char_linearsvc", "C": .1, "validation_macro_f1": .8}]
        self.assertEqual(choose_candidate(candidates, cfg)["candidate_id"], "char01")
        self.assertEqual(choose_candidate(candidates[:3], cfg)["candidate_id"], "word1")

    def test_known_template_leakage_raises(self):
        rows = [{"description": "[debit] A #123", "category": "X"}, {"description": "[debit] A #456", "category": "X"}]
        records = [{"record_id": 1, "group_id": "g1"}, {"record_id": 2, "group_id": "g2"}]
        groups = [{"group_id": "g1", "record_ids": [1]}, {"group_id": "g2", "record_ids": [2]}]
        with self.assertRaises(ValueError):
            leakage_checks(records, rows, groups, [], {"g1": "train", "g2": "test"})

    def test_pipeline_configs_have_no_test_fit_or_probability_calibrator(self):
        cfg = config()
        word = make_pipeline("word_logreg", .1, cfg)
        char = make_pipeline("char_linearsvc", 10., cfg)
        self.assertEqual(list(word.named_steps), ["tfidf", "classifier"])
        self.assertEqual(char.named_steps["tfidf"].analyzer, "char_wb")
        self.assertEqual(char.named_steps["classifier"].C, 10.)
        self.assertNotIn("calibrator", char.named_steps)
        self.assertFalse(cfg["refit_train_validation"])


if __name__ == "__main__":
    unittest.main()
