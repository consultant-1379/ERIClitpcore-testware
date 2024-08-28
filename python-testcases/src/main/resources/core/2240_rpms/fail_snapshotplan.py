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
from litp.core.litp_logging import LitpLogger
from litp.core.exceptions import CallbackExecutionException
from litp.plan_types.restore_snapshot import restore_snapshot_tags
from litp.plan_types.remove_snapshot import remove_snapshot_tags
from litp.plan_types.create_snapshot import create_snapshot_tags
from litp.core.task import CallbackTask

log = LitpLogger()


class FailSnapshotPlan(Plugin):
    """
    LITP fails all snapshot plans
    """

    def _fail(self, api):  # pylint: disable=W0613
        raise CallbackExecutionException("Failed deliberately")

    def create_snapshot_plan(self, plugin_api_context):

        action = plugin_api_context.snapshot_action()
        node = plugin_api_context.query('node')[0]
        if action == 'create':
            # therefore the plan is deliberately failed at phase 1
            return [CallbackTask(
                        node,
                        'Should fail',
                        self._fail,
                        tag_name=create_snapshot_tags.VALIDATION_TAG
                    )]

        if action == 'remove':
            # therefore the plan is deliberately failed at phase 1
            return [CallbackTask(
                        node,
                        'Should fail',
                        self._fail,
                        tag_name=remove_snapshot_tags.VALIDATION_TAG
                    )]
        elif action == 'restore':
            return [CallbackTask(
                        node,
                        'Should fail',
                        self._fail,
                        tag_name=restore_snapshot_tags.VALIDATION_TAG
                    )]
