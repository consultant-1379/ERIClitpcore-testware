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


class Story200916Plugin(Plugin):
    """
    LITP story200916 plugin
    """

    def validate_model(self, plugin_api_context):
        """
        No validation performed - dummy plugin
        """
        return []

    def dummy(self, callback_api):
        pass

    def create_configuration(self, plugin_api_context):
        """
        Plugin can provide tasks based on the model ...

        """
        tasks = []
        cfgs = plugin_api_context.query('torf-200916-item-type',
                                        is_applied=False)
        for c in cfgs:
            tasks.append(CallbackTask(c, "Dummy task", self.dummy))
        return tasks
