from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas import ReplayCommand, TelemetryIn


def valid_packet() -> dict:
    return {
        "device_id": "edge-pi-01",
        "well_id": "WELL-00014",
        "timestamp": "2026-09-10T12:00:00Z",
        "sequence": 1,
        "measurements": {
            "P_PDG": 1.0, "P_TPT": 2.0, "T_TPT": 3.0, "P_MON_CKP": 4.0,
            "T_JUS_CKP": 5.0, "P_JUS_CKGL": 6.0, "QGL": 7.0,
        },
    }


def test_telemetry_accepts_exact_seven_variable_contract() -> None:
    packet = TelemetryIn.model_validate(valid_packet())
    assert packet.measurements.qgl == 7.0
    assert packet.model_dump(by_alias=True)["measurements"]["P_PDG"] == 1.0


def test_telemetry_rejects_unknown_top_level_fields() -> None:
    data = valid_packet()
    data["raw_password"] = "must-not-pass"
    with pytest.raises(ValidationError):
        TelemetryIn.model_validate(data)


def test_replay_speed_is_constrained() -> None:
    assert ReplayCommand(command="SET_SPEED", speed=20).speed == 20
    with pytest.raises(ValidationError):
        ReplayCommand(command="SET_SPEED", speed=7)
