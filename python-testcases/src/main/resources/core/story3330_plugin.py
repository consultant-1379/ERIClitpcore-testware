from litp.core.plugin import Plugin
from litp.core.task import CallbackTask
from litp.core.rpc_commands import run_rpc_command
from litp.core.litp_logging import LitpLogger
from litp.core.execution_manager import CallbackExecutionException
log = LitpLogger()


class Story3330Plugin(Plugin):

    def create_configuration(self, plugin_api_context):
        tasks = []
        nodes = [node.hostname for node in plugin_api_context.query('node')]
        nodes.extend([
            node.hostname for node in plugin_api_context.query('ms')
            ]
        )

        for item in plugin_api_context.query('story3330', is_initial=True):
            # the positive case
            if item.name == 'test_01':
                tasks.append(
                    CallbackTask(
                        item, 'RPC task completes',
                        self.dummy_callback_success, nodes=nodes
                    )
                )
            # the negative case
            elif item.name == 'test_02':
                tasks.append(
                    CallbackTask(
                        item, 'RPC task fails',
                        self.dummy_callback_failure, nodes=nodes
                    )
                )
            elif item.name == 'test_03':
                tasks.append(
                    CallbackTask(
                        item, 'RPC task timeout',
                        self.dummy_callback_timeout, nodes=nodes
                    )
                )

            elif item.name == 'test_04':
                tasks.append(
                    CallbackTask(
                        item, 'RPC task invalid args',
                        self.dummy_callback_timeout, nodes=str(nodes)
                    )
                )

        return tasks

    def dummy_callback_success(self, plugin_api_context, nodes):
        log.trace.debug(plugin_api_context)
        log.trace.info(
            run_rpc_command(
                nodes, 'service', 'status', {'service': 'network'}
            )
        )

    def dummy_callback_failure(self, plugin_api_context, nodes):
        log.trace.debug(plugin_api_context)
        response = run_rpc_command(
            nodes, 'service', 'start', {'service': 'unknown'})
        for node in nodes:
            if response[node]['errors'] != '':
                log.trace.error(response)
                raise CallbackExecutionException

    def dummy_callback_timeout(self, plugin_api_context, nodes):
        log.trace.debug(plugin_api_context)
        nodes[:] = ['{0}timeout'.format(node) for node in nodes]
        response = run_rpc_command(
            nodes, 'service', 'status', {'service': 'network'})
        for node in nodes:
            if response[node]['errors'] != '':
                log.trace.error(response)
                raise CallbackExecutionException
