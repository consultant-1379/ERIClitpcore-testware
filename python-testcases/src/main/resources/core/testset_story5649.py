'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@author:    Jacek Spera, Matt Boyer
@summary:   Integration test for multiple model items assigned to tasks
            Story: 5649 Sub-Task: 6748
'''

from litp_generic_test import GenericTest
from rest_utils import RestUtils
from litp_cli_utils import CLIUtils
import test_constants
import os


class CliShim(object):
    '''
    Jacek's CLI shim.
    Wraps calls to the CI framework's CLI methods in such a way that common
    arguments such as the MS needn't be repeated throughout ITs.
    '''
    def __init__(self, test):
        self.test = test
        self.mgmt_server = test.get_management_node_filename()

    def show(self, item_path):
        '''
        Wrapper for execute_cli_show_cmd
        '''
        return self.test.execute_cli_show_cmd(self.mgmt_server, item_path)

    def create(self, item_path, item_type, option_string=""):
        '''
        Wrapper for execute_cli_create_cmd
        '''
        return self.test.execute_cli_create_cmd(
            self.mgmt_server,
            item_path,
            item_type,
            props=option_string
        )

    def update(self, item_path, option_string=""):
        '''
        Wrapper for execute_cli_update_cmd
        '''
        return self.test.execute_cli_update_cmd(
            self.mgmt_server,
            item_path,
            props=option_string
        )

    def create_plan(self):
        '''
        Wrapper for execute_cli_updateplan_cmd
        '''
        return self.test.execute_cli_createplan_cmd(self.mgmt_server)

    def run_plan(self):
        '''
        Wrapper for execute_cli_runplan_cmd and wait_for_plan_state
        '''
        self.test.execute_cli_runplan_cmd(self.mgmt_server)
        return self.test.wait_for_plan_state(
            self.mgmt_server,
            test_constants.PLAN_COMPLETE
        )

    def show_plan(self):
        '''
        Wrapper for execute_cli_showplan_cmd
        '''
        return self.test.execute_cli_showplan_cmd(self.mgmt_server)


class Story5649(GenericTest):
    """
    As a plugin developer, I want to be able to specify a list of model items
    for the tasks I'm generating, so that these items will have their state
    updated based on the results of the execution of my tasks
    """

    def setUp(self):
        """Runs before every test to perform setup"""
        super(Story5649, self).setUp()
        self.test_ms = self.get_management_node_filename()
        self.item_extension = 'story5649'
        self.plugin = 'story5649'
        self.ms_ip = self.get_node_att(self.test_ms, 'ipv4')
        self.rest = RestUtils(self.ms_ip)
        self.utils = CLIUtils()
        self.litp = CliShim(self)

        self.test_plugins = (
            'ERIClitpstory5649api_CXP1234567-1.0.1-'
            'SNAPSHOT20141010150558.noarch.rpm',
            'ERIClitpstory5649_CXP1234567-1.0.1-'
            'SNAPSHOT20141010150357.noarch.rpm',
        )

    def tearDown(self):
        """Runs after every test to perform cleanup"""
        super(Story5649, self).tearDown()
        # We'll need to create and run a plan to actually remove items
        self.rest.clean_paths()
        del self.litp

    def _get_local_filepath(self, path, isdir=False):
        """
        Description:
            Get the local filepath to the test currently running and use it to
            retrieve the requested directory or file which must be copied onto
            the node under test
        """

        # get the directory path of where the current test file is located
        local_path = os.path.dirname(repr(__file__).strip('\''))
        # check that the local path to test file holds the requested
        # path
        self.assertTrue(
            self.is_text_in_list(path, os.listdir(local_path)),
            '\'{0}\' not found in directory \'{1}\' - listing \'{2}\''.
            format(path, local_path, os.listdir(local_path))
        )
        if isdir:
            # check that requested path is really a directory
            self.assertTrue(
                os.path.isdir('{0}/{1}'.format(local_path, path)),
                '\'{0}/{1}\' is not a directory'.format(local_path, path)
            )
            return '{0}/{1}'.format(local_path, path)
        else:
            # check that requested path is really a file
            self.assertTrue(
                os.path.isfile('{0}/{1}'.format(local_path, path)),
                '\'{0}/{1}\' is not a file'.format(local_path, path)
            )
            return '{0}/{1}'.format(local_path, path)

    def _check_installed_plugins(self):
        """
        Description:
            Check which, if any, dummy plugins are installed and get the list
            of those which aren't but are required
        """

        plugins_require_install = list()
        # for each plugin rpm in tuple test plugins, check if the rpm is
        # already installed and if not, mark it for installation
        for plugin in self.test_plugins:
            if not self._is_plugin_installed(plugin.split('.rpm')[0]):
                plugins_require_install.append(plugin)

        return plugins_require_install

    def _is_plugin_installed(self, plugin):
        """
        Desrcription:
            Check if the required dummy plugins, for the test to run, are
            already installed from a previous test run
        """

        # check if the given plugin rpm is installed or not
        _, stderr, rcode = self.run_command(
            self.test_ms,
            self.rhc.check_pkg_installed([plugin])
        )
        self.assertEqual([], stderr)
        if rcode == 0:
            return True

        return False

    def _check_plugin_is_registered(self):
        """
        Description:
            Check the plugins required for the test run are registered with the
            litpd service
        """

        # check the plugin is registered with the litpd service
        expected_info_logs = [
            'INFO: Added ModelExtension: \\"{0}\\"'.format(
                self.item_extension
            ),
            'INFO: Added Plugin: \\"{0}\\"'.format(self.plugin)
        ]
        stdout, stderr, rcode = self.run_command(
            self.test_ms,
            self.rhc.get_grep_file_cmd(
                test_constants.GEN_SYSTEM_LOG_PATH,
                expected_info_logs
            ),
            su_root=True
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def _install_plugins(self):
        """
        Description:
            For any dummy plugin, required by the test, that aren't installed,
            install them
        """

        plugins_require_install = self._check_installed_plugins()
        if plugins_require_install:
            # get the local filepath to the plugin rpm directory
            local_path = self._get_local_filepath('plugins', isdir=True)
            # for each plugin marked for installation, copy the rpm to the
            # management node where the test is running on
            for plugin in plugins_require_install:
                local_filepath = '{0}/{1}'.format(local_path, plugin)
                self.assertTrue(
                    self.copy_file_to(
                        self.test_ms,
                        local_filepath,
                        test_constants.LITP_PKG_REPO_DIR,
                        root_copy=True,
                        add_to_cleanup=False
                    ),
                    'Failed to copy file \'{0}\' to \'{1}\' on node \'{2}\''.
                    format(
                        local_filepath,
                        test_constants.LITP_PKG_REPO_DIR,
                        self.test_ms
                    )
                )
            # recreate the yum repository to recognise the newly copied rpm
            # files
            stdout, stderr, rcode = self.run_command(
                self.test_ms,
                self.rhc.get_createrepo_cmd(
                    test_constants.LITP_PKG_REPO_DIR
                ),
                su_root=True
            )
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)
            # remove the .rpm extension from each of the plugins marked for
            # installation so yum will be able to recognise them and install
            # them
            plugins_require_install[:] = [
                plugin.split('.rpm')[0] for plugin in plugins_require_install
            ]
            # install the rpm files using yum
            stdout, stderr, rcode = self.run_command(
                self.test_ms,
                self.rhc.get_yum_install_cmd(plugins_require_install),
                su_root=True
            )
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)
            # check that the plugins were successfully installed
            for plugin in plugins_require_install:
                self.assertTrue(
                    self._is_plugin_installed(plugin),
                    'Failed to install plugin \'{0}\''.format(plugin)
                )
            self._check_plugin_is_registered()
            self.restart_litpd_service(self.test_ms)

    def obsolete_01_n_single_task_multiple_model_items(self):
        """
        Obsolete: Test has been converted to an AT:
        ats/testset_story5649/test_01_n_single_task_multiple_model_items.at
        Test Description:
        Given a LITP deployment and a LITP plugin, where one task is generated
        by the plugin, if a list of multiple model items is associated with the
        task and the task execution fails, then none of the model item states
        will be updated.

        Pre-Requisites:
        1.  A running litpd service
        2.  An installed test item type extension/plugin

        Risks:
        1.  Once an item type extension is installed and registered with the
            litpd service, it cannot be removed
        2.  Once a plugin is installed, it cannot be removed

        Pre-Test Steps:
        1.  Create a new item type extension as described in the LITP 2 SDK.
        2.  Create a new plugin as described in the LITP 2 SDK.
            The new plugin to associate a list of model items to the task to be
            returned.

        Steps:
        1.  Execute the create command to create a test model item
        2.  Execute the create command to create a second test model item
        3.  Execute the create_plan command
        4.  Execute the run_plan command and wait for successful plan execution
        5.  Check the model items are in Applied state
        6.  Update one of the model items and check state of the model item is
            now Updated
        7.  Execute the create command to create a third model item and check
            its state is Initial
        8.  Execute the create_plan command
        9.  Execute the show_plan command and check the task returned from the
            plugin exists
        10. Execute the run_plan command and wait for plan failure
        11. Check each model item has an unchanged state

        Restore:
        1.  Execute the remove command on all test model items
        2.  Execute the create_plan command
        3.  Execute the run_plan command and wait for successful plan execution
        4.  Check test model items are removed

        Expected Result:
        After the task execution fails, check the model items' states are
        unchanged.
        """
        self._install_plugins()

        self.litp.create("/software/items/test_item01", self.plugin,
                         "name=test_01_01")
        self.litp.create("/software/items/test_item02", self.plugin,
                         "name=test_01_02")

        self.litp.create_plan()
        self.assertTrue(self.litp.run_plan())
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item02"))

        self.litp.update("/software/items/test_item01",
                         "name=test_01_01_updated")
        self.assertEquals('Updated',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))

        self.litp.create("/software/items/test_item03", self.plugin,
                         "name=test_01_03")
        self.assertEquals('Initial',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item03"))

        self.litp.create_plan()

        plan_stdout, _, _ = self.litp.show_plan()
        self.assertTrue(
            self.is_text_in_list("Callback test_01_01_updated", plan_stdout)
        )
        self.rest.run_plan_rest()
        self.rest.wait_for_plan_state_rest(test_constants.PLAN_TASKS_FAILED)

        self.assertEquals('Updated (deployment of properties indeterminable)',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))
        self.assertEquals('Applied (deployment of properties indeterminable)',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item02"))
        self.assertEquals('Initial (deployment of properties indeterminable)',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item03"))

    def obsolete_02_p_single_task_multiple_model_items(self):
        """
        Obsolete: Test has been converted to an AT:
        ats/testset_story5649/test_02_p_single_task_multiple_model_items.at
        Test Description
        Given a LITP deployment and a LITP plugin, where one task is generated
        by the plugin, if a list of multiple model items is associated with the
        task and the task execution is successful, then the model items will be
        set to an Applied state.

        Pre-Requisites
        1.  A running litpd service
        2.  An installed test item type extension/plugin

        Risks
        1.  Once an item type extension is installed and registered with the
            litpd service, it cannot be removed
        2.  Once a plugin is installed, it cannot be removed

        Pre-Test Steps
        1.  Create a new item type extension as described in the LITP 2 SDK
        2.  Create a new plugin as described in the LITP 2 SDK
            Edit the new plugin to associate a list of model items to the task
            to be returned
            NOTE: (Ideally, the items should be in varying states i.e. Initial,
            Updated and Applied)

        Steps:
        1.  Execute the create command to create a test model item
        2.  Execute the create command to create a second test model item
        3.  Execute the create_plan command
        4.  Execute the run_plan command and wait for successful plan execution
        5.  Check the model items are in Applied state
        6.  Update one of the model items and check state of the model item is
            now Updated
        7.  Execute the create command to create a third model item and check
            its state is Initial
        8.  Execute the create_plan command
        9.  Execute the show_plan command and check the task returned from the
            plugin exists
        10. Execute the run_plan command and wait for successful plan execution
        11. Check the model items are in Applied state

        Restore
        1.  Execute the remove command on all test model items
        2.  Execute the create_plan command
        3.  Execute the run_plan command and wait for successful plan execution
        4.  Check test model items are removed

        Expected Result
        After the task execution is successful, check the model items' states
        are set to Applied.
        """
        self._install_plugins()

        self.litp.create("/software/items/test_item01", self.plugin,
                         "name=test_02_01")
        self.litp.create("/software/items/test_item02", self.plugin,
                         "name=test_02_02")

        self.litp.create_plan()
        self.assertTrue(self.litp.run_plan())
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item02"))

        self.litp.update(
            "/software/items/test_item01",
            "name=test_02_01_updated"
        )
        self.assertEquals('Updated',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))

        self.litp.create("/software/items/test_item03", self.plugin,
                         "name=test_02_03")
        self.assertEquals('Initial',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item03"))

        self.litp.create_plan()
        plan_stdout, _, _ = self.litp.show_plan()
        self.assertTrue(
            self.is_text_in_list("Callback test_02_01_updated", plan_stdout)
        )
        self.assertTrue(self.litp.run_plan())

        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item02"))
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item03"))

    def obsolete_03_n_Multiple_Tasks_Failure(self):
        '''
        Obsolete: Test has been converted to an AT:
        ats/testset_story5649/test_03_n_Multiple_Tasks_Failure.at
        Test Description

            Given a LITP deployment and a LITP plugin, where multiple tasks are
            generated by the plugin, if a single model item is associated with
            those tasks and any of the tasks' execution fail, then the model
            item state will not be updated.

        Pre-Requisites

            A running litpd service
            An installed test item type extension/plugin

        Risks

            Once an item type extension is installed and registered with the
            litpd service, it cannot be removed
            Once a plugin is installed, it cannot be removed

        Pre-Test Steps

            Create a new item type extension as described in the LITP 2 SDK
            Create a new plugin as described in the LITP 2 SDK
            Edit the new plugin to return a number of tasks
            Edit the new plugin to associate a single model item to all tasks
            to be returned

        Steps:

            Execute the create command to create a test model item and check
            its state is Initial
            Execute the create_plan command
            Execute the show_plan command and check the tasks, returned from
            the plugin, exist
            Execute the run_plan command and wait for plan failure
            Check that, even though some tasks were successful, the task(s)
            that fail, results in model item state remaining unchanged

        Restore

            Execute the remove command on all test model items
            Execute the create_plan command
            Execute the run_plan command and wait for successful plan execution
            Check test model items are removed

        Expected Result

            After the task(s) execution fail, check the model item's state is
            unchanged.
        '''
        self._install_plugins()
        item_vpath = '/software/items/test3'
        self.execute_cli_create_cmd(
            self.test_ms,
            item_vpath,
            "story5649",
            "name=test_03"
        )

        test_item_json, _, _ = self.rest.get(item_vpath)
        test_item_status, _ = self.rest.get_json_response(test_item_json)
        self.assertEquals('Initial', test_item_status['state'])

        node_vpaths = self.find(self.test_ms, "/deployments", "node")
        for node_vpath in node_vpaths:
            # Inherit the item in order to trigger a task
            node_item = '/'.join([node_vpath, 'items', 'test_03'])
            self.execute_cli_inherit_cmd(
                self.test_ms,
                node_item,
                item_vpath
            )

            inherited_test_item_json, _, _ = self.rest.get(node_item)
            inherited_test_item_status, _ = self.rest.get_json_response(
                inherited_test_item_json
            )
            self.assertEquals('Initial', inherited_test_item_status['state'])
            self.assertTrue(
                inherited_test_item_status['applied_properties_determinable'])
        self.rest.create_plan_rest()

        out, _, _ = self.execute_cli_showplan_cmd(self.test_ms)
        self.assertEquals(1, self.utils.get_num_phases_in_plan(out))
        self.assertEquals(2, self.utils.get_num_tasks_in_phase(out, 1))

        self.rest.run_plan_rest()
        self.rest.wait_for_plan_state_rest(test_constants.PLAN_TASKS_FAILED)
        out, _, _ = self.execute_cli_showplan_cmd(self.test_ms)

        test_item_json, _, _ = self.rest.get(item_vpath)
        test_item_status, _ = self.rest.get_json_response(test_item_json)
        self.assertEquals('Initial', test_item_status['state'])
        self.assertFalse(
                test_item_status['applied_properties_determinable'])

    def obsolete_04_p_Multiple_Tasks_Success(self):
        """
        Obsolete: Test has been converted to an AT:
        ats/testset_story5649/test_04_p_Multiple_Tasks_Success.at
        Test Description

            Given a LITP deployment and a LITP plugin, where multiple tasks are
            generated by the plugin, if a single model item is associated with
            those tasks and all tasks' execution are successful, then the model
            item will be set to an Applied state.
            Pre-Requisites

            A running litpd service
            An installed test item type extension/plugin

        Risks

            Once an item type extension is installed and registered with the
            litpd service, it cannot be removed
            Once a plugin is installed, it cannot be removed

        Pre-Test Steps

            Create a new item type extension as described in the LITP 2 SDK
            Create a new plugin as described in the LITP 2 SDK
            Edit the new plugin to return a number of tasks
            Edit the new plugin to associate a single model item to all tasks
            to be returned

        Steps:

            Execute the create command to create a test model item and check
            its state is Initial
            Execute the create_plan command
            Execute the show_plan command and check the tasks, returned from
            the plugin, exist
            Execute the run_plan command and wait for successful plan execution
            Check that the model item state is set to Applied

        Restore

            Execute the remove command on all test model items
            Execute the create_plan command
            Execute the run_plan command and wait for successful plan execution
            Check test model items are removed

        Expected Result

            After the task(s) execution are successful, check the model item's
            state is set to Applied.
        """
        self._install_plugins()
        item_vpath = '/software/items/test4'
        self.execute_cli_create_cmd(
            self.test_ms,
            item_vpath,
            "story5649",
            "name=test_04"
        )

        test_item_json, _, _ = self.rest.get(item_vpath)
        test_item_status, _ = self.rest.get_json_response(test_item_json)
        self.assertEquals('Initial', test_item_status['state'])

        node_vpaths = self.find(self.test_ms, "/deployments", "node")
        for node_vpath in node_vpaths:
            # Inherit the item in order to trigger a task
            node_item = '/'.join([node_vpath, 'items', 'test_04'])
            _, _, _ = self.execute_cli_inherit_cmd(
                self.test_ms,
                node_item,
                item_vpath
            )

            inherited_test_item_json, _, _ = self.rest.get(node_item)
            inherited_test_item_status, _ = self.rest.get_json_response(
                inherited_test_item_json
            )
            self.assertEquals('Initial', inherited_test_item_status['state'])
            self.assertTrue(
                inherited_test_item_status['applied_properties_determinable'])
        self.rest.create_plan_rest()

        out, _, _ = self.execute_cli_showplan_cmd(self.test_ms)
        self.assertEquals(1, self.utils.get_num_phases_in_plan(out))
        self.assertEquals(2, self.utils.get_num_tasks_in_phase(out, 1))

        self.rest.run_plan_rest()
        self.rest.wait_for_plan_state_rest(test_constants.PLAN_COMPLETE)
        out, _, _ = self.execute_cli_showplan_cmd(self.test_ms)

        test_item_json, _, _ = self.rest.get(item_vpath)
        test_item_status, _ = self.rest.get_json_response(test_item_json)
        self.assertEquals('Applied', test_item_status['state'])
        self.assertTrue(
                test_item_status['applied_properties_determinable'])

    def obsolete_05_p_multiple_tasks_with_multiple_model_items(self):
        """
        Obsolete: Test has been converted to an AT:
        ats/testset_story5649/
        test_05_p_multiple_tasks_with_multiple_model_items.at
        Test Description
        Given a LITP deployment and a LITP plugin, where multiple tasks are
        generated by the plugin, if a list of multiple model items is
        associated with those tasks and all tasks' execution are successful,
        then the model items will be set to an Applied state, if and only if
        all associated tasks are successful.

        Pre-Requisites
        1.  A running litpd service
        2.  An installed test item type extension/plugin

        Risks
        1.  Once an item type extension is installed and registered with the
            litpd service, it cannot be removed
        2.  Once a plugin is installed, it cannot be removed

        Pre-Test Steps
        1.  Create a new item type extension as described in the LITP 2 SDK
        2.  Create a new plugin as described in the LITP 2 SDK
            Edit the new plugin to return a number of tasks
            Edit the new plugin to associate a number of model items to a
            number of tasks to be returned
            NOTE: (Ideally, two model items per two tasks for a total of four
            tasks, where one set will be successful and the other will fail)

        Steps:
        1.  Execute the create command to create a number of test model items
        2.  Execute the create_plan command
        3.  Execute the show_plan command and check the tasks, returned from
            the plugin, exist
        4.  Execute the run_plan command and wait for plan failure
        5.  Check the model items associated with the successful tasks are all
            in Applied state
        6.  Check the model items associated with the failed task(s) are all in
            Initial state

        Restore
        1.  Execute the remove command on all test model items
        2.  Execute the create_plan command
        3.  Execute the run_plan command and wait for successful plan execution
        4.  Check test model items are removed

        Expected Result
        The model items associated with the successful tasks will be set to an
        Applied state while the model items associated with the failed tasks
        will remain in an unchanged state.
        """
        self._install_plugins()

        self.litp.create("/software/items/test_item01", self.plugin,
                         "name=test_05_01")
        self.litp.create("/software/items/test_item02", self.plugin,
                         "name=test_05_02")
        self.litp.create("/software/items/test_item03", self.plugin,
                         "name=test_05_03")
        self.litp.create("/software/items/test_item04", self.plugin,
                         "name=test_05_04")

        self.litp.create_plan()
        show_plan = self.litp.show_plan()[0]
        self.assertTrue(self.is_text_in_list("Callback test_05_01", show_plan))
        self.assertTrue(self.is_text_in_list("Callback test_05_04", show_plan))

        self.rest.run_plan_rest()
        self.rest.wait_for_plan_state_rest(test_constants.PLAN_FAILED)

        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item01"))
        self.assertEquals('Applied',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item02"))
        self.assertEquals('Initial (deployment of properties indeterminable)',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item03"))
        self.assertEquals('Initial (deployment of properties indeterminable)',
                          self.get_item_state(self.test_ms,
                                              "/software/items/test_item04"))
