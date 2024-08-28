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
from litp.core.task import CallbackTask
from litp.core.execution_manager import CallbackExecutionException
from time import sleep
import os

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story6864Plugin(Plugin):
    # pylint: disable=W0613
    def callback(self, callback_api, item_id):
        while True:
            sleep(1)
            if not os.path.isfile("/tmp/{0}".format(item_id)):
                break

    def dummy1(self, callback_api):
        pass

    def dummy2(self, callback_api):
        pass

    def fail(self, callback_api):
        raise CallbackExecutionException("callback task failed")

    def create_configuration(self, api):
        ms = api.query("ms")[0]
        cfgs = ms.query('story6864-node-config', is_initial=True)
        tasks = [None] * 4
        for cfg in cfgs:
            if cfg.item_id.endswith("_only"):
                return [CallbackTask(cfg, "Dummy task (single)", self.dummy1)]
            elif cfg.item_id.endswith("_before"):
                tasks[0] = CallbackTask(cfg, "Dummy task (before polling)",
                                        self.dummy1)
            elif cfg.item_id.endswith("_lock"):
                tasks[1] = CallbackTask(
                    cfg, "Polling task for /tmp/{0}".format(cfg.item_id),
                    self.callback, cfg.item_id)
            elif cfg.item_id.endswith("_after"):
                tasks[2] = CallbackTask(cfg, "Dummy task (after polling)",
                                        self.dummy2)
            elif cfg.item_id.endswith("_fail"):
                tasks[3] = CallbackTask(cfg, "Dummy task (fail)", self.fail)

        # remove nonexistent
        tasks = [t for t in tasks if t]
        # add dependency info to ensure order
        for i in range(0, len(tasks)):
            if i - 1 >= 0:
                tasks[i].requires.add(tasks[i - 1])
        return tasks
