from litp.core.plugin import Plugin
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask
from litp.core.task import RemoteExecutionTask
from litp.core.task import OrderedTaskList


class Story1838Plugin(Plugin):
    """test plugin for LITPCDS-1838"""

    def get_callback_config_tasks(self, node, item, unique=True):
        """return callback and config tasks"""

        if not unique:
            return [
                        CallbackTask(
                            item, "CallbackTask() {0}".format(item.name),
                            self.cb_do_something
                        ),
                        ConfigTask(
                            node, item, "ConfigTask() {0}".format(item.name),
                            "notify", "cf_do_something_{0}_1".format(item.name)
                        )
                   ]
        else:
            return [
                        CallbackTask(
                            item, "CallbackTask() {0}".format(item.name),
                            self.cb_do_something
                        ),
                        ConfigTask(
                            node, item, "ConfigTask() {0}".format(item.name),
                            "notify", "cf_do_something_{0}".format(item.name)
                        )
                   ]

    def get_remote_execution_task(self, node, item):
        """return a remote execution task"""

        return [
                RemoteExecutionTask(
                    [node], item,
                    "RemoteExecutionTask() {0}".format(item.name), "service",
                    "status", service="network")
                ]

    def get_ordered_task_list(self, api, node, item):
        """return an ordered task list"""

        ms = api.query("ms")[0]
        tasks = self.get_callback_config_tasks(node, item, False)
        tasks.extend(self.get_remote_execution_task(node, item))
        return OrderedTaskList(ms, tasks)

    def get_cluster_tasks(self, api):
        """return software item tasks that hangs off a cluster model item"""

        cluster = [cluster for cluster in api.query("cluster")][0]

        for ref in cluster.query("story1838", is_initial=True):
            if ref.name == "test_10":
                return self.get_callback_config_tasks(cluster, ref)

        return []

    def get_lock_task(self, node, ms):
        """return lock task"""

        return  RemoteExecutionTask(
                    [node], ms, "Lock task {0}".format(node.hostname),
                    "lock_unlock", "lock"
                )

    def get_unlock_task(self, node, ms):
        """return unlock task"""

        return  RemoteExecutionTask(
                    [node], ms, "Unlock task {0}".format(node.hostname),
                    "lock_unlock", "unlock"
                )

    def create_configuration(self, api):
        """create configuration"""

        tasks = []
        nodes = []

        # query test item type
        items = [item for item in api.query("story1838")]

        # query all nodes
        nodes = [node for node in api.query("node")]

        # get tasks for each required test based on name property and item
        # state
        for item in items:
            if item.name == "test_10" and item.is_initial():
                tasks = self.get_cluster_tasks(api)
            elif item.name == "test_updated":
                if item.is_updated() or item.is_for_removal() or \
                        item.is_initial():
                    for node in nodes:
                        for ref in node.query("story1838"):
                            tasks.extend(
                                self.get_callback_config_tasks(node, ref)
                            )
            else:
                for node in nodes:
                    for ref in node.query("story1838"):
                        if item.name == "test_01":
                            if item.is_initial() or item.is_for_removal():
                                tasks.extend(
                                    self.get_callback_config_tasks(node, ref)
                                )
                        elif item.name == "test_08":
                            if item.is_initial():
                                tasks.append(
                                    self.get_ordered_task_list(api, node, ref)
                                )
                        elif item.name == "test_09":
                            if item.is_initial():
                                tasks.extend(
                                    self.get_remote_execution_task(node, ref)
                                )
                        elif item.name == "test_11":
                            if item.is_initial():
                                tasks.extend(
                                    self.get_callback_config_tasks(node, ref)
                                )
                                tasks.extend(
                                    self.get_remote_execution_task(node, ref)
                                )
                                tasks.append(
                                    self.get_ordered_task_list(api, node, ref)
                                )
                        else:
                            if item.is_initial():
                                tasks.extend(
                                    self.get_callback_config_tasks(node, ref)
                                )

        return tasks

    def create_lock_tasks(self, api, node):
        """create lock/unlock tasks"""

        # query test item type
        items = [item for item in api.query("story1838")]

        # query /ms
        ms = api.query("ms")[0]

        # generate lock/unlocak tasks for each test based on property name and
        # item state
        for item in items:
            if item.name == "test_01" or item.name == "test_updated":
                if item.is_initial() or item.is_for_removal() or \
                        item.is_updated():
                    return (
                            self.get_lock_task(node, ms),
                            self.get_unlock_task(node, ms)
                            )
            elif item.name == "test_03" and item.is_initial():
                pass
            elif item.name == "test_04" and item.is_initial():
                return (
                        self.get_lock_task(node, ms),
                        )
            elif item.name == "test_05" and item.is_initial():
                return (
                        self.get_unlock_task(node, ms),
                        )
            elif item.name == "test_07" and item.is_initial():
                hamngr = [
                    cluster.ha_manager for cluster in api.query("cluster")
                ]
                if hamngr == "bob":
                    return (
                            self.get_lock_task(node, ms),
                            self.get_unlock_task(node, ms)
                            )
            else:
                if item.is_initial():
                    return (
                            self.get_lock_task(node, ms),
                            self.get_unlock_task(node, ms)
                        )

        return ()

    def cb_do_something(self, api):
        """a callback method that does nothing"""

        pass
