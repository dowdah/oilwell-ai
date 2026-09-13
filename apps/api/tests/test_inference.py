from datetime import UTC, datetime, timedelta
import pytest
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


def test_runtime_uses_exact_training_window_and_ten_second_stride(tmp_path) -> None:
    runtime = InferenceRuntime(Settings(inference_model_dir=tmp_path))
    class Recorder:
        def __init__(self): self.windows = []
        def predict(self, samples):
            self.windows.append(samples)
            return "Normal", 1.0, 0.0
    recorder = Recorder()
    runtime.active.adapter, runtime.active.metadata = recorder, metadata()
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    for offset in range(210):
        runtime.add("well", timestamp + timedelta(seconds=offset), {name: float(offset) for name in CORE_VARIABLES})
    assert len(recorder.windows) == 4
    assert all(len(window) == 180 for window in recorder.windows)
    assert [(w[-1]["timestamp"] - timestamp).total_seconds() for w in recorder.windows] == [179, 189, 199, 209]
    from oilwell_ml.features import window_features as offline_features
    for window in recorder.windows:
        assert window_features(window) == offline_features([row["measurements"] for row in window])


def test_runtime_restarts_warmup_after_gap_or_invalid_value(tmp_path) -> None:
    runtime = InferenceRuntime(Settings(inference_model_dir=tmp_path))
    runtime.active.adapter, runtime.active.metadata = XGBoostAdapter(metadata(), FakeModel()), metadata()
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    values = {name: 1.0 for name in CORE_VARIABLES}
    for offset in range(180): runtime.add("well", timestamp + timedelta(seconds=offset), values)
    assert runtime.add("well", timestamp + timedelta(seconds=185), values)[0].status == "warming_up"
    assert len(runtime.windows["well"]) == 1
    bad = {**values, "QGL": float("nan")}
    assert runtime.add("well", timestamp + timedelta(seconds=186), bad)[0].status == "invalid_schema"
    assert not runtime.windows["well"]


def test_shadow_prediction_failure_does_not_discard_active_result(tmp_path) -> None:
    runtime = InferenceRuntime(Settings(inference_model_dir=tmp_path))
    runtime.active.adapter, runtime.active.metadata = XGBoostAdapter(metadata(), FakeModel()), metadata()
    class Broken:
        def predict(self, samples): raise RuntimeError("unavailable shadow")
    runtime.shadow.adapter, runtime.shadow.metadata = Broken(), {**metadata(), "model_type": "tcn"}
    timestamp = datetime(2026, 9, 10, tzinfo=UTC)
    for offset in range(180):
        outcomes = runtime.add("well", timestamp + timedelta(seconds=offset), {name: 1.0 for name in CORE_VARIABLES})
    assert outcomes[0].status == "predicted"
    assert outcomes[1].status == "model_unavailable"


@pytest.mark.asyncio
async def test_native_inference_does_not_block_event_loop_and_remains_serial(monkeypatch):
    import asyncio
    import threading
    import time
    runtime = InferenceRuntime(Settings())
    entered = threading.Event()
    release = threading.Event()
    calls = []
    def slow(well, timestamp, measurements):
        calls.append(well)
        entered.set()
        assert release.wait(2)
        return []
    monkeypatch.setattr(runtime, 'add', slow)
    first = asyncio.create_task(runtime.add_async('first', datetime.now(UTC), {}))
    deadline = time.monotonic() + 1
    while not entered.is_set() and time.monotonic() < deadline:
        await asyncio.sleep(.01)
    assert entered.is_set()
    second = asyncio.create_task(runtime.add_async('second', datetime.now(UTC), {}))
    try:
        await asyncio.sleep(.03)
        assert calls == ['first']
    finally:
        release.set()
    await asyncio.gather(first, second)
    assert calls == ['first', 'second']


@pytest.mark.asyncio
async def test_cancelled_request_keeps_window_lock_until_native_worker_finishes(monkeypatch):
    import asyncio
    import threading
    runtime = InferenceRuntime(Settings())
    entered, release = threading.Event(), threading.Event()
    calls = []
    def slow(well, *_):
        calls.append(well); entered.set()
        assert release.wait(2)
        return []
    monkeypatch.setattr(runtime, 'add', slow)
    first = asyncio.create_task(runtime.add_async('cancelled', datetime.now(UTC), {}))
    for _ in range(100):
        if entered.is_set(): break
        await asyncio.sleep(.01)
    assert entered.is_set()
    first.cancel()
    second = asyncio.create_task(runtime.add_async('next', datetime.now(UTC), {}))
    try:
        await asyncio.sleep(.03)
        assert calls == ['cancelled']
    finally:
        release.set()
    results = await asyncio.gather(first, second, return_exceptions=True)
    assert isinstance(results[0], asyncio.CancelledError)
    assert results[1] == []
    assert calls == ['cancelled', 'next']
