'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     December 2015
@author:    Maria Varley
@summary:   Integration test for cluster ordering
            Agile: STORY LITPCDS-8809
'''

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from rest_utils import RestUtils
import test_constants
import os


class Story8809(GenericTest):
    '''
    As a LITP Architect I want LITP Core's Task Sort algorithm to sort
    an upgrade plan on a cluster by cluster order
    '''
    test_node_if1 = None
    test_ms_if1 = None

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story8809, self).setUp()

        # 2. Set up variables used in the test
        self.ms1 = self.get_management_node_filenames()[0]
        self.managed_nodes = self.get_managed_node_filenames()

        self.redhatutils = RHCmdUtils()
        self.ms_ip_address = self.get_node_att(self.ms1, 'ipv4')
        self.rest = RestUtils(self.ms_ip_address)

        self.node1_repo = "story8809_test06repo"
        self.node1_pkg_name = "node1_pkg_story1708"
        self.node1_rpm = "node1_pkg_story1708-2.0-1.noarch"
        self.node1_upgrade_rpm = "node1_pkg_story1708-6.0-6.noarch"

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        super(Story8809, self).tearDown()

    def _find_software_items_path(self):
        """
        Finds and returns the software items path
        """
        sw_items = self.find(
            self.ms1, "/software",
            "collection-of-software-item")
        self.assertNotEqual([], sw_items)
        sw_items_path = sw_items[0]
        return sw_items_path

    def _find_node1_path(self):
        """
        Finds and returns node1 items path
        """
        node1_path = self.find(self.ms1, "/deployments", "node", True)[0]
        node_1_sw_items_url = node1_path + "/items"
        return node_1_sw_items_url

    def _create_repo_install_pkg(self):
        """
        Description:
        Function that create a yum repository and installs a package
        from that repository onto a peer node
        """
        # 1. Create a directory which will become a yum repository
        repo_dir_path = test_constants.PARENT_PKG_REPO_DIR + self.node1_repo
        self.run_command(self.ms1, "mkdir {0}".format(
            repo_dir_path), su_root=True)

        # 2. Copy dummy RPMs into the created directory
        local_path = os.path.dirname(os.path.abspath(__file__)) \
                + "/story8809_rpms/" + self.node1_rpm + ".rpm"
        self.assertTrue(self.copy_file_to(self.ms1, local_path, \
                "{0}".format(repo_dir_path), \
                root_copy=True, add_to_cleanup=False))

        # 3. Execute "create_repo" command
        self.run_command(
            self.ms1, "createrepo {0}".format(repo_dir_path), su_root=True)

        # Find the software items path
        sw_items_path = self._find_software_items_path()

        # Get node1 path
        node_1_sw_items_url = self._find_node1_path()

        # 4. Create yum repository in the LITP Model for the created repo
        sw_items_url = "{0}/{1}".format(
            sw_items_path, self.node1_repo)
        props = "name='{0}'\
            ms_url_path='/{1}'".format(self.node1_repo, self.node1_repo,)
        self.execute_cli_create_cmd(
            self.ms1, sw_items_url, "yum-repository", props)

        # 5. The Peer node inherits from the yum repository item
        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_1_sw_items_url, self.node1_repo), \
            "{0}/{1}".format(sw_items_path, self.node1_repo))

        # 6.Create a package model item to be installed on the Peer node
        props = "name='{0}' repository='{1}'".format(
            self.node1_pkg_name, self.node1_repo)
        package_path = "{0}/{1}".format(sw_items_path, self.node1_pkg_name)
        self.execute_cli_create_cmd(self.ms1, \
            package_path, \
            "package", props)

        # 7.The Peer Node inherits the package item
        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_1_sw_items_url, self.node1_pkg_name), \
            package_path)

    def _upgrade_pkg(self):
        """
        Description:
        Ugrade the installed package
        """
        repo_dir_path = test_constants.PARENT_PKG_REPO_DIR + self.node1_repo

        # Find the software items path
        sw_items_path = self._find_software_items_path()

        # 1. Copy upgrade dummy rpm into the yum repository directory
        local_path = os.path.dirname(os.path.abspath(__file__)) + \
            "/story8809_rpms/" + self.node1_upgrade_rpm + ".rpm"
        self.assertTrue(self.copy_file_to(self.ms1, local_path, \
                "{0}".format(repo_dir_path), \
                root_copy=True, add_to_cleanup=False))

        # 2. Execute the "createrepo --update" command on the repos
        self.run_command(
            self.ms1, "createrepo --update -v {0}".format(
            repo_dir_path), su_root=True)

        # 3. Update the version and release properties on the package item
        #    in the model and on the inherited items
        props = "version='6.0' release='6'"
        self.execute_cli_update_cmd(
            self.ms1, "{0}/{1}".format(
            sw_items_path, self.node1_pkg_name), props)

    @attr('all', 'expansion', 'story8809', 'story8809_tc06_08_09')
    def test_09_n_installation_plan_fails_after_vcs_installed(self):
        """
        Description:
        Test that when an installation plan fails after
        VCS install tasks have been executed and the plan is recreated,
        the subsequent plan contains tasks in no particular order

        Actions:
        1. Update the "dependency_list" property
        2. Follow the installation steps
        3. Ensure installation plan fails after
           VCS has been installed
        4. Recreate plan
        5. Check that the recreated plan containing node
           lock and unlock tasks shows that the dependencies
           in the depencdency list is not followed

        Result:
        Ensure that a recreated failed installation plan
        after VCS has installed, i.e. has lock/unlock tasks
        is not affected
        """
        # Remove and create_snapshot
        self.remove_all_snapshots(self.ms1)
        self.execute_and_wait_createsnapshot(self.ms1, add_to_cleanup=False)

        # 1. Install package
        self._create_repo_install_pkg()

        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1,
                                                 test_constants.PLAN_COMPLETE,
                                                 timeout_mins=60))

        # 5. Create a list of the nodes that will be added
        nodes_to_expand = list()
        nodes_to_expand.append("node2")
        nodes_to_expand.append("node3")

        # 6. Create a new cluster 2
        cluster_collect = self.find(self.ms1, '/deployments',
                            'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
            'cluster_id=1043 dependency_list=c3'
        self.execute_cli_create_cmd(self.ms1,
                            cluster_collect + "/c2",
                            'vcs-cluster',
                             props)

        # 7. Create a new cluster 3
        cluster_collect = self.find(self.ms1, '/deployments',
                            'cluster', False)[0]
        props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' +\
            'cluster_id=1044'
        self.execute_cli_create_cmd(self.ms1,
                            cluster_collect + "/c3",
                            'vcs-cluster',
                             props)

        # 8. Execute the expand script for expanding cluster 2 with node2
        # and cluster 3 with node 3.
        self.execute_expand_script(self.ms1, 'expand_cloud_c2_mn2.sh',
                           cluster_filename='RHEL7_192.168.0.42_4node.sh')
        self.execute_expand_script(self.ms1, 'expand_cloud_c3_mn3.sh',
                           cluster_filename='RHEL7_192.168.0.42_4node.sh')

        # 9. Upgrade installed package
        self._upgrade_pkg()

        node2_path = self.find(
            self.ms1, cluster_collect + "/c2", "node", True)[0]
        node_2_sw_items_url = node2_path + "/items"

        node3_path = self.find(
            self.ms1, cluster_collect + "/c3", "node", True)[0]
        node_3_sw_items_url = node3_path + "/items"

        # Find the software items path
        sw_items_path = self._find_software_items_path()

        # 10.Additional Peer node inherits from the yum repository item
        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_2_sw_items_url, self.node1_repo), \
            "{0}/{1}".format(sw_items_path, self.node1_repo))

        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_3_sw_items_url, self.node1_repo), \
            "{0}/{1}".format(sw_items_path, self.node1_repo))

        # 11.Additional Peer Nodes inherits the package item
        package_path = "{0}/{1}".format(sw_items_path, self.node1_pkg_name)

        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_2_sw_items_url, self.node1_pkg_name), \
            package_path)
        self.execute_cli_inherit_cmd(self.ms1, \
            "{0}/{1}".format(node_3_sw_items_url, self.node1_pkg_name), \
            package_path)

        # 12.Create plan
        self.execute_cli_createplan_cmd(self.ms1)

        # 13.Run plan
        self.execute_cli_runplan_cmd(self.ms1)

        # 14.Wait until VCS has been installed before stopping the plan
        self.assertTrue(self.wait_for_task_state(
            self.ms1, 'Create VCS service group for NIC "br0"',
            test_constants.PLAN_TASKS_INCONSISTENT,
            ignore_variables=False, timeout_mins=60))

        # 15.Stop plan after VCS has been installed
        self.execute_cli_stopplan_cmd(self.ms1)
        self.assertTrue(self.wait_for_plan_state(
            self.ms1, test_constants.PLAN_STOPPED,
            timeout_mins=60))

        try:
            self.log("info", "Attempting to re-create stopped plan.....")
            # 16.Create plan
            self.execute_cli_createplan_cmd(self.ms1)
            stdout, _, _ = self.execute_cli_showplan_cmd(self.ms1)

            plan = self.cli.parse_plan_output(stdout)

            # 17. Need to verify that there are lock tasks for both Node1 &
            # Node3 in the plan. Node3 should occur before Node1 due to
            # cluster dependencies
            self.log("info",
                    "Verifying that lock tasks for both Node1 and Node3 exist")
            node1_lock_phase = -1
            node3_lock_phase = -1
            for phase_nr in plan:
                for task_nr in plan[phase_nr]:
                    if 'Lock VCS on node "node3"' ==\
                                            plan[phase_nr][task_nr]['DESC'][1]:
                        node3_lock_phase = phase_nr

                    if 'Lock VCS on node "node1"' ==\
                                            plan[phase_nr][task_nr]['DESC'][1]:
                        node1_lock_phase = phase_nr

            # Ensure that Lock tasks have been found for both nodes
            err_msg = "No lock tasks found for either/or " +\
                      "Node1({0}) or Node3({1})".format(node1_lock_phase,
                                                        node3_lock_phase)
            self.assertFalse(node3_lock_phase == -1 or node1_lock_phase == -1,
                             err_msg)

            # Ensure that Node3 lock task comes before Node1
            err_msg = "Lock Phase for Node3(" +\
                      "{0}), occurs after Node1({1})".format(node3_lock_phase,
                                                             node1_lock_phase)
            self.assertTrue((node3_lock_phase < node1_lock_phase and
                             node1_lock_phase != -1 and
                             node3_lock_phase != -1), err_msg)

            # 18.Run plan
            self.execute_cli_runplan_cmd(self.ms1)

            # 19.Wait for plan to complete
            self.assertTrue(self.wait_for_plan_state(
                self.ms1, test_constants.PLAN_COMPLETE,
                timeout_mins=60))

        finally:
            # 20.Restore Snapshot so system returned back to a
            #    one node state again.
            self.execute_and_wait_restore_snapshot(
                self.ms1, "-f", poweroff_nodes=nodes_to_expand)

            # 21.Create a new snapshot for the next test
            #    to have a restore_point
            self.execute_and_wait_createsnapshot(
                self.ms1, add_to_cleanup=False)
