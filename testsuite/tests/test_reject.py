"""Tests if EnvoyConfig containing invalid configuration will be rejected by a webhook"""
import pytest
from openshift import OpenShiftPythonException

from testsuite.openshift.envoy import EnvoyConfig


def test_reject_invalid_config(openshift, blame):
    """Invalid configuration should be rejected by a webhook"""
    config = EnvoyConfig.create_instance(
        openshift,
        blame("config"),
        {
            "http": """
name: http
enable_reuse_port: false
address: MISSING
    """
        },
    )

    with pytest.raises(OpenShiftPythonException) as exc:
        config.commit()

    assert 'admission webhook "envoyconfig.marin3r.3scale.net" denied the request' in exc.value.result.err()
