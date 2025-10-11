import warnings
import numpy as np
from asammdf import MDF


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

    # ------------------------------------------------------------------ #
    def __getattr__(self, name):
        """Allow dot-access to MDF signal channels."""
        if name == "time":
            return self._time

        if name in self._injected:
            return self._injected[name]

        # Allow MDF internal attributes
        if name in ("groups", "channels", "version", "attachments"):
            return super().__getattribute__(name)

        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass

        # Treat as signal name
        try:
            return self.get(name).samples.flatten()
        except Exception:
            warnings.warn(f"⚠️ Missing signal '{name}' in MDF file")
            return np.array([])

    # ------------------------------------------------------------------ #
    def __setattr__(self, name, value):
        """Allow dynamic injection of computed signals."""
        if isinstance(value, (np.ndarray, list)) and not name.startswith("_"):
            self._injected[name] = np.asarray(value)
        else:
            super().__setattr__(name, value)
