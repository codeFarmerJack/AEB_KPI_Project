# src/viz/core/data_adapters.py
import warnings
import pandas as pd


class DataAdapters:
    """
    Collection of small helpers for mapping graphSpec fields to DataFrame columns.
    """

    @staticmethod
    def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        if df is None:
            return pd.DataFrame()
        df = df.copy()
        df.columns = (
            df.columns.astype(str)
            .str.strip()
            .str.replace(" ", "_")
            .str.replace("\n", "_")
            .str.lower()
        )
        return df

    @staticmethod
    def resolve_xy_columns(kpi_data: pd.DataFrame, x_var: str, y_var: str):
        """
        Map graphSpec-ref names to actual KPI columns, using your 'clean' function
        from the old ScatterPlotter.
        """
        def clean(s: str) -> str:
            return (
                str(s)
                .lower()
                .replace(" ", "")
                .replace("[", "")
                .replace("]", "")
            )

        cols = list(kpi_data.columns)
        mapping = {clean(c): c for c in cols}

        x_col = mapping.get(clean(x_var))
        y_col = mapping.get(clean(y_var))

        # If not found, try "substring" fallback (same as before)
        if x_col is None:
            for c in cols:
                if clean(x_var) in clean(c):
                    x_col = c
                    break

        if y_col is None:
            for c in cols:
                if clean(y_var) in clean(c):
                    y_col = c
                    break

        if x_col is None or y_col is None:
            warnings.warn(f"⚠️ X ({x_var}) or Y ({y_var}) not found in KPI data")

        return x_col, y_col
