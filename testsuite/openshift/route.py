"""All classes related to Openshift Route"""
from enum import Enum
from functools import cached_property
from typing import Union

from testsuite.openshift import OpenShiftObject
from testsuite.openshift.client import OpenShiftClient


class Route(OpenShiftObject):
    """Route Openshift object"""

    class Type(Enum):
        """Route types enum."""

        EDGE = "edge"
        PASSTHROUGH = "passthrough"
        REENCRYPT = "reencrypt"

        def __str__(self) -> str:
            return self.value

    @classmethod
    def create_instance(
        cls,
        openshift: OpenShiftClient,
        name,
        service,
        port,
        tls: Union[Type, str] = None,
        labels=None,
    ):
        """Creates new Route instance"""
        model = {
            "apiVersion": "route.openshift.io/v1",
            "kind": "Route",
            "metadata": {"name": name},
            "spec": {
                "to": {"kind": "Service", "name": service},
                "port": {"targetPort": port},
            },
        }
        if tls is not None:
            model["spec"]["tls"] = {"termination": str(tls)}
        if labels is not None:
            model["metadata"]["labels"] = labels

        return cls(model, context=openshift.context)

    @cached_property
    def hostname(self):
        """Returns hostname of the route"""
        return self.model.status.ingress[0].host
