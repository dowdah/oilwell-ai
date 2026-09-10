from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.inference import CORE_VARIABLES, FEATURE_NAMES, InferenceRuntime, window_features


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
    runtime.model, runtime.metadata = FakeModel(), metadata()
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    measurements = {name: 1.0 for name in CORE_VARIABLES}
    for offset in range(179):
        outcome = runtime.add("well-1", timestamp + timedelta(seconds=offset), measurements)
    assert outcome.status == "warming_up"
    outcome = runtime.add("well-1", timestamp + timedelta(seconds=179), measurements)
    assert outcome.status == "predicted"
    assert outcome.predicted_class == "Flow Instability"
    assert outcome.anomaly_score == 0.8


def test_metadata_rejects_wrong_feature_contract() -> None:
    invalid = metadata()
    invalid["features"][0] = "unexpected_feature"
    try:
        InferenceRuntime._validate_metadata(invalid)
    except ValueError as exc:
        assert "feature schema" in str(exc)
    else:
        raise AssertionError("invalid model metadata must not load")
