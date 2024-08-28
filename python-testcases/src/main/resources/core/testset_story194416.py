"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2017
@author:    Laura Forbes, Pat Bohan
@summary:   TORF-194416
            As a LITP user I want the ability to remove a node
            item from the model when the node is non-contactable.
"""

from litp_generic_test import GenericTest, attr
import test_constants as const


class Story194416(GenericTest):
    """
        As a LITP user I want the ability to remove a node
        item from the model when the node is non-contactable.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story194416, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.removed_node = self.mn_nodes[0]
        self.removed_node_url = self.find(
            self.ms_node, "/deployments", "node")[0]
        self.healthy_nodes = [self.ms_node, self.mn_nodes[1]]

    def tearDown(self):
        """ Runs after every single test """
        super(Story194416, self).tearDown()

    def create_run_wait_plan_success(self, timeout_mins=20):
        """
        Description:
            Runs the 'litp create_plan' and 'litp run_plan' commands
                and waits for the plan to successfully complete.
        Kwargs:
            timeout_mins (int): When to timeout from the method
            if the plan is still running.
        """
        self.log('info', 'Execute "litp create_plan" command.')
        self.execute_cli_createplan_cmd(self.ms_node)
        self.log('info', 'Execute "litp run_plan" command.')
        self.execute_cli_runplan_cmd(self.ms_node)
        self.log('info', 'Wait for the plan to succeed.')
        self.assertTrue(self.wait_for_plan_state(
            self.ms_node, const.PLAN_COMPLETE, timeout_mins),
                         "Plan did not complete successfully.")

    def assert_no_errors_msgs(self, start_pos):
        """
        Description:
            Ensures that no "ERROR" or "WARNING:" messages are
            logged to /var/log/messages on the MS from the
            line specified to the end of the file.
        Args:
            start_pos (int): Line of file to check from.
        """

        msgs_to_check = ["WARNING:", "ERROR"]

        for msg in msgs_to_check:

            msg_found = self.wait_for_log_msg(
                self.ms_node, msg, log_len=start_pos, timeout_sec=1,
                return_log_msgs=True)

            if msg_found:
                #Ignoring postgres errors due to TORF-252951
                errors = [err_msg for err_msg in msg_found
                          if "postgres" not in err_msg]

                self.assertTrue(errors == [], "'{0}' message(s) found in {1}"
                                .format(msg, const.GEN_SYSTEM_LOG_PATH))

    def check_path_not_in_model(self, path_to_check, item_type):
        """
        Description:
            Ensures that the specified path does not exist in the LITP model.
        Args:
            path_to_check (str): Path to check in the LITP model.
            item_type (str): The resource type to filter by.
        """
        self.assertEqual(0, len(self.find(
            self.ms_node, path_to_check, item_type, assert_not_empty=False)),
                         "Path {0} unexpectedly found in model.".format(
                             path_to_check))

    def puppet_reference_checks(self, node, puppet_reference):
        """
        Description:
            Asserts that the specified node has a Puppet manifest file
        Args:
            node (str): Hostname of node to check.
            puppet_reference (bool): True if node is expected to
                be referenced in the Puppet manifest, False otherwise.
        """
        self.log("info", "Check if a Puppet manifest "
                         "for {0} exists.".format(node))
        cmd = 'ls {0}{1}.pp'.format(
            const.PUPPET_MANIFESTS_DIR, self.removed_node)
        stdout, stderr, rc = self.run_command(
            self.ms_node, cmd, default_asserts=False)

        if puppet_reference:
            # Puppet manifest should exist for node
            self.assertNotEqual([], stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, rc)
        else:
            # Puppet manifest for node should not exist
            self.assertEqual([], stdout)
            self.assertNotEqual([], stderr)
            self.assertNotEqual(0, rc)

    @attr('all', 'revert', 'story194416', 'story194416_tc01')
    def test_01_p_remove_uncontactable_node(self):
        """
            @tms_id: torf_194416_tc01
            @tms_requirements_id: TORF-194416
            @tms_title: Remove Node, No Communication With
                                            Previously Removed Node
            @tms_description:
                1) When I issue the 'litp remove' command to remove a node item
                    from the model followed by 'litp create_plan' and
                    'litp run_plan' commands when the node is non-contactable,
                    then the node item and its children are marked ForRemoval,
                    plan is created with tasks to remove the node and runs with
                    no attempted communication with the node, there is no delay
                    in running any of the tasks pertaining to the removal of
                    the node, plan completes successfully after which the node
                    is removed from the model and there is no configuration or
                    reference persisted in relation to the removed node.
                2) When I update a cluster in which a non-contactable node was
                    previously removed from the model and I create/run a plan,
                    then there is no attempted communication with the removed
                    node and the update is applied to all other
                    nodes in the cluster.
            @tms_test_steps:
                @step: Export 'services' XML
                @result: 'services' XML exported successfully
                @step: Export XML of node to be removed
                @result: Node XML exported successfully
                @step: Remove non-modelled dependent package ghostscript-cups
                @result: ghostscript-cups is removed
                @step: Remove each service group from cluster
                @result: All service groups transition to 'ForRemoval' state
                @step: Create 2 cluster aliases
                @result: Aliases created successfully
                @step: Create/run plan to remove SGs and add cluster aliases
                @result: Plan runs successfully
                @result: Service group items no longer in model
                @step: Assert that node to be removed has a Puppet manifest
                    file
                @result: Assertions successful
                @step: Power off node to be removed
                @result: Node shuts down
                @step: Remove node from the model
                @result: Node transitions to 'ForRemoval' state
                @step: Remove and add a cluster alias
                @result: Alias transitions to 'ForRemoval'
                    state, alias in 'Initial' state
                @step: Create/run plan to remove node and
                    remove/add cluster aliases
                @result: Plan runs successfully
                @result: Node item no longer in model
                @step: Assert no errors in logs
                @result: No errors found in logs
                @step: Assert that node to be removed has no Puppet manifest
                    file
                @result: Assertions successful
                @step: Run 'litp create_plan'
                @result: 'DoNothingPlanError' returned
                @step: Remove cluster alias path, create/run plan
                @result: Plan runs successfully, item removed from model
                @step: Assert no errors in logs
                @result: No errors found in logs
                @step: Re-add removed node to model via XML, create/run plan
                @result: Plan runs to completion
                @result: Node in model in 'Applied' state
                @step: Assert that node to be removed has a Puppet manifest
                    file
                @result: Assertions successful
                @step: Re-add removed service groups to model, create/run plan
                @result: All service groups re-added to model and
                    are in state 'Applied'
            @tms_test_precondition: There is more than 1 node in
                the cluster, node to be removed is offline.
            @tms_execution_type: Automated
        """
        self.log("info", "1. Find path to cluster in LITP model.")
        cluster_path = self.find(
            self.ms_node, '/deployments', 'vcs-cluster')[0]

        # All VCS services must be removed in order for node removal to work
        self.log("info", "2. Find 'services' path under 'cluster' path.")
        services_path = self.find(self.ms_node, cluster_path,
                                  'collection-of-clustered-service')[0]

        self.log("info", "3. Find all service groups in the cluster.")
        service_groups_paths = self.find(self.ms_node, services_path,
                                         'vcs-clustered-service')
        # List SGs in cluster to check that they
        # have been re-added after test completes
        service_groups = []

        self.log("info", "4. Export 'services' XML so that it "
                         "can be re-imported after test.")
        services_xml_file = "/tmp/services.xml"
        self.execute_cli_export_cmd(
            self.ms_node, services_path, filepath=services_xml_file)

        self.log("info", "5. Find path to nodes under cluster.")
        node_path = self.find(self.ms_node, cluster_path,
                              'collection-of-node')[0]

        self.log("info", "6. Export XML of node to be removed so "
                         "that it can be re-imported after test.")
        node_xml_file = "/tmp/{0}.xml".format(self.removed_node)
        self.execute_cli_export_cmd(
            self.ms_node, self.removed_node_url, filepath=node_xml_file)

        self.log("info",
                     "7. Remove any non-modelled dependant packages")
        cmd = "{0} -e ghostscript-cups --nodeps".format(const.RPM_PATH)
        self.run_puppet_once(self.ms_node)
        for node in self.mn_nodes:
            std_out, _, _ = self.run_command(node, cmd, su_root=True,
                                                  default_asserts=True)
            self.assertEqual([], std_out,
                                "rpm command did not execute as expected")

        try:
            # FOR NODE REMOVAL TO WORK, ALL SERVICE
            # GROUPS MUST BE REMOVED FROM THE CLUSTER
            self.log("info", "8. Remove each service group from cluster "
                             "(required in order for node removal to work).")
            for service_group in service_groups_paths:
                # ADD EACH SERVICE GROUP TO A LIST SO THAT WE CAN CHECK
                # THAT THEY HAVE BEEN ADDED BACK IN AFTER RE-EXPANDING
                service_groups.append(service_group.split('/')[-1])
                self.log("info", "Removing {0}".format(service_group))
                self.execute_cli_remove_cmd(self.ms_node, service_group)

            self.log("info", "9. Create 2 cluster aliases.")
            self.log("info", "9.1 Create cluster alias path.")
            config_url = "{0}{1}".format(cluster_path,
                            "/configs/torf194416_aliases")
            self.execute_cli_create_cmd(
                self.ms_node, config_url, "alias-cluster-config")

            self.log("info", "9.2 Create 2 aliases under cluster path.")
            for count in range(2):
                link_url = config_url +\
                           "/aliases/torf194416alias{0}".format(count)
                props = "address=192.168.0.4{0} " \
                        "alias_names=torf194416alias{0}".format(count)
                self.execute_cli_create_cmd(self.ms_node, link_url, "alias",
                                            props, expect_positive=True)

            self.log("info", "10. Create and run a plan to "
                             "remove the SGs and add the cluster aliases.")
            self.create_run_wait_plan_success()

            self.log("info", "11. Verify that the SG items "
                             "have been deleted from the model.")
            self.check_path_not_in_model(
                services_path, 'vcs-clustered-service')

            self.log("info", "12. Assert that the node to be removed has "
                             "a Puppet manifest file.")
            self.puppet_reference_checks(self.removed_node, True)

            self.log("info", "BEGINNING NODE REMOVAL TEST.")
            # Get current last line number of messages file (i.e. file length)
            start_log_pos = self.get_file_len(
                self.ms_node, const.GEN_SYSTEM_LOG_PATH)

            self.turn_on_litp_debug(self.ms_node)

            self.log('info', '13. Power off the node to be removed.')
            if self.is_ip_pingable(self.ms_node, self.removed_node):
                self.poweroff_peer_node(self.ms_node, self.removed_node)

            self.log('info', '14. Remove node from the model.')
            self.execute_cli_remove_cmd(self.ms_node, self.removed_node_url)

            self.log('info', '15. Remove and add a cluster alias.')
            remove_alias = config_url + "/aliases/torf194416alias0"
            self.execute_cli_remove_cmd(self.ms_node, remove_alias)
            link_url = config_url + "/aliases/torf194416alias3"
            props = "address=192.168.0.49 alias_names=torf194416alias3"
            self.execute_cli_create_cmd(
                self.ms_node, link_url, "alias", props, expect_positive=True)

            self.log("info", "16. Create and run a plan to remove "
                             "the node and remove/add the cluster aliases.")
            self.create_run_wait_plan_success()

            self.log("info", "17. Verify that the node item "
                             "has been deleted from the model.")
            self.check_path_not_in_model(self.removed_node_url, 'node')

            self.log('info', "18. Assert that no 'ERROR' or"
                             " 'WARNING' messages were logged "
                             "to {0}.".format(const.GEN_SYSTEM_LOG_PATH))
            self.assert_no_errors_msgs(start_log_pos)

            self.log("info", "19. Assert that the Puppet manifest for the "
                             "removed node does not exist.")
            self.puppet_reference_checks(self.removed_node, False)

            self.log("info", "20. Verify that 'DoNothingPlanError' is returned"
                             " when 'litp create_plan' is executed when there "
                             "have been no further model updates.")
            create_plan_err_msg = 'DoNothingPlanError    Create ' \
                                  'plan failed: no tasks were generated'
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.ms_node, expect_positive=False)
            self.assertTrue(create_plan_err_msg == stderr[0],
                            "Expected 'DoNothingPlanError' not returned.")

            self.log("info", "BEGINNING TEST FOR 'NO COMMUNICATION "
                             "WITH PREVIOUSLY REMOVED NODE'.")
            start_log_pos = self.get_file_len(
                self.ms_node, const.GEN_SYSTEM_LOG_PATH)
            self.log("info", "21. Remove the cluster alias "
                             "path previously created.")
            self.execute_cli_remove_cmd(self.ms_node, config_url)
            self.log("info", "22. Create and run a plan and "
                             "ensure it completes successfully.")
            self.create_run_wait_plan_success()

            self.log("info", "23. Verify that the aliases "
                             "path has been deleted from the model.")
            self.check_path_not_in_model(config_url, 'alias-cluster-config')

            self.log('info', "24. Assert that no 'ERROR' or"
                             " 'WARNING' messages were logged "
                             "to {0}.".format(const.GEN_SYSTEM_LOG_PATH))
            self.assert_no_errors_msgs(start_log_pos)

        finally:
            self.log("info", "25. Re-add the removed node to the model.")
            self.execute_cli_load_cmd(self.ms_node, node_path, node_xml_file)
            self.log("info", "26. Create and run a plan and "
                             "ensure it completes successfully.")
            self.create_run_wait_plan_success(timeout_mins=25)
            self.log("info", "27. Ensure node has been re-added to "
                             "model and is in state 'Applied'.")
            node_state = self.get_item_state(
                self.ms_node, self.removed_node_url)
            self.assertEqual('Applied', node_state,
                             "{0} not in expected 'Applied' state after "
                             "successful plan to import it via XML.".format(
                                 self.removed_node))

            self.log("info", "28. Set passwords on re-added node.")
            cmd = "sed -i '/{0}/d' {1}/known_hosts".format(
                self.removed_node, const.SSH_KEYS_FOLDER)
            _, _, rc = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, rc)

            self.assertTrue(self.set_pws_new_node(
                self.ms_node, self.removed_node), "Failed to set password.")

            self.log("info", "29. Assert that the node to be removed has "
                             "a Puppet manifest file.")
            self.puppet_reference_checks(self.removed_node, True)

            self.log("info", "30. Re-add removed service groups to the model.")
            self.execute_cli_load_cmd(self.ms_node, cluster_path,
                                      services_xml_file, args="--merge")
            self.log("info", "31. Create and run a plan and "
                             "ensure it completes successfully.")
            self.create_run_wait_plan_success()

            self.log("info", "32. Ensure all service groups have been re-added"
                             " to the model and are in state 'Applied'.")
            for service_group in self.find(self.ms_node, services_path,
                                           'vcs-clustered-service'):
                service_state = self.get_item_state(
                    self.ms_node, service_group)
                self.assertEqual('Applied', service_state,
                                 "{0} not in expected 'Applied' state after "
                                 "successful plan to import it"
                                 " via XML.".format(service_group))

                service_groups.remove(service_group.split('/')[-1])
            self.assertEqual([], service_groups)
