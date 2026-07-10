#!/usr/bin/env python3
"""Slice full 1000-row Excel workbooks into a smaller test subset (e.g. 50 or 100)."""

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
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source_name, out_name, key_col in INTERNAL_SPECS:
        src = source_dir / source_name
        if not src.exists():
            raise FileNotFoundError(f"Missing source workbook: {src}")
        df = pd.read_excel(src, engine="openpyxl")
        if key_col == "CustomerID" and source_name.startswith("customer_master"):
            sliced = df.head(len(customer_ids)).copy()
            ids = {str(v).strip() for v in sliced[key_col]}
            customer_ids.clear()
            customer_ids.update(ids)
        else:
            sliced = df[df[key_col].astype(str).str.strip().isin(customer_ids)].copy()
        out = output_dir / out_name
        sliced.to_excel(out, index=False, engine="openpyxl")
        counts[out_name] = len(sliced)
    return counts


def _slice_external(source_dir: Path, output_dir: Path, limit: int) -> int:
    source_name, out_name, _ = EXTERNAL_SPEC
    src = source_dir / source_name
    if not src.exists():
        raise FileNotFoundError(f"Missing source workbook: {src}")
    df = pd.read_excel(src, engine="openpyxl")
    sliced = df.head(limit).copy()
    out = output_dir / out_name
    sliced.to_excel(out, index=False, engine="openpyxl")
    return len(sliced)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create Excel subset for pre-XAI pipeline testing"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of internal customers and external leads (default: 100)",
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=PROJECT_ROOT,
        help="Directory containing the full *_1000.xlsx files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: data/excel_subset_<limit>)",
    )
    args = parser.parse_args()

    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")

    output_dir = args.output_dir or (PROJECT_ROOT / "data" / f"excel_subset_{args.limit}")
    output_dir.mkdir(parents=True, exist_ok=True)

    customer_master = args.source_dir / "customer_master_1000.xlsx"
    if not customer_master.exists():
        raise SystemExit(f"Not found: {customer_master}")

    master_df = pd.read_excel(customer_master, engine="openpyxl")
    customer_ids = {str(v).strip() for v in master_df["CustomerID"].head(args.limit)}

    print(f"Slicing {args.limit} customers -> {output_dir}")
    internal_counts = _slice_internal(args.source_dir, output_dir, customer_ids)
    external_count = _slice_external(args.source_dir, output_dir, args.limit)

    print("\nInternal files:")
    for name, count in internal_counts.items():
        print(f"  {name}: {count}")
    print(f"\nExternal leads: {external_count}")

    env_path = output_dir / "env_snippet.txt"
    env_path.write_text(
        "\n".join(
            [
                f"# Add to .env for {args.limit}-customer test run",
                f"EXPECTED_CUSTOMER_COUNT={args.limit}",
                f"EXPECTED_LEAD_COUNT={args.limit}",
                f"CUSTOMER_MASTER_EXCEL_PATH={output_dir.as_posix()}/customer_master.xlsx",
                f"TRANSACTION_HISTORY_EXCEL_PATH={output_dir.as_posix()}/transaction_history.xlsx",
                f"LOAN_HISTORY_EXCEL_PATH={output_dir.as_posix()}/loan_history.xlsx",
                f"DIGITAL_ACTIVITY_EXCEL_PATH={output_dir.as_posix()}/digital_activity.xlsx",
                f"EXTERNAL_LEADS_EXCEL_PATH={output_dir.as_posix()}/external_leads.xlsx",
                "",
                "# Use forward slashes in .env on Windows (backslashes break \\U escapes)",
                "# Then run:",
                "# python scripts/run_pre_xai_pipeline.py",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\nEnv hints written to: {env_path}")
    print("\nNext:")
    print(f"  1. Stop any running 1000-customer pipeline")
    print(f"  2. Copy paths from {env_path} into .env")
    print(f"  3. Set EXPECTED_CUSTOMER_COUNT={args.limit} and EXPECTED_LEAD_COUNT={args.limit}")
    print("  4. python scripts/run_pre_xai_pipeline.py")


if __name__ == "__main__":
    main()
