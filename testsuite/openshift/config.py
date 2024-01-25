"""Module containing all config classes"""
from abc import ABC, abstractmethod
from enum import Enum
from functools import cached_property

import openshift as oc
import yaml

from testsuite.openshift import OpenShiftObject
from testsuite.openshift.client import OpenShiftClient


def convert_to_yaml(data: list[str | dict]):
    """Convert dict to specific format Marin3r uses and convert value to yaml if it is not a string"""
    transformed = []
    for value in data:
        transformed.append({"value": value if isinstance(value, str) else yaml.dump(value)})
    return transformed


class BaseEnvoyConfig(OpenShiftObject, ABC):
    """Base class for all EnvoyConfigs"""

    class Status(Enum):
        """All known statuses of EnvoyConfig"""

        # pylint: disable=invalid-name
        InSync = "InSync"
        Rollback = "Rollback"

    @classmethod
    @abstractmethod
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
        """Creates new EnvoyConfig instance"""

    @property
    @abstractmethod
    def listeners(self):
        """Returns all configured listeners"""

    @cached_property
    def ports(self) -> dict[str, int]:
        """Returns all the configured ports and their name"""
        ports = {}
        for listener in self.listeners:
            ports[listener["name"]] = listener["address"]["socket_address"]["port_value"]
        return ports

    def wait_status(self, status: Status, timeout=60):
        """Waits until config has the expected status"""
        with oc.timeout(timeout):

            def _status(obj):
                return obj.model.status.cacheState == status.value

            success, _, _ = self.self_selector().until_all(success_func=_status)
            return success


class LegacyEnvoyConfig(BaseEnvoyConfig):
    """Legacy EnvoyConfig resource, using envoyResources field"""

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
                    "clusters": convert_to_yaml(clusters or []),
                    "endpoints": convert_to_yaml(endpoints or []),
                    "runtimes": convert_to_yaml(runtimes or []),
                    "routes": convert_to_yaml(routes or []),
                    "scopedRoutes": convert_to_yaml(scoped_routes or []),
                    "listeners": convert_to_yaml(listeners),
                    "secrets": [{"name": value} for value, _ in (secrets or [])],
                },
            },
        }

        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)

    @property
    def listeners(self):
        listeners = []
        for listener in self.model.spec.envoyResources.listeners:
            listeners.append(yaml.safe_load(listener["value"]))
        return listeners


class EnvoyConfig(BaseEnvoyConfig):
    """Envoy config configured using spec.resources"""

    # pylint: disable=too-many-locals
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
        """Creates new instance"""
        model = {
            "apiVersion": "marin3r.3scale.net/v1alpha1",
            "kind": "EnvoyConfig",
            "metadata": {"name": name},
            "spec": {
                "nodeID": name,
                "serialization": "yaml",
                "resources": [],
            },
        }
        for resource_type, values in {
            "cluster": clusters,
            "endpoint": endpoints,
            "runtime": runtimes,
            "route": routes,
            "scopedRoute": scoped_routes,
            "listener": listeners,
        }.items():
            for value in values or []:
                if isinstance(value, str):
                    value = yaml.safe_load(value)
                model["spec"]["resources"].append(
                    {
                        "type": resource_type,
                        "value": value,
                    }
                )
        for secret, is_ca in secrets or []:
            resource = {
                "type": "secret",
                "generateFromTlsSecret": secret,
            }
            if is_ca:
                resource["blueprint"] = "validationContext"
            model["spec"]["resources"].append(resource)

        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)

    @property
    def listeners(self):
        sections = []
        for section in self.model.spec.resources:
            if section.type == "listener":
                sections.append(section["value"])
        return sections
