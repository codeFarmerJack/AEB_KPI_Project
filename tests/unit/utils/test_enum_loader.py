import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.enum_loader import EnumMapper


def _write_enum_yaml(path):
    content = "\n".join(
        [
            "EnumToValueMap:",
            "  aebFullState: AutoEmergencyBrakingPlannerState",
            "ValueToEnumMap:",
            "  aebTargetType: ObstacleClass",
            "",
            "AutoEmergencyBrakingPlannerState:",
            "  STATE_INVALID: 0",
            "  STATE_READY: 1",
            "",
            "ObstacleClass:",
            "  OBSTACLE_CLASS_INVALID: 0",
            "  OBSTACLE_CLASS_CAR: 1",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def test_decode_values_uses_signal_mapping(tmp_path):
    enum_path = tmp_path / "enums.yaml"
    _write_enum_yaml(enum_path)
    mapper = EnumMapper(str(enum_path))

    values = np.array([0, 1, 2, np.nan], dtype=float)
    decoded = mapper.decode_values("aebFullState", values)

    assert decoded == ["STATE_INVALID", "STATE_READY", "2", None]


def test_decode_values_handles_value_map_and_fallback(tmp_path):
    enum_path = tmp_path / "enums.yaml"
    _write_enum_yaml(enum_path)
    mapper = EnumMapper(str(enum_path))

    values = np.array([1, 0], dtype=float)
    decoded = mapper.decode_values("aebTargetType", values)

    assert decoded == ["OBSTACLE_CLASS_CAR", "OBSTACLE_CLASS_INVALID"]

    decoded_fallback = mapper.decode_values("unknownSignal", values, fallback_enum="ObstacleClass")
    assert decoded_fallback == ["OBSTACLE_CLASS_CAR", "OBSTACLE_CLASS_INVALID"]


def test_decode_values_preserves_strings(tmp_path):
    enum_path = tmp_path / "enums.yaml"
    _write_enum_yaml(enum_path)
    mapper = EnumMapper(str(enum_path))

    values = np.array(["RAW", "1"], dtype=object)
    decoded = mapper.decode_values("aebFullState", values)

    assert decoded == ["RAW", "1"]
