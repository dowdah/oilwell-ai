"""Portable regression coverage for replay identity and offline SHAP artifacts."""

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from xgboost import DMatrix, XGBClassifier

from oilwell_ml.features import CORE_VARIABLES, FEATURE_NAMES, window_features


def load_script(name):
    path = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def prepare():
    return load_script("prepare_demo_windows")


@pytest.fixture(scope="module")
def generate():
    return load_script("generate_explanations")


def demo_instance(tmp_path, offsets, *, labels=None, name="WELL-00001_20260101000000.parquet", well_id=None):
    offsets = list(offsets)
    signals = [{name: float(index + channel) for channel, name in enumerate(CORE_VARIABLES)}
               for index in range(len(offsets))]
    rows = {name: [row[name] for row in signals] for name in CORE_VARIABLES}
    rows["timestamp"] = [datetime(2026, 1, 1) + timedelta(seconds=value) for value in offsets]
    rows["class"] = labels if labels is not None else [3] * len(offsets)
    path = tmp_path / name
    pq.write_table(pa.table(rows), path)
    item = {
        "source_path": path.name, "instance_id": path.name, "label": "3",
        "label_name": "Severe Slugging", "observation_labels": ["3"], "well_id": well_id,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    return item, signals


def test_demo_window_recovers_missing_well_id_from_edge_filename(prepare, tmp_path):
    item, signals = demo_instance(tmp_path, range(180))
    window = prepare.first_window(item, tmp_path, 180)
    assert window["well_id"] == "WELL-00001"
    assert window["window_start"] == "2026-01-01T00:00:00+00:00"
    assert window["window_end"] == "2026-01-01T00:02:59+00:00"
    assert window["source_sha256"] == item["sha256"]
    assert window["features"] == dict(zip(FEATURE_NAMES, window_features(signals), strict=True))


@pytest.mark.parametrize("name,well_id", [
    ("WELL-00001_20260101000000.parquet", "WELL-00014"),
    ("unidentified.parquet", None),
])
def test_demo_window_rejects_conflicting_or_unknown_well_identity(prepare, tmp_path, name, well_id):
    item, _ = demo_instance(tmp_path, range(180), name=name, well_id=well_id)
    with pytest.raises(ValueError):
        prepare.first_window(item, tmp_path, 180)


def test_demo_window_keeps_replay_alignment_across_label_changes(prepare, tmp_path):
    # The API consumes all rows. Filtering five leading normal labels would
    # create a 5..184 window that is absent from its 0..179, 10..189 schedule.
    item, signals = demo_instance(tmp_path, range(200), labels=[0] * 5 + [3] * 195)
    window = prepare.first_window(item, tmp_path, 180)
    assert window["window_start"] == "2026-01-01T00:00:00+00:00"
    assert window["window_end"] == "2026-01-01T00:02:59+00:00"
    assert window["features"] == dict(zip(FEATURE_NAMES, window_features(signals[:180]), strict=True))


@pytest.mark.parametrize("restart", [200, 50], ids=["gap", "backwards"])
def test_demo_window_rewarms_after_time_discontinuity(prepare, tmp_path, restart):
    item, signals = demo_instance(tmp_path, list(range(100)) + list(range(restart, restart + 180)))
    window = prepare.first_window(item, tmp_path, 180)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=restart)
    assert window["window_start"] == start.isoformat()
    assert window["window_end"] == (start + timedelta(seconds=179)).isoformat()
    assert window["features"] == dict(zip(FEATURE_NAMES, window_features(signals[100:]), strict=True))


@pytest.fixture(scope="module")
def small_model(tmp_path_factory):
    """Fit a tiny synthetic model; no ignored delivery assets are required."""
    directory = tmp_path_factory.mktemp("explanation-model")
    matrix = np.array([[float(index + feature / 10) for feature in range(len(FEATURE_NAMES))]
                       for index in range(18)])
    labels = np.repeat(np.arange(3), 6)
    model = XGBClassifier(n_estimators=3, max_depth=2, n_jobs=1, random_state=17,
                          objective="multi:softprob", eval_metric="mlogloss")
    model.fit(matrix, labels)
    model.save_model(directory / "model.json")
    metadata = {
        "model_type": "xgboost", "version": "synthetic-xgb-v1", "artifact_file": "model.json",
        "features": list(FEATURE_NAMES), "feature_schema_version": "3w-7v-window-stats-v1",
        "window_seconds": 180, "stride_seconds": 10,
        "class_mapping": {"0": "Normal", "1": "Severe Slugging", "2": "Flow Instability"},
    }
    (directory / "model_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return directory, model


def feature_window():
    return {
        "well_id": "WELL-00001", "window_start": "2026-01-01T00:00:00+00:00",
        "window_end": "2026-01-01T00:02:59+00:00",
        "features": {name: float(index / 10) for index, name in enumerate(FEATURE_NAMES)},
        "trend_summary": "Synthetic fixture; contributions are not causal evidence.",
    }


def run_generator(generate, monkeypatch, tmp_path, directory, windows):
    input_path, output_path = tmp_path / "private-windows.json", tmp_path / "explanation_manifest.json"
    input_path.write_text(json.dumps(windows), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        "generate_explanations.py", "--model-dir", str(directory),
        "--windows-json", str(input_path), "--output", str(output_path), "--top-k", "5",
    ])
    generate.main()
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_generator_preserves_identity_and_actual_predicted_class_contributions(generate, monkeypatch, tmp_path, small_model):
    directory, model = small_model
    window = feature_window()
    output = run_generator(generate, monkeypatch, tmp_path, directory, [window])
    summary = output["window_summaries"][0]
    for name in ("well_id", "window_start", "window_end", "trend_summary"):
        assert summary[name] == window[name]
    assert output["model_version"] == "synthetic-xgb-v1"
    assert output["feature_schema_version"] == "3w-7v-window-stats-v1"
    matrix = np.array([[window["features"][name] for name in FEATURE_NAMES]])
    winner = int(np.argmax(model.predict_proba(matrix)[0]))
    contributions = model.get_booster().predict(
        DMatrix(matrix, feature_names=list(FEATURE_NAMES)), pred_contribs=True,
    )[0, winner, :-1]
    ranked = np.argsort(np.abs(contributions))[::-1][:5]
    assert summary["top_features"] == [FEATURE_NAMES[index] for index in ranked]
    assert summary["contributions"] == {
        FEATURE_NAMES[index]: round(float(contributions[index]), 6) for index in ranked
    }
    assert "features" not in summary and "measurements" not in summary
    assert "measurements" not in json.dumps(output)


def test_generator_normalizes_equivalent_timezone_to_utc(generate, monkeypatch, tmp_path, small_model):
    directory, _ = small_model
    window = feature_window()
    window["window_start"] = "2026-01-01T08:00:00+08:00"
    window["window_end"] = "2026-01-01T08:02:59+08:00"
    output = run_generator(generate, monkeypatch, tmp_path, directory, [window])
    summary = output["window_summaries"][0]
    assert summary["window_start"] == "2026-01-01T00:00:00+00:00"
    assert summary["window_end"] == "2026-01-01T00:02:59+00:00"


@pytest.mark.parametrize("invalid", ["null_id", "blank_id", "missing_id", "naive_start", "naive_end", "old_span", "nan", "infinity"])
def test_generator_rejects_unmatchable_or_nonfinite_windows(generate, monkeypatch, tmp_path, small_model, invalid):
    directory, _ = small_model
    window = feature_window()
    if invalid == "null_id":
        window["well_id"] = None
    elif invalid == "blank_id":
        window["well_id"] = " \t"
    elif invalid == "missing_id":
        del window["well_id"]
    elif invalid == "naive_start":
        window["window_start"] = "2026-01-01T00:00:00"
    elif invalid == "naive_end":
        window["window_end"] = "2026-01-01T00:02:59"
    elif invalid == "old_span":
        window["window_end"] = "2026-01-01T00:03:00+00:00"
    else:
        window["features"][FEATURE_NAMES[0]] = float("nan" if invalid == "nan" else "inf")
    with pytest.raises(ValueError):
        run_generator(generate, monkeypatch, tmp_path, directory, [window])
    assert not (tmp_path / "explanation_manifest.json").exists()
