"""Read-only XGBoost serving and deterministic window feature extraction."""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median, stdev
from typing import Any

from .config import Settings

logger = logging.getLogger(__name__)

CORE_VARIABLES = (
    "P_PDG", "P_TPT", "T_TPT", "P_MON_CKP", "T_JUS_CKP", "P_JUS_CKGL", "QGL",
)
FEATURE_STATS = ("mean", "std", "min", "max", "median", "range", "slope", "last", "first_difference")
FEATURE_NAMES = tuple(f"{variable}__{stat}" for variable in CORE_VARIABLES for stat in FEATURE_STATS)


def window_features(samples: list[dict[str, Any]]) -> list[float]:
    """Return the stable feature vector used by both training and serving."""
    if not samples:
        raise ValueError("a non-empty telemetry window is required")
    values: list[float] = []
    for variable in CORE_VARIABLES:
        series = [float(sample["measurements"][variable]) for sample in samples]
        slope = 0.0 if len(series) < 2 else (series[-1] - series[0]) / (len(series) - 1)
        first_difference = 0.0 if len(series) < 2 else series[-1] - series[-2]
        values.extend([
            sum(series) / len(series), stdev(series) if len(series) > 1 else 0.0,
            min(series), max(series), median(series), max(series) - min(series),
            slope, series[-1], first_difference,
        ])
    return values


@dataclass(frozen=True)
class InferenceOutcome:
    status: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    model_version: str | None = None
    predicted_class: str | None = None
    confidence: float | None = None
    anomaly_score: float | None = None
    feature_schema_version: str | None = None
    latency_ms: float | None = None


class InferenceRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.windows: dict[str, deque[dict[str, Any]]] = {}
        self.model: Any | None = None
        self.metadata: dict[str, Any] | None = None
        self.load_error: str | None = None

    @property
    def status(self) -> str:
        return "ready" if self.model is not None else "unavailable"

    def load(self) -> None:
        self.model = None
        self.metadata = None
        self.load_error = None
        metadata_path = self.settings.inference_model_dir / "model_metadata.json"
        if not metadata_path.exists():
            self.load_error = f"model metadata not found: {metadata_path}"
            logger.info("Inference disabled: %s", self.load_error)
            return
        try:
            metadata = json.loads(metadata_path.read_text())
            self._validate_metadata(metadata)
            artifact = self.settings.inference_model_dir / metadata["artifact_file"]
            if not artifact.is_file():
                raise ValueError(f"model artifact not found: {artifact.name}")
            from xgboost import XGBClassifier

            model = XGBClassifier()
            model.load_model(artifact)
            self.model, self.metadata = model, metadata
            logger.info("Loaded XGBoost model version %s", metadata["version"])
        except Exception as exc:
            self.load_error = str(exc)
            logger.warning("Inference disabled: %s", exc)

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any]) -> None:
        from jsonschema import Draft202012Validator

        schema_path = Path(__file__).with_name("model_metadata.schema.json")
        errors = sorted(Draft202012Validator(json.loads(schema_path.read_text())).iter_errors(metadata), key=str)
        if errors:
            raise ValueError(f"metadata schema validation failed: {errors[0].message}")
        required = {
            "version", "model_type", "training_data_version", "features", "window_seconds",
            "class_mapping", "metrics", "created_at", "git_commit", "artifact_file",
            "feature_schema_version", "stride_seconds", "manifest_sha256", "parameters",
        }
        missing = required - metadata.keys()
        if missing:
            raise ValueError(f"metadata missing fields: {', '.join(sorted(missing))}")
        if metadata["model_type"] != "xgboost":
            raise ValueError("ECS only serves xgboost artifacts")
        if metadata["window_seconds"] != 180 or metadata["stride_seconds"] != 10:
            raise ValueError("artifact window contract must be 180 seconds / 10 second stride")
        if metadata["features"] != list(FEATURE_NAMES):
            raise ValueError("artifact feature schema does not match the API contract")
        if not isinstance(metadata["class_mapping"], dict) or "0" not in metadata["class_mapping"]:
            raise ValueError("metadata class_mapping must include class 0 (Normal)")
        artifact_file = metadata["artifact_file"]
        if not isinstance(artifact_file, str) or Path(artifact_file).name != artifact_file:
            raise ValueError("artifact_file must be a plain filename")

    def add(self, well_id: str, timestamp: datetime, measurements: dict[str, float]) -> InferenceOutcome:
        if self.model is None or self.metadata is None:
            return InferenceOutcome(status="model_unavailable")
        if set(measurements) != set(CORE_VARIABLES):
            return InferenceOutcome(status="invalid_schema")
        samples = self.windows.setdefault(well_id, deque())
        sample = {"timestamp": timestamp, "measurements": measurements}
        samples.append(sample)
        cutoff = timestamp.timestamp() - self.settings.telemetry_window_seconds
        while samples and samples[0]["timestamp"].timestamp() < cutoff:
            samples.popleft()
        first = samples[0]["timestamp"]
        if timestamp.timestamp() - first.timestamp() < self.settings.telemetry_window_seconds - 1:
            return InferenceOutcome(
                status="warming_up", window_start=first, window_end=timestamp,
                model_version=self.metadata["version"], feature_schema_version=self.metadata["feature_schema_version"],
            )
        started = time.perf_counter()
        probabilities = [float(value) for value in self.model.predict_proba([window_features(list(samples))])[0]]
        class_index = max(range(len(probabilities)), key=probabilities.__getitem__)
        classes = getattr(self.model, "classes_", list(range(len(probabilities))))
        class_key = str(classes[class_index])
        predicted = self.metadata["class_mapping"].get(class_key, class_key)
        normal_index = next((index for index, value in enumerate(classes) if str(value) == "0"), None)
        if normal_index is None:
            raise ValueError("loaded model does not expose Normal class 0")
        return InferenceOutcome(
            status="predicted", window_start=first, window_end=timestamp,
            model_version=self.metadata["version"], predicted_class=predicted,
            confidence=probabilities[class_index], anomaly_score=1.0 - probabilities[normal_index],
            feature_schema_version=self.metadata["feature_schema_version"],
            latency_ms=(time.perf_counter() - started) * 1000,
        )
