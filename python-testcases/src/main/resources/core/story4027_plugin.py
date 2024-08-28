from litp.core.plugin import Plugin
from litp.core.task import CallbackTask

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story4027Plugin(Plugin):

    def cb_raise_exception(self, callback_api, item_name):
        if item_name == "test_01" or item_name == "test_02":
            for node in callback_api.query("node"):
                for item in node.query("story4027", name=item_name):
                    item.updatable = "false"
                for item in node.query("story4027-items", name=item_name):
                    item.updatable = "false"
        elif item_name == "test_03":
            for item in callback_api.query("story4027", name=item_name):
                item.updatable = "false"
            for item in callback_api.query("story4027-items", name=item_name):
                item.updatable = "false"

    def create_configuration(self, plugin_api_context):
        tasks = []
        exclude = []

        for node in plugin_api_context.query("node"):
            for test_collection in node.query(
                                    "story4027-items", is_initial=True):
                for test_item in test_collection.query("story4027"):
                    exclude.append(test_item)
                    tasks.append(
                        CallbackTask(
                            test_item,
                            "CallbackTask(): {0}".format(test_item.name),
                            self.cb_raise_exception, test_item.name
                        )
                    )
                tasks.append(
                    CallbackTask(
                        test_collection,
                        "CallbackTask(): {0}".format(test_collection.name),
                        self.cb_raise_exception, test_collection.name
                    )
                )
            for test_item in node.query("story4027", is_initial=True):
                if test_item not in exclude:
                    tasks.append(
                        CallbackTask(
                            test_item,
                            "CallbackTask(): {0}".format(test_item.name),
                            self.cb_raise_exception, test_item.name
                        )
                    )

        return tasks
