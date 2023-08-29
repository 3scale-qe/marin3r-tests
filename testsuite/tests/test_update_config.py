"""Tests if new configuration is applied, if valid"""
import yaml

from testsuite.openshift.config import BaseEnvoyConfig, LegacyEnvoyConfig

INVALID_URL_CLUSTER = {
    "name": "httpbin",
    "connect_timeout": "0.25s",
    "type": "STRICT_DNS",
    "load_assignment": {
        "cluster_name": "httpbin",
        "endpoints": [
            {
                "lb_endpoints": [
                    {
                        "endpoint": {
                            "address": {
                                "socket_address": {
                                    "address": "invalid.service",
                                    "port_value": 8080,
                                }
                            }
                        }
                    }
                ]
            }
        ],
    },
}


def update_config(config: BaseEnvoyConfig):
    """Update envoy configuration"""

    if isinstance(config, LegacyEnvoyConfig):

        def _apply(obj):
            obj.model.spec.envoyResources.clusters = [{"value": yaml.dump(INVALID_URL_CLUSTER)}]

    else:

        def _apply(obj):
            for resource in obj.model.spec.resources:
                if resource.type == "cluster":
                    resource.value = INVALID_URL_CLUSTER

    result, success = config.modify_and_apply(_apply)
    assert success, f"Config wasn't updated: {result}"


def test_update_config(client, envoy_config):
    """Tests if updated config is applied"""
    response = client.get("/get")
    assert response.status_code == 200

    update_config(envoy_config)
    assert envoy_config.wait_status(BaseEnvoyConfig.Status.InSync)

    client.retry_codes = {}
    response = client.get("/get")
    assert response.status_code == 503
