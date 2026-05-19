"""
01_extract_xlsx.py

Reads both raw .xlsx workbooks and dumps every tab as its own CSV under
data/raw/sheets/{player_stats,league}/. This is intentionally a dumb,
lossless dump — no parsing or cleaning. It exists so downstream scripts
(and humans) can inspect individual tabs without re-opening Excel.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SHEETS_DIR = RAW_DIR / "sheets"

WORKBOOKS = {
    "player_stats": RAW_DIR / "player_stats_raw.xlsx",
    "league": RAW_DIR / "league_raw.xlsx",
}


def safe_filename(sheet_name: str) -> str:
    # Excel allows characters that are awkward in filenames. Keep it portable.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", sheet_name).strip("_")


def extract_workbook(label: str, xlsx_path: Path) -> list[str]:
    if not xlsx_path.exists():
        sys.exit(f"ERROR: missing {xlsx_path}")
    out_dir = SHEETS_DIR / label
    out_dir.mkdir(parents=True, exist_ok=True)

    # header=None preserves the raw grid; the parser scripts will decide how to interpret rows.
    sheets = pd.read_excel(xlsx_path, sheet_name=None, header=None, engine="openpyxl")
    written = []
    for name, df in sheets.items():
        out_path = out_dir / f"{safe_filename(name)}.csv"
        df.to_csv(out_path, index=False, header=False)
        written.append(name)
    return written


def main() -> None:
    print("=" * 60)
    print("01_extract_xlsx.py — dumping workbook tabs to CSV")
    print("=" * 60)

    for label, xlsx_path in WORKBOOKS.items():
        tabs = extract_workbook(label, xlsx_path)
        print(f"\n[{label}] {xlsx_path.name}")
        print(f"  -> wrote {len(tabs)} tab(s) to data/raw/sheets/{label}/")
        for t in tabs:
            print(f"     - {t}")

    print("\nDone.")


if __name__ == "__main__":
    main()
