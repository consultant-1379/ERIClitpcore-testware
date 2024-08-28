from litp.core.plugin import Plugin
from litp.core.task import OrderedTaskList
from litp.core.task import CallbackTask
from litp.core.task import RemoteExecutionTask

#
# THIS FILE IS PROVIDED AS A REFERENCE/EXAMPLE TO SHOW WHAT AN RPCTask() PLUGIN
# IS SUPPOSED TO DO
#


class mockpackagerpcPlugin(Plugin):

    def callback_do_nothing(self):

        pass

    def execute_valid_remote_procedure_call(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'status', service='httpd')])

        return tasks

    def execute_invalid_remote_procedure_call_agent_unavailable(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'servce', 'status', service='httpd')])

        return tasks

    def execute_invalid_remote_procedure_call_action_unavailable(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'servce', 'sttus', service='httpd')])

        return tasks

    def execute_invalid_remote_procedure_call_agent_fails_exec(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'start', service='unknown')])

        return tasks

    def execute_invalid_remote_procedure_call_invalid_kwarguments(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'start', servce='unknown')])

        return tasks

    def execute_invalid_remote_procedure_call_invalid_arguments(self, api):

        tasks = list()

        management_servers = api.query('ms')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask([ms], package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'start', 'unknown')])

        return tasks

    def execute_invalid_remote_procedure_call_on_nodes(self, api):

        tasks = list()

        management_servers = api.query('ms')
        managed_nodes = api.query('node')
        managed_nodes.insert(0, management_servers[0])

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask(managed_nodes, package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'start', service='httpd')])

        return tasks

    def execute_valid_remote_procedure_call_on_nodes(self, api):

        tasks = list()

        management_servers = api.query('ms')
        managed_nodes = api.query('node')

        for ms in management_servers:
            for package in ms.query('mock-package'):
                if package.is_initial():
                    tasks.extend([
                        RemoteExecutionTask(managed_nodes, package,
                            'RPCTask for {0}:{1}'.format(package.name,
                                                         ms.hostname),
                            'service', 'status', service='network')])

        return tasks

    def ordered_remote_procedure_task(self, api):

        tasks = list()

        nodes = api.query('ms')
        nodes.extend(api.query('node'))

        for node in sorted(nodes, key=lambda node: node.hostname.lower()):
            for package in sorted(node.query('mock-package'),
                                key=lambda package: package.name.lower()):
                if package.is_initial():
                    tasks.append(
                        OrderedTaskList(package,
                            [
                            CallbackTask(
                                package, 'callback_do_nothing {0}:{1}'.format(
                                                package.name, node.hostname),
                                self.callback_do_nothing),
                            RemoteExecutionTask([node], package,
                                'RPCTask for {0}:{1}'.format(package.name,
                                                             node.hostname),
                                'service', 'status', service='network')
                            ]))

        return tasks

    def create_configuration(self, plugin_api_context):

        tasks = list()

        packages = plugin_api_context.query('mock-package')

        packages[:] = [package for package in packages if package.is_initial()]

        for package in packages:
            if package.version == '1.0':
                tasks.extend(self.execute_valid_remote_procedure_call(
                                                        plugin_api_context))

            if package.version == '2.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_agent_unavailable(
                                                        plugin_api_context))

            if package.version == '3.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_agent_fails_exec(
                                                        plugin_api_context))

            if package.version == '4.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_action_unavailable(
                                                        plugin_api_context))

            if package.version == '5.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_invalid_kwarguments(
                                                        plugin_api_context))

            if package.version == '6.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_invalid_arguments(
                                                        plugin_api_context))

            if package.version == '7.0':
                return self.ordered_remote_procedure_task(plugin_api_context)

            if package.version == '8.0':
                tasks.extend(self.execute_valid_remote_procedure_call(
                                                        plugin_api_context))

            if package.version == '9.0':
                tasks.extend(
                self.execute_invalid_remote_procedure_call_on_nodes(
                                                        plugin_api_context))

            if package.version == '10.0':
                tasks.extend(
                self.execute_valid_remote_procedure_call_on_nodes(
                                                        plugin_api_context))

        return tasks
