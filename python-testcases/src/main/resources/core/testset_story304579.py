'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2019
@author:    Sam Luby
@summary:   TORF-304579
            Test that no failure messages occur when the correct webserver
            responses are found when restarting litpd.
            Also test that the two expected failure messages do occur when
            incorrect responses are received from the webserver.
'''
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants


class Story304579(GenericTest):
    """
    TORF-304579:
        Investigate if silently polling in litpd init script is required
        at litpd startup
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story304579, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.litpd_serivce = 'litpd'
        self.litpd_file_path = test_constants.LITPD_SERVICE_FILE
        self.log_path = test_constants.GEN_SYSTEM_LOG_PATH
        self.failure_msgs = [
            'HTTP unix socket server did not come up after 10 seconds.',
            'HTTP TCP server did not come up after 10 seconds.']
        self.litpd_restart_str = 'Warning: litpd.service changed on '\
            'disk. Run \'systemctl daemon-reload\' to reload units.'
        self.error_str = 'No Warning from systemctl to reload units in '\
            'restart output'
        self.daemon_reload = False

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story304579, self).tearDown()
        if self.daemon_reload:
            self.systemctl_daemon_reload(self.ms_node)

    def _check_logs(self, start_log_position, log_message,
                    expect_positive=True):
        """check /var/log/messages for failure messages"""
        message = self.wait_for_log_msg(self.ms_node,
                                        log_message,
                                        timeout_sec=20,
                                        log_len=start_log_position,
                                        return_log_msgs=True)
        if expect_positive:
            self.assertEqual([], message)
        else:
            self.assertTrue(self.is_text_in_list(log_message, message),
                            "Correct message in logs not found.")

    @attr('all', 'revert', 'Story304579', 'Story304579_tc01')
    def test_01_p_no_failure_messages_found(self):
        """
        @tms_id: TORF-304579_tc01
        @tms_requirements_id: TORF-299751
        @tms_title: Verify that specific failure messages don't occur
            in logs.
        @tms_description: Verify that specific failure messages don't
            occur in logs when restarting the litpd service.
        @tms_test_steps:
            @step: Determine log point before restarting service
            @result: Log point taken
            @step:  Restart litpd service.
            @result:  litpd starts with no warning issued.
            @step: Check /var/log/messages for the failure messages
            @result: No failure messages should be written to logs
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self.log('info', '1. Get log position when litpd restarts')
        log_position = self.get_file_len(self.ms_node, self.log_path)

        self.log('info', '2. Restart litpd service')
        stdout, stderr, rc = self.restart_service(self.ms_node,
                                                  self.litpd_serivce,
                                                  assert_success=True,
                                                  su_root=True,
                                                  su_timeout_secs=60)

        self.assertEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(rc, 0)

        self.log('info', '3. Looking for the two failure messages in logs')
        for msg in self.failure_msgs:
            self._check_logs(log_position, msg)

    @attr('all', 'revert', 'Story304579', 'Story304579_tc02')
    def test_02_n_failure_messages_found(self):
        """
        @tms_id: TORF-304579_tc02
        @tms_requirements_id: TORF-299751
        @tms_title: Verify that failure messages occur when searching for an
            incorrect string in the responses from the servers.
        @tms_description: Verify that failure messages occur in logs when
            restarting the litpd server, due to finding unexpected responses
            from a curl and a GET request from the HTTP TCP and HTTP unix
            socket server respectively.
        @tms_test_steps:
            @step:  Backup the litpd bash file located in /etc/init.d/ and
                store in a temporary location.
            @result:  Copying file is successful.
            @step:  Use the sed command to edit the strings that are being
                searched for using grep.
            @result:  sed command is successful and the string to search has
                been changed.
            @step: Determine log position before restart of litpd service
            @result: Log point taken
            @step:  Restart litpd service.
            @result:  litpd comes online successfully with warning in stdout.
            @step:  Set the daemon-reload boolean to allow the warning to
                    be cleared during tearDown.
            @result: daemon-reload boolean set
            @step:  Examine the output of /var/log/messages. Look for the
                two expected failure messages.
            @result:  Two messages are present.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """

        self.log('info', '1. Backup litpd file')
        self.assertTrue(self.backup_file(self.ms_node, self.litpd_file_path,
                                         restore_after_plan=True))

        old_str = 'Powered by a webserver'
        new_str = 'replaced string here'

        self.log('info', '2. Get sed command to replace strings in file')
        cmd = self.rhcmd.get_replace_str_in_file_cmd(old_str, new_str,
                                                     self.litpd_file_path,
                                                     sed_args='-i')

        self.log('info', '3. Replace strings in file using sed command')
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        self.log('info', '4. Get log position when litpd restarts')
        log_position = self.get_file_len(self.ms_node, self.log_path)

        self.log('info', '5. Restart litpd service')
        stdout, _, _ = self.restart_service(self.ms_node, self.litpd_serivce,
                                            assert_success=False, su_root=True,
                                            su_timeout_secs=120)

        self.assertTrue(self.is_text_in_list(self.litpd_restart_str,
                                             stdout), self.error_str)

        self.log('info', '6. Reload litpd unit file in cleanup')
        self.daemon_reload = True

        self.log('info', '7. Check /var/log/messages for error messages')

        for msg in self.failure_msgs:
            self._check_logs(log_position, msg, expect_positive=False)
