"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2016
@author:    Roman Jarzebiak
@summary:   Bug LITPCDS-13803
            Error message in logs when "litpd" service is restarted while
            a plan is running
"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Bug13803(GenericTest):
    """
    Bug LITPCDS-13803
        Error message in logs when "litpd" service is restarted while
        a plan is running
    """

    def setUp(self):
        """ Runs before every single test """
        super(Bug13803, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.node1_path = self.find(self.ms_node, '/deployments', 'node')[0]
        self.node1_items_col_path = self.find(self.ms_node,
                                        self.node1_path,
                                        'ref-collection-of-software-item')[0]
        self.item_id = 'test13803_tc01'
        self.software_items_col_path = self.find(self.ms_node,
                                        '/software',
                                        'collection-of-software-item')[0]
        self.source_item_url = '{0}/{1}'.format(self.software_items_col_path,
                                        self.item_id)
        self.ms_items_col_path = self.find(self.ms_node,
                                        '/ms',
                                        'ref-collection-of-software-item')[0]
        self.ms_item_url = '{0}/{1}'.format(self.ms_items_col_path,
                                        self.item_id)
        self.node1_item_url = '{0}/{1}'.format(self.node1_items_col_path,
                                        self.item_id)

    def tearDown(self):
        """ Runs after every single test """
        super(Bug13803, self).tearDown()

    @attr('all', 'revert', 'bug13803', 'bug13803tc01')
    def test_01_n_restart_litp_while_plan_running(self):
        """
        @tms_id: litpcds_13803_tc01
        @tms_requirements_id: TORF-107258
        @tms_title: Verify that When a configuration task is stopped by
                    "litpd restart" no errors are logged
        @tms_description: Verify that if a "litpd restart" is issued while a
                          configuration task is running the plan stops and no
                          error are logged to '/var/log/messages'
        @tms_test_steps:
         @step: Create items which will generate configuration tasks
         @result: Items created successfully
         @step: Create and start running the plan
         @result: Plan starts successfully
         @step: Restart the litpd service and wait for the plan to stop
         @result: Plan is in stopped state
         @step: Check that no error msg "ERROR: Exception running background
             job" was logged to "/var/log/messages"
         @result: Specified error message not found in "/var/log/messages"
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        cursor_pos = self.get_file_len(self.ms_node, const.GEN_SYSTEM_LOG_PATH)
        self.log('info',
        '1. Create items which will generate config tasks')
        self.execute_cli_create_cmd(self.ms_node,
                                    self.source_item_url,
                                    'package',
                                    'name=telnet')

        for url in [self.ms_item_url, self.node1_item_url]:
            self.execute_cli_inherit_cmd(self.ms_node,
                                    url,
                                    self.source_item_url)

        self.log('info',
        '2. Create and start running the plan.')
        self.execute_cli_createplan_cmd(self.ms_node)
        self.execute_cli_runplan_cmd(self.ms_node)

        self.log('info',
        '3. Restart the litpd service and wait for the plan to stop.')
        self.restart_litpd_service(self.ms_node)
        plan_state_err_msg = "Plan is not in the expected state 'stopped'."
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                                                    const.PLAN_STOPPED),
                                                    plan_state_err_msg)

        item_state_err_msg = "'{0}' is not in an 'Initial' state as"\
                           " expected.".format(self.node1_item_url)
        self.assertEqual(self.get_item_state(self.ms_node,
                    self.node1_item_url),
                           'Initial',
                           item_state_err_msg)

        msg_to_check = 'ERROR: Exception running background job'
        self.log('info',
        '4. Assert that no error msg "{0}" was logged to "{1}".'. format(
            msg_to_check, const.GEN_SYSTEM_LOG_PATH))
        msg_errors = self.wait_for_log_msg(self.ms_node,
                                               'ERROR',
                                               const.GEN_SYSTEM_LOG_PATH,
                                               log_len=cursor_pos,
                                               return_log_msgs=True,
                                               timeout_sec=1)
        assert_f_err_msg = 'Unexpected message "{0}" found on '\
                '"{1}"'.format(msg_to_check, const.GEN_SYSTEM_LOG_PATH)
        self.assertFalse(self.is_text_in_list(msg_to_check, msg_errors),
                assert_f_err_msg)
