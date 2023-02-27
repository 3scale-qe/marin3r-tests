"""Conftest for all TLS tests"""
from typing import Optional

import pytest

from testsuite.certificates import CertInfo, Certificate, CFSSLClient
from testsuite.utils import cert_builder


@pytest.fixture(scope="module")
def listeners(secrets):
    """Listeners section of EnvoyConfig. Keys are name, value is config"""
    return {
        "http": f"""
name: http
address:
    socket_address:
      address: 0.0.0.0
      port_value: 8000
filter_chains:
  - transport_socket:
      name: envoy.transport_sockets.tls
      typed_config:
        "@type": type.googleapis.com/envoy.extensions.transport_sockets.tls.v3.DownstreamTlsContext
        require_client_certificate: true
        common_tls_context:
            tls_certificate_sds_secret_configs:
              - name: {secrets["envoy_cert"]}
                sds_config: {{ ads: {{}}, resource_api_version: "V3" }}
            validation_context_sds_secret_config:
              name: {secrets["envoy_ca"]}
              sds_config: {{ ads: {{}}, resource_api_version: "V3" }}
    filters:
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
            - {{ match: {{ prefix: "/" }}, route: {{ cluster: "httpbin" }}}}
        http_filters:
            - name: envoy.filters.http.router
              typed_config:
                "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
        """
    }


@pytest.fixture(scope="module")
def secrets(create_secret, certificates, blame):
    """Define all the secrets used in TLS, specifically CA and envoy cert"""
    envoy_cert = create_secret(certificates["envoy_cert"], blame("envoy-cert"))
    envoy_ca = create_secret(certificates["envoy_ca"], blame("envoy-ca"))
    return {"envoy_cert": envoy_cert, "envoy_ca": envoy_ca}


@pytest.fixture(scope="session")
def wildcard_domain(openshift):
    """
    Wildcard domain of openshift cluster
    """
    return f"*.{openshift.apps_url}"


@pytest.fixture(scope="module")
def certificates(cfssl, wildcard_domain):
    """
    Certificate hierarchy used for the tests
    May be overwritten to configure different test cases
    """
    cert_attributes = {
        "O": "Organization Test",
        "OU": "Unit Test",
        "L": "Location Test",
        "ST": "State Test",
        "C": "Country Test",
    }
    chain = {
        "envoy_ca": CertInfo(
            children={
                "envoy_cert": None,
                "valid_cert": CertInfo(names=[cert_attributes]),
            }
        ),
        "invalid_ca": CertInfo(children={"invalid_cert": None}),
    }
    return cert_builder(cfssl, chain, wildcard_domain)


@pytest.fixture(scope="module")
def create_secret(blame, request, openshift):
    """Creates TLS secret from Certificate"""

    def _create_secret(certificate: Certificate, name: str, labels: Optional[dict[str, str]] = None):
        secret_name = blame(name)
        secret = openshift.create_tls_secret(secret_name, certificate, labels=labels)
        request.addfinalizer(lambda: openshift.delete_selector(secret))
        return secret_name

    return _create_secret


@pytest.fixture(scope="module")
def use_tls():
    """Use TLS in envoy"""
    return True


@pytest.fixture(scope="session")
def cfssl(testconfig):
    """CFSSL client library"""
    client = CFSSLClient(binary=testconfig["cfssl"])
    if not client.exists:
        raise ValueError("CFSSL binary path is not properly configured!")
    return client
