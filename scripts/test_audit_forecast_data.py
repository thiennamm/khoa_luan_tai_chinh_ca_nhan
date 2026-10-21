"""Logic-only fixtures; no transaction data, database, training or network."""
import unittest
from datetime import date
from decimal import Decimal

from audit_forecast_data import duplicate_counts, excel_date, money, month_keys, parse_date, temporal_plan


class ForecastAuditLogicTests(unittest.TestCase):
    def test_excel_1900_leap_bug_boundary(self):
        self.assertEqual(excel_date("1"), date(1900, 1, 1))
        self.assertEqual(excel_date("59"), date(1900, 2, 28))
        with self.assertRaises(ValueError):
            excel_date("60")
        self.assertEqual(excel_date("61"), date(1900, 3, 1))

    def test_excel_1904_epoch(self):
        self.assertEqual(excel_date("0", True), date(1904, 1, 1))

    def test_date_rejects_fractional_serial(self):
        with self.assertRaises(ValueError):
            excel_date("44000.5")

    def test_text_date_is_strict_dmy(self):
        self.assertEqual(parse_date({"type": "s", "value": "31/01/2020"}), date(2020, 1, 31))
        with self.assertRaises(ValueError):
            parse_date({"type": "s", "value": "31/02/2020"})

    def test_numeric_swap_is_explicit_and_does_not_change_cell(self):
        cell = {"type": "n", "value": "42013"}
        self.assertEqual(parse_date(cell), date(2015, 1, 9))
        self.assertEqual(parse_date(cell, swap_numeric=True), date(2015, 9, 1))
        self.assertEqual(cell["value"], "42013")

    def test_decimal_rounding_and_blank_are_separate(self):
        self.assertIsNone(money(" "))
        self.assertEqual(money("0"), Decimal("0.00"))
        self.assertEqual(money("1.005"), Decimal("1.01"))
        self.assertEqual(money("2.2999999999999998"), Decimal("2.30"))
        with self.assertRaises(ValueError):
            money("NaN")

    def test_month_keys_do_not_skip_year_boundary(self):
        self.assertEqual(list(month_keys(date(2020, 12, 15), date(2021, 2, 2))), ["2020-12", "2021-01", "2021-02"])

    def test_duplicate_candidate_counts(self):
        stats, _ = duplicate_counts([("a",), ("a",), ("a",), ("b",)])
        self.assertEqual(stats, {"duplicate_groups": 1, "rows_in_groups": 3, "excess_rows": 2})

    def test_time_plan_preserves_missing_calendar_break(self):
        months = [{"month": key, "transactions": 1} for key in month_keys(date(2010, 1, 1), date(2016, 12, 1))]
        months[40]["transactions"] = None
        plan = temporal_plan(months)
        self.assertEqual(plan["interior_months_with_rows"], 81)
        self.assertEqual(plan["longest_interior_calendar_run_with_rows"], 42)
        self.assertNotIn("conditional_split", plan)
        self.assertEqual(months[40]["transactions"], None)
        self.assertEqual(plan["approved_forecast_origins"], 0)

    def test_time_plan_83_months_59_12_12_and_47_origins(self):
        months = [{"month": key, "transactions": 1} for key in month_keys(date(2015, 7, 1), date(2022, 7, 1))]
        plan = temporal_plan(months)
        self.assertEqual(plan["longest_interior_calendar_run_with_rows"], 83)
        self.assertEqual(plan["conditional_split"]["train"], {"start": "2015-08", "end": "2020-06", "months": 59})
        self.assertEqual(plan["maximum_conditional_one_step_origins"], 47)
        self.assertEqual(plan["conditional_split"]["test"]["months"], 12)


if __name__ == "__main__":
    unittest.main()
