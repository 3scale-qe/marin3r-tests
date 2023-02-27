"""Configure basic envoy deployment test"""


def test_simple_request(client):
    """Tests if simple envoy configuration is applied and request works"""
    response = client.get("/get")
    assert response.status_code == 200
