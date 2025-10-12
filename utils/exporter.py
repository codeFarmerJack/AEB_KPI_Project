import os
import warnings
import pandas as pd


def export_kpi_to_excel(kpi_df: pd.DataFrame, output_dir: str, sheet_name: str):
    """
    Export KPI DataFrame to an Excel workbook, creating or updating a sheet.

    Parameters
    ----------
    kpi_df : pd.DataFrame
        The KPI table to export. Must contain data and (optionally) attrs["display_names"].
    output_dir : str
        Directory path where the Excel file will be saved.
    sheet_name : str
        Name of the Excel sheet to create or update (e.g., "aeb", "fcw").
    """
    try:
        if not isinstance(kpi_df, pd.DataFrame):
            raise TypeError("kpi_df must be a pandas DataFrame.")
        if not sheet_name or not isinstance(sheet_name, str):
            raise ValueError("sheet_name must be a non-empty string.")

        # Ensure output folder exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        output_filename = os.path.join(output_dir, "AS-Long_KPI_Results.xlsx")

        df = kpi_df.copy()

        # --- Clean & sort ---
        if "label" in df.columns:
            df = df.dropna(subset=["label"])
        if "vehSpd" in df.columns:
            df = df.sort_values("vehSpd")

        # --- Apply display names (if defined) ---
        display_map = df.attrs.get("display_names", {})
        renamed = {col: display_map.get(col, col) for col in df.columns}
        renamed["label"] = "label"
        df = df.rename(columns=renamed)

        # --- Determine whether to create or update ---
        file_exists = os.path.exists(output_filename)

        if file_exists:
            # ✅ Update only the given sheet
            with pd.ExcelWriter(
                output_filename,
                engine="openpyxl",
                mode="a",
                if_sheet_exists="replace"
            ) as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"🔁 Updated sheet '{sheet_name}' in existing workbook → {output_filename}")
        else:
            # 🆕 Create a new workbook
            with pd.ExcelWriter(output_filename, engine="openpyxl", mode="w") as writer:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"🆕 Created new workbook and exported KPIs → {output_filename}")

    except Exception as e:
        warnings.warn(f"⚠️ Failed to export KPI results for '{sheet_name}': {e}")
