from litp.core.plugin import Plugin
from litp.core.execution_manager import ConfigTask, CallbackTask
from litp.core.future_property_value import FuturePropertyValue

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class Story5508Plugin(Plugin):

    def cb_do_something(self, callback_api, model_ref_id):
        for node in callback_api.query('node'):
            for item in node.query('story5508', is_initial=True):
                if item.item_id == model_ref_id:
                    item.ensure = 'present'

    def cb_do_something_else(self, callback_api, model_ref_id):
        for node in callback_api.query('node'):
            for item in node.query('story5508', is_initial=True):
                if item.item_id == model_ref_id:
                    item.ensure = 'absent'

    def cb_do_nothing(self, callback_api, model_ref_id):
        for node in callback_api.query('node'):
            for item in node.query('story5508', is_initial=True):
                if item.item_id == model_ref_id:
                    log.trace.debug('DO NOTHING: {0}'.format(item))

    def create_configuration(self, plugin_api_context):
        tasks = []
        for node in plugin_api_context.query('node'):
            for model_ref in node.query('story5508', is_initial=True):
                future_property_value = FuturePropertyValue(
                    model_ref,
                    'ensure'
                )
                if model_ref.name == 'story5508test01':
                    cbtask = CallbackTask(
                        model_ref,
                        'CallbackTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        self.cb_do_something,
                        model_ref.item_id
                    )
                    cftask = ConfigTask(
                        node,
                        model_ref,
                        'ConfigTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        'firewallchain',
                        'cf_{0}_{1}:filter:IPv4'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        ensure=future_property_value
                    )
                    cftask.requires.add(cbtask)
                    tasks.append(cbtask)
                    tasks.append(cftask)
                if model_ref.name == 'story5508test02':
                    cbtask = CallbackTask(
                        model_ref,
                        'CallbackTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        self.cb_do_something,
                        model_ref.item_id
                    )
                    cftask = ConfigTask(
                        node,
                        model_ref,
                        'ConfigTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        'firewallchain',
                        'cf_{0}_{1}:filter:IPv4'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        ensure=future_property_value
                    )
                    cbtask2 = CallbackTask(
                        model_ref,
                        'CallbackTask2():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        self.cb_do_something_else,
                        model_ref.item_id
                    )
                    cftask2 = ConfigTask(
                        node,
                        model_ref,
                        'ConfigTask2():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        'firewallchain',
                        'cf2_{0}_{1}:filter:IPv4'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        ensure=future_property_value
                    )
                    #cbtask3_1 = CallbackTask(
                    #    model_ref,
                    #    'CallbackTask3_1():{0}:{1}'.format(
                    #        model_ref.name,
                    #        node.hostname
                    #    ),
                    #    self.cb_do_something
                    #)
                    #cbtask3_2 = CallbackTask(
                    #    model_ref,
                    #    'CallbackTask3_2():{0}:{1}'.format(
                    #        model_ref.name,
                    #        node.hostname
                    #    ),
                    #    self.cb_do_something_else
                    #)
                    #cftask3 = ConfigTask(
                    #    node,
                    #    model_ref,
                    #    'ConfigTask3():{0}:{1}'.format(
                    #        model_ref.name,
                    #        node.hostname
                    #    ),
                    #    'firewallchain',
                    #    'cf3_{0}_{1}:filter:IPv4'.format(
                    #        model_ref.name,
                    #        node.hostname
                    #    ),
                    #    ensure=future_property_value
                    #)
                    cftask.requires.add(cbtask)
                    cbtask2.requires.add(cftask)
                    cftask2.requires.add(cbtask2)
                    #cbtask3_1.requires.add(cftask2)
                    #cbtask3_2.requires.add(cbtask3_1)
                    #cftask3.requires.add(cbtask3_2)
                    tasks.append(cbtask)
                    tasks.append(cftask)
                    tasks.append(cbtask2)
                    tasks.append(cftask2)
                    #tasks.append(cbtask3_1)
                    #tasks.append(cbtask3_2)
                    #tasks.append(cftask3)
                if model_ref.name == 'story5508test03':
                    cbtask = CallbackTask(
                        model_ref,
                        'CallbackTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        self.cb_do_nothing,
                        model_ref.item_id
                    )
                    cftask = ConfigTask(
                        node,
                        model_ref,
                        'ConfigTask():{0}:{1}'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        'firewallchain',
                        'cf_{0}_{1}:filter:IPv4'.format(
                            model_ref.name,
                            node.hostname
                        ),
                        ensure=future_property_value
                    )
                    cftask.requires.add(cbtask)
                    tasks.append(cbtask)
                    tasks.append(cftask)

        return tasks
