"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2022
@author:    Laurence Canny
@summary:   TORF-568650
            I want to ensure litpd service starts after postgres
            service without errors and verify services have
            restarted after ms reboot
"""
from litp_generic_test import GenericTest, attr
import test_constants as const


class Bug568650(GenericTest):
    """
    I want to ensure litpd service starts after postgres
    service without errors and verify services have
    restarted after ms reboot
    """

    def setUp(self):
        """ Runs before every test """
        super(Bug568650, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip = self.get_node_att(self.ms_node, 'ipv4')

    def tearDown(self):
        """ Runs after every single test """
        super(Bug568650, self).tearDown()

    def check_for_service_up(self, service, check_phrase):
        """
        Description: Checking status of a service and grepping for
                     matching string in output.
        Args:
            service (str): the service queried for status
            check_phrase (str): status output to match
        """
        status_cmd_str = ('{0} status {1} |'
                          '{2} {3}').format(const.SYSTEMCTL_PATH, service,
                                            const.GREP_PATH, check_phrase)

        self.run_command(self.ms_node, status_cmd_str, su_root=True,
                         default_asserts=True)

    def wait_for_service_up(self, service, check_phrase):
        """
        Description: Wait for service to come up.
                     Check status of a service, then assert
                     against a return code of 0 if status output is
                     matched within time limit.
        Args:
            service (str): the service queried for status
            check_phrase (str): status output to match
        """
        status_cmd_str = ('{0} status {1} |'
                          '{2} {3}').format(const.SYSTEMCTL_PATH, service,
                                            const.GREP_PATH, check_phrase)

        self.assertTrue(self.wait_for_cmd(self.ms_node, status_cmd_str, 0,
                                          timeout_mins=1, su_root=True))

    def reboot_ms_and_assert_success(self):
        """
        Description: Reboots the MS and waits for the node to
                     come back up.
        """
        cmd = "(sleep 1; {0} -r now {1}) &".format(const.SHUTDOWN_PATH,
                                                   self.ms_node)

        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        self.assertTrue(self.wait_for_ping(self.ms_ip, False, retry_count=4),
                        "Node '{0} has not gone down".format(self.ms_node))

        self.assertTrue(self.wait_for_node_up(self.ms_node,
                        wait_for_litp=True), "'{0} did not come up in "
                        "expected timeframe".format(self.ms_node))

    def get_service_uptime(self, service):
        """
        Description: Get service uptime
        Args:
            service (str): service queried for uptime
        """
        cmd = "{0} status {1} | {2} since | {3} '{{print $9}}'" \
              .format(const.SYSTEMCTL_PATH, service, const.GREP_PATH,
                      const.AWK_PATH)
        stdout, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                        default_asserts=True)

        timeformat = ''.join(stdout)
        service_uptime = ''.join(i for i in timeformat if i.isdigit())
        uptime = int(service_uptime)

        return uptime

    @attr('all', 'revert', 'bug568650', 'bug568650_tc01')
    def test_01_verify_services_startup_after_ms_reboot(self):
        """
        @tms_id: TORF_568650_tc01
        @tms_requirements_id: TORF-568650
        @tms_title:
        @tms_description:
        @tms_test_steps:
            @step: Add sleep to postgres config file and reload
                   config file
            @result: 60 second sleep added to postgres config
            @step: Reboot ms
            @result: MS rebooted
            @step: Wait for postgresql service to start
            @result: postgresql successfully starts
            @step: Verify litpd is running
            @result: litpd service successfully starts
            @step: Get litpd service uptime
            @result: service uptime returned
            @step: Get postgresql service uptime
            @result: service uptime returned
            @step: Verify litpd service started after postgresql service
            @result: Service start order verified
            @step: Verify various services are running
            @result: Checked services are running
            @step: Remove sleep from postgresql config and reload config
            @result: postgresql configuration file reset
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        add_str = "ExecStartPre=/usr/bin/sleep 60"
        find_str = "postgresql-check-db-dir %N"
        postgres_file_path = "/usr/lib/systemd/system/" \
                             "rh-postgresql96-postgresql.service"

        self.log("info", "1. Add sleep to postgres config file")

        cmd = "{0} -i '/{1}/a {2}' {3}".format(const.SED_PATH, find_str,
                                               add_str, postgres_file_path)
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        self.log("info", "2. Call systemctl daemon-reload for change to "
                 " take effect")
        self.run_command(self.ms_node, "systemctl daemon-reload", su_root=True,
                         default_asserts=True)

        self.log("info", "3. Reboot the MS")

        self.reboot_ms_and_assert_success()

        self.log("info", "4. Wait for postgresql service to start")
        self.wait_for_service_up("postgresql", "running")

        self.log("info", "5. Verify litpd is running")
        self.check_for_service_up("litpd", "running")

        self.log("info", "6. Get litpd service uptime")
        litpd_uptime = self.get_service_uptime("litpd")

        self.log("info", "7. Get postgresql service uptime")
        postgresql_uptime = self.get_service_uptime("postgresql")

        self.log("info", "8. Verify litpd started after postgresql service")
        self.assertTrue(litpd_uptime < postgresql_uptime)

        self.log("info", "9. Verify services are running")
        for process in ["puppet", "puppetdb_monitor", "puppetserver",
                        "mcollective.service", "rabbitmq-server",
                        "celery"]:
            self.check_for_service_up(process, "running")

        self.log("info", "10. Remove sleep from postgres config file")
        cmd = "{0} -i '\\|{1}|d' {2}".format(const.SED_PATH, add_str,
                                             postgres_file_path)
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

        self.run_command(self.ms_node, "systemctl daemon-reload", su_root=True,
                         default_asserts=True)
