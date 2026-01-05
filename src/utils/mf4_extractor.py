import os
import argparse
import pandas as pd
import numpy as np
from asammdf import MDF, Signal
from typing import Optional, Tuple


# ================================================================
# Utility functions
# ================================================================

def remove_mdf_suffixes(channel_names: list) -> list:
    """Removes suffixes from MDF channel names (like /ETK, /CAN)."""
    cleaned_names = []
    for name in channel_names:
        parts = name.split("\\")
        cleaned = parts[0] if parts else name
        cleaned_names.append(cleaned)
    return cleaned_names


def mdf_unit_to_tact_unit(mdf_unit: str) -> str:
    """Maps MDF units to Tact units."""
    if not mdf_unit or mdf_unit == "":
        return "u[1]"
    unit_map = {
        "[%]": "%", "%": "%", "perc": "%", "Perc": "%",
        "[Nm]": "nm", "Nm": "nm", "nm": "nm",
        "[°C]": "degc", "°C": "degc", "[degC]": "degc", "degC": "degc",
        "[bar]": "bar", "bar": "bar",
        "[mbar]": "mbar", "mbar": "mbar",
        "[Pa]": "pa", "Pa": "pa",
        "[hPa]": "hpa", "hPa": "hpa",
        "[rpm]": "rpm", "RPM": "rpm",
        "g": "g", "G": "g", "[g]": "g",
        "[-]": "u[1]", "-": "u[1]", "": "u[1]",
        "[s]": "s", "s": "s",
        "[m/s2]": "ms-2", "m/s2": "ms-2",
        "[ms]": "ms", "ms": "ms",
        "[km/h]": "kph", "km/h": "kph",
        "[mph]": "kph", "mph": "kph",
        "[V]": "v", "V": "v",
        "[W]": "w", "W": "w",
        "[kW]": "kw", "kW": "kw",
        "[kg]": "kg", "kg": "kg",
    }
    return unit_map.get(mdf_unit, "u[1]")


def convert_tact_unit(data_in: np.ndarray, unit_in: str, unit_out: str, full_name: str) -> Tuple[np.ndarray, bool]:
    """Convert data between known units."""
    if unit_in == unit_out:
        return data_in, False
    cnv_name = f"{unit_in}>>{unit_out}"
    convert = True
    if cnv_name == "ms-2>>g":
        data_out = data_in / 9.80665
    elif cnv_name in ["mbar>>bar", "hpa>>bar", "ms>>s"]:
        data_out = data_in / 1000
    elif cnv_name in ["bar>>mbar", "s>>ms"]:
        data_out = data_in * 1000
    else:
        print(f'"{full_name}" - Could not convert "{cnv_name}". Passing original value.')
        data_out = data_in
        convert = False
    return data_out, convert


# ================================================================
# Core extractor
# ================================================================

def mf4_extractor(
    dat_path: str,
    signal_database: Optional[pd.DataFrame] = None,
    req: Optional[list] = None,
    m: Optional[MDF] = None,
    data: Optional[pd.DataFrame] = None,
    resample: Optional[float] = None,
    convert_to_tact_unit: bool = True,
    load_signals: bool = True,
    waitbar: bool = False,
):
    """
    Reads MDF (.dat/.mf4), extracts signals into a pandas DataFrame.
    Returns:
        data_out, mdf_object, all_channels, summary, used_signals, raster_info, unit_conversions
    """

    data_out = data if data is not None else pd.DataFrame()
    summary = pd.DataFrame()
    used = pd.DataFrame()
    raster = pd.DataFrame(columns=["Variable", "Raster"])
    mods = pd.DataFrame(columns=["Signal", "From", "To"])

    dat_path = os.path.abspath(dat_path)
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"File '{dat_path}' does not exist")

    if m is None or not isinstance(m, MDF):
        print(f"    > Processing MDF file: {dat_path}")
        m = MDF(dat_path)

    if not load_signals:
        return data_out, m, [], summary, used, raster, mods

    # --- Collect MDF signals ---
    channels_db = m.channels_db
    sigs_data = []
    for ch_name, value in channels_db.items():
        if len(value) < 1:
            continue
        group_idx = value[0][0] if isinstance(value[0], tuple) else value[0]
        ch_idx = value[1] if len(value) > 1 else 0
        sigs_data.append({"ChannelName": ch_name, "GroupIndex": group_idx, "ChannelIndex": ch_idx})
    sigs = pd.DataFrame(sigs_data)

    # --- Clean names ---
    sigs_copy = sigs.copy()
    sigs_copy["ChannelName"] = (
        sigs_copy["ChannelName"].astype(str).str.split("\\\\", n=1).str[0]
    )

    # --- Build group index -> raster name map ---
    group_to_name = {
        i: (
            getattr(g, "comment", None)
            or getattr(g.channel_group, "acq_name", None)
            or f"group_{i}"
        )
        for i, g in enumerate(m.groups)
    }
    sigs["RasterName"] = sigs["GroupIndex"].map(group_to_name)
    sigs_copy["RasterName"] = sigs_copy["GroupIndex"].map(group_to_name)

    # --- Add base name column ---
    sigs_copy["ChannelBase"] = sigs_copy["ChannelName"].str.split(r"[\\/]").str[-1]

    signals_read, to_read = [], []
    temp_frames = []
    min_ts = None
    max_ts = None
    raster_rows = []
    mods_rows = []

    signal_db = None
    tactunit_map = {}
    generic_names = set()
    if signal_database is not None:
        signal_db = signal_database.copy()
        signal_db.columns = signal_db.columns.str.lower()
        if "genericname" in signal_db.columns:
            generic_names = {
                str(g).strip().lower()
                for g in signal_db["genericname"]
                if pd.notna(g)
            }
        if "genericname" in signal_db.columns and "tactunit" in signal_db.columns:
            tactunit_map = {
                str(g).strip().lower(): t
                for g, t in zip(signal_db["genericname"], signal_db["tactunit"])
                if pd.notna(g) and pd.notna(t)
            }

    # ================================================================
    # Match requested signals to MDF channels
    # ================================================================
    if signal_database is not None:
        raster_groups = {}
        for group_idx, group_rows in sigs_copy.groupby("GroupIndex", sort=False):
            if group_rows.empty:
                continue
            raster_name = str(group_rows["RasterName"].iloc[0]).strip().lower()
            channel_map = dict(zip(group_rows["ChannelName"].str.lower(), group_rows.index))
            raster_groups.setdefault(raster_name, []).append((group_idx, channel_map))

        for row in signal_db.itertuples(index=False):
            generic_name = getattr(row, "genericname", None)
            raster_val = getattr(row, "raster", None)
            synonym_val = getattr(row, "synonym", None)

            if pd.isna(generic_name) or pd.isna(raster_val) or pd.isna(synonym_val):
                continue
            generic_name = str(generic_name).strip()
            raster_val = str(raster_val).strip()
            synonym_val = str(synonym_val).strip()
            if not raster_val or not synonym_val or not generic_name:
                continue

            raster_key = raster_val.lower()
            if raster_key not in raster_groups:
                print(f"Raster group '{raster_val}' not found in MF4 → skipping {generic_name}")
                continue

            matching_groups = raster_groups.get(raster_key, [])
            found = False
            synonym_key = synonym_val.lower()
            for group_idx, channel_map in matching_groups:
                if synonym_key in channel_map:
                    best_loc = channel_map[synonym_key]
                    ch_name = sigs.at[best_loc, "ChannelName"]
                    to_read.append(
                        {
                            "FullName": ch_name,
                            "GroupIndex": group_idx,
                            "GenericName": generic_name,
                            "Raster": raster_val,
                        }
                    )
                    signals_read.append(generic_name)
                    found = True
                    break

            if not found:
                print(f"    ⚠️ No match for {generic_name} in raster '{raster_val}'")

    # ================================================================
    # Read each matched signal
    # ================================================================
    for row in to_read:
        full_name = row["FullName"]
        group_idx = row["GroupIndex"]
        generic_name = row["GenericName"]
        raster_val = row["Raster"]

        try:
            sig_data = m.get(full_name, group=group_idx)
            timestamps, samples = sig_data.timestamps, sig_data.samples
            if len(timestamps) == 0:
                continue

            # --- Handle duplicate timestamps ---
            index = pd.Index(timestamps)
            temp_df = pd.DataFrame({generic_name: samples}, index=index)
            dup_mask = index.duplicated(keep="first")
            if dup_mask.any():
                dup_count = int(dup_mask.sum())
                print(
                    f"⚠️ Duplicate timestamps detected in {full_name} "
                    f"({dup_count} duplicates) → keeping first occurrence"
                )
                temp_df = temp_df.loc[~dup_mask]

            # --- Optional unit conversion ---
            if convert_to_tact_unit and signal_database is not None:
                generic_key = str(generic_name).strip().lower()
                if generic_key in generic_names:
                    mdf_unit = sig_data.unit if sig_data.unit else "u[1]"
                    tact_unit = tactunit_map.get(generic_key, "u[1]")
                    if tact_unit is None or (isinstance(tact_unit, float) and np.isnan(tact_unit)):
                        tact_unit = "u[1]"
                    if mdf_unit != tact_unit:
                        samples_converted, did_convert = convert_tact_unit(
                            samples,
                            mdf_unit_to_tact_unit(mdf_unit),
                            tact_unit,
                            full_name,
                        )
                        temp_df[generic_name] = samples_converted
                        if did_convert:
                            mods_rows.append({"Signal": generic_name, "From": mdf_unit, "To": tact_unit})

            temp_frames.append(temp_df)
            if resample is not None:
                min_ts = index[0] if min_ts is None else min(min_ts, index[0])
                max_ts = index[-1] if max_ts is None else max(max_ts, index[-1])

            # --- Record raster info ---
            raster_rows.append({"Variable": generic_name, "Raster": raster_val})

        except Exception as e:
            print(f"Error reading {full_name}: {e}")

    # ================================================================
    # Summary
    # ================================================================
    frames = []
    if data_out is not None and not data_out.empty:
        frames.append(data_out)
    frames.extend(temp_frames)

    if frames:
        if resample is None:
            data_out = pd.concat(frames, axis=1, join="outer").sort_index()
        elif min_ts is not None and max_ts is not None:
            resample_steps = np.arange(min_ts, max_ts + resample / 2, resample)
            resampled_frames = [df.reindex(resample_steps, method="nearest") for df in frames]
            data_out = pd.concat(resampled_frames, axis=1)

    if req is not None:
        read_signals = data_out.columns.tolist()
        not_read = [r for r in req if r not in read_signals]
        summary = pd.DataFrame({
            "Requested": req,
            "Read": [r if r in read_signals else "" for r in req],
            "NotRead": [r if r in not_read else "" for r in req],
        })
    else:
        summary = pd.DataFrame({"Read": signals_read})

    used = (
        pd.DataFrame(to_read).reindex(columns=["GenericName", "FullName", "Raster"])
        if to_read
        else pd.DataFrame(columns=["GenericName", "FullName", "Raster"])
    )
    raster = (
        pd.DataFrame(raster_rows, columns=["Variable", "Raster"])
        if raster_rows
        else pd.DataFrame(columns=["Variable", "Raster"])
    )
    mods = (
        pd.DataFrame(mods_rows, columns=["Signal", "From", "To"])
        if mods_rows
        else pd.DataFrame(columns=["Signal", "From", "To"])
    )

    if not data_out.empty and data_out.isna().any().any():
        data_out = data_out.interpolate(method="linear")

    # ================================================================
    # Final output
    # ================================================================
    if not data_out.empty:
        print(f"✅ Extracted {len(data_out.columns)} signal(s) from {os.path.basename(dat_path)}")
    else:
        print(f"⚠️ No valid signals extracted from {os.path.basename(dat_path)}")

    return data_out, m, sigs["ChannelName"].tolist(), summary, used, raster, mods


# ================================================================
# CLI interface
# ================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract signals from MDF file to .mf4")
    parser.add_argument("dat_path", type=str, help="Path to MDF file")
    parser.add_argument("--signal_db", type=str, help="Path to signal database CSV or Excel file")
    parser.add_argument("--req", nargs="+", help="List of requested signals")
    parser.add_argument("--resample", type=float, help="Resample rate in seconds")
    parser.add_argument("--no_convert", action="store_true", help="Disable unit conversion")
    args = parser.parse_args()

    args.dat_path = os.path.abspath(args.dat_path)

    # Load signal database
    if args.signal_db:
        if args.signal_db.endswith(".csv"):
            signal_database = pd.read_csv(args.signal_db).rename(columns=str.lower)
        elif args.signal_db.endswith(".xlsx"):
            signal_database = pd.read_excel(args.signal_db).rename(columns=str.lower)
        else:
            raise ValueError("Signal database must be a .csv or .xlsx file")
    else:
        signal_database = None

    req = args.req if args.req else None
    convert_to_tact_unit = not args.no_convert

    mf4_extractor(
        dat_path=args.dat_path,
        signal_database=signal_database,
        req=req,
        resample=args.resample,
        convert_to_tact_unit=convert_to_tact_unit,
    )
