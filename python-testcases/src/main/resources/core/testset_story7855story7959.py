'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2015
@author:    Maria Varley
@summary:   Integration test to determine if the "applied_properties"
            associated with an item are determinable
            Agile: STORIES LITPCDS-7855, LITPCDS-7959
'''

from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
import json


class Story7855Story7959(GenericTest):
    '''
    As a plugin-developer I want to be able to determine
    if the "applied_properties" associated with an item
    are determinable and the model item state transitions
    should use this flag when needed
    As a LITP User I want to be made aware when
    the applied properties are indeterminable
    '''
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
        super(Story7855Story7959, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        self.ms_ip_address = self.get_node_att(self.ms1, 'ipv4')
        self.rest = RestUtils(self.ms_ip_address)
        self.rhel = RHCmdUtils()

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
        super(Story7855Story7959, self).tearDown()

    def _assert_apd_with_rest(self, item_path, apd):
        """
        Description:
            Check that property "applied_property_determinable" is correctly
            handled both by CLI and REST interface (LITPCDS-7959)
            REST GET always contains property "applied_property_determinable"
            set to either "true" or "false"
        Args:
            item_path (str): the item we are checking the APD flag on
            apd (bool): the expected value of the APD flag
        """
        stdout, stderr, status = self.rest.get(item_path)
        self.assertEqual('', stderr)
        self.assertEqual(200, status)
        props = json.loads(''.join(stdout))
        self.assertEqual(apd,
                         props.get('applied_properties_determinable', None))

    @attr('all', 'revert', 'story7855_7959', 'story7855_7959_tc06')
    def test_06_n_task_not_associated_with_model_item_fails(self):
        """
        @tms_id:
            litpcds_7855
        @tms_requirements_id:
            LITPCDS-7855, LITPCDS-7959
        @tms_title:
            Verify "Applied Property Determinable" flag management
        @tms_description:
            Verify the management of the "Applied Property Determinable" under
            a number of conditions
        @tms_test_steps:
        @step: Create a new item with valid properties in the model
        @result: Item created successfully
        @step: Update the item just created with a valid property value
        @result: Item updated successfully
        @result: The item is in "Updated" state
        @result: The item APD flag is set to true
        @step: Create a second item with an invalid property that will cause
               the plan to fail
        @result: Item created successfully
        @result: Attempt to deploy the items created/updated
        @result: The deployment plan fails
        @result: The valid item is in "Applied"
        @result: The APD flag of the valid item is set to "true"
        @result: The invalid item is in "Initial" state
        @result: The APD flag of the invalid item is set to "false"
        @step: Restart "litpd" service
        @result: The litpd service restarted successfully
        @result: The state and APD flag of the items did not change
        @step: Update both the valid and invalid item so that they both have
               valid properties
        @result: Items are updated successfully
        @result: The valid item is in "Updated"
        @result: The APD flag of the valid item is still set to "true"
        @result: The invalid item is still in "Initial" state
        @result: The APD flag of the invalid item is still set to "false"
        @step: Deploy the changes
        @result: The plan completed successfully
        @result: The valid item is in "Applied"
        @result: The APD flag of the valid item is set to "true"
        @result: The invalid item is in "Applied" state
        @result: The APD flag of the invalid item is set to "true"
        @step: Update an item with an invalid property
        @result: The item updated successfully
        @result: The item is in "Updated" state
        @result: The ADP flag of the item is set to "true"
        @step: Attempt to deploy the change
        @result: The plan fails
        @result: The item is in "Updated" state
        @result: The ADP flag of the item is set to "false"
        @step: Remove the item from the model
        @result: The item is in "ForRemoval" state
        @result: The ADP flag of the item is set to "false"
        @step: Restart "litpd" service
        @result: The litpd service restarted successfully
        @result: The state and APD flag of the item did not change
        @step: Update the item with an invalid property
        @result: The item is in "Updated" state
        @result: The ADP flag of the item is set to "false"
        @step: Restart "litpd" service
        @result: The litpd service restarted successfully
        @result: The state and APD flag of the item did not change
        @step: Update the item with a valid property
        @result: The item is in "Updated" state
        @result: The ADP flag of the item is set to "false"
        @step: Remove the item from the model
        @result: The item is in "ForRemoval" state
        @result: The ADP flag of the item is set to "false"
        @step: Update the item with a valid property
        @result: The item is in "Updated" state
        @result: The ADP flag of the item is set to "false"
        @step: Restart "litpd" service
        @result: The litpd service restarted successfully
        @result: The state and APD flag of the item did not change
        @step: Remove the item from the model
        @result: The item is in "ForRemoval" state
        @result: The ADP flag of the item is set to "false"
        @step: Run the plan to remove the item
        @result: Plan completed successfully
        @result: Item does not exist in model
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Define resources to use in this test')
        n1_path = self.find(self.ms1, "/deployments", "node", True)[0]
        n1_name = self.get_node_filename_from_url(self.ms1, n1_path)
        sysparam_n1_config_path = self.find(self.ms1,
                                            n1_path,
                                            "sysparam-node-config")[0]

        sp1 = {
            'key': "net.ipv4.ip_forward",
            'url': '{0}/params/7855test06a'.format(sysparam_n1_config_path),
            'item_type': 'sysparam',
            'valid_prop1': 'key="net.ipv4.ip_forward" value="599"',
            'valid_prop2': 'key="net.ipv4.ip_forward" value="499"',
            'valid_prop3': 'key="net.ipv4.ip_forward" value="500"'
        }

        sp2 = {
            'key': "kernel.msgmax",
            'url': '{0}/params/7855test06b'.format(sysparam_n1_config_path),
            'item_type': 'sysparam',
            'invalid_prop': 'key="kernel.msgmax" value="val"',
            'valid_prop': 'key="kernel.msgmax" value="65536"'
        }

        self.log('info',
        '2. Backup "sysctl.conf" file on node1')
        self.backup_file(n1_name, const.SYSCTL_CONFIG_FILE)

        try:
            self.log('info',
            '3. Create a new sysparam item on node1')
            self.execute_cli_create_cmd(self.ms1,
                                        sp1['url'],
                                        sp1['item_type'],
                                        props=sp1['valid_prop1'])

            self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE, 10)

            self.log('info',
            '4. Update the sysparam item just created and check that the new '
               'sysparam item is in "Updated" state and its APD flag is set '
               'to "true"')
            self.execute_cli_update_cmd(self.ms1,
                                        sp1['url'],
                                        props=sp1['valid_prop2'])

            sp1_state = self.get_item_state(self.ms1, sp1['url'])
            self.assertEqual("Updated", sp1_state)
            self._assert_apd_with_rest(sp1['url'], apd=True)

            self.log('info',
            '5. Deploy a sysparam item that will cause the plan to fail. '
               'Check that item with valid property is in "Applied" state '
               'and its APD flag set to "true" while the item invalid '
               'property is in "Initial" state and APD is set to "false"')
            self.execute_cli_create_cmd(self.ms1,
                                        sp2['url'],
                                        sp2['item_type'],
                                        props=sp2['invalid_prop'])

            self.run_and_check_plan(self.ms1, const.PLAN_FAILED, 10)

            sp1_state = self.get_item_state(self.ms1, sp1['url'])
            sp2_state = self.get_item_state(self.ms1, sp2['url'])

            self.assertEqual('Applied', sp1_state)
            self._assert_apd_with_rest(sp1['url'], apd=True)
            self.assertEqual(
                'Initial (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '6. Restart "litp" service and check that item states and APD '
               'have not changed')
            self.restart_litpd_service(self.ms1)

            sp1_state = self.get_item_state(self.ms1, sp1['url'])
            sp2_state = self.get_item_state(self.ms1, sp2['url'])

            self.assertEqual('Applied', sp1_state)
            self._assert_apd_with_rest(sp1['url'], apd=True)

            self.assertEqual(
                'Initial (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '7. Update item with valid property with different valid property '
               'and item with invalid property with a valid property. '
               'Check that item with valid property is in "Updated" state '
               'and its APD flag set to "true" while the item with invalid '
               'property is in "Initial" state and APD is set to "false"')
            self.execute_cli_update_cmd(self.ms1,
                                        sp1['url'],
                                        props=sp1['valid_prop3'])

            self.execute_cli_update_cmd(self.ms1,
                                        sp2['url'],
                                        props=sp2['valid_prop'])

            sp1_state = self.get_item_state(self.ms1, sp1['url'])
            sp2_state = self.get_item_state(self.ms1, sp2['url'])

            self.assertEqual('Updated', sp1_state)
            self._assert_apd_with_rest(sp1['url'], apd=True)

            self.assertEqual(
                'Initial (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '8. Deploy the changes and check that both items are in '
               '"Applied" state and their APD is set to "true"')
            self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE, 10)
            sp1_state = self.get_item_state(self.ms1, sp1['url'])
            sp2_state = self.get_item_state(self.ms1, sp2['url'])

            self.assertEqual('Applied', sp1_state)
            self._assert_apd_with_rest(sp1['url'], apd=True)

            self.assertEqual('Applied', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=True)

            self.log('info',
            '9. Update a model item that will cause the plan to fail. '
               'Check that the item is in "Updated" state and its APD flag '
               'is set to "true"')
            self.execute_cli_update_cmd(self.ms1,
                                        sp2['url'],
                                        props=sp2['invalid_prop'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])

            self.assertEqual('Updated', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=True)

            self.log('info',
            '10. Attempt to deploy the model and check that the item is in '
                '"Update" state and its APD flag is set to "false"')
            self.run_and_check_plan(self.ms1, const.PLAN_FAILED, 10)

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
                'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '11. Restart the litp service and check that state and APD flag '
                'of the item have not changed')
            self.restart_litpd_service(self.ms1)
            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '12. Remove the invalid item from the model and check that the '
                'item is now in "ForRemoval" state and its APD is set '
                'to "false"')
            self.execute_cli_remove_cmd(self.ms1, sp2['url'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'ForRemoval (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '13. Restart the litp service and check that state and APD flag '
                'of the item have not changed')
            self.restart_litpd_service(self.ms1)
            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'ForRemoval (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '14. Update the item with invalid property again and check that '
                'the item is in "Update" state and its APD is set to "false"')
            self.execute_cli_update_cmd(self.ms1,
                                        sp2['url'],
                                        props=sp2['invalid_prop'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '15. Restart the litp service and check that state and APD flag '
                'of the item have not changed')
            self.restart_litpd_service(self.ms1)
            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '16. Remove the invalid item and check that it is in "ForRemoval" '
                'state and its APD is set to "false')
            self.execute_cli_remove_cmd(self.ms1, sp2['url'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'ForRemoval (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '17. Update the item with a valid property and check that it is '
                'state "Updated" and its APD is fset to "false"')
            self.execute_cli_update_cmd(self.ms1,
                                        sp2['url'],
                                        props=sp2['valid_prop'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '18. Restart litp service and check that state and APD flag of '
                'the item have not changed')
            self.restart_litpd_service(self.ms1)

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'Updated (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '19. Remove the item and check it is now in "ForRemoval" state '
                'and its APD flag is set to "false"')
            self.execute_cli_remove_cmd(self.ms1, sp2['url'])

            sp2_state = self.get_item_state(self.ms1, sp2['url'])
            self.assertEqual(
             'ForRemoval (deployment of properties indeterminable)', sp2_state)
            self._assert_apd_with_rest(sp2['url'], apd=False)

            self.log('info',
            '20. Run the plan to remove the item and check that the item is '
                'not loger in the model')

            self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE, 10)

            items = self.find(self.ms1,
                              sp2['url'],
                              sp2['item_type'],
                              assert_not_empty=False)
            self.assertEqual([], items,
                'Item "{0}" still found on model after removal'.
                format(sp2['url']))

        finally:
            self.log('info',
            'FINALLY: Restore initial "sysctl.conf" file on node1')
            self.restore_backup_files()

            self.log('info',
            'FINALLY: Reload "sysctl.conf" file on node1')
            cmd = self.rhel.get_sysctl_cmd(
                            '-e -p {0}'.format(const.SYSCTL_CONFIG_FILE))
            self.run_command(n1_name, cmd, su_root=True, default_asserts=True)
