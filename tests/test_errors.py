def test_404_returns_rfc9457_problem_details(client):
    response = client.get("/api/non-existent-endpoint")
    assert response.status_code == 404
    assert response.headers.get("content-type").startswith("application/problem+json")

    data = response.json()
    assert data["status"] == 404
    assert data["title"] == "Not Found"
    assert "instance" in data


def test_406_not_acceptable_for_xml_accept_header(client):
    response = client.get("/api/health", headers={"Accept": "application/xml"})
    assert response.status_code == 406
    assert response.headers.get("content-type").startswith("application/problem+json")

    data = response.json()
    assert data["status"] == 406
    assert data["title"] == "Not Acceptable"


def test_415_unsupported_media_type_for_plain_text(client):
    response = client.post(
        "/api/health",
        content="raw text body",
        headers={"Content-Type": "text/plain"},
    )
    assert response.status_code == 415
    assert response.headers.get("content-type").startswith("application/problem+json")

    data = response.json()
    assert data["status"] == 415
    assert data["title"] == "Unsupported Media Type"
