'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2013
@author:    Ares
@summary:   Integration test for ___
            Agile:
                Epic: N/A
                Story: LITPCDS-1575
                Sub-Task: LITPCDS-3093, LITPCDS-3088, LITPCDS-3089
'''

import os
import test_constants as const
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils


class Story1575(GenericTest):
    """
    LITPCDS-1575: As a LITP plugin developer I want to define a remote
                  execution task type that can kick off an action on a set of
                  managed nodes so that I can trigger non configuration actions
                  on managed nodes
    """

    def setUp(self):
        """
        Description:
            setUp() test method runs before every test
        """

        # call super class setup
        super(Story1575, self).setUp()

        # get cluster information
        self.management_node = self.get_management_node_filename()

        self.managed_nodes = self.get_managed_node_filenames()

        # setup required items for the test
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()

        self.pkg_urls = (
                        '/mock_story_1575_01',
                        '/mock_story_1575_02',
                        )
        self.plugin_type = 'mock-package'
        self.properties = 'name=\'{0}\' version=\'{1}\''
        self.pkg_names = (
                        'pkg_z_01',
                        'pkg_C_02',
                        )

        self.test_plugins = (
        'ERIClitpmockpackageapi.rpm',
        'ERIClitpmockpackagerpc.rpm')

    def tearDown(self):
        """
        Description:
            tearDown() test method runs after every test
        """

        # call super class teardown
        super(Story1575, self).tearDown()

    def _is_plugin_installed(self, plugin):
        """
        Desrcription:
            Check if the required dummy plugins, for the test to run, are
            already installed from a previous test run
        """

        # check if the fiven plugin rpm is installed or not

        _, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.check_pkg_installed([plugin]))
        self.assertEqual([], stderr)

        if rcode == 0:
            return True

        return False

    def _check_installed_plugins(self):
        """
        Description:
            Check which, if any, dummy plugins are installed and get the list
            of those which aren't but are required
        """

        plugins_req_install = list()

        # for each plugin rpm in tuple test plugins, check if the rpm is
        # already installed and if not, mark it for installation

        for d_plugin in self.test_plugins:
            if not self._is_plugin_installed(d_plugin.split('.rpm')[0]):
                plugins_req_install.append(d_plugin)

        return plugins_req_install

    def _install_rpms(self):
        """
        Description:
        Method that installs plugins and extensions
        if they are not already installed.
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.management_node, self.rhc.check_pkg_installed(
                self.test_plugins), su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            plugin_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'plugins'))
            local_rpm_paths = []

            for plugin in self.test_plugins:
                local_rpm_paths.append("{0}/{1}".format(plugin_dir, plugin))

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths))

    def _check_plugin_is_registered(self):
        """
        Description:
            Check the plugins required for the test run are registered with the
            litpd service
        """

        # check mockpackage_extension and mockpackagerpc are registered with
        # the litpd service

        stdout, stderr, rcode = self.run_command(self.management_node,
                            self.rhc.get_grep_file_cmd(
                                    const.GEN_SYSTEM_LOG_PATH, [
                                    'INFO: Added ModelExtension: \\"mockpac'\
                                    'kage\\"',
                                    'INFO: Added Plugin: \\"mockpackagerpc\\"']
                            ),
                            su_root=True
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def _execute_test(self, node_url, package_url, package_name, version):
        """
        Description:
            Execute a set of steps common to all tests
        """

        # install any plugins, if required, and then restart the litpd service

        plugins_req_install = self._check_installed_plugins()

        if plugins_req_install:
            self._install_rpms()
            self._check_plugin_is_registered()
            self.restart_litpd_service(self.management_node)

       # execute 'create' commands on the LITP model tree, creating items
       # that will be picked up by the plugin

        source_paths = list()
        for url in self.find(self.management_node, '/software',
                           'software-item', rtn_type_children=False):

            source_paths.append('{0}{1}'.format(url, package_url))

            self.execute_cli_create_cmd(self.management_node,
                                    '{0}{1}'.format(url, package_url),
                                    self.plugin_type,
                                    self.properties.format(package_name,
                                                           version))

        # check if node_url is a str or a list

        if isinstance(node_url, str):

            # execute 'link' commands on the LITP model tree, linking the
            # items to the nodes

            for url in self.find(self.management_node, node_url,
                    'software-item', rtn_type_children=False, find_refs=True,
                    exclude_services=True):

                for source_path in source_paths:
                    self.execute_cli_inherit_cmd(
                        self.management_node,
                        '{0}{1}'.format(url, package_url),
                        source_path
                    )

        elif isinstance(node_url, list):

            # execute 'link' commands on the LITP model tree, linking the
            # items to the nodes for each node in the list

            for n_url in node_url:
                for url in self.find(self.management_node, n_url,
                    'software-item', rtn_type_children=False, find_refs=True,
                    exclude_services=True):

                    for source_path in source_paths:
                        self.execute_cli_inherit_cmd(
                            self.management_node,
                            '{0}{1}'.format(url, package_url),
                            source_path
                        )

    @attr('all', 'non-revert')
    def test_01_p_rpc_task(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask()

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Check the plan output

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            Remote procedure call tasks must be in the plan output
        """

        # version property for mock-package to run this test

        version = '1.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the show command on the node url to retrieve the hostname of
        # the node

        stdout, _, _ = self.execute_cli_show_cmd(self.management_node, ms_,
                                                    '-j', load_json=False)
        hostname = self.cli.get_properties(stdout)['hostname']

        # execute the 'show_plan' command

        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)

        # check the RPCTask is created in the plan

        match_text = 'RPCTask for {0}:{1}'
        self.assertTrue(self.is_text_in_list(
                        match_text.format(self.pkg_names[0], hostname),
                        stdout),
        '\'{0}\' not found in {1}'.format(match_text.format(self.pkg_names[0],
                                                            hostname),
                                         stdout))

    @attr('all', 'non-revert')
    def test_02_n_agent_not_available(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(), which
            will attempt to make use of an unvailbale agent

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the plan execution fails
            5. Check /var/log/messages for error

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            RPC task must fail because the agent specified is unavailable
        """

        # version property for mock-package to run this test

        version = '2.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the show command on the node url to retrieve the hostname of
        # the node

        stdout, _, _ = self.execute_cli_show_cmd(self.management_node, ms_,
                                                    '-j', load_json=False)
        hostname = self.cli.get_properties(stdout)['hostname']
        self.assertNotEqual('', hostname)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to fail

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check /var/log/messages for failure

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_grep_file_cmd(
                                const.GEN_SYSTEM_LOG_PATH,
                                ['ERROR: Error running \\[\'mco\', \'rpc\', '\
                                '\'--no-progress\', \'servce\', \'status\','\
                                ' \'service=httpd\', \'-I\', \'{0}\'\\]'.\
                                                            format(hostname)
                                ]),
                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    @attr('all', 'non-revert')
    def test_03_n_agent_fails_execution(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(), which
            will attempt to make use of an available agent that fails to
            execute

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the plan execution fails
            5. Check /var/log/messages for error

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            RPC task must fail because the agent fails execution
        """

        # version property for mock-package to run this test

        version = '3.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to fail

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check /var/log/messages for error

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_grep_file_cmd(
                                const.GEN_SYSTEM_LOG_PATH,
                                ['Error running .*service=unknown']),
                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    @attr('all', 'non-revert')
    def test_04_n_agent_with_invalid_action(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(), which
            will attempt to make use of an available agent with an
            unavailable/invalid action

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the plan execution fails
            5. Check /var/log/messages for error

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            RPC task must fail because the action specified is
            unavailable/invalid
        """

        # version property for mock-package to run this test

        version = '4.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to fail

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check /var/log/messages for error

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_grep_file_cmd(
                                const.GEN_SYSTEM_LOG_PATH,
                                ['Error running .*sttus']),
                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    @attr('all', 'non-revert')
    def test_05_n_agent_with_valid_action_invalid_keyword_arguments(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(), which
            will attempt to make use of an available agent with an
            valid action but invalid keyword arguments

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the plan execution fails
            5. Check /var/log/messages for error

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            RPC task must fail because the arguments passed are invalid
        """

        # version property for mock-package to run this test

        version = '5.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the show command on the node url to retrieve the hostname of
        # the node

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for plan to fail

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check /var/log/messages for error

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_grep_file_cmd(
                                const.GEN_SYSTEM_LOG_PATH,
                                ['Error running .*servce=unknown']),
                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def obsolete_06_n_agent_with_valid_action_invalid_arguments(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(), which
            will attempt to make use of an available agent with an
            valid action but invalid arguments

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the plan execution fails
            5. Check /var/log/messages for error

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            RPC task must fail because the arguments passed are invalid
        """

        # version property for mock-package to run this test

        version = '6.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for plan to fail

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check /var/log/messages for error

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_grep_file_cmd(
                                const.GEN_SYSTEM_LOG_PATH,
                                ['Could not parse --arg']),
                                su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    @attr('all', 'non-revert')
    def test_07_p_ordered_list_rpc_task(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask() and add
            it to an OrderedTaskList()

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Check the 'RPCTask()' plan order

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            Plan output must be in the specified ordered list set by the plugin
            with the RPC tasks present
        """

        # version property for mock-package to run this test

        version = '7.0'

        # node url which the test will run against

        nodes = self.find(self.management_node, '/', 'node')
        self.assertNotEqual([], nodes)

        ms_ = self.find(self.management_node, '/', 'ms')
        self.assertNotEqual('', ms_)

        nodes.extend(ms_)

        # execute common test steps

        self._execute_test(nodes, self.pkg_urls[0], self.pkg_names[0], version)
        self._execute_test(nodes, self.pkg_urls[1], self.pkg_names[1], version)

        # execute the show command on the node url to retrieve the hostname of
        # the node

        hostnames = list()
        for node in nodes:
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node,
                                                     node, '-j',
                                                     load_json=False)
            hostname = self.cli.get_properties(stdout)['hostname']
            self.assertNotEqual('', hostname)
            hostnames.append(hostname)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'show_plan' command

        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)

        # check the order of the RPCTask() are as specified in the plugin
        # using the OrderedTaskList()

        match_text = 'RPCTask for {0}:{1}'
        for hostname in sorted(hostnames,
                                        key=lambda hostname: hostname.lower()):

            self.assertTrue(self.is_text_in_list(
                            match_text.format(self.pkg_names[0], hostname),
                            stdout),
            '\'{0}\' not found in {1}'.format(match_text.format(
                                                            self.pkg_names[0],
                                                            hostname),
                                             stdout))

            self.assertTrue(self.is_text_in_list(
                            match_text.format(self.pkg_names[1], hostname),
                            stdout),
            '\'{0}\' not found in {1}'.format(match_text.format(
                                                            self.pkg_names[1],
                                                            hostname),
                                             stdout))

            self.execute_cli_showplan_cmd(self.management_node)

            current_index = stdout.index(match_text.format(self.pkg_names[0],
                                                           hostname))
            next_index = stdout.index(match_text.format(self.pkg_names[1],
                                                        hostname))
            self.assertTrue((current_index > next_index),
            'Host: {0} - Index Value: {1} | Package: {2} > '\
            'Index Value: {3} | Package {4}'.format(
                                    hostname, current_index, self.pkg_names[0],
                                    next_index, self.pkg_names[1]))

    @attr('all', 'non-revert')
    def test_08_p_rpc_task_success_check_model_state(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask()

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the model item's state is set to Applied

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            Remote execution task must be successful and the model item's state
            is set to Applied
        """

        # version property for mock-package to run this test

        version = '8.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual(ms_, '')

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[0], self.pkg_names[0], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'create_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_COMPLETE))

        # check that the model item's state is now set to Applied

        for url in self.find(self.management_node, ms_, self.plugin_type):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                        '-j', load_json=False)

            # get the name property value of each package linked to the node

            item_name = self.cli.get_properties(stdout)['name']

            # check if the package name matches any of the package names used
            # for the test and if it does, check its current state

            if item_name == self.pkg_names[0]:
                stdout, stderr, rcode = self.run_command(self.management_node,
                                            self.cli.get_show_data_value_cmd(
                                                url, 'state'))
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

                self.assertTrue(self.is_text_in_list('Applied', stdout),
                'Expected state Applied for item {0} but got stdout: {1}'.\
                                                        format(url, stdout))

    @attr('all', 'non-revert')
    def test_09_n_hang_rpc_call_off_ms_model_item_fails(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(). Hang
            the task off of a model item (/ms) and set the execution of the
            remote task to occur on the nodes. The execution must be successful
            on one node, but fail on the other. Check that the model item's
            state remains unchanged after this.

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the model item's state is still Initial

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            Remote execution task will fail on the second node and the /ms
            model item state must stay in Initial state
        """

        # version property for mock-package to run this test

        version = '9.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[1], self.pkg_names[1], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'run_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_FAILED))

        # check that the model item's state is now set to Initial

        for url in self.find(self.management_node, ms_, self.plugin_type):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                        '-j', load_json=False)

            # get the name property value of each package linked to the node

            item_name = self.cli.get_properties(stdout)['name']

            # check if the package name matches any of the package names used
            # for the test and if it does, check its current state

            if item_name == self.pkg_names[1]:
                state_val = self.execute_show_data_cmd(
                    self.management_node, url, 'state')
                self.assertEquals(
                    'Initial (deployment of properties indeterminable)',
                    state_val)

    @attr('all', 'non-revert')
    def test_10_p_hang_rpc_call_off_ms_model_item(self):
        """
        Description:
            Create a new dummy plugin to make use of the new RPCTask(). Hang
            the task off of a model item (/ms) and set the execution of the
            remote task to occur on the nodes. The execution must be successful
            on all nodes. Check that the model item's state is set to Applied.

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed and running litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.1.2
               Documentation
            2. Edit the plugin to make use of the 'RPCTask()'
            3. Edit the plugin to make use of an mcollective agent/action
            4. Build an 'RPM' package for the plugin
            5. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
            1. Execute the 'create' command to create a mock item
            2. Execute the 'create_plan' command
            3. Execute the 'run_plan' command
            4. Check the model item's state is set to Applied

        Restore:
            1. Remove the created item from the LITP model tree
            2. Execute the 'create_plan' command

        Results:
            Model item /ms must be set to Applied
        """

        # version property for mock-package to run this test

        version = '10.0'

        # node url which the test will run against

        ms_ = self.find(self.management_node, '/', 'ms')[0]
        self.assertNotEqual('', ms_)

        # execute common test steps

        self._execute_test(ms_, self.pkg_urls[1], self.pkg_names[1], version)

        # execute the 'create_plan' command

        self.execute_cli_createplan_cmd(self.management_node)

        # execute the 'create_plan' command

        self.execute_cli_runplan_cmd(self.management_node)

        # wait for the plan to complete

        self.assertTrue(self.wait_for_plan_state(self.management_node,
                                                 const.PLAN_COMPLETE))

        # check that the model item's state is now set to Applied

        for url in self.find(self.management_node, ms_, self.plugin_type):
            stdout, _, _ = self.execute_cli_show_cmd(self.management_node, url,
                                                        '-j', load_json=False)

            # get the name property value of each package linked to the node

            item_name = self.cli.get_properties(stdout)['name']

            # check if the package name matches any of the package names used
            # for the test and if it does, check its current state

            if item_name == self.pkg_names[1]:
                stdout, stderr, rcode = self.run_command(self.management_node,
                                            self.cli.get_show_data_value_cmd(
                                                url, 'state'))
                self.assertEqual(0, rcode)
                self.assertEqual([], stderr)
                self.assertNotEqual([], stdout)

                self.assertTrue(self.is_text_in_list('Applied', stdout),
                'Expected state Applied for item {0} but got stdout: {1}'.\
                                                        format(url, stdout))
