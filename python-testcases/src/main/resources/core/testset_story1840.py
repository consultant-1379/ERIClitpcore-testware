"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2014
@author:    Padraic
@summary:   Integration test for mCollective validation
            These tests will verify that mcollective is working and that it is
            enforced by puppet.
            Agile: STORY-1840
"""
import time
import re
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants


class Story1840(GenericTest):
    """
    As a system architect I want to include Mcollective in LITP so that I
    can replace the deprecated puppet-kick.
    """
    def setUp(self):
        """Setup variables for every test"""
        # 1. Call super class setup
        super(Story1840, self).setUp()
        # 2. Set up variables used in the test
        self.ms_nodes = self.get_management_node_filenames()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.mn_node = self.mn_nodes[0]
        self.mn_hname = self.get_node_att(self.mn_node, "hostname")

        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """Runs for every test"""
        super(Story1840, self).tearDown()

    def __get_puppet_interval(self, node):
        '''
        Returns the interval between puppet runs (runinterval). This is
        configured in the file referenced by the PUPPET_CONFIG_FILE constant.
        '''
        pp_cfg_file = test_constants.PUPPET_CONFIG_FILE
        pp_cfg_var = "runinterval"
        self.log("info", "Puppet cfg file is {0}".format(pp_cfg_file))
        cmd = self.rhcmd.get_grep_file_cmd(pp_cfg_file, pp_cfg_var)
        out, err, ret_code = self.run_command(node, cmd, su_root=True)

        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list(pp_cfg_var, out),
                        "{0} not in file".format(pp_cfg_var))
        sreg = r'{0}\s+=\s+(\d+)'.format(pp_cfg_var)
        reg_exp = re.compile(sreg, re.DOTALL)
        reg_match = reg_exp.search(str(out))
        if reg_match:
            str_val = reg_match.group(1)
            self.log('info', "Puppet runinterval is [{0}]".format(str_val))
            ret_val = int(str_val)
        else:
            self.log('error', "Couldn't find {0} in file {1}".format(
                pp_cfg_var, pp_cfg_file))
            ret_val = False
        return ret_val

    def obsolete_01_p_verify_mcollective_services(self):
        """
        NOTE: This test is a duplicate of test_01_p_mcollective_running
        in testset_story2490.py so making obsolete
        Description:
           This test checks that the mcollective service is running on MS and
           all managed nodes.
        Actions:
            1. Verify that the mcollective service is running on MS
            2. Verify that the mcollective service is running on MNs
       Results:
           Mcollective is running on MS and all managed nodes.
        """

        # 1. Verify that the mcollective service is running on MS
        cmd = self.rhcmd.get_service_running_cmd("mcollective")
        out, err, ret_code = self.run_command(self.ms_node, cmd, su_root=True)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list('running', out),
                        "mcollective is not running")

        # 2. Verify that the mcollective service is running on MNs
        for node in self.mn_nodes:
            out, err, ret_code = self.run_command(node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list('running', out),
                            "mcollective is not running")

    def obsolete_02_p_verify_mcollective_cmd_single_mn(self):
        """
        Obsolete:test_02, test_03 and test_04 are now covered by added test
        test_09_p_verify_mcollective
        Description:
            This test checks that mcollective has been installed correctly by
            verifying that an mcollective command can be issued from the MS to
            a single MN.
        Actions:
            1. Issue an mco command to show the status of puppet on a MN.
            2. Verify that the MN replies with the correct return code.
            3. Verify that the MN replies with the correct response.
            4. Stop the puppet service on the MN using mco.
            5. Verify that the puppet service is stopped on the MN.
            6. Verify that puppet is not stopped on all other nodes.
            7. Restart the puppet service on the MN.
        Result:
            It is possible to issue mcollective commands from the MS to a
            single MN.
        """
        try:
            # 1. Issue an mco command to show the status of puppet on a MN.
            mco_cmd = self.cli.get_mco_cmd(
                "service puppet status -I {0}".format(self.mn_hname))
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

            # 2. Verify that the MN replies with the correct return code.
            self.assertTrue(ret_code == 0, "Non zero return code")

            # 3. Verify that the MN replies with the correct response.
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("running", out),
                            "Unexpected mco response")

            # 4. Stop the puppet service on the MN using mco
            mco_cmd = self.cli.get_mco_cmd(
                "service puppet stop -I {0}".format(self.mn_hname))
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 5. Verify that the puppet service is stopped on the MN
            cmd = "/sbin/service puppet status"
            out, err, ret_code = self.run_command(self.mn_node, cmd)
            self.assertTrue(ret_code < 4, "service cmd failed")
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("stopped", out),
                            "Unexpected service status response")

            # 6. Verify that puppet is not stopped on all other nodes.
            other_nodes = self.mn_nodes[1:]
            other_nodes.append(self.ms_node)
            for node in other_nodes:
                out, err, ret_code = self.run_command(node, cmd)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertTrue(self.is_text_in_list("running", out),
                                "Unexpected service status response")

        finally:
            # 7. Restart the puppet service on the MN
            cmd = "/sbin/service puppet start"
            out, err, ret_code = self.run_command(self.mn_node, cmd,
                                                  su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("OK", out),
                            "Unexpected service start response")

    def obsolete_03_p_verify_mcollective_cmd_all_nodes(self):
        """
        Obsolete:test_02, test_03 and test_04 are now covered by added test
        test_09_p_verify_mcollective
        Description:
            This test checks that mcollective has been installed correctly by
            verifying that an mcollective command can be issued from the MS to
            all nodes.
        Actions:
            1. Issue an mco command to show the status of puppet on all nodes.
            2. Stop the puppet service on all nodes.
            3. Verify that the puppet service is stopped on all nodes.
            4. Restart the puppet service.
            5. Verify that the puppet service is started on all nodes.
        Result:
            It is possible to issue mcollective commands from the MS to a
            single MN.
        """
        try:
            # 1. Issue an mco command to show the status of puppet on all nodes
            mco_cmd = self.cli.get_mco_cmd("service puppet status")
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

            # 2. Stop the puppet service on all nodes
            mco_cmd = self.cli.get_mco_cmd("service puppet stop -y")
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 3. Verify that the puppet service is stopped on all nodes
            all_nodes = []
            all_nodes.extend(self.ms_nodes)
            all_nodes.extend(self.mn_nodes)
            for node in all_nodes:
                cmd = "/sbin/service puppet status"
                out, err, ret_code = self.run_command(node, cmd)
                self.assertTrue(ret_code < 4, "service cmd failed")
                self.assertEqual([], err)
                self.assertTrue(self.is_text_in_list("stopped", out),
                                "Unexpected service status response")
        finally:
            # 4. Restart the puppet service
            mco_cmd = self.cli.get_mco_cmd("service puppet start -y")
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 5. Verify that the puppet service is started on all nodes
            for node in all_nodes:
                cmd = "/sbin/service puppet status"
                out, err, ret_code = self.run_command(node, cmd)
                self.assertTrue(ret_code < 4, "service cmd failed")
                self.assertEqual([], err)
                self.assertTrue(self.is_text_in_list("running", out),
                                "Unexpected service status response")

    def obsolete_04_n_verify_no_mco_cli_mns(self):
        """
        Obsolete:test_02, test_03 and test_04 are now covered by added test
        test_09_p_verify_mcollective
        Description:
             This test verifies that no mcollective CLI is available on the MNs
        Actions:
            1. Issue an mcollective command to show the status of puppet on
               an MN.
            2. Verify that the MN replies with a non zero return value.
            3. Verify that the MN replies with an error response.
        Result:
            It is not possible to issue mcollective commands from the MN.
        """

        # 1. Attempt an mco command to show the status of puppet on all MN.
        cmd = "mco service puppet status"
        out, err, ret_code = self.run_command(self.mn_node, cmd)

        # 2. Verify that the MN replies with a non zero return value.
        self.log("info", "Return code is [{0}]".format(ret_code))
        self.assertNotEqual(0, ret_code)

        # 3. Verify that the MN replies with the correct response.
        self.assertEqual([], out)
        self.assertNotEqual([], err)
        self.assertTrue(self.is_text_in_list("command not found", err),
                        "Unexpected response")

    def obsolete_05_p_verify_mcollective_puppet_controlled(self):
        """
        Obsolete: test_10_p_verify_mcollective_puppet_controlled
        will cover test_05, test_06 and test_07
        Description:
            This test will verify that mcollective configuration is under
            puppet control:
        Actions:
            1. Remove the mcollective configuration file.
            2. Verify that puppet recreates the file.
        Result:
            mcollective configuration is under puppet control
        """
        try:
            cfg_file_reset = False

            # 1. Remove the mcollective configuration file
            mco_cfg_file = test_constants.MCOLLECTIVE_CONFIG_FILE
            cmd = self.rhcmd.get_move_cmd(mco_cfg_file, mco_cfg_file + "_old")
            out, err, ret_code = self.run_command(self.ms_node, cmd,
                                                  su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.assertEqual([], out)

            # 2. Verify that puppet recreates the file.
            pp_interval = self.__get_puppet_interval(self.ms_node)
            self.assertTrue(isinstance(pp_interval, int))
            poll_count = ((pp_interval * 2) / 10)
            for _ in range(poll_count):
                if self.remote_path_exists(self.ms_node, mco_cfg_file):
                    cfg_file_reset = True
                    break
                time.sleep(10)
            self.assertTrue(cfg_file_reset, ("Config file hasen't been " +
                            "enforced in {0} seconds".format(pp_interval * 2)))
        finally:
            # 3. Restore config file if puppet doesn't.
            if not cfg_file_reset:
                cmd = self.rhcmd.get_move_cmd(mco_cfg_file + "_old",
                                              mco_cfg_file)
                out, err, ret_code = self.run_command(self.ms_node, cmd,
                                                      su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertEqual([], out)

    def obsolete_06_p_verify_puppet_kick_deprecated(self):
        """
        Obsolete: test_10_p_verify_mcollective_puppet_controlled
        will cover test_05, test_06 and test_07
        Description:
            This test will verify that there is no puppet kick warning in
            the system log /var/log/messages.
        Actions:
            1. Check that there are no logs from puppet kick in the syslog.
        Result:
            mcollective configuration is under puppet control
        """
        log_message = "kick is deprecated"
        cmd = self.rhcmd.get_grep_file_cmd("/var/log/messages", log_message)
        out, err, ret_code = self.run_command(self.ms_node, cmd,
                                              su_root=True)
        # Assert ret_code < 2. ret_code 1 is valid: no lines found.
        self.assertTrue((ret_code < 2), "Command failed")
        self.assertEqual([], err)
        self.assertFalse(
            self.is_text_in_list('kick is deprecated', out)
        )

    def obsolete_07_p_verify_mcollective_enforced_by_puppet_stop(self):
        """
        Obsolete: test_10_p_verify_mcollective_puppet_controlled
        will cover test_05, test_06 and test_07
        Description:
            This test will verify that the mcollective service is enforced by
            puppet. Note the valid 'service status' return codes.
            0     program is running or service is OK
            1     program is dead and /var/run pid file exists
            2     program is dead and var/lock lock file exists
            3     program is not running
        Actions:
            1. Stop mcollective service on MS
            2. Stop mcollective service on a managed node.
            3. Verify that the service is started again by puppet on MS.
            4. Verify that the service is started again by puppet on MN.
            5. Verify that the restarted mcollective still works.
        Result:
            mcollective service is under puppet control
        """
        try:
            mn_mco_restarted = False
            ms_mco_restarted = False

            # 1. Stop mcollective service on MS
            stop_cmd = self.rhcmd.get_service_stop_cmd("mcollective")
            out, err, ret_code = self.run_command(self.ms_node, stop_cmd,
                                                  su_root=True,
                                                  execute_timeout=0.75)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.log("info", "Stop MS mco stdout is '{0}'".format(str(out)))

            # 2. Stop mcollective service on a managed node.
            out, err, ret_code = self.run_command(self.mn_node, stop_cmd,
                                                  su_root=True,
                                                  execute_timeout=0.75)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.log("info", "Stop MN mco stdout is '{0}'".format(str(out)))

            # Kick puppet on MS
            cmd = "killall puppet -10 -u root"
            out, err, ret_code = self.run_command(self.ms_node, cmd,
                                                  su_root=True,
                                                  execute_timeout=0.75)
            self.assertTrue((ret_code == 0), "Command failed")
            self.assertEqual([], err)
            self.assertEqual([], err)

            # Kick puppet on MN
            cmd = "killall puppet -10 -u root"
            out, err, ret_code = self.run_command(self.mn_node, cmd,
                                                  su_root=True,
                                                  execute_timeout=0.75)
            self.assertTrue((ret_code == 0), "Command failed")
            self.assertEqual([], err)
            self.assertEqual([], err)

            # 3. Verify that the service is started again by puppet on MS.
            status_cmd = self.rhcmd.get_service_running_cmd("mcollective")
            pp_interval = self.__get_puppet_interval(self.ms_node)
            self.assertTrue(isinstance(pp_interval, int))
            poll_loops = int(((pp_interval * 2) / 10))
            for _ in range(poll_loops):
                out, err, ret_code = self.run_command(
                    self.ms_node, status_cmd, execute_timeout=0.75)
                self.assertTrue(ret_code < 4, "service cmd failed")
                self.assertEqual([], err)
                if self.is_text_in_list("running", out):
                    ms_mco_restarted = True
                    break
                time.sleep(10)
            self.assertTrue(ms_mco_restarted, ("Mcollective hasn't been " +
                            "enforced in {0} seconds".format(pp_interval * 2)))

            # 4. Verify that the service is started again by puppet on MN.
            pp_interval = self.__get_puppet_interval(self.mn_node)
            self.assertTrue(isinstance(pp_interval, int))
            poll_loops = int(((pp_interval * 2) / 10))
            for _ in range(poll_loops):
                out, err, ret_code = self.run_command(self.mn_node, status_cmd)
                self.assertTrue(ret_code < 4, "service cmd failed")
                self.assertEqual([], err)
                if self.is_text_in_list("running", out):
                    mn_mco_restarted = True
                    break
                time.sleep(10)
            self.assertTrue(mn_mco_restarted, ("Mcollective hasn't been " +
                            "enforced in {0} seconds".format(pp_interval * 2)))

            # 5. Verify that the restarted mcollective still works.
            mco_cmd = self.cli.get_mco_cmd(
                "service puppet status -I {0}".format(self.mn_hname))
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("running", out),
                            "Unexpected mco response")
        finally:
            # 6. Restart mcollective if not done by puppet.
            start_cmd = self.rhcmd.get_service_start_cmd("mcollective")

            if not ms_mco_restarted:
                out, err, ret_code = self.run_command(self.ms_node, start_cmd,
                                                      su_root=True,
                                                      execute_timeout=0.75)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)

            if not mn_mco_restarted:
                out, err, ret_code = self.run_command(self.mn_node, start_cmd,
                                                      su_root=True,
                                                      execute_timeout=0.75)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)

    @attr('all', 'revert', 'story1840', 'story1840_tc08')
    def test_08_p_verify_mcollective_enforced_by_puppet_kill(self):
        """
        @tms_id: litpcds_1840_tc08
        @tms_requirements_id: LITPCDS-1840
        @tms_title: mcollective process is under puppet control
        @tms_description: This test will verify that the mcollective service
            is enforced by puppet if the process is killed.
        @tms_test_steps:
            @step: Kill mcollective process on MS.
            @result: mcollective is not running on MS
            @step: Kill mcollective process on a managed node.
            @result: mcollective is not running on managed node.
            @step: Kill puppet process on MS.
            @result: puppet is not running on MS
            @step: Kill puppet process on a managed node.
            @result: puppet is not running on managed node.
            @step: Verify that mcollective is started again by puppet on MS
            @result: mcollective is running on MS
            @step: Verify that mcollective is started again by puppet
                on managed node.
            @result: mcollective is running on managed node.
            @step: Verify that the restarted mcollective still works.
            @result: mcollective service is running.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        mn_mco_restarted = False
        ms_mco_restarted = False

        self.log('info', 'Kill mcollective process on MS.')
        kill_cmd = "killall mcollectived"
        stdout, _, _ = self.run_command(self.ms_node, kill_cmd,
                                        default_asserts=True,
                                        su_root=True)
        self.assertEqual([], stdout)

        self.log('info', 'Kill mcollective process on a managed node.')
        stdout, _, _ = self.run_command(self.mn_node, kill_cmd,
                                        default_asserts=True,
                                        su_root=True)
        self.assertEqual([], stdout)

        self.log('info', 'Kill puppet process on MS.')
        cmd = "killall puppet -10 -u root"
        stdout, _, _ = self.run_command(self.ms_node, cmd,
                                        default_asserts=True,
                                        su_root=True)
        self.assertEqual([], stdout)

        self.log('info', 'Kill puppet process on a managed node.')
        cmd = "killall puppet -10 -u root"
        stdout, _, _ = self.run_command(self.mn_node, cmd,
                                        default_asserts=True,
                                        su_root=True)
        self.assertEqual([], stdout)

        self.log('info', 'Verify that mcollective is started again'
                 ' by puppet on MS.')
        status_cmd = self.rhcmd.get_systemctl_status_cmd("mcollective")
        pp_interval = self.__get_puppet_interval(self.ms_node)
        self.assertTrue(isinstance(pp_interval, int))
        poll_loops = int(((pp_interval * 2) / 10))
        for _ in range(poll_loops):
            out, err, ret_code = self.run_command(self.ms_node, status_cmd)
            self.assertTrue(ret_code < 4, "service cmd failed")
            self.assertEqual([], err)
            if self.is_text_in_list("running", out):
                ms_mco_restarted = True
                break
            time.sleep(10)
        self.assertTrue(ms_mco_restarted, ("Mcollective hasn't been " +
                        "enforced in {0} seconds".format(pp_interval * 2)))

        self.log('info', 'Verify that mcollective is started again by puppet '
                 'on managed node.')
        pp_interval = self.__get_puppet_interval(self.mn_node)
        self.assertTrue(isinstance(pp_interval, int))
        poll_loops = int(((pp_interval * 2) / 10))
        for _ in range(poll_loops):
            out, err, ret_code = self.run_command(self.mn_node, status_cmd)
            self.assertTrue(ret_code < 4, "service cmd failed")
            self.assertEqual([], err)
            if self.is_text_in_list("running", out):
                mn_mco_restarted = True
                break
            time.sleep(10)
        self.assertTrue(mn_mco_restarted, ("Mcollective hasn't been " +
                        "enforced in {0} seconds".format(pp_interval * 2)))

        self.log('info', 'Kill puppet process on a managed node.')
        mco_cmd = self.cli.get_mco_cmd("service puppet status -I {0}"
                                       .format(self.mn_hname))
        stdout, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list("running", out),
                        "Unexpected mco response")

    @attr('all', 'revert', 'story1840', 'story1840_tc09')
    def test_09_p_verify_mcollective(self):
        """
        @tms_id: litpcds_1840_tc09
        @tms_requirements_id: LITPCDS-1840
        @tms_title: Check mcollective installation
        @tms_description: This test merges test_02, test_03 and test_04
            This test checks that mcollective has been installed correctly by
            verifying that an mcollective command can be issued from the MS to
            a single MN and all MNs
        @tms_test_steps:
            @step: Issue an mco command to show the status of puppet on a MN.
            @result: The status is correct
            @step: Issue an mco command to show the status of puppet on all MNs
            @result: The status is correct
            @step: Attempt to run an mco cli command to show the status
               of puppet on a MN.
            @result: mco feedback is correct
            @step: Stop the puppet service on particular MN using mco
            @result: puppet is not running on selected managed node only.
            @step: Issue an mco command to stop puppet on all nodes
            @result: puppet service is stopped on all MNs
            @step: Issue a cli command to start puppet on a particular MN
            @result: puppet is running on selected managed node only.
            @step: Issue an mco command to start puppet service on all nodes
            @result: puppet service is running on all MNs
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        all_nodes = []
        all_nodes.extend(self.ms_nodes)
        all_nodes.extend(self.mn_nodes)
        self.log('info', 'Issue an mco command to show the status of '
                 'puppet on a MN.')
        mco_cmd = self.cli.get_mco_cmd(
            "service puppet status -I {0}".format(self.mn_hname))
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

        self.assertTrue(ret_code == 0, "Non zero return code")

        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list("running", out),
                        "Unexpected mco response")

        self.log('info', 'Issue an mco command to show the status of puppet '
                 'on all MNs')
        mco_cmd = self.cli.get_mco_cmd("service puppet status")
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

        self.assertEqual([], err)
        self.assertEqual(0, ret_code)

        self.assertTrue(self.is_text_in_list("running", out),
                        "Unexpected mco response")

        self.log('info', 'Attempt to run an mco cli command to show the status'
                 ' of puppet on a MN.')
        cmd = "mco service puppet status"
        out, err, ret_code = self.run_command(self.mn_node, cmd)

        self.log("info", "Return code is [{0}]".format(ret_code))
        self.assertNotEqual(0, ret_code)

        self.assertEqual([], out)
        self.assertNotEqual([], err)
        self.assertTrue(self.is_text_in_list("command not found", err),
                        "Unexpected response")
        self.log('info', 'Stop the puppet service on particular MN using mco')
        mco_cmd = self.cli.get_mco_cmd(
            "service puppet stop -I {0}".format(self.mn_hname))
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)

        self.log('info', 'Verify that the puppet service is stopped on the MN')
        cmd = self.rhcmd.get_systemctl_status_cmd("puppet")
        out, err, ret_code = self.run_command(self.mn_node, cmd)
        self.assertTrue(ret_code < 4, "service cmd failed")
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list("Active: inactive (dead)", out),
                        "Unexpected service status response")

        self.log('info', 'Verify that puppet is not stopped on all other MNs')
        other_nodes = self.mn_nodes[1:]
        other_nodes.append(self.ms_node)
        for node in other_nodes:
            stdout, _, _ = self.run_command(node, cmd, default_asserts=True)
            self.assertTrue(self.is_text_in_list("Active: active (running)",
                             stdout),
                            "Unexpected service status response")
        self.log('info', 'Issue an mco command to stop puppet on all nodes')
        mco_cmd = self.cli.get_mco_cmd("service puppet stop -y")
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

        self.assertEqual(2, ret_code)

        self.assertEqual([], err)
        self.assertNotEqual([], out)

        self.log('info', 'Verify that the puppet service is stopped on '
                 'all MNs')
        for node in all_nodes:
            cmd = self.rhcmd.get_systemctl_status_cmd("puppet")
            out, err, ret_code = self.run_command(node, cmd)
            self.assertTrue(ret_code < 4, "service cmd failed")
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("Active: inactive (dead)",
                            out),
                            "Unexpected service status response")

        self.log('info', 'Issue a cli command to start puppet on a'
                 'particular MN')
        cmd = self.rhcmd.get_systemctl_start_cmd("puppet")
        stdout, _, _ = self.run_command(self.mn_node, cmd,
                                        su_root=True,
                                        default_asserts=True)
        self.assertEqual([], stdout)

        cmd = self.rhcmd.get_systemctl_status_cmd("puppet")
        stdout, _, _ = self.run_command(self.mn_node, cmd,
                                        su_root=True,
                                        default_asserts=True)
        self.assertTrue(self.is_text_in_list(
                        "Active: active (running)", stdout),
                        "Unexpected service running response")

        self.log('info', 'Issue an mco command to restart '
                 'puppet service on all nodes')
        mco_cmd = self.cli.get_mco_cmd("service puppet start -y")
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
        self.assertEqual(2, ret_code)
        self.assertEqual([], err)

        for node in all_nodes:
            cmd = self.rhcmd.get_systemctl_status_cmd("puppet")
            out, err, ret_code = self.run_command(node, cmd)
            self.assertTrue(ret_code < 4, "service cmd failed")
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("Active: active (running)",
                            out),
                            "Unexpected service status response")

    @attr('all', 'revert', 'story1840', 'story1840_tc10')
    def test_10_p_verify_mcollective_puppet_controlled(self):
        """
        @tms_id: litpcds_1840_tc10
        @tms_requirements_id: LITPCDS-1840
        @tms_title: Check mcollective is controlled by puppet
        @tms_description: Verify that mcollective configuration
            and the mcollective service is under puppet control.
            No puppet kick warning in the system log /var/log/messages
        @tms_test_steps:
            @step: Remove the mcollective configuration file.
            @result: The file is removed.
            @step: Verify that puppet recreates the file
            @result: The file is recreated.
            @step: Stop mcollective and puppet on nodes (ms + mn)
            @result: puppet is starting mcollective automatically
            @step: Verify that the restarted mcollective still works
            @result: mcollective service is running.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'Check that there are no logs from puppet '
                 'kick in the syslog')
        log_message = "kick is deprecated"
        self.assertFalse(self.wait_for_log_msg(self.ms_node, log_message,
                                               test_constants.
                                               GEN_SYSTEM_LOG_PATH,
                                               timeout_sec=10),
                         'We have logs from puppet kick in the syslog')
        self.log('info', 'Remove the mcollective configuration file.')
        cfg_file_reset = False
        mco_cfg_file = test_constants.MCOLLECTIVE_CONFIG_FILE
        cmd = self.rhcmd.get_move_cmd(mco_cfg_file, mco_cfg_file + "_old")
        stdout, _, _ = self.run_command(self.ms_node, cmd,
                                        su_root=True, default_asserts=True)
        self.assertEqual([], stdout)

        self.log('info', 'Verify that puppet recreates the file')
        check_file_cmd = 'ls {0}'.format(mco_cfg_file)
        self.assertTrue(self.wait_for_puppet_action(self.ms_node, self.ms_node,
                                                    check_file_cmd, 0),
                        "Config file not restored by puppet")

        self.log('info', 'Stop mcollective on nodes (ms + mn\'s)')
        # Stop mcollective service on MS
        stop_cmd = self.rhcmd.get_systemctl_stop_cmd("mcollective")
        stdout, _, _ = self.run_command(self.ms_node, stop_cmd,
                           su_root=True, execute_timeout=0.75,
                           default_asserts=True)
        self.assertEqual([], stdout)

        # Stop mcollective service on a managed node
        stdout, _, _ = self.run_command(self.mn_node, stop_cmd,
                           su_root=True, execute_timeout=0.75,
                           default_asserts=True)
        self.assertEqual([], stdout)

        self.log('info', 'Kill puppet on ms and one node in order to check'
                 ' after is autostarted mcollective is autostarted as well')
        # Kick puppet on MS
        cmd = "killall puppet -10 -u root"
        stdout, _, _ = self.run_command(self.ms_node, cmd,
                           su_root=True, execute_timeout=0.75,
                           default_asserts=True)
        self.assertEqual([], stdout)

        # Kick puppet on MN
        cmd = "killall puppet -10 -u root"
        stdout, _, _ = self.run_command(self.mn_node, cmd,
                           su_root=True, execute_timeout=0.75,
                           default_asserts=True)
        self.assertEqual([], stdout)

        self.log('info', 'Verify that the service is started again by '
                 'puppet (ms + mn\'s)')
        # Verify that the service is started again by puppet on MS
        status_cmd = self.rhcmd.get_systemctl_status_cmd("mcollective")
        self.assertTrue(self.wait_for_puppet_action(self.ms_node,
                                                    self.ms_node,
                                                    status_cmd, 0),
                        "Service not started by puppet on MS")

        self.log('info', 'Verify that the service is started again by puppet '
                 'on MN')
        # Verify that the service is started again by puppet on MN
        self.assertTrue(self.wait_for_puppet_action(self.ms_node, self.mn_node,
                                                    status_cmd, 0),
                        "Service not started by puppet on MN")

        # Verify that the restarted mcollective still works
        mco_cmd = self.cli.get_mco_cmd(
            "service puppet status -I {0}".format(self.mn_hname))
        out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)

        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertTrue(self.is_text_in_list("running", out),
                        "Unexpected mco response")

        self.log('info', 'Cleanup after the test')
        # Restore config file if puppet doesn't.
        if not cfg_file_reset:
            cmd = self.rhcmd.get_move_cmd(mco_cfg_file + "_old",
                                          mco_cfg_file)
            stdout, _, _ = self.run_command(self.ms_node, cmd,
                                            su_root=True,
                                            default_asserts=True)
            self.assertEqual([], stdout)
