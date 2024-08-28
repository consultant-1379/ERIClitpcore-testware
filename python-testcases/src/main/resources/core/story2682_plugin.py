from litp.core.plugin import Plugin
from litp.core.task import CallbackTask, ConfigTask

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story2682Plugin(Plugin):
    def do_trivial(self, api, item):
        log.trace.debug('{0}: {1}'.format(item, api))

    def create_configuration(self, api):
        tasks = []
        for item in api.query("story2682"):
            if item.is_initial() or item.is_updated():
                if item.callback_task_true == 'true':
                    tasks.extend([CallbackTask(item, "Apply callback item",
                                              self.do_trivial, item.name)])
                if item.config_task_true == 'true':
                    for node in api.query("node"):
                        for lnk in node.query("story2682"):
                            if lnk.config_task_true == 'true':
                                tasks.extend([ConfigTask(node, lnk,
                                                        "Apply config item",
                                                        'notify', item.name)])
            elif item.is_for_removal():
                if item.callback_task_true == 'true':
                    tasks.extend([CallbackTask(item, "Remove callback item",
                                               self.do_trivial, item.name)])
                if item.config_task_true == 'true':
                    for node in api.query("node"):
                        for lnk in node.query("story2682"):
                            if lnk.config_task_true == 'true':
                                tasks.extend([ConfigTask(node, lnk,
                                                        "Remove config item",
                                                        'notify', item.name)])
        return tasks
