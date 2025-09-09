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
    parser.add_argument("signaldb", type=str, help="Path to SignalDatabase CSV file")
    args = parser.parse_args()

    print("==== DEBUG: Arguments ====")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    print(f"Resample: {args.resample}")
    print(f"SignalDB: {args.signaldb}")
    print("==========================")

    # Load MDF file
    print("[DEBUG] Loading MDF file...")
    mdf = MDF(args.input)
    print(f"[DEBUG] MDF file loaded with {len(mdf.channels_db)} channels")

    # Determine signals to extract
    if args.signaldb:
        print(f"[DEBUG] Trying to load SignalDatabase from {args.signaldb}")
        try:
            db = pd.read_csv(args.signaldb)
            print(f"[DEBUG] SignalDatabase columns: {list(db.columns)}")
            if 'GenericName' in db.columns:
                sigs = db['GenericName'].dropna().unique().tolist()
                print(f"[DEBUG] Using GenericName, found {len(sigs)} signals")
            elif 'TactName' in db.columns:
                sigs = db['TactName'].dropna().unique().tolist()
                print(f"[DEBUG] Using TactName, found {len(sigs)} signals")
            else:
                sigs = []
                print("[WARN] No GenericName or TactName column found in SignalDatabase")
        except Exception as e:
            print(f"[ERROR] Failed to load SignalDatabase: {e}")
            sigs = list(mdf.channels_db.keys())  # Fallback to all signals
            print(f"[DEBUG] Falling back to all {len(sigs)} signals from MDF")
    else:
        sigs = list(mdf.channels_db.keys())  # Default to all signals if no SignalDatabase
        print(f"[DEBUG] No SignalDatabase provided, using all {len(sigs)} signals from MDF")

    # Ensure sigs is a list
    if not isinstance(sigs, list):
        sigs = [sigs]

    print(f"[DEBUG] Final signal list length: {len(sigs)}")

    dfs = []
    for sig in sigs:
        if sig in mdf.channels_db:
            print(f"[DEBUG] Extracting signal: {sig}")
            df = mdf.get(sig).to_dataframe()
            dfs.append(df)
        else:
            print(f"[WARN] Signal {sig} not found in {args.input}")

    if not dfs:
        print("[ERROR] No signals loaded")
        sys.exit(1)

    print(f"[DEBUG] Concatenating {len(dfs)} DataFrames")
    data = pd.concat(dfs, axis=1)
    print(f"[DEBUG] Combined DataFrame shape: {data.shape}")

    # Resample if requested
    if args.resample > 0:
        print(f"[DEBUG] Resampling with step {args.resample}s")
        data = data.resample(f"{args.resample}S").nearest()
        print(f"[DEBUG] Data shape after resample: {data.shape}")

    # Fill gaps
    print("[DEBUG] Filling gaps with nearest values")
    data = data.fillna(method="nearest")

    # Convert to dict for MATLAB .mat export
    mat_dict = {}
    for col in data.columns:
        mat_dict[col] = data[col].to_numpy()
    print(f"[DEBUG] Prepared MAT dict with {len(mat_dict)} variables")

    # Also include time vector
    mat_dict["time"] = data.index.astype(np.int64) / 1e9  # ns → s
    print("[DEBUG] Time vector added to MAT dict")

    # Save to .mat
    sio.savemat(args.output, mat_dict)
    print(f"[OK] Saved {args.output} with {len(data)} samples and {len(data.columns)} signals.")

if __name__ == "__main__":
    main()
