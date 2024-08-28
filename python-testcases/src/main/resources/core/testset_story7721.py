"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2015
@author:    Maria Varley
@summary:   LITPCDS-7721
            As a LITP user I want the config task requires (for all the tasks)
            to be recalculated each time I run create_plan so that litp
            generates a more robust puppet manifest
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from rest_utils import RestUtils
import test_constants as const
import json


class Story7721(GenericTest):
    """
    As a LITP user I want the config task requires (for all the tasks)
    to be recalculated each time I run create_plan so that litp generates
    a more robust puppet manifest
    """
    def setUp(self):
        """ Runs before every single test """
        super(Story7721, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        # self.mns = self.get_managed_node_filenames()
        self.rhel = RHCmdUtils()
        self.rest = RestUtils(self.get_node_att(self.ms1, 'ipv4'))
        self.expected_json = "2"

    def tearDown(self):
        """ Runs after every single test """
        super(Story7721, self).tearDown()

    def _check_manifest(self, manifest_file, search_item):
        """
        Description:
            grep a puppet manifest for a particular line
        Args:
            manifest_file (str): manifest file to be searched
            search_item (str): search item
        Return:
            list, The list of lines matching the given pattern
        """
        manifest_file_path = '{0}{1}'. \
                             format(const.PUPPET_MANIFESTS_DIR, manifest_file)
        cmd = self.rhel.get_grep_file_cmd(manifest_file_path, search_item)
        stdout, _, _ = self.run_command(self.ms1, cmd, default_asserts=True,
            su_root=True)
        self.assertNotEqual([], stdout)

        return stdout

    def _get_props_from_url_via_rest(self, item_url):
        """
        Description
            Get properties of the given item by issuing a REST request
        Args:
            item_url (str): Item path
        """
        stdout, stderr, status = self.rest.get(item_url)
        self.assertEqual('', stderr)
        self.assertEqual(200, status)
        props = json.loads(''.join(stdout))
        return props

    @attr('all', 'revert', 'story7721', 'story7721_tc08')
    def test_08_n_plan_failure_after_task_phase_successful(self):
        """
        @tms_id:
            litpcds_7721_tc08
        @tms_requirements_id:
            LITPCDS-7721
        @tms_title:
            Verify config tasks dependency managemnt
        @tms_description:
            Test that if a phase contains a task that has a dependency
            on a previously executed task and that phase is successful
            but the plan fails later, then the task is applied and persisted
            NOTE: also verifies Bug LITPCDS-9839
        @tms_test_steps:
        @step: Create items in the model that have dependent config tasks
        @result: Item created successfully
        @step: Run the deployment plan and wit until the
               'Create VCS service group for NIC "eth1"' is running'
        @result: Task "Create VCS service group for NIC "eth1"' is running
        @step: Stop the plan by restarting "litpd" service
        @result: Plan is stopped
        @result: Configuration tasks that were executed before the
                 plan was stopped have completed successfully
        @result: The puppet manifest files contain definition of the resources
                 for which the config task completed
        @result: The "cluster" item type is in "Applied" state and its APD
                 flag is set to "false"
        @result: The item that depends on cluster item is in "Initial" state
                 and its APD flag is set to "false"
        @result: The items that do not depend on "cluster" item are in
                 "Applied" state and their APD flag is set to "true"
        @step: Create the plan again
        @result: Plan created successfully
        @result: Config tasks that completed successfully before the plan was
                 stopped are not in the plan
        @step: Run the plan again
        @result: Plan completed successfully
        @result: Puppet manifest definition for items successfully created are
                 still present
        @result: All new items and cluster item are in "Applied" state and
                 their APD flag is set to "true"
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Create a "network", bridge", "eth" and "vlan" items on the MS')
        coll_network_url = self.find(self.ms1,
                                     "/infrastructure",
                                     "network",
                                     rtn_type_children=False)[0]
        network_url = '{0}/network_7721_tc08'.format(coll_network_url)
        props = "name='network_7721_tc08' subnet='10.10.10.0/24'"
        self.execute_cli_create_cmd(self.ms1, network_url, "network", props)

        self.log('info',
        '2. Create "bridge", "vlan" and "eth" items on node1')
        n1_url = self.find(self.ms1, "/deployments", "node")[0]
        n1_if1 = self.verify_backup_free_nics(self.ms1, n1_url)[0]

        n1_eth_url = n1_url + "/network_interfaces/eth_7721"
        props = "device_name='{0}' macaddress='{1}'".\
                       format(n1_if1["NAME"], n1_if1["MAC"])
        self.execute_cli_create_cmd(self.ms1, n1_eth_url, "eth", props)

        n1_bridge_url = n1_url + "/network_interfaces/br_7721"
        props = "ipaddress='10.10.10.22' device_name='br7721' \
                 ipv6address='fe05::2' network_name='network_7721_tc08'"
        self.execute_cli_create_cmd(self.ms1, n1_bridge_url, "bridge", props)

        n1_vlan_url = n1_url + "/network_interfaces/vlan_7721"
        props = "device_name='{0}.629' bridge='br7721'". \
                        format(n1_if1["NAME"])
        self.execute_cli_create_cmd(self.ms1, n1_vlan_url, "vlan", props)

        self.log('info',
        '3. Run the plan until the "Create VCS service group for NIC "eth1" '
           'is running')
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_showplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        phase_to_stop = 'Create VCS service group for NIC "eth1"'
        self.assertTrue(self.wait_for_task_state(self.ms1,
                                                 phase_to_stop,
                                                 const.PLAN_TASKS_RUNNING,
                                                 ignore_variables=False,
                                                 seconds_increment=1))

        self.log('info',
        '4. Stop the plan by restarting litpd service')
        self.restart_litpd_service(self.ms1)
        self.assertTrue(self.wait_for_plan_state(self.ms1, const.PLAN_STOPPED))

        self.log('info',
        '5. Check that node 1 "vlan" and "bridge" configuration tasks '
           'completed successfully')
        plan = self.execute_cli_showplan_cmd(self.ms1)[0]

        successful_task_1 = 'Configure bridge "br7721" on node "node1"'
        self.assertTrue(self.is_text_in_list(successful_task_1, plan),
            'Task "{0}" not found in plan'.format(successful_task_1))

        successful_task_2 = 'Configure vlan "eth1.629" on node "node1"'
        self.assertTrue(self.is_text_in_list(successful_task_2, plan),
            'Task "{0}" not found in plan'.format(successful_task_2))

        self.log('info',
        '6. Check that the successful tasks in phase 2 are in the manifest '
            'file')
        manifest_constents = self._check_manifest("node1.pp", "br7721")
        task_br7721 = 'task_node1__litpnetwork_3a_3aconfig__br7721'
        self.assertTrue(
            self.is_text_in_list(task_br7721, manifest_constents),
            "Task for br7721 not found in manifest")

        manifest_constents = self._check_manifest("node1.pp", "eth1_2e629")
        task_eth1_2e629 = 'task_node1__litpnetwork_3a_3aconfig__eth1_2e629'
        self.assertTrue(
            self.is_text_in_list(task_eth1_2e629, manifest_constents),
            "Task for eth1_2e629 not found in manifest")

        self.log('info',
        '7. Verify that the cluster item-type is in "Applied" state and '
           '"applied_properties_indeterminable is set to "false" '
           '(bug LITPCDS-9839)')
        cluster_url = self.find_children_of_collect(self.ms1,
                                                    "/deployments",
                                                    "cluster")[0]

        props = self._get_props_from_url_via_rest(cluster_url)
        self.assertFalse(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_bridge_url)
        self.assertFalse(props.get('applied_properties_determinable'))
        self.assertEqual('Initial', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_eth_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_vlan_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        self.log('info',
        '8. Create the plan again and check that successful tasks are not '
           'present')
        #
        # This section needs to be improved.
        # We need to verify that all items with APD false need to have a config
        # task in the plan.
        # The current test code works but it is not accurate
        #
        self.execute_cli_createplan_cmd(self.ms1)
        plan = self.execute_cli_showplan_cmd(self.ms1)[0]

        self.assertTrue(self.is_text_in_list(successful_task_1, plan),
            'Previously successfully executed task "{0}" found in plan'.
            format(successful_task_1))

        self.assertFalse(self.is_text_in_list(successful_task_2, plan),
            'Previously successfully executed task "{0}" found in plan'.
            format(successful_task_1))

        self.log('info',
        '9. Run the plan')
        self.execute_cli_runplan_cmd(self.ms1)
        plan_complete = self.wait_for_plan_state(self.ms1,
                                                 const.PLAN_COMPLETE,
                                                 timeout_mins=10)
        self.assertTrue(plan_complete)

        self.log('info',
        '10. Check that previously created entries in manifest are not '
            'removed')
        manifest_constents = self._check_manifest("node1.pp", "br7721")
        self.assertTrue(
            self.is_text_in_list(task_br7721, manifest_constents),
            "dependency not in manifest")

        manifest_constents = self._check_manifest("node1.pp", "eth1_2e629")
        self.assertTrue(
            self.is_text_in_list(task_eth1_2e629, manifest_constents),
            "dependency not in manifest")

        self.log('info',
        '11. Verify state and APD of the relevant items')
        # "cluster" item state and APD bug LITPCDS-9839
        props = self._get_props_from_url_via_rest(cluster_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_bridge_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_eth_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))

        props = self._get_props_from_url_via_rest(n1_vlan_url)
        self.assertTrue(props.get('applied_properties_determinable'))
        self.assertEqual('Applied', props.get('state'))
