"""Base conftest"""
import pytest

from testsuite.config import settings
from testsuite.openshift.envoy import DiscoveryService, EnvoyConfig, Envoy, SidecarEnvoy
from testsuite.openshift.httpbin import Httpbin
from testsuite.utils import randomize, _whoami, create_simple_cluster


@pytest.fixture(scope="session")
def testconfig():
    """Testsuite settings"""
    return settings


@pytest.fixture(scope="session")
def openshift(testconfig):
    """OpenShift client for the primary namespace"""
    client = testconfig["openshift"]
    if not client.connected:
        pytest.fail("You are not logged into Openshift or the namespace doesn't exist")
    return client


@pytest.fixture(scope="session")
def blame(request):
    """Returns function that will add random identifier to the name"""

    def _blame(name: str, tail: int = 3) -> str:
        """Create 'scoped' name within given test

        This returns unique name for object(s) to avoid conflicts

        Args:
            :param name: Base name, e.g. 'svc'
            :param tail: length of random suffix"""

        nodename = request.node.name
        if nodename.startswith("test_"):  # is this always true?
            nodename = nodename[5:]

        context = nodename.lower().split("_")[0]
        if len(context) > 2:
            context = context[:2] + context[2:-1].translate(str.maketrans("", "", "aiyu")) + context[-1]

        if "." in context:
            context = context.split(".")[0]

        return randomize(f"{name[:8]}-{_whoami()[:8]}-{context[:9]}", tail=tail)

    return _blame


@pytest.fixture(scope="session")
def label(blame):
    """Session scope label for all resources"""
    return blame("testrun")


@pytest.fixture(scope="session")
def backend(request, openshift, blame, label):
    """Deploys Httpbin backend"""
    httpbin = Httpbin(openshift, blame("httpbin"), label)
    request.addfinalizer(httpbin.delete)
    httpbin.commit()
    return httpbin


@pytest.fixture(scope="session")
def discovery_service(request, openshift, blame, label):
    """Discovery Service to be used in tests"""
    service = DiscoveryService.create_instance(openshift, blame("discovery_service"), {"app": label})
    request.addfinalizer(service.delete)
    service.commit()
    return service


@pytest.fixture(scope="module")
def listeners():
    """Listeners section of EnvoyConfig. Keys are name, value is config"""
    return {
        "http": """
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
    }


@pytest.fixture(scope="module")
def clusters(backend):
    """Clusters section of EnvoyConfig. Keys are name, value is config"""
    return {"httpbin": create_simple_cluster(backend, "httpbin")}


@pytest.fixture(scope="module")
def endpoints():
    """Endpoints section of EnvoyConfig. Keys are name, value is config"""
    return {}


@pytest.fixture(scope="module")
def runtimes():
    """Runtimes section of EnvoyConfig. Keys are name, value is config"""
    return {}


@pytest.fixture(scope="module")
def routes():
    """Routes section of EnvoyConfig. Keys are name, value is config"""
    return {}


@pytest.fixture(scope="module")
def scoped_routes():
    """ScopedRoutes section of EnvoyConfig. Keys are name, value is config"""
    return {}


@pytest.fixture(scope="module")
def secrets():
    """Secrets section of EnvoyConfig. Keys are name, value is secret name"""
    return {}


# pylint: disable=unused-argument
@pytest.fixture(scope="module")
def envoy_config(
    request, openshift, blame, listeners, clusters, endpoints, runtimes, routes, scoped_routes, secrets, envoy_class
):
    """EnvoyConfig"""
    config = EnvoyConfig.create_instance(
        openshift,
        blame("config"),
        listeners,
        clusters,
        endpoints,
        runtimes,
        routes,
        scoped_routes,
        secrets,
    )
    request.addfinalizer(config.delete)
    config.commit()
    return config


@pytest.fixture(scope="module", params=[Envoy, SidecarEnvoy])
def envoy_class(request):
    """Envoy class to use in tests"""
    return request.param


@pytest.fixture(scope="module")
def use_tls():
    """True, if the Envoy should be configured with TLS"""
    return False


@pytest.fixture(scope="module")
def envoy(request, envoy_class, openshift, envoy_config, discovery_service, blame, testconfig, backend, use_tls):
    """Envoy to be used in tests"""
    envoy = envoy_class(
        openshift,
        blame("envoy"),
        discovery_service,
        envoy_config,
        backend,
        testconfig["envoy"]["image"],
        use_tls,
    )
    request.addfinalizer(envoy.delete)
    envoy.commit()
    return envoy


@pytest.fixture(scope="module")
def client(envoy):
    """Default HTTPX client for connecting to envoy"""
    return envoy.client()
