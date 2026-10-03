import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

@pytest.fixture # to będzie fixture, której będziemy używać jako moją aplikację wszędzie w testach
# Działa jak @BeforeEach i @AfterEach w junit
def client():
    # @BeforeEach - przed yield
    with TestClient(app) as test_client:
        yield test_client
    # @AfterEach - po yield
