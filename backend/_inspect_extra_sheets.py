"""One-off: dump the 'Shipping Info' and 'Si' sheets of sample build plans."""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent / "data" / "build plan"

samples = [
    "LzP Build Plan WW1626 rev1.xlsx",
    "WhP A0 Build Plan WW3325 Rev01.xlsx",
    "PeP2 Build Plan ww18'26 Rev6.xlsx",
    "SpP Build Plan WW1926 rev1.xlsx",
]

for name in samples:
    p = ROOT / name
    if not p.exists():
        print(f"MISSING: {p}")
        continue
    print(f"\n############ FILE: {name}")
    xls = pd.ExcelFile(p, engine="calamine")
    print("sheets:", xls.sheet_names)
    for s in xls.sheet_names:
        if s.strip().lower() in ("shipping info", "si"):
            df = pd.read_excel(p, engine="calamine", sheet_name=s, header=None)
            print(f"\n==== SHEET '{s}'  shape={df.shape}")
            with pd.option_context("display.max_columns", None, "display.width", 200):
                print(df.head(30).to_string())
