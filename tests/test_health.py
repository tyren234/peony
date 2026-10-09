def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-content-type-options") == "nosniff"


def test_home_page_endpoint(client):
    response = client.get("/", headers={"Accept": "text/html"})
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert "content-security-policy" in response.headers
    assert "Waterdeep Watchtower" in response.text
