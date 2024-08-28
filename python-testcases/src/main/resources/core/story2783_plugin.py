from litp.core.plugin import Plugin
from litp.core.task import CallbackTask, OrderedTaskList
import random

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story2783Plugin(Plugin):
    def _get_random_value(self):
        self.used_vals = self.used_vals or []
        while True:
            rand = repr(random.random())
            if rand not in self.used_vals:
                self.used_vals.append(rand)
                return rand

    def callback(self, api, item_name):
        for item in api.query("story2783", name=item_name):
            if item_name == 'test_01':
                item.rest_only = self.get_random_value()
            if item_name in ['test_02', 'test_03', 'test_04', 'test_05',
                             'test_06', 'test_07', 'test_14', 'test_15']:
                item.plugin_only = self.get_random_value()
                if item_name == 'test_15':
                    item.plugin_only = self.get_random_value()
            if item_name in ['test_08', 'test_09', 'test_10', 'test_11',
                             'test_12', 'test_13']:
                item.both = self.get_random_value()
            if item_name == 'test_17':
                item.view = self.get_random_value()

    def callback2(self, api, item_name):
        for item in api.query("story2783", name=item_name):
            item.plugin_only = self.get_random_value()

    def failure(self, api, item_name):
        for item in api.query('story2783', name=item_name):
            item.none = self.get_random_value()

    def create_configuration(self, api):
        task1 = None
        task2 = None
        tasks = []
        for item in api.query("story2783"):
            if item.is_initial() or item.is_updated():
                if 'test_15' in item.name:
                    if item.name == 'test_15':
                        task1 = CallbackTask(
                            item, 'task 01: {0}'.format(item.name),
                            self.callback, item.name
                        )
                        task2 = CallbackTask(
                            item, 'task 02: {0}'.format(item.name),
                            self.callback2, item.name
                        )
                    if task1 and task2:
                        tasks.append(OrderedTaskList(item, [task1, task2]))
                elif item.name == 'test_16':
                    tasks.extend([CallbackTask(item, '', self.failure,
                                                                item.name)])
                else:
                    tasks.extend([CallbackTask(item, "", self.callback,
                                                                item.name)])

        return tasks
