"""Tests that TLS configuration works as expected"""
import pytest
from httpx import ReadError


def test_valid_certificate(certificates, envoy):
    """Tests that valid certificate will be accepted"""
    with envoy.client(verify=certificates["envoy_ca"], cert=certificates["valid_cert"]) as client:
        response = client.get("/get")
        assert response.status_code == 200


def test_no_certificate(envoy, certificates):
    """Test that request without certificate will be rejected"""
    with pytest.raises(ReadError, match="certificate required"):
        with envoy.client(verify=certificates["envoy_ca"]) as client:
            client.get("/get")


def test_invalid_certificate(certificates, envoy):
    """Tests that certificate with different CA will be rejeceted"""
    with pytest.raises(ReadError, match="unknown ca"):
        with envoy.client(verify=certificates["envoy_ca"], cert=certificates["invalid_cert"]) as client:
            client.get("/get")
