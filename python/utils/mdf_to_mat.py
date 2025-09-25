import os
import argparse
import pandas as pd
import numpy as np
from asammdf import MDF
from scipy.io import savemat
from typing import Optional, Tuple

def remove_mdf_suffixes(channel_names: list) -> list:
    """Removes suffixes from MDF channel names (like /ETK, /CAN)."""
    cleaned_names = []
    for name in channel_names:
        parts = name.split('\\')
        cleaned = parts[0] if parts else name
        cleaned_names.append(cleaned)
    return cleaned_names

def mdf_unit_to_tact_unit(mdf_unit: str) -> str:
    """Maps MDF units to Tact units."""
    if not mdf_unit or mdf_unit == '':
        return 'u[1]'
    unit_map = {
        '[%]': '%', '%': '%', 'perc': '%', 'Perc': '%',
        '[Nm]': 'nm', 'Nm': 'nm', 'nm': 'nm',
        '[°C]': 'degc', '°C': 'degc',
        '[degC]': 'degc', 'degC': 'degc',
        '[bar]': 'bar', 'bar': 'bar',
        '[mbar]': 'mbar', 'mbar': 'mbar',
        '[Pa]': 'pa', 'Pa': 'pa',
        '[hPa]': 'hpa', 'hPa': 'hpa',
        '[rpm]': 'rpm', 'RPM': 'rpm',
        'g': 'g', 'G': 'g', '[g]': 'g',
        '[-]': 'u[1]', '-': 'u[1]', '': 'u[1]',
        '[s]': 's', 's': 's',
        '[m/s2]': 'ms-2', 'm/s2': 'ms-2',
        '[ms]': 'ms', 'ms': 'ms',
        '[km/h]': 'kph', 'km/h': 'kph',
        '[mph]': 'kph', 'mph': 'kph',
        '[V]': 'v', 'V': 'v',
        '[W]': 'w', 'W': 'w',
        '[kW]': 'kw', 'kW': 'kw',
        '[kg]': 'kg', 'kg': 'kg',
    }
    return unit_map.get(mdf_unit, 'u[1]')

def convert_tact_unit(data_in: np.ndarray, unit_in: str, unit_out: str, full_name: str) -> Tuple[np.ndarray, bool]:
    """Convert data between known units."""
    if unit_in == unit_out:
        return data_in, False
    cnv_name = f"{unit_in}>>{unit_out}"
    convert = True
    if cnv_name == 'ms-2>>g':
        data_out = data_in / 9.80665
    elif cnv_name in ['mbar>>bar', 'hpa>>bar', 'ms>>s']:
        data_out = data_in / 1000
    elif cnv_name in ['bar>>mbar', 's>>ms']:
        data_out = data_in * 1000
    else:
        print(f'"{full_name}" - Could not convert "{cnv_name}". Passing original value.')
        data_out = data_in
        convert = False
    return data_out, convert

def mdf_to_mat(dat_path: str,
               signal_database: Optional[pd.DataFrame] = None,
               req: Optional[list] = None,
               m: Optional[MDF] = None,
               data: Optional[pd.DataFrame] = None,
               resample: Optional[float] = None,
               convert_to_tact_unit: bool = True,
               load_signals: bool = True,
               waitbar: bool = False):
    """
    Reads MDF (.dat/.mf4) into a pandas DataFrame using raster filtering:
    1. Match raster names from CSV against MF4 group names.
    2. Inside group, find signals aligning with synonym.
    """

    data_out = data if data is not None else pd.DataFrame()
    summary  = pd.DataFrame()
    used     = pd.DataFrame()
    raster   = pd.DataFrame(columns=['Variable', 'Raster'])
    mods     = pd.DataFrame(columns=['Signal', 'From', 'To'])

    dat_path = os.path.abspath(dat_path)
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"File '{dat_path}' does not exist")

    if m is None or not isinstance(m, MDF):
        print(f"    > Processing MDF file: {dat_path}")
        m = MDF(dat_path)

    if not load_signals:
        return data_out, m, [], summary, used, raster, mods

    # Collect MDF signals
    channels_db = m.channels_db
    sigs_data = []
    for ch_name, value in channels_db.items():
        if len(value) < 1:
            continue
        group_idx = value[0][0] if isinstance(value[0], tuple) else value[0]
        ch_idx = value[1] if len(value) > 1 else 0
        sigs_data.append({'ChannelName': ch_name, 'GroupIndex': group_idx, 'ChannelIndex': ch_idx})
    sigs = pd.DataFrame(sigs_data)

    # Clean names
    sigs_copy = sigs.copy()
    sigs_copy['ChannelName'] = [remove_mdf_suffixes([name])[0] for name in sigs_copy['ChannelName']]

    # Build group index -> raster name map
    group_to_name = {
        i: (getattr(g, "comment", None) or getattr(g.channel_group, "acq_name", None) or f"group_{i}")
        for i, g in enumerate(m.groups)
    }
    sigs['RasterName'] = sigs['GroupIndex'].map(group_to_name)
    sigs_copy['RasterName'] = sigs_copy['GroupIndex'].map(group_to_name)

    # Clean names
    sigs_copy['ChannelName'] = [remove_mdf_suffixes([name])[0] for name in sigs_copy['ChannelName']]

    # ✅ Add a base name column (last segment after '/' or '\')
    sigs_copy['ChannelBase'] = sigs_copy['ChannelName'].str.split(r'[\\/]').str[-1]

    signals_read, to_read = [], []

    # --- Core Logic: check raster groups ---
    if signal_database is not None:
        for _, row in signal_database.iterrows():
            generic_name = row['genericname']
            raster_val = str(row['raster']).strip()
            synonym_val = str(row['synonym']).strip()

            if not raster_val or not synonym_val:
                continue

            # Check if raster exists in MF4
            if not any(raster_val.lower() == str(rn).lower() for rn in sigs_copy['RasterName']):
                print(f"Raster group '{raster_val}' not found in MF4 → skipping {generic_name}")
                continue

            syns = [s.strip() for s in synonym_val.split(',') if s.strip()]

            # Search within the correct raster group
            # Find all groups with this raster name
            matching_groups = sigs_copy[sigs_copy['RasterName'].str.lower() == raster_val.lower()]['GroupIndex'].unique()

            found = False
            for group_idx in matching_groups:
                group_channels = sigs_copy[sigs_copy['GroupIndex'] == group_idx]

                # 🔍 Always enforce exact match
                matches = group_channels[
                    group_channels['ChannelName'].str.lower() == synonym_val.lower()
                ]

                if not matches.empty:
                    best_loc = matches.index[0]
                    ch_name = sigs.at[best_loc, 'ChannelName']
                    to_read.append({
                        'FullName': ch_name,
                        'GroupIndex': group_idx,
                        'GenericName': generic_name,
                        'Raster': raster_val
                    })
                    signals_read.append(generic_name)
                    found = True
                    break

            if not found:
                print(f"    ⚠️ No match found for {generic_name} in raster '{raster_val}'")

    # --- Read signals ---
    for _, row in pd.DataFrame(to_read).iterrows():
        full_name = row['FullName']
        group_idx = row['GroupIndex']
        generic_name = row['GenericName']
        raster_val = row['Raster']
        try:
            sig_data = m.get(full_name, group=group_idx)
            timestamps, samples = sig_data.timestamps, sig_data.samples
            if len(timestamps) == 0:
                continue

            temp_df = pd.DataFrame({generic_name: samples}, index=timestamps)

            if convert_to_tact_unit and signal_database is not None:
                row_idx = signal_database[signal_database['genericname'].str.lower() == generic_name.lower()].index
                if not row_idx.empty:
                    mdf_unit = sig_data.unit if sig_data.unit else 'u[1]'
                    tact_unit = signal_database.at[row_idx[0], 'tactunit'] if 'tactunit' in signal_database.columns else 'u[1]'
                    if mdf_unit != tact_unit:
                        samples_converted, did_convert = convert_tact_unit(
                            samples, mdf_unit_to_tact_unit(mdf_unit), tact_unit, full_name)
                        temp_df[generic_name] = samples_converted
                        if did_convert:
                            mods = pd.concat(
                                [mods, pd.DataFrame({'Signal': [generic_name], 'From': [mdf_unit], 'To': [tact_unit]})],
                                ignore_index=True)

            if resample is not None:
                resample_steps = np.arange(timestamps[0], timestamps[-1] + resample / 2, resample)
                temp_df = temp_df.reindex(resample_steps, method='nearest')

            if data_out.empty:
                data_out = temp_df
            else:
                if resample is not None:
                    data_out = data_out.reindex(resample_steps, method='nearest').join(
                        temp_df.reindex(resample_steps, method='nearest'), how='outer')
                else:
                    data_out = data_out.join(temp_df, how='outer').interpolate(method='linear')

            r = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else np.inf
            raster = pd.concat([raster, pd.DataFrame({'Variable': [generic_name], 'Raster': [raster_val]})],
                               ignore_index=True)

        except Exception as e:
            print(f"Error reading {full_name}: {e}")

    # Build summary + used DataFrames
    if req is not None:
        read_signals = data_out.columns.tolist()
        not_read = [r for r in req if r not in read_signals]
        summary = pd.DataFrame({
            'Requested': req,
            'Read': [r if r in read_signals else '' for r in req],
            'NotRead': [r if r in not_read else '' for r in req]
        })
    else:
        summary = pd.DataFrame({'Read': signals_read})

    used = pd.DataFrame(to_read).reindex(columns=['GenericName', 'FullName', 'Raster']) if to_read else \
        pd.DataFrame(columns=['GenericName', 'FullName', 'Raster'])

    if not data_out.empty and data_out.isna().any().any():
        data_out = data_out.interpolate(method='linear')

    return data_out, m, sigs['ChannelName'].tolist(), summary, used, raster, mods

# --- Main CLI ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract signals from MDF file to .mat')
    parser.add_argument('dat_path', type=str, help='Path to MDF file')
    parser.add_argument('--signal_db', type=str, help='Path to signal database CSV or Excel file')
    parser.add_argument('--req', nargs='+', help='List of requested signals')
    parser.add_argument('--resample', type=float, help='Resample rate in seconds')
    parser.add_argument('--no_convert', action='store_true', help='Disable unit conversion')
    args = parser.parse_args()

    args.dat_path = os.path.abspath(args.dat_path)

    if args.signal_db:
        if args.signal_db.endswith('.csv'):
            signal_database = pd.read_csv(args.signal_db).rename(columns=str.lower)
        elif args.signal_db.endswith('.xlsx'):
            signal_database = pd.read_excel(args.signal_db).rename(columns=str.lower)
        else:
            raise ValueError("Signal database must be a .csv or .xlsx file")
    else:
        signal_database = None

    req = args.req if args.req else None
    convert_to_tact_unit = not args.no_convert

    data, m, sigs, summary, used, raster, mods = mdf2matConv(
        dat_path=args.dat_path,
        signal_database=signal_database,
        req=req,
        resample=args.resample,
        convert_to_tact_unit=convert_to_tact_unit
    )

    # Save only mapped signals
    if not data.empty and signal_database is not None:
        mat_file = os.path.splitext(args.dat_path)[0] + '.mat'
        try:
            signals_struct = {'time': data.index.values.reshape(-1, 1)}
            mapped_names = signal_database['genericname'].str.strip().unique().tolist()
            for col in data.columns:
                if col in mapped_names:
                    valid_name = col.replace('.', '_').replace('-', '_').replace(' ', '_')
                    signals_struct[valid_name] = data[col].values.reshape(-1, 1)

            if len(signals_struct) > 1:
                savemat(mat_file, {'signalMat': signals_struct})
                # print(f"    Saved mapped signals to {mat_file}")
            else:
                print("    Warning: No mapped signals found to save in MAT file.")
        except Exception as e:
            print(f"    Error saving .mat file: {e}")

    #print("    Processing complete.")
