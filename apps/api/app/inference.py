"""Read-only active XGBoost and shadow TCN inference over one shared window."""

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
CORE_VARIABLES = ("P_PDG", "P_TPT", "T_TPT", "P_MON_CKP", "T_JUS_CKP", "P_JUS_CKGL", "QGL")
FEATURE_STATS = ("mean", "std", "min", "max", "median", "range", "slope", "last", "first_difference")
FEATURE_NAMES = tuple(f"{variable}__{stat}" for variable in CORE_VARIABLES for stat in FEATURE_STATS)


def window_features(samples: list[dict[str, Any]]) -> list[float]:
    if not samples:
        raise ValueError("a non-empty telemetry window is required")
    values: list[float] = []
    for variable in CORE_VARIABLES:
        series = [float(sample["measurements"][variable]) for sample in samples]
        slope = 0.0 if len(series) < 2 else (series[-1] - series[0]) / (len(series) - 1)
        first_difference = 0.0 if len(series) < 2 else series[-1] - series[-2]
        values.extend([sum(series) / len(series), stdev(series) if len(series) > 1 else 0.0, min(series), max(series), median(series), max(series) - min(series), slope, series[-1], first_difference])
    return values


@dataclass(frozen=True)
class InferenceOutcome:
    status: str
    model_type: str
    model_mode: str
    window_start: datetime | None = None
    window_end: datetime | None = None
    model_version: str | None = None
    predicted_class: str | None = None
    confidence: float | None = None
    anomaly_score: float | None = None
    feature_schema_version: str | None = None
    latency_ms: float | None = None


class ModelAdapter:
    def __init__(self, metadata: dict[str, Any], model: Any) -> None:
        self.metadata, self.model = metadata, model

    def predict(self, samples: list[dict[str, Any]]) -> tuple[str, float, float]:
        raise NotImplementedError


class XGBoostAdapter(ModelAdapter):
    @classmethod
    def load(cls, directory: Path, metadata: dict[str, Any]) -> "XGBoostAdapter":
        from xgboost import XGBClassifier
        model = XGBClassifier()
        model.load_model(directory / metadata["artifact_file"])
        return cls(metadata, model)

    def predict(self, samples: list[dict[str, Any]]) -> tuple[str, float, float]:
        probabilities = [float(value) for value in self.model.predict_proba([window_features(samples)])[0]]
        classes = getattr(self.model, "classes_", list(range(len(probabilities))))
        winner = max(range(len(probabilities)), key=probabilities.__getitem__)
        normal = next((index for index, value in enumerate(classes) if str(value) == "0"), None)
        if normal is None:
            raise ValueError("loaded XGBoost model does not expose Normal class 0")
        key = str(classes[winner])
        return self.metadata["class_mapping"].get(key, key), probabilities[winner], 1.0 - probabilities[normal]


class TCNAdapter(ModelAdapter):
    @classmethod
    def load(cls, directory: Path, metadata: dict[str, Any]) -> "TCNAdapter":
        import sys
        import torch
        try:
            from oilwell_ml.tcn import TCNConfig, build_tcn
            from oilwell_ml.tcn_data import StandardScaler
        except ModuleNotFoundError:
            ml_root = str(Path(__file__).resolve().parents[2] / "ml")
            if ml_root not in sys.path:
                sys.path.insert(0, ml_root)
            from oilwell_ml.tcn import TCNConfig, build_tcn
            from oilwell_ml.tcn_data import StandardScaler
        config = TCNConfig.from_dict(json.loads((directory / metadata["config_file"]).read_text()))
        scaler = StandardScaler.from_dict(json.loads((directory / metadata["scaler_file"]).read_text()))
        model = build_tcn(config)
        model.load_state_dict(torch.load(directory / metadata["artifact_file"], map_location="cpu", weights_only=True))
        model.eval()
        adapter = cls(metadata, model)
        adapter.scaler = scaler
        return adapter

    def predict(self, samples: list[dict[str, Any]]) -> tuple[str, float, float]:
        import torch
        rows = [sample["measurements"] for sample in samples]
        tensor = torch.tensor([self.scaler.transform(rows)], dtype=torch.float32)
        with torch.no_grad():
            probabilities = torch.softmax(self.model(tensor), dim=1)[0].tolist()
        winner = max(range(len(probabilities)), key=probabilities.__getitem__)
        return self.metadata["class_mapping"].get(str(winner), str(winner)), float(probabilities[winner]), float(1.0 - probabilities[0])


class ModelSlot:
    def __init__(self, mode: str, directory: Path) -> None:
        self.mode, self.directory = mode, directory
        self.adapter: ModelAdapter | None = None
        self.metadata: dict[str, Any] | None = None
        self.load_error: str | None = None

    @property
    def status(self) -> str:
        return "ready" if self.adapter else "unavailable"

    def load(self) -> None:
        self.adapter, self.metadata, self.load_error = None, None, None
        path = self.directory / "model_metadata.json"
        if not path.is_file():
            self.load_error = f"model metadata not found: {path}"
            logger.info("%s inference disabled: %s", self.mode, self.load_error)
            return
        try:
            metadata = json.loads(path.read_text())
            InferenceRuntime._validate_metadata(metadata)
            declared = metadata.get("mode", "active" if metadata["model_type"] == "xgboost" else "shadow")
            if declared != self.mode:
                raise ValueError(f"artifact declares mode {declared}, expected {self.mode}")
            if not (self.directory / metadata["artifact_file"]).is_file():
                raise ValueError(f"model artifact not found: {metadata['artifact_file']}")
            loader = XGBoostAdapter if metadata["model_type"] == "xgboost" else TCNAdapter
            self.adapter, self.metadata = loader.load(self.directory, metadata)
            logger.info("Loaded %s %s model %s", self.mode, metadata["model_type"], metadata["version"])
        except Exception as exc:
            self.load_error = str(exc)
            logger.warning("%s inference disabled: %s", self.mode, exc)

    def summary(self) -> dict[str, Any]:
        metadata = self.metadata or {}
        return {"mode": self.mode, "status": self.status, "error": self.load_error, "model_type": metadata.get("model_type"), "version": metadata.get("version"), "training_data_version": metadata.get("training_data_version"), "metrics": metadata.get("metrics"), "feature_schema_version": metadata.get("feature_schema_version")}


class InferenceRuntime:
    """Loads independent active/shadow artifacts and evaluates both against identical samples."""
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.windows: dict[str, deque[dict[str, Any]]] = {}
        self.active = ModelSlot("active", settings.inference_model_dir)
        self.shadow = ModelSlot("shadow", settings.shadow_inference_model_dir)

    @property
    def status(self) -> str:
        return self.active.status

    @property
    def load_error(self) -> str | None:
        return self.active.load_error

    def load(self) -> None:
        self.active.load(); self.shadow.load()

    def model_status(self) -> list[dict[str, Any]]:
        return [self.active.summary(), self.shadow.summary()]

    @staticmethod
    def _validate_metadata(metadata: dict[str, Any]) -> None:
        from jsonschema import Draft202012Validator
        schema = json.loads(Path(__file__).with_name("model_metadata.schema.json").read_text())
        errors = sorted(Draft202012Validator(schema).iter_errors(metadata), key=str)
        if errors:
            raise ValueError(f"metadata schema validation failed: {errors[0].message}")
        required = {"version", "model_type", "training_data_version", "features", "window_seconds", "class_mapping", "metrics", "created_at", "git_commit", "artifact_file", "feature_schema_version", "stride_seconds", "manifest_sha256", "parameters"}
        missing = required - metadata.keys()
        if missing:
            raise ValueError(f"metadata missing fields: {', '.join(sorted(missing))}")
        if metadata["window_seconds"] != 180 or metadata["stride_seconds"] != 10:
            raise ValueError("artifact window contract must be 180 seconds / 10 second stride")
        if not isinstance(metadata["class_mapping"], dict) or metadata["class_mapping"].get("0") != "Normal":
            raise ValueError("metadata class_mapping must map class 0 to Normal")
        if not isinstance(metadata["artifact_file"], str) or Path(metadata["artifact_file"]).name != metadata["artifact_file"]:
            raise ValueError("artifact_file must be a plain filename")
        if metadata["model_type"] == "xgboost":
            if metadata["features"] != list(FEATURE_NAMES) or metadata["feature_schema_version"] != "3w-7v-window-stats-v1":
                raise ValueError("artifact feature schema does not match the XGBoost API contract")
        elif metadata["model_type"] == "tcn":
            if metadata["features"] != list(CORE_VARIABLES) or metadata["feature_schema_version"] != "3w-7v-tcn-v1":
                raise ValueError("artifact feature schema does not match the TCN API contract")
            if not isinstance(metadata.get("config_file"), str) or not isinstance(metadata.get("scaler_file"), str):
                raise ValueError("TCN metadata requires config_file and scaler_file")
        else:
            raise ValueError("unsupported model type")

    def add(self, well_id: str, timestamp: datetime, measurements: dict[str, float]) -> list[InferenceOutcome]:
        samples = self.windows.setdefault(well_id, deque())
        samples.append({"timestamp": timestamp, "measurements": measurements})
        cutoff = timestamp.timestamp() - self.settings.telemetry_window_seconds
        while samples and samples[0]["timestamp"].timestamp() < cutoff:
            samples.popleft()
        return [self._outcome(slot, list(samples)) for slot in (self.active, self.shadow)]

    def _outcome(self, slot: ModelSlot, samples: list[dict[str, Any]]) -> InferenceOutcome:
        metadata = slot.metadata or {}
        model_type = str(metadata.get("model_type") or ("xgboost" if slot.mode == "active" else "tcn"))
        if slot.adapter is None:
            return InferenceOutcome(status="model_unavailable", model_type=model_type, model_mode=slot.mode)
        if not samples or set(samples[-1]["measurements"]) != set(CORE_VARIABLES):
            return InferenceOutcome(status="invalid_schema", model_type=model_type, model_mode=slot.mode, model_version=metadata.get("version"))
        start, end = samples[0]["timestamp"], samples[-1]["timestamp"]
        common = {"model_type": model_type, "model_mode": slot.mode, "window_start": start, "window_end": end, "model_version": metadata["version"], "feature_schema_version": metadata["feature_schema_version"]}
        if end.timestamp() - start.timestamp() < self.settings.telemetry_window_seconds - 1:
            return InferenceOutcome(status="warming_up", **common)
        started = time.perf_counter()
        predicted, confidence, anomaly_score = slot.adapter.predict(samples)
        return InferenceOutcome(status="predicted", predicted_class=predicted, confidence=confidence, anomaly_score=anomaly_score, latency_ms=(time.perf_counter() - started) * 1000, **common)
