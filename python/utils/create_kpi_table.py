import json
import pandas as pd
import numpy as np
import warnings
from pathlib import Path

def create_kpi_table_from_json(json_file, n=0):
    """
    Create KPI DataFrame based on JSON schema.

    Parameters
    ----------
    json_file : str or Path
        Path to JSON file containing variable definitions.
    n : int, optional
        Number of rows. Default = 0 (empty table).

    Returns
    -------
    df : pandas.DataFrame
        DataFrame with specified variables and units stored in .attrs["display_names"].
    """
    json_file = Path(json_file)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    # Load schema
    with open(json_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    if "variables" not in schema or not schema["variables"]:
        raise ValueError(f'JSON schema missing or empty "variables" field in {json_file}')

    vars_list = schema["variables"]
    var_names = [v["name"] for v in vars_list]
    var_types = [v.get("type", "double").lower() for v in vars_list]
    var_units = [v.get("unit", "") for v in vars_list]

    # Create display names with units
    display_names = [
        f"{name} [{unit}]" if unit else name
        for name, unit in zip(var_names, var_units)
    ]

    # Map types to Pandas dtypes and default values
    valid_types = {"string": "string", "double": "float64", "logical": "boolean"}
    initial_values = {}
    dtypes = {}

    for name, t in zip(var_names, var_types):
        if t not in valid_types:
            warnings.warn(
                f'Unsupported type "{t}" for variable "{name}" in {json_file}. Defaulting to double.'
            )
            t = "double"

        dtype = valid_types[t]
        dtypes[name] = dtype

        if t == "string":
            initial_values[name] = pd.Series([""] * n, dtype="string")
        elif t == "double":
            initial_values[name] = pd.Series([np.nan] * n, dtype="float64")
        elif t == "logical":
            initial_values[name] = pd.Series([False] * n, dtype="boolean")

    # Build DataFrame
    df = pd.DataFrame(initial_values, columns=var_names)

    # Ensure dtypes
    for name, dtype in dtypes.items():
        df[name] = df[name].astype(dtype)

    # Store display names in DataFrame attrs (metadata)
    df.attrs["display_names"] = dict(zip(var_names, display_names))

    # Sanity check
    missing = set(var_names) - set(df.columns)
    if missing:
        raise ValueError(f"Failed to create variables: {', '.join(missing)} in {json_file}")

    return df
