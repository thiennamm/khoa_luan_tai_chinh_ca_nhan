"""TASK 07B, conditional exploratory expanding-window experiment, offline.

Raw workbook stays untouched; versioned derived data and models remain in data/.
No transaction descriptions, locations or website data are exported.
"""
import argparse
import hashlib
import json
import math
import platform
import time
import warnings
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
import threadpoolctl
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import audit_forecast_data as audit
import run_classification_windows as compatibility

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "experiments" / "forecast-v1.json"
META = ROOT / "docs" / "metadata"
RUN_BASE = ROOT / "data" / "experiments" / "forecast"
DEFAULT_RUN = RUN_BASE / "task07b-v1"
FEATURES = ["lag_1", "lag_2", "lag_3", "lag_12", "mean_previous_3"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
        handle.write(json.dumps({"at_utc": now(), "event": name, **fields}) + "\n")


def receipt(run, name, value):
    path = run / f"{name}.json"
    write_json(path, value, exclusive=True)
    (run / f"{name}.sha256").write_text(sha(path) + "\n", encoding="utf-8")


def check_receipt(run, name):
    path = run / f"{name}.json"
    if sha(path) != (run / f"{name}.sha256").read_text().strip():
        raise ValueError(f"Changed receipt: {name}")
    return read_json(path)


def runtime():
    return {"python": platform.python_version(), "scikit-learn": sklearn.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__, "joblib": joblib.__version__,
            "threadpoolctl": threadpoolctl.__version__, "platform": platform.platform()}


def config():
    cfg = read_json(CONFIG)
    if cfg["source_sha256"] != audit.EXPECTED_SHA or cfg["date_branch"] != "swap_numeric_month_day_hypothesis":
        raise ValueError("Unexpected source/date branch")
    if cfg["features"] != FEATURES or cfg["alpha_values"] != [0.1, 1.0, 10.0] or cfg["warmup_months"] != 12:
        raise ValueError("This first experiment uses only the prescribed features/alphas")
    if not cfg["keep_all_debits"] or not cfg["keep_duplicate_candidates"] or cfg["remove_large_amounts"]:
        raise ValueError("Debit exclusion is not allowed")
    if cfg["clip_prediction_lower_bound"] != 0 or cfg["forecast_horizon_months"] != 1:
        raise ValueError("Unexpected clipping or forecast horizon")
    return cfg


def calendar_months(start, end):
    return list(audit.month_keys(date.fromisoformat(start + "-01"), date.fromisoformat(end + "-01")))


def require_contiguous(months, start, end):
    if months != calendar_months(start, end):
        raise ValueError("Missing/duplicate/out-of-order calendar month; never fill with zero")


def derive(cfg):
    source_path, audit_path = META / "forecast-source.json", META / "forecast-audit.json"
    source, previous = read_json(source_path), read_json(audit_path)
    if source["version"] != 1 or source["sha256"] != cfg["source_sha256"]:
        raise ValueError("Not the audited MoneyData V1 source")
    if sha(Path(audit.__file__)) != previous["script_sha256"]:
        raise ValueError("Audit script changed since recorded audit")
    sheets, epoch = audit.workbook()  # Also verifies pinned raw SHA-256.
    rows = [row for row in sheets[0]["rows"][1:] if any(c["value"].strip() for c in row["cells"].values())]
    months = defaultdict(lambda: {"transactions": 0, "debit_transactions": 0, "total": Decimal("0.00")})
    lineage = []
    for row in rows:
        d = audit.parse_date(row["cells"]["B"], epoch, swap_numeric=True)
        key = d.strftime("%Y-%m")
        amount = audit.money(row["cells"]["E"]["value"])
        months[key]["transactions"] += 1
        if amount is not None:
            if amount <= 0:
                raise ValueError("Unexpected non-positive source debit; do not silently remove")
            months[key]["debit_transactions"] += 1
            months[key]["total"] += amount
            lineage.append({"excel_row": row["row"], "assumed_month": key, "debit": str(amount),
                            "included": cfg["series_start"] <= key <= cfg["series_end"],
                            "reason": "retained" if cfg["series_start"] <= key <= cfg["series_end"] else "boundary_month"})
    all_months = [{"month": key, "observed_debit_total": str(item["total"]),
                   "transactions": item["transactions"], "debit_transactions": item["debit_transactions"],
                   "coverage": "unknown"} for key, item in sorted(months.items())]
    reference = previous["date_branches"][cfg["date_branch"]]["monthly"]
    if len(all_months) != len(reference):
        raise ValueError("Derived months differ from prior audit")
    for item, old in zip(all_months, reference):
        if any(item[key] != old[key] for key in ["month", "transactions", "debit_transactions", "observed_debit_total"]):
            raise ValueError("Derived count/amount differs from prior audit")
    excluded = [item["month"] for item in all_months if not cfg["series_start"] <= item["month"] <= cfg["series_end"]]
    if excluded != cfg["excluded_boundary_months"]:
        raise ValueError("Unexpected excluded months")
    kept = [item for item in all_months if cfg["series_start"] <= item["month"] <= cfg["series_end"]]
    require_contiguous([item["month"] for item in kept], cfg["series_start"], cfg["series_end"])
    derived = {"derived_version": cfg["derived_version"], "source_sha256": cfg["source_sha256"],
               "date_branch": cfg["date_branch"], "author_confirmed": False, "currency": None,
               "coverage_fully_confirmed": False, "target": cfg["target"], "months": kept}
    summary = {"raw_transactions": len(rows), "all_observed_months": len(all_months),
               "all_debit_rows": len(lineage), "all_debit_total": str(sum((Decimal(item["debit"]) for item in lineage), Decimal("0.00"))),
               "kept_months": len(kept), "kept_transactions": sum(item["transactions"] for item in kept),
               "kept_debit_rows": sum(item["debit_transactions"] for item in kept),
               "kept_debit_total": str(sum((Decimal(item["observed_debit_total"]) for item in kept), Decimal("0.00"))),
               "excluded_boundaries": [item for item in all_months if item["month"] in excluded],
               "missing_months": [], "deduplication_applied": False, "outlier_removal_applied": False}
    paths = [CONFIG, Path(__file__), Path(audit.__file__), Path(compatibility.__file__), Path(threadpoolctl.__file__),
             source_path, audit_path, ROOT / "docs" / "forecast-data-audit.md", META / "forecast-monthly-summary.md", audit.RAW / audit.FILENAME,
             ROOT / "requirements.txt"]
    hashes = {path.relative_to(ROOT).as_posix(): sha(path) for path in paths}
    return derived, all_months, lineage, summary, hashes


def features_at(values, target_index):
    if target_index < 12 or target_index > len(values):
        raise ValueError("Twelve past calendar months are required")
    past = np.asarray(values[:target_index], dtype=np.float64)
    if not np.all(np.isfinite(past)):
        raise ValueError("Missing/non-finite past values are not imputed")
    return np.array([past[-1], past[-2], past[-3], past[-12], np.mean(past[-3:])], dtype=np.float64)


def training_data(values, target_index):
    if target_index <= 12:
        raise ValueError("No supervised training rows after lag warmup")
    x = np.array([features_at(values, i) for i in range(12, target_index)])
    y = np.asarray(values[12:target_index], dtype=np.float64)
    return x, y


def baseline_raw(name, values, target_index):
    x = features_at(values, target_index)
    return float({"previous_month": x[0], "mean_previous_3": x[4], "same_month_previous_year": x[3]}[name])


def clip_prediction(raw, cfg):
    if not math.isfinite(raw):
        raise ValueError("Non-finite prediction")
    return max(cfg["clip_prediction_lower_bound"], float(raw))


def scores(predictions):
    if not predictions:
        raise ValueError("No forecast origins")
    residuals = np.array([p["predicted"] - p["observed"] for p in predictions])
    return {"mae": float(np.mean(np.abs(residuals))),
            "median_absolute_error": float(np.median(np.abs(residuals))),
            "signed_bias": float(np.mean(residuals)), "origins": len(predictions),
            "negative_predictions_clipped": sum(p["raw_prediction"] < 0 for p in predictions)}


def make_pipeline(alpha, cfg):
    return Pipeline([("scaler", StandardScaler(**cfg["standard_scaler"])),
                     ("ridge", Ridge(alpha=alpha, random_state=cfg["seed"], **cfg["ridge"]))])


def choose_alpha(candidates):
    return min(candidates, key=lambda c: (c["scores"]["mae"], c["alpha"]))["alpha"]


def schedule_for(months, cfg):
    schedule = []
    for part in ["validation", "test"]:
        for month in calendar_months(cfg[part]["start"], cfg[part]["end"]):
            index = months.index(month)
            schedule.append({"partition": part, "target_month": month, "target_index": index,
                             "history_start": months[0], "history_end": months[index - 1], "history_months": index,
                             "first_training_target": months[12], "last_training_target": months[index - 1],
                             "training_samples": index - 12, "latest_feature_month": months[index - 1]})
    return schedule


def publish(run, name, value):
    if run == DEFAULT_RUN.resolve():
        write_json(META / name, value)


def prepare(run):
    if (run / "protocol-lock.json").exists():
        verify_lock(run)
        print("Existing protocol verified; no replacement.")
        return
    if run.exists() and any(run.iterdir()):
        raise ValueError("Unsealed nonempty run directory; use a fresh directory")
    cfg = config()
    derived, all_months, lineage, summary, inputs = derive(cfg)
    months = [item["month"] for item in derived["months"]]
    if months[:59] != calendar_months(cfg["initial_history"]["start"], cfg["initial_history"]["end"]):
        raise ValueError("Initial 59-month calendar history does not match design")
    schedule = schedule_for(months, cfg)
    if len(schedule) != 24 or len([s for s in schedule if s["partition"] == "validation"]) != 12:
        raise ValueError("Expected 12 validation and 12 test origins")
    run.mkdir(parents=True, exist_ok=True)
    files = {"config.json": cfg, "monthly-v1.json": derived, "all-observed-months-v1.json": all_months,
             "debit-lineage.json": lineage, "data-summary.json": summary, "schedule.json": schedule}
    for name, value in files.items():
        write_json(run / name, value, exclusive=True)
    with threadpoolctl.threadpool_limits(limits=cfg["thread_limit"]):
        info = [{"internal_api": item["internal_api"], "num_threads": item["num_threads"]} for item in threadpoolctl.threadpool_info()]
        if any(item["num_threads"] != 1 for item in info):
            raise ValueError("Thread limit not effective")
    lock = {"experiment_id": cfg["experiment_id"], "locked_at_utc": now(), "runtime": runtime(),
            "input_hashes": inputs, "local_hashes": {name: sha(run / name) for name in files},
            "threadpools_during_limit": info, "full_series_previously_seen_in_audit": True,
            "not_fully_blind_evaluation": True, "date_hypothesis_author_confirmed": False,
            "currency_verified": False, "coverage_fully_confirmed": False}
    receipt(run, "protocol-lock", lock)
    event(run, "design_and_schedule_locked", derived_sha256=sha(run / "monthly-v1.json"), schedule_sha256=sha(run / "schedule.json"))
    publish(run, "forecast-experiment-protocol.json", lock | {"summary": summary,
            "protocol_sha256": sha(run / "protocol-lock.json"), "local_run_directory": run.relative_to(ROOT).as_posix()})
    print(json.dumps(summary | {"locked_at_utc": lock["locked_at_utc"], "derived_sha256": sha(run / "monthly-v1.json"),
                               "schedule_sha256": sha(run / "schedule.json"), "protocol_sha256": sha(run / "protocol-lock.json")}, indent=2))


def verify_lock(run):
    lock = check_receipt(run, "protocol-lock")
    for path, expected in lock["input_hashes"].items():
        if sha(ROOT / path) != expected:
            raise ValueError(f"Locked input changed: {path}")
    for path, expected in lock["local_hashes"].items():
        if sha(run / path) != expected:
            raise ValueError(f"Locked data/schedule changed: {path}")
    if lock["runtime"] != runtime():
        raise ValueError("Runtime differs from sealed design")
    return lock


def forecast_origins(run, values, months, origins, cfg, alpha=None, baseline=None):
    predictions, fits = [], []
    for origin in origins:
        index = origin["target_index"]
        fit_seconds = 0.0
        if baseline is not None:
            raw = baseline_raw(baseline, values, index)
        else:
            x, y = training_data(values, index)
            estimator = make_pipeline(alpha, cfg)
            tick = time.perf_counter()
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                estimator.fit(x, y)
            fit_seconds = time.perf_counter() - tick
            if int(estimator.named_steps["scaler"].n_samples_seen_) != index - 12:
                raise ValueError("Scaler fitted on unexpected number of samples")
            raw = float(estimator.predict(features_at(values, index).reshape(1, -1))[0])
            model_path = run / "models" / f"{origin['partition']}_alpha_{alpha}_{months[index]}.joblib"
            model_path.parent.mkdir(exist_ok=True)
            joblib.dump(estimator, model_path, compress=3)
            fits.append(origin | {"alpha": alpha, "model_path": model_path.relative_to(run).as_posix(),
                                  "model_sha256": sha(model_path), "fit_seconds": fit_seconds,
                                  "scaler_samples": int(estimator.named_steps["scaler"].n_samples_seen_),
                                  "warnings": [{"category": type(w.message).__name__, "message": str(w.message)} for w in caught]})
        predictions.append({"month": months[index], "observed": float(values[index]),
                            "raw_prediction": raw, "predicted": clip_prediction(raw, cfg),
                            "history_end": months[index - 1], "history_months": index,
                            "fit_seconds": fit_seconds})
    return {"predictions": predictions, "scores": scores(predictions), "fits": fits,
            "total_fit_seconds": sum(f["fit_seconds"] for f in fits)}


def load_series(run):
    derived = read_json(run / "monthly-v1.json")
    months = [item["month"] for item in derived["months"]]
    values = [float(Decimal(item["observed_debit_total"])) for item in derived["months"]]
    return months, values


def validate(run):
    verify_lock(run)
    if (run / "test-opened.json").exists():
        raise ValueError("Test already evaluated/opened; selection cannot be changed")
    if (run / "selection.json").exists():
        check_receipt(run, "selection")
        print("Validation selection already locked; no new fits.")
        return
    cfg = config()
    months, values = load_series(run)
    origins = [o for o in read_json(run / "schedule.json") if o["partition"] == "validation"]
    event(run, "validation_started", alpha_grid=cfg["alpha_values"], test_not_scored=True)
    baselines, candidates = {}, []
    with threadpoolctl.threadpool_limits(limits=cfg["thread_limit"]):
        for baseline in cfg["baselines"]:
            baselines[baseline] = forecast_origins(run, values, months, origins, cfg, baseline=baseline)
        for alpha in cfg["alpha_values"]:
            path = run / f"validation-alpha-{alpha}.json"
            if path.exists():
                result = read_json(path)
                if result["protocol_sha256"] != sha(run / "protocol-lock.json"):
                    raise ValueError("Candidate checkpoint provenance mismatch")
                for fit in result["fits"]:
                    if sha(run / fit["model_path"]) != fit["model_sha256"]:
                        raise ValueError("Candidate model checksum mismatch")
            else:
                result = forecast_origins(run, values, months, origins, cfg, alpha=alpha)
                result.update({"alpha": alpha, "protocol_sha256": sha(run / "protocol-lock.json")})
                write_json(path, result, exclusive=True)
            candidates.append(result)
            event(run, "alpha_validation_complete", alpha=alpha, mae=result["scores"]["mae"], fits=len(result["fits"]))
            print(json.dumps({"alpha": alpha, **result["scores"], "fit_seconds": result["total_fit_seconds"]}), flush=True)
    selection = {"selected_at_utc": now(), "protocol_sha256": sha(run / "protocol-lock.json"),
                 "selected_alpha": choose_alpha(candidates), "rule": cfg["selection"],
                 "candidates": candidates, "baselines": baselines, "test_used_for_selection": False}
    receipt(run, "selection", selection)
    event(run, "alpha_selection_locked", alpha=selection["selected_alpha"], selection_sha256=sha(run / "selection.json"))
    print("Locked alpha from clipped validation MAE:", selection["selected_alpha"])


def verify_selection(run):
    selection = check_receipt(run, "selection")
    if selection["protocol_sha256"] != sha(run / "protocol-lock.json") or choose_alpha(selection["candidates"]) != selection["selected_alpha"]:
        raise ValueError("Selection no longer matches sealed design/rule")
    return selection


def test(run):
    lock = verify_lock(run)
    selection = verify_selection(run)
    if (run / "results.json").exists():
        check_receipt(run, "results")
        print("Existing test result verified; no new fits or predictions.")
        return
    opening = {"opened_at_utc": now(), "selection_sha256": sha(run / "selection.json"),
               "selected_alpha": selection["selected_alpha"], "protocol_sha256": sha(run / "protocol-lock.json")}
    if (run / "test-opened.json").exists():
        if read_json(run / "test-opened.json")["selection_sha256"] != opening["selection_sha256"]:
            raise ValueError("Test cannot resume under a different selection")
    else:
        write_json(run / "test-opened.json", opening, exclusive=True)
        event(run, "test_started_after_selection", alpha=selection["selected_alpha"])
    cfg = config()
    months, values = load_series(run)
    origins = [o for o in read_json(run / "schedule.json") if o["partition"] == "test"]
    methods = {}
    with threadpoolctl.threadpool_limits(limits=cfg["thread_limit"]):
        for baseline in cfg["baselines"]:
            methods[baseline] = forecast_origins(run, values, months, origins, cfg, baseline=baseline)
        methods["ridge"] = forecast_origins(run, values, months, origins, cfg, alpha=selection["selected_alpha"])
    result = {"completed_at_utc": now(), "protocol_sha256": sha(run / "protocol-lock.json"),
              "selection_sha256": sha(run / "selection.json"), "derived_sha256": sha(run / "monthly-v1.json"),
              "selected_alpha": selection["selected_alpha"], "target": cfg["target"], "runtime": lock["runtime"],
              "date_branch": cfg["date_branch"], "date_hypothesis_author_confirmed": False,
              "currency": None, "coverage_fully_confirmed": False, "not_fully_blind_evaluation": True,
              "validation": {"candidates": [{"alpha": c["alpha"], "scores": c["scores"], "total_fit_seconds": c["total_fit_seconds"]} for c in selection["candidates"]],
                             "baselines": {name: value["scores"] for name, value in selection["baselines"].items()}},
              "test": methods}
    receipt(run, "results", result)
    event(run, "test_complete", results_sha256=sha(run / "results.json"), fixed_alpha=selection["selected_alpha"], ridge_fits=len(methods["ridge"]["fits"]))
    publish(run, "forecast-experiment-results.json", result)
    print(json.dumps({name: value["scores"] for name, value in methods.items()}, indent=2))


def verify(run):
    lock = verify_lock(run)
    derived, all_months, lineage, summary, inputs = derive(config())
    expected = {"monthly-v1.json": derived, "all-observed-months-v1.json": all_months,
                "debit-lineage.json": lineage, "data-summary.json": summary,
                "schedule.json": schedule_for([m["month"] for m in derived["months"]], config())}
    if inputs != lock["input_hashes"] or any(json_bytes(value) != (run / name).read_bytes() for name, value in expected.items()):
        raise ValueError("Derived data/schedule is not byte-reproducible")
    months, values = load_series(run)
    candidates = []
    if (run / "selection.json").exists():
        selection = verify_selection(run)
        candidates.extend(selection["candidates"])
    if (run / "results.json").exists():
        result = check_receipt(run, "results")
        if result["selection_sha256"] != sha(run / "selection.json"):
            raise ValueError("Results do not match selection")
        candidates.extend(result["test"].values())
    fits_checked = 0
    for candidate in candidates:
        calculated = scores(candidate["predictions"])
        if any(not np.isclose(calculated[k], candidate["scores"][k], rtol=0, atol=1e-10) for k in calculated):
            raise ValueError("Metrics do not reconcile with saved forecasts")
        for fit in candidate["fits"]:
            if sha(run / fit["model_path"]) != fit["model_sha256"]:
                raise ValueError("Saved model changed")
            x, y = training_data(values, fit["target_index"])
            model = joblib.load(run / fit["model_path"])
            scaler = model.named_steps["scaler"]
            if int(scaler.n_samples_seen_) != len(y) or not np.allclose(scaler.mean_, x.mean(axis=0), rtol=0, atol=1e-8) or not np.allclose(scaler.var_, x.var(axis=0), rtol=1e-12, atol=1e-8):
                raise ValueError("Scaler statistics are not from that origin's past-only training set")
            if model.named_steps["ridge"].alpha != fit["alpha"] or fit["last_training_target"] >= fit["target_month"]:
                raise ValueError("Temporal/model invariant failed")
            fits_checked += 1
    print(f"PASS: byte-reproducible data/schedule, intact source/protocol, metrics and {fits_checked} past-only scaler/model fits; no fitting/prediction performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "validate", "test", "verify"])
    parser.add_argument("--run-dir", default="data/experiments/forecast/task07b-v1")
    args = parser.parse_args()
    run = (ROOT / args.run_dir).resolve()
    if not run.is_relative_to(RUN_BASE.resolve()) or run == RUN_BASE.resolve():
        parser.error("Run directory must be inside ignored data/experiments/forecast/")
    compatibility.install_adapter()  # Process-local, no environment/package edits.
    {"prepare": prepare, "validate": validate, "test": test, "verify": verify}[args.phase](run)
