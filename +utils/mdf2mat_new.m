#!/usr/bin/env python3
import sys
import argparse
import scipy.io as sio
import pandas as pd
import numpy as np
from asammdf import MDF

def main():
    parser = argparse.ArgumentParser(description="Convert MF4 to MAT via asammdf")
    parser.add_argument("input", help="Input MF4 file")
    parser.add_argument("output", help="Output MAT file")
    parser.add_argument("resample", type=float, help="Resample step in seconds (0 = no resample)")
    parser.add_argument("--signaldb", type=str, help="Path to SignalDatabase CSV file")
    args = parser.parse_args()

    print(f"Input file path: {args.input}")

    # Load MDF file
    mdf = MDF(args.input)

    # Determine signals to extract
    if args.signaldb:
        try:
            db = pd.read_csv(args.signaldb)
            if 'GenericName' in db.columns:
                sigs = db['GenericName'].dropna().unique().tolist()
            elif 'TactName' in db.columns:
                sigs = db['TactName'].dropna().unique().tolist()
            else:
                sigs = []
        except Exception as e:
            print(f"[ERROR] Failed to load SignalDatabase: {e}")
            sigs = list(mdf.channels_db.keys())  # Fallback to all signals
    else:
        sigs = list(mdf.channels_db.keys())  # Default to all signals if no SignalDatabase

    # Ensure sigs is a list
    if not isinstance(sigs, list):
        sigs = [sigs]

    dfs = []
    for sig in sigs:
        if sig in mdf.channels_db:
            df = mdf.get(sig).to_dataframe()
            dfs.append(df)
        else:
            print(f"[WARN] Signal {sig} not found in {args.input}")

    if not dfs:
        print("[ERROR] No signals loaded")
        sys.exit(1)

    data = pd.concat(dfs, axis=1)

    # Resample if requested
    if args.resample > 0:
        data = data.resample(f"{args.resample}S").nearest()

    # Fill gaps
    data = data.fillna(method="nearest")

    # Convert to dict for MATLAB .mat export
    mat_dict = {}
    for col in data.columns:
        mat_dict[col] = data[col].to_numpy()

    # Also include time vector
    mat_dict["time"] = data.index.astype(np.int64) / 1e9  # ns → s

    # Save to .mat
    sio.savemat(args.output, mat_dict)
    print(f"[OK] Saved {args.output} with {len(data)} samples and {len(data.columns)} signals.")

if __name__ == "__main__":
    main()
