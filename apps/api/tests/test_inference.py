from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.config import Settings
import json

from app.inference import CORE_VARIABLES, FEATURE_NAMES, InferenceRuntime, TCNAdapter, XGBoostAdapter, window_features


class FakeModel:
    classes_ = [0, 1]

    def predict_proba(self, rows):
        assert len(rows) == 1
        assert len(rows[0]) == len(FEATURE_NAMES)
        return [[0.2, 0.8]]


def metadata() -> dict:
    return {
        "version": "test-xgb", "model_type": "xgboost", "training_data_version": "3W 2.0.0",
        "features": list(FEATURE_NAMES), "window_seconds": 180, "stride_seconds": 10,
        "class_mapping": {"0": "Normal", "1": "Flow Instability"}, "metrics": {},
        "created_at": "2026-09-10T00:00:00Z", "git_commit": "test", "artifact_file": "xgboost_model.json",
        "feature_schema_version": "3w-7v-window-stats-v1", "manifest_sha256": "a" * 64, "parameters": {},
    }


def test_window_features_match_the_serving_contract() -> None:
    first = {name: 1.0 for name in CORE_VARIABLES}
    second = {name: 3.0 for name in CORE_VARIABLES}
    assert len(window_features([{"measurements": first}, {"measurements": second}])) == 63


def test_runtime_warms_then_predicts_after_a_180_second_timestamp_window(tmp_path) -> None:
    runtime = InferenceRuntime(Settings(inference_model_dir=tmp_path))
    runtime.active.adapter = XGBoostAdapter(metadata(), FakeModel())
    runtime.active.metadata = metadata()
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    measurements = {name: 1.0 for name in CORE_VARIABLES}
    for offset in range(179):
        outcomes = runtime.add("well-1", timestamp + timedelta(seconds=offset), measurements)
    active, shadow = outcomes
    assert active.status == "warming_up"
    assert shadow.status == "model_unavailable"
    active, shadow = runtime.add("well-1", timestamp + timedelta(seconds=179), measurements)
    assert active.status == "predicted"
    assert active.predicted_class == "Flow Instability"
    assert active.anomaly_score == 0.8
    assert shadow.model_mode == "shadow"


def test_metadata_rejects_wrong_feature_contract() -> None:
    invalid = metadata()
    invalid["features"][0] = "unexpected_feature"
    try:
        InferenceRuntime._validate_metadata(invalid)
    except ValueError as exc:
        assert "feature schema" in str(exc)
    else:
        raise AssertionError("invalid model metadata must not load")


def test_tcn_adapter_loads_a_shadow_artifact_and_keeps_its_mode(tmp_path) -> None:
    import sys
    import pytest
    torch = pytest.importorskip("torch", reason="TCN artifact validation requires the optional serving dependency")

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ml"))
    from oilwell_ml.tcn import TCNConfig, build_tcn
    from oilwell_ml.tcn_data import StandardScaler

    config = TCNConfig()
    metadata = {
        "version": "test-tcn", "model_type": "tcn", "mode": "shadow", "training_data_version": "3W 2.0.0",
        "features": list(CORE_VARIABLES), "window_seconds": 180, "stride_seconds": 10,
        "class_mapping": {"0": "Normal", "1": "Severe Slugging", "2": "Flow Instability", "3": "Hydrate in Service Line"},
        "metrics": {}, "created_at": "2026-09-10T00:00:00Z", "git_commit": "test", "artifact_file": "tcn_model.pt",
        "feature_schema_version": "3w-7v-tcn-v1", "manifest_sha256": "a" * 64, "parameters": {},
        "config_file": "tcn_config.json", "scaler_file": "scaler.json",
    }
    (tmp_path / "tcn_config.json").write_text(json.dumps(config.to_dict()))
    (tmp_path / "scaler.json").write_text(json.dumps(StandardScaler((0.0,) * 7, (1.0,) * 7).to_dict()))
    torch.save(build_tcn(config).state_dict(), tmp_path / "tcn_model.pt")
    InferenceRuntime._validate_metadata(metadata)
    adapter = TCNAdapter.load(tmp_path, metadata)
    predicted, confidence, score = adapter.predict([{"measurements": {name: 1.0 for name in CORE_VARIABLES}} for _ in range(180)])
    assert predicted in metadata["class_mapping"].values()
    assert 0 <= confidence <= 1 and 0 <= score <= 1
