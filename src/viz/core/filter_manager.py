# src/viz/core/filter_manager.py
import numpy as np
import pandas as pd
import warnings


class FilterManager:
    """
    Handles 'plotenabled' logic and conditional masking over kpi_data.
    """

    @staticmethod
    def is_row_enabled(val) -> bool:
        s = str(val).strip().lower()
        if s == "true":
            return True
        if s in ["false", "na", "none", ""]:
            return False
        # fallback: treat as enabled
        return True

    @staticmethod
    def build_mask(kpi_data: pd.DataFrame, plot_enabled):
        """
        Interpret the plotenabled cell and build a boolean mask over kpi_data.
        - "TRUE" → all rows
        - "FALSE"/"none" → no rows
        - "flagName" → kpi_data[flagName] interpreted as boolean-ish
        - "!flagName" → negation
        """
        val = str(plot_enabled).strip()
        low = val.lower()

        if low == "true":
            return pd.Series(True, index=kpi_data.index)

        if low in ["false", "na", "none", ""]:
            return pd.Series(False, index=kpi_data.index)

        negate = False
        if val.startswith("!"):
            negate = True
            val = val[1:].strip()

        if val not in kpi_data.columns:
            warnings.warn(f"⚠️ Conditional flag '{plot_enabled}' not found; plotting all rows.")
            return pd.Series(True, index=kpi_data.index)

        col = kpi_data[val]

        if col.dtype == bool:
            mask = col
        elif np.issubdtype(col.dtype, np.number):
            mask = col.fillna(0) != 0
        else:
            mask = col.astype(str).str.lower().isin(["true", "1", "yes", "y"])

        if negate:
            mask = ~mask

        return mask.reindex(kpi_data.index, fill_value=False)
