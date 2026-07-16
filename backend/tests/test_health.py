from flask.testing import FlaskClient


def test_health_endpoint(client: FlaskClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.content_type == "application/json"
    assert response.get_json() == {
        "status": "running",
        "service": "school-policy-api",
    }
