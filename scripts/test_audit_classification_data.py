"""In-memory logic fixtures only; no dataset, Django or network access."""
import unittest

from audit_classification_data import (
    UnionFind, body, direction, duplicate_stats, fixed_samples, normalize, template,
)


class AuditLogicTests(unittest.TestCase):
    def test_whitespace_and_case(self):
        self.assertEqual(normalize("  A\t B\nC  "), "a b c")

    def test_punctuation_is_not_removed_by_basic_normalization(self):
        self.assertNotEqual(normalize("A*B"), normalize("A B"))

    def test_unicode_canonical_equivalence(self):
        self.assertEqual(normalize("e\u0301"), normalize("é"))

    def test_direction_only_at_start(self):
        self.assertEqual(direction(" [CrEdIt] A"), "credit")
        self.assertEqual(direction("A [credit]"), "missing")
        self.assertEqual(body("[debit] A  B"), body("[credit] a b"))

    def test_duplicate_counts_distinguish_groups_rows_and_excess(self):
        stats, _, conflicts = duplicate_stats(["a", "a", "a", "b"], ["X", "X", "Y", "Y"])
        self.assertEqual(stats["duplicate_groups"], 1)
        self.assertEqual(stats["rows_in_duplicate_groups"], 3)
        self.assertEqual(stats["excess_rows"], 2)
        self.assertEqual(stats["rows_in_conflicting_groups"], 3)
        self.assertEqual(conflicts, [[0, 1, 2]])

    def test_template_masks_references_and_preserves_words(self):
        self.assertEqual(template("[debit] A*X12Y"), template("[credit] a*Z34W"))
        self.assertNotEqual(template("A 123"), template("B 456"))
        self.assertEqual(template("A #123"), template("A 456"))

    def test_template_bank_reference_fields(self):
        self.assertEqual(template("A WEB ID: X12Y"), template("A WEB ID: ABCD"))
        self.assertEqual(template("A PPD ID: 123"), template("A PPD ID: 456"))

    def test_group_transitivity(self):
        groups = UnionFind(4)
        groups.union(0, 1)
        groups.union(2, 3)
        groups.union(1, 3)
        self.assertEqual(len({groups.find(i) for i in range(4)}), 1)

    def test_fixed_samples_are_deterministic_and_distinct(self):
        rows = [{"description": text, "category": label}
                for text, label in [(" A ", "X"), ("a", "X"), ("B", "X"), ("A", "Y")]]
        first = fixed_samples(rows, count=5)
        self.assertEqual(first, fixed_samples(rows, count=5))
        self.assertEqual(len(first["X"]), 2)
        self.assertEqual(len(first["Y"]), 1)
        self.assertIn(1, [item["record_id"] for item in first["X"]])
        self.assertNotIn(2, [item["record_id"] for item in first["X"]])


if __name__ == "__main__":
    unittest.main()
