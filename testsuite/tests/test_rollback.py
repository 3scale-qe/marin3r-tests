"""Tests if rollback functionality works as expected, e.g. rejected configuration should be rolled back
https://github.com/3scale-ops/marin3r/blob/main/docs/walkthroughs/self-healing.md
"""
from testsuite.openshift.envoy import EnvoyConfig


# You cannot change socket_options with envoy 1.25, and the update should be rejected
INVALID_LISTENER_CHANGE = """
name: http
enable_reuse_port: false
address:
    socket_address:
      address: 0.0.0.0
      port_value: 5000
socket_options:
  - description: "support tcp keep alive"
    state: 0
    level: 1
    name: 9
    int_value: 1
filter_chains:
    - filters:
        - name: envoy.http_connection_manager
          typed_config:
            "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
            stat_prefix: local
            use_remote_address: true
            route_config:
              name: local_route
              virtual_hosts:
              - name: local_service
                domains: ['*']
                routes:
                - { match: { prefix: "/" }, route: { cluster: "httpbin" } }
            http_filters:
                - name: envoy.filters.http.router
                  typed_config:
                    "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
        """


def update_config(config: EnvoyConfig):
    """Updates EnvoyConfig configuration to an invalid one"""

    def _apply(obj):
        obj.model.spec.envoyResources.listeners = [{"name": "http", "value": INVALID_LISTENER_CHANGE}]

    result, success = config.modify_and_apply(_apply)
    assert success, f"Config wasn't updated: {result}"


def test_update_config(client, envoy_config):
    """Tests if the incorrect configuration will be rolled back and won't stop working"""
    response = client.get("/get")
    assert response.status_code == 200

    update_config(envoy_config)
    assert envoy_config.wait_status(EnvoyConfig.Status.Rollback)

    response = client.get("/get")
    assert response.status_code == 200
