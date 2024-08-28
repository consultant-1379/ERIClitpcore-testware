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
#from litp.core.validators import ValidationError
from litp.core.task import ConfigTask

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class story10575depend2Plugin(Plugin):
    """
    LITP story10575depend2 plugin
    """

    def validate_model(self, plugin_api_context):
        """
        This method can be used to validate the model ...

        .. warning::
          Please provide a summary of the model validation performed by
          story10575depend2 here
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

    @staticmethod
    def _config_items(node_item, item_type):
        return node_item.query(item_type)

    @staticmethod
    def _config_task(node_item, model_item, kwargs, new_id=''):
        if new_id != '':
            call_id = new_id
        else:
            call_id = "call_id_"
        description = "ConfigTask {0} on node {1}".format(
            model_item.name, node_item.hostname
        )
        return ConfigTask(
            node_item, model_item, description, "notify",
            "{0}{1}".format(call_id, model_item.name), **kwargs
        )

    def _create_depend(self, node_item, model_item, query_dependency):
        tasks = list()
        task = None
        # dependency story-10575a query item
        # test_05: dependency story-10575b query item
        if model_item.is_initial() or model_item.is_updated():
            kwargs = {"message": model_item.name}
            task = self._config_task(node_item, model_item, kwargs)
        if task:
            config_item = node_item.query(query_dependency)
            if config_item:
                task.requires.add(config_item[0])
            tasks.append(task)
        return tasks

    def create_configuration(self, plugin_api_context):
        """
        Plugin can provide tasks based on the model ...

        *Example CLI for this plugin:*

        .. code-block:: bash

          # Please provide an example CLI snippet for plugin story10575depend
          # here
        """
        tasks = []
        nodes = plugin_api_context.query("node") +\
            plugin_api_context.query("ms")

        for node in nodes:
            if self._config_items(node, "depend2-story-10575"):
                _sw = node.query("depend2-story-10575")[0]
                tasks.extend(
                    self._create_depend(node, _sw, "depend-story-10575")
                )
        log.trace.debug("TASKS_depend: {0}".format(tasks))
        return tasks
