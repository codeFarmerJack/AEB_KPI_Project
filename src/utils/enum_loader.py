import yaml
import numpy as np

class EnumMapper:
    """Load enum definitions and provide conversion utilities."""

    def __init__(self, yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        self.enums = {
            k: v
            for k, v in content.items()
            if k not in {"EnumToValueMap", "ValueToEnumMap"}
        }
        self.signal_to_enum = content.get("EnumToValueMap", {})
        self.value_to_enum = content.get("ValueToEnumMap", {})

    def get_enum_for_signal(self, signal_name):
        """Return enum group name mapped to a given MDF signal name."""
        return self.signal_to_enum.get(signal_name)

    def get_enum_for_value(self, signal_name):
        """Return enum group name to decode numeric signal values."""
        return self.value_to_enum.get(signal_name)

    def to_number(self, enum_name, value):
        """Convert symbolic value → number."""
        table = self.enums.get(enum_name, {})
        return table.get(value, None)

    def to_name(self, enum_name, number):
        """Convert numeric value → symbolic name."""
        table = self.enums.get(enum_name, {})
        inv = {v: k for k, v in table.items()}
        return inv.get(number, None)

    def decode_values(self, signal_name, values, fallback_enum=None):
        """
        Decode signal values into enum names when possible.
        - Preserves strings.
        - Returns None for None/NaN.
        - Falls back to numeric string if no enum match exists.
        """
        if values is None:
            return None

        enum_name = (
            self.get_enum_for_value(signal_name)
            or self.get_enum_for_signal(signal_name)
            or fallback_enum
        )

        names = []
        for v in np.asarray(values):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                names.append(None)
                continue
            if isinstance(v, str):
                names.append(v)
                continue
            try:
                code = int(v)
            except Exception:
                names.append(None)
                continue
            if enum_name:
                names.append(self.to_name(enum_name, code) or str(code))
            else:
                names.append(str(code))
        return names
