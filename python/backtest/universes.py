"""Write universe files (vn30 / vn50 / vn100) next to the price data.

- vn30, vn50: user-provided constituent lists (editable JSON in the data folder).
- vn100: all symbols currently present in the data folder.
Universe filtering then happens at load time: `load_panel` intersects the
selected universe with the CSVs actually available in the data folder.
"""
from __future__ import annotations

import json
import os

DATA_DIR = r"F:\data_finance\data"

VN30 = [
    "ACB", "BCM", "BID", "BVH", "CTG",
    "FPT", "GAS", "GVR", "HDB", "HPG",
    "LPB", "MBB", "MSN", "MWG", "PLX",
    "POW", "SAB", "SHB", "SSB", "SSI",
    "STB", "TCB", "TPB", "VCB", "VHM",
    "VIB", "VIC", "VJC", "VNM", "VPB",
]

VN50 = [
    "ACB", "BCM", "BID", "BVH", "CTG",
    "FPT", "GAS", "GEX", "GMD", "GVR",
    "HDB", "HCM", "HPG", "KBC", "KDH",
    "LPB", "MBB", "MSN", "MWG", "NLG",
    "NVB", "PDR", "PLX", "PNJ", "POW",
    "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TCH", "TPB", "VCB", "VCG",
    "VCI", "VHM", "VIB", "VIC", "VJC",
    "VIX", "VND", "VNM", "VPB", "VRE",
    "VTP", "DGC", "DPM", "REE", "VHC",
]


def all_symbols(data_dir: str = DATA_DIR) -> list[str]:
    return sorted(
        f[:-4].upper()
        for f in os.listdir(data_dir)
        if f.lower().endswith(".csv")
    )


def write_universes(data_dir: str = DATA_DIR) -> None:
    os.makedirs(data_dir, exist_ok=True)
    vn100 = all_symbols(data_dir)
    for name, symbols in (("vn30", VN30), ("vn50", VN50), ("vn100", vn100)):
        path = os.path.join(data_dir, f"universe_{name}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(symbols, fh, indent=1)
        print(f"{name}: {len(symbols)} symbols -> {path}")


if __name__ == "__main__":
    write_universes()