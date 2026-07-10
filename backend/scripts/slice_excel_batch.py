#!/usr/bin/env python3
"""Slice a batch of rows from full 1000-row Excel files (e.g. offset 50, limit 50 = rows 51–100)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INTERNAL_SPECS: list[tuple[str, str, str]] = [
    ("customer_master_1000.xlsx", "customer_master.xlsx", "CustomerID"),
    ("loan_history_1000.xlsx", "loan_history.xlsx", "CustomerID"),
    ("digital_activity_1000.xlsx", "digital_activity.xlsx", "CustomerID"),
    ("transaction_history_15000.xlsx", "transaction_history.xlsx", "CustomerID"),
]

EXTERNAL_SPEC = ("external_leads_1000.xlsx", "external_leads.xlsx", "LeadID")


def _slice_internal(
    source_dir: Path,
    output_dir: Path,
    customer_ids: set[str],
    offset: int,
    limit: int,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    master_path = source_dir / "customer_master_1000.xlsx"
    master_df = pd.read_excel(master_path, engine="openpyxl")
    batch = master_df.iloc[offset : offset + limit]
    customer_ids.update(str(v).strip() for v in batch["CustomerID"])

    for source_name, out_name, key_col in INTERNAL_SPECS:
        src = source_dir / source_name
        if not src.exists():
            raise FileNotFoundError(f"Missing source workbook: {src}")
        df = pd.read_excel(src, engine="openpyxl")
        if key_col == "CustomerID" and source_name.startswith("customer_master"):
            sliced = batch.copy()
        else:
            sliced = df[df[key_col].astype(str).str.strip().isin(customer_ids)].copy()
        out = output_dir / out_name
        sliced.to_excel(out, index=False, engine="openpyxl")
        counts[out_name] = len(sliced)
    return counts


def _slice_external(source_dir: Path, output_dir: Path, offset: int, limit: int) -> int:
    source_name, out_name, _ = EXTERNAL_SPEC
    src = source_dir / source_name
    if not src.exists():
        raise FileNotFoundError(f"Missing source workbook: {src}")
    df = pd.read_excel(src, engine="openpyxl")
    sliced = df.iloc[offset : offset + limit].copy()
    out = output_dir / out_name
    sliced.to_excel(out, index=False, engine="openpyxl")
    return len(sliced)


def main() -> None:
    parser = argparse.ArgumentParser(description="Slice Excel batch with offset (next N customers)")
    parser.add_argument("--offset", type=int, default=50, help="Skip first N rows (default: 50)")
    parser.add_argument("--limit", type=int, default=50, help="Rows to take (default: 50)")
    parser.add_argument("--source-dir", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or (
        PROJECT_ROOT / "data" / f"excel_batch_{args.offset}_{args.limit}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    customer_ids: set[str] = set()
    print(f"Slicing rows {args.offset + 1}–{args.offset + args.limit} -> {output_dir}")
    internal_counts = _slice_internal(
        args.source_dir, output_dir, customer_ids, args.offset, args.limit
    )
    external_count = _slice_external(args.source_dir, output_dir, args.offset, args.limit)

    print("\nInternal files:")
    for name, count in internal_counts.items():
        print(f"  {name}: {count}")
    print(f"\nExternal leads: {external_count}")

    env_path = output_dir / "env_snippet.txt"
    env_path.write_text(
        "\n".join(
            [
                f"# Batch rows {args.offset + 1}–{args.offset + args.limit}",
                f"EXPECTED_CUSTOMER_COUNT={args.limit}",
                f"EXPECTED_LEAD_COUNT={args.limit}",
                f"CUSTOMER_MASTER_EXCEL_PATH={output_dir.as_posix()}/customer_master.xlsx",
                f"TRANSACTION_HISTORY_EXCEL_PATH={output_dir.as_posix()}/transaction_history.xlsx",
                f"LOAN_HISTORY_EXCEL_PATH={output_dir.as_posix()}/loan_history.xlsx",
                f"DIGITAL_ACTIVITY_EXCEL_PATH={output_dir.as_posix()}/digital_activity.xlsx",
                f"EXTERNAL_LEADS_EXCEL_PATH={output_dir.as_posix()}/external_leads.xlsx",
                "",
                "# python scripts/load_excel_to_mongo.py",
                "# python scripts/run_pre_xai_pipeline.py",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nEnv hints: {env_path}")


if __name__ == "__main__":
    main()
