"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2014
@author:    Ares
@summary:   Integration test for LITPCDS-5890
            Agile:
                Epic: N/A
                Story: N/A
                Sub-Task: N/A
"""

import os
import collections
import test_constants
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
from rest_utils import RestUtils
from vcs_utils import VCSUtils


class Story5890(GenericTest):
    """
    LITPCDS-5890:
    When a node Unlock task fails I want the next plan run to identify that a
    Node with no model updates is in an locked state and needs to be unlocked.
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story5890, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip_address = self.get_node_att(self.ms_node, 'ipv4')
        self.cli = CLIUtils()
        self.rhc = RHCmdUtils()
        self.rest = RestUtils(self.ms_ip_address)
        self.vcs = VCSUtils()
        self.backup_path = '/tmp'
        self.xml_filepath = 'xml_files'
        self.xml_filename = '{0}_story5890.xml'
        self.package = 'nonexistentpackage'
        self.lock_path = '/opt/VRTSvcs/bin/haconf'
        self.node_locked = 1
        self.node_unlocked = 0

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""

        # call super class teardown
        super(Story5890, self).tearDown()

    def _copy_file_to(self):
        """Copies file to location specified by xml_filename & xml_filepath."""
        self.copy_file_to(
            self.ms_node,
            os.path.abspath(
                os.path.join(
                    os.path.join(os.path.dirname(__file__), self.xml_filepath),
                    self.xml_filename.format('node_load')
                )
            ),
            self.backup_path, root_copy=True
        )

    def _get_nodes_from_model(self, req='all'):
        """Returns a list of node locations in the model."""
        nodes = self.find(self.ms_node, '/deployments', 'node')
        if req != 'all':
            return nodes[0:int(req)]
        return nodes

    def _chk_expected_property_value(self, url, proprty, expect):
        """Tests if the passed parameters match the expected properties."""
        self.assertEqual(
            expect,
            self.execute_show_data_cmd(self.ms_node, url, proprty)
        )

    def _get_hostname_from_node_url(self, node):
        """Returns a string hostname for the given node url."""
        return self.execute_show_data_cmd(
            self.ms_node, node, 'hostname'
        )

    def _get_hastatus_on_node(self, node):
        """Executes hasstatus command on node and returns hasstatus int."""
        node_hastatus = -1
        node_filename = self.get_node_filename_from_url(self.ms_node, node)
        stdout, stderr, rcode = self.run_command(
            node_filename, self.vcs.get_hastatus_sum_cmd(), su_root=True)
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)
        hostname = self.get_node_att(node_filename, 'hostname')
        for line in stdout:
            if 'A  {0}'.format(hostname) in line:
                node_hastatus = int(line.split(' ')[-1])
        return node_hastatus

    def _get_first_task_in_plan(self, stdout):
        """Returns task object which is at the top of the plan."""
        return self.cli.parse_plan_output(stdout)[1][1]

    def _get_last_task_in_plan(self, stdout):
        """Returns task object which is at the bottom of the plan."""
        phase = self.cli.get_num_phases_in_plan(stdout)
        task = self.cli.get_num_tasks_in_phase(stdout, phase)
        plan_d = self.cli.parse_plan_output(stdout)
        return plan_d[phase][task]

    def _get_relevant_task_from_plan(self, stdout, nodes, lookup):
        """
        Return first task object in the plan that matches lookup parameter.
        """
        hostnames = collections.OrderedDict()
        task_index = -1
        for node in nodes:
            hostname = self._get_hostname_from_node_url(node)
            hostnames[hostname] = node
        for line in stdout:
            if lookup in line:
                task_index = stdout.index(line)
                break
        for hostname in hostnames.keys():
            if hostname in stdout[task_index]:
                relevant_task = stdout[task_index]
                relevant_node = hostnames[hostname]
        return relevant_node, relevant_task

    def _get_task_state_from_plan(self, lookup):
        """Returns a string of the task state which matches lookup paramter."""
        task_state = ''
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        plan_d = self.cli.parse_plan_output(stdout)
        for phase in plan_d.keys():
            for task in plan_d[phase].keys():
                for desc in plan_d[phase][task]['DESC']:
                    if lookup in desc:
                        task_state = plan_d[phase][task]['STATUS']
        return task_state

    def _find_all_specific_tasks_in_plan(self, stdout, description, node_path):
        """Searches through the plan and returns a list of matching tasks."""
        matching_tasks = []
        plan_d = self.cli.parse_plan_output(stdout)
        for phase in plan_d.keys():
            for task in plan_d[phase].keys():
                # Only find matching tasks
                desc = plan_d[phase][task]['DESC']
                if description in desc and node_path in desc:
                    matching_tasks.append(plan_d[phase][task])
        return matching_tasks

    def _manual_unlock(self, node):
        """Manually unlock node."""
        node_hostname = self._get_hostname_from_node_url(node)
        node_filename = self.get_node_filename_from_url(self.ms_node,
                                                        node)
        cmd1 = "haconf -makerw"
        cmd2 = "hasys -unfreeze -persistent " + node_hostname
        cmd3 = "haconf -dump"
        for cmd in [cmd1, cmd2, cmd3]:
            self.run_command(node_filename, cmd, su_root=True)

    def _assert_nodes_unlocked(self, nodes, ignore_node=None):
        """Test if all nodes (except ignored if inclued) are unlocked."""

        for node in nodes:
            if node != ignore_node:
                self._chk_expected_property_value(node, 'is_locked', 'false')
                self.assertEqual(0, self._get_hastatus_on_node(node))

    def _create_package(self, package_name, version=None, release=None,
                        expected_state=True):
        """Executes litp command to create a given package."""
        items = self.find(self.ms_node, "/software", "software-item", False)
        items_path = items[0]
        package_url = os.path.join(items_path, package_name)
        props = "name='{0}'".format(package_name)
        if version:
            props += " version={0}".format(version)
        if release:
            props += " release={0}".format(release)

        self.execute_cli_create_cmd(
            self.ms_node,
            package_url,
            "package",
            props,
            args="",
            expect_positive=expected_state)

        return package_url

    def _create_package_inherit(self, node_url, package_name, source_url):
        """Executes litp inherit command for a given package."""
        node_sw_ref = self.find(self.ms_node,
                                node_url,
                                'software-item',
                                False, find_refs=True,
                                exclude_services=True)[0]

        self.execute_cli_inherit_cmd(
            self.ms_node,
            os.path.join(node_sw_ref, package_name),
            source_url
        )

    def _assert_lock_task_on_top(self, stdout):
        """Tests if the first task in a plan is an lock task."""
        self.assertTrue(
            self.is_text_in_list("Lock VCS",
                                 self.
                                 _get_first_task_in_plan(stdout)['DESC']))

    def _assert_unlock_task_on_top(self, stdout):
        """Tests if the first task in a plan is an unlock task."""
        self.assertTrue(
            self.is_text_in_list(
                'Unlock VCS', self.
                _get_first_task_in_plan(stdout)['DESC']))

    def _assert_plan_failed(self):
        """Tests if the plan has failed."""
        self.assertTrue(self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_FAILED))

    def _fail_plan_leaving_locked_node(self, nodes):
        """Creates, runs and fails a plan leaving a node in a locked state."""
        pkg_url = self._create_package(package_name=self.package,
                                       version='5.6', release='el6')
        # Create task to install non-existent package, to fail plan
        for node in nodes:
            self._create_package_inherit(node, self.package, pkg_url)

        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self._assert_lock_task_on_top(stdout)

        node_r, task_r = (self.
                          _get_relevant_task_from_plan(stdout, nodes,
                                                       'Install package "{0}"'.
                                                       format(self.package)))
        self.execute_cli_runplan_cmd(self.ms_node)
        self._assert_plan_failed()
        self.assertEqual('Failed', self._get_task_state_from_plan(task_r))

        return node_r

    def _remove_software_from_nodes(self, nodes):
        """Removes any software objects from the nodes."""
        for node in nodes:
            items = self.find(self.ms_node, node, 'software-item', False,
                              find_refs=True, exclude_services=True)
            item_url = os.path.join(items[0], self.package)
            self.execute_cli_remove_cmd(self.ms_node, item_url)

    def _remove_snapshot(self):
        """Executes remove snapshot, then creates plan to create snapshot."""
        # Remove existing snapshot . . .
        self.execute_cli_removesnapshot_cmd(self.ms_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_COMPLETE
            )
        )
        # . . . then create plan, will will create new snapshot
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        task_r = self._get_first_task_in_plan(stdout)

        # Make sure the unlock task is there ...
        self.assertTrue(self.is_text_in_list("Unlock VCS", task_r["DESC"]))

        # ... and make sure the entire plan is successfull
        self.assertTrue(
            self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_COMPLETE
            )
        )

    def _dummy_locking_cmds(self, node_filename):
        """Replaces the locking cmds for a node with one that will fail."""
        # Move existing locking cmd
        self.mv_file_on_node(node_filename, self.lock_path,
                             self.lock_path + "_old", '-f', True, False)
        # Create new locking commands that will fail
        file_contents = ["#!/bin/bash", "echo \"Dummy lock failure\" >&2",
                         "exit 93"]
        create_success = self.create_file_on_node(
                node_filename, self.lock_path, file_contents,
                su_root=True, add_to_cleanup=False)
        self.assertTrue(create_success, "File could not be created")

        cmd = "/bin/chmod +x " + self.lock_path
        _, err, ret_code = self.run_command(node_filename, cmd,
                                            su_root=True)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)

    def _fix_locking_cmds(self, node_filename, assert_ret=True):
        """Reverts the changed locking cmds to original working order."""
        cmd = self.rhc.get_move_cmd((self.lock_path + "_old"), self.lock_path)
        _, err, ret_code = self.run_command(node_filename, cmd, su_root=True)
        if assert_ret:
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

    def _dummy_lock_while_task_runs(self, node_filename, task):
        """
        execute the dummy locking when the specified tasks begins execution
        """
        self.assertTrue(
            self.wait_for_task_state(
                self.ms_node, task, test_constants.PLAN_TASKS_RUNNING, False
            )
        )
        self._dummy_locking_cmds(node_filename)

    @attr('all', 'revert', 'story5890', 'story5890_tc01')
    def test_01_n_is_lock_property_not_updatable(self):
        """
        @tms_id: litpcds_5890_tc01
        @tms_requirements_id: LITPCDS-5890
        @tms_title: Verify "is_locked" property is not updateable.
        @tms_description: It must be impossible to update the "is_locked"
            property in any way.
            Also verify story TORF-107192 (test_05_pn_xml_metrics_collection)
        @tms_test_steps:
            @step: Attempt update of is_locked property using CLI
            @result: The property is not updateable
            @step: Attempt update of is_locked property using XML
            @result: The property is not updateable
            @step: Attempt update of is_locked property using XML --merge
            @result: The property is not updateable
            @step: Attempt update of is_locked property using XML --replace
            @result: The property is not updateable
            @step: Attempt update of is_locked property using REST
            @result: The property is not updateable
            @step: Check metrics messages and metrics values
            @result: Only expected metrics are present with
                correct values (type):
               '[XML][Import].NoOfModelItems': int,
               '[XML][Import].TimeTaken': float,
               '[XML][Export].NoOfModelItems': int,
               '[XML][Export].TimeTaken': float,
        @tms_test_precondition: Make sure the cluster with two (or more)
            nodes is deployed
            Make sure there's a plugin that will generate node
            lock/unlock tasks
        @tms_execution_type: Automated
        """
        metrics_file_path = '/var/log/litp/metrics.log'
        metrics_file_path_1 = '/var/log/litp/metrics.log.1'
        cursor_metrics = self.get_file_len(self.ms_node, metrics_file_path)

        nodes = self._get_nodes_from_model()
        for node in nodes:
            self._chk_expected_property_value(node, 'is_locked', 'false')
            self.log('info', 'Attempt update of is_locked property using CLI')
            _, stderr, _ = self.execute_cli_update_cmd(
                self.ms_node, node, 'is_locked=\'true\'',
                expect_positive=False
            )
            self.assertTrue(
                self.is_text_in_list('InvalidRequestError', stderr)
            )
            filepath = os.path.join(
                self.backup_path, self.xml_filename.format('node_export')
            )

            stdout, stderr, rcode = self.run_command(
                self.ms_node,
                self.cli.get_xml_export_cmd(node, filepath)
            )
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertEqual([], stdout)
            stdout, stderr, rcode = self.run_command(
                self.ms_node,
                self.rhc.get_grep_file_cmd(
                    filepath, ["property is not updatable"]
                )
            )
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)
            self.assertTrue(self.is_text_in_list('is_locked', stdout))
        self._copy_file_to()
        filepath = os.path.join(
            self.backup_path, self.xml_filename.format('node_load')
        )
        stdout, stderr, rcode = self.run_command(
            self.ms_node,
            self.rhc.get_grep_file_cmd(
                filepath, ["property is not updatable"]
            )
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)
        # XML file contains is_locked=true but should be ignored upon load;
        # creation of new nodes should always be is_locked=false
        self.assertTrue(
            self.is_text_in_list('<is_locked>true', stdout)
        )
        parent_url = self.get_parent_path(nodes[0])
        test_node_url = self.find(
            self.ms_node, "/deployments", "node", True)[0]

        self.log('info', 'Attempt update of is_locked property using XML')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.ms_node, parent_url, filepath, expect_positive=False)
        # check the is_locked property is set to False even though the XML
        # file has it set to true (including --merge/--replace)
        self._chk_expected_property_value(
            test_node_url, 'is_locked', 'false'
        )
        self.assertTrue(
                self.is_text_in_list('ItemExistsError', stderr)
            )
        self.log('info', 'Attempt update of is_locked property using XML')
        self.execute_cli_load_cmd(
            self.ms_node, parent_url, filepath, '--merge'
        )
        self._chk_expected_property_value(
            test_node_url, 'is_locked', 'false'
        )
        self.log('info', 'Attempt update of is_locked property using '
                 'XML --REPLACE')
        self.execute_cli_load_cmd(
            self.ms_node, parent_url, filepath, '--replace'
        )
        self._chk_expected_property_value(
            test_node_url, 'is_locked', 'false'
        )
        self.log('info', 'Attempt update of is_locked property using REST')
        stdout, stderr, rcode = self.rest.put(
            nodes[0], self.rest.HEADER_JSON,
            '{"properties": {"is_locked": "true"}}'
        )
        self.assertEqual(422, rcode)
        self.assertEqual('', stderr)
        self.assertNotEqual('', stdout)
        self.assertTrue('InvalidRequestError' in stdout)
        stdout, stderr, rcode = self.rest.put(
            test_node_url, self.rest.HEADER_JSON,
            '{"properties": {"is_locked": "true"}}'
        )
        self.assertEqual(422, rcode)
        self.assertEqual('', stderr)
        self.assertNotEqual('', stdout)
        self.assertTrue('InvalidRequestError' in stdout)
        self.log('info', 'Check metrics messages and metrics values')
        self.log('info', 'Check "import_iso" metrics')
        lines = self.wait_for_log_msg(self.ms_node,
                                      'XML',
                                      log_file=metrics_file_path,
                                      timeout_sec=10,
                                      log_len=cursor_metrics,
                                      rotated_log=metrics_file_path_1,
                                      return_log_msgs=True)

        actual_metrics = {}
        for line in lines:
            parts = line.split('=')
            actual_metrics[parts[0]] = parts[1]

        expected_metrics = {
           '[XML][Import].NoOfModelItems': int,
           '[XML][Import].TimeTaken': float,
           '[XML][Export].NoOfModelItems': int,
           '[XML][Export].TimeTaken': float,
        }

        for exp_key, exp_type in expected_metrics.iteritems():
            for act_key, act_val in actual_metrics.iteritems():
                if act_key.endswith(exp_key):
                    try:
                        act_val = exp_type(act_val)
                    except ValueError:
                        act_val = None
                    self.assertNotEqual(None, act_val,
                                        'Wrong value type for metric "{0}"'.
                                        format(exp_key))
                    break
            else:
                self.fail('Metrics not found for "{0}"'.format(exp_key))

    # @attr('pre-reg', 'revert')
    def obsolete_02_n_fail_standard_task(self):
        """
        Obsoleted:
        replaced with AT:
        ERIClitpcore/ats/plan/node_lock/node_lock_config_task.at

        Test Description
        Given a plan with lock/unlock tasks is run when a standard task on a
        locked node fails then the plan execution will fail and the subsequent
        plan will contain an unlock task for the node locked in previous plan.

        Pre-Requisites
        A running litpd service

        Pre-Test Steps
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks

        Steps:
        1.  Execute the cli create command to create a test item in the model
        2.  Execute the cli inherit command to inherit the test item to a
            node(s)
        3.  Execute the cli create_plan command (Make sure lock tasks are
            around the task that's about to be failed)
        4.  Execute the cli run_plan command
        5.  Check the plan execution fails on one of the locked nodes
        6.  Check /var/log/messages for logged exception
        7.  Execute show command on a node item and verify it is not locked
            - is_locked property is true
        8.  Execute the cli create_plan command
        9.  Execute the cli show_plan command to verify the unlock task is on
            top of the plan (in Phase 1) and that all the others tasks that
            weren't run successfully in previous plan are there

        Restore
        1.  Execute the cli remove command on the test item reference under the
            node(s)
        2.  Execute the cli remove command on the test item
        3.  Execute the cli create_plan command
        4.  Execute the cli run_plan command to have the node unlocked

        Expected Result
        The subsequent plan will contain an unlock task for the node locked in
        previous plan.
        """
        nodes = self._get_nodes_from_model()
        self._fail_plan_leaving_locked_node(nodes)
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertTrue(
            self.is_text_in_list(
                "Unlock VCS",
                self._get_first_task_in_plan(stdout)['DESC']
            )
        )

    def obsolete_03_n_fail_unlock_task(self):
        """
        Obsoletd:
        Covered by: test_11_n_fail_unlock_lock_tasks
        Description:
        Given a plan with lock/unlock tasks is run when a unlock task on a
        locked node fails then the plan execution will fail and the subsequent
        plan will contain an unlock task for the node locked in previous plan.

        Pre-Requisites:
        A running litpd service

        Pre-Test Steps:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks
        Make sure that unlock task is going to fail

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command (Make sure lock tasks are
                around the task that's about to be failed)
            4.  Execute the cli run_plan command
            5.  Check the plan execution fails on one of the locked nodes
            6.  Check /var/log/messages for logged exception
            7.  Execute show command on a node item and verify it is not locked
                - is_locked property is true
            8.  Execute the cli create_plan command
            9.  Execute the cli show_plan command to verify the unlock task is
                on top of the plan (in Phase 1) and that all the others tasks
                that weren't run successfully in previous plan are there

        Restore:
            1.  Execute the cli remove command on the test item reference under
                the node(s)
            2.  Execute the cli remove command on the test item
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command to have the node unlocked

        Expected Result:
        The subsequent plan will contain an unlock task for the node locked in
        previous plan.
        """

        nodes = self._get_nodes_from_model()
        pkg_url = self._create_package(package_name='telnet')
        for node in nodes:
            # Create simple plan and fail lock task
            self._create_package_inherit(node, 'telnet', pkg_url)
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        node_r, task_r_unlck = self._get_relevant_task_from_plan(stdout,
                                                                 nodes,
                                                                 'Unlock VCS')
        node_filename = self.get_node_filename_from_url(self.ms_node,
                                                        node_r)
        _, task_r_pkg = self._get_relevant_task_from_plan(stdout, [node_r],
                                                          'Install package')
        try:
            self.execute_cli_runplan_cmd(self.ms_node)
            self._dummy_lock_while_task_runs(node_filename, task_r_pkg)
            self._assert_plan_failed()
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertEqual('Failed', self.
                             _get_task_state_from_plan(task_r_unlck))
            self.assertEqual(self.node_locked,
                             self._get_hastatus_on_node(node_r))
            self._assert_nodes_unlocked(nodes, node_r)
            self.execute_cli_createplan_cmd(self.ms_node)
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            self._assert_unlock_task_on_top(stdout)
        finally:
            self._fix_locking_cmds(node_filename, False)
            self.run_command(self.ms_node, self.cli.get_run_plan_cmd())
            self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE)

    def obsolete_04_n_fail_unlock_task_is_last_task_in_plan(self):
        """
        Obsoleted:
        Covered by: test_11_n_fail_unlock_lock_tasks
        Description:
        Given a plan with lock/unlock tasks is run when a unlock task on a
        locked node fails and this unlock task is the last task in a plan
        then the plan execution will fail and the subsequent plan will consist
        only of one unlock task for the node locked in previous plan.

        Pre-Requisites:
        A running litpd service

        Pre-Test Actions:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks
        Make sure that unlock task is going to fail

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command (Make sure lock tasks are
                around the task that's about to be failed)
            4.  Execute the cli run_plan command
            5.  Check the plan execution fails on the very last task which is
                an unlock task
            6.  Check /var/log/messages for logged exception
            7.  Execute show command on a node item and verify it is not locked
                - is_locked property is true
            8.  Execute the cli create_plan command
            9.  Execute the cli show_plan command to verify the unlock task is
                on top of the plan (in Phase 1) and that this is the only task
                within a plan.

        Restore:
            1.  Execute the cli remove command on the test item reference under
                the node(s)
            2.  Execute the cli remove command on the test item
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command to have the node unlocked

        Expected Result:
        The subsequent plan will contain an unlock task for the node locked in
        previous plan
        """

        nodes = self._get_nodes_from_model()
        node = nodes[0]
        node_filename = self.get_node_filename_from_url(
                self.ms_node, node)
        pkg_url = self._create_package(package_name='telnet')
        self._create_package_inherit(node, 'telnet', pkg_url)
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        last_task_desc = self._get_last_task_in_plan(stdout)['DESC']
        _, task_r_unlck = self._get_relevant_task_from_plan(stdout, [node],
                                                            'Unlock VCS')
        _, task_r_pkg = self._get_relevant_task_from_plan(stdout, [node],
                                                          'Install package')
        self.assertEqual(task_r_unlck, last_task_desc[1])
        try:
            self.execute_cli_runplan_cmd(self.ms_node)
            self._dummy_lock_while_task_runs(node_filename, task_r_pkg)
            self._assert_plan_failed()
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertEqual('Failed',
                             self._get_last_task_in_plan(stdout)['STATUS'])
            self.assertEqual(self.node_locked,
                             self._get_hastatus_on_node(node))
            self.execute_cli_createplan_cmd(self.ms_node)
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            self._assert_unlock_task_on_top(stdout)
        finally:
            self._fix_locking_cmds(node_filename, False)
            self.run_command(self.ms_node, self.cli.get_run_plan_cmd())
            self.wait_for_plan_state(self.ms_node,
                                     test_constants.PLAN_COMPLETE)

    def obsolete_05_n_fail_lock_task(self):
        """
        Obsoleted:
        Covered by: test_11_n_fail_unlock_lock_tasks
        Description:
        Given a plan with lock/unlock tasks is run  when a lock task fails
        then the plan execution will fail and the node is not locked and
        subsequent plan does not contain an unlock task for this node in
        Phase 1

        Pre-Requisites:
        A running litpd service

        Pre-Test Actions:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks
        Make sure that lock task is going to fail

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command (Make sure lock tasks are
                around the task that's about to be failed)
            4.  Execute the cli run_plan command
            5.  Check the plan execution fails on a lock task
            6.  Check /var/log/messages for logged exception
            7.  Execute the cli create_plan command
            8.  Execute show command on a node item and verify it is not locked
                - is_locked property is false
            9.  Execute the cli show_plan command to verify there's no unlock
                task for a node in Phase 1

        Restore:
            1.  Execute the cli remove command on the test item reference under
                the node(s)
            2.  Execute the cli remove command on the test item
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command to have the node unlocked

        Expected Resuls:
        Subsequent plan will not require unlock task at the top of plan
        """
        nodes = self._get_nodes_from_model()
        node = nodes[0]
        node_filename = self.get_node_filename_from_url(
                self.ms_node, nodes[0])
        try:
            # Create simple plan and fail lock task
            self._dummy_locking_cmds(node_filename)
            pkg_url = self._create_package(package_name='telnet')
            self._create_package_inherit(node, 'telnet', pkg_url)
            self.execute_cli_createplan_cmd(self.ms_node)
            self.execute_cli_runplan_cmd(self.ms_node)
            self._assert_plan_failed()
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            task_r = self._get_relevant_task_from_plan(stdout, nodes,
                                                       'Lock VCS')
            self.assertEqual('Failed',
                             self._get_task_state_from_plan(task_r[1]))
            self._assert_nodes_unlocked(nodes)
            # LITPCDS-9805 Check that the
            # "applied_properties_indeterminable" flag is set to "true"
            # when a node locking task fails
            stdout, stderr, status = self.rest.get(node)
            self.assertEqual("", stderr)
            self.assertEqual(200, status)
            self.assertTrue(
                    '"applied_properties_determinable": true' in stdout)
            self.assertTrue(
                    '"state": "Applied"' in stdout)

            # Assert no unlock task at top of plan
            self.execute_cli_createplan_cmd(self.ms_node)
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
            self.assertFalse(self.is_text_in_list("Unlock VCS",
                                                  self.
                                                  _get_first_task_in_plan
                                                  (stdout)['DESC']))

        finally:
            self._fix_locking_cmds(node_filename, False)

    def obsolete_test_06_p_unlock_task_after_manual_unlock(self):
        """
        #tms_id: litpcds_5890_tc06
        #tms_requirements_id: LITPCDS-5890
        #tms_title: Verify plan has unlock task when the node unlock
            is done manually.
        #tms_description: Given a failed plan that leaves a node locked,
        if the unlock is executed manually on the node,
        then the subsequent plan will have an
        unlock task at the top but it should not fail to update the model even
        though node is already unlocked.
        #tms_test_steps:
            #step: Execute the cli create command to create a test item,
                 inherit it to a node(s) and create and run the plan.
                (the test item causing plan failure when the node is locked)
            #result: The item is created and inherited and the plan is failing
                and the node remaining locked
            #step: Unlock node manually using vcs commands
            #result: The node is unlocked
            #step: Recreate the plan
            #result: Unlock task is present at top
            #step: Run the plan
            #result: Unlock task is successful and is_locked set to false
            #step: Execute the cli create_plan command and verify there's no
                 unlock tasks on in phase 1.
            #result: No tasks are present
        #tms_test_precondition: Make sure the cluster with two (or more)
            nodes is deployed
            Make sure there's a plugin that will generate node
            lock/unlock tasks
        #tms_execution_type: Automated
        """
        pass

    def obsolete_07_p_no_locked_node_on_success_plan(self):
        """
        Obsoleted:
        Check covered in: test_06_p_unlock_task_after_manual_unlock

        Description:
        Given a plan with lock/unlock tasks is run when plan is ran
        successfully then the subsequent plan does not attempt to unlock a node
        in phase 1

        Pre-Requisites:
        A running litpd service

        Pre-Test Actions:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command
            5.  Check the plan finishes successfully
            6.  Execute show command on a node item and verify it is not locked
                - is_locked property is false
            7.  Execute the cli inherit command to inherit some other test item
                to a node(s)
            8.  Execute the cli create_plan command and verify there's no
                unlock tasks on in phase 1.

        Expected Result:
        The plan execution will succeed.The subsequent plan will not
        contain unlock task for the nodes locked in previous plan in phase 1.
        """
        # Create and run a plan with lock tasks which will succeed
        nodes = self._get_nodes_from_model()
        node = nodes[0]
        pkg_url = self._create_package(package_name='telnet')
        self._create_package_inherit(node, 'telnet', pkg_url)
        self.execute_cli_createplan_cmd(self.ms_node)
        self.execute_cli_runplan_cmd(self.ms_node)
        # Assert that the plan ran successfully
        self.assertTrue(
            self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_COMPLETE
            )
        )
        nodes = self._get_nodes_from_model()
        self._assert_nodes_unlocked(nodes)

        # Create another plan and assert there is no unlock task at top
        pkg_url = self._create_package(package_name='finger')
        self._create_package_inherit(node, 'finger', pkg_url)
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertFalse(
            self.is_text_in_list(
                "Unlock VCS",
                self._get_first_task_in_plan(stdout)['DESC']
            )
        )

    # @attr('pre-reg', 'revert')
    def obsolete_08_p_unlock_task_before_snapshot_task(self):
        """
        NB: This test is now obsolete. The restore_snapshot tasks are not
        created by the create_plan automatically anymore.

        Given a failed plan that leaves a node locked, if the snapshots from
        the previous plan are removed, the subsequent plan will have the unlock
        task at the top before any new snapshots are created

        Pre-Requisites
        A running litpd service

        Pre-Test Steps
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks

        Steps
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command
            5.  Check the plan fails
            6.  Remove snapshots from plan run
            7.  Recreate the plan
            8.  Check unlock task before snapshot tasks

        Expected Result
        Unlock task comes before snapshot tasks
        """
        nodes = self._get_nodes_from_model()
        # Create and run plan which will fail, leaving node locked
        self._fail_plan_leaving_locked_node(nodes)
        # Remove snapshot, then create_plan, which will create new snapshot
        self.execute_cli_removesnapshot_cmd(self.ms_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_COMPLETE
            )
        )
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        # Assert unlock task is above snapshot task
        self.assertTrue(
            self.is_text_in_list(
                "Unlock VCS",
                self._get_first_task_in_plan(stdout)['DESC']
            )
        )
        self.assertTrue(
            self.is_text_in_list(
                "snap",
                self.cli.parse_plan_output(stdout)[2][1]['DESC']
            )
        )

    def obsolete_09_p_chk_unlock_tasks_not_run_simultaneously(self):
        """
        Obsoleted:
        Check covered in: testset_story8260.py
        test_01_p_manifest_backup_config_task_fail
        Description:
        Given a failed plan that leaves a node locked, the subsequent plan will
        have an unlock task at the top and the normal lock/unlock tasks in
        their usualy order and only one unlock task can run each time. Tests
        LITPCDS-6170

        Pre-Requisites:
        A running litpd service

        Pre-Test Actions:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command
            5.  Check the plan fails
            6.  Recreate the plan
            7.  Check unlock task is at the top
            8.  Run the plan
            9.  Check that the first unlock task is successful while the rest
               are still initial

        Expected Result:
        No simultaneous task runs
        """
        nodes = self._get_nodes_from_model()
        # Create a failed plan leaving node in locked state
        self._fail_plan_leaving_locked_node(nodes)
        # Create a new plan, which will have unlock task at top
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self._assert_unlock_task_on_top(stdout)
        self.execute_cli_runplan_cmd(self.ms_node)
        self.wait_for_plan_state(
            self.ms_node, test_constants.PLAN_FAILED
        )
        # Get the matching unlock tasks for node1
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        first_unlock_task = self._get_first_task_in_plan(stdout)
        matching_unlock_tasks = \
            self._find_all_specific_tasks_in_plan(stdout,
                                                  first_unlock_task
                                                  ["DESC"][1],
                                                  first_unlock_task['DESC'][0])
        # Assert that the matching unlock tasks have different states
        self.assertTrue(matching_unlock_tasks[0]['STATUS'] !=
                        matching_unlock_tasks[1]['STATUS'])

    def obsolete_10_p_fail_unlock_next_plan_with_no_lock_tasks(self):
        """
        Obsoleted:
        Covered by: test_11_n_fail_unlock_lock_tasks
        Description:
        Given a failed plan that leaves a node locked, if all items added are
        removed from the model, the subsequent plan will contain only one task
        for unlocking the locked node.

        Pre-Requisites:
        A running litpd service

        Pre-Test Actions:
        Make sure the cluster with two (or more) nodes is deployed
        Make sure there's a plugin that will generate node lock/unlock tasks

        Actions:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli inherit command to inherit the test item to a
                node(s)
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command
            5.  Check the plan fails
            6.  Remove all created items from the model tree
            7.  Execute show command on a node item and verify it islocked
                - is_locked property is true
            8.  Execute the cli create_plan command
            9.  Check only unlock task exists in the plan

        Expected Result:
        The subsequent plan will only have an unlock task
        """
        nodes = self._get_nodes_from_model()
        ms_path = self.find(self.ms_node, '/ms', 'ms')[0]
        self._fail_plan_leaving_locked_node(nodes)
        # Remove packages and install telnet on ms (no locking)
        self._remove_software_from_nodes(nodes)
        pkg_url = self._create_package(package_name='telnet')
        self._create_package_inherit(ms_path, 'telnet', pkg_url)
        self.execute_cli_createplan_cmd(self.ms_node)
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        # Assert that unlock task is in phase2 (LITPCDS-12163)
        plan_d = self.cli.parse_plan_output(stdout)
        self.assertTrue(self.is_text_in_list(
                        'Unlock VCS',
                        plan_d[2][1]['DESC']))
        for phase in plan_d.keys():
            for task in plan_d[phase].keys():
                if task != 1:
                    self.assertFalse(
                        self.is_text_in_list(
                                             'Unlock VCS',
                                             plan_d[phase]
                                             [task]['DESC']))

    def obsolete_test_11_n_fail_unlock_lock_tasks(self):
        """
        #tms_id: litpcds_5890_tc11
        #tms_requirements_id: LITPCDS-5890
        #tms_title: Verify unlock/lock behavior when plan fails
            on these tasks. (the test is a combination of merged test cases)
        #tms_description:
            test_03_n_fail_unlock_task
            Description:
            Given a plan with lock/unlock tasks is run when a unlock task on a
            locked node fails then the plan execution will fail and
            the subsequent plan will contain an unlock task for
            the node locked in previous plan.

            test_04_n_fail_unlock_task_is_last_task_in_plan
            Description:
            Given a plan with lock/unlock tasks is run when a unlock task on a
            locked node fails and this unlock task is the last task in a plan
            then the plan execution will fail and the subsequent plan
            will consist only of one unlock task for the node locked
            in previous plan.

            test_05_n_fail_lock_task
            Description:
            Given a plan with lock/unlock tasks is run  when a lock task fails
            then the plan execution will fail and the node is not locked and
            subsequent plan does not contain an unlock task for this node in
            Phase 1

            test_10_p_fail_unlock_next_plan_with_no_lock_tasks
            Description:
            Given a failed plan that leaves a node locked, if all items
            added are removed from the model, the subsequent plan will contain
            only one task for unlocking the locked node

            Verifying bug LITPCDS-9805
        #tms_test_steps:
            #step: Execute the cli create command to create a test item and
                inherit it to a node(s)
                (the test item causing plan failure when the node is locked
                and make sure lock tasks are around the task
                that's about to be failed)
            #result: The item is created and inherited
            #step: Create and run the plan
            #result: The plan is fails on one of the locked nodes
            #step: Execute show command on a node item and verify it is not
                locked - is_locked property is true
            #result: The node is unlocked, and the property value is correct
            #step: LITPCDS-9805 Check that the
                "applied_properties_indeterminable" flag is set to "true"
                when a node locking task fails
            #result: The property value is correct
            #step: Execute the cli create_plan command
            #result: The unlock task is on top of the plan (in Phase 1) and
                that all the others tasks that weren't run successfully
                in previous plan are there
            #step: Run the plan
            #result: Ensure lock task will succeed and ensure the unlock task
                will fail
            #step: Execute show command on a node item and verify it is locked
               - is_locked property is true
            #result: The property value is as expected
            #step: Execute the "create_plan" command
            #result: The unlock task is on top of the plan (in Phase 1) and
                this is the only task within a plan
                Ensure unlock and lock task will succeed
            #step: Run the plan
            #result: Ensure lock task will succeed and ensure the unlock task
                will fail
            #step: Execute show command on a node item and verify it is locked
               - is_locked property is true
            #result: The property value is as expected
            #step: Execute the "create_plan" command
            #result: The unlock task is on top of the plan (in Phase 1) and
                this is the only task within a plan
        #tms_test_precondition: Make sure the cluster with two (or more)
            nodes is deployed
            Make sure there's a plugin that will generate node
            lock/unlock tasks
        #tms_execution_type: Automated
        """
        pass
