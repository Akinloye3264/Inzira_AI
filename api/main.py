from __future__ import annotations

import hmac
import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from src.inzira.features import build_assessment_features, validate_household_counts
from src.inzira.inference import run_screening
from src.inzira.resources import RuntimeBundle, load_runtime_bundle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
API_VERSION = "1.0.0"


class ScreeningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    province: Literal[1, 2, 3, 4, 5] | None = None
    ur: Literal[1, 2] | None = None
    household_members: Annotated[int | None, Field(ge=1, le=30)] = None
    children_count: Annotated[int | None, Field(ge=0, le=20)] = None
    elderly_count: Annotated[int | None, Field(ge=0, le=20)] = None
    sleeping_rooms: Annotated[int | None, Field(ge=1, le=15)] = None
    floor_material: Literal[1, 2, 3, 4, 5, 6, 8] | None = None
    electricity_access: Literal[0, 1] | None = None
    livestock_range: Literal["none", "1_2", "3_5", "6_plus"] | None = None
    mobile_phone: Literal[0, 1] | None = None
    recent_internet_use: Literal[0, 1] | None = None
    insured_members: Annotated[int | None, Field(ge=0, le=30)] = None
    agricultural_activity: Literal[0, 1] | None = None
    wage_employment: Literal[0, 1] | None = None
    nonfarm_business: Literal[0, 1] | None = None


class ScreeningResponse(BaseModel):
    score: float
    threshold: float
    elevated_risk: bool
    completeness: float
    limited_information: bool
    small_household: bool
    model_name: str
    model_version: str
    decision_role: str = "initial_screening_only"


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    target: str
    threshold: float
    minimum_answered_fraction: float
    test_status: str
    decision_role: str = "initial_screening_only"


@lru_cache(maxsize=1)
def get_bundle() -> RuntimeBundle:
    return load_runtime_bundle(PROJECT_ROOT)


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.environ.get("INZIRA_API_KEY", "").strip()
    if expected and (
        not x_api_key or not hmac.compare_digest(x_api_key, expected)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )


app = FastAPI(
    title="Inzira AI Screening API",
    description=(
        "Privacy-conscious initial household vulnerability screening. "
        "The result is not an eligibility or benefits decision."
    ),
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "inzira-ai-api", "version": API_VERSION}


@app.get(
    "/v1/model-info",
    response_model=ModelInfoResponse,
    dependencies=[Depends(require_api_key)],
    tags=["model"],
)
def model_info() -> ModelInfoResponse:
    configuration = get_bundle().configuration
    return ModelInfoResponse(
        model_name=str(configuration["model_name"]),
        model_version="lite-v1",
        target=str(configuration["target"]),
        threshold=float(configuration["threshold"]),
        minimum_answered_fraction=float(
            configuration["minimum_answered_fraction"]
        ),
        test_status=str(configuration["test_status"]),
    )


@app.post(
    "/v1/screenings",
    response_model=ScreeningResponse,
    dependencies=[Depends(require_api_key)],
    tags=["screening"],
)
def screen_household(payload: ScreeningRequest) -> ScreeningResponse:
    answers = payload.model_dump()
    count_error = validate_household_counts(answers)
    if count_error:
        raise HTTPException(
            status_code=422,
            detail=f"Household counts are inconsistent: {count_error}",
        )

    bundle = get_bundle()
    assessment = build_assessment_features(
        answers, bundle.configuration["input_features"]
    )
    try:
        result = run_screening(bundle, assessment)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return ScreeningResponse(
        score=result.score,
        threshold=result.threshold,
        elevated_risk=result.elevated_risk,
        completeness=result.completeness,
        limited_information=result.limited_information,
        small_household=result.small_household,
        model_name=str(bundle.configuration["model_name"]),
        model_version="lite-v1",
    )
