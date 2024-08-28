"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Oct 2017
@author:    Laura Forbes
@summary:   TORF-184851
            As a LITP User I want the ability to reinstall
            a peer node that is already deployed.
"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Story184851(GenericTest):
    """
        As a LITP User I want the ability to reinstall
        a peer node that is already deployed.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story184851, self).setUp()

        self.ms_node = self.get_management_node_filename()
        self.node_urls = self.find(self.ms_node, '/deployments', 'node')
        self.restore_node_url = self.node_urls[0]
        self.restore_node = self.get_props_from_url(
            self.ms_node, self.restore_node_url, filter_prop='hostname')

        self.cluster2 = {'id': 'c2',
                         'cluster_id': '1043',
                         'script': 'expand_cloud_c2_mn2.sh',
                         'node': 'node2'}

        self.cluster3 = {'id': 'c3',
                         'cluster_id': '1044',
                         'script': 'expand_cloud_c3_mn3.sh',
                         'node': 'node3'}

        self.cluster4 = {'id': 'c4',
                         'cluster_id': '1045',
                         'script': 'expand_cloud_c4_mn4.sh',
                         'node': 'node4'}

        self.cluster_collect_url = self.find(
            self.ms_node, '/deployments', 'cluster', False)[0]

        self.clusters_to_expand = [self.cluster2, self.cluster3, self.cluster4]
        self.nodes_to_expand = list()

    def tearDown(self):
        """ Runs after every single test """
        super(Story184851, self).tearDown()

    def check_deployment_1_cluster_1_node(self):
        """
        Description:
            Asserts that the test environment has 1 cluster with 1 node.
        """
        clusters = self.find(self.ms_node, '/deployments', 'vcs-cluster')
        nodes = self.find(self.ms_node, '/deployments', 'node')
        self.assertTrue(len(clusters) == 1 and len(nodes) == 1,
                        'This test requires a LITP '
                        '1-cluster 1-node deployment.')

    def _expand_model(self):
        """
        Description:
            Expands the model with new clusters and nodes.
        """
        for cluster in self.clusters_to_expand:
            self.nodes_to_expand.append(cluster['node'])

            cluster['url'] = '{0}/{1}'.format(
                self.cluster_collect_url, cluster['id'])

            props = 'cluster_type=sfha low_prio_net=mgmt llt_nets=hb1,hb2 ' \
                    'cluster_id={0}'.format(cluster['cluster_id'])

            self.execute_cli_create_cmd(
                self.ms_node, cluster['url'], 'vcs-cluster',
                props=props, add_to_cleanup=False)

            self.execute_expand_script(self.ms_node, cluster['script'])

    def _check_item_state(self, state, paths):
        """
        Description:
            Check that all items under given paths are in the specified state.
        Args:
            state (str): Expected state of LITP item(s)
            paths (list): Paths to check
        """
        for path in paths:
            self.assertTrue(
                self.is_expected_state(self.ms_node, path=path, state=state),
                'Found at least one item under "{0}" not '
                'in {1} state'.format(path, state))

    def _list_online_sgs(self, vcs_node):
        """
        Description:
            Runs a 'hastatus -sum' command on the specified VCS node and
            returns a list of Service Groups that are online in the VCS Cluster
            that contains that node. If there are parallel SGs, then the list
            will return them twice if they are both online.
        Args:
            vcs_node (str): Node to run 'hastatus -sum' command on
        Returns:
            sg_list (list): List of Service Groups ONLINE in the VCS Cluster
        """
        sg_list = []
        sgs = self.run_vcs_hastatus_sum_command(vcs_node)

        for service_group in sgs['SERVICE_GROUPS']:
            if service_group['STATE'] == 'ONLINE':
                sg_list.append(service_group['GROUP'])

        return sg_list

    @attr('all', 'revert', 'story184851', 'story184851_tc04', 'bur_only_test')
    def test_04_p_prepare_restore_node_url(self):
        """
            @tms_id: torf_184851_tc04
            @tms_requirements_id: TORF-184851
            @tms_title: Prepare Restore Node
            @tms_description: Execute "litp prepare_restore"
                on a node in a single-cluster deployment.
            @tms_test_steps:
                @step: Execute "litp restore_model" on MS
                @result: Model successfully restored
                @step: Find the number of ONLINE
                    Service Groups in the VCS Cluster
                @result: Number of ONLINE SGs recorded
                @step: Execute "litp prepare_restore" on a node
                @result: Command executed successfully
                @result: Every item in LITP model under
                    restored node is in state "Initial"
                @step: Create LITP plan
                @result: Plan successfully created
                @step: Run LITP plan
                @result: Plan runs to completion
                @result: Every item in LITP model under
                    restored node is in state "Applied"
                @step: Reset passwords on restored node
                @result: Passwords reset successfully
                @step: Find the number of ONLINE
                    Service Groups in the VCS Cluster
                @result: Number of ONLINE SGs same as before prepare_restore
            @tms_test_precondition: None
            @tms_execution_type: Automated
        """
        self.log('info', '1. Run "litp restore_model" on MS.')
        self.execute_cli_restoremodel_cmd(self.ms_node)

        self.log('info', '2. Get a list of the Service Groups '
                         'currently ONLINE in the VCS Cluster.')
        sgs_online_before = self._list_online_sgs(self.restore_node)

        self.log('info', '3. Run "litp prepare_restore" on "{0}".'.format(
            self.restore_node_url))
        self.execute_cli_prepare_restore_cmd(
            self.ms_node, args="-p {0}".format(self.restore_node_url))

        self.log('info', '4. Check that everything under "{0}" is '
                         'in "Initial" state.'.format(self.restore_node_url))
        self._check_item_state(state='Initial', paths=[self.restore_node_url])

        self.log('info', '5. Execute "litp create_plan".')
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info', '6. Execute "litp run_plan".')
        self.execute_cli_runplan_cmd(self.ms_node)

        self.log('info', '6.1. Wait for the plan to succeed.')
        self.assertEqual(True, self.wait_for_plan_state(
            self.ms_node, const.PLAN_COMPLETE, timeout_mins=25),
                         "Plan did not complete successfully.")

        self.log('info', '7. Check everything under "{0}" is '
                         'in "Applied" state.'.format(self.restore_node_url))
        self._check_item_state(state='Applied', paths=[self.restore_node_url])

        self.log("info", "8. Set passwords on restored node.")
        # Remove restored node entry in known_hosts file.
        cmd = "sed -i '/{0}/d' {1}/known_hosts".format(
                self.restore_node, const.SSH_KEYS_FOLDER)
        _, _, rc = self.run_command(self.ms_node, cmd)
        self.assertEqual(0, rc)

        self.assertTrue(self.set_pws_new_node(self.ms_node, self.restore_node),
                        "Failed to set passwords on restored node.")
        # Ensure passwords set correctly
        _, stderr, rc = self.run_command(self.restore_node, 'hostname')
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)

        self.log('info', '9. Get a list of the Service Groups '
                         'currently ONLINE in the VCS Cluster.')
        sgs_online_after = self._list_online_sgs(self.restore_node)
        self.log('info', '9.1. Ensure the same number of Service Groups '
                         'are ONLINE after the prepare_restore as '
                         'before the prepare_restore.')
        self.assertEqual(sgs_online_before, sgs_online_after)

    @attr('all', 'expansion', 'story184851', 'story184851_tc05')
    def test_05_p_prepare_restore_node_url_multicluster(self):
        """
            @tms_id: torf_184851_tc05
            @tms_requirements_id: TORF-184851
            @tms_title: Prepare_Restore 1 node on multi-cluster system
            @tms_description: Execute "litp prepare_restore"
                on a node in a multi-cluster deployment.
            @tms_test_steps:
                @step: Create 3 new clusters with one node each
                @result: Items successfully created
                @step: Run expansion plan
                @result: Plan successfully completes
                @step: Execute "litp restore_model" on MS
                @result: Model successfully restored
                @step: Execute "litp prepare_restore" on a node
                @result: Command executed successfully
                @result: Every item in LITP model under
                restored node is in state "Initial"
                @result: Every item under every other
                node is in state "Applied"
                @step: Create LITP plan
                @result: Plan successfully created
                @step: Run LITP plan
                @result: Plan runs to completion
                @result: Every item in LITP model under
                restored node is in state "Applied"
            @tms_test_precondition: Test environment has 1 cluster with 1 node.
            @tms_execution_type: Automated
        """
        self.log('info', '1. Check test environment is 1 cluster with 1 node.')
        self.check_deployment_1_cluster_1_node()

        self.log('info', '2. Create three new clusters with one node each.')
        # Expand the LITP model with the new clusters and nodes
        self._expand_model()

        self.log('info', '3. Run an expansion plan.')
        self.run_and_check_plan(self.ms_node, const.PLAN_COMPLETE,
                                plan_timeout_mins=60,
                                add_to_cleanup=False)

        self.log('info', '4. Run "restore_model" command on MS.')
        self.execute_cli_restoremodel_cmd(self.ms_node)

        self.log('info', '5. Run "prepare_restore" command for {0}'.format(
            self.restore_node_url))
        self.execute_cli_prepare_restore_cmd(
            self.ms_node, args="-p {0}".format(self.restore_node_url))

        self.log('info', '6. Check system state after "prepare_restore"')
        self.log('info', '6.1. Check that everything under "{0}" is '
                         'in "Initial" state'.format(self.restore_node_url))
        self._check_item_state(state='Initial', paths=[self.restore_node_url])
        self.log('info', '6.2. Check that everything '
                         'else is in "Applied" state')
        self._check_item_state(state='Applied', paths=self.node_urls[1:])

        self.log('info', '7. Execute "litp create_plan".')
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info', '8. Execute "litp run_plan".')
        self.execute_cli_runplan_cmd(self.ms_node, add_to_cleanup=False)

        self.log('info', '8.1 Wait for the plan to succeed.')
        self.assertEqual(True, self.wait_for_plan_state(
            self.ms_node, const.PLAN_COMPLETE, timeout_mins=30),
                         "Plan did not complete successfully.")

        self.log('info', '9. Check that everything under "{0}" is '
                         'in "Applied" state'.format(self.restore_node_url))
        self._check_item_state(state='Applied', paths=[self.restore_node_url])
