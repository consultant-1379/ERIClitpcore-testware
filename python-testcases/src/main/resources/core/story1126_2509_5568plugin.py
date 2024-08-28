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

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story1126_2509_5568Plugin(Plugin):

    def dummy(self, callback_api):
        pass

    def create_configuration(self, api):
        ms = api.query("ms")[0]
        cfgs = ms.query('migrations-node-config', is_initial=True)
        tasks = [None] * 4
        for cfg in cfgs:
            return [CallbackTask(cfg, "Dummy task (single)", self.dummy)]

        # remove nonexistent
        tasks = [t for t in tasks if t]
        # add dependency info to ensure order
        for i in range(0, len(tasks)):
            if i - 1 >= 0:
                tasks[i].requires.add(tasks[i - 1])
        return tasks
