"""Tests if configuration using routes field works as expected"""
import pytest


@pytest.fixture(scope="module")
def routes():
    """Routes configuration for httpbin"""
    return [
        """
name: local
virtual_hosts:
  - name: all
    domains: ["*"]
    routes:
      - match:
            prefix: "/"
        route:
            cluster: httpbin
"""
    ]


@pytest.fixture(scope="module")
def listeners():
    """Listeners section of EnvoyConfig. Keys are name, value is config"""
    return [
        """
name: http
address:
    socket_address:
      address: 0.0.0.0
      port_value: 8000
filter_chains:
    - filters:
        - name: envoy.http_connection_manager
          typed_config:
            "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
            stat_prefix: local
            use_remote_address: true
            rds: { route_config_name: "local", config_source: { ads: {}, resource_api_version: "V3" }}
            http_filters:
                - name: envoy.filters.http.router
                  typed_config:
                    "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
        """
    ]


def test_routes(client):
    """Tests if configuration using routes works"""
    response = client.get("/get")
    assert response.status_code == 200
