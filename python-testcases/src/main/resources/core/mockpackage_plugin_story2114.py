from litp.core.plugin import Plugin
from litp.core.task import OrderedTaskList
from litp.core.task import ConfigTask
from litp.core.task import CallbackTask

from litp.core.litp_logging import LitpLogger
log = LitpLogger()


class MockPackagePlugin(Plugin):

    def _mock_callback(self, plugin_api_context):
        log.trace.debug(
        'DUMMYPLUGIN_STORY2114: called _mock_callback() method \'{0}\''.format(
                                                        plugin_api_context))

    def _mock_raise_exception(self, plugin_api_context):
        log.trace.debug(
        'DUMMYPLUGIN_STORY2114: called _mock_raise_exception() method '\
        '\'{0}\''.format(plugin_api_context))
        raise Exception('DummyPlugin failure')

    def _ordered_task_list_test_01_04(self, plugin_api_context, pkgs):

        tasks = list()

        nodes = plugin_api_context.query('node') + \
               plugin_api_context.query('ms')

        for node in nodes:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: found node {0}'.format(node.hostname))

            mock_pkgs = [mock_pkg for mock_pkg in node.query('mock-package') \
                        if mock_pkg.get_source() in pkgs and \
                        mock_pkg.is_initial()]

            if not mock_pkgs:
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: no \'mock-packages\' found for node '\
                '{0}'.format(node.hostname))
                continue

            ordered_tasks = list()
            for mock_pkg in sorted(mock_pkgs,
                                key=lambda mock_pkg: mock_pkg.name.lower()):
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: creating ConfigTask() for node {0} '\
                'package {1}'.format(node.hostname, mock_pkg.name))
                ordered_tasks.append(ConfigTask(node, mock_pkg,
                        'task package {0}'.format(mock_pkg.name), 'file',
                        "/tmp/second_%s" % mock_pkg.name,
                        path="/tmp/%s" % mock_pkg.name, content=mock_pkg.name))
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: added ConfigTask() to Ordered'\
                'TaskList()')

            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: creating CallbackTask() for node {0} '\
            'package {1}'.format(node.hostname, mock_pkg.name))
            ordered_tasks.append(CallbackTask(node,
                                'callback_mock_callback', self._mock_callback))
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: added CallbackTask() to OrderedTaskList()')

            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: creating CallbackTask() for node {0} '\
            'package {1}'.format(node.hostname, mock_pkg.name))
            ordered_tasks.append(CallbackTask(node,
                        'callback_raise_exception_callback',
                        self._mock_raise_exception))
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: added CallbackTask() to OrderedTaskList()')

            tasks.append(OrderedTaskList(node, ordered_tasks))

        log.trace.debug(
        'DUMMYPLUGIN_STORY2114: all tasks to be run: {0}'.format(tasks))

        return tasks

    def _ordered_task_list_test_02(self, plugin_api_context, pkgs):

        tasks = list()

        nodes = plugin_api_context.query('node') + \
               plugin_api_context.query('ms')

        for node in nodes:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: found node {0}'.format(node.hostname))

            mock_pkgs = [mock_pkg for mock_pkg in node.query('mock-package') \
                        if mock_pkg.get_source() in pkgs]

            if not mock_pkgs:
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: no \'mock-packages\' found for node '\
                '{0}'.format(node.hostname))
                continue

            for mock_pkg in mock_pkgs:
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: creating ConfigTask() for node {0} '\
                'package {1}'.format(node.hostname, mock_pkg.name))
                tasks.append(ConfigTask(node, mock_pkg,
                        'task package {0}'.format(mock_pkg.name), 'file',
                        "/tmp/second_%s" % mock_pkg.name,
                        path="/tmp/%s" % mock_pkg.name, content=mock_pkg.name))
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: added ConfigTask() to tasks list')

            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: creating CallbackTask() for node {0} '\
            'package {1}'.format(node.hostname, mock_pkg.name))
            tasks.append(CallbackTask(node,
                                'callback_mock_callback', self._mock_callback))
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: added CallbackTask() to tasks list')

            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: creating CallbackTask() for node {0} '\
            'package {1}'.format(node.hostname, mock_pkg.name))
            tasks.append(CallbackTask(node,
                        'callback_raise_exception_callback',
                        self._mock_raise_exception))
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: added CallbackTask() to tasks list()')

            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: creating CallbackTask() for node {0} '\
            'package {1}'.format(node.hostname, mock_pkg.name))
            tasks.append(CallbackTask(node,
                                'callback_mock_callback', self._mock_callback))
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: added CallbackTask() to tasks list')

        log.trace.debug(
        'DUMMYPLUGIN_STORY2114: all tasks to be run: {0}'.format(tasks))

        return tasks

    def _ordered_task_list_test_03(self, plugin_api_context, pkgs):

        tasks = list()

        nodes = plugin_api_context.query('node') + \
               plugin_api_context.query('ms')

        for node in nodes:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: found node {0}'.format(node.hostname))

            mock_pkgs = [mock_pkg for mock_pkg in node.query('mock-package') \
                        if mock_pkg.get_source() in pkgs]

            if not mock_pkgs:
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: no \'mock-packages\' found for node '\
                '{0}'.format(node.hostname))
                continue

            ordered_tasks = list()
            for mock_pkg in sorted(mock_pkgs,
                                key=lambda mock_pkg: mock_pkg.name.lower()):
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: creating ConfigTask() for node {0} '\
                'using model item {1}'.format(node.hostname, node.item_id))
                ordered_tasks.append(ConfigTask(node, node,
                            'node {0} task first'.format(node.hostname),
                            'file', "/tmp/first_%s" % mock_pkg.name,
                            path="/tmp/%s" % mock_pkg.name,
                            content=mock_pkg.name))
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: added ConfigTask() to Ordered'\
                'TaskList()')

                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: creating ConfigTask() for node {0} '\
                'using model item {1}'.format(node.hostname, mock_pkg.item_id))
                ordered_tasks.append(ConfigTask(node, mock_pkg,
                        'package {0} task second'.format(mock_pkg.name),
                        'file', "/tmp/second_%s" % mock_pkg.name,
                        path="/tmp/%s" % mock_pkg.name,
                            content=mock_pkg.name))
                log.trace.debug(
                'DUMMYPLUGIN_STORY2114: added ConfigTask() to Ordered'\
                'TaskList()')

            tasks.append(OrderedTaskList(node, ordered_tasks))

        log.trace.debug(
        'DUMMYPLUGIN_STORY2114: all tasks to be run: {0}'.format(tasks))

        return tasks

    def create_configuration(self, plugin_api_context):

        mock_pkgs_t01 = [mock_pkg for mock_pkg in \
                        plugin_api_context.query('mock-package') if \
                        mock_pkg.is_initial() and mock_pkg.version == '1']

        if mock_pkgs_t01:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: running with test_p_01')
            return self._ordered_task_list_test_01_04(
                            plugin_api_context, mock_pkgs_t01)

        mock_pkgs_t02 = [mock_pkg for mock_pkg in \
                        plugin_api_context.query('mock-package') if \
                        mock_pkg.is_initial() and mock_pkg.version == '2']

        if mock_pkgs_t02:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: running with test_p_02')
            return self._ordered_task_list_test_02(
                            plugin_api_context, mock_pkgs_t02)

        mock_pkgs_t03 = [mock_pkg for mock_pkg in \
                        plugin_api_context.query('mock-package') if \
                        mock_pkg.is_initial() and mock_pkg.version == '3']

        if mock_pkgs_t03:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: running with test_p_03')
            return self._ordered_task_list_test_03(
                            plugin_api_context, mock_pkgs_t03)

        mock_pkgs_t04 = [mock_pkg for mock_pkg in \
                        plugin_api_context.query('mock-package') if \
                        mock_pkg.is_initial() and mock_pkg.version == '4']

        if mock_pkgs_t04:
            log.trace.debug(
            'DUMMYPLUGIN_STORY2114: running with test_p_04')
            return self._ordered_task_list_test_01_04(
                            plugin_api_context, mock_pkgs_t04)

        return []
