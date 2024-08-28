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
                Story: LITPCDS-2114
                Sub-Task: LITPCDS-2664, LITPCDS-2661, LITPCDS-2663
'''

import os
import test_constants as const
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils


class Story2114(GenericTest):
    """
    LITPCDS-2114: As a plug-in developer, I want to specify sequencing of tasks
                  on a single item in the model, so that tasks are ordered as
                  expected.
    """

    def setUp(self):
        """
        Description:
            setUp() test method runs before every test
        """

        # call super class setup
        super(Story2114, self).setUp()

        # get cluster information
        self.management_node = self.get_management_node_filename()
        self.assertNotEqual('', self.management_node)

        self.managed_nodes = self.get_managed_node_filenames()
        self.assertNotEqual([], self.managed_nodes)

        # setup required items for the test
        self.cmds = list()
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()

        self.pkg_urls = (
                        '/mock_pkg_01',
                        '/mock_pkg_02',
                        '/mock_pkg_03',
                        '/mock_pkg_04'
                        )
        self.plugin_type = 'mock-package'
        self.properties = 'name=\'{0}\' version=\'{1}\''
        self.pkg_names = (
                        'pkg_z_01',
                        'pkg_c_02',
                        'pkg_C_03',
                        'pkg_a_04'
                        )

        # check if dummy plugins installed
        _dummy_test_plugins = (
        'ERIClitpmockpackageapi_CXP1234567-1.0.1-SNAPSHOT20201013.noarch.rpm',
        'ERIClitpmockpackage_CXP1234567-1.0.1-SNAPSHOT20201013.noarch.rpm')

        plugins_req_install = self._check_installed_plugins(
                                _dummy_test_plugins)

        # install any plugins, if required, and then restart the litpd service
        if plugins_req_install:
            self._install_plugins(plugins_req_install)
            self._restart_litpd_service()

    def tearDown(self):
        """
        Description:
            tearDown() test method runs after every test
        """

        # call super class teardown
        super(Story2114, self).tearDown()

    def _is_plugin_installed(self, plugin):
        """
        Desrcription:
            Check if the required dummy plugins, for the test to run, are
            already installed from a previous test run
        """

        _, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.check_pkg_installed([plugin]))
        self.assertEqual([], stderr)

        if rcode == 0:
            return True

        return False

    def _check_installed_plugins(self, dummy_plugins):
        """
        Description:
            Check which, if any, dummy plugins are installed and get the list
            of those which aren't but are required
        """

        plugins_req_install = list()

        for d_plugin in dummy_plugins:
            if not self._is_plugin_installed(d_plugin.split('.rpm')[0]):
                plugins_req_install.append(d_plugin)

        return plugins_req_install

    def _install_plugins(self, plugins_req_install):
        """
        Description:
            For any dummy plugin, required by the test, that aren't installed,
            install them
        """

        local_path = os.path.dirname(repr(__file__).strip('\''))
        self.assertTrue(self.is_text_in_list(
                        'plugins', os.listdir(local_path)),
        '/plugins folder not found in directory {0} - listing {1}'.format(
                            local_path, os.listdir(local_path)))
        self.assertTrue(os.path.isdir(local_path + '/plugins'),
        '{0} is a file not a folder'.format(local_path + '/plugins'))
        local_path = local_path + '/plugins/'

        for d_plugin in plugins_req_install:
            local_filepath = local_path + d_plugin
            self.assertTrue(self.copy_file_to(self.management_node,
                            local_filepath, const.LITP_PKG_REPO_DIR,
                                            root_copy=True,
                                              add_to_cleanup=False))

        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_createrepo_cmd(const.LITP_PKG_REPO_DIR),
                        su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        plugins_req_install[:] = [d_plugin.split('.rpm')[0] \
                                for d_plugin in plugins_req_install]

        self.toggle_puppet(self.management_node, enable=False)
        stdout, stderr, rcode = self.run_command(self.management_node,
                        self.rhc.get_yum_install_cmd(plugins_req_install),
                        su_root=True)
        self.toggle_puppet(self.management_node)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        for d_plugin in plugins_req_install:
            self.assertTrue(self._is_plugin_installed(d_plugin),
            'Failed to install dummy plugin {0}'.format(d_plugin))

    def _restart_litpd_service(self):
        """
        Description:
            If any dummy plugins had to be installed, restart the litpd service
            so that the plugins are registered
        """

        self.restart_litpd_service(self.management_node)
        #stdout, stderr, rcode = self.run_command(self.management_node,
        #            self.rhc.get_service_restart_cmd('litpd'), su_root=True)
        #self.assertEqual(0, rcode)
        #self.assertEqual([], stderr)
        #self.assertNotEqual([], stdout)

        stdout, stderr, rcode = self.run_command(self.management_node,
                            self.rhc.get_grep_file_cmd(
                                    const.GEN_SYSTEM_LOG_PATH, [
                                    'INFO: Added ModelExtension: \\"mockpac'\
                                    'kage\\"',
                                    'INFO: Added Plugin: \\"mockpackage\\"']),
                                    su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def _exec_litp_commands(self):
        """
        Description:
            Execute a list of create or link commands
        """

        for cmd in self.cmds:
            stdout, stderr, rcode = self.run_command(self.management_node, cmd)
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertEqual([], stdout)

    def _exec_create_plan_command(self):
        """
        Description:
            Execute the create_plan command
        """
        self.execute_cli_createplan_cmd(self.management_node)

    def _exec_run_plan_command(self):
        """
        Description:
            Execute the run_plan command
        """
        self.execute_cli_runplan_cmd(self.management_node)

    def _exec_show_plan_command(self):
        """
        Description:
            Execute the show_plan command
        """
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        return stdout

    def obsolete_01_p_create_ordered_task_list_via_dummy_plugin(self):
        """
        Obsolete - tested by ATs:
            ERIClitpcore/ats/plan/plan_ordered_task_list
            and UTs
        Description:
           Create a dummy plugin, which will set up a set of ordered tasks.

           Install and register the plugin with the litpd model.

           Using the CLI, create or update a set of items in the model tree
           that will use the dummy plugin and, after executing the
           'create_plan' command, running the 'show_plan' command must produce
           the tasks in the order specified by the dummy plugin.

        Pre-Requisites:
           A plugin development environment
           A dummy plugin
           An installed litpd service
           An installed and running MS

        Risks:
           Once a plugin is installed, it cannot be
           deregistered/uninstalled/removed

        Pre-Test Actions:
           1. Generate a dummy plugin as described in the LITP 2.0.7
              Documentation
           2. Edit the plugin to make use of the 'OrderedTaskList()',
              'ConfigTask()' and 'CallbackTask()' Plugin API methods
                   Use two 'ConfiTask()' and two 'CallbackTask()' in a mixed
                   order
                   'CallbackTask()' produces a new 'Phase' in the plan
           3. Build an 'RPM' package for the plugin
           4. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
           1. Execute 'create' commands on the LITP model tree, creating items
              that will be picked up by the plugin
           2. Execute 'link' commands on the LITP model tree, linking the
              items to the nodes
           3. Execute the 'create_plan' command
           4. Execute the 'show_plan' command
           5. Check the order of the tasks in the 'show_plan' output

        Results:
           The tasks listed in the 'show_plan' output must be in the order
           specified by the plugin
        """

       # 1. Execute 'create' commands on the LITP model tree, creating items
       #    that will be picked up by the plugin

        version = '1'
        for url in self.find(self.management_node, '/software',
                           'software-item', rtn_type_children=False):
            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[0],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[0],
                                                           version)))

            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[1],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[1],
                                                           version)))
            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[2],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[2],
                                                           version)))

            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[3],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[3],
                                                           version)))

        nodes = self.find(self.management_node, '/', 'ms')
        nodes.extend(self.find(self.management_node, '/deployments', 'node'))

        nodes_software_items = list()
        for node in nodes:
            nodes_software_items.extend(self.find(self.management_node,
                           node, 'software-item', rtn_type_children=False))

        # 2. Execute 'link' commands on the LITP model tree, linking the
        #    items to the nodes

        url = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]
        for item in nodes_software_items:
            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[0],
                            url + self.pkg_urls[0]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[1],
                            url + self.pkg_urls[1]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[2],
                            url + self.pkg_urls[2]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[3],
                            url + self.pkg_urls[3]))

        self._exec_litp_commands()

        # 3. Execute the 'create_plan' command

        self._exec_create_plan_command()

        # 4. Execute the 'show_plan' command

        stdout = self._exec_show_plan_command()

        # 5. Check the order of the tasks in the 'show_plan' output
        #    check the tasks exist for each node in the plan

        task_package = 'task package {0}'
        for item in nodes_software_items:
            if '/nodes/' in item:
                item = item.split('/nodes/')[1]
            self.assertTrue(self.is_text_in_list(
                       '{0}{1}'.format(item, self.pkg_urls[3]), stdout),
            'Expected task {0}{1} not found in plan'.format(
                                                    item, self.pkg_urls[3]))
            self.assertTrue(self.is_text_in_list(
                           task_package.format(self.pkg_names[3]), stdout),
            'Expected task {0} not found in plan'.format(self.pkg_names[3]))
            self.assertTrue(self.is_text_in_list(
                       '{0}{1}'.format(item, self.pkg_urls[1]), stdout),
            'Expected task {0}{1} not found in plan'.format(
                                                    item, self.pkg_urls[1]))
            self.assertTrue(self.is_text_in_list(
                           task_package.format(self.pkg_names[1]), stdout),
            'Expected task {0} not found in plan'.format(self.pkg_names[1]))
            self.assertTrue(self.is_text_in_list(
                       '{0}{1}'.format(item, self.pkg_urls[2]), stdout),
            'Expected task {0}{1} not found in plan'.format(
                                                    item, self.pkg_urls[2]))
            self.assertTrue(self.is_text_in_list(
                           task_package.format(self.pkg_names[2]), stdout),
            'Expected task {0} not found in plan'.format(self.pkg_names[2]))
            self.assertTrue(self.is_text_in_list(
                       '{0}{1}'.format(item, self.pkg_urls[0]), stdout),
            'Expected task {0}{1} not found in plan'.format(
                                                    item, self.pkg_urls[2]))
            self.assertTrue(self.is_text_in_list(
                           task_package.format(self.pkg_names[0]), stdout),
            'Expected task {0} not found in plan'.format(self.pkg_names[2]))

        #   check the order of the tasks for each node in the plan using their
        #   index number in the returned list
        #   the order is defined by the mockpackage_plugin and
        #   OrderedTaskList() method in core

        self.assertTrue((stdout.index(
                           task_package.format(self.pkg_names[3])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[1]))) and \
                       (stdout.index(
                           task_package.format(self.pkg_names[3])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[2]))) and \
                       (stdout.index(
                           task_package.format(self.pkg_names[3])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[0]))),
        'Expected task not in expected order')

        self.assertTrue((stdout.index(
                           task_package.format(self.pkg_names[1])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[2]))) and \
                       (stdout.index(
                           task_package.format(self.pkg_names[1])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[0]))),
        'Expected task not in expected order')

        self.assertTrue((stdout.index(
                           task_package.format(self.pkg_names[2])) < \
                       stdout.index(
                           task_package.format(self.pkg_names[0]))),
        'Expected task not in expected order')

    def obsolete_02_p_create_unordered_task_list_via_dummy_plugin(self):
        """
        Obsolete:
        Story10575 uses a pluign that generated tasks using both
        the ordered task list and unordered and checks the plan to ensure
        its ordered as expected
        Description:
          Create a dummy plugin, which will set up a set of unordered tasks.

          Install and register the plugin with the litpd model.

          Using the CLI, create or update a set of items in the model tree
          that will use the dummy plugin and, after executing the
          'create_plan' command, running the 'show_plan' command must produce
          the tasks in no particular order, aside from the 'CallbackTask()'
          creating new plan 'Phase'(s).

        Pre-Requisites:
          A plugin development environment
          A dummy plugin
          An installed litpd service
          An installed and running MS

        Risks:
          Once a plugin is installed, it cannot be
          deregistered/uninstalled/removed

        Pre-Test Actions:
          1. Generate a dummy plugin as described in the LITP 2.0.7
             Documentation
          2. Edit the plugin to make use of the 'ConfigTask()' and
            'CallbackTask()' Plugin API methods
                  Use two 'ConfiTask()' and two 'CallbackTask()' in a mixed
                  order
                  'CallbackTask()' produces a new 'Phase' in the plan
          3. Build an 'RPM' package for the plugin
          4. Install the package onto a LITP environment, so that it gets
             registered with the 'litpd' service

        Actions:
          1. Execute 'create' commands on the LITP model tree, creating items
             that will be picked up by the plugin
          2. Execute the 'link' commands on the LITP model tree, linking the
             created items to the nodes
          3. Execute the 'create_plan' command
          4. Execute the 'show_plan' command
          5. Check the tasks exist in the 'show_plan' output

        Results:
          The tasks must be listed in the 'show_plan' output and each
          callback task must have created a new plan phase
        """

        # 1. Execute 'create' commands on the LITP model tree, creating items
        #    that will be picked up by the plugin

        version = '2'
        for url in self.find(self.management_node, '/software',
                          'software-item', rtn_type_children=False):
            self.cmds.append(self.cli.get_create_cmd(
                          url + self.pkg_urls[0],
                          self.plugin_type,
                          properties=self.properties.format(
                                                          self.pkg_names[0],
                                                          version)))

            self.cmds.append(self.cli.get_create_cmd(
                          url + self.pkg_urls[1],
                          self.plugin_type,
                          properties=self.properties.format(
                                                          self.pkg_names[1],
                                                          version)))
            self.cmds.append(self.cli.get_create_cmd(
                          url + self.pkg_urls[2],
                          self.plugin_type,
                          properties=self.properties.format(
                                                          self.pkg_names[2],
                                                          version)))

            self.cmds.append(self.cli.get_create_cmd(
                          url + self.pkg_urls[3],
                          self.plugin_type,
                          properties=self.properties.format(
                                                          self.pkg_names[3],
                                                          version)))

        nodes = self.find(self.management_node, '/', 'ms')
        nodes.extend(self.find(self.management_node, '/deployments', 'node'))

        nodes_software_items = list()
        for node in nodes:
            nodes_software_items.extend(self.find(self.management_node,
                node, 'software-item', rtn_type_children=False, find_refs=True,
                exclude_services=True)
            )

        # 2. Execute the 'link' commands on the LITP model tree, linking the
        #    created items to the nodes

        url = self.find(
            self.management_node, '/software', 'software-item', False,
            exclude_services=True
        )[0]
        for item in nodes_software_items:
            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[0],
                            url + self.pkg_urls[0]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[1],
                            url + self.pkg_urls[1]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[2],
                            url + self.pkg_urls[2]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[3],
                            url + self.pkg_urls[3]))

        # here is where the create and link commands are actually executed from
        # the self.cmds list

        self._exec_litp_commands()

        # 3. Execute the 'create_plan' command

        self._exec_create_plan_command()

        # 4. Execute the 'show_plan' command

        stdout = self._exec_show_plan_command()

        # 5. Check the tasks exist in the 'show_plan' output
        #    for this test we can't rely on any particular order, so we can
        #    only assert that the expected tasks exist

        for item in nodes_software_items:
            if '/nodes/' in item:
                item = item.split('/nodes/')[1]
            self.assertTrue(self.is_text_in_list(
                      '{0}{1}'.format(item, self.pkg_urls[0]), stdout),
            'Expected tasks not found in plan')
            self.assertTrue(self.is_text_in_list(
                      '{0}{1}'.format(item, self.pkg_urls[1]), stdout),
            'Expected tasks not found in plan')
            self.assertTrue(self.is_text_in_list(
                      '{0}{1}'.format(item, self.pkg_urls[2]), stdout),
            'Expected tasks not found in plan')
            self.assertTrue(self.is_text_in_list(
                      '{0}{1}'.format(item, self.pkg_urls[3]), stdout),
            'Expected tasks not found in plan')

        self.assertTrue(self.is_text_in_list(
                      'callback_mock_callback', stdout),
        'Expected tasks not found in plan')
        self.assertTrue(self.is_text_in_list(
                      'callback_raise_exception_callback', stdout),
        'Expected tasks not found in plan')

    @attr('all', 'non-revert')
    def test_03_p_task_order_no_override_item_order(self):
        """
        Tests for plug-in tasks ordering.

        Steps:
           Create a dummy plugin, which will set up a set of ordered tasks,
           using two different model items, which are always executed in a
           particular order (i.e. package before node); and deliberately
           switch the order.

           Install and register the plugin with the litpd model.

           Using the CLI, create or update a set of items in the model tree
           that will use the dummy plugin and, after executing the
           'create_plan' command, running the 'show_plan' command must produce
           both the model items and tasks in the order specified by the dummy
           plugin.

        Pre-Requisites:
           A plugin development environment
           A dummy plugin
           An installed litpd service
           An installed and running MS

        Risks:
           Once a plugin is installed, it cannot be
           deregistered/uninstalled/removed

        Pre-Test Actions:
           1. Generate a dummy plugin as described in the LITP 2.0.7
              Documentation
           2. Edit the plugin to make use of the 'ConfigTask()' and
             'CallbackTask()' Plugin API methods, using two different model
             items
                   Use two 'ConfiTask()' and two 'CallbackTask()' in a mixed
                   order
                   'CallbackTask()' produces a new 'Phase' in the plan
           3. Build an 'RPM' package for the plugin
           4. Install the package onto a LITP environment, so that it gets
              registered with the 'litpd' service

        Actions:
           1. Execute the 'create' commands on the LITP model tree, creating
              items that will be picked up by the plugin
           2. Execute the 'link' commands on the LITP model tree, linking the
              created items to the nodes
           3. Execute the 'create_plan' command
           4. Execute the 'show_plan' command
           5. Check the tasks exist in the 'show_plan' output

        Results:
           The tasks for each model item must be listed in the 'show_plan'
           output in the order specified by the dummy plugin
        """

        # 1. Execute the 'create' commands on the LITP model tree, creating
        #    items that will be picked up by the plugin

        version = '3'
        for url in self.find(self.management_node, '/software',
                           'software-item', rtn_type_children=False):
            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[0],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[0],
                                                           version)))

            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[1],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[1],
                                                           version)))
            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[2],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[2],
                                                           version)))

            self.cmds.append(self.cli.get_create_cmd(
                           url + self.pkg_urls[3],
                           self.plugin_type,
                           properties=self.properties.format(
                                                           self.pkg_names[3],
                                                           version)))

        # find all the nodes in the LITP model tree

        nodes = self.find(self.management_node, '/', 'ms')
        nodes.extend(self.find(self.management_node, '/deployments', 'node'))

        # find the node software-items collection child of the nodes in the
        # LITP model tree

        nodes_software_items = list()
        for node in nodes:
            nodes_software_items.extend(self.find(self.management_node,
                node, 'software-item', rtn_type_children=False, find_refs=True,
                exclude_services=True)
            )

        # 2. Execute the 'link' commands on the LITP model tree, linking the
        #    created items to the nodes

        url = self.find(
            self.management_node, '/software', 'software-item', False,
            exclude_services=True
        )[0]
        for item in nodes_software_items:
            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[0],
                            url + self.pkg_urls[0]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[1],
                            url + self.pkg_urls[1]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[2],
                            url + self.pkg_urls[2]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[3],
                            url + self.pkg_urls[3]))

        # here is where the create and link commands are actually executed from
        # the self.cmds list

        self._exec_litp_commands()

        # 3. Execute the 'create_plan' command

        self._exec_create_plan_command()

        # 4. Execute the 'show_plan' command

        stdout = self._exec_show_plan_command()

        # 5. Check the tasks exist in the 'show_plan' output
        #    check that model item node comes before model item package in an
        #    ordered task list, which proves ordered tasks list overwrite the
        #    usual order of model items

        node_task_index = 0
        pkg_task_index = 0
        for item in nodes_software_items:
            if '/nodes/' in item:
                item = item.split('/nodes/')[1]
            for line in stdout:
                if item in line:
                    curr_index = stdout.index(line)
                    next_index = curr_index + 1
                    if 'node' in stdout[next_index] and 'task first' in \
                                                           stdout[next_index]:
                        node_task_index = next_index
                    if 'package' in stdout[next_index] and 'task second' in \
                                                           stdout[next_index]:
                        pkg_task_index = next_index

        self.assertNotEqual(node_task_index, pkg_task_index)
        self.assertTrue((node_task_index < pkg_task_index))

    def obsolete_04_n_ordered_task_fails_phase_stops(self):
        """
        Obsolete - tested in ATs and UTs
            ats/plan/plan_update_initial_source_item.at
            ats/plan/plan_tasks_partial_puppet_fail.at
            ats/plan/plan_state_failed.at
            ats/plan/node_lock/node_lock_callback_task.at
            ats/plan/node_lock/node_lock_config_task.at
            ats/plan/node_lock/node_lock_config_task.at
        Description:
            Create a dummy plugin, which will set up a set of ordered tasks,
            one of which will delibirately raise an exception.

            Install and register the plugin with the litpd model.

            Using the CLI, create or update a set of items in the model tree
            that will use the dummy plugin and, after executing the
            'create_plan' command, running the 'show_plan' command must produce
            both the tasks in the order specified by the dummy plugin.

            After executing the 'run_plan' command and the exception is raised
            by one of the tasks, the phase must immediately stop and no other
            task will execute.

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.0.7
               Documentation
            2. Edit the plugin to make use of the 'ConfigTask()' and
              'CallbackTask()' Plugin API methods, using two different model
              items
                    Use two 'ConfiTask()' and two 'CallbackTask()' in a mixed
                    order
                    'CallbackTask()' produces a new 'Phase' in the plan
            3. Build an 'RPM' package for the plugin
            4. Install the package onto a LITP environment, so that it gets
               registered with the 'litpd' service

        Actions:
            1. Execute the 'create' commands on the LITP model tree, creating
               items that will be picked up by the plugin
            2. Execute the 'link' commands on the LITP model tree, linking the
               created items to the nodes
            3. Execute the 'create_plan' command
            4. Execute the 'run_plan' command
            5. Execute the 'show_plan' command
            6. Check the plan failed

        Post-Test Actions:
            1. A test against LITPCDS-1860, checking that it's indeed fixed

        Results:
            The plugin will raise an exception and the plan will fail and stop.
        """

        # Pylint fix
        # Obsolete test case. Return pass statement
        pass

#        # 1. Execute 'create' commands on the LITP model tree, creating items
#        #    that will be picked up by the plugin
#
#        version = '4'
#        for url in self.find(self.management_node, '/software',
#                            'software-item', rtn_type_children=False):
#            self.cmds.append(self.cli.get_create_cmd(
#                            url + self.pkg_urls[0],
#                            self.plugin_type,
#                            properties=self.properties.format(
#                                                            self.pkg_names[0],
#                                                            version)))
#
#            self.cmds.append(self.cli.get_create_cmd(
#                            url + self.pkg_urls[1],
#                            self.plugin_type,
#                            properties=self.properties.format(
#                                                            self.pkg_names[1],
#                                                            version)))
#            self.cmds.append(self.cli.get_create_cmd(
#                            url + self.pkg_urls[2],
#                            self.plugin_type,
#                            properties=self.properties.format(
#                                                            self.pkg_names[2],
#                                                            version)))
#
#            self.cmds.append(self.cli.get_create_cmd(
#                            url + self.pkg_urls[3],
#                            self.plugin_type,
#                            properties=self.properties.format(
#                                                            self.pkg_names[3],
#                                                            version)))
#
#        # find all the nodes from the LITP model tree
#
#        nodes = self.find(self.management_node, '/', 'ms')
#        nodes.extend(self.find(self.management_node, '/deployments', 'node'))
#
#        # find the software-items collection child of the nodes in the LITP
#        # model tree
#
#        nodes_software_items = list()
#        for node in nodes:
#            nodes_software_items.extend(self.find(self.management_node,
#                            node, 'software-item', rtn_type_children=False))
#
#        # 2. Execute the 'link' commands on the LITP model tree, linking the
#        #    created items to the nodes
#
#        url = self.find(
#            self.management_node, '/software', 'software-item', False
#        )[0]
#        for item in nodes_software_items:
#            self.cmds.append(self.cli.get_inherit_cmd(
#                           item + self.pkg_urls[0],
#                            url + self.pkg_urls[0]))
#
#            self.cmds.append(self.cli.get_inherit_cmd(
#                           item + self.pkg_urls[1],
#                            url + self.pkg_urls[1]))
#
#            self.cmds.append(self.cli.get_inherit_cmd(
#                           item + self.pkg_urls[2],
#                            url + self.pkg_urls[2]))
#
#            self.cmds.append(self.cli.get_inherit_cmd(
#                           item + self.pkg_urls[3],
#                            url + self.pkg_urls[3]))
#
#        # here is where the create and link commands are actually executed
#        # from the self.cmds list
#
#        self._exec_litp_commands()
#
#        # 3. Execute the 'create_plan' command
#
#        self._exec_create_plan_command()
#
#        # 4. Execute the 'run_plan' command
#
#        self._exec_run_plan_command()
#
#        # wait for the plan to stop running
#        self.assertTrue(self.wait_for_plan_state(
#                        self.management_node, const.PLAN_FAILED),
#        'Expected plan to fail, but it didn\'t')
#
#        # 5. Execute the 'show_plan' command
#
#        stdout = self._exec_show_plan_command()
#
#        #6. Check the plan failed
#        #   check that the plan failed at the expected task
#
#        if self.is_text_in_list('callback_raise_exception_callback', stdout):
#            indx = stdout.index('callback_raise_exception_callback')
#            if self.is_text_in_list('\t\t/', [stdout[indx - 1]]):
#                self.assertTrue(self.is_text_in_list('Failed\t\t', stdout),
#                'Plan failed but not at the expected task')
#
#        # 1. A test against LITPCDS-1860, checking that it's indeed fixed
#        #   now the check to verify that LITPCDS-1860 is indeed fixed as per
#        #   the acceptance criteria of the story
#
#        #   the successful tasks must not be included in the plan again
#        #   get successful tasks from current failed plan
#
#        successful_tasks = [line.strip('Success\t\t') for line in stdout \
#                           if self.is_text_in_list('Success\t\t', [line]) and
#                           not self.is_text_in_list('callback',
#                                        [stdout[stdout.index(line) + 1]])]
#
#        # the tasks that are still in initial state must be included in the
#        # regenerated plan
#
#        initial_tasks = [line for line in stdout \
#                        if self.is_text_in_list('Initial\t\t', [line])]
#
#        # get the hostname of any node where the plan tasks were successful
#
#        std_out = list()
#        hostname = ''
#
#        # only one node will ever have successful tasks, the rest will never
#        # be run because the callback_raise_exception task will fail, as
#        # intended, and the plan stops
#        # therefore, we only need to find the
#        # node in plan which has tasks which were successful and get its
#        # hostname
#        # since the other nodes are never run, no manifests are ever generated
#        # for those and they can be safely ignored
#
#        for node in nodes:
#            for line in stdout:
#                if self.is_text_in_list(node, [line]) and \
#                    self.is_text_in_list('Success\t\t', [line]):
#                    std_out, _, _ = self.execute_cli_show_cmd(
#                        self.management_node, node, "-j")
#        if std_out:
#            hostname = self.cli.get_properties(std_out)['hostname']
#
#        self.assertNotEqual('', hostname)
#
#        # check that the puppet manifests task have the appropriate
#        # requirements specified by the order of the tasks
#
#        stdout, stderr, rcode = self.run_command(self.management_node,
#                            self.rhc.get_grep_file_cmd(
#                                   const.PUPPET_MANIFESTS_DIR + '*.pp', [
#                                   'require=>\n[Class["task_{0}__file___2ftm'\
#                                   'p_2fsecond__pkg__a__04"]'.format(
#                                                                   hostname),
#                                   'require=>\n[Class["task_{0}__file___2ftm'\
#                                   'p_2fsecond__pkg___43__03"]]'.format(
#                                                               hostname)]))
#        self.assertEqual(0, rcode)
#        self.assertEqual([], stderr)
#        self.assertNotEqual([], stdout)
#
#        del self.cmds[:]
#
#        # add a new mock-package to the LITP model tree
#
#        for url in self.find(self.management_node, '/software',
#                            'software-item', rtn_type_children=False):
#            self.cmds.append(self.cli.get_create_cmd(
#                            url + '/mock_pkg_05', self.plugin_type,
#                            properties=self.properties.format('pkg_b',
#                                                              version)))
#
#        # link a new mock-package to the LITP model tree
#
#        url = self.find(
#            self.management_node, '/software', 'software-item', False
#        )[0]
#        for item in nodes_software_items:
#            self.cmds.append(self.cli.get_inherit_cmd(
#                            item + '/mock_pkg_05',
#                            url + '/mock_pkg_05'))
#
#        # here is where the create and link commands are actually executed
#        # from the self.cmds list
#
#        self._exec_litp_commands()
#
#        # execute the 'create_plan' command
#
#        self._exec_create_plan_command()
#
#        # Execute the 'show_plan' command
#
#        stdout = self._exec_show_plan_command()
#
#        # check successful tasks are missing
#
#        for line in successful_tasks:
#            self.assertFalse(self.is_text_in_list(line, stdout),
#            'Successful task from previous plan were added to new plan again')
#
#        # check initial tasks are not missing
#
#        for line in initial_tasks:
#            self.assertTrue(self.is_text_in_list(line, stdout),
#            'Initial tasks from previous plan were not added to new plan '\
#            'again')

    def obsolete_05_p_create_plan_overwrite_previous_not_run_plan(self):
        """
        Obsolete - tested by ATs
            ERIClitpcore/ats/plan/plan_create_plan_should_remove_existing_\
                plan_even_if_no_plan_has_been_created.at
        Description:
            A test to check that LITPCDS-2802 Bug is indeed fixed.

            Create a dummy plugin, which will set up a set of ordered tasks.

            Install and register the plugin with the litpd model.

            Using the CLI, create or update a set of items in the model tree
            that will use the dummy plugin and, after executing the
            'create_plan' command, running the 'show_plan' command must produce
            the task.

            Removing the items without running the plan and executing the
            'create_plan' and 'show_plan' commands again, must produce errors

        Pre-Requisites:
            A plugin development environment
            A dummy plugin
            An installed litpd service
            An installed and running MS

        Risks:
            Once a plugin is installed, it cannot be
            deregistered/uninstalled/removed

        Pre-Test Actions:
            1. Generate a dummy plugin as described in the LITP 2.0.7
               Documentation
            2. Edit the plugin to make use of the 'OrderedTaskList()',
               'ConfigTask()' and 'CallbackTask()' Plugin API methods
                    Use two 'ConfiTask()' and two 'CallbackTask()' in a mixed
                    order
                    'CallbackTask()' produces a new 'Phase' in the plan
            3. Build an 'RPM' package for the plugin
            4. Install the package onto a LITP environment, so that it gets
               registered with the 'litpd' service

        Actions:
            1. Execute 'create' commands on the LITP model tree, creating items
               that will be picked up by the plugin
            2. Execute 'link' commands on the LITP model tree, linking the
               items to the nodes
            3. Execute the 'create_plan' command
            4. Execute the 'show_plan' command
            5. Execute 'remove' commands on the LITP model tree, removing the
               model items
            6. Execute the 'create_plan' command and check for errors
            7. Execute the 'show_plan' command and check for errors

        Results:
            The second 'create_plan' and 'show_plan' commands must produce
            errors
        """

        # 1. Execute 'create' commands on the LITP model tree, creating items
        #    that will be picked up by the plugin

        version = '1'
        for url in self.find(self.management_node, '/software',
                            'software-item', rtn_type_children=False):
            self.cmds.append(self.cli.get_create_cmd(
                            url + self.pkg_urls[0],
                            self.plugin_type,
                            properties=self.properties.format(
                                                            self.pkg_names[0],
                                                            version)))

            self.cmds.append(self.cli.get_create_cmd(
                            url + self.pkg_urls[1],
                            self.plugin_type,
                            properties=self.properties.format(
                                                            self.pkg_names[1],
                                                            version)))
            self.cmds.append(self.cli.get_create_cmd(
                            url + self.pkg_urls[2],
                            self.plugin_type,
                            properties=self.properties.format(
                                                            self.pkg_names[2],
                                                            version)))

            self.cmds.append(self.cli.get_create_cmd(
                            url + self.pkg_urls[3],
                            self.plugin_type,
                            properties=self.properties.format(
                                                            self.pkg_names[3],
                                                            version)))

        nodes = self.find(self.management_node, '/', 'ms')
        nodes.extend(self.find(self.management_node, '/deployments', 'node'))

        nodes_software_items = list()
        for node in nodes:
            nodes_software_items.extend(self.find(self.management_node,
                            node, 'software-item', rtn_type_children=False))

        # 2. Execute 'link' commands on the LITP model tree, linking the
        #    items to the nodes

        url = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]
        for item in nodes_software_items:
            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[0],
                            url + self.pkg_urls[0]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[1],
                            url + self.pkg_urls[1]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[2],
                            url + self.pkg_urls[2]))

            self.cmds.append(self.cli.get_inherit_cmd(
                           item + self.pkg_urls[3],
                            url + self.pkg_urls[3]))

        self._exec_litp_commands()

        # 3. Execute the 'create_plan' command

        self._exec_create_plan_command()

        # 4. Execute the 'show_plan' command

        stdout = self._exec_show_plan_command()
        self.assertNotEqual([], stdout)

        # 5. Execute 'remove' commands on the LITP model tree, removing the
        #    model items

        for url in self.find(self.management_node, '/', self.plugin_type):
            self.execute_cli_remove_cmd(self.management_node, url)

        # 6. Execute the 'create_plan' again and check for error message
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )

        self.assertTrue(self.is_text_in_list('DoNothingPlanError', stderr),
        'Expected error message not found')

        # 7. Execute the 'show_plan' command and check for error message
        _, stderr, _ = self.execute_cli_showplan_cmd(
            self.management_node, expect_positive=False
        )
        self.assertTrue(self.is_text_in_list('InvalidLocationError', stderr),
        'Expected error message not found')
