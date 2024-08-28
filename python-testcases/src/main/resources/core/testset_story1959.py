'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    Padraic
@summary:   Integration test for Passenger validation
            These tests will verify that passenger is working and that it is
            enforced by puppet.
            Agile: STORY-1959
'''
import time
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants


class Story1959(GenericTest):
    """
    As in Installer I want to install and configure puppet using Passenger on
    Apache so that it is more scalable than the default WEBrick mechanism.
    """
    def setUp(self):
        """Setup variables for every test"""
        # 1. Call super class setup
        super(Story1959, self).setUp()
        # 2. Set up variables used in the test
        self.ms_nodes = self.get_management_node_filenames()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.assertNotEqual([], self.mn_nodes)
        self.mn_node = self.mn_nodes[0]

        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """Runs for every test"""
        super(Story1959, self).tearDown()

    def __check_apache_server(self, node):
        """
        Check that the apache web server is OK by:
            1. Verifying that it is running.
            2. Verifying that it is accepting connections on the expected port.
        """
        # 1. Check that the apache web server is running.
        cmd = self.rhcmd.get_service_running_cmd("httpd")
        out, err, ret_code = self.run_command(node, cmd, su_root=True)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list('running', out),
                        "Unexpected service status response")
        self.assertEqual(0, ret_code)

        # Check that the web server port is accepting connections.
        server_port = test_constants.PASSENGER_SERVER_PORT
        ms_ip = self.get_node_att(node, 'ipv4')
        self.assertNotEqual('', ms_ip)

        cmd = "/usr/bin/nc -z {0} {1}".format(ms_ip, server_port)
        out, err, ret_code = self.run_command(node, cmd, su_root=True)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list('succeeded', out),
                        "Unexpected netcat response")
        self.assertEqual(0, ret_code)

        return True

    def __replace_file_string(self, node, filename, old_str, new_str):
        """ Modify a line from a file.
            Replace old_str with new_str
        """
        cmd = "/bin/sed -i 's/{0}/{1}/g' {2}".format(old_str, new_str,
                                                     filename)
        out, err, ret_code = self.run_command(node, cmd, su_root=True)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertEqual([], out)

    #attr('all', 'revert', 'story1959', 'story1959_tc01')
    def obsolete_01_n_passenger_apache_config_enforced(self):
        """
        #tms_id:
            litpcds_1959_tc01

        #tms_requirements_id: LITPCDS-1959

        #tms_title:
            test passenger service when apache config is missing
        #tms_description:
            This test will verify that the passenger(puppetmaster) apache
            config file is enforced by puppet.
        #tms_test_steps:
         #step:
            Remove the apache configuration file.
         #result:
            Puppet is successfully started without configuration file
         #step:
            Verify that puppet recreates the file.
         #result:
            The passenger apache config is enforced by puppet.
        #tms_test_precondition:
            NA
        #tms_execution_type: Automated
        """
        pass

    #attr('all', 'revert', 'story1959', 'story1959_tc02')
    def obsolete_02_n_passenger_config_dir_enforced(self):
        """
        #tms_id:
            litpcds_1959_tc02

        #tms_requirements_id: LITPCDS-1959

        #tms_title:
            test passenger service when passenger config dir is missing
        #tms_description:
            This test will verify that the passenger(puppetmaster)
            config directory is enforced by puppet.
        #tms_test_steps:
         #step:
            Remove the passenger configuration directory.
         #result:
            Puppet is successfully started without passenger config dir
         #step:
            Verify that puppet recreates the directory.
         #result:
            The passenger config directory is enforced by puppet.
        #tms_test_precondition:
            NA
        #tms_execution_type: Automated
        """
        pass

    #attr('all', 'revert', 'story1959', 'story1959_tc03')
    def obsolete_03_p_passenger_running(self):
        """
        #tms_id:
            litpcds_1959_tc03

        #tms_requirements_id: LITPCDS-1959

        #tms_title:
            test passenger service is running with correct version
        #tms_description:
            This test verifies that passenger is running.
        #tms_test_steps:
         #step:
            Request and verify a status report from Passenger.
         #result:
            Passenger is running with correct version.
        #tms_test_precondition:
            NA
        #tms_execution_type: Automated
        """
        pass

    @attr('all', 'revert', 'story1959', 'story1959_tc04')
    def test_04_n_puppetmaster_not_running(self):
        """
        @tms_id:
            litpcds_1959_tc04

        @tms_requirements_id: LITPCDS-1959

        @tms_title:
            test puppet master service is not used anymore
        @tms_description:
            This test verifies that the deprecated puppet master service is
            not running. It has been replaced by a puppet master function
            implemented with mod_passenger in an Apache HTTP server.
        @tms_test_steps:
         @step:
            Search and check for the puppet master process.
         @result:
            Puppet master is not running.
        @tms_test_precondition:
            NA
        @tms_execution_type: Automated
        """
        # 1. Search for the puppet master process on the MS
        cmd = '/bin/ps -elf | grep "puppet server" | grep -v grep'
        out, err, ret_code = self.run_command(self.ms_node, cmd)

        # 2. Verify that the process is not running.
        self.assertEqual(1, ret_code)
        self.assertEqual([], err)
        self.assertFalse(self.is_text_in_list('puppet server', out))

    @attr('all', 'revert', 'story1959', 'story1959_tc05')
    def test_05_p_passenger_concurrency(self):
        """
        @tms_id:
            litpcds_1959_tc05

        @tms_requirements_id: LITPCDS-1959

        @tms_title:
            test puppet agents are not generating Error 400
        @tms_description:
            This test verifies that the deprecated puppet master service is
            not running. It has been replaced by a puppet master function
            implemented with mod_passenger in an Apache HTTP server.
        @tms_test_steps:
         @step:
            Kick off puppet catalog runs on all node and check syslog
            for Error 400.
         @result:
            The agents don't generate '400 error's to the system log
            Puppet using the passenger web server handles puppet catalog runs
            that are initiated at almost the same time.
        @tms_test_precondition:
            NA
        @tms_execution_type: Automated
        """
        all_nodes = self.ms_nodes + self.mn_nodes
        log_path = test_constants.GEN_SYSTEM_LOG_PATH
        log_msg = "Error 400"
        log_lens = {}

        # Store the current log lengths.
        for node in all_nodes:
            log_lens[node] = self.get_file_len(node, log_path)

        # 1. Kick off puppet catalog runs on all node.
        cmd = "/usr/bin/killall puppet -10 -u root"
        results = self.run_commands(all_nodes, [cmd], su_root=True)
        errors = self.get_stderr(results)
        self.assertEqual([], errors)
        # Check that stdout is empty
        self.assertTrue(self.is_std_out_empty(results), "Std_out is not empty")

        # 2. Verify that agents don't generate '400 error's to the system log
        for node in all_nodes:
            # Run grep on the server logs related to this test
            self.assertFalse(self.wait_for_log_msg(node, log_msg, log_path,
                                                   timeout_sec=10,
                                                   log_len=log_lens[node]),
                             'Error 400 is found in syslog')

    @attr('all', 'revert', 'story1959', 'story1959_tc06')
    def test_06_n_puppet_enforces_hosts(self):
        """
        @tms_id:
            litpcds_1959_tc06

        @tms_requirements_id: LITPCDS-1959

        @tms_title:
            test puppet is still working when hosts file is
            missing (only on nodes).
        @tms_description:
            This test checks that after the introduction of Passenger, puppet
            is still working on all hosts.
        @tms_test_steps:
         @step:
            Modify /etc/hosts file and kick puppet.
         @result:
            Puppet is still working on all hosts and puppet restores
            the original file contents
        @tms_test_precondition:
            NA
        @tms_execution_type: Automated
        """
        try:
            hosts_file_reset = False
            all_nodes = self.ms_nodes + self.mn_nodes
            hosts_file = "/etc/hosts"
            # Copy /etc/hosts to a safe place
            # Copy with '-p' option to retain file properties in new file
            cmd = "/bin/cp -p {0} {0}_1959".format(hosts_file)
            for node in all_nodes:
                out, err, ret_code = self.run_command(node, cmd, su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertEqual([], out)

            # 1. Modify /etc/hosts file on MNs.
            # for node in self.mn_nodes:
            # Only executing test on one node
            node = self.mn_nodes[0]
            old_hst_str = self.get_node_att(node, "hostname")

            new_hst_str = "1959_BlahDeeBlah"
            self.__replace_file_string(node, hosts_file,
                                       old_hst_str, new_hst_str)
            # /etc/hosts on MS is not tested because if all entries are changed
            # on MS, puppet will break, we should not change the entries that
            # contain the "localhost" string. left for future development

            # 2. Kick puppet
            self.start_new_puppet_run(self.ms_node)

            # 3. Verify that puppet restores the original file contents.
            hosts_fixed = {}
            start_time = time.time()
            elapsed = 0
            pp_interval = self.get_puppet_interval(self.ms_node)
            while elapsed < (pp_interval * 2):
                # for node in all_nodes:
                # Store in dict if the hostname is restored to /etc/hosts
                hst_str = self.get_node_att(node, "hostname")
                cmd = self.rhcmd.get_grep_file_cmd(hosts_file, hst_str)
                out, err, ret_code = self.run_command(node, cmd)
                self.assertTrue((ret_code < 2), "Command failed")
                self.assertEqual([], err)
                hosts_fixed[node] = self.is_text_in_list(hst_str, out)

                self.log("info", "hosts_fixed: {0}".format(str(hosts_fixed)))
                if all(val is True for val in hosts_fixed.values()):
                    self.log("info", "All True, All hosts restored")
                    hosts_file_reset = True
                    break
                time.sleep(10)
                curr_time = time.time()
                elapsed = curr_time - start_time
                print "Now taken {0} seconds ".format(str(int(elapsed)))
            self.assertTrue(hosts_file_reset, ("Config file hasen't been " +
                            "enforced in {0} seconds".format(pp_interval * 2)))

        finally:
            # 4. Restore the file
            for node in all_nodes:
                cmd = "/bin/mv -f {0}_1959 {0}".format(hosts_file)
                out, err, ret_code = self.run_command(node, cmd, su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertEqual([], out)
