from litp.core.plugin import Plugin
from litp.core.task import CallbackTask


class Story5649Plugin(Plugin):
    """test plugin for LITPCDS-5649"""

    def _get_counts(self, items):
        items_count = len(items)
        initial_count = 0
        updated_count = 0
        applied_count = 0
        for item in items:
            if item.is_initial():
                initial_count += 1
            elif item.is_updated():
                updated_count += 1
            elif item.is_applied():
                applied_count += 1
        return items_count, initial_count, updated_count, applied_count

    def _create_cfg_test_01_neg(self, items):
        total_count, initial_count, updated_count, applied_count \
            = self._get_counts(items)

        if total_count == initial_count:
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success)
            task1.model_items = set(items)
            return [task1]

        if updated_count and applied_count and initial_count:
            # unsuccessful task
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_fail)
            task1.model_items = set(items)
            return [task1]

        raise RuntimeError("Test case messed up its setup. "
                           "Expected all initial or at least one of initial, "
                           "updated and applied.")

    def _create_cfg_test_02_pos(self, items):
        total_count, initial_count, updated_count, applied_count \
            = self._get_counts(items)
        if total_count == initial_count or \
                (updated_count and applied_count and initial_count):
            # successful task
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success)
            task1.model_items = set(items)
            return [task1]
        raise RuntimeError("Test case messed up its setup. "
                           "Expected all initial or at least one of initial, "
                           "updated and applied.")

    def _create_cfg_test_03_neg(self, items):
        total_count, initial_count, _, _ = self._get_counts(items)
        if total_count == initial_count:
            # successful task
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_fail)
            task2 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success)
            return [task1, task2]

        raise RuntimeError("Test case messed up its setup. "
                           "Expected all initial.")

    def _create_cfg_test_04_pos(self, items):
        total_count, initial_count, _, _ = self._get_counts(items)
        if total_count == initial_count:
            # successful task
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success)
            task2 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success2)
            return [task1, task2]

        raise RuntimeError("Test case messed up its setup. "
                           "Expected all initial.")

    def _create_cfg_test_05_pos(self, items):
        total_count, initial_count, _, _ = self._get_counts(items)
        if total_count == initial_count:
            task1 = CallbackTask(items[0],
                                 "Callback {0}".format(items[0].name),
                                 self.cb_success)
            task2 = CallbackTask(items[-1],
                                 "Callback {0}".format(items[-1].name),
                                 self.cb_fail)
            # allow items 1, 2 to be successful
            task1.model_items = set(items)
            task2.model_items = set([items[-2]])
            return [task1, task2]

        raise RuntimeError("Test case messed up its setup. "
                           "Expected all initial.")

    def create_configuration(self, api):
        items = api.query("story5649")
        items.sort(key=lambda x: x.name)
        if all([item.is_for_removal() for item in items]):
            return []

        if all([item.name.startswith("test_01") for item in items]):
            if len(items) < 2:
                raise RuntimeError("Test case messed up its setup. "
                                   "Expected at least 2 items")
            return self._create_cfg_test_01_neg(items)
        if all([item.name.startswith("test_02") for item in items]):
            if len(items) < 2:
                raise RuntimeError("Test case messed up its setup. "
                                   "Expected at least 2 items")
            return self._create_cfg_test_02_pos(items)
        if all([item.name.startswith("test_03") for item in items]):
            return self._create_cfg_test_03_neg(items)
        if all([item.name.startswith("test_04") for item in items]):
            return self._create_cfg_test_04_pos(items)
        if all([item.name.startswith("test_05") for item in items]):
            if len(items) < 4:
                raise RuntimeError("Test case messed up its setup. "
                                   "Expected at least 4 items")
            return self._create_cfg_test_05_pos(items)

        raise RuntimeError("Test case mixed up model setup. "
                           "At least 1, 2 or 4  model items must be present, "
                           "depending on TC. "
                           "Model item's name must start with "
                           r"test_\{ZERO_PADDED_TC_NUMBER\}")

    def cb_success(self, api):
        pass

    def cb_success2(self, api):
        pass

    def cb_fail(self, api):
        raise
