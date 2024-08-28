##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################

from litp.core.plugin import Plugin
from litp.core.task import ConfigTask, CallbackTask, RemoteExecutionTask
from litp.core.exceptions import CallbackExecutionException

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story107192Plugin(Plugin):
    """
    LITP story107192 plugin
    """

    def validate_model(self, plugin_api_context):
        """
        This method can be used to validate the model ...

        .. warning::
          Please provide a summary of the model validation performed by
          story107192 here
        """
        errors = []
#        nodes = plugin_api_context.query("node")
#        for node in nodes:
#            if node.hostname == "NOT_ALLOWED":
#                errors.append(ValidationError(
#                                item_path=node.get_vpath(),
#                                error_message="hostname cannot "
#                                "be 'NOT_ALLOWED'"
#                              ))
        return errors

    def cb_do_nothing(self, cb_api, *args, **kwargs):
        pass

    def cb_fail(self, cb_api, *args, **kwargs):
        raise CallbackExecutionException("Oh no!")

    def create_configuration(self, plugin_api_context):
        """
        Plugin can provide tasks based on the model ...

        """
        tasks = []

        nodes = plugin_api_context.query("node") + \
                [plugin_api_context.query_by_vpath("/ms")]
        for node in nodes:
            for trigger_item in node.query("software-item",
                    item_id="story107192"):
                cfg_task = ConfigTask(
                    node,
                    trigger_item,
                    "Nilpotent ConfigTask",
                    "notify", trigger_item.item_id,
                )
                tasks.append(cfg_task)

                cb_task = CallbackTask(
                    trigger_item,
                    "Nilpotent CallbackTask",
                    self.cb_do_nothing,
                )
                tasks.append(cb_task)

                re_task = RemoteExecutionTask(
                    [node],
                    trigger_item,
                    "Nilpotent RemoteExecutionTask",
                    "rpcutil",
                    "ping",
                )
                tasks.append(re_task)

            for fail_item in node.query("software-item",
                    item_id="story107192_fail"):
                if fail_item.applied_properties_determinable:
                    cb_task = CallbackTask(
                            fail_item,
                            "Failing CallbackTask",
                            self.cb_fail,
                    )
                    tasks.append(cb_task)

        return tasks
