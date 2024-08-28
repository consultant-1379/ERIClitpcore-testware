'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2014
@author:    Ares
@summary:   Integration test for LITPCDS-4429
            Agile:
                Epic: N/A
                Story: LITPCDS-4429
                Sub-Task:
'''

import os
import test_constants
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils


class Story4429(GenericTest):
    """
    LITPCDS-4429:
    As a LITP Developer, I want the model to support task ordering on a
    per-node basis, so that my tasks are correctly ordered using a minimal
    number of node locks.
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story4429, self).setUp()
        self.management_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()
        self.log_path = test_constants.GEN_SYSTEM_LOG_PATH
        self.manifests = test_constants.PUPPET_MANIFESTS_DIR
        self.plugin_id = 'story4429'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""

        # call super class teardown
        super(Story4429, self).tearDown()

    def _check_item_type_registered(self):
        """check model item type extension registered with litp"""

        expected_match = [
            'INFO: Added ModelExtension: \\"{0}'.format(self.plugin_id),
            'INFO: Added Plugin: \\"{0}'.format(self.plugin_id)
        ]

        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(self.log_path, expected_match)
        )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

    @staticmethod
    def get_local_rpm_paths(path, rpm_substring):
        """
        given a path (which should contain some rpms) and a substring
        which is present in the rpm names you want, return a list of
        absolute paths to the rpms that are local to your test
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_substring in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
        ]

    def _install_item_type_extension(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """

        # since the copy_and_install_rpms method in the framework, doesn't
        # check if the package is already installed, we must check if the
        # package does indeed need to be installed - if we don't, and the
        # package is installed, the test will fail
        _, _, rcode = self.run_command(
            self.management_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths
                )
            )
            self._check_item_type_registered()

    def _get_expected_message(self, filepath, expected, test_log_len=-1):
        """get expected message from log from plugin execution"""

        if filepath == self.log_path:
            # check /var/log/messages for the expected message
            if test_log_len != -1:
                stdout, stderr, rcode = self.run_command(
                    self.management_node,
                    self.rhc.get_grep_file_cmd(
                        filepath, expected,
                        file_access_cmd='/usr/bin/tail -n {0}'.format(
                            test_log_len
                        )
                    )
                )
            else:
                stdout, stderr, rcode = self.run_command(
                    self.management_node,
                    self.rhc.get_grep_file_cmd(filepath, expected)
                )
        else:
            stdout, stderr, rcode = self.run_command(
                self.management_node,
                self.rhc.get_grep_file_cmd(filepath, expected)
            )
        self.assertEqual(0, rcode)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)

    def _create_model_items(self, test_name, item_type):
        """create model items for test in litp model"""

        # get software item url
        software_item = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]
        # create the test model item
        model_item = os.path.join(software_item, item_type)
        self.execute_cli_create_cmd(
            self.management_node, model_item, item_type,
            'name=\'{0}\''.format(test_name)
        )
        # get all nodes
        nodes = self.find(self.management_node, '/deployments', 'node')
        nodes.append('/ms')
        # reference model item to nodes
        for node in nodes:
            node_item = self.find(
                self.management_node, node, 'software-item', False,
                find_refs=True
            )[0]
            reference_item = os.path.join(node_item, item_type)
            self.execute_cli_inherit_cmd(
                self.management_node, reference_item, model_item
            )

    def _get_task_index(self, task_type, task_name):
        """get the index of the task from the show_plan output"""

        # get the output of show_plan
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        # get number of phases in plan from output
        number_phases_plan = self.cli.get_num_phases_in_plan(stdout)
        # go through each phase
        for phase in range(0, number_phases_plan):
            if phase + 1 == number_phases_plan:
                phase_ = number_phases_plan
            else:
                phase_ = phase + 1
            # get number of tasks
            number_tasks_phase = self.cli.get_num_tasks_in_phase(
                stdout, phase_
            )
            # for each task in the phase
            for task in range(0, number_tasks_phase):
                if task + 1 == number_tasks_phase:
                    task_ = number_tasks_phase
                else:
                    task_ = task + 1
                # get description of task
                task_description = self.cli.get_task_desc(
                    stdout, phase_, task_
                )
                # if task description matches the description lookup string,
                # get the index of the line from show_plan output
                if task_type in task_description[1] and \
                        task_name in task_description[1]:
                    line = [
                        line for line in stdout if task_description[1] in line
                    ][0]

                    return stdout.index(line)

        return -1

    #@attr('all', 'non-revert')
    def obsolete_01_n_ordered_task_list_validation(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_01_n_ordered_task_list_validation.at

        Description:
            Given a LITP deployment, when a create_plan command is executed and
            an OrderedTaskList() is returned from a plugin, if the list
            contains tasks for multiple nodes, then validation will fail.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return an OrderedTaskList() with tasks for
                multiple node
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check for error/exception message in /var/log/messages

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            Validation must fail on plan creation and an error/exception must
            be logged in /var/log/messages.
        """

        self._install_item_type_extension()
        self._create_model_items('test_01', self.plugin_id)
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InternalServerError', stderr)
        )
        self._get_expected_message(
            self.log_path,
            ['OrderedTaskList can only contain tasks for the same node']
        )

    #@attr('all', 'non-revert')
    def obsolete_02_p_task_dependencies(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/test_02_p_task_dependencies.at

        Description:
            Given a LITP deployment, when a create_plan command is executed and
            a plugin returns tasks with dependencies set up for other tasks,
            the created plan will preserve the dependencies and ensure that the
            required dependencies are executed first.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires TaskB
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check TaskB will be executed before TaskA

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            show_plan output shows TaskB will be executed before TaskA
        """

        self._install_item_type_extension()
        self._create_model_items('test_02', self.plugin_id)
        self.execute_cli_createplan_cmd(self.management_node)
        taska_index = self._get_task_index('CallbackTask()', 'TaskA')
        taskb_index = self._get_task_index('CallbackTask()', 'TaskB')
        self.assertTrue(taskb_index < taska_index)

    #@attr('all', 'non-revert')
    def obsolete_03_n_task_cyclic_dependency(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/test_03_n_task_cyclic_dependency.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks with dependencies set up for other
            tasks, in such a way as to create a cyclic dependency, then
            validation must fail.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return task dependencies in the form of
                TaskA requires TaskB requires TaskC requires TaskA
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check for error/exception message in /var/log/messages

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            Validation must fail on plan creation and an error/exception must
            be logged in /var/log/messages.
        """

        self._install_item_type_extension()
        self._create_model_items('test_03', self.plugin_id)
        start_log_position = self.get_file_len(
            self.management_node, self.log_path
        )
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )
        end_log_position = self.get_file_len(
            self.management_node, self.log_path
        )
        test_logs_len = end_log_position - start_log_position
        self.assertTrue(
            self.is_text_in_list('InternalServerError', stderr)
        )
        self._get_expected_message(
            self.log_path,
            ['A cyclic dependency exists in graph'], test_logs_len
        )

    #@attr('all', 'non-revert')
    def obsolete_04_n_ordered_task_list_cyclic_dependencies(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_04_n_ordered_task_list_cyclic_dependencies.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns an OrderedTaskList() that contains tasks with
            dependencies set up for other tasks, within the same ordered task
            list, then *validation must fail.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return an OrderedTaskList() where Task A in
                list depends on TaskB in list
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check for error/exception message in /var/log/messages

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            Validation must fail on plan creation and an error/exception must
            be logged in /var/log/messages.
        """

        self._install_item_type_extension()
        self._create_model_items('test_04', self.plugin_id)
        start_log_position = self.get_file_len(
            self.management_node, self.log_path
        )
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )
        end_log_position = self.get_file_len(
            self.management_node, self.log_path
        )
        test_logs_len = end_log_position - start_log_position
        self.assertTrue(
            self.is_text_in_list('InternalServerError', stderr)
        )
        self._get_expected_message(
            self.log_path,
            ['A cyclic dependency exists in graph'], test_logs_len
        )

    #@attr('all', 'non-revert')
    def obsolete_05_p_task_depends_on_ordered_task_list_task(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_05_p_task_depends_on_ordered_task_list_tas.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on tasks contained within an
            OrderedTaskList(), then the created plan will *preserve the
            dependencies and ensure that the required dependencies are executed
            first.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires TaskB
                which is an OrderedTaskList() of [TaskC, TaskB]
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check TaskC will be executed before TaskB and TaskB will be
                executed before TaskA

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            show_plan output shows TaskB will be executed before TaskA and
            TaskC will be executed before TaskB
        """

        self._install_item_type_extension()
        self._create_model_items('test_05', self.plugin_id)
        self.execute_cli_createplan_cmd(self.management_node)
        taska_index = self._get_task_index('CallbackTask()', 'TaskA')
        taskb_index = self._get_task_index('CallbackTask()', 'TaskB')
        taskc_index = self._get_task_index('CallbackTask()', 'TaskC')
        self.assertTrue(taskb_index < taskc_index)
        self.assertTrue(taskc_index < taska_index)
        self.assertTrue(taskb_index < taska_index)

    #@attr('all', 'non-revert')
    def obsolete_06_n_task_depends_on_query_item_diff_node(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_06_n_task_depends_on_query_item_diff_node.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on tasks from the query item
            of a different node, validation must fail.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires the query
                item of TaskB that is hanging off a separate node
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check for error/exception message in /var/log/messages

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            Validation must fail on plan creation and an error/exception must
            be logged in /var/log/messages.
        """

        self._install_item_type_extension()
        self._create_model_items('test_06', self.plugin_id)
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InternalServerError', stderr)
        )
        self._get_expected_message(
            self.log_path, ['required item relates to a different node']
        )

    # @attr('all', 'non-revert')
    def obsolete_07_p_task_depends_on_query_item_call_type_call_id(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                test_07_p_task_depends_on_query_item_call_type_call_id.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on another task's (OR
            plugin's) query item and call_type, call_id tuple, hen the created
            plan will preserve the dependencies and ensure that the required
            dependencies are executed first.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires query
                item of TaskB and its call_type, call_id tuple
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check TaskB will be executed before TaskA

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            show_plan output shows TaskB will be executed before TaskA
        """

        self._install_item_type_extension()
        self._create_model_items('test_07', self.plugin_id)
        self._create_model_items('test_07', '{0}-1'.format(self.plugin_id))
        self.execute_cli_createplan_cmd(self.management_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        self.assertTrue(
            self.is_text_in_list('ConfigTask() TaskA', stdout)
        )
        self.assertTrue(
            self.is_text_in_list('ConfigTask() TaskB', stdout)
        )
        taska_index = self._get_task_index('ConfigTask()', 'TaskA')
        node_hostname = stdout[taska_index].split(':')[-1]
        self.execute_cli_runplan_cmd(self.management_node)
        self.wait_for_plan_state(
            self.management_node, test_constants.PLAN_COMPLETE
        )
        self._get_expected_message(
            os.path.join(self.manifests, '{0}.pp'.format(node_hostname)),
            ['require => \\[Class', 'notify__cf__do__nothing__test__07__']
        )

    #@attr('all', 'non-revert')
    def obsolete_08_p_task_depends_on_query_item_only(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_08_p_task_depends_on_query_item_only.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on another task's (OR
            plugin's) query item,then the created plan will preserve the
            dependencies and ensure that the required dependencies are executed
            first.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires query
                item of TaskB
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check TaskB will be executed before TaskA

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            show_plan output shows TaskB will be executed before TaskA
        """

        self._install_item_type_extension()
        self._create_model_items('test_08', self.plugin_id)
        self._create_model_items('test_08', '{0}-1'.format(self.plugin_id))
        self.execute_cli_createplan_cmd(self.management_node)
        taska_index = self._get_task_index('ConfigTask()', 'TaskA')
        taskb_index = self._get_task_index('CallbackTask()', 'TaskB')
        self.assertTrue(taskb_index < taska_index)
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.management_node, test_constants.PLAN_COMPLETE
            )
        )

    #@attr('all', 'non-revert')
    def obsolete_09_n_task_depends_on_call_type_no_call_id(self):
        """
        Obsoleted:
            replaced with AT:
            ERIClitpcore/ats/Story_4429/\
                    test_09_n_task_depends_on_call_type_no_call_id.at

        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on another task's (OR
            plugin's) call_type and call_id tuple, if either call_type or
            call_if are missing, then the created plan will fail validation.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires a
                call_type, call_id tuple with a missing call_id
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check for error/exception message in /var/log/messages

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            Validation must fail on plan creation and an error/exception must
            be logged in /var/log/messages.
        """

        self._install_item_type_extension()
        self._create_model_items('test_09', self.plugin_id)
        self._create_model_items('test_09', '{0}-1'.format(self.plugin_id))
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.management_node, expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InternalServerError', stderr)
        )
        self._get_expected_message(
            self.log_path,
            ['invalid task dependency: notify']
        )

    @attr('all', 'non-revert')
    def test_10_p_task_depends_on_own_query_item(self):
        """
        Description:
            Given a LITP deployments, when a create_plan command is executed
            and a plugin returns tasks that depend on another task's (OR
            plugin's) call_type, call_id tuple, then the created plan will
            preserve the dependencies and ensure that the required dependencies
            are executed first.

        Pre-Requisites:
            1. A running litpd service

        Risks:
            Once a plugin/extension package is installed, it cannot be removed

        Pre-Test Steps:
            1.  Create a new dummy extension as described in the LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to return a task where TaskA requires the
                call_type, call_id tuple of TaskB
            4.  Build and install the extension package
            5.  Build and install the plugin package

        Steps:
            1.  Execute the CLI create command to create an item type
            2.  Execute the CLI inherit command to reference the item type to
                the nodes
            3.  Execute the CLI create_plan command
            4.  Check TaskB will be executed before TaskA

        Restore:
            1.  Execute the CLI remove command to remove the item type and its
                references

        Expected Result:
            show_plan output shows TaskB will be executed before TaskA
        """

        self._install_item_type_extension()
        self._create_model_items('test_10', self.plugin_id)
        self.execute_cli_createplan_cmd(self.management_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.management_node)
        self.assertTrue(
            self.is_text_in_list('ConfigTask() TaskA', stdout)
        )
        self.assertFalse(
            self.is_text_in_list('ConfigTask() TaskB', stdout)
        )
        self.assertFalse(
            self.is_text_in_list('ConfigTask() TaskC', stdout)
        )
        self.assertFalse(
            self.is_text_in_list('CallbackTask() TaskA', stdout)
        )
        self.assertFalse(
            self.is_text_in_list('CallbackTask() TaskB', stdout)
        )
        self.assertFalse(
            self.is_text_in_list('CallbackTask() TaskC', stdout)
        )
