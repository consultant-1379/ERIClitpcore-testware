"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2018
@author:    karen.flannery@ammeon.com
@summary:   TORF-224354
            Update LITP core so that Consul service starts first and
            is available for other services to register
"""


from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from litp_cli_utils import CLIUtils
import test_constants
import os


class Story224354(GenericTest):
    """
        Assert that the tasks TAGGED with PRE_CLUSTER_TAG are executed
        before peer node tasks
    """

    def setUp(self):
        """
            Runs before every single test
        """

        super(Story224354, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()
        self.wireshark_pkg = "wireshark"
        self.conf_type = "story224354-conf"
        self.item_name1 = "test_story224354"
        self.item_name2 = "test_story224354a"
        self.sw_items_path = self.find(self.ms_node, "/software",
                                       "collection-of-software-item")
        self.ms_items_path = self.find(self.ms_node, "/ms",
                                       "ref-collection-of-software-item")
        self.nodes_path = self.find(self.ms_node, "/deployments", "node")
        self.plugin_id = "story224354"

    def tearDown(self):
        """
            Runs after every single test
        """
        super(Story224354, self).tearDown()

    def _install_item_extension(self):
        """
            check if a plugin/extension rpm is installed and if not, install it
        """
        _, _, rcode = self.run_command(
            self.ms_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_path_ls(
                os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'plugins')), self.plugin_id
            )

            self.log("info", "local_rpm_paths is: {0}".format(local_rpm_paths))

            self.assertTrue(self.copy_and_install_rpms(self.ms_node,
                                                       local_rpm_paths),
                            "RPM was not installed")

    @attr('all', 'revert', 'story224354', 'story224354_tc01',
          'story224354_tc02')
    def test_01_p_verify_pre_cluster_tag(self):
        """
            @tms_id: torf_224354_tc01
            @tms_requirements_id: TORF-224354
            @tms_title: Verify that tasks tagged
                with PRE_CLUSTER_TAG are executed
                after MS tasks and before tasks on peer nodes
            @tms_description: Installs plugin with a CallbackTask
                tagged with PRE_CLUSTER_TAG.
                Installs wireshark package on ms and peer nodes.
                Creates dummy item and inherits to peer nodes
                Creates and executes plan and verifies PRE_CLUSTER_TAG task
                is executed after ms tasks and
                before other tasks on peer nodes.
            @tms_test_steps:
             @step: Create 'wireshark' item in LITP model
             @result: 'wireshark' item is created in LITP model
             @step: Create dummy item 'test_story224354'
                  which is tagged with PRE_CLUSTER_TAG in LITP model
             @result: dummy item 'test_story224354' is created in LITP model
             @step: Inherit 'wireshark' item onto ms and peer nodes
             @result: 'wireshark' item is inherited onto ms and peer nodes
             @step: Inherit dummy item 'test_story224354' onto peer nodes
             @result: dummy item is inherited onto peer nodes
             @step: create_plan, show_plan, verify task order and run_plan
             @result: Plan executes successfully.
                 Task tagged with PRE_CLUSTER_TAG is executed after ms tasks
                 and before peer node phases.
            @tms_test_precondition: N/A
            @tms_execution_type: Automated
        """

        self._install_item_extension()

        ms_task_description = 'Install package "{0}" on node "{1}"'.format(
            self.wireshark_pkg, self.ms_node)

        self.log("info", "#1: Create 'wireshark' item in LITP model."
                         "Inherit item to MS.")
        self.execute_cli_create_cmd(self.ms_node,
                                    "{0}/{1}".format(self.sw_items_path[0],
                                                     self.wireshark_pkg),
                                    "package", "name=wireshark")
        self.execute_cli_inherit_cmd(self.ms_node, "{0}/{1}".format(
            self.ms_items_path[0], self.wireshark_pkg),
                                     "{0}/{1}".format(self.sw_items_path[0],
                                                      self.wireshark_pkg))

        self.log("info", "#2: Create dummy item 'story224354-conf', "
                         "which is created by the plugin for test purposes, "
                         "in LITP model.")
        self.execute_cli_create_cmd(self.ms_node, "{0}/{1}".format(
            self.sw_items_path[0], self.item_name1), self.conf_type,
                                    "name=test_story224354")

        self.log("info", "#3: Inherit wireshark and "
                         "story224354-conf on to peer nodes.")
        for path in self.nodes_path:
            sw_items = \
                {"{0}/items/{1}".format(path, self.wireshark_pkg): self.
                    wireshark_pkg,
                 "{0}/items/{1}".format(path, self.item_name1): self.item_name1
                 }

            for item_path, item_name in sw_items.iteritems():
                self.execute_cli_inherit_cmd(self.ms_node, item_path,
                                             "{0}/{1}".format(self.
                                                              sw_items_path[0],
                                                              item_name))

        self.log("info", "#4: create and show plan")
        self.execute_cli_createplan_cmd(self.ms_node)
        show_plan_output, _, _ = self.execute_cli_showplan_cmd(self.ms_node)

        self.log("info", "#5: Verify MS tasks are executed before "
                         "tasks tagged with PRE_CLUSTER_TAG - phase 1")
        self.assertEqual(self.cli.get_plan_phase(show_plan_output, 1)[3],
                         ms_task_description,
                         "MS task '{0}' is not in phase 1 as expected".format(
                             ms_task_description))

        self.log("info", "#6: Verify tasks tagged with "
                         "PRE_CLUSTER_TAG are in the expected phase 2")
        self.assertEqual(self.cli.get_plan_phase(show_plan_output, 2)[3],
                         "Mcollective check_file_exist command to run on {0}"
                         .format(self.mn_nodes[0]),
                         "PRE_CLUSTER_TAG task is NOT in phase 2 as expected")

        self.log("info", "#7: Create test file on peer nodes in order for "
                         "the callbackTask (Mcollective check_file_exist) to "
                         "be successful")
        for node in self.mn_nodes:
            self.create_file_on_node(node, "/tmp/{0}".format(self.item_name1),
                                     ['file content'], su_root=True)

        self.log("info", "#8: Run plan successfully")
        self.run_and_check_plan(self.ms_node, test_constants.PLAN_COMPLETE,
                                plan_timeout_mins=5)

    @attr('all', 'revert', 'story224354', 'story224354_tc04')
    def test_04_n_fail_plan_with_pre_cluster_tag(self):
        """ @tms_id: torf_224354_tc04
            @tms_requirements_id: TORF-224354
            @tms_title: Verify that if a plan fails on a task tagged
                with the PRE_CLUSTER_TAG,
                when the plan is recreated the failing task is included
            @tms_description: Deletes test file that the tagged task checks for
                (/tmp/test-story224354a).
                Creates and executes plan. When the plan fails on the task,
                creates missing test file, recreates the plan and runs again.
            @tms_test_steps:
             @step: Create dummy item 'test_story224354a'
                which is tagged with PRE_CLUSTER_TAG in LITP model
             @result: dummy item 'test_story224354a' is created in LITP model
             @step: Inherit dummy item 'test_story224354a' onto peer nodes
             @result: dummy item is inherited onto peer nodes
             @step: create_plan, show_plan and verify order of tasks
             @result: plan is created with tasks in the expected order
             @step: create test file on node1 and delete from node2
             @result: /tmp/test-story224354a is created on node1 and deleted
                 from node 2
             @step: run_plan
             @result: Plan fails on check_file_exist task on node2
             @step: create test file on node2
             @result: test file is created on node2
             @step: recreate plan and run_plan
             @result: Failing task is included in recreated plan.
                 Plan executes successfully as the test file is present on
                 node1 and node2
            @tms_test_precondition: N/A
            @tms_execution_type: Automated
        """

        self.log("info", "#1: Create dummy item 'story224354-conf', "
                         "which is created by the plugin for test purposes, "
                         "in LITP model.")
        self.execute_cli_create_cmd(self.ms_node,
                                    "{0}/{1}".format(self.sw_items_path[0],
                                                     self.item_name2), self.
                                    conf_type, "name=test_story224354a")

        self.log("info", "#2: Inherit story224354-conf onto peer nodes")
        for path in self.nodes_path:
            full_peer_path_test = "{0}/items/{1}".format(path, self.item_name2)
            self.execute_cli_inherit_cmd(self.ms_node, full_peer_path_test,
                                         "{0}/{1}".format(
                                             self.sw_items_path[0], self
                                                 .item_name2))

        self.log("info", "#3: Create and show plan")
        self.execute_cli_createplan_cmd(self.ms_node)
        show_plan_output, _, _ = self.execute_cli_showplan_cmd(self.ms_node)

        self.log("info", "#4: Verify tasks tagged with "
                         "PRE_CLUSTER_TAG are in the expected phase - 1")
        self.assertEqual(self.cli.get_plan_phase(show_plan_output, 1)[3],
                         "Mcollective check_file_exist command to run on {0}".
                         format(self.mn_nodes[0]),
                         "PRE_CLUSTER_TAG tasks are not in phase 1 as expected"
                         )

        self.log("info", "#5: Create test file on node1 only "
                         "and delete file from node2 - "
                         "'check_file_exist' task will fail on node2")
        self.create_file_on_node(self.mn_nodes[0],
                                 "/tmp/{0}".format(self.item_name2),
                                 ['file content'], su_root=True)
        self.remove_item(self.mn_nodes[1], "/tmp/{0}".format(self.item_name2))

        self.log("info", "#6: run_plan and wait for plan state - FAILED")
        self.run_and_check_plan(self.ms_node, test_constants.PLAN_FAILED,
                                plan_timeout_mins=5)

        self.log("info", "#7: Verify expected task is failed")
        show_plan_output, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(self.cli.get_plan_phase(show_plan_output, 1)[4],
                         "Failed\t\t/deployments/d1/clusters/c1",
                         'Task "{0}" is not failed as expected'.format
                         ("Mcollective check_file_exist command to run on {0}"
                          .format(self.mn_nodes[1])))

        self.log("info", "#8: create test file and re-create plan")
        self.create_file_on_node(self.mn_nodes[1],
                                 "/tmp/{0}".format(self.item_name2),
                                 ['file content'], su_root=True)
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log("info", '#9: Verify that the "Failed" task '
                         'is re-created in phase 1')
        show_plan_output, _, _ = self.execute_cli_showplan_cmd(self.ms_node)
        self.assertEqual(self.cli.get_plan_phase(show_plan_output, 1)[5],
                         "Mcollective check_file_exist command to run on {0}".
                         format(self.mn_nodes[1]),
                         "PRE_CLUSTER_TAG tasks are not recreated in phase 1 "
                         "as expected")

        self.log("info", "#10: Run plan successfully")
        self.run_and_check_plan(self.ms_node, test_constants.PLAN_COMPLETE,
                                plan_timeout_mins=5)
