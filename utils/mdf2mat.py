import argparse
import pandas as pd
from asammdf import MDF
from scipy.io import savemat


def removeMdfSuffixes(channelNames):
    """Removes suffixes from MDF channel names."""
    result = []
    for ch in channelNames:
        parts = ch.split("\\")
        result.append(parts[0])
    return result


def mdf2mat(datPath, signalDatabase=None, resample=None):
    """
    Python equivalent of simplified MATLAB mdf2mat_new (V1).
    """
    if signalDatabase is None or not isinstance(signalDatabase, pd.DataFrame):
        raise ValueError("signalDatabase (pandas.DataFrame) is required")

    mdfObj = MDF(datPath)
    sigs = pd.DataFrame(mdfObj.channels_db)
    sigsCopy = [ch.replace(".", "_") for ch in sigs["name"]]
    sigsCopy = removeMdfSuffixes(sigsCopy)

    # --- Determine which signals to read ---
    if "GenericName" in signalDatabase.columns:
        sigList = signalDatabase["GenericName"].unique()
    elif "TactName" in signalDatabase.columns:
        sigList = signalDatabase["TactName"].unique()
    else:
        sigList = []

    toRead = []
    for sig in sigList:
        if "GenericName" in signalDatabase.columns:
            locs = signalDatabase["GenericName"].str.lower() == str(sig).lower()
        elif "TactName" in signalDatabase.columns:
            locs = signalDatabase["TactName"].str.lower() == str(sig).lower()
        else:
            locs = pd.Series([False] * len(signalDatabase))

        if "Synonym" in signalDatabase.columns:
            syns = signalDatabase.loc[locs, "Synonym"].tolist()
        elif "A2LName" in signalDatabase.columns:
            syns = signalDatabase.loc[locs, "A2LName"].tolist()
        else:
            syns = []

        flatSyns = []
        for s in syns:
            if isinstance(s, (list, tuple)):
                flatSyns.extend(s)
            else:
                flatSyns.append(s)

        for syn in flatSyns:
            if syn and isinstance(syn, str):
                sigToFind = syn.replace(".", "_")
                if sigToFind.lower() in [s.lower() for s in sigsCopy]:
                    idx = [j for j, sc in enumerate(sigsCopy) if sc.lower() == sigToFind.lower()][0]
                    toRead.append({
                        "fullName": sigs["name"].iloc[idx],
                        "channel": sigs["channel_group_nr"].iloc[idx],
                        "genericName": sig
                    })

    toReadDf = pd.DataFrame(toRead)
    data = None
    rasterList = []

    if not toReadDf.empty:
        for gName in toReadDf["genericName"].unique():
            row = toReadDf[toReadDf["genericName"] == gName].iloc[0]
            channelName = row["fullName"]

            signal = mdfObj.get(channelName)
            ts = signal.timestamps
            values = signal.samples

            if len(ts) > 1:
                rasterVal = pd.Series(ts).diff().mean()
            else:
                rasterVal = None
            rasterList.append([gName, rasterVal])

            series = pd.Series(values, index=pd.to_datetime(ts, unit="s"))
            if resample is not None:
                series = series.resample(f"{resample}S").nearest()

            df = series.to_frame(name=gName)
            if data is None:
                data = df
            else:
                data = data.join(df, how="outer")

        raster = pd.DataFrame(rasterList, columns=["variable", "raster"])
        used = toReadDf[["genericName", "fullName"]]
    else:
        data = pd.DataFrame()
        raster = pd.DataFrame(columns=["variable", "raster"])
        used = pd.DataFrame(columns=["genericName", "fullName"])

    if not data.empty:
        data = data.interpolate(method="nearest").ffill().bfill()

    return data, mdfObj, used, sigs, raster


def runMdf2mat(mf4Path, matPath, signalDbPath, resample=None):
    """
    Wrapper for MATLAB Docker call.
    Reads mf4, applies signalDatabase, saves result as .mat
    """
    # Load signalDatabase
    if signalDbPath.endswith(".csv"):
        signalDb = pd.read_csv(signalDbPath)
    else:
        signalDb = pd.read_excel(signalDbPath)

    data, mdfObj, used, sigs, raster = mdf2mat(
        mf4Path,
        signalDatabase=signalDb,
        resample=resample,
    )

    # Export to MAT file (camelCase keys)
    savemat(matPath, {
        "data": data.to_dict(orient="list") if data is not None else {},
        "used": used.to_dict(orient="list"),
        "sigs": sigs.to_dict(orient="list"),
        "raster": raster.to_dict(orient="list"),
    })

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert MF4 to MAT with signal database mapping")

    parser.add_argument("mf4Path", type=str, help="Path to input .mf4 file")
    parser.add_argument("matPath", type=str, help="Path to output .mat file")
    parser.add_argument("signalDbPath", type=str, help="Path to signal database (CSV or Excel)")
    parser.add_argument("--resample", type=float, default=None, help="Resample rate in seconds")

    args = parser.parse_args()

    runMdf2mat(
        args.mf4Path,
        args.matPath,
        args.signalDbPath,
        resample=args.resample
    )
