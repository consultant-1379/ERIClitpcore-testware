from litp.core.plugin import Plugin
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask
from litp.core.task import RemoteExecutionTask


class Story1838SecondPlugin(Plugin):
    """test plugin for LITPCDS-1838"""

    def get_callback_config_tasks(self, node, item):
        """return callback and config tasks"""

        return [
                CallbackTask(item, "CallbackTask() {0}".format(item.name),
                    self.cb_do_something),
                ConfigTask(node, item, "ConfigTask() {0}".format(item.name),
                    "notify", "cf_do_something")
                ]

    def get_lock_task(self, node, ms):
        """return lock task"""

        return  RemoteExecutionTask(
                    [node], ms, "Lock task {0}".format(node.item_id),
                    "lock_unlock", "lock"
                )

    def get_unlock_task(self, node, ms):
        """return unlock task"""

        return  RemoteExecutionTask(
                    [node], ms, "Unlock task {0}".format(node.item_id),
                    "lock_unlock", "unlock"
                )

    def create_configuration(self, api):
        """create configuration"""

        tasks = []

        # query test item type
        items = [item for item in api.query("story1838", is_initial=True)]

        # if test is test_06 and property second_plugin is true, generate the
        # configtask and callbacktasks
        for item in items:
            if item.second_plugin == "true":
                if item.name == "test_06":
                    nodes = [node for node in api.query("node")]
                    for node in nodes:
                        tasks.extend(
                            self.get_callback_config_tasks(node, item)
                        )

        return tasks

    def create_lock_tasks(self, api, node):
        """create lock/unlock tasks"""

        # query test item type
        items = [item for item in api.query("story1838", is_initial=True)]

        # if test is test_06 and property second_plugin is true, generate the
        # lock/unlock tasks
        for item in items:
            if item.second_plugin == "true":
                if item.name == "test_06":
                    ms = api.query("ms")[0]
                    return (
                            self.get_lock_task(node, ms),
                            self.get_unlock_task(node, ms)
                        )

        return ()

    def cb_do_something(self, api):
        """a callback method that does nothing"""

        pass
