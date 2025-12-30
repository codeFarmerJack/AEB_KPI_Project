import warnings
import numpy as np
from asammdf import MDF
import traceback


def get_signal(mdf, name: str, *, required: bool = False, default=None, as_array: bool = True):
    """
    Unified helper to fetch signals from MDF/SignalMDF with optional requirement.
    - required=True raises AttributeError if missing.
    - default is returned when available and signal is missing.
    - as_array=True converts to numpy array.
    """
    val = None

    if name == "time" and hasattr(mdf, "_time"):
        val = getattr(mdf, "_time", None)
    elif hasattr(mdf, "_injected") and name in getattr(mdf, "_injected", {}):
        val = mdf._injected.get(name)
    else:
        try:
            sig = mdf.get(name)
            val = sig.samples if hasattr(sig, "samples") else sig
        except Exception:
            if required:
                raise AttributeError(name)
            return default

    if as_array:
        try:
            arr = np.asarray(val)
        except Exception:
            if required:
                raise AttributeError(name)
            return default
        if arr.size == 0:
            if required:
                raise AttributeError(name)
            return default
        return arr
    return val


class SignalMDF(MDF):
    """
    Extended MDF class with:
      - Safe time vector resolution
      - Dot-access for signal names
      - Injection support for computed signals
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._injected = {}
        self._time = self._resolve_time()

    @property
    def time(self):
        return self._time

    def inject_signal(self, name, value):
        self._injected[name] = np.asarray(value)

    # ------------------------------------------------------------------ #
    def _resolve_time(self):
        """Resolve a safe time vector, even if multiple masters exist."""
        # 1) Try the master of group 0
        try:
            master = self.get_master(0)
            if master is not None and master.size:
                return master.flatten()
        except Exception:
            pass

        # 2) Try all occurrences of a channel named 'time'
        try:
            candidates = self.select("time")
            if candidates:
                for item in candidates:
                    try:
                        if isinstance(item, tuple) and len(item) == 2:
                            gp, ch = item
                            arr = self.get("time", group=gp, index=ch).samples
                        else:
                            arr = getattr(item, "samples", np.array([]))
                        arr = np.asarray(arr).ravel()
                        if arr.size > 0:
                            return arr
                    except Exception:
                        continue
        except Exception:
            pass

        # 3) Last resort: synthesize equidistant time vector
        try:
            n = len(self.groups[0].channels[0].samples)
        except Exception:
            n = 0
        warnings.warn("⚠️ Synthesized time vector (equidistant).")
        return np.arange(n, dtype=float)

def safe_load_mdf(file_path):
    try:
        print(f"   🟦 Loading MF4 → {file_path}")
        mdf = SignalMDF(file_path)
        print("   🟩 Loaded OK")
        return mdf
    except Exception as e:
        print("   🟥 Failed to load MF4")
        print("      Type:", type(e).__name__)
        print("      Message:", e)
        traceback.print_exc()
        return None
