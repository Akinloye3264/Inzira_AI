from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def complete_payload() -> dict[str, object]:
    return {
        "province": 1,
        "ur": 2,
        "household_members": 6,
        "children_count": 3,
        "elderly_count": 1,
        "sleeping_rooms": 2,
        "floor_material": 1,
        "electricity_access": 1,
        "livestock_range": "1_2",
        "mobile_phone": 1,
        "recent_internet_use": 0,
        "insured_members": 3,
        "agricultural_activity": 1,
        "wage_employment": 0,
        "nonfarm_business": 0,
    }


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_screening_endpoint_runs_verified_model():
    response = client.post("/v1/screenings", json=complete_payload())
    assert response.status_code == 200
    result = response.json()
    assert 0 <= result["score"] <= 1
    assert result["model_version"] == "lite-v1"
    assert result["decision_role"] == "initial_screening_only"


def test_screening_endpoint_rejects_inconsistent_counts():
    payload = complete_payload()
    payload["children_count"] = 6
    payload["elderly_count"] = 2
    response = client.post("/v1/screenings", json=payload)
    assert response.status_code == 422


def test_api_key_protects_model_routes(monkeypatch):
    monkeypatch.setenv("INZIRA_API_KEY", "test-secret")
    assert client.post("/v1/screenings", json=complete_payload()).status_code == 401
    response = client.post(
        "/v1/screenings",
        json=complete_payload(),
        headers={"X-API-Key": "test-secret"},
    )
    assert response.status_code == 200
