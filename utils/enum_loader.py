import yaml

class EnumMapper:
    """Load enum definitions and provide conversion utilities."""

    def __init__(self, yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
        self.enums = {k: v for k, v in content.items() if k != "SignalToEnumMap"}
        self.signal_to_enum = content.get("SignalToEnumMap", {})

    def get_enum_for_signal(self, signal_name):
        """Return enum group name mapped to a given MDF signal name."""
        return self.signal_to_enum.get(signal_name)

    def to_number(self, enum_name, value):
        """Convert symbolic value → number."""
        table = self.enums.get(enum_name, {})
        return table.get(value, None)

    def to_name(self, enum_name, number):
        """Convert numeric value → symbolic name."""
        table = self.enums.get(enum_name, {})
        inv = {v: k for k, v in table.items()}
        return inv.get(number, None)