"""Logic fixtures only; no network, transaction workbook or estimator fitting."""
import unittest
import numpy as np

from run_forecast_experiment import (
    baseline_raw, calendar_months, choose_alpha, clip_prediction, config,
    features_at, make_pipeline, require_contiguous, schedule_for, scores, training_data,
)


class ForecastExperimentTests(unittest.TestCase):
    def test_features_use_exact_prescribed_past_lags(self):
        y = list(range(1, 84))
        np.testing.assert_array_equal(features_at(y, 59), [59, 58, 57, 48, 58])

    def test_future_and_target_mutations_do_not_change_training_or_features(self):
        a = list(range(1, 84)); b = a[:59] + [999999] * 24
        np.testing.assert_array_equal(features_at(a, 59), features_at(b, 59))
        xa, ya = training_data(a, 59); xb, yb = training_data(b, 59)
        np.testing.assert_array_equal(xa, xb); np.testing.assert_array_equal(ya, yb)
        self.assertEqual(len(ya), 47)

    def test_expanding_window_includes_new_actual_only_on_next_origin(self):
        y = list(range(1, 84))
        self.assertEqual(len(training_data(y, 71)[1]), 59)
        self.assertEqual(len(training_data(y, 82)[1]), 70)
        self.assertEqual(features_at(y, 60)[0], y[59])

    def test_missing_calendar_month_is_rejected(self):
        months = calendar_months("2015-08", "2022-06")
        require_contiguous(months, "2015-08", "2022-06")
        del months[30]
        with self.assertRaises(ValueError):
            require_contiguous(months, "2015-08", "2022-06")

    def test_missing_numeric_history_is_not_imputed(self):
        y = np.arange(83, dtype=float); y[20] = np.nan
        with self.assertRaises(ValueError):
            features_at(y, 59)

    def test_baselines_are_past_only(self):
        y = list(range(1, 84))
        self.assertEqual(baseline_raw("previous_month", y, 59), 59)
        self.assertEqual(baseline_raw("mean_previous_3", y, 59), 58)
        self.assertEqual(baseline_raw("same_month_previous_year", y, 59), 48)

    def test_clipping_happens_before_scoring_and_bias_is_pred_minus_actual(self):
        prediction = clip_prediction(-4., config())
        result = scores([{"predicted": prediction, "observed": 2., "raw_prediction": -4.}])
        self.assertEqual(result["mae"], 2.)
        self.assertEqual(result["median_absolute_error"], 2.)
        self.assertEqual(result["signed_bias"], -2.)
        self.assertEqual(result["negative_predictions_clipped"], 1)

    def test_alpha_selection_min_mae_then_lower_alpha(self):
        candidates = [{"alpha": a, "scores": {"mae": m}} for a, m in [(10., 2.), (1., 1.), (.1, 1.)]]
        self.assertEqual(choose_alpha(candidates), .1)

    def test_schedule_is_12_validation_12_test_with_no_future_targets(self):
        schedule = schedule_for(calendar_months("2015-08", "2022-06"), config())
        self.assertEqual(len(schedule), 24)
        self.assertEqual(schedule[0]["target_month"], "2020-07")
        self.assertEqual(schedule[0]["training_samples"], 47)
        self.assertEqual(schedule[12]["target_month"], "2021-07")
        self.assertEqual(schedule[-1]["training_samples"], 70)
        self.assertTrue(all(s["history_end"] < s["target_month"] for s in schedule))

    def test_pipeline_has_scaler_then_ridge_and_fixed_alpha(self):
        model = make_pipeline(10., config())
        self.assertEqual(list(model.named_steps), ["scaler", "ridge"])
        self.assertEqual(model.named_steps["ridge"].alpha, 10.)
        self.assertEqual(model.named_steps["ridge"].solver, "cholesky")


if __name__ == "__main__":
    unittest.main()
