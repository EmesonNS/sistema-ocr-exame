import re


def test_request_observability_injects_request_id_header(client, caplog):
    with caplog.at_level("INFO"):
        response = client.get("/health")

    assert response.status_code == 200
    request_id = response.headers.get("X-Request-ID")
    assert request_id
    assert re.fullmatch(r"[0-9a-f]{32}", request_id)
    assert "request_completed" in caplog.text


def test_request_observability_preserves_client_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "custom-request-id"})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "custom-request-id"
