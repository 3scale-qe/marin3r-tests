"""Basic OpenShift classes"""
import abc

from openshift import APIObject


class LifecycleObject(abc.ABC):
    """Any objects which has its lifecycle controlled by create() and delete() methods"""

    @abc.abstractmethod
    def commit(self):
        """Commits resource.
        if there is some reconciliation needed, the method should wait until it is all reconciled"""

    @abc.abstractmethod
    def delete(self):
        """Removes resource,
        if there is some reconciliation needed, the method should wait until it is all reconciled"""


class OpenShiftObject(APIObject):
    """Custom APIObjects which tracks if the object was already committed to the server or not"""

    def __init__(self, dict_to_model=None, string_to_model=None, context=None):
        super().__init__(dict_to_model, string_to_model, context)
        self.committed = False

    def commit(self):
        """
        Creates object on the server and returns created entity.
        It will be the same class but attributes might differ, due to server adding/rejecting some of them.
        """
        self.create(["--save-config=true"])
        self.committed = True
        return self.refresh()

    def delete(self, ignore_not_found=True, cmd_args=None):
        """Deletes the resource, by default ignored not found"""
        return super().delete(ignore_not_found, cmd_args)
