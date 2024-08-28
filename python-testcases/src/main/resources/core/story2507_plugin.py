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


class Story2507Plugin(Plugin):
    # pylint: disable=W0613
    def callback(self, callback_api, item_id):
        while True:
            sleep(1)
            if not os.path.isfile("/tmp/{0}".format(item_id)):
                break

    def dummy(self, callback_api):
        pass

    def fail(self, callback_api):
        raise CallbackExecutionException("callback task failed")

    def create_configuration(self, api):
        ms = api.query("ms")[0]
        cfgs = ms.query('story2507-software-item', is_initial=True)
        for cfg in cfgs:
            if cfg.item_id.endswith("_lock"):
                return [CallbackTask(
                    cfg, "Polling task for /tmp/{0}".format(cfg.item_id),
                    self.callback, cfg.item_id)]
        for cfg in cfgs:
            return [CallbackTask(cfg, "Dummy task", self.dummy)]
        return []
