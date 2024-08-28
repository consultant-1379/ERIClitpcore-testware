##############################################################################
# COPYRIGHT Ericsson AB 2014
#
# The copyright to the computer program(s) herein is the property of
# Ericsson AB. The programs may be used and/or copied only with written
# permission from Ericsson AB. or in accordance with the terms and
# conditions stipulated in the agreement/contract under which the
# program(s) have been supplied.
##############################################################################
import time
import os
from litp.core.plugin import Plugin
#from litp.core.validators import ValidationError
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask
from litp.core.task import OrderedTaskList
from litp.core.execution_manager import CallbackExecutionException
from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story10575Plugin(Plugin):
    """
    LITP story10575 plugin
    Creates a model item that can be configured to generate
    single or multiple ConfigTasks, and can optionally
    genrate deconfigure ConfigTasks
    """

    @staticmethod
    def _config_task_description(node_item, model_item, deconfigure=False):
        if deconfigure:
            description = "ConfigTask deconfigure {0} on node {1}"
        else:
            description = "ConfigTask {0} on node {1}"
        return description.format(model_item.name, node_item.hostname)

    @staticmethod
    def _config_task(node_item, model_item, description, kwargs, new_id=''):
        if new_id != '':
            call_id = new_id
        else:
            call_id = "call_id_"
        return ConfigTask(
            node_item, model_item, description, "notify",
            "{0}{1}".format(call_id, model_item.name), **kwargs
        )

    @staticmethod
    def _config_task2(node_item, model_item, description, kwargs, new_id=''):
        if new_id != '':
            call_id = new_id
        else:
            call_id = "call_id_"
        return ConfigTask(
            node_item, model_item, description, "file",
            "{0}{1}".format(call_id, model_item.name), **kwargs
        )

    @staticmethod
    def _config_task3(node_item, model_item, description, kwargs, new_id=''):
        if new_id != '':
            call_id = new_id
        else:
            call_id = "call_id_"
        return ConfigTask(
            node_item, model_item, description, "package",
            "{0}{1}".format(call_id, model_item.name), **kwargs
        )

    def cb_simple_callback(self, api):
        time.sleep(2)
        log.trace.debug(api)

    def _callback_task(self, model_item):
        description = "standalone CallbackTask {0}".format(model_item.name)
        return CallbackTask(model_item, description, self.cb_simple_callback)

    def mock_call(self, api):
        log.trace.debug(
        "Another CallbackTask {0}".format(api))

    def _mock_callback(self, model_item):
        description = "Another CallbackTask {0}".format(model_item.name)
        return CallbackTask(model_item, description, self.mock_call)

    def cb_wait_callback(self, api):
        while True:
            time.sleep(4)
            if os.path.isfile("/tmp/story10575.txt"):
                break

    def _cb_wait_while_check_manifests(self, model_item):
        description = "Wait CallbackTask {0}".format(model_item.name)
        return CallbackTask(model_item, description, self.cb_wait_callback)

    def cb_fail(self, api):
        raise CallbackExecutionException("callback task failed")

    def _cb_fail_callback_task(self, model_item):
        description = "Fail CallbackTask {0}".format(model_item.name)
        return CallbackTask(model_item, description, self.cb_fail)

    @staticmethod
    def _config_items(node_item, item_type):
        return node_item.query(item_type)

    def _generate_tasks(self, node_item, model_item):
        ordered_tasks = list()
        tasks = list()
        task = None
        task2 = None
        task_ = None
        task3 = None
        wait_task = None
        fail_task = None
        fail_phase = None
        # If item is in state "Initial" or "Updated" a ConfigTask is generated
        if model_item.is_initial() or model_item.is_updated():
            description = "First ConfigTask {0} on node {1}".format(
                           model_item.name, node_item.hostname)
            kwargs = {"path": "/etc/story10575{0}.txt".format(model_item.name),
                      "ensure": "present",
                      "content": "This_is_a_story_10575_file"}
            task = self._config_task2(
                      node_item, model_item, description, kwargs,
                      "file10575{0}_task_id_".format(model_item.name))
            # if property, "multipleconfig" is true,
            # then an additional ConfigTask is generated
            if model_item.multipleconfig == 'true':
                description = "Second ConfigTask {0} on node {1}".format(
                              model_item.name, node_item.hostname)
                kwargs = {"provider": "yum",
                         "name": "{0}".format(model_item.packagename),
                         "ensure": "present"}
                task2 = self._config_task3(
                         node_item, model_item, description, kwargs,
                         "{0}10575_task_id_".format(model_item.packagename))
                description = "Third ConfigTask {0} on node {1}".format(
                              model_item.name, node_item.hostname)
            # Generate 2 callback tasks at item creation/update
            # One will be set as part of an Orderlist and the other
            # will not
            task_ = self._callback_task(model_item)
            task3 = self._mock_callback(model_item)

        # If item is in state "ForRemoval", and the property, deconfigure
        # is true, then plugin will generate a deconfigure ConfigTask and
        if model_item.is_for_removal() and model_item.deconfigure == 'true':
            description = self._config_task_description(
                node_item, model_item, deconfigure=True
            )
            kwargs = {"path": "/etc/story10575{0}.txt".format(
                      model_item.name),
                      "ensure": "absent"}
            task = self._config_task2(
                      node_item, model_item, description, kwargs,
                      "file10575{0}_task_id_".format(model_item.name)
            )
            # if property, "multipleconfig" is true,
            # another deconfigure task is created
            if model_item.multipleconfig == 'true':
                description = self._config_task_description(
                node_item, model_item, deconfigure=True
                )
                kwargs = {"provider": "yum",
                          "name": "{0}".format(model_item.packagename),
                          "ensure": "absent"}
                task2 = self._config_task3(
                          node_item, model_item, description,
                          kwargs, "{0}10575_task_id_".format(
                          model_item.packagename)
                )
            # ConfigTask that wil fail phase
            if model_item.failphase == 'true':
                description = self._config_task_description(
                node_item, model_item, deconfigure=True
                )
                kwargs = {"provider": "yum",
                          "name": "{0}".format(model_item.packagename),
                          "ensure": "present"}
                fail_phase = self._config_task3(
                          node_item, model_item, description,
                          kwargs, "{0}10575_failtask_id_".format(
                          model_item.packagename)
                )
            # Callback task that will fail the removal plan
            if model_item.failplan == 'true':
                fail_task = self._cb_fail_callback_task(model_item)
        # Callback task that will wait until a file is created
        # so that the puppet manifiests can be checked during the plan
            if model_item.wait == 'true':
                wait_task = self._cb_wait_while_check_manifests(model_item)

        # OrderedTaskList tasks allow a plugin to create a chain
        # of tasks where each task becomes a dependency of the previous one
        if task:
            ordered_tasks.append(task)
            if task2:
                ordered_tasks.append(task2)
            # Task 3 is a callback task that is in ordered task list
            if task3:
                ordered_tasks.append(task3)
        # This task is not part of the ordered list and has no
        # dependency on the other tasks generated by the plugin
        if task_:
            tasks.append(task_)
        if wait_task:
            wait_task.requires.add(task)
            tasks.append(wait_task)
        if fail_task:
            fail_task.requires.add(task)
            tasks.append(fail_task)
        if fail_phase:
            fail_phase.requires.add(task)
            tasks.append(fail_phase)
        if ordered_tasks:
            log.trace.debug("TASKS ORDERED LIST: {0}".format(ordered_tasks))
            tasks.append(OrderedTaskList(node_item, ordered_tasks))
        log.trace.debug("ALL TASKS: {0}".format(tasks))
        return tasks

    def create_configuration(self, plugin_api_context):
        """
        Plugin can provide tasks based on the model ...

        *Example CLI for this plugin:*

        .. code-block:: bash

        """
        tasks = []
        nodes = plugin_api_context.query("node") +\
            plugin_api_context.query("ms")

        for node in nodes:
            #for ms_ in plugin_api_context.query("ms"):
            if self._config_items(node, "story-10575a"):
                for config_10575a in self._config_items(node, "story-10575a"):
                    if config_10575a:
                        tasks.extend(self._generate_tasks(node, config_10575a))
        log.trace.debug("RETURNED TASKS: {0}".format(tasks))
        return tasks
