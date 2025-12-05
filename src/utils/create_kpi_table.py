import json
import pandas as pd
import numpy as np
import warnings
from pathlib import Path


# ------------------------------------------------------------------ #
# Public API
# ------------------------------------------------------------------ #
def create_kpi_table_from_df(schema_df: pd.DataFrame, n: int = 0, feature: str | None = None) -> pd.DataFrame:
    """
    Create KPI DataFrame from DataFrame schema, automatically including 'Common' KPIs.

    Parameters
    ----------
    schema_df : pd.DataFrame
        The schema DataFrame (e.g., read from Excel KPI spec).
        Must contain columns: [Feature, name, type, unit].
    n : int, optional
        Number of rows to initialize (default 0).
    feature : str or None, optional
        If given (e.g. 'AEB' or 'FCW'), will include both 'Common' and that feature’s KPIs.

    Returns
    -------
    pd.DataFrame
        Initialized KPI result table containing merged Common + feature KPIs,
        with preserved display name mappings for export.
    """
    if not isinstance(schema_df, pd.DataFrame):
        raise TypeError(f"Expected DataFrame, got {type(schema_df)}")

    # --- Normalize column names ---
    schema_df.columns = schema_df.columns.str.strip().str.lower()

    if "feature" not in schema_df.columns:
        raise ValueError("Schema DataFrame must contain column 'Feature' to filter by feature name.")

    # --- Normalize feature names ---
    schema_df["feature"] = schema_df["feature"].astype(str).str.strip().str.upper()

    # --- Extract subsets ---
    common_df = schema_df[schema_df["feature"] == "COMMON"]

    if feature is not None:
        feature = feature.strip().upper()
        feature_df = schema_df[schema_df["feature"] == feature]

        if common_df.empty and feature_df.empty:
            warnings.warn(f"⚠️ No KPIs found for '{feature}' or 'Common' — returning empty table.")
            return pd.DataFrame()

        # --- Combine Common + feature rows (Common first) ---
        combined_df = pd.concat([common_df, feature_df], ignore_index=True)
        print(f"🧩 Combined {len(common_df)} Common + {len(feature_df)} {feature} KPIs")

        # --- Build KPI table ---
        df = _create_kpi_table(combined_df, n)

        # --- Build and attach display name mapping ---
        display_names = {
            str(row["name"]): (
                f"{row['name']} [{row['unit']}]" if pd.notna(row.get("unit")) and str(row["unit"]).strip() else str(row["name"])
            )
            for _, row in combined_df.iterrows()
        }
        df.attrs["display_names"] = display_names
        return df

    # --- No feature specified → Common only ---
    if common_df.empty:
        warnings.warn("⚠️ No 'Common' KPIs found in schema.")
        return pd.DataFrame()

    print(f"🧩 Created KPI table with {len(common_df)} Common KPIs only")

    df = _create_kpi_table(common_df, n)
    display_names = {
        str(row["name"]): (
            f"{row['name']} [{row['unit']}]" if pd.notna(row.get("unit")) and str(row["unit"]).strip() else str(row["name"])
        )
        for _, row in common_df.iterrows()
    }
    df.attrs["display_names"] = display_names
    return df



def create_kpi_table_from_json(json_file, n: int = 0, feature: str | None = None) -> pd.DataFrame:
    """
    Create KPI DataFrame from JSON schema, optionally filtering by feature.
    """
    json_file = Path(json_file)
    if not json_file.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")

    with open(json_file, "r", encoding="utf-8") as f:
        schema = json.load(f)

    if "variables" not in schema or not schema["variables"]:
        raise ValueError(f'JSON schema missing or empty "variables" in {json_file}')

    schema_df = pd.DataFrame(schema["variables"])
    return create_kpi_table_from_df(schema_df, n, feature)

# ------------------------------------------------------------------ #
# Internal helper
# ------------------------------------------------------------------ #
def _create_kpi_table(schema: pd.DataFrame, n: int = 0) -> pd.DataFrame:
    """
    Build KPI table from schema DataFrame (expects columns: name, type, unit).
    """
    required_cols = {"name", "type", "unit"}
    if not required_cols.issubset(schema.columns):
        raise ValueError(
            f"Schema must contain at least {required_cols}, found {schema.columns.tolist()}"
        )

    schema = schema[list(required_cols)]  # keep only needed columns

    var_names = schema["name"].astype(str).tolist()
    var_types = schema["type"].str.lower().tolist()
    var_units = schema["unit"].fillna("").astype(str).tolist()

    # Create display names like "vehSpd [km/h]"
    display_names = [f"{n} [{u}]" if u else n for n, u in zip(var_names, var_units)]

    # Map schema types → Pandas dtypes
    valid_types = {"string": "string", "double": "float64", "logical": "boolean"}
    initial_values, dtypes = {}, {}

    for name, t in zip(var_names, var_types):
        if t not in valid_types:
            warnings.warn(f'Unsupported type "{t}" for variable "{name}". Defaulting to double.')
            t = "double"
        dtype = valid_types[t]
        dtypes[name] = dtype

        if n > 0:
            if t == "string":
                initial_values[name] = pd.Series([""] * n, dtype="string")
            elif t == "double":
                initial_values[name] = pd.Series([np.nan] * n, dtype="float64")
            elif t == "logical":
                initial_values[name] = pd.Series([False] * n, dtype="boolean")
        else:
            # create empty column with proper dtype but no rows
            initial_values[name] = pd.Series(dtype=valid_types[t])

    df = pd.DataFrame(initial_values, columns=var_names)
    for name, dtype in dtypes.items():
        df[name] = df[name].astype(dtype)

    df.attrs["display_names"] = dict(zip(var_names, display_names))
    return df


