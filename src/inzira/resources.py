from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib


@dataclass(frozen=True)
class RuntimeBundle:
    root: Path
    model: Any
    preprocessor: Any
    configuration: dict[str, Any]
    schema: dict[str, Any]
    translations: dict[str, Any]
    fairness_policy: dict[str, Any]
    interventions: dict[str, Any]
    test_results: dict[str, Any]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repair_text(value: Any) -> Any:
    """Repair a replacement character present in the exported draft JSON."""
    if isinstance(value, str):
        return value.replace("\ufffd", "–")
    if isinstance(value, list):
        return [_repair_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _repair_text(item) for key, item in value.items()}
    return value


def find_latest_bundle(project_root: Path) -> Path:
    artifact_root = project_root / "artifacts"
    candidates = sorted(
        path
        for path in artifact_root.glob("inzira_lite_v1_*")
        if path.is_dir() and (path / "manifest.json").exists()
    )
    if not candidates:
        raise FileNotFoundError(
            "No verified Inzira Lite bundle was found under the artifacts directory."
        )
    return candidates[-1]


def load_runtime_bundle(project_root: Path) -> RuntimeBundle:
    bundle_root = find_latest_bundle(project_root)
    models = bundle_root / "models"
    content = bundle_root / "content"
    evaluation = bundle_root / "evaluation"

    configuration = _read_json(models / "inzira_lite_configuration.json")
    schema = _read_json(content / "lite_ui_feature_schema.json")
    translations = _repair_text(
        _read_json(content / "inzira_ui_translations_draft.json")
    )
    fairness_policy = _repair_text(
        _read_json(content / "inzira_lite_fairness_policy.json")
    )
    interventions = _repair_text(_read_json(content / "intervention_catalogue.json"))
    test_results = _repair_text(
        _read_json(evaluation / "inzira_lite_final_test_results.json")
    )

    return RuntimeBundle(
        root=bundle_root,
        model=joblib.load(models / "inzira_lite_model.joblib"),
        preprocessor=joblib.load(models / "inzira_lite_preprocessor.joblib"),
        configuration=configuration,
        schema=schema,
        translations=translations,
        fairness_policy=fairness_policy,
        interventions=interventions,
        test_results=test_results,
    )
