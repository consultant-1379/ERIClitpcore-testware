"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2015
@author:    Lorcan Hamill / Padraic Doyle
@summary:   LITPCDS-8246
            Integration test for LITPCDS-8246. As a LITP user I want to be able
            to get LITP into maintenance mode and have the service return 503.
"""
import sys
import time
import socket
import exceptions
import test_constants
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
from redhat_cmd_utils import RHCmdUtils


class Story8246(GenericTest):
    """
    LITPCDS-8246:
    As a LITP user I want to be able to get LITP into maintenance mode
    and have the service return 503.
    """

    HTTP_STATUS_OK = 200
    HTTP_STATUS_CREATED = 201
    HTTP_STATUS_SERVICE_UNAVAILABLE = 503

    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story8246, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.rest = RestUtils(self.get_node_att(self.ms1, 'ipv4'))
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

        self.maintenance_path = '/litp/maintenance'
        self.enable_maintenance_cmd = (
            self.cli.get_update_cmd(self.maintenance_path, "enabled=true"))

        self.disable_maintenance_cmd = (
            self.cli.get_update_cmd(self.maintenance_path, "enabled=false"))

        self.server_unavailable_error = {
            'error_type': 'ServerUnavailableError',
            'msg': '    LITP is in maintenance mode'
        }

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        self.rest.clean_paths()
        self.run_command(self.ms1,
                         self.disable_maintenance_cmd,
                         add_to_cleanup=False)
        super(Story8246, self).tearDown()

    def _set_maintenance_mode(self, enabled, use_rest=False):
        """
        Description:
            Set maintenance mode using the CLI or directly using the REST
            interface.
        Args:
            enabled (bool): Specify whether maintenance is to be disabled
                           or enabled
            use_rest (bool): Specify whether to use REST or CLI interface
        """
        if use_rest:
            value = 'true' if enabled else 'false'
            data = '{"properties":{"enabled": "' + value + '"}}'
            out, err, rc = self.rest.put(self.maintenance_path,
                                         self.rest.HEADER_JSON,
                                         data)
            self.assertEqual(self.HTTP_STATUS_OK, rc)
            self.assertEqual('', err)
            self.assertNotEqual('', out)
        else:
            if enabled:
                cmd = self.enable_maintenance_cmd
            else:
                cmd = self.disable_maintenance_cmd

            stdout, _, _ = self.run_command(self.ms1,
                                            cmd,
                                            default_asserts=True,
                                            add_to_cleanup=False)
            self.assertEqual([], stdout)

    def _verify_reboot_completes(self):
        """
            Verify that reboot completes.
        """
        self.assertTrue(self._node_rebooted(self.ms1))
        self.assertTrue(self._litp_up())

    def _node_rebooted(self, node):
        """
            Verify that a node  has rebooted.
        """
        node_restarted = False
        max_duration = 1800
        elapsed_sec = 0
        cmd = self.rhcmd.get_cat_cmd('/proc/uptime')
        while elapsed_sec < max_duration:
            try:
                out, err, ret_code = self.run_command(node, cmd,
                                                      su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertNotEqual([], out)
                uptime_seconds = float(out[0].split()[0])
                self.log("info", "{0} is up for {1} seconds"
                         .format(node, str(uptime_seconds)))

                if uptime_seconds < 75.0:
                    self.log("info", "{0} has been rebooted"
                             .format(node))
                    node_restarted = True
                    break
            except (socket.error, exceptions.AssertionError):
                self.log("info", "{0} is not up at the moment"
                         .format(node))
            except:
                self.log("error", "Reboot check. Unexpected Exception: {0}"
                         .format(sys.exc_info()[0]))
                self.disconnect_all_nodes()

            time.sleep(10)
            elapsed_sec += 10

        if not node_restarted:
            self.log("error", "{0} not rebooted in last {1} seconds."
                     .format(node, str(max_duration)))
        return node_restarted

    def _litp_up(self):
        """
            Verify that the MS has a working litp instance.
        """
        litp_up = False
        max_duration = 300
        elapsed_sec = 0

        while elapsed_sec < max_duration:
            try:
                _, err, rc = self.execute_cli_show_cmd(self.ms1,
                                                       "/deployments",
                                                       expect_positive=False)
                self.assertEqual(1, rc)
                missing, extra = self.check_cli_errors(
                                        [self.server_unavailable_error],
                                        err)
                if [] == missing and [] == extra:
                    self.log("info", "Litp is up but in maintenance mode.")
                    litp_up = True
                    break
                else:
                    self.log("info", "Litp is not up.")

            except (socket.error, exceptions.AssertionError):
                self.log("info", "Litp is not up after {0} seconds"
                         .format(elapsed_sec))
            except:
                self.log("error", "Unexpected Exception: {0}"
                         .format(sys.exc_info()[0]))

            time.sleep(10)
            elapsed_sec += 10

        if not litp_up:
            self.log("error", "Litp is not up in last {0} seconds."
                     .format(str(max_duration)))
        return litp_up

    @staticmethod
    def _initialize_new_fw_rule_item(test_id, parent_id):
        """
        Description:
            Set values required to create a new firewall rule item
        Args:
            test_id (str): Test identifier
            parent_id (str): The firewall rule's parent url
        Returns:
            dict, Values for new firewall item
        """
        new_fw_rule = {}
        new_fw_rule['id'] = 'fw_story8246_{0}'.format(test_id)
        new_fw_rule['type'] = 'firewall-rule'
        new_fw_rule['props'] = 'name="555 story8246 {0}"'.format(test_id)
        new_fw_rule['parent_id'] = '{0}/rules'.format(parent_id)
        new_fw_rule['url'] = '{0}/{1}'.format(new_fw_rule['parent_id'],
                                              new_fw_rule['id'])
        new_fw_rule['rest_data'] = \
            '{{"id": "{0}", "type": "{1}", "properties": {{ }}}}'. \
            format(new_fw_rule['id'], new_fw_rule['type'])
        return new_fw_rule

    def _assert_cli_errors(self, expected_errors, actual_errors):
        """
        Description:
            Check CLI command errors and assert they are correct
        Args:
            expected_errors (list): List of dictionaries describing errors
            actual_errors (list): Command errors output
        """
        missing, extra = self.check_cli_errors(expected_errors, actual_errors)
        self.assertEqual([], missing)
        self.assertEqual([], extra)

    def _assert_rest_cmd_results(self, rc, out, err,
                                 expected_rc, expected_err):
        """
        Description:
            Assert REST request results.
        Args:
            rc (int): RSET request return code
            out (str): REST request output
            err (str): REST request error message
            expected_rc (int): Expected return code
            expected_err (str): expected error message
        """
        self.assertEqual(expected_rc, rc)
        self.assertEqual(expected_err, err)
        self.assertNotEqual('', out)

    @attr('all', 'revert', 'story8246', 'story8246_tc01')
    def test_01_p_enabled_gives_503(self):
        """
        @tms_id:
            litpcds_8246_tc01
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            When LITP is in maintenance mode the user cannot configure the
            model
        @tms_description:
            Test that setting the property "enabled" of "maintenance" item to
            "true" will make the litpd service return a 503 for any other
            request.
            Also verify that when property "enabled" is set back to false litp
            service returns to normal operating mode
            This behaviour is tested with both REST and CLI interfaces.
        @tms_test_steps:
        @step: Enable LITP maintenance mode using REST interface
        @result: "maintenance" mode is enabled
        @result: The LITP "maintenance" item can be viewed
        @step: Attempt to view model items and change the model by entering the
               following commands:
               - litp show commnad
               - litp create item command
               - litp remove item command
               - litp load XML command
               - litp restore_model command
               - litp prepare_restore command
        @result: A "ServerUnavailableError" is thrown and a HTTP "503" code
                 is returned
        @step: Disable LITP maintenance mode using REST interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes attempted during maintenance mode found on model
        @step: Make changes to the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @step: Enable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is enabled
        @result: The LITP "maintenance" item can be viewed
        @step: Attempt to view model items and change the model by entering the
               following commands:
               - litp show commnad
               - litp create item command
               - litp remove item command
               - litp load XML command
               - litp restore_model command
               - litp prepare_restore command
        @result: A "ServerUnavailableError" is thrown and a HTTP "503" code
                 is returned
        @step: Disable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes attempted during maintenance mode found on model
        @step: Change the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Identify items to use in this test')
        ms_fw_node_config_url = self.find(self.ms1,
                                         '/ms',
                                         'firewall-node-config')[0]

        new_fw_rule = self._initialize_new_fw_rule_item(
                                        test_id='01',
                                        parent_id=ms_fw_node_config_url)

        existing_fw_rule_url = self.find(self.ms1,
                                         ms_fw_node_config_url,
                                         'firewall-rule')[0]

        fw_rule_xml_file = '/tmp/existing_fw_rule_url.xml'
        self.execute_cli_export_cmd(self.ms1,
                                    existing_fw_rule_url,
                                    filepath=fw_rule_xml_file)

        self.log('info',
        '2. Make sure the maintenance mode is turned off')
        self.assertEqual('false', self.get_props_from_url(
                                                self.ms1,
                                                self.maintenance_path,
                                                filter_prop='enabled'))

        for i, rest in enumerate((True, False), start=3):
            if rest == True:
                self.log('info',
                '{0}.1. Enable maintenance mode using REST'.format(i))
            else:
                self.log('info',
                '{0}.1. Enable maintenance mode using CLI'.format(i))

            self._set_maintenance_mode(enabled=True, use_rest=rest)

            _, stderr, _ = self.execute_cli_show_cmd(self.ms1,
                                                     '/',
                                                     expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info',
            '{0}.2. Assert that content of "maintenance" item can be shown'.
                    format(i))
            _, stderr, _ = self.execute_cli_show_cmd(self.ms1,
                                                     self.maintenance_path,
                                                     expect_positive=True)

            self.log('info',
            '{0}.3. Assert that user cannot view or change model while '
                    '"maintenance" mode is enabled'.format(i))

            self.log('info', 'Assert that LITP items cannot be created')
            _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            out, err, rc = self.rest.post(new_fw_rule['parent_id'],
                                          self.rest.HEADER_JSON,
                                          new_fw_rule['rest_data'])
            self._assert_rest_cmd_results(rc,
                                          out,
                                          err,
                                          self.HTTP_STATUS_SERVICE_UNAVAILABLE,
                                          expected_err='')

            self.log('info', 'Assert that LITP items cannot be removed')
            _, stderr, _ = self.execute_cli_remove_cmd(self.ms1,
                                                       existing_fw_rule_url,
                                                       expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            out, err, rc = self.rest.delete(existing_fw_rule_url)
            self._assert_rest_cmd_results(rc,
                                          out,
                                          err,
                                          self.HTTP_STATUS_SERVICE_UNAVAILABLE,
                                          expected_err='')

            self.log('info', 'Assert that XML files cannot be loaded')
            load_mount_point = '{0}/rules'.format(ms_fw_node_config_url)
            _, stderr, _ = self.execute_cli_load_cmd(self.ms1,
                                                     load_mount_point,
                                                     fw_rule_xml_file,
                                                     args='--merge',
                                                     expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info', 'Assert that LITP model cannot be restored')
            _, stderr, _ = self.execute_cli_restoremodel_cmd(
                                                self.ms1,
                                                expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            data = '{"id": "restore_model", ' \
                   '"properties": {"update_trigger": "updatable" }}'
            out, err, rc = self.rest.put('/litp/restore_model',
                                         self.rest.HEADER_JSON,
                                         data)
            self._assert_rest_cmd_results(rc,
                                          out,
                                          err,
                                          self.HTTP_STATUS_SERVICE_UNAVAILABLE,
                                          expected_err='')

            self.log('info', 'Assert that "prepare_restore" cannot be run')
            # NOTE:
            # We expect the "prepare_restore" command being prevented from
            # running when the maintenance mode is enabled.
            # If this test fails and "prepare_restore" actually executes
            # then the test environment will be left in a corrupted state
            _, stderr, _ = self.execute_cli_prepare_restore_cmd(
                                                self.ms1,
                                                expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            data = \
            '{"id": "prepare-restore", "properties": {"actions": "all" }}'
            out, err, rc = self.rest.put('/litp/prepare-restore',
                                         self.rest.HEADER_JSON,
                                         data)
            self._assert_rest_cmd_results(rc,
                                          out,
                                          err,
                                          self.HTTP_STATUS_SERVICE_UNAVAILABLE,
                                          expected_err='')

            self.log('info',
            '{0}.4. Disable maintenance mode'.format(i))
            self._set_maintenance_mode(enabled=False, use_rest=rest)

            self.log('info',
            '{0}.5. Assert that changes to the model made while in '
                   'maintenance mode did not take place'.format(i))
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

            self.find(self.ms1, existing_fw_rule_url, 'firewall-rule')

            self.log('info',
            '{0}.6. Assert that the model can be changed'.format(i))
            self.execute_cli_create_cmd(self.ms1,
                                        new_fw_rule['url'],
                                        new_fw_rule['type'],
                                        props=new_fw_rule['props'])
            self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])

            self.execute_cli_remove_cmd(self.ms1, new_fw_rule['url'])
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

    @attr('all', 'revert', 'story8246', 'story8246_tc03')
    def test_03_p_property_enabled_is_idempotent(self):
        """
        @tms_id:
            litpcds_8246_tc03
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            Test that maintenance item property "enabled" is idempotent
        @tms_description:
            Verify that running:
                > litp update -p /litp/maintenance -o enabled=false
            in normal operating mode has no effect.
            Also verify that running:
                > litp update -p /litp/maintenance -o enabled=true
            in maintenance mode has no effect.
            This behaviour is tested with both REST and CLI interfaces.
        @tms_test_steps:
        @step: Disable LITP maintenance mode using REST interface
        @result: "maintenance" mode is disabled
        @step: Make changes to the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @step: Disable LITP maintenance mode again using REST interface
        @result: "maintenance" mode is disabled
        @step: Make changes to the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @step: Enable LITP maintenance mode using REST interface
        @result: "maintenance" mode is enabled
        @step: Change the model
        @result: A "ServerUnavailableError" is thrown
        @step: Enable LITP maintenance mode again using REST interface
        @result: "maintenance" mode is enabled
        @step: Change the model
        @result: A "ServerUnavailableError" is thrown
        @step: Disable LITP maintenance mode using REST interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes found on model
        @step: Disable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is disabled
        @step: Make changes to the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @step: Disable LITP maintenance mode again using CLI interface
        @result: "maintenance" mode is disabled
        @step: Make changes to the model by creating and removing a LITP item
        @result: The model has changed accordingly
        @step: Enable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is enabled
        @step: Change the model
        @result: A "ServerUnavailableError" is thrown
        @step: Enable LITP maintenance mode again using CLI interface
        @result: "maintenance" mode is enabled
        @step: Change the model
        @result: A "ServerUnavailableError" is thrown
        @step: Disable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes found on model
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Identify items to use in this test')
        ms_fw_node_config_url = self.find(self.ms1,
                                         '/ms',
                                         'firewall-node-config')[0]

        new_fw_rule = self._initialize_new_fw_rule_item(
                                        test_id='03',
                                        parent_id=ms_fw_node_config_url)

        for i, rest in enumerate((True, False), start=2):
            self.log('info',
            '{0}.1. Turn off maintenance mode using {1}'.
                    format(i, 'REST' if rest else 'CLI'))

            self._set_maintenance_mode(enabled=False, use_rest=rest)

            self.log('info',
            '{0}.2. Assert that the model can be changed'.format(i))
            self.execute_cli_create_cmd(self.ms1,
                                        new_fw_rule['url'],
                                        new_fw_rule['type'],
                                        props=new_fw_rule['props'])
            self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])

            self.execute_cli_remove_cmd(self.ms1, new_fw_rule['url'])
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

            self.log('info',
            '{0}.3. Turn off maintenance mode again using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=False, use_rest=rest)

            self.log('info',
            '{0}.4. Assert that the model can be changed'.format(i))
            self.execute_cli_create_cmd(self.ms1,
                                        new_fw_rule['url'],
                                        new_fw_rule['type'],
                                        props=new_fw_rule['props'])
            self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])

            self.execute_cli_remove_cmd(self.ms1, new_fw_rule['url'])
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

            self.log('info',
            '{0}.5. Turn on maintenance mode using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=True, use_rest=rest)

            self.log('info',
            '{0}.6. Assert that user cannot change model while '
                    '"maintenance" mode is enabled'.format(i))
            _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info',
            '{0}.7. Turn on maintenance mode again using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=True, use_rest=rest)

            self.log('info',
            '{0}.8. Assert that user cannot change model while '
                    '"maintenance" mode is enabled'.format(i))
            _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info',
            '{0}.9. Turn off maintenance mode using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=False, use_rest=rest)

            self.log('info',
            '{0}.10. Assert that changes to the model made while in '
                    'maintenance mode did not take place'.format(i))
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

    @attr('all', 'revert', 'story8246', 'story8246_tc05')
    def test_05_p_maintenance_mode_perstits_litpd_service_restart(self):
        """
        @tms_id:
            litpcds_8246_tc05
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            Maintenance mode persists after a litp service restart.
        @tms_description:
            Maintenance mode persists after a litp service restart.
        @tms_test_steps:
        @step: Enable LITP maintenance mode using REST interface
        @result: "maintenance" mode is enabled
        @step: Attempt to make changes to the model
        @result: A "ServerUnavailableError" is thrown
        @step: Restart litpd service
        @result: litpd service has restarted
        @step: Attempt to make changes to the model
        @result: A "ServerUnavailableError" is thrown
        @step: Disable LITP maintenance mode using REST interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes found on model
        @step: Make changes to the model by creating and removing LITP items
        @result: The model has changed accordingly
        @step: Restart litpd service
        @result: litpd service has restarted
        @step: Make changes to the model by creating and removing LITP items
        @result: The model has changed accordingly
        @step: Enable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is enabled
        @step: Attempt to make changes the model
        @result: A "ServerUnavailableError" is thrown
        @step: Restart litpd service
        @result: litpd service has restarted
        @step: Attempt to make changes to the model
        @result: A "ServerUnavailableError" is thrown
        @step: Disable LITP maintenance mode using CLI interface
        @result: "maintenance" mode is disabled
        @step: Check model items
        @result: No changes found on model
        @step: Make changes to the model by creating and removing LITP items
        @result: The model has changed accordingly
        @step: Restart litpd service
        @result: litpd service has restarted
        @step: Make changes to the model by creating and removing LITP items
        @result: The model has changed accordingly
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Identify items to use in this test')
        ms_fw_node_config_url = self.find(self.ms1,
                                         '/ms',
                                         'firewall-node-config')[0]

        new_fw_rule = self._initialize_new_fw_rule_item(
                                        test_id='05',
                                        parent_id=ms_fw_node_config_url)

        existing_fw_rule_url = self.find(self.ms1,
                                         ms_fw_node_config_url,
                                         'firewall-rule')[0]

        for i, rest in enumerate((True, False), start=2):
            self.log('info',
            '{0}.1. Turn on maintenance mode using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=True, use_rest=rest)

            self.log('info',
            '{0}.2. Assert that user cannot change model while '
                    '"maintenance" mode is enabled'.format(i))
            _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            _, stderr, _ = self.execute_cli_remove_cmd(self.ms1,
                                                       existing_fw_rule_url,
                                                       expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info',
            '{0}.3. Restart "litpd" service'.format(i))
            self.restart_litpd_service(self.ms1, debug_on=False)

            self.log('info',
            '{0}.4. Assert that user cannot change model while '
                    '"maintenance" mode is enabled'.format(i))
            _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
            self._assert_cli_errors([self.server_unavailable_error], stderr)

            self.log('info',
            '{0}.5. Turn off maintenance mode using {1}'.
                    format(i, 'REST' if rest else 'CLI'))
            self._set_maintenance_mode(enabled=False, use_rest=rest)

            self.log('info',
            '{0}.5. Assert that changes to the model made while in '
                   'maintenance mode did not take place'.format(i))
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

            self.find(self.ms1, existing_fw_rule_url, new_fw_rule['type'])

            self.log('info',
            '{0}.6. Assert that the model can be changed'.format(i))
            self.execute_cli_create_cmd(self.ms1,
                                        new_fw_rule['url'],
                                        new_fw_rule['type'],
                                        props=new_fw_rule['props'])
            self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])

            self.execute_cli_remove_cmd(self.ms1, new_fw_rule['url'])
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

            self.log('info',
            '{0}.7. Restart "litpd" service'.format(i))
            self.restart_litpd_service(self.ms1, debug_on=False)

            self.log('info',
            '{0}.6. Assert that the model can be changed'.format(i))
            self.execute_cli_create_cmd(self.ms1,
                                        new_fw_rule['url'],
                                        new_fw_rule['type'],
                                        props=new_fw_rule['props'])
            self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])

            self.execute_cli_remove_cmd(self.ms1, new_fw_rule['url'])
            found = self.find(self.ms1,
                              new_fw_rule['url'],
                              new_fw_rule['type'],
                              assert_not_empty=False)
            self.assertEqual([], found)

    @attr('all', 'revert', 'story8246', 'story8246_tc10')
    def test_10_p_validation_of_the_enabled_property_values(self):
        """
        @tms_id:
            litpcds_8246_tc10
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            test the validation of the "enabled" property values
        @tms_description:
            Test when attempting to set property "enabled" of "maintenance"
            item a "ValidationError" is thrown.
        @tms_test_steps:
        @step: Set the maintenance mode with invalid values
        @result: For each value a "ValidationError" is thrown
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        invalid_values = ['True', 'tru', 'ttrue', 'TRUE',
                         '0', '1', '-', '-1',
                         'ffalse', 'FALSE', 'False', 'falsefalse']

        for value in invalid_values:
            prop = "enabled={0}".format(value)
            _, stderr, _ = self.execute_cli_update_cmd(self.ms1,
                                                       self.maintenance_path,
                                                       prop,
                                                       expect_positive=False)
            expexted_error = {
                'error_type': 'ValidationError',
                'msg': " in property: \"enabled\"    Invalid value '{0}'.".
                         format(value)
            }
            self._assert_cli_errors([expexted_error], stderr)

    @attr('all', 'revert', 'story8246', 'story8246_tc11')
    def test_11_p_the_mmode_is_persisted_after_an_MS_reboot(self):
        """
        @tms_id:
            litpcds_8246_tc11
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            This test will verify that the maintenance mode is persisted after
            an MS reboot.
        @tms_description:
            This test will verify that the maintenance mode is persisted after
            an MS reboot.
        @tms_test_steps:
        @step: Enable maintenance mode
        @result: Maintenance mode is enabled
        @step: Reboot MS
        @result: MS rebooted
        @step: Attempt to make changes to the model
        @result: A "ServerUnavailableError" is thrown
        @result: Item
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        ms_fw_node_config_url = self.find(self.ms1,
                                         '/ms',
                                         'firewall-node-config')[0]

        new_fw_rule = self._initialize_new_fw_rule_item(
                                        test_id='11',
                                        parent_id=ms_fw_node_config_url)

        self.log('info', '1. Enable maintenance mode')
        self._set_maintenance_mode(enabled=True)

        self.log('info', '2. Reboot the MS')
        cmd = "(sleep 1; {0} -r now) &".format(test_constants.SHUTDOWN_PATH)
        self.run_command(self.ms1, cmd, su_root=True)
        self._verify_reboot_completes()

        self.log('info', '3. Verify that maintenance mode is still enabled')
        _, stderr, _ = self.execute_cli_create_cmd(
                                            self.ms1,
                                            new_fw_rule['url'],
                                            new_fw_rule['type'],
                                            props=new_fw_rule['props'],
                                            expect_positive=False)
        self._assert_cli_errors([self.server_unavailable_error], stderr)

        self.log('info', '4. Disable maintenance mode')
        self._set_maintenance_mode(enabled=False)

    @attr('all', 'revert', 'story8246', 'story8246_tc12')
    def test_12_n_mmode_item_cannot_removed_with_remove_cmd(self):
        """
        @tms_id:
            litpcds_8246_tc12
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            The LITP "maintenance" mode model cannot be removed
        @tms_description:
            This test will verify that the maintenance mode model item cannot
            be removed with the litp remove command.
        @tms_test_steps:
        @step: Enable the maintenance mode
        @result: Maintenance mode enabled
        @step: Attempt to remove the maintenance mode item
        @result: A "ServerUnavailableError" is thrown
        @step: Disable maintenance mode
        @result: Maintenance mode is disabled
        @step: Attempt to remove the maintenance mode item
        @result: A "MethodNotAllowedError" is thrown
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self._set_maintenance_mode(enabled=True)
        _, stderr, _ = self.execute_cli_remove_cmd(self.ms1,
                                                self.maintenance_path,
                                                expect_positive=False)
        self._assert_cli_errors([self.server_unavailable_error], stderr)

        self._set_maintenance_mode(enabled=False)
        _, stderr, _ = self.execute_cli_remove_cmd(self.ms1,
                                                self.maintenance_path,
                                                expect_positive=False)

        expected_error = {
            'url': self.maintenance_path,
            'error_type': 'MethodNotAllowedError',
            'msg': '    Remove method on path not allowed'
        }
        self._assert_cli_errors([expected_error], stderr)

    @attr('all', 'revert', 'story8246', 'story8246_tc13')
    def test_13_p_pkg_install_plan_finish_if_mmode_enabled(self):
        """
        @tms_id:
            litpcds_8246_tc13
        @tms_requirements_id:
            LITPCDS-8246
        @tms_title:
            Setting maintenance mode will not stop a running deployment plan
        @tms_description:
            This test will verify that a package install plan finishes if
            maintenance mode is enabled while a plan is running.
        @tms_test_steps:
        @step: Create a new litp item and run the plan
        @result: Plan is running
        @step: Enable maintenance mode
        @result: Maintenance mode is enabled
        @step: Wait for the plan to complete
        @result: The plan completes successfully
        @step: Disable maintenance mode
        @result: Maintenance mode is disabled
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info',
        '1. Create a new firewall rule item and run the plan')
        ms_fw_node_config_url = self.find(self.ms1,
                                         '/ms',
                                         'firewall-node-config')[0]

        new_fw_rule = self._initialize_new_fw_rule_item(
                                        test_id='13',
                                        parent_id=ms_fw_node_config_url)

        self.execute_cli_create_cmd(self.ms1,
                                    new_fw_rule['url'],
                                    new_fw_rule['type'],
                                    props=new_fw_rule['props'])

        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1)

        self.log('info',
        '2. Enable maintenance mode')
        _, stderr, rc = self.run_command(self.ms1, self.enable_maintenance_cmd)
        enabled = self.get_props_from_url(self.ms1,
                                          self.maintenance_path,
                                          filter_prop='enabled')

        self.log('info',
        '3. Wait for the plan to complete')
        self.wait_for_log_msg(self.ms1,
                              "Plan execution successful",
                              return_log_msgs=True,
                              timeout_sec=300)

        self.log('info',
        '4. Disable maintenance mode')
        self._set_maintenance_mode(enabled=False)

        self.log('info',
        '5. Assert that plan completed successfully and that maintenance '
           'mode was enabled while plan was running')
        self.assertEqual([], stderr)
        self.assertEqual('true', enabled)
        self.assertEqual(0, rc)
        self.assertEqual(0, self.get_current_plan_state(self.ms1))
        self.find(self.ms1, new_fw_rule['url'], new_fw_rule['type'])
