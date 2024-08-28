'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@date:      January 2018
@author:    Bryan McNulty
@summary:   Integration tests for removal of root ssh access to LMS server.
'''
import test_constants as const
from litp_generic_test import GenericTest, attr
import paramiko
from redhat_cmd_utils import RHCmdUtils


class Story256031(GenericTest):
    """
    TORF-256031 As a LITP user I want the ability to remove root SSH
    access to the LMS
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story256031, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.ms_ip = self.get_node_att(self.ms_node, 'ipv4')
        self.admin_user = self.get_node_att(self.ms_node, "username")
        self.admin_pw = self.get_node_att(self.ms_node, "password")
        self.rootpw = self.get_node_att(self.ms_node, "rootpw")

        self.sshd_conf_path = self.find(self.ms_node,
                                            '/ms',
                                            'sshd-config')[0]
        self.ms_fw_coll_path = self.find(self.ms_node,
                                            '/ms',
                                            'collection-of-firewall-rule')[0]
        self.node_fw_coll_path = self.find(self.ms_node,
                                            '/deployments',
                                            'collection-of-firewall-rule')[1]

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story256031, self).tearDown()

    def _check_sshd_config_root_login(self, expected_value):
        """
        Description:
            Asserts that the sshd_config item is in an applied state, the
            permit_root_login item is as expected and that the
            'PermitRootLogin' item in the sshd config file is set correctly.

        Args:
            expected_value (str): This is the expected 'permit_root_login'
            value for the sshd_config item.
        """
        sshd_state = self.get_item_state(self.ms_node, self.sshd_conf_path)
        self.assertEqual('Applied', sshd_state,
            'The sshd_config item is not in an applied state as expected')
        permit_root_login_val = self.get_props_from_url(self.ms_node,
                                        self.sshd_conf_path,
                                        filter_prop='permit_root_login')
        self.assertEqual(expected_value, permit_root_login_val,
            "The value of the sshd_config items 'permit_root_login' " \
            "is {0} and not {0} as expected".format(
                permit_root_login_val, expected_value))

        grep_cmd = "{0} PermitRootLogin {1} | grep -v '#'".format(
                   const.GREP_PATH, const.SSH_CFG_FILE)

        stdout, _, _ = self.run_command(self.ms_node, grep_cmd, su_root=True)

        err_msg = "The 'PermitRootLogin' value in the '{0}' file is not " \
            "'{1}' as expected when the 'permit_root_login' value for the " \
            "sshd_config item is {2} in the model."

        sshd_conf_value = 'yes'
        if expected_value != 'true':
            sshd_conf_value = 'no'

        self.assertEqual(sshd_conf_value, stdout[0].split()[1],
                    err_msg.format(const.SSH_CFG_FILE,
                                   sshd_conf_value, expected_value))

    def _verify_idempotency(self, step_num):
        """
        Description:
            Record the state of the stopped plan & assert that the recreated
            plan is created with all the tasks which are in initial state in
            in the stopped plan, and also the recreated plan does not include
            the successful tasks from the stopped plan.
        Args:
            step_num (int): This is the step number to use in the first
            message this function's logs to test output.
        """
        self.log('info',
        '{0}. Record tasks in stopped plan in state "Initial" and state'
            ' "Success".'.format(step_num))
        successful = self.get_plan_task_states(self.ms_node,
                                              const.PLAN_TASKS_SUCCESS)
        initial_plan1 = self.get_plan_task_states(self.ms_node,
                                              const.PLAN_TASKS_INITIAL)

        successful_tasks_plan1 = [task['MESSAGE'] for task in successful]
        initial_tasks_plan1 = [task['MESSAGE'] for task in initial_plan1]

        self.log('info',
        '{0}. Re-create plan.'.format(step_num + 1))
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info',
        '{0}. Verify "Success" tasks from previous plan are not'
                'in recreated plan.'.format(step_num + 2))
        stdout, _, _ = self.execute_cli_showplan_cmd(self.ms_node)

        for task in successful_tasks_plan1:
            if "Lock" in task or "Unlock" in task:
                continue

            self.log('info', 'Verify successful task "{0}" not '
                            'in recreated plan'.format(task))
            self.assertFalse(self.is_text_in_list(task, stdout),
                            'Previously Successful task "{0}" found in '
                            'recreated plan:\n\n"{1}"'.format(task, stdout))

        self.log('info',
        '{0}. Verify "Initial" tasks from previous plan are in '
                  'recreated plan'.format(step_num + 3))

        initial_plan2 = self.get_plan_task_states(self.ms_node,
                                                  const.PLAN_TASKS_INITIAL)

        initial_tasks_plan2 = [task['MESSAGE'] for task in initial_plan2]

        for task in initial_tasks_plan1:
            if "Lock" in task or "Unlock" in task:
                continue

            self.log('info',
                    'Verify task "{0}" in recreated plan'.format(task))
            self.assertTrue(self.is_text_in_list(task, initial_tasks_plan2),
                            'Previously Initial task "{0}" not found in '
                            'recreated plan:\n\n"{1}"'.format(task, stdout))

    @attr('all', 'revert', 'Story256031', 'Story256031_tc04')
    def test_04_verify_sshd_config_behavior(self):
        """
        @tms_id: TORF-256031_tc_04, TORF-256031_tc_22,
            TORF-256031_tc_17, TORF-256031_tc_05, TORF-256031_tc_08,
            TORF-256031_tc_21, TORF-256031_tc_18
        @tms_requirements_id: TORF-256031
        @tms_title: Multiple IT tests for story to remove ssh root access
            to the LMS server.
        @tms_description: Remove SSH root access to MS, & test that ssh
            connection from a gateway to MS with root user fails.
            Check plan idempotency by stopping plan before update of
            sshd_config item is applied, then restarting plan.
            Upgrade openssh using yum upgrade, when root access is not
            allowed.
            Remove SSH root access to MS, & test ssh connection from a gateway
            to MS with valid non-root user.
            Reboot the MS, when root access is not allowed.
            Check plan idempotency by stopping plan before update of
            sshd_config item, then restarting plan.
            Enable root login on MS when it was not permitted from gateway.
        @tms_test_steps:
            @step: Create a plan with new firewall rules on the ms & a node
                and an update on the 'sshd_config' item's 'permit_root_login'
                property to 'false'
            @result: Plan is created successfully.
            @step: Run the plan and wait for the phase with the update on the
                'sshd_config' item to be in the running state.
            @result: phase with the update on the 'sshd_config' item is in a
                running state.
            @step: Stop plan
            @result: Plan is stopped
            @step: Record tasks in stopped plan in
                state 'initial' and 'success'
            @result: Plan states stored successfully
            @step: Re-create plan
            @result: Plan recreated successfully
            @step: Verify successful tasks not in recreated plan
            @result: Successful tasks not in recreated plan
            @step: Verify initial tasks from previous plan
                are in recreated plan
            @result: Initial tasks in recreated plan
            @step: Run the plan.
            @result: Plan completes successfully.
            @step: Check the 'sshd_config' item'
            @result: The state is set to 'applied', the 'permit_root_login'
                property is set to false.
            @step: Attempt to login with root user from the gateway.
            @result: An 'AuthenticationException' will be raised.
            @step: Attempt to logon to MS with the litp-admin user.
            @result: The attempt is successful.
            @step: Reboot the MS.
            @result: The reboot is successful.
            @result: the permit root login property remains set as false.
            @step: Create a plan with updates to the firewall rules on the ms
                & a node and an update on the 'sshd_config' item's
                'permit_root_login' property to 'true'.
            @result: Plan created successfully
            @step: Run the plan and stop it before the phase with the
                'sshd_config update' starts.
            @result: Plan stops as expected
            @step: Record tasks in stopped plan in
                state 'initial' and 'success'
            @result: Plan states stored successfully
            @step: Re-create plan
            @result: Plan recreated successfully
            @step: Verify successful tasks not in recreated plan
            @result: Successful tasks not in recreated plan.
            @step: Verify initial tasks from previous plan
                are in recreated plan.
            @result: Initial tasks in recreated plan.
            @step: Run the plan
            @result: The plan is successful.
            @step: Attempt to logon with root user from the gateway.
            @result: The attempt is successful.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # Test Case 4. Remove SSH root access to MS, & test that ssh connection
        # from a gateway to MS with root user fails.
        #
        # Test case 22. Check plan idempotency by stopping plan after update
        # of sshd_config item is applied, then recreating and running plan.
        self.log('info',
        "1.  Create a plan with config tasks which also includes an update "
            "to the sshd_config item to change 'permit_root_login to false'.")
        self.execute_cli_create_cmd(self.ms_node,
                        '{0}/fw_icmp_15'.format(self.ms_fw_coll_path),
                        'firewall-rule',
                        props='action="accept" name="115 icmp" proto="icmp"')
        self.execute_cli_update_cmd(self.ms_node,
                        self.sshd_conf_path,
                        'permit_root_login=false')
        self.execute_cli_create_cmd(self.ms_node,
                        '{0}/fw_icmp_116'.format(self.node_fw_coll_path),
                        'firewall-rule',
                        props='action="accept" name="116 icmp" proto="icmp"')
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info',
        '2. Run the plan and stop it after the sshd_config update')
        self.execute_cli_runplan_cmd(self.ms_node)
        self.wait_for_task_state(self.ms_node, 'Set the SSHD config on',
            const.PLAN_TASKS_RUNNING)
        self.execute_cli_stopplan_cmd(self.ms_node)
        self.wait_for_plan_state(self.ms_node, const.PLAN_STOPPED)

        # Below function will record the state of the stopped plan,
        # recreate the plan & assert they are equal to states of the
        # recreated plan.
        self._verify_idempotency(3)

        self.log('info',
        "7.  Run the plan and check that the 'permit_root_login'"
            "property is as expected")
        self.run_and_check_plan(self.ms_node, const.PLAN_TASKS_SUCCESS, 10)
        self._check_sshd_config_root_login('false')

        self.log('info',
        '8.  Assert that attempting to login with root user will raise a '
            'paramiko AuthenticationException')
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.assertRaises(paramiko.AuthenticationException, session.connect,
                self.ms_ip, username='root', password=self.rootpw)

        # Test Case 17. Reinstall openssh using yum to simulate a yum upgrade
        # when root access is not allowed.
        self.log('info',
        "9.  Reinstall the openssh package, verify it's reinstall in the "
            "logs and check that 'permit_root_login' property remains set "
            "to false as expected in the model & check that the "
            "PermitRootLogin value in the /etc/ssh/sshd_config file remains "
            "set to 'no' as expected.")
        start_pos = self.get_file_len(self.ms_node,
                                          const.GEN_SYSTEM_LOG_PATH)
        msg = 'Installed: openssh-server-7.4p1-21.el7.x86_64'
        log_not_found_msg = '"{0}" not found in {1} as expected.'.format(
            msg, const.GEN_SYSTEM_LOG_PATH)
        cmd = self.rhcmd.get_yum_cmd('reinstall -y openssh-server.x86_64')

        self.run_command(self.ms_node, cmd, su_root=True)
        msg_found = self.check_for_log(self.ms_node, msg,
                                    const.GEN_SYSTEM_LOG_PATH,
                                    start_pos,
                                    su_root=False)
        self.assertTrue(msg_found, log_not_found_msg)
        self._check_sshd_config_root_login('false')

        # Test Case 5. Remove SSH root access to MS, & test ssh connection
        # from a gateway to MS with valid non-root user.
        self.log('info',
        '10.  Login to MS with litp-admin will be successful.')
        session.connect(self.ms_ip, username=self.admin_user,
                                        password=self.admin_pw)
        _, stdout, _ = session.exec_command('hostname -I')
        host_ip = stdout.readlines()[0].split()[0]
        ssh_conn_err = "There has been an error in the ssh " \
                           "connection to the MS."
        self.assertEqual(host_ip, self.ms_ip, ssh_conn_err)

        # Test Case 18. Reboot the MS, when root access is not allowed.
        self.log('info',
        '11.  Reboot the MS')
        cmd = "{0} -r now".format(const.SHUTDOWN_PATH)
        self.run_command(self.ms_node, cmd, su_root=True,
                         default_asserts=False)
        self.assertTrue(self.wait_for_ping(self.ms_ip, False, retry_count=4),
                        "Node '{0} has not gone down".format(self.ms_node))
        self.assertTrue(self.wait_for_node_up(self.ms_node,
                        wait_for_litp=True), "'{0} did not come up in "
                        "expected timeframe".format(self.ms_node))

        self.log('info',
        '12.  Check the permit root login property remains set as false')
        self._check_sshd_config_root_login('false')

        # Test case 21. Check plan idempotency by stopping plan before update
        # of sshd_config item, then recreating & running the plan.
        #
        # Test case 8. Enable root login on MS when it was not permitted
        # from gateway
        self.log('info',
        '13.  Create a plan which includes a sshd_config update '
            'and other items')
        self.execute_cli_update_cmd(self.ms_node,
                                '{0}/fw_icmp_15'.format(self.ms_fw_coll_path),
                        props='proto="tcp"')

        self.execute_cli_update_cmd(self.ms_node,
                                    self.sshd_conf_path,
                                    'permit_root_login=true')
        self.execute_cli_update_cmd(self.ms_node,
                            '{0}/fw_icmp_116'.format(self.node_fw_coll_path),
                        props='proto="tcp"')
        self.execute_cli_createplan_cmd(self.ms_node)

        self.log('info',
        '14.  Run the plan and stop it before the sshd_config update')
        self.execute_cli_runplan_cmd(self.ms_node)
        self.wait_for_task_state(self.ms_node, 'Update firewall rule '
            '\"115 icmp\" on node', const.PLAN_TASKS_RUNNING,
            ignore_variables=False)
        self.execute_cli_stopplan_cmd(self.ms_node)
        self.wait_for_plan_state(self.ms_node, const.PLAN_STOPPED)

        # Below function will record the state of the stopped plan,
        # recreate the plan & assert they are equal to states of the
        # recreated plan.
        self._verify_idempotency(15)

        self.log('info',
        "19.  Run the remainder of the plan and ensure that it's successful.")
        self.execute_cli_runplan_cmd(self.ms_node)
        self.wait_for_plan_state(self.ms_node, const.PLAN_COMPLETE)
        self._check_sshd_config_root_login('true')

        self.log('info',
        '20.  Test ssh connection to MS sever using root user.')
        session.connect(self.ms_ip,
                        username='root',
                        password=self.rootpw)
        _, stdout, _ = session.exec_command('hostname -I')
        host_ip = stdout.readlines()[0].split()[0]
        self.assertEqual(host_ip, self.ms_ip, ssh_conn_err)
