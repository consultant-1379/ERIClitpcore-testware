"""
COPYRIGHT Ericsson 2023
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2023
@author:    Aniket Vyawahare, Joe Noonan
@summary:   TORF-646275
            puppetserver_monitor service was not enabled during initial
            install. This test is to verify that the puppetserver and
            puppetserver_monitor services are enabled and active
"""
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const


class Story646275(GenericTest):
    """
    I want to ensure puppetserver_monitor is enabled and active
    after ms reboot
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story646275, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        self.ms_ip = self.get_node_att(self.ms1, 'ipv4')
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """ Runs after every single test """
        super(Story646275, self).tearDown()

    def reboot_ms_and_assert_success(self):
        """
        Description: Reboots the MS and waits for the node to
                     come back up.
        """
        cmd = "(sleep 1; {0} -r now {1}) &".format(const.SHUTDOWN_PATH,
                                                   self.ms1)

        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.assertTrue(self.wait_for_ping(self.ms_ip, False, retry_count=4),
                        "Node '{0} has not gone down".format(self.ms1))

        self.assertTrue(self.wait_for_node_up(self.ms1,
                        wait_for_litp=True), "'{0} did not come up in "
                        "expected timeframe".format(self.ms1))

    @attr('all', 'revert', 'story646725', 'story646725_tc01')
    def test_01_verify_puppetserver_is_enabled_active(self):
        """
        @tms_id:
            torf_646275_tc_01
        @tms_requirements_id:
            TORF-646275
        @tms_title:
            Check that the puppetserver is enabled and active
        @tms_description:
            Check that the puppetserver is enabled and active
        @tms_test_steps:
        @step: Run "systemctl is-enabled puppetserver
                    systemctl is-active puppetserver"
        @result: Output shows that puppetserver is enabled and active

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        status_cmd_str = self.rhcmd.get_systemctl_isenabled_cmd(
                        "puppetserver")
        stdout, _, _ = self.run_command(self.ms1, status_cmd_str,
                            su_root=True, default_asserts=False)
        self.assertEqual(stdout[0], "enabled",
                        "FAILURE: Puppetserver is disabled")
        status_cmd_str = self.rhcmd.get_systemctl_is_active_cmd(
                        "puppetserver")
        stdout, _, _ = self.run_command(self.ms1, status_cmd_str,
                            su_root=True, default_asserts=False)
        self.assertEqual(stdout[0], "active",
                        "FAILURE: Puppetserver is inactive")

    def test_02_p_check_puppetserver_monitor_is_enabled_active(self):
        """
        @tms_id:
            torf_646275_tc_02
        @tms_requirements_id:
            TORF-646275
        @tms_title:
            Check that the puppetserver_monitor is enabled and active
        @tms_description:
            Check that the puppetserver_monitor is enabled and active
        @tms_test_steps:
        @step: Run "systemctl is-enabled puppetserver_monitor
                    systemctl is-active puppetserver_monitor"
        @result: Output shows that puppetserver_monitor is
                    enabled and active

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        status_cmd_str = self.rhcmd.get_systemctl_isenabled_cmd(
                        "puppetserver_monitor")
        stdout, _, _ = self.run_command(self.ms1, status_cmd_str,
                            su_root=True, default_asserts=False)
        self.assertEqual(stdout[0], "enabled",
                        "FAILURE: Puppetserver_monitor is disabled")
        status_cmd_str = self.rhcmd.get_systemctl_is_active_cmd(
                        "puppetserver_monitor")
        stdout, _, _ = self.run_command(self.ms1, status_cmd_str,
                            su_root=True, default_asserts=False)
        self.assertEqual(stdout[0], "active",
                        "FAILURE: Puppetserver_monitor is inactive")

    @attr('all', 'revert', 'story646725', 'story646725_tc03')
    def test_03_verify_puppetserver_and_monitor_active_after_reboot(self):
        """
        @tms_id:
            torf_646275_tc_03
        @tms_requirements_id:
            TORF-646275
        @tms_title:
            Check that the puppetserver and puppetserver_monitor services
            are active after ms reboot
        @tms_description:
            Check that the puppetserver and puppetserver_monitor services
            are active after ms reboot
        @tms_test_steps:
        @step: Reboot ms
        @result: MS rebooted
        @step: Wait for puppetserver service to start
        @result: puppetserver successfully starts
        @step: Wait for puppetserver_monitor service to start
        @result: puppetserver_monitor successfully starts

        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.reboot_ms_and_assert_success()

        status_cmd_str = self.rhcmd.get_systemctl_is_active_cmd(
                        "puppetserver")

        stdout = self.wait_for_cmd(self.ms1,
                        status_cmd_str, 0, timeout_mins=1, su_root=True)

        self.assertTrue(stdout, 'FAILURE: Puppetserver is inactive')

        status_cmd_str = self.rhcmd.get_systemctl_is_active_cmd(
                        "puppetserver_monitor")

        stdout = self.wait_for_cmd(self.ms1,
                        status_cmd_str, 0, timeout_mins=1, su_root=True)

        self.assertTrue(stdout, 'FAILURE: Puppetserver_monitor is inactive')
