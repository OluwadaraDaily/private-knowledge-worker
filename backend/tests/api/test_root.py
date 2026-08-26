from fastapi.testclient import TestClient


def test_get_api_info(client: TestClient) -> None:
    response = client.get("/api/v1/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "Private Knowledge Worker API",
        "version": "0.1.0",
    }


def test_unknown_route_returns_not_found(client: TestClient) -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
