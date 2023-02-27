"""Module containing all classes related to Envoy configured by Marin3r"""
from enum import Enum
from functools import cached_property

import yaml
import openshift as oc

from testsuite.httpx import HttpxBackoffClient
from testsuite.openshift import OpenShiftObject, LifecycleObject
from testsuite.openshift.client import OpenShiftClient
from testsuite.openshift.httpbin import Httpbin
from testsuite.openshift.route import Route


class DiscoveryService(OpenShiftObject):
    """DiscoveryService resource"""

    @classmethod
    def create_instance(cls, openshift: OpenShiftClient, name, labels=None):
        """Creates new DiscoveryService"""
        model = {
            "apiVersion": "operator.marin3r.3scale.net/v1alpha1",
            "kind": "DiscoveryService",
            "metadata": {"name": name},
        }

        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)


def convert_to_yaml(data: dict[str, dict]):
    """Convert dict to specific format Marin3r uses and convert value to yaml if it is not a string"""
    transformed = []
    for key, value in data.items():
        transformed.append({"name": key, "value": value if isinstance(value, str) else yaml.dump(value)})
    return transformed


class EnvoyConfig(OpenShiftObject):
    """EnvoyConfig resource"""

    # pylint: disable=invalid-name
    class Status(Enum):
        """All known statuses of EnvoyConfig"""

        InSync = "InSync"
        Rollback = "Rollback"

    @classmethod
    def create_instance(
        cls,
        openshift: OpenShiftClient,
        name,
        listeners,
        clusters=None,
        endpoints=None,
        runtimes=None,
        routes=None,
        scoped_routes=None,
        secrets=None,
        labels=None,
    ):
        """Creates new EnvoyConfig"""
        model = {
            "apiVersion": "marin3r.3scale.net/v1alpha1",
            "kind": "EnvoyConfig",
            "metadata": {"name": name},
            "spec": {
                "nodeID": name,
                "serialization": "yaml",
                "envoyResources": {
                    "clusters": convert_to_yaml(clusters or {}),
                    "endpoints": convert_to_yaml(endpoints or {}),
                    "runtimes": convert_to_yaml(runtimes or {}),
                    "routes": convert_to_yaml(routes or {}),
                    "scoped_routes": convert_to_yaml(scoped_routes or {}),
                    "listeners": convert_to_yaml(listeners),
                    "secrets": [{"name": value} for value in (secrets or {}).values()],
                },
            },
        }

        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)

    @cached_property
    def ports(self) -> dict[str, int]:
        """Returns all the configured ports and their name"""
        ports = {}
        for listener in self.model.spec.envoyResources.listeners:
            ports[listener.name] = yaml.safe_load(listener.value)["address"]["socket_address"]["port_value"]
        return ports

    def wait_status(self, status: Status, timeout=30):
        """Waits until config has the expected status"""
        with oc.timeout(timeout):

            def _status(obj):
                return obj.model.status.cacheState == status.value

            success, _, _ = self.self_selector().until_all(success_func=_status)
            return success


class EnvoyDeployment(OpenShiftObject):
    """Envoy deployed from template"""

    @classmethod
    def create_instance(
        cls,
        openshift: OpenShiftClient,
        name,
        discovery_service: DiscoveryService,
        config: EnvoyConfig,
        image,
        labels=None,
    ):
        """Creates new EnvoyDeployment"""
        model = {
            "apiVersion": "operator.marin3r.3scale.net/v1alpha1",
            "kind": "EnvoyDeployment",
            "metadata": {"name": name, "namespace": openshift.project},
            "spec": {
                "discoveryServiceRef": discovery_service.name(),
                "envoyConfigRef": config.name(),
                "ports": [{"name": key, "port": value} for key, value in config.ports.items()],
                "image": image,
                "replicas": {"static": 1},
            },
        }

        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)

    def wait(self):
        """Waits until the deployment is ready"""
        with self.context, oc.timeout(120):
            success, _, _ = oc.selector("deployment", labels={"app.kubernetes.io/instance": self.name()}).until_all(
                success_func=lambda obj: "readyReplicas" in obj.model.status
            )
            return success


class Envoy(LifecycleObject):
    """Envoy instance deployed through EnvoyDeployment"""

    def __init__(
        self,
        openshift: OpenShiftClient,
        name,
        discovery_service: DiscoveryService,
        config: EnvoyConfig,
        backend: Httpbin,
        image,
        tls=False,
        labels=None,
    ) -> None:
        super().__init__()
        self.openshift = openshift
        self.name = name
        self.discovery_service = discovery_service
        self.config = config
        self.backend = backend
        self.image = image
        self.labels = labels
        self.tls = tls

        self.service = None
        self.route = None
        self.deployment = None

    def create_route(self):
        """Creates routes pointing to this envoy"""
        tls = Route.Type.PASSTHROUGH if self.tls else None
        return Route.create_instance(self.openshift, self.name, self.name, "http", tls)

    def create_service(self):
        """Creates service pointing to this envoy"""
        model = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {"name": self.name, "namespace": self.openshift.project},
            "spec": {
                "selector": {"app.kubernetes.io/instance": self.name},
                "ports": [
                    {"name": key, "targetPort": value, "port": value, "protocol": "TCP"}
                    for key, value in self.config.ports.items()
                ],
            },
        }
        return OpenShiftObject(dict_to_model=model)

    def commit(self):
        self.deployment = EnvoyDeployment.create_instance(
            self.openshift,
            self.name,
            self.discovery_service,
            self.config,
            self.image,
            self.labels,
        )
        self.deployment.commit()
        self.deployment.wait()
        self.service = self.create_service()
        self.service.commit()
        self.route = self.create_route()
        self.route.commit()

    def delete(self):
        for item in [self.route, self.service, self.deployment]:
            if item is not None:
                item.delete()

    def client(self, **kwargs):
        """Return Httpx client for the requests to this backend"""
        protocol = "https" if self.tls else "http"
        return HttpxBackoffClient(base_url=f"{protocol}://{self.route.hostname}", **kwargs)


class SidecarEnvoy(Envoy):
    """Envoy injected as a Sidecar"""

    def commit(self):
        def _apply(deployment):
            template = deployment.model.spec.template
            template.setdefault("metadata", {}).setdefault("annotations", {})[
                "marin3r.3scale.net/node-id"
            ] = self.config.name()
            template.metadata.annotations["marin3r.3scale.net/envoy-image"] = self.image
            template.metadata.annotations["marin3r.3scale.net/ports"] = ",".join(
                f"{key}:{value}" for key, value in self.config.ports.items()
            )
            template.metadata.labels["marin3r.3scale.net/status"] = "enabled"
            template.metadata.labels["app.kubernetes.io/instance"] = self.name

        self.backend.deployment.modify_and_apply(_apply)
        self.openshift.is_ready(self.backend.deployment.self_selector())
        self.service = self.create_service()
        self.service.commit()
        self.route = self.create_route()
        self.route.commit()
