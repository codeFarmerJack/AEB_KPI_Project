import os
import argparse
import pandas as pd
import numpy as np
from asammdf import MDF
from scipy.io import savemat
from typing import Optional, Tuple, Dict, Any, Union
import warnings

def remove_mdf_suffixes(channel_names: list) -> list:
    """
    Removes suffixes from the end of MDF channel names, e.g., /ETK, /CAN.
    """
    cleaned_names = []
    for name in channel_names:
        # Split by '\' and take the first part
        parts = name.split('\\')
        cleaned = parts[0] if parts else name
        cleaned_names.append(cleaned)
    return cleaned_names

def mdf_unit_to_tact_unit(mdf_unit: str) -> str:
    """
    Maps MDF units to Tact units.
    """
    if not mdf_unit or mdf_unit == '':
        return 'u[1]'
    
    unit_map = {
        '[%]': '%', '%': '%', 'perc': '%', 'Perc': '%',
        '[Nm]': 'nm', 'Nm': 'nm', 'nm': 'nm',
        '[°C]': 'degc', '°C': 'degc', '[degree Celsius]': 'degc', 'degree Celsius': 'degc',
        '[degC]': 'degc', 'degC': 'degc', '[degc]': 'degc', 'degc': 'degc', 'deg. C': 'degc', 'Deg. C': 'degc',
        '[°C/s]': 'degc-1', '°C/s': 'degc-1',
        '[bar]': 'bar', 'bar': 'bar', '[Bar]': 'bar', 'Bar': 'bar',
        '[mbar]': 'mbar', 'mbar': 'mbar',
        '[Pa]': 'pa', 'Pa': 'pa',
        '[hPa]': 'hpa', 'hPa': 'hpa',
        '[U/min]': 'rpm', 'U/min': 'rpm', '[1/min]': 'rpm', '1/min': 'rpm', '[RPM]': 'rpm', 'RPM': 'rpm',
        '[rpm]': 'rpm', 'rpm': 'rpm', 'Shaft Speed in RPM': 'rpm',
        '[U/(min*s)]': 'rpms-1', 'U/(min*s)': 'rpms-1', 'rpm/s': 'rpms-1', 'Rpm/s': 'rpms-1', 'RPM/s': 'rpms-1',
        'g': 'g', 'G': 'g', '[g]': 'g', '[G]': 'g',
        '[-]': 'u[1]', '-': 'u[1]', '': 'u[1]', 'gear': 'u[1]', 'Gear': 'u[1]', '1': 'u[1]',
        '[s]': 's', 's': 's',
        '[m_s2]': 'ms-2', 'm_s2': 'ms-2', '[m/s2]': 'ms-2', 'm/s2': 'ms-2', '[m/s^2]': 'ms-2', 'm/s^2': 'ms-2',
        '[1/s^2]': 'ms-2', '1/s^2': 'ms-2', 'm_s_s': 'ms-2', 'm/s/s': 'ms-2',
        '[ms]': 'ms', 'ms': 'ms',
        '[km/h]': 'kph', 'km/h': 'kph', '[kph]': 'kph', 'kph': 'kph',
        '[m/h]': 'kph', 'm/h': 'kph', '[mph]': 'kph', 'mph': 'kph',
        '[VER]': 'ver', 'VER': 'ver', '[ver]': 'ver', 'ver': 'ver',
        '[Volt]': 'v', 'Volt': 'v', '[V]': 'v', 'V': 'v',
        '[W]': 'w', 'W': 'w',
        '[kW]': 'kw', 'kW': 'kw',
        '[kg]': 'kg', 'kg': 'kg',
    }
    
    if mdf_unit in unit_map:
        return unit_map[mdf_unit]
    else:
        print(f'Unit "{mdf_unit}" not found.')
        return 'u[1]'

def convert_tact_unit(data_in: np.ndarray, unit_in: str, unit_out: str, full_name: str) -> Tuple[np.ndarray, bool]:
    """
    Converts data from input unit to output unit.
    """
    if unit_in == unit_out:
        return data_in, False
    
    # Generate conversion name for switch/case equivalent
    cnv_name = f"{unit_in}>>{unit_out}"
    
    convert = True
    if cnv_name == 'ms-2>>g':
        data_out = data_in / 9.80665  # Assuming config.Math.G = 9.80665
    elif cnv_name in ['mbar>>bar', 'hpa>>bar', 'ms>>s']:
        data_out = data_in / 1000
    elif cnv_name in ['bar>>mbar', 's>>ms']:
        data_out = data_in * 1000
    else:
        print(f'"{full_name}" - Could not convert "{cnv_name}". Passing original value.')
        data_out = data_in
        convert = False
    
    return data_out, convert

def mdf2matSim(dat_path: str,
               signal_database: Optional[pd.DataFrame] = None,
               req: Optional[list] = None,
               m: Optional[MDF] = None,
               data: Optional[pd.DataFrame] = None,
               resample: Optional[float] = None,
               convert_to_tact_unit: bool = True,
               load_signals: bool = True,
               waitbar: bool = False) -> Tuple[pd.DataFrame, MDF, list, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Reads MDF objects (.dat/.mf4) into a pandas DataFrame (timetable equivalent).
    
    Parameters:
    -----------
    dat_path : str
        Path to the MDF file (required).
    signal_database : pd.DataFrame, optional
        Database of signals with generic names, synonyms, units, etc.
    req : list, optional
        List of requested signal names.
    m : MDF, optional
        Pre-loaded MDF object.
    data : pd.DataFrame, optional
        Existing DataFrame for appending signals.
    resample : float, optional
        Resampling rate in seconds.
    convert_to_tact_unit : bool, default True
        Convert signals to Tact units.
    load_signals : bool, default True
        Whether to load signals or abort after reading MDF.
    waitbar : bool, default False
        Show progress (simulated in console).
    
    Returns:
    --------
    data : pd.DataFrame
        Extracted signal data with time index.
    m : MDF
        MDF object.
    sigs : list
        List of signals in the file.
    summary : pd.DataFrame
        Summary of requested, read, and not-read signals.
    used : pd.DataFrame
        Details of exact signals read.
    raster : pd.DataFrame
        Original raster rates.
    mods : pd.DataFrame
        Unit conversion logs.
    """
    data_out = data if data is not None else pd.DataFrame()
    summary = pd.DataFrame()
    used = pd.DataFrame()
    raster = pd.DataFrame(columns=['Variable', 'Raster'])
    mods = pd.DataFrame(columns=['Signal', 'From', 'To'])

    # Ensure absolute path
    dat_path = os.path.abspath(dat_path)
    if not os.path.exists(dat_path):
        raise FileNotFoundError(f"File '{dat_path}' does not exist")

    if m is None or not isinstance(m, MDF):
        print(f"Reading MDF file: {dat_path}")
        m = MDF(dat_path)

    if not load_signals:
        return data_out, m, [], summary, used, raster, mods

    # Get list of signals in file
    channels_db = m.channels_db  # Dictionary of {channel_name: (group_index, channel_index, ...)}
    sigs_data = []
    for ch_name, value in channels_db.items():
        if len(value) < 1:
            continue  # Skip if no group index
        if isinstance(value[0], tuple):
            group_idx = value[0][0]  # Take the first element if group_idx is a tuple
        else:
            group_idx = value[0]
        # Handle channel index
        if len(value) > 1:
            ch_idx = value[1]  # Use second element if available
        else:
            ch_idx = 0  # Default to 0 if channel index is not provided
        sigs_data.append({
            'ChannelName': ch_name,
            'ChannelGroupNumber': group_idx + 1,  # Convert to 1-based indexing
            'ChannelIndex': ch_idx
        })
    sigs = pd.DataFrame(sigs_data)

    # Create copy and remove suffixes
    sigs_copy = sigs.copy()
    sigs_copy['ChannelName'] = [remove_mdf_suffixes([name])[0] for name in sigs_copy['ChannelName']]

    if data_out.empty:
        n_vars = 0
        raster_list = []
    else:
        n_vars = len(data_out.columns)
        raster_list = [np.mean(np.diff(data_out.index)) for _ in range(n_vars)]

    signals_read = []

    # Determine signals to read
    if signal_database is not None:
        if req is not None:
            # Use req as primary list, mapped through signal_database
            ls = req
        else:
            # Fall back to signal_database if no req provided
            valid_cols = ['genericname']
            if not any(col in signal_database.columns for col in valid_cols):
                raise ValueError("Signal database must contain 'genericname' column")
            ls = signal_database[valid_cols[0]].unique().tolist()
    else:
        ls = req if req is not None else None

    # If no signal database and no req, read all signals
    if signal_database is None and ls is None:
        data_out = pd.DataFrame()
        for i in range(len(m.groups)):
            if m.groups[i].data_size > 0:
                if waitbar:
                    print(f"Processing group {i+1}/{len(m.groups)}")
                try:
                    temp_data = m.get(group_index=i)
                    temp_df = pd.DataFrame(temp_data.samples, index=temp_data.timestamps)
                    temp_df.columns = [col.replace('.', '_') for col in temp_data.samples.dtype.names]
                    if data_out.empty:
                        data_out = temp_df
                    else:
                        data_out = data_out.join(temp_df, how='outer').interpolate(method='linear')
                    r = np.mean(np.diff(temp_data.timestamps)) if len(temp_data.timestamps) > 1 else np.inf
                    raster_list.extend([r] * len(temp_df.columns))
                except Exception as e:
                    print(f"Error reading group {i+1}: {e}")
        summary = pd.DataFrame({'Read': data_out.columns.tolist()})
        used = pd.DataFrame()
        if raster_list:
            raster = pd.DataFrame({'Variable': data_out.columns.tolist(), 'Raster': raster_list})
    else:
        # With signal database or req
        to_read = []
        n = 0
        for i in ls:
            if waitbar:
                print(f"Processing signal {i}")
            locs = signal_database['genericname'].str.lower() == str(i).lower() if signal_database is not None else []
            syns_series = signal_database.loc[locs, 'synonym'] if signal_database is not None and 'synonym' in signal_database.columns else []
            syns = []
            for syn_str in syns_series.dropna():
                syns.extend([s.strip() for s in str(syn_str).split(',') if s.strip()])

            found_match = False
            temp_r = []
            locs_in_sigs = []
            for syn in [i] + syns:  # Include the generic name itself as a potential match
                if not syn:
                    continue
                sig_to_find = syn.replace('.', '_')
                loc = sigs[sigs_copy['ChannelName'].str.lower() == sig_to_find.lower()].index.tolist()
                if loc:
                    locs_in_sigs.extend(loc)
                    if len(loc) > 1:
                        for l in loc:
                            group_num = sigs.at[l, 'ChannelGroupNumber']
                            ch_name = sigs.at[l, 'ChannelName']
                            try:
                                temp_sig = m.get(ch_name, group=group_num - 1, raw=True)
                                if len(temp_sig.timestamps) > 1:
                                    temp_r.append(np.mean(np.diff(temp_sig.timestamps)))
                                else:
                                    temp_r.append(np.inf)
                            except:
                                temp_r.append(np.inf)
                    else:
                        temp_r.append(np.inf)

            if locs_in_sigs:
                min_idx = np.argmin(temp_r)
                best_loc = locs_in_sigs[min_idx]
                ch_name = sigs.at[best_loc, 'ChannelName']
                group_num = sigs.at[best_loc, 'ChannelGroupNumber']
                to_read.append({'FullName': ch_name, 'Channel': group_num, 'GenericName': i})
                signals_read.append(i)
                found_match = True

            if not found_match and signal_database is not None:
                print(f"No match found for {i}")

        if to_read:
            to_read_df = pd.DataFrame(to_read)
            if not data_out.empty:
                existing = to_read_df['GenericName'].isin(data_out.columns)
                to_read_df = to_read_df[~existing]

            for _, row in to_read_df.iterrows():
                full_name = row['FullName']
                group_num = row['Channel'] - 1  # 0-based
                generic_name = row['GenericName']
                try:
                    sig_data = m.get(full_name, group=group_num)
                    timestamps = sig_data.timestamps
                    samples = sig_data.samples
                    if len(timestamps) == 0:
                        continue

                    temp_df = pd.DataFrame({full_name: samples}, index=timestamps)

                    if len(timestamps) > 1:
                        back_time = np.diff(timestamps) < 0
                        if np.any(back_time):
                            locs = np.where(back_time)[0]
                            for loc in locs:
                                e_time = timestamps[loc + 1]
                                err_loc = np.where(timestamps < e_time)[0]
                                r_loc = err_loc < (loc + 1)
                                err_loc_to_remove = err_loc[~r_loc]
                                temp_df = temp_df.drop(temp_df.index[err_loc_to_remove])

                    if temp_df.empty:
                        continue

                    if convert_to_tact_unit and signal_database is not None:
                        row_idx = signal_database[signal_database['synonym'].str.contains(full_name.split('\\')[0], na=False)].index
                        if not row_idx.empty:
                            row_idx = row_idx[0]
                            mdf_unit = m.get(full_name, group=group_num).unit if m.get(full_name, group=group_num).unit else 'u[1]'
                            tact_unit = signal_database.at[row_idx, 'tactunit'] if 'tactunit' in signal_database.columns else 'u[1]'
                            if mdf_unit != tact_unit:
                                samples_converted, did_convert = convert_tact_unit(samples, mdf_unit_to_tact_unit(mdf_unit), tact_unit, full_name)
                                temp_df[full_name] = samples_converted
                                if did_convert:
                                    mods = pd.concat([mods, pd.DataFrame({'Signal': [full_name.split('\\')[0]], 'From': [mdf_unit], 'To': [tact_unit]})], ignore_index=True)

                    if resample is not None:
                        start_time = timestamps[0]
                        end_time = timestamps[-1]
                        resample_steps = np.arange(start_time, end_time + resample / 2, resample)
                        temp_df = temp_df.reindex(resample_steps, method='nearest')

                    temp_df = temp_df.rename(columns={full_name: generic_name})

                    if data_out.empty:
                        data_out = temp_df
                    else:
                        if resample is not None:
                            data_out = data_out.reindex(resample_steps, method='nearest').join(temp_df.reindex(resample_steps, method='nearest'), how='outer')
                        else:
                            data_out = data_out.join(temp_df, how='outer').interpolate(method='linear')

                    r = np.mean(np.diff(timestamps)) if len(timestamps) > 1 else np.inf
                    raster = pd.concat([raster, pd.DataFrame({'Variable': [generic_name], 'Raster': [r]})], ignore_index=True)

                except Exception as e:
                    print(f"Error reading {full_name}: {e}")

            if req is not None:
                read_signals = data_out.columns.tolist()
                not_read = [r for r in req if r not in read_signals]
                summary = pd.DataFrame({'Requested': req, 'Read': [r if r in read_signals else '' for r in req], 'NotRead': [r if r in not_read else '' for r in req]})
            else:
                summary = pd.DataFrame({'Read': signals_read})

            used = to_read_df[['GenericName', 'FullName']]

    if not data_out.empty and data_out.isna().any().any():
        data_out = data_out.interpolate(method='linear')

    return data_out, m, sigs['ChannelName'].tolist(), summary, used, raster, mods

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract signals from MDF file to .mat')
    parser.add_argument('dat_path', type=str, help='Path to MDF file')
    parser.add_argument('--signal_db', type=str, help='Path to signal database CSV or Excel file')
    parser.add_argument('--req', nargs='+', help='List of requested signals')
    parser.add_argument('--resample', type=float, help='Resample rate in seconds')
    parser.add_argument('--no_convert', action='store_true', help='Disable unit conversion')
    args = parser.parse_args()

    # Convert relative path to absolute path
    args.dat_path = os.path.abspath(args.dat_path)

    # Load signal database (CSV or Excel)
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

    data, m, sigs, summary, used, raster, mods = mdf2matSim(
        dat_path=args.dat_path,
        signal_database=signal_database,
        req=req,
        resample=args.resample,
        convert_to_tact_unit=convert_to_tact_unit
    )

    # Debug: Check if data is empty
    if data.empty:
        print("Warning: DataFrame is empty. No signals extracted.")
        print(f"Requested signals: {req}")
        print(f"MDF channels: {[ch.name for group in m.groups for ch in group.channels]}")
    else:
        print(f"DataFrame columns: {data.columns.tolist()}")
        print(f"DataFrame shape: {data.shape}")

    if not data.empty:
        mat_file = os.path.splitext(args.dat_path)[0] + '.mat'
        try:
            # Create a struct with time and signals
            signals_struct = {'time': data.index.values}
            for col in data.columns:
                # Replace invalid characters for MATLAB field names
                valid_name = col.replace('.', '_').replace('-', '_').replace(' ', '_')
                signals_struct[valid_name] = data[col].values
            # Save the struct to .mat file
            savemat(mat_file, {'signalMat': signals_struct})
            print(f"Saved {mat_file}")
        except Exception as e:
            print(f"Error saving .mat file: {e}")

    print("Processing complete.")