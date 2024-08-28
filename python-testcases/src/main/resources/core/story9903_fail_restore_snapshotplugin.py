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
from litp.core.task import CallbackTask
from litp.core.snapshot_model_api import SnapshotModelApi

log = LitpLogger()


class Story9903FailRestoreSnapshotPlugin(Plugin):
    """
    LITP story9903_fail_restore_snapshot plugin
    """

    def _fail(self, api):  # pylint: disable=W0613
        raise CallbackExecutionException("Failed deliberately")

    def create_snapshot_plan(self, plugin_api_context):

        # raises either NoSnapshotItemError or NoMatchingActionError
        action = plugin_api_context.snapshot_action()

        found = self._snapshot_model_exposed(plugin_api_context)
        if action == 'create':
            if found:
                log.trace.info('Story9903 - create_snapshot - '
                               '[ERROR] snapshot model found')
            else:
                log.trace.info('Story9903 - create_snapshot - '
                               '[OK] snapshot model not found')

        elif action == 'remove':
            if found:
                log.trace.info('Story9903 - remove_snapshot - '
                               '[OK] snapshot model found')
            else:
                log.trace.info('Story9903 - remove_snapshot - '
                               '[ERROR] snapshot model not found')

        elif action == 'restore':
            if found:
                log.trace.info('Story9903 - restore_snapshot - '
                               '[OK] snapshot model found')
            else:
                log.trace.info('Story9903 - restore_snapshot - '
                               '[ERROR] snapshot model not found')

            # Running the full restore_snapshot is not suitable for core KGB,
            # therefore the plan is deliberately failed at phase 1
            node = plugin_api_context.query('node')[0]
            return [CallbackTask(
                        node,
                        'Should fail',
                        self._fail,
                        tag_name=restore_snapshot_tags.VALIDATION_TAG
                    )]
        return []

    def _snapshot_model_exposed(self, plugin_api_context):
        # Try to get snapshot model from plugin_api_context and then verify
        # that it can be queried
        snapshot_model = plugin_api_context.snapshot_model()

        if snapshot_model:
            if not isinstance(snapshot_model, SnapshotModelApi):
                raise TypeError("snapshot_model is not an instance \
                        of SnapshotModelApi")

            # Query snapshot model.
            # If snapshot_model couldn't be queried raises IndexError.
            nodes = snapshot_model.query('node')
            for node in nodes:
                fs = node.query('file-system-base')[0]
                if fs:
                    return True
        return False
