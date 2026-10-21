"""MoneyData V1 audit, standard library only; never edits the source workbook.

Raw workbook and row-level diagnostics stay in ignored data/. No Django, SQLite,
model fitting or personal transaction text in shareable outputs.
"""
import argparse
import calendar
import hashlib
import json
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DATASET = "dnxtg6n4rv"
VERSION = 1
DOI = "10.17632/dnxtg6n4rv.1"
PAGE = f"https://data.mendeley.com/datasets/{DATASET}/{VERSION}"
API = f"https://data.mendeley.com/public-api/datasets/{DATASET}/files?folder_id=root&version={VERSION}"
FILE_ID = "36b3d359-2491-4282-850f-3f03e00fbfe3"
FILENAME = "laramee26openBankTransactionData.xlsx"
EXPECTED_SHA = "716eaf9ad4a3cf60dc9c9c8a20ed9a917c545a1b5f139f40ed91d2104faa3ff7"
RAW = ROOT / "data" / "external" / "moneydata" / "v1"
META = ROOT / "docs" / "metadata"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get(url, limit):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": PAGE})
    with urlopen(request, timeout=45) as response:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Download exceeds configured size limit")
        return data


def download():
    manifest_path = META / "forecast-source.json"
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    metadata = get(API, 100_000)
    files = json.loads(metadata)
    chosen = [entry for entry in files if entry["id"] == FILE_ID and entry["filename"] == FILENAME]
    if len(chosen) != 1:
        raise ValueError("Expected pinned V1 file not found")
    details = chosen[0]["content_details"]
    if details["sha256_hash"] != EXPECTED_SHA or chosen[0]["status"] != "COMPLETED":
        raise ValueError("Source metadata differs from pinned V1")
    url = details["download_url"]
    if not url.startswith(f"https://data.mendeley.com/public-files/datasets/{DATASET}/files/{FILE_ID}/"):
        raise ValueError("Unexpected download host/file ID")
    content = get(url, 5_000_000)
    if sha256(content) != EXPECTED_SHA or len(content) != details["size"]:
        raise ValueError("Workbook hash/size differs from official metadata")
    path = RAW / FILENAME
    if path.exists() and path.read_bytes() != content:
        raise ValueError("Refusing to overwrite a different local workbook")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(content)
    if previous is None:
        (RAW / "files-api.json").write_bytes(metadata)
        write_json(manifest_path, {
            "dataset": "MoneyData — Bank Transactions Dataset", "dataset_id": DATASET,
            "version": VERSION, "doi": DOI, "source_url": PAGE, "files_api_url": API,
            "contributor": "Robert Laramee", "institution": "University of Nottingham",
            "published": "2026-01-14", "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/", "license_evidence": PAGE,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "file_id": FILE_ID, "filename": FILENAME, "download_url": url,
            "bytes": len(content), "sha256": EXPECTED_SHA,
            "local_raw_directory": RAW.relative_to(ROOT).as_posix(),
            "source_modified": False,
        })
    else:
        if previous["sha256"] != EXPECTED_SHA or previous["version"] != VERSION:
            raise ValueError("Previous provenance mismatch")
    print("Official MoneyData V1 download verified; raw bytes unchanged.")


def workbook():
    """Read values, cell types, formats and formula/cache evidence, no recalculation."""
    path = RAW / FILENAME
    content = path.read_bytes()
    if sha256(content) != EXPECTED_SHA:
        raise ValueError("Raw workbook SHA-256 mismatch")
    with zipfile.ZipFile(path) as archive:
        if sum(item.file_size for item in archive.infolist()) > 50_000_000:
            raise ValueError("Workbook expanded size exceeds audit limit")
        book = ET.fromstring(archive.read("xl/workbook.xml"))
        properties = book.find("m:workbookPr", NS)
        date1904 = properties is not None and properties.get("date1904", "0").lower() in {"1", "true"}
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(part.text or "" for part in item.findall(".//m:t", NS)) for item in strings]
        styles = ET.fromstring(archive.read("xl/styles.xml"))
        formats = {int(item.get("numFmtId")): item.get("formatCode") for item in styles.findall("m:numFmts/m:numFmt", NS)}
        xfs = [int(item.get("numFmtId", "0")) for item in styles.findall("m:cellXfs/m:xf", NS)]
        relations = {item.get("Id"): item.get("Target") for item in ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        sheets = []
        for sheet in book.findall("m:sheets/m:sheet", NS):
            target = relations[sheet.get(f"{{{REL}}}id")]
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            xml = ET.fromstring(archive.read(target))
            rows = []
            for row in xml.findall("m:sheetData/m:row", NS):
                cells = {}
                for cell in row.findall("m:c", NS):
                    value = cell.find("m:v", NS)
                    text = value.text if value is not None and value.text is not None else ""
                    kind = cell.get("t", "n")
                    if kind == "s":
                        text = shared[int(text)] if text else ""
                    elif kind == "inlineStr":
                        text = "".join(item.text or "" for item in cell.findall(".//m:t", NS))
                    style = int(cell.get("s", "0"))
                    fmt_id = xfs[style]
                    cells[re.sub(r"\d", "", cell.get("r"))] = {
                        "value": text, "type": kind, "format_id": fmt_id,
                        "format": formats.get(fmt_id, f"builtin:{fmt_id}"),
                        "formula": cell.find("m:f", NS) is not None,
                    }
                rows.append({"row": int(row.get("r")), "cells": cells})
            sheets.append({"name": sheet.get("name"), "state": sheet.get("state", "visible"), "rows": rows})
    return sheets, date1904


def inspect_schema():
    sheets, date1904 = workbook()
    # Header values only: never print transaction cells.
    output = {"date1904": date1904, "sheets": []}
    for sheet in sheets:
        nonempty = [row for row in sheet["rows"] if any(cell["value"].strip() for cell in row["cells"].values())]
        header = nonempty[0] if nonempty else {"row": None, "cells": {}}
        output["sheets"].append({"name": sheet["name"], "state": sheet["state"],
            "xml_rows": len(sheet["rows"]), "nonempty_rows": len(nonempty),
            "header_row": header["row"], "headers": {col: cell["value"] for col, cell in header["cells"].items()},
            "cell_types": dict(Counter(cell["type"] for row in nonempty[1:] for cell in row["cells"].values())),
            "number_formats": dict(Counter(str(cell["format"]) for row in nonempty[1:] for cell in row["cells"].values())),
            "formula_cells": sum(cell["formula"] for row in nonempty for cell in row["cells"].values())})
    print(json.dumps(output, ensure_ascii=False, indent=2))


def excel_date(value, date1904=False):
    serial = Decimal(value)
    if not serial.is_finite() or serial != serial.to_integral_value():
        raise ValueError("Non-integral/invalid Excel day serial")
    days = int(serial)
    if not date1904 and days == 60:
        raise ValueError("Excel fictitious 1900-02-29")
    origin = date(1904, 1, 1) if date1904 else date(1899, 12, 31) if days < 60 else date(1899, 12, 30)
    return origin + timedelta(days=days)


def parse_date(cell, date1904=False, swap_numeric=False):
    if cell["type"] == "n":
        result = excel_date(cell["value"], date1904)
        if swap_numeric:
            result = date(result.year, result.day, result.month)
        return result
    if cell["type"] == "s" and re.fullmatch(r"\d{2}/\d{2}/\d{4}", cell["value"].strip()):
        return datetime.strptime(cell["value"].strip(), "%d/%m/%Y").date()
    raise ValueError("Unrecognized date representation")


def money(value):
    if not value.strip():
        return None
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Non-finite amount")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def month_keys(start, end):
    current = start.replace(day=1)
    while current <= end:
        yield current.strftime("%Y-%m")
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def duplicate_counts(keys):
    groups = defaultdict(list)
    for i, key in enumerate(keys):
        groups[key].append(i)
    repeated = [ids for ids in groups.values() if len(ids) > 1]
    return {"duplicate_groups": len(repeated), "rows_in_groups": sum(map(len, repeated)),
            "excess_rows": len(keys) - len(groups)}, repeated


def temporal_plan(months):
    # Availability count only; never declares completeness or fills absent months.
    interior = months[1:-1]
    blocks = []
    for item in interior:
        if item["transactions"] is None:
            if blocks and blocks[-1]:
                blocks.append([])
        else:
            if not blocks:
                blocks.append([])
            blocks[-1].append(item["month"])
    blocks = [block for block in blocks if block]
    block = max(blocks, key=len, default=[])
    plan = {"boundary_months_excluded": [months[0]["month"], months[-1]["month"]],
            "interior_months_with_rows": sum(item["transactions"] is not None for item in interior),
            "longest_interior_calendar_run_with_rows": len(block),
            "confirmed_coverage_months": 0, "approved_forecast_origins": 0,
            "conditional_only": True, "minimum_training_months_for_origin_count": 36,
            "maximum_conditional_one_step_origins": max(len(block) - 36, 0)}
    if len(block) >= 60:
        plan["conditional_split"] = {
            "train": {"start": block[0], "end": block[-25], "months": len(block) - 24},
            "validation": {"start": block[-24], "end": block[-13], "months": 12},
            "test": {"start": block[-12], "end": block[-1], "months": 12},
            "validation_origins": 12, "test_origins": 12,
            "maximum_origins_start": block[36], "maximum_origins_end": block[-1],
        }
    return plan


def audit():
    provenance = json.loads((META / "forecast-source.json").read_text(encoding="utf-8"))
    if provenance["sha256"] != EXPECTED_SHA or provenance["version"] != 1 or provenance["file_id"] != FILE_ID:
        raise ValueError("Unexpected provenance")
    sheets, date1904 = workbook()
    source = sheets[0]
    header = source["rows"][0]
    expected = ["Transaction Number", "Transaction Date", "Transaction Type", "Transaction Description",
                "Debit Amount", "Credit Amount", "Balance", "Category", "Location City", "Location Country"]
    columns = list("ABCDEFGHIJ")
    if [header["cells"].get(col, {}).get("value") for col in columns] != expected:
        raise ValueError("Unexpected V1 schema")
    rows = [row for row in source["rows"][1:] if any(cell["value"].strip() for cell in row["cells"].values())]
    values = [{col: row["cells"].get(col, {}).get("value", "") for col in columns} for row in rows]
    if any(set(row["cells"]) - set(columns) for row in rows):
        raise ValueError("Unexpected additional columns")
    result = {"audit_version": 1, "source_sha256": EXPECTED_SHA, "script_sha256": sha256(Path(__file__).read_bytes()),
              "doi": DOI, "rows": len(rows), "schema": dict(zip(columns, expected)),
              "sheets": [{"name": sheet["name"], "xml_rows": len(sheet["rows"]),
                          "nonempty_rows": sum(any(c["value"].strip() for c in row["cells"].values()) for row in sheet["rows"])} for sheet in sheets],
              "blank_counts": {name: sum(not row[col].strip() for row in values) for col, name in zip(columns, expected)},
              "excel_error_cells": sum(c["type"] == "e" for row in rows for c in row["cells"].values()),
              "formula_cells": sum(c["formula"] for row in rows for c in row["cells"].values()),
              "currency": {"verified": False, "code": None, "currency_column_present": False,
                           "amount_number_formats": sorted({row["cells"][col]["format"] for row in rows for col in "EFG"})},
              "identity": {"user_id_column": False, "account_id_column": False,
                           "customers_as_described_by_paper": 1, "accounts_verified_from_file": None},
              "methods": {"money": "Decimal from XML numeric text; quantize .01 ROUND_HALF_UP for diagnostics; blank side is None, not an imputed transaction",
                          "date_text": "strict DD/MM/YYYY", "date_numeric": "Excel 1900/1904 serial with separate month/day swap sensitivity branch",
                          "missing_months": "None, never zero", "coverage_verified": False}}
    ids = [int(row["A"]) for row in values]
    result["transaction_numbers"] = {"unique": len(set(ids)), "min": min(ids), "max": max(ids),
                                      "missing_integer_ids": len(set(range(min(ids), max(ids) + 1)) - set(ids)),
                                      "strictly_increasing_in_sheet": all(a < b for a, b in zip(ids, ids[1:]))}
    amounts = []
    money_stats = {}
    for col, name in zip("EFG", ["debit", "credit", "balance"]):
        present = [Decimal(row[col]) for row in values if row[col].strip()]
        rounded = [money(row[col]) for row in values if row[col].strip()]
        deltas = [abs(a - b) for a, b in zip(present, rounded)]
        money_stats[name] = {"present": len(present), "blank": len(rows) - len(present),
                             "negative": sum(v < 0 for v in present), "zero": sum(v == 0 for v in present),
                             "raw_xml_sum": str(sum(present, Decimal(0))),
                             "rounded_sum": str(sum(rounded, Decimal(0))),
                             "values_adjusted_at_two_decimals": sum(v != 0 for v in deltas),
                             "maximum_rounding_adjustment": str(max(deltas, default=Decimal(0)))}
        if name == "balance":
            # Balances are stocks, not additive flows; do not publish their sum.
            del money_stats[name]["raw_xml_sum"]
            del money_stats[name]["rounded_sum"]
    for row in values:
        amounts.append({col: money(row[col]) for col in "EFG"})
    result["money"] = money_stats
    result["direction"] = {"debit_only": sum(a["E"] is not None and a["F"] is None for a in amounts),
                           "credit_only": sum(a["F"] is not None and a["E"] is None for a in amounts),
                           "both_present": sum(a["E"] is not None and a["F"] is not None for a in amounts),
                           "both_absent": sum(a["E"] is None and a["F"] is None for a in amounts)}
    # Empty inactive amount side contributes no posted flow; not calendar imputation.
    residuals = [amounts[i]["G"] - (amounts[i + 1]["G"] - (amounts[i]["E"] or Decimal(0)) + (amounts[i]["F"] or Decimal(0))) for i in range(len(rows) - 1)]
    result["balance_reconciliation"] = {"adjacent_pairs_in_sheet": len(residuals),
                                        "mismatches_at_two_decimals": sum(v != 0 for v in residuals),
                                        "max_absolute_residual": str(max(map(abs, residuals), default=Decimal(0)))}
    result["transaction_types"] = {}
    for typ in sorted({row["C"].strip() for row in values}):
        indices = [i for i, row in enumerate(values) if row["C"].strip() == typ]
        result["transaction_types"][typ or "<blank>"] = {"rows": len(indices),
            "debit_rows": sum(amounts[i]["E"] is not None for i in indices),
            "credit_rows": sum(amounts[i]["F"] is not None for i in indices)}
    duplicates, duplicate_rows = duplicate_counts([tuple(row[col] for col in columns) for row in values])
    no_id_stats, no_id_rows = duplicate_counts([tuple(row[col] for col in columns[1:]) for row in values])
    result["duplicates"] = {"all_fields": duplicates, "excluding_transaction_number": no_id_stats}
    local = {"date_errors": {}, "candidate_duplicate_excel_rows": {"all_fields": [[rows[i]["row"] for i in group] for group in duplicate_rows],
                                                                  "excluding_transaction_number": [[rows[i]["row"] for i in group] for group in no_id_rows]}}
    parsed_branches = {}
    result["date_storage"] = {"type_counts": dict(Counter(row["cells"]["B"]["type"] for row in rows)),
                              "date1904": date1904,
                              "text_dmy_mdy_ambiguous_rows": sum(row["cells"]["B"]["type"] == "s" and all(int(part) <= 12 for part in row["cells"]["B"]["value"].split("/")[:2]) for row in rows)}
    text_dates = [parse_date(row["cells"]["B"], date1904) for row in rows if row["cells"]["B"]["type"] == "s"]
    numeric_dates = [parse_date(row["cells"]["B"], date1904) for row in rows if row["cells"]["B"]["type"] == "n"]
    result["date_storage"].update({"text_only_first_date": min(text_dates).isoformat(), "text_only_last_date": max(text_dates).isoformat(),
                                   "numeric_serial_day_at_most_12": sum(d.day <= 12 for d in numeric_dates),
                                   "numeric_serial_month_day_equal": sum(d.day == d.month for d in numeric_dates)})
    result["date_branches"] = {}
    for branch, swap in [("stored_calendar", False), ("swap_numeric_month_day_hypothesis", True)]:
        dates = []
        errors = []
        for row in rows:
            try:
                dates.append(parse_date(row["cells"]["B"], date1904, swap))
            except (ValueError, InvalidOperation, OverflowError):
                dates.append(None)
                errors.append(row["row"])
        local["date_errors"][branch] = errors
        parsed_branches[branch] = dates
        valid = [d for d in dates if d is not None]
        by_month = defaultdict(list)
        for i, d in enumerate(dates):
            if d is not None:
                by_month[d.strftime("%Y-%m")].append(i)
        months = []
        for key in month_keys(min(valid), max(valid)):
            indices = by_month.get(key, [])
            months.append({"month": key, "transactions": len(indices) if indices else None,
                           "debit_transactions": sum(amounts[i]["E"] is not None for i in indices) if indices else None,
                           "credit_transactions": sum(amounts[i]["F"] is not None for i in indices) if indices else None,
                           "observed_debit_total": str(sum((amounts[i]["E"] or Decimal(0) for i in indices), Decimal("0.00"))) if indices else None,
                           "observed_credit_total": str(sum((amounts[i]["F"] or Decimal(0) for i in indices), Decimal("0.00"))) if indices else None,
                           "days_with_rows": len({dates[i] for i in indices}) if indices else None,
                           "coverage": "unknown", "boundary_month": key in {min(valid).strftime("%Y-%m"), max(valid).strftime("%Y-%m")}})
        unique_days = sorted(set(valid))
        gaps = [{"previous_observed_day": left.isoformat(), "next_observed_day": right.isoformat(),
                 "calendar_days_without_rows": (right - left).days - 1}
                for left, right in zip(unique_days, unique_days[1:]) if (right - left).days > 1]
        business_keys = [(d.isoformat() if d else "<invalid>", values[i]["C"].strip().casefold(),
                          " ".join(values[i]["D"].casefold().split()), str(amounts[i]["E"]), str(amounts[i]["F"])) for i, d in enumerate(dates)]
        business_stats, business_rows = duplicate_counts(business_keys)
        local["candidate_duplicate_excel_rows"][branch + "_business_key"] = [[rows[i]["row"] for i in group] for group in business_rows]
        summary = {"first_date": min(valid).isoformat(), "last_date": max(valid).isoformat(), "invalid_dates": len(errors),
                   "descending_order_violations_in_sheet": sum(a < b for a, b in zip(dates, dates[1:]) if a is not None and b is not None),
                   "weekend_rows": sum(d.weekday() >= 5 for d in valid), "unique_days_with_rows": len(unique_days),
                   "calendar_months": len(months), "months_without_rows": [item["month"] for item in months if item["transactions"] is None],
                   "longest_gap_without_rows_days": max((g["calendar_days_without_rows"] for g in gaps), default=0),
                   "gaps_with_at_least_7_calendar_days_without_rows": [g for g in gaps if g["calendar_days_without_rows"] >= 7],
                   "duplicate_business_key_candidates": business_stats,
                   "monthly": months, "temporal_plan": temporal_plan(months), "date_semantics_confirmed": False}
        result["date_branches"][branch] = summary
    # Flags describe evidence, not verified internal transfers/refunds/card repayments.
    flags = {
        "type_TFR": lambda row: row["C"].strip() == "TFR",
        "category_account_transfer": lambda row: row["H"].strip().casefold() == "account transfer",
        "category_savings": lambda row: row["H"].strip().casefold() == "savings",
        "category_investment": lambda row: row["H"].strip().casefold() == "investment",
        "category_cash": lambda row: row["H"].strip().casefold() == "cash",
        "type_CPT": lambda row: row["C"].strip() == "CPT",
        "type_DEB": lambda row: row["C"].strip() == "DEB",
        "category_supplementary_income_includes_refunds_per_dictionary": lambda row: row["H"].strip().casefold() == "supplementary income",
        "category_named_return_or_reimbursement": lambda row: row["H"].strip().casefold() in {"safety deposit return", "travel reimbursement"},
        "description_refund_keywords": lambda row: bool(re.search(r"\b(?:refund(?:ed|s)?|reversal|reimburse(?:ment|d)?)\b", row["D"], re.I)),
        "description_card_keywords": lambda row: bool(re.search(r"\b(?:credit\s+card|card\s+repayment|card\s+payment|barclaycard|mastercard|visa|amex|american\s+express)\b", row["D"], re.I)),
    }
    result["flow_evidence_flags"] = {}
    local["evidence_flag_excel_rows"] = {}
    for name, predicate in flags.items():
        indices = [i for i, row in enumerate(values) if predicate(row)]
        result["flow_evidence_flags"][name] = {"rows": len(indices),
            "debit_rows": sum(amounts[i]["E"] is not None for i in indices),
            "credit_rows": sum(amounts[i]["F"] is not None for i in indices),
            "small_group_amounts_suppressed": 0 < len(indices) < 5,
            "debit_total": None if 0 < len(indices) < 5 else str(sum((amounts[i]["E"] or Decimal(0) for i in indices), Decimal("0.00"))),
            "credit_total": None if 0 < len(indices) < 5 else str(sum((amounts[i]["F"] or Decimal(0) for i in indices), Decimal("0.00")))}
        local["evidence_flag_excel_rows"][name] = [rows[i]["row"] for i in indices]
    # Report no personal category labels, names, descriptions, locations or balances by row.
    result["category_quality"] = {"raw_distinct_nonblank_labels": len({r["H"] for r in values if r["H"].strip()}),
                                  "trimmed_distinct_nonblank_labels": len({r["H"].strip() for r in values if r["H"].strip()}),
                                  "rows_with_outer_whitespace": sum(r["H"] != r["H"].strip() for r in values)}
    write_json(META / "forecast-audit.json", result)
    write_json(RAW / "audit" / "row-diagnostics.json", local)
    lines = ["# MoneyData V1 — thống kê tháng theo hai cách diễn giải ngày", "",
             "Được tạo bởi `scripts/audit_forecast_data.py`. Chỉ có thống kê tổng hợp. Đơn vị tiền gốc chưa xác minh; số tiền làm tròn Decimal 2 chữ số cho kiểm định. Không phải tổng chi tiêu tiêu dùng.", "",
             "Hai nhánh là phân tích độ nhạy, không phải hai người/tài khoản. Không sửa tệp gốc. Mọi tháng đều chưa có xác nhận độ phủ; tháng biên có nguy cơ không trọn vẹn. Xem `../forecast-data-audit.md` trước khi sử dụng.", ""]
    for branch, summary in result["date_branches"].items():
        lines += [f"## {branch}", "", "| Tháng | Giao dịch | Ghi nợ | Ghi có | Tổng ghi nợ quan sát | Tổng ghi có quan sát | Biên |", "|---|---:|---:|---:|---:|---:|---|"]
        for month in summary["monthly"]:
            def display(value):
                return "chưa biết" if value is None else str(value)
            lines.append("| " + " | ".join(display(month[k]) for k in ["month", "transactions", "debit_transactions", "credit_transactions", "observed_debit_total", "observed_credit_total"]) + " | " + ("có" if month["boundary_month"] else "") + " |")
        lines += [""]
    (META / "forecast-monthly-summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"rows": result["rows"], "blank_counts": result["blank_counts"],
                      "direction": result["direction"], "duplicates": result["duplicates"],
                      "balance_reconciliation": result["balance_reconciliation"],
                      "date_branches": {name: {k: v for k, v in summary.items() if k != "monthly"} for name, summary in result["date_branches"].items()},
                      "flow_evidence_flags": result["flow_evidence_flags"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--inspect-schema", action="store_true")
    options = parser.parse_args()
    if options.download_only and not options.download:
        parser.error("--download-only requires --download")
    if options.download:
        download()
    if options.inspect_schema:
        inspect_schema()
    elif not options.download_only:
        audit()
