"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2016
@author:    David Hong-Minh
@summary:   Integration tests for managing
            LITP Task Timeout
            Agile: BUG LITPCDS-11610
"""
import os
import re
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants
from litp_generic_utils import GenericUtils


class Bug11610(GenericTest):
    """
    Task didn't timeout after 8 hours: "Update node host file"
    """

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
        super(Bug11610, self).setUp()

        # 2. Set up variables used in the test
        self.ms_node = self.get_management_node_filenames()[0]
        self.mn_nodes = self.get_managed_node_filenames()
        self.plugin_id = 'bug11610'
        self.redhatutils = RHCmdUtils()
        self.software_items = "/software/items"
        self.g_utils = GenericUtils

        self.error_messages = dict()
        self.error_messages['puppet_phase_timeout'] = \
            'Incorrect "puppet_phase_timeout" value specified ' \
            'in /etc/litpd.conf. Valid "puppet_phase_timeout" ' \
            'value is an integer within a range [0, 604800]'
        self.error_messages['puppet_poll_frequency'] = \
            'Incorrect "puppet_poll_frequency" value specified ' \
            'in /etc/litpd.conf. Valid "puppet_poll_frequency" ' \
            'value is an integer: 0 or [60, 3600]'
        self.error_messages['puppet_poll_count'] = \
            'Incorrect "puppet_poll_count" value specified ' \
            'in /etc/litpd.conf. Valid "puppet_poll_count" ' \
            'value is an integer within a range [1, 1000]'
        self.error_messages['puppet_mco_timeout'] = \
            'Incorrect "puppet_mco_timeout" value specified ' \
            'in /etc/litpd.conf. Valid "puppet_mco_timeout" ' \
            'value is an integer within a range [300, 900]'

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
        super(Bug11610, self).tearDown()

    @staticmethod
    def get_local_rpm_paths(path, rpm_id):
        """
        Description:
        Method that returns a list of absolute paths to the
        RPMs required to be installed for testing
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_id in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
            ]

    def _install_rpms(self):
        """
        Description:
        Method that installs plugin and extension
        if they are not already installed
        """
        # Check if the plugin is already installed
        _, _, rcode = self.run_command(
            self.ms_node, self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True)

        # If not, copy plugin and extension onto MS
        if rcode == 1:
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(self.ms_node, local_rpm_paths))

    def _update_litpd_conf(self, node, param, update_val, litp_file,
                           expect_positive=True, restart_litpd=False):
        """
        Description:
        Method that updates a parameter in the litpd.conf file to a specified
        value

        Args:
        node (str): Node you want to run command on

        param (str): parameter to update

        update_val (str): value parameter will be updated to

        litp_file (str) : file in which the parameter exists

        expect_positive (bool) : if you expect the litpd/celeryd restart
                                to be successful after litpd.conf
                                update. Default is true
        restart_litpd (bool) : if true will restart the litpd service after
                              updating the litpd.conf file. If false will
                              restart the celeryd service. Default is true
        Returns:
        orig_val (str): original value of parameter

        Result:
        Parameter in litpd.conf is updated to specified value
        """

        service_name = 'celeryd'

        if restart_litpd:
            service_name = "litpd"

        search_param = ["^{0}".format(param)]
        grep_cmd = self.redhatutils.get_grep_file_cmd(litp_file, search_param)

        # Execute the grep command to find current value of the parameter
        outlist, _, _ = \
            self.run_command(node, grep_cmd, su_root=True)

        # Save current timeout value
        old_val = outlist[0].split("=")[1].strip()
        old_param_val = param + " = " + old_val

        # Update this value to a new value
        new_param_val = param + " = " + update_val
        sed_cmd = self.redhatutils.get_replace_str_in_file_cmd(
            old_param_val,
            new_param_val,
            litp_file,
            '-i'
        )

        if expect_positive:
            self.run_command(node, sed_cmd, default_asserts=True, su_root=True)

            # Restart service so changes take effect
            self.restart_service(self.ms_node, service_name)

        else:
            self.run_command(node, sed_cmd, default_asserts=False,
                             su_root=True)

            # Restart service so changes take effect
            stdout, stderr, rc = self.restart_service(self.ms_node,
                                                      service_name,
                                                      assert_success=False)
            error_msg = self.error_messages[param]
            self.log('info', error_msg)
            self.assertTrue(self.is_text_in_list(error_msg, stdout))
            self.assertEqual([], stderr)
            self.assertNotEqual(0, rc)

        return old_val

    def _chk_param_val_applied(self,
                               log_output,
                               expected_conf_val):
        """
        Description:
        Method that checks that a parameter in the litpd.conf file is
        applied from the system by checking syslog.

        Args:

        log_output (list): log message(s) from /var/log/messages

        expected_conf_val (int): The value from litpd.conf which will be
            checked against syslog results.
        """

        timestamps = []
        for log_msg in log_output:

            msg = re.search(r'\w{3}\s+\d{1,2} \d{2}:\d{2}:\d{2}', log_msg)
            timestamps.append(msg.group())

        actual_val_in_sec_task = self.g_utils.diffdates(timestamps[0],
                                                        timestamps[1])
        actual_val_in_sec_plan = self.g_utils.diffdates(timestamps[2],
                                                        timestamps[3])

        # Allow 20 seconds tolerance which is equivalent to one mco command
        # to be run and make sure messages are after test start time
        self.assertTrue(actual_val_in_sec_task - expected_conf_val <= 20)
        self.assertTrue(actual_val_in_sec_plan - expected_conf_val <= 20)

    @attr('manual-test', 'revert', 'bug11610', 'bug11610_t01')
    def test_01_n_chk_puppet_parameters_configurable(self):
        """
        @tms_id: litpcds_11610_tc01
        @tms_requirements_id: LITPCDS-11610
        @tms_title: Check puppet related vlues in /etc/litpd.conf configurable
        @tms_description: Ensure that the Puppet timeout values in the
            /etc/litpd.conf file can only be updated using valid values.
            Note:
            See Confluence page for
            'How Long Does It Take for Different Tasks to Time Out?'
            http://confluence-nam.lmera.ericsson.se
            /pages/viewpage.action?pageId=52601503
        @tms_test_steps:
            @step: Attempt to start litp with valid
                   puppet_phase_timeout values
            @result: Litp starts successfully
            @step: Attempt to start litp with invalid
                   puppet_phase_timeout values
            @result: Litp doesn't start
            @step: Attempt to start litp with valid
                puppet_poll_frequency values
            @result: Litp starts successfully
            @step: Attempt to start litp with invalid
                   puppet_poll_frequency values
            @result: Litp doesn't start
            @step: Attempt to start litp with valid
                   puppet_poll_count values
            @result: Litp starts successfully
            @step: Attempt to start litp with invalid
                   puppet_poll_count values
            @result: Litp doesn't start
            @step: Attempt to start litp with valid
                   puppet_mco_timeout values
            @result: Litp starts successfully
            @step: Attempt to start litp with invalid
                   puppet_mco_timeout values
            @result: Litp doesn't start
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # path to /etc/litpd.conf and a backup of the
        # back up the file so it can be restored on cleanup
        # in case of test failures
        litp_file = test_constants.LITPD_CONF_FILE
        self.backup_file(self.ms_node, litp_file)

        # puppet_phase_timeout

        # Manage timeout constraints in LITP
        # The puppet_phase_timeout parameter defines the
        # timeout value (in seconds) for the Puppet phase
        # The value of this parameter can be any integer
        # between 0 and 604800
        search_val = "puppet_phase_timeout"

        puppet_phase_values_p = ["0", "1000", "604800"]
        puppet_phase_values_n = ["-1", "604801", "abc", "", "3,50"]
        restore = ""

        self.log('info', '1. check if litp starts normally with valid '
                 'puppet_phase_timeout values in litpd.conf file')

        for p_value in puppet_phase_values_p:
            old = self._update_litpd_conf(
                self.ms_node, search_val, p_value, litp_file,
                expect_positive=True, restart_litpd=True)
            if not restore:
                restore = old

        self.log('info', '2. check that litp doesn\'t start with invalid '
                 'puppet_phase_timeout values in litpd.conf file')
        for n_value in puppet_phase_values_n:
            self._update_litpd_conf(
                self.ms_node, search_val, n_value, litp_file,
                expect_positive=False, restart_litpd=True)

        self._update_litpd_conf(
            self.ms_node, search_val, restore, litp_file,
            expect_positive=True, restart_litpd=True)

        # puppet_poll_frequency

        # The puppet_poll_frequency parameter defines the frequency
        # (in seconds) of Puppet polling, where the Puppet polling mechanism
        # polls the Puppet status to determine if the configuration is still
        # being applied.
        # Valid "puppet_poll_frequency" value is an integer: 0 or [60, 3600]
        search_val = "puppet_poll_frequency"

        puppet_pf_values_p = ["0", "60", "1000", "3600"]
        puppet_pf_values_n = ["-1", "1", "59", "3601", "abc", "", "73,50"]
        restore = ""

        self.log('info', '3. check if litp starts normally with valid '
                 'puppet_poll_frequency values in litpd.conf file')
        for p_value in puppet_pf_values_p:
            old = self._update_litpd_conf(
                self.ms_node, search_val, p_value, litp_file,
                expect_positive=True, restart_litpd=True)
            if not restore:
                restore = old

        self.log('info', '4. check that litp doesn\'t start with invalid '
                 'puppet_poll_frequency values in litpd.conf file')
        for n_value in puppet_pf_values_n:
            self._update_litpd_conf(
                self.ms_node, search_val, n_value, litp_file,
                expect_positive=False, restart_litpd=True)

        self._update_litpd_conf(
            self.ms_node, search_val, restore, litp_file,
            expect_positive=True, restart_litpd=True)

        # puppet_poll_count

        # The puppet_poll_count parameter defines the number of times
        # that Puppet is polled.
        # The value of this parameter can be any integer between 1 and 1000
        search_val = "puppet_poll_count"
        puppet_pc_values_p = ["1", "60", "1000"]
        puppet_pc_values_n = ["-1", "0", "1001", "abc", "", "3,50"]
        restore = ""

        self.log('info', '5. check if litp starts normally with valid '
                 'puppet_poll_count values in litpd.conf file')
        for p_value in puppet_pc_values_p:
            old = self._update_litpd_conf(
                self.ms_node, search_val, p_value, litp_file,
                expect_positive=True, restart_litpd=True)
            if not restore:
                restore = old

        self.log('info', '6. check that litp doesn\'t start with invalid '
                 'puppet_poll_count values in litpd.conf file')
        for n_value in puppet_pc_values_n:
            self._update_litpd_conf(
                self.ms_node, search_val, n_value, litp_file,
                expect_positive=False, restart_litpd=True)

        self._update_litpd_conf(
            self.ms_node, search_val, restore, litp_file,
            expect_positive=True, restart_litpd=True)

        # puppet_mco_timeout

        # The puppet_mco_timeout parameter defines the time (in seconds) that
        # the Puppet manager waits for a successful MCO Puppet command.
        # The value of this parameter can be any integer between 300 and 900

        search_val = "puppet_mco_timeout"
        puppet_mcot_values_p = ["300", "600", "900"]
        puppet_mcot_values_n = ["-1", "299", "901", "abc", "", "500,50"]
        restore = ""

        self.log('info', '7. check if litp starts normally with valid '
                 'puppet_mco_timeout values in litpd.conf file')
        for p_value in puppet_mcot_values_p:
            old = self._update_litpd_conf(
                self.ms_node, search_val, p_value, litp_file,
                expect_positive=True, restart_litpd=True)
            if not restore:
                restore = old

        self.log('info', '8. check that litp doesn\'t start with invalid '
                 'puppet_mco_timeout values in litpd.conf file')
        for n_value in puppet_mcot_values_n:
            self._update_litpd_conf(
                self.ms_node, search_val, n_value, litp_file,
                expect_positive=False, restart_litpd=True)

        self._update_litpd_conf(
            self.ms_node, search_val, restore, litp_file,
            expect_positive=True, restart_litpd=True)

    @attr('manual-test', 'revert', 'bug11610', 'bug11610_t02')
    def test_02_n_chk_puppet_mco_timeout_configurable(self):
        """
        @tms_id: litpcds_11610_tc02
        @tms_requirements_id: LITPCDS-11610
        @tms_title: Check that puppet_mco_timeout value is configurable
        @tms_description: Ensure the puppet_mco_timeout timeout
            value in the /etc/litpd.conf file can be updated and applies.
        @tms_test_steps:
         @step: Install test plugin RPM.
         @result: RPM installed successfully
         @step: Update puppet_mco_timeout in config file
            and save current value
         @result: litp restarts with new config value
         @step: Create model item that generates a puppet config task
         @result: Items can be created
         @step: Create and run plan
         @result: Plan can be created and runs
         @step: Poweroff node 1 and wait for plan to fail
         @result: Plan fails
         @step: Check that the new value have been adopted
           by checking for expected log entries
         @result: The parameter, puppet_mco_timeout is applied
           as defined in litpd.conf file
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        search_val1 = "puppet_mco_timeout"
        update_val1 = "360"
        litp_conf_contents = self.get_file_contents(self.ms_node,
                                                    test_constants.
                                                    LITPD_CONF_FILE,
                                                    su_root=True)
        puppet_poll_freq_value = \
            self.g_utils.get_prop_from_file(litp_conf_contents,
                                            'puppet_poll_frequency')
        self.assertNotEqual(None, puppet_poll_freq_value)
        puppet_poll_count_value = \
            self.g_utils.get_prop_from_file(litp_conf_contents,
                                            'puppet_poll_count')
        self.assertNotEqual(None, puppet_poll_count_value)

        pln_tmt_after_fl_task = \
            int(puppet_poll_freq_value) * int(puppet_poll_count_value)
        self.log('info', 'Step 1. Install test plugin RPM.')
        self._install_rpms()

        self.log('info', 'Step 2. Define messages used to calculate the '
                 'puppet_mco_timeout.')
        msgs_to_check = []

        msgs_to_check.append("INFO: Phase 2 completed")
        msgs_to_check.append("ERROR: (McoTimeoutException(...), " \
                "'Cannot run disable from agent puppet on node1: " \
                "No answer from node node1, no more retries')")
        msgs_to_check.append("INFO: Phase 3 failed")
        msgs_to_check.append("ERROR: (McoTimeoutException(...), " \
                "'Cannot run clean from agent puppetlock on node1: " \
                "No answer from node node1, no more retries')")

        # Manage timeout constraints in LITP
        # The puppet_mco_timeout parameter defines the time (in seconds) that
        # the Puppet manager waits for a successful MCO Puppet command.

        self.log('info', 'Step 3. Update puppet_mco_timeout in config file and'
                 ' save current value')
        orig_val1 = self._update_litpd_conf(
            self.ms_node, search_val1, update_val1, test_constants.
            LITPD_CONF_FILE)

        self.log('info', 'Step 4. Create model item that generate a '
                 'puppet config task')
        # Find paths to use in model item creation
        sitem = os.path.join(self.software_items, "package" + "{0}")

        nodes_uri = self.find(
            self.ms_node, path='/deployments', resource='node')
        node1_deployment = nodes_uri[0] + "/items/" + "package" + "{0}"
        node2_deployment = nodes_uri[1] + "/items/" + "package" + "{0}"

        self.log('info', 'Step 4a. Create a model item 1a that generates a'
                 ' Config Task to create the resource')
        props = "name=telnet"
        self.execute_cli_create_cmd(
            self.ms_node, sitem.format("1a"), "package", props)

        self.log('info', 'Step 4b. Create a model item 1b that inherits model'
                 ' item 1a and generates a Config Task to create the '
                 'resource on node1')
        self.execute_cli_inherit_cmd(
            self.ms_node, node1_deployment.format("1b"), sitem.format("1a"))

        self.execute_cli_inherit_cmd(
            self.ms_node, node2_deployment.format("1b"), sitem.format("1a"))

        try:
            # Find the current log position so all log messages before
            # this test can be ignored
            start_log_pos = self.get_file_len(self.ms_node,
                                              test_constants.
                                              GEN_SYSTEM_LOG_PATH)

            self.log('info', 'Step 5. Execute "create_plan" command')
            self.execute_cli_createplan_cmd(self.ms_node)

            self.log('info', 'Step 6. Execute "run_plan" command')
            self.execute_cli_runplan_cmd(self.ms_node)

            self.log('info', 'Wait for first task (Phase 1) to be successful '
                     'before powering down node1. Callback task (Phase 2) '
                     '(generated by test plugin) will wait for node1 before '
                     'completing and indicates the start of '
                     'puppet_mco_timeout')
            self.assertTrue(self.
                            wait_for_task_state(self.ms_node,
                                                'Lock VCS on node "{0}"'.
                                                format(self.mn_nodes[0]),
                                                test_constants.
                                                PLAN_TASKS_SUCCESS,
                                                ignore_variables=False))

            self.log('info', 'Step 7. Poweroff node1')
            self.poweroff_peer_node(self.ms_node, self.mn_nodes[0])

            self.log('info', 'Step 8. Wait for plan to fail It indicates that'
                     ' the end of the puppet_mco_timeout')
            phase_3_failed = ('Install package "telnet" on node "node1"'.
                              format(self.mn_nodes[0]))

            self.assertTrue(self.
                            wait_for_task_state(self.ms_node,
                                                phase_3_failed,
                                                test_constants.
                                                PLAN_TASKS_FAILED,
                                                False),
                            'Telnet package is installed in not '
                            'available node')

            self.assertTrue(self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_FAILED,
                timeout_mins=pln_tmt_after_fl_task))

            log_msgs = []
            for msg_to_check in msgs_to_check:

                log_msgs.append(self.check_for_log(self.ms_node, msg_to_check,
                               test_constants.GEN_SYSTEM_LOG_PATH,
                               start_log_pos,
                               return_log_msg=True)[0])

            self.log('info', 'Step 9. Check that the new value has '
                     'been applied')
            expected_val = int(update_val1)

            self._chk_param_val_applied(log_msgs, expected_val)

        finally:
            self.poweron_peer_node(self.ms_node, self.mn_nodes[0])

            # Return parameter to original value
            self._update_litpd_conf(
                self.ms_node, search_val1, orig_val1, test_constants.
                LITPD_CONF_FILE)

    @attr('manual-test', 'revert', 'bug11610', 'bug11610_t03')
    def test_03_n_chk_puppet_poll_count_configurable(self):
        """
        @tms_id: litpcds_11610_tc03
        @tms_requirements_id: LITPCDS-11610
        @tms_title: Check that puppet_poll_count value is configurable
        @tms_description: Ensure that the puppet_poll_count value
            in the /etc/litpd.conf file can be updated
            Note:
            block_puppet_on.msg script is needed to simulate loss of
            communication with puppet on a specific node. Disabling puppet
            service on the node is insufficient as mco rpc commands
            still get through. Script drops all communication
            (firewall rule) with the specified node and keeps on
            reapplying the rule as puppet keeps on trying to fix it.
            Blocking starts on a specific message in /var/log/messages
            that indicates a specific phase has been reached so that
            the exact conditions needed to reproducue polling
            for poll count tests are met.

        @tms_test_steps:
         @step: Get and store current poll count parameter, update it
                and restart litp
         @result: litp starts with new puppet poll count value
         @step: Create model item that generate a puppet config task
         @result: items can be created
         @step: Create and run plan
         @result: tasks created thus plan created, can be run
         @step: Run custom script to disable
                puppet communication with node2'
         @result: script runs in background
         @step: Wait for plan to fail
         @result: Plan failed due to broken communication with node2
         @step: Check expected error messages in log
         @result: messages on failed polling posted in /var/log/messages
                  number of retries as specified via puppet_poll_count
         @step: Restore previously stored initial poll count value,
                disable puppet block
         @result: communication with node2 restored
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # Install Plugin pms required for testing
        self._install_rpms()

        local_base_path = os.path.dirname(os.path.abspath(__file__))
        story_files = "11610_files"
        block_script = "block_puppet_on_msg.sh"

        ms_tmp_dir = "/tmp/"

        self.copy_file_to(self.ms_node,
                          os.path.join(local_base_path,
                                       story_files,
                                       block_script),
                          ms_tmp_dir,
                          root_copy=True)

        # update script with actual node2 name
        sed_cmd = self.redhatutils.get_replace_str_in_file_cmd(
            'NODE=',
            'NODE={0}'.format(self.mn_nodes[1]),
            os.path.join('/tmp/',
                         block_script),
            '-i'
        )

        self.run_command(self.ms_node, sed_cmd, default_asserts=False,
                         su_root=True)

        # Manage timeout constraints in LITP
        # The puppet_poll_count parameter defines the
        # number of times that Puppet is polled.
        # The value of this parameter can be any integer
        # and is configurable
        litp_file = test_constants.LITPD_CONF_FILE

        search_val = "puppet_poll_count"
        update_val = '2'

        # 1. Execute the grep command to find current value of the
        #    parameter
        # 2. Update the current value to a new value
        # 3. Save the current timeout value

        self.log('info', '1. Get and store current '
                         'poll count parameter, update it')
        orig_val1 = self._update_litpd_conf(
            self.ms_node, search_val, update_val, litp_file)

        # messages on polling
        msg_1 = "DEBUG: puppet not applying"
        msg_2 = ("ERROR: Maximum poll count reached. Puppet not applying "
                 "configuration. Failing running tasks"
                 )

        self.log('info', '2. Create model item that generates puppet task')

        # Find paths to use in model item creation
        sitem = os.path.join(self.software_items,
                             "package" + "{0}")

        nodes_uri = self.find(
            self.ms_node, path='/deployments', resource='node')
        node2_deployment = nodes_uri[1] + "/items/" + "package" + "{0}"

        props = "name=telnet"
        self.execute_cli_create_cmd(
            self.ms_node, sitem.format("1a"), "package", props)

        self.execute_cli_inherit_cmd(
            self.ms_node, node2_deployment.format("1b"), sitem.format("1a"))

        # Find the current log position so all log messages before
        # this test can be ignored
        test_logs_len = self.get_file_len(self.ms_node,
                                          test_constants.GEN_SYSTEM_LOG_PATH)
        try:
            self.log('info', '3. Create and run plan')

            self.execute_cli_createplan_cmd(self.ms_node)

            self.execute_cli_runplan_cmd(self.ms_node)

            self.assertTrue(
                self.wait_for_task_state(
                    self.ms_node,
                    'Lock VCS on node "{0}"'.format(
                        self.mn_nodes[1]),
                    test_constants.PLAN_TASKS_SUCCESS,
                    ignore_variables=False)
            )

            self.log('info', '4. Run script to disable '
                             'puppet communication with node2')

            self.run_command(self.ms_node,
                             '/usr/bin/nohup {0} > /dev/null 2>&1 &'.format(
                                 os.path.join(ms_tmp_dir, block_script),
                             ),
                             su_root=True)

            self.log('info', '5. Wait for plan to fail')
            self.assertTrue(self.wait_for_plan_state(
                self.ms_node, test_constants.PLAN_FAILED, timeout_mins=40),
                "The state of the last run plan is not 'failed' as expected.")

            self.log("info", "6. Check expected error messages in log")
            self.log("info", "6a. count of puppet not applying messages")

            self.assertEqual(len(
                self.wait_for_log_msg(
                    self.ms_node,
                    msg_1,
                    timeout_sec=10,
                    log_len=test_logs_len,
                    return_log_msgs=True)
            ),
                int(update_val),
                "count of puppet not applying messages should match "
                "puppet_poll_count"
            )

            self.log("info", "6b. maximum poll count reached message once")

            self.assertEqual(len(
                self.wait_for_log_msg(
                    self.ms_node,
                    msg_2,
                    timeout_sec=10,
                    log_len=test_logs_len,
                    return_log_msgs=True)
            ),
                1,
                "maximum poll count reached message should be posted once"
            )

        finally:

            self.log("info", "7. Cleanup - Restore previously stored "
                             "initial poll count value,"
                             "disable puppet block")

            get_pid_cmd = "ps -ef | " \
                          "grep {0} | " \
                          "grep -v 'grep' | " \
                          "awk '{{print $2}}'" \
                .format(block_script)

            pid, _, _ = self.run_command(self.ms_node, get_pid_cmd,
                                         default_asserts=True)

            self.run_command(self.ms_node,
                             '/bin/kill {0}'.format(pid[0]),
                             su_root=True,
                             default_asserts=True
                             )

            self._update_litpd_conf(
                self.ms_node, search_val, orig_val1, litp_file)

            # make sure puppet communication with node2 restored
            self.assertTrue(
                self.wait_for_cmd(self.ms_node,
                                  '/usr/bin/mco ping',
                                  expected_stdout=self.mn_nodes[1],
                                  expected_rc=1,
                                  timeout_mins=3))
