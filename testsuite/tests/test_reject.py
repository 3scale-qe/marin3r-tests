"""Tests if EnvoyConfig containing invalid configuration will be rejected by a webhook"""
import pytest
from openshift import OpenShiftPythonException


def test_reject_invalid_config(openshift, blame, envoy_config_class):
    """Invalid configuration should be rejected by a webhook"""
    config = envoy_config_class.create_instance(
        openshift,
        blame("config"),
        [
            """
name: http
enable_reuse_port: false
address: MISSING
    """
        ],
    )

    with pytest.raises(OpenShiftPythonException) as exc:
        config.commit()

    assert 'admission webhook "envoyconfig.marin3r.3scale.net-v1alpha1" denied the request' in exc.value.result.err()
