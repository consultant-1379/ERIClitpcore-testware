"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2014, Refactored May 2019
@author:    Padraic, Yashi Sahu
@summary:   Tests to verify functionality delivered in Story 2490.
                -Install Mcollective.
                -Note: Mcollective functionality is tested in another story.
                -Prevent root ssh on managed nodes.
                -Configure yum repositories on managed nodes.
                -Create the litp-admin user on managed nodes.
            Agile: STORY-2490
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const


class Story2490(GenericTest):
    """
    As an admin I want software and configuration that are essential to LITP
    functionality to be deployed by default, without having to add anything
    to my model.
    """

    def setUp(self):
        """Runs before every test"""
        super(Story2490, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.node1 = self.mn_nodes[0]
        self.all_nodes = [self.ms_node] + self.mn_nodes
        self.rootpw_ms = self.get_node_att(self.ms_node, "rootpw")
        self.lpa_passwd = self.get_node_att(self.ms_node, "password")
        self.repos = ["OS", "3PP", "LITP"]
        self.cfg_file = const.SSH_CFG_FILE
        self.litp_admin = "litp-admin"
        self.rhcmd = RHCmdUtils()

    def tearDown(self):
        """Runs after every test"""
        super(Story2490, self).tearDown()

    def get_user_groups(self, user, rootpw):
        """
        Description:
            Get the list of groups a user belongs to
        Args:
            user (str): The user to check groups for
            rootpw (str): The root password of user
        Returns:
            user_groups (list): Groups the user belongs
                                to.
        """
        cmd = '{0} {1}'.format(const.GROUPS_PATH, user)
        stdout = self.run_command(self.ms_node, cmd,
                                  username="root",
                                  password=rootpw,
                                  default_asserts=True)[0][0]
        user_groups = ((stdout.split(': '))[1]).split(' ')

        return user_groups

    def check_root_ssh_connection(self, expect_success=False):
        """
        Description:
           Checks ssh connection to the node
        Kwargs:
           expect_success(bool):If True, will expect ssh connection
           to be successful. Default is False
        """

        stdout = self.run_command_via_node(self.ms_node, self.node1,
                                    "hostname",
                                    username="root", password=self.rootpw_ms,
                                    timeout_secs=10)[0]
        err_msg = "Permission denied, please try again."

        if not expect_success:
            self.assertEqual(err_msg, stdout[-1],
                             "Expected error message not "
                             "found")
        else:
            self.assertNotEqual(err_msg, stdout[-1],
                                "ssh connection failed when it "
                                "was expected to be successful")

    def wait_for_puppet_restore_litp_admin(self, puppet_interval):
        """
        Description:
            Waits for puppet to restore litp-admin user
        Args
            Puppet interval(int): interval between
             puppet runs.
        """
        # Note: cannot utilize utils as methods first login
        # as litp-admin and the litp-admin user does not
        # currently exist as part of this test.
        puppet_wait_mins = (puppet_interval / 60) * 2

        puppet_status = '{0} puppet status | ' \
                        '{1} "Currently applying a catalog"'.format(
            const.MCO_EXECUTABLE, const.GREP_PATH)

        run_complete = self.wait_for_cmd(self.ms_node,
                                         puppet_status, 1,
                                         default_time=2,
                                         direct_root_login=True)

        self.assertTrue(run_complete, "Current puppet run did not complete in "
                                      "the required time")
        self.run_mco_command(self.ms_node, "{0} puppet "
                                "runonce".format(const.MCO_EXECUTABLE))
        cmd = self.rhcmd.get_grep_file_cmd(const.PASSWD_PATH,
                                           self.litp_admin)

        action = self.wait_for_cmd(self.ms_node, cmd, 0,
                                   timeout_mins=puppet_wait_mins,
                                   direct_root_login=True)
        self.assertTrue(action, "{0} user not found".
                        format(self.litp_admin))

    def execute_replace_str_in_file_cmd(self, original_value, new_value,
                                        search_file, default_asserts=True):
        """
        Description:
            Replaces all strings in a given file on node1
        Args:
            original_value (str): The old string that should be
                           replaced.
            new_value (str): The new string.
            search_file (str): The filepath
        Kwargs:
            default_asserts(bool): By default set to True, false
                            otherwise
        """

        cmd_replace_txt = self.rhcmd.get_replace_str_in_file_cmd(
                                    original_value,
                                    new_value,
                                    search_file, sed_args='-i')

        self.run_command(self.node1, cmd_replace_txt, su_root=True,
                         default_asserts=default_asserts)

    @attr('all', 'revert', 'story2490', 'story2490_tc01')
    def test_01_p_mcollective_running(self):
        """
        @tms_id: litpcds_2490_tc1
        @tms_requirements_id: LITPCDS-2490
        @tms_title: mcollective running on all nodes
        @tms_description: This test checks mcollective service is running on
           MS and all managed nodes.
        @tms_test_steps:
        @step: Run service mcollective status on the ms and peer nodes
        @result: mcollective is running on the ms and peer nodes
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info",
                 "1. Verify that the mcollective service is running on MS "
                 "and peer nodes")
        for node in self.all_nodes:
            self.get_service_status(node, "mcollective",
                                     su_root=True)

    @attr('all', 'revert', 'story2490', 'story2490_tc02')
    def test_02_p_litp_admin_enforced_on_ms(self):
        """
        @tms_id: litpcds_2490_tc2
        @tms_requirements_id: LITPCDS-2490
        @tms_title: puppet recreates litp-admin user if removed
        @tms_description: This test checks litp-admin user is enforced,
           so that it's recreated if it's deleted manually.
        @tms_test_steps:
        @step: Get the groups the "litp-admin" user
                belongs to
        @result: User groups of litp-admin user obtained.
        @step: Check if litp-admin user is logged in
        @result: litp-admin user is successfully logged_in.
        @step: Logout and assert the litp-admin user
        @result: litp-admin successfully logged_out and
            assertion confirmed .
        @step: Delete and assert the litp-admin user
        @result: Litp -admin user deleted and assertio
              is confirmed .
        @step: Wait for litp-admin user to be restored
        @result: litp-admin user successfully restored
        @step: Verify litp-admin user has been added
                to correct groups.
        @result: litp-admin user is suceesfuly added to
               user groups.
        @step: Finally restore the litp-admin user
        @result: litp-admin is successfully restored.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        try:
            puppet_interval = self.get_puppet_interval(self.ms_node)

            self.log('info', "1. Get the groups the litp-admin user "
                             "belongs to")
            user_groups = self.get_user_groups(self.litp_admin, self.rootpw_ms)

            self.log('info', "2. Check if litp-admin user is logged in")
            cmd = self.rhcmd.get_ps_cmd(args="-elf | grep {0} | grep -v grep".
                                      format(self.litp_admin))
            logged_in, err, ret_code = self.run_command(self.ms_node, cmd,
                                                 username="root",
                                                 password=self.rootpw_ms)
            # Assert ret_code < 2. ret_code 1 is valid: no lines found.
            self.assertTrue((ret_code < 2), 'Command: "{0}" failed '
                                            'with error code: "{1}"'.
                            format(cmd, ret_code))
            self.assertEqual([], err, '"{0}" user '
                                      'is not logged in'.
                             format(self.litp_admin))

            self.log('info', "3. Logout the litp-admin user")
            if logged_in:
                cmd = "{0} -KILL -u {1}".format(const.PKILL_PATH,
                                                self.litp_admin)
                err, ret_code = self.run_command(self.ms_node, cmd,
                                                    username="root",
                                        password=self.rootpw_ms)[1:]
                self.assertTrue((ret_code < 2), 'Command: "{0}" failed '
                                    'with error code: "{1}"'.
                                format(cmd, ret_code))
                self.assertEqual([], err, "Failed to logout litp-admin user")

            self.log('info', "4. Delete the litp-admin user")
            cmd = '{0} {1}'.format(const.USERDEL_PATH, self.litp_admin)
            err, ret_code = self.run_command(self.ms_node, cmd,
                                          username="root",
                                          password=self.rootpw_ms)[1:]

            # Fails to remove user's 'group' as 'celery' user was added to
            # 'litp-admin' group as part of TORF-289907 but user is still
            # successfully removed
            errors_to_ignore = ["userdel: group litp-admin not removed "
                                "because it has other members."]

            self.assertEqual(errors_to_ignore, err, "Unexpected errors "
                                         "found: {0}".format(err))
            self.assertEqual(0, ret_code, "Failed to remove "
                                          "the litp-admin user")

            self.log('info', "5.Wait for litp-admin user to be restored")
            self.wait_for_puppet_restore_litp_admin(puppet_interval)

            self.log('info', "6. Verify litp-admin user has been added "
                             "to correct groups")
            restored_groups = self.get_user_groups(self.litp_admin,
                                                   self.rootpw_ms)

            self.log('info', "7. Add 'litp-access' group as puppet manifest "
                             "restores only groups 'litp-admin' and 'celery'")
            if 'litp-access' not in restored_groups:
                restored_groups.append('litp-access')

            self.assertEqual(user_groups, restored_groups, "litp-admin "
                                    "user has not been added to all groups")

        finally:
            self.log('info', "8. Finally restore the litp-admin user")
            cmd = '{0} {1}'.format(const.USERDEL_PATH, self.litp_admin)
            err, ret_code = self.run_command(self.ms_node, cmd,
                                          username="root",
                                          password=self.rootpw_ms)[1:]
            cmd = ("{0} {1} -u 1000 -g {2} -G "
                   "{3},{4},{5} -p `openssl passwd  -1 {6} `".
                   format(const.USERADD_PATH,
                          self.litp_admin,
                          self.litp_admin,
                          user_groups[0],
                          user_groups[1],
                          user_groups[2],
                          self.lpa_passwd))
            self.run_command(self.ms_node, cmd,
                             username="root",
                             password=self.rootpw_ms)

    @attr('all', 'revert', 'story2490', 'story2490_tc03')
    def test_03_p_os_yum_repo_available(self):
        """
        @tms_id: litpcds_2490_tc3
        @tms_requirements_id: LITPCDS-2490
        @tms_title: expected repositories available on all nodes
        @tms_description: This test verifies that the OS, litp and 3pp
           repositories are all available on the MS and MNs.
        @tms_test_steps:
         @step: Check OS, litp, 3pp are all available
                repos on the MS and peer nodes
         @result: OS, 3PP and LITP repos available on ms and
              peer nodes.
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', "1. Check OS, litp, 3pp are all "
                    "available repos on the MS and peer nodes")
        yum_repolist = self.rhcmd.check_yum_repo_cmd()
        for node in self.all_nodes:
            check_yum_output = self.run_command(node, yum_repolist,
                                     su_root=True, default_asserts=True)[0]
            for repo in self.repos:
                self.assertTrue(self.is_text_in_list(repo, check_yum_output),
                                "OS repo not available on {0}".format(repo))

    @attr('all', 'revert', 'story2490', 'story2490_tc04')
    def test_04_p_os_yum_repo_enforced(self):
        """
        @tms_id: litpcds_2490_tc4
        @tms_requirements_id: LITPCDS-2490
        @tms_title: puppet enforces repositories present on nodes
        @tms_description: This test verifies that the yum repository is
            enforced so that it is recreated if it is deleted manually.
        @tms_test_steps:
         @step:  Remove the yum repositories on the MS and peer nodes.
         @result: Yum repositories removed from Ms and peer nodes.
         @step: Start a new puppet run and wait for puppet
                to recreate the yum repositories
         @result: New yum repositories created successfully.
         @step: Verify that the repositories are recreated
                by puppet on MS and peer nodes
         @result: Yum repositories created successfully on MS
                and peer nodes.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log("info", "1. Remove the yum repositories on the "
                         "MS and peer nodes")
        path = "/tmp/tmp2490/"
        for node in self.all_nodes:
            dir_created = self.create_dir_on_node(node, path, su_root=True)
            self.assertTrue(dir_created, "Directory '{0}' could not "
                                         "be created".format(path))
            file_moved = self.mv_file_on_node(node, "{0}/*".format
                                        (const.YUM_CONFIG_FILES_DIR),
                                             path, su_root=True)
            self.assertTrue(file_moved, "File '{0}' was not moved to '{1}' "
                                       "successfully".format(path,
                                            const.YUM_CONFIG_FILES_DIR))
        self.log('info', "2. Start a new puppet run and wait for puppet "
                         "to recreate the yum repositories")
        self.start_new_puppet_run(self.ms_node)

        self.log('info', "3. Verify that the repositories are recreated "
                         "by puppet on MS and peer nodes")
        check_repo_cmd = self.rhcmd.check_repo_cmd(self.repos)
        for node in self.all_nodes:
            repos_present = self.wait_for_puppet_action(self.ms_node,
                                         node, check_repo_cmd, 0)
            self.assertTrue(repos_present, "Expected Repos {0} "
                                           "not re-created by puppet")

    @attr('all', 'revert', 'story2490', 'story2490_tc05')
    def test_05_p_no_root_ssh_enforced(self):
        """
        @tms_id: litpcds_2490_tc5
        @tms_requirements_id: LITPCDS-2490
        @tms_title: puppet enforces root cannot ssh to managed node
        @tms_description: This test checks that root user cannot ssh to
            a managed node and that this is enforced by puppet.
        @tms_test_steps:
          @step: Change the SSH Deamon config to
                permit root login.
          @result: SSH deamon config successfully changed
                 to permit root login.
          @step: Verify direct root ssh access to a
                 peer node is now possible
          @result: Ssh connection successfully executed
               on node.
          @step: Start new puppet run and wait for
               puppet to restore original SSH config.
          @result: Puppet restored original ssh config
          @step:  Verify direct root ssh access to a peer
                 node is not possible
          @result: Direct root ssh access to a peer node
                   failed.
          @step: Change the SSH Daemon config back
                if puppet misses .
          @result: Executed successfully.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        sshd_was_reset = False
        try:
            self.log("info", "1. Change the SSH Deamon config to "
                             "Permit Root Login")
            sshd_orig_text = 'PermitRootLogin no'
            sshd_txt_replace = 'PermitRootLogin yes'
            self.execute_replace_str_in_file_cmd(sshd_orig_text,
                                            sshd_txt_replace, self.cfg_file)

            sshd_was_reset = True
            self.restart_service(self.node1, 'sshd',
                                 su_root=True)
            self.log('info', '2. Verify direct root ssh access to a peer'
                             ' node is now possible')
            self.check_root_ssh_connection(expect_success=True)
            self.log('info', "3.Start new puppet run and wait for "
                             "puppet to restore original SSH config")
            self.start_new_puppet_run(self.ms_node)
            cmd = self.rhcmd.get_grep_file_cmd(self.cfg_file, [sshd_orig_text])
            self.wait_for_puppet_action(self.ms_node, self.node1, cmd, 0,
                                        su_root=True)
            self.log('info', '4. Verify direct root ssh access to a peer'
                             ' node is not possible')
            self.check_root_ssh_connection()
        finally:
            if sshd_was_reset:
                self.log('info', "In case puppet misses it, "
                                 "change the ssh config back ")
                sshd_orig_text = 'PermitRootLogin yes'
                sshd_txt_replace = 'PermitRootLogin no'
                self.execute_replace_str_in_file_cmd(sshd_orig_text,
                                        sshd_txt_replace, self.cfg_file)
                self.restart_service(self.node1, 'sshd',
                                     su_root=True)
