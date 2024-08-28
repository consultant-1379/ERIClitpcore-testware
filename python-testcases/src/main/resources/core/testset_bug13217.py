'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2016
@author:    Alexander Pugachev
@summary:   Litp Logging force_debug= true in the model but not returning
            debug messages to logs
            Agile: BUG LITPCDS-13217
'''
import test_constants as const
from litp_cli_utils import CLIUtils
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
from ConfigParser import SafeConfigParser


class Bug13217(GenericTest):
    """
    I expect LITP service to read litp_logging.conf for logging level
    and force_debug options of /litp/logging model item can be changed
    only manually.

    I expect restore_model to not have an impact on logging level
    and force_debug.
    """
    def setUp(self):
        """ Runs before every single test """
        super(Bug13217, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.rhc = RHCmdUtils()
        self.last_log_position = None
        self._stop_litpd(ignore_error=True)
        self._start_litpd()
        self.logging_path = self.find(self.ms_node, '/litp', 'logging')[0]
        self.fw_rule_coll_path = self.find(self.ms_node,
                                    '/ms',
                                    'collection-of-firewall-rule')[0]
        self.fw_icmp_path = '{0}/fw_icmp'.format(self.fw_rule_coll_path)
        self.scp = SafeConfigParser()
        self.logging_local_path = '/tmp/litp_logging.conf'
        #test_03 variables
        self.new_fw_rule_url = '{0}/fw_story13217'.format(
                                        self.fw_rule_coll_path)
        self.props_t3 = 'name="555 story 13217"'

    def tearDown(self):
        """ Runs after every single test """
        # 1. Ensure true is turned on after test run
        self._start_litpd(ignore_error=True)
        self.turn_on_litp_debug(self.ms_node)

        # 2. Call superclass teardown
        super(Bug13217, self).tearDown()

    def _remember_log_position(self):
        """Save log file length for later use."""
        self.last_log_position = self._current_log_position()

    def _current_log_position(self):
        """Measure log file length for later use."""
        return self.get_file_len(
            self.ms_node, const.GEN_SYSTEM_LOG_PATH)

    def _stop_litpd(self, ignore_error=False):
        """Stop litpd service

        Stops service and wait for it to stop responding to API calls.

        Can ignore failing attempt. It is useful if service is already stopped.

        :param boolean ignore_error: whether to tolerate "service" call error
        """
        self.stop_service(self.ms_node, 'litpd',
                          add_to_cleanup=False,
                          assert_success=not ignore_error)
        cmd = self.cli.get_show_cmd('/')
        self.wait_for_cmd(self.ms_node, cmd, 1, default_time=3)

    def _start_litpd(self, ignore_error=False):
        """Start litpd

        Starts service and wait for it to start responging to API calls.

        Can ignore failing attempt. It is useful is service is already started.

        :param boolean ignore_error: whether to tolerate "service" call error
        """
        self.start_service(self.ms_node, 'litpd',
                           assert_success=not ignore_error)
        cmd = self.cli.get_show_cmd('/')
        self.wait_for_cmd(self.ms_node, cmd, 0, default_time=3)

    def _assert_force_debug(self, expected_value):
        """Assert force_debug has given value

        Makes an assertion that "/litp/logging" model item's
        property "force_debug" has given value
        :param string expected_value: value to assert
        """
        force_debug_val = self.execute_show_data_cmd(self.ms_node,
                                                    self.logging_path,
                                                    'force_debug')
        self.assertEqual(force_debug_val, expected_value)

    def _noise_in_log(self):
        """Leave accountable traces in log

        Manipulates litpd service to make it emit messages of severity
        "INFO" and "DEBUG" to /var/log/messages.
        """
        # emits some info level log messages.
        self.execute_cli_update_cmd(
            self.ms_node,
            self.fw_icmp_path,
            'name="100 icmp2"')
        # reverts changes done to deployment model.
        self.execute_cli_update_cmd(
            self.ms_node,
            self.fw_icmp_path,
            'name="100 icmp"')
        # emits some debug level log messages.
        cmd = self.cli.get_litp_version_cmd()
        self.run_command(self.ms_node, cmd, default_asserts=True)

    def _assert_effective_logging_level(self, expected_level):
        """Assert litpd is logging with at least a given logging level

        :param string expected_level: log message severity to search for
        """
        level_marker = "{0}: ".format(expected_level)
        self.assertTrue(self.wait_for_log_msg(
            self.ms_node,
            level_marker,
            timeout_sec=60,
            log_len=self.last_log_position))

    def _set_force_debug(self, value):
        """Set force_debug to given value

        Uses CLI to update "/litp/logging" model item's property "force_debug".

        :param string value: new value for force_debug
        """
        cmd = self.cli.get_litp_debug_cmd(value == 'true')
        self.run_command(self.ms_node, cmd, default_asserts=True)

    def _patch_conf(self):
        """Patch litpd configuration to all-debug version

        Replaces logging levels in /etc/litp_logging.conf.
        Every level "INFO" turns into "DEBUG".
        """
        pattern = "level=INFO"
        replacement = "level=DEBUG"

        self.backup_file(self.ms_node,
                            const.LITP_LOGGING_CONF,
                            restore_after_plan=False)

        cmd = "{0} -i.bak s/{1}/{2}/g {3}".format(const.SED_PATH,
                                                  pattern,
                                                  replacement,
                                                  const.LITP_LOGGING_CONF)
        self.run_command(self.ms_node, cmd,
                         add_to_cleanup=False,
                         su_root=True,
                         default_asserts=True)

        cmd = self.rhc.get_grep_file_cmd(const.LITP_LOGGING_CONF, pattern)
        _, _, rc = self.run_command(self.ms_node, cmd,
                                    add_to_cleanup=False)
        self.assertNotEqual(rc, 0)

        cmd = self.rhc.get_grep_file_cmd(const.LITP_LOGGING_CONF, replacement)
        self.run_command(self.ms_node, cmd,
                         add_to_cleanup=False,
                         default_asserts=True)

    def _run_deployment_plan(self):
        """Run plan

        Creates simple plan, runs it and waits for it finish successfully.
        """
        self.execute_cli_update_cmd(
            self.ms_node,
            self.fw_icmp_path,
            'name="100 icmp3"')
        self.run_and_check_plan(self.ms_node, const.PLAN_COMPLETE, 20)

    @attr('all', 'revert', 'story13217', 'story13217_tc01')
    def test_01_restart_then_restore_model(self):
        """
        @tms_id: litpcds_13217_tc01
        @tms_requirements_id: LITPCDS-227
        @tms_title: Tests that when force_debug is "false" restore_model does
            not bring back force_debug="true"
        @tms_description: Tests that when force_debug is "false" restore_model
            does not bring back force_debug="true"
        @tms_test_steps:
            @step: Check that force_debug is "false"
            @result: Logging behaves as expected
            @step: Set force_debug to "True" & check logging level
            @result: Logging behaves as expected
            @step: Run a deloyment plan & wait for it to complete
            @result: Deployment plan completes
            @step: Assert that "force_debug" is set to "true" in config
            @result: "force_debug" is as expected in config
            @step: Restart litpd service
            @result: Litpd service restarts successfully
            @step: Check that force_debug is "false"
            @result: Logging behaves as expected
            @step: Restore model
            @result: Model restores successfully
            @step: Check that force_debug is "false"
            @result: Logging behaves as expected
        @tms_test_precondition: The debug level is set to "INFO" in
                                 /etc/litp_logging.conf
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. remember last log position')
        self._remember_log_position()
        self.log('info',
        '2. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '3. assert force_debug is "false"')
        self._assert_force_debug("false")
        self.log('info',
        '4. assert effective logging level is INFO since last log position')
        self._assert_effective_logging_level("INFO")
        self.turn_on_litp_debug(self.ms_node)
        self.log('info',
        '5. remember last log position')
        self._remember_log_position()
        self.log('info',
        '6. Create messages in log(noise) by running litp commands')
        self._noise_in_log()
        self.log('info',
        '7. assert force_debug is "true"')
        self._assert_force_debug("true")
        self.log('info',
        '8. assert effective logging level is DEBUG since last log position')
        self._assert_effective_logging_level("DEBUG")
        self.log('info',
        '9. run deployment plan')
        self._run_deployment_plan()
        self.log('info',
        '10. stop litpd')
        self._stop_litpd()
        self.log('info',
        '11. start litpd')
        self._start_litpd()
        self.log('info',
        '12. remember last log position')
        self._remember_log_position()
        self.log('info',
        '13. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '14. assert force_debug is "false"')
        self._assert_force_debug("false")
        self.log('info',
        '15. assert effective logging level is INFO'
        ' since last log position')
        self._assert_effective_logging_level("INFO")
        self.log('info',
        '16. restore model')
        self.execute_cli_restoremodel_cmd(self.ms_node)
        self.log('info',
        '17. remember last log position')
        self._remember_log_position()
        self.log('info',
        '18. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '19. assert force_debug is "false"')
        self._assert_force_debug("false")
        self.log('info',
        '20. assert effective logging level is INFO'
        ' since last log position')
        self._assert_effective_logging_level("INFO")

    @attr('all', 'revert', 'story13217', 'story13217_tc02')
    def test_02_force_debug_on_debug(self):
        """
        @tms_id: litpcds_13217_tc02
        @tms_requirements_id: LITPCDS-227
        @tms_title: If configuration file has level DEBUG then force_debug
            is still controlled only manually.
        @tms_description: If configuration file has level DEBUG then
            force_debug is still controlled only manually.
        @tms_test_steps:
            @step: Stop litpd
            @result: Litpd stopped successfully
            @step: Patch LITP "litp_logging.conf" with logging level DEBUG
            @result: "litp_logging.conf" updated without error
            @step: Start litpd
            @result: "litpd" started successfully
            @step: Create messages in log(noise) by running litp commands
            @result: Noise successfully created in log.
            @step: Assert force_debug is "false"
            @result: Assertion successful
            @step: Assert effective logging level is DEBUG since last log
                position
            @result: Assertion successful
            @step: Set force_debug to "true"
            @result: Force_debug set to "true" successfully
            @step: Remember last log position
            @result: Log position recorded successfully
            @step: Create messages in log by running litp commands
            @result: Noise successfully created in logs
            @step: Assert force_debug is "true"
            @result: Assertion successful
            @step: Assert effective logging level is DEBUG since last log
                position
            @result: Assertion successful
            @step: Set force_debug to "false"
            @result: Force_debug set to "false" successfully
            @step: Remember last log position
            @result: Log position recorded successfully
            @step: Create messages in log by running litp commands
            @result: Noise successfully created in logs
            @step: Assert force_debug is "false"
            @result: Assertion successful
            @step: Assert effective logging level is DEBUG since last log
                position
            @result: Assertion successful
        @tms_test_precondition: The debug level is set to "INFO" in
                                 /etc/litp_logging.conf
        @tms_execution_type: Automated
        """
        self.log('info',
        ' 1. stop litpd')
        self._stop_litpd()
        self.log('info',
        '2. patch LITP litp_logging.conf with logging level DEBUG')
        self._patch_conf()
        self.log('info',
        '3. start litpd')
        self._start_litpd()
        self.log('info',
        '4. remember last log position')
        self._remember_log_position()
        self.log('info',
        '5. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '6. assert force_debug is "false"')
        self._assert_force_debug("false")
        self.log('info',
        '7. assert effective logging level is DEBUG'
        ' since last log position')
        self._assert_effective_logging_level("DEBUG")
        self.log('info',
        '8. set force_debug to "true"')
        self.turn_on_litp_debug(self.ms_node)
        self.log('info',
        '9. remember last log position')
        self._remember_log_position()
        self.log('info',
        '10. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '11. assert force_debug is "true"')
        self._assert_force_debug("true")
        self.log('info',
        '12. assert effective logging level is DEBUG'
        ' since last log position')
        self._assert_effective_logging_level("DEBUG")
        self.log('info',
        '13. set force_debug to "false"')
        self._set_force_debug("false")
        self.log('info',
        '14. remember last log position')
        self._remember_log_position()
        self.log('info',
        '15. Create messages(noise) in log by running litp commands')
        self._noise_in_log()
        self.log('info',
        '16. assert force_debug is "false"')
        self._assert_force_debug("false")
        self.log('info',
        '17. assert effective logging level is DEBUG'
        ' since last log position')
        self._assert_effective_logging_level("DEBUG")

    @attr('all', 'revert', 'story13217', 'story13217_tc03')
    def test_03_p_restore_model_does_not_affect_logging_item(self):
        """
        @tms_id: litpcds_13217_tc03
        @tms_requirements_id: LITPCDS-227
        @tms_title: Verify that restore_model does not affect "logging" item
        @tms_description: Verify that running the "litp restore_model" command
            does not affect the value of the "force_debug" property of
            "logging" item
        @tms_test_steps:
         @step: Change the value of "force_debug" property
         @result: Property value changed successfully
         @step: Create a new item to make changes to the model
         @result: Item created successfully
         @step: Run the "litp restore_model" command
         @result: Command completed successfully
         @result: The item that was created does not exist in the model
         @result: The "force_debug" property is still set to "true"
        @tms_test_precondition: The debug level is set to "INFO" in
                                 /etc/litp_logging.conf
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Assert that the debug level is set to "INFO" in '
           '{0}'.format(const.LITP_LOGGING_CONF))
        self.download_file_from_node(self.ms_node,
                                     remote_filepath=const.LITP_LOGGING_CONF,
                                     local_filepath=self.logging_local_path,
                                     root_copy=True)

        self.scp.read(self.logging_local_path)
        litptrace = self.scp.get('logger_litptrace', 'level')
        litpevent = self.scp.get('logger_litpevent', 'level')
        self.assertEqual('INFO', litptrace,
            '"litptrace" level set to "INFO" is required to run this test')
        self.assertEqual('INFO', litpevent,
            '"litpevent" level set to "INFO" is required to run this test')

        self.log('info',
        '2. Change the value of force_debug')
        if self.is_litp_debug_enabled(self.ms_node):
            new_force_debug = 'false'
        else:
            new_force_debug = 'true'
        self.execute_cli_update_cmd(self.ms_node,
                                    self.logging_path,
                                    'force_debug={0}'.format(new_force_debug))

        self.log('info',
        '3. Create a new litp item to make changes to the model')
        self.execute_cli_create_cmd(self.ms_node,
                                    self.new_fw_rule_url,
                                    'firewall-rule',
                                    props=self.props_t3)

        self.log('info',
        '4. Run "litp restore_plan" and verify that "force_debug" is not '
           'restored')
        self.execute_cli_restoremodel_cmd(self.ms_node)

        new_items = self.find(self.ms_node,
                              self.new_fw_rule_url,
                              'firewall-rule',
                              assert_not_empty=False)
        self.assertEqual([], new_items)

        self._assert_force_debug(new_force_debug)
