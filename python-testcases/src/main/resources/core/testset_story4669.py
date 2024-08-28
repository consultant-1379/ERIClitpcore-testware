"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2014
@author:    Maria Varley
@summary:   Integration test for rest API for DEBUG operations
            Agile: STORY LITPCDS-4669
"""

import os

from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
from litp_cli_utils import CLIUtils
from json_utils import JSONUtils
import test_constants as const
from ConfigParser import SafeConfigParser


class Story4669(GenericTest):
    """
    As an application designer, I want a uri for true on the litpd service,
    so that I only have one mount point in my web service that conforms to
    REST specifications
    """

    def setUp(self):
        """
        Description:
            Runs before every single test.
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story4669, self).setUp()
        self.ms1 = self.get_management_node_filenames()[0]
        self.rest = RestUtils(self.get_node_att(self.ms1, 'ipv4'))
        self.cli = CLIUtils()
        self.json = JSONUtils()
        self.path = "/tmp"
        self.logging_url = "/litp/logging"
        self.litp_path = "/litp"

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Ensure true is turned on after test run
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        # 1. Ensure true is turned on after test run
        cmd = self.cli.get_update_cmd(self.logging_url, "force_debug=true")
        self.run_command(self.ms1, cmd)

        # 2. Call superclass teardown
        super(Story4669, self).tearDown()

    def copy_xml_file_to_management_node(self, filename):
        """Copies xml file to be loaded onto the MS"""

        # Locate given XML file in test file directory and copy it to the
        # management server to be used by the test
        self.assertTrue(
            self.copy_file_to(
                self.ms1,
                os.path.join(
                    os.path.abspath(
                        os.path.join(os.path.dirname(__file__), 'xml_files'),
                    ),
                    filename
                ),
                self.path
            )
        )

    def _get_debug_level_from_config_file(self, force_download=False):
        """
        Description:
            Parse "/etc/litp_logging.conf" file to get debug log level
            configuration
        Args:
            force_download (bool): Specify if the file needs to be downloaded
                                   even if it exists locally already
        Return:
            str, The value of the logger_litptrace level
        """
        local_litp_logging_conf = '/tmp/{0}'. \
            format(os.path.basename(const.LITP_LOGGING_CONF))
        if not os.path.exists(local_litp_logging_conf) or force_download:
            self.download_file_from_node(
                                    self.ms1,
                                    remote_filepath=const.LITP_LOGGING_CONF,
                                    local_filepath=local_litp_logging_conf,
                                    root_copy=True)

        scp = SafeConfigParser()
        scp.read(local_litp_logging_conf)
        return scp.get('logger_litptrace', 'level').strip('"')

    @attr('all', 'revert', 'story4669', 'story4669_tc01')
    def test_01_p_enable_true_rest(self):
        """
        @tms_id: litpcds_4669_tc01
        @tms_requirements_id: LITPCDS-4669
        @tms_title: Tests that force_debug can be enabled (set to true)
            from the REST interface.
        @tms_description: Tests that switching litp debug level via REST
            interface is possible, INFO or DEBUG levels can be enabled,
            message on selected logging level is posted in logs
        @tms_test_steps:
         @step: Check that '/litp' path exists on model by running
           REST command 'CURL GET'
         @result: '/litp' path exists
         @step: Check that '/litp/logging' path exists on model by running
           REST command 'CURL GET'
         @result: '/litp/logging' path exists
         @step: Set force_debug to false through the rest interface
         @result: command executed successfully and response is HAL Compliant
         @result: message logged INFO: Updated item /litp/logging.
                        Updated properties: 'force_debug': false
         @step: Set force_debug to true through the REST interface
         @result: command executed successfully and response is HAL Compliant
         @result: message logged INFO: Updated item /litp/logging.
                        Updated properties: 'force_debug': true
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'Check that \'/litp\' path exists on model '
                         'by running REST command \'CURL GET\'')

        stdout, stderr, status = self.rest.get(self.litp_path)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=True, has_props=False
            )
        )

        self.log('info', 'Check that \'/litp/logging\' path exists '
                         'on model by running REST command \'CURL GET\'')
        stdout, stderr, status = self.rest.get(self.logging_url)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'Get the current log file position before '
                         'force_debug is set')
        start_log_pos1 = self.get_file_len(
            self.ms1, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', 'Set force_debug to false through REST')
        message_data = "{\"properties\": {\"force_debug\": \"false\"} }"
        stdout, stderr, rc, = self.rest.put(
            self.logging_url, self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command executed successfully')
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True))

        self.log('info', 'Check expected INFO message was logged '
                         'during the test')
        false_val_log = ["INFO: Updated item /litp/logging. "
                        "Updated properties: 'force_debug': false"]
        self.assertTrue(self.wait_for_log_msg(self.ms1, false_val_log,
                        log_len=start_log_pos1))

        self.log('info', 'Get the current log file position before '
                         'force_debug is set')
        start_log_pos2 = self.get_file_len(
            self.ms1, const.GEN_SYSTEM_LOG_PATH)

        self.log('info', ' Set force_debug to true through '
                         'the rest interface')
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, rc = self.rest.put(
            self.logging_url, self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command executed successfully')
        self.assertEqual("", stderr)
        self.assertEqual(200, rc)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True))

        self.log('info', 'Check expected INFO message was logged '
                         'during the test')
        true_val_log = ["INFO: Updated item /litp/logging. "
                        "Updated properties: 'force_debug': true"]
        self.assertTrue(self.wait_for_log_msg(self.ms1, true_val_log,
                        log_len=start_log_pos2))

    @attr('all', 'revert', 'story4669', 'story4669_tc02')
    def test_02_p_enable_true_cli(self):
        """
        @tms_id: litpcds_4669_tc02
        @tms_requirements_id: LITPCDS-4669
        @tms_title: Setting logging level using deprecated CLI command options
        @tms_description: Tests that on updating force_debug from the CLI
            interface with deprecated 'normal' and 'override' parameters
            a message is displayed indicating that command is deprecated.
            Logging level applied.
        @tms_test_steps:
         @step: Disable litp "force_debug" using the deprecated "-o normal"
                CLI command option
         @result: User informed that "This command is deprecated."
         @result: The "force_debug" property of logging item is set to "false".
         @step: Enable litp "force_debug" using the deprecated "-o override"
                CLI command option.
         @result: User informed that "This command is deprecated"
         @result: The "force_debug" property of logging item is set to "true"
        @tms_test_precondition:
            "level" of litptrace_level" in litp_logging.conf file is set to
            "INFO"
        @tms_execution_type: Automated
        """
        litptrace_level = self._get_debug_level_from_config_file(
                                                    force_download=True)
        if litptrace_level != 'INFO':
            self.log('info', 'logging level found: {0}, '
                             'changing to INFO'.format(litptrace_level))
            sed_cmd = '/bin/sed -i \'/logger_litptrace/!b;n;clevel=INFO\''\
                      ' {0}'.format(const.LITP_LOGGING_CONF)

            self.run_command(self.ms1,
                             sed_cmd,
                             default_asserts=True,
                             su_root=True)
            self.restart_litpd_service(self.ms1)

        # Making sure the force_debug is enabled
        self.execute_cli_update_cmd(self.ms1,
                                    self.logging_url,
                                    props='force_debug=true')

        self.log('info', '1. Disable litp force_debug using the '
                         'deprecated "-o normal" CLI command option.')
        cmd = "litp debug -o normal"
        stdout, stderr, _ = self.run_command(self.ms1, cmd,
                                             add_to_cleanup=False,
                                             default_asserts=True)
        expected_cli_msg = "This command is deprecated. " \
            "Use 'litp update -p /litp/logging -o force_debug=false' instead"
        self.assertTrue(self.is_text_in_list(expected_cli_msg, stdout),
                        'Message "{0}" not found in \n"{1}"'.
                        format(expected_cli_msg, '\n'.join(stderr)))

        # Ensure that the "force_debug" property of
        # the logging item is updated to "false"
        self.assertEqual('false', self.get_props_from_url(
                                            self.ms1,
                                            self.logging_url,
                                            filter_prop='force_debug'))

        # Disable the "force_debug" property for the next test
        self.execute_cli_update_cmd(self.ms1,
                                    self.logging_url,
                                    props='force_debug=false')

        self.log('info', '2. Enable litp force_debug using the '
                         'deprecated "-o override" CLI command option.')
        cmd = "litp debug -o override"
        stdout, stderr, _ = self.run_command(self.ms1,
                                              cmd,
                                              add_to_cleanup=False,
                                              default_asserts=True)

        expected_cli_msg = "This command is deprecated. " \
            "Use 'litp update -p /litp/logging -o force_debug=true' instead"
        self.assertTrue(self.is_text_in_list(expected_cli_msg, stdout),
                        'Message "{0}" not found in \n"{1}"'.
                        format(expected_cli_msg, '\n'.join(stderr)))

        self.assertEqual('true', self.get_props_from_url(
                                            self.ms1,
                                            self.logging_url,
                                            filter_prop='force_debug'))

    @attr('all', 'revert', 'story4669', 'story4669_tc03')
    def test_03_p_update_true_cli(self):
        """
        @tms_id: litpcds_4669_tc03
        @tms_requirements_id: LITPCDS-4669
        @tms_title: Tests that force_debug can be enabled via CLI interface.
        @tms_description: Tests that updating force_debug from the CLI
            interface is possible with the litp update command.
        @tms_test_steps:
         @step: Check /litp path is present
         @result: /litp present
         @step: Check /item-types
         @result: 'logging' present in /item-types
         @step: Check /property-types
         @result: 'force-debug' not present in /property-types
            as it is boolean, not a type
         @step: Check type of /litp path
         @result: Type of /litp is litp-service-base
         @step: Execute: litp show -p /litp/logging
         @result: /litp/logging shows the current value of
            litp service log level
         @step: Run "litp update -p /litp/logging -o force_debug=false"
         @result: The "force_debug" property of logging item is set to "false".
         @step: Run "litp update -p /litp/logging -o force_debug=true"
         @result: The "force_debug" property of logging item is set to "true".
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'Execute: litp show -p /')
        stdout, _, _ = self.execute_cli_show_cmd(self.ms1, "/")

        self.log('info', 'Ensure the /litp path is present')
        self.assertTrue(self.is_text_in_list(self.litp_path, stdout))

        self.log('info', 'Check item-type contains "logging" type')
        stdout, _, _ = self.execute_cli_show_cmd(self.ms1,
                                                 "/item-types")
        self.assertTrue(self.is_text_in_list("logging", stdout))

        self.log('info', 'Check property-type does not contain force_debug '
                         'as it is not a property-type but boolean.')
        stdout, _, _ = self.execute_cli_show_cmd(
            self.ms1, "/property-types")
        self.assertFalse(self.is_text_in_list("force_debug", stdout))

        self.log('info', 'Execute: litp show -p /litp')
        stdout, _, _ = self.execute_cli_show_cmd(
            self.ms1, self.litp_path)
        self.log('info', 'Check type of /litp is "litp-service-base".')
        self.assertTrue(self.is_text_in_list("litp-service-base", stdout))

        self.log('info', 'Execute: litp show -p /litp/logging')
        stdout, _, _ = self.execute_cli_show_cmd(self.ms1, self.logging_url)
        self.assertTrue(self.is_text_in_list(
            "force_debug: true", stdout), "force_debug property missing")
        self.assertTrue(self.is_text_in_list(self.logging_url, stdout))

        self.log('info', 'Ensure the current value of litp service log level'
                         ' is returned.')
        show_property_result, _, _ = self.execute_cli_show_cmd(
            self.ms1, self.logging_url, "-o force_debug")
        show_property_result = "".join(show_property_result)
        self.assertEqual(show_property_result, "true")

        self.log('info', 'Execute: '
                         'litp update -p /litp/logging -o force_debug=false')
        self.execute_cli_update_cmd(
            self.ms1, self.logging_url, "force_debug=false")

        self.assertEqual('false', self.get_props_from_url(
            self.ms1,
            self.logging_url,
            filter_prop='force_debug'))

        self.log('info', 'Execute: '
                         'litp update -p /litp/logging -o force_debug=true')
        self.execute_cli_update_cmd(
            self.ms1, self.logging_url, "force_debug=true")

        self.assertEqual('true', self.get_props_from_url(
            self.ms1,
            self.logging_url,
            filter_prop='force_debug'))

    @attr('all', 'revert', 'story4669', 'story4669_tc04')
    def test_04_p_true_export_xml(self):
        """
        @tms_id: litpcds_4669_tc04
        @tms_requirements_id: LITPCDS-4669
        @tms_title: test that /litp is not included in the XML export
        @tms_description: Test checks that neither the /litp nor /litp/logging
            path can be exported to xml using the litp export command
        @tms_test_steps:
         @step: Export root as xml
         @result: /litp/logging not present in exported xml
         @step: Attempt to export /litp/logging
         @result: MethodNotAllowedError posted
         @step: Attempt to export /litp
         @result: MethodNotAllowedError posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        filepath1 = os.path.join(self.path, 'xml_test04a_root.xml')
        filepath2 = os.path.join(self.path, 'xml_test04b_root.xml')

        self.log('info', 'Export root as xml')
        self.execute_cli_export_cmd(
            self.ms1, "/", filepath1)

        self.log('info', 'Check that the "logging" element is not present '
                         'in the exported file')
        stdout, stderr, rc = self.run_command(
            self.ms1, self.rhc.get_grep_file_cmd(
                filepath1, ['<litp:logging ']))
        self.assertEqual(1, rc)
        self.assertEqual([], stderr)
        self.assertEqual([], stdout)

        self.log('info', 'Attempt to export the path, "/litp/logging"')
        _, stderr, _ = self.execute_cli_export_cmd(
            self.ms1, self.logging_url, filepath2, expect_positive=False)

        self.log('info', 'check that MethodNotAllowedError posted')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr), \
            "did not get expected error message:MethodNotAllowedError")

        self.log('info', 'Attempt to export the path, "/litp"')
        _, stderr, _ = self.execute_cli_export_cmd(
            self.ms1, self.litp_path, filepath2, expect_positive=False)

        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr), \
            "did not get expected error message:MethodNotAllowedError")

    @attr('all', 'revert', 'story4669', 'story4669_tc05')
    def test_05_n_true_load_xml(self):
        """
        @tms_id: litpcds_4669_tc05
        @tms_requirements_id: LITPCDS-4669
        @tms_title: test that an error is raised when a user attempts to load
            XML containing /litp
        @tms_description: Test checks that an error message is posted on
            attempt to load an xml file containing /litp path
        @tms_test_steps:
         @step: Attempt to load XML file with /litp path
            using the "--replace" option
         @result: InvalidXMLError is posted
         @step: Attempt to load XML file with /litp path
            using the "--merge" option
         @result: InvalidXmlError is posted
         @step: Attempt to load XML file with /litp/logging path
         @result: InvalidXmlError is posted
        @tms_test_precondition: xml files containing /litp, /litp/logging
            paths copied to ms
        @tms_execution_type: Automated
        """
        self.log('info', 'Copy xml file containing /litp onto the MS')
        self.copy_xml_file_to_management_node('xml_test05a_root.xml')

        filepath = os.path.join(self.path, "xml_test05a_root.xml")

        self.log('info', 'Attempt to load the xml file using the '
                         '"--replace" option')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.ms1, "/",
            filepath, "--replace", expect_positive=False)

        self.log('info', 'Check for expected error message:InvalidXMLError')
        invalidxmlerr = ('InvalidXMLError    This element is not expected.')
        self.assertTrue(self.is_text_in_list(invalidxmlerr, stderr),
                        "did not get expected Error")

        self.log('info', 'Attempt to load the xml file using the '
                         '"--merge" option')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.ms1, "/",
            filepath, "--merge", expect_positive=False)

        self.log('info', 'Check for expected error message:InvalidXMLError')
        self.assertTrue(self.is_text_in_list(
          invalidxmlerr, stderr),
          "did not get expected Error")

        self.log('info', 'Copy a second xml file containing '
                         '/litp/logging onto the MS')
        self.copy_xml_file_to_management_node('xml_test05b_load_logging.xml')

        self.log('info', 'Attempt to load the XML file')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.ms1, self.logging_url,
            filepath, expect_positive=False)

        self.log('info', 'Check for expected error '
                         'message:MethodNotAllowedError')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr), \
            "did not get expected error message:MethodNotAllowedError")

    @attr('all', 'revert', 'story4669', 'story4669_tc06')
    def test_06_n_rest_true_validation(self):
        """
        @tms_id: litpcds_4669_tc06
        @tms_requirements_id: LITPCDS-4669
        @tms_title: Validation errors for unsupported operations on debug_level
            via REST interface
        @tms_description: Test that correct validation errors are returned
            when incorrect scenarios are executed for '/litp',
            '/litp/logging' paths and force_debug through rest interface
        @tms_test_steps:
         @step: Execute the put command with incorrect force_debug property
            value
         @result: ValidationError returned
         @step: Execute the put command with missing force_debug property value
         @result: InvalidRequestError returned
         @step: Execute the put command on /litp path
         @result: MethodNotAllowedError returned
         @step: Execute the put command with invalid path i.e/litp/logging/test
         @result: MethodNotAllowedError returned
         @step: Execute a curl post command on /litp/logging
         @result: MethodNotAllowedError returned
         @step: Execute a curl delete command on /litp/logging
         @result: MethodNotAllowedError returned
         @step: Execute a curl post command on /litp
         @result: MethodNotAllowedError returned
         @step: Execute a curl delete command on /litp
         @result: MethodNotAllowedError returned
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', 'Execute the put command with incorrect force_debug '
                         'property value')
        message_data = "{\"properties\": {\"force_debug\": \"incorrect\"} }"
        stdout, stderr, rc, = self.rest.put(
            "/litp/logging", self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'ValidationError')
        self.assertEqual(422, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Invalid value 'incorrect'.",
            litp_element['messages'][0]['message'])
        self.assertEquals("ValidationError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute the put command with missing force_debug '
                         'property value')
        message_data = "{\"properties\": {\"force_debug\":} }"
        stdout, stderr, rc, = self.rest.put(
            "/litp/logging", self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'InvalidRequestError')
        self.assertEqual(422, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals(
            'Payload is not valid JSON: {"properties": {"force_debug":} }',
            litp_element['messages'][0]['message'])
        self.assertEquals("InvalidRequestError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute the put command on /litp path')
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, rc, = self.rest.put(
            self.litp_path, self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Update method on path not allowed",
            litp_element['messages'][0]['message'])
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute the put command with invalid path, i.e '
                         '/litp/logging/test')
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, rc = self.rest.put(
            self.logging_url + "/test", self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Update method on path not allowed",
            litp_element['messages'][0]['message'])
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute a curl post command on /litp/logging')
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, rc, = self.rest.post(
            self.logging_url, self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Create method on path not allowed",
            litp_element['messages'][0]['message'])
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute a curl delete command on /litp/logging')
        stdout, stderr, rc, = self.rest.delete(self.logging_url)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual('', stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Remove method on path not allowed",
            litp_element['messages'][0]['message'])
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute a curl post command on /litp')
        message_data = "{\"properties\": {\"force_debug\": \"true\"} }"
        stdout, stderr, rc, = self.rest.post(
            self.litp_path, self.rest.HEADER_JSON,
            data=message_data)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual("", stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Create method on path not allowed",
            litp_element['messages'][0]['message'])
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

        self.log('info', 'Execute a curl delete command on /litp')
        stdout, stderr, rc, = self.rest.delete(self.litp_path)

        self.log('info', 'Assert command returned expected error: '
                         'MethodNotAllowedError')
        self.assertEqual(405, rc)
        self.assertEqual('', stderr)
        litp_element, errorlist = self.rest.get_json_response(stdout)
        self.assertEquals("Remove method on path not allowed",
            litp_element['messages'][0]['message'])
        self.assertEquals("MethodNotAllowedError",
            litp_element['messages'][0]['type'])
        self.assertEquals([], errorlist)

    @attr('all', 'revert', 'story4669', 'story4669_tc07')
    def test_07_n_cli_true_validation(self):
        """
        @tms_id: litpcds_4669_tc07
        @tms_requirements_id: LITPCDS-4669
        @tms_title: Validation errors for unsupported operations on debug_level
            via CLI interface
        @tms_description: Test that correct validation errors are returned when
            incorrect scenarios are executed for '/litp', '/litp/logging' paths
            and force_debug through cli interface
        @tms_test_steps:
         @step: Attempt a litp create command on path /litp/logging
         @result: MethodNotAllowedError is returned
         @step: Attempt a litp remove command on path /litp/logging
         @result: MethodNotAllowedError is returned
         @step: Attempt a litp create command on path /litp
         @result: MethodNotAllowedError is returned
         @step: Attempt a litp remove command on path /litp
         @result: MethodNotAllowedError is returned
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', 'Attempt a litp create command on path /litp/logging')
        _, stderr, _ = self.execute_cli_create_cmd(
            self.ms1, self.logging_url, "logging",
            "force_debug=false", expect_positive=False)

        self.log('info', 'Assert Expected Error: MethodNotAllowedError '
                         'is returned')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr),
            "did not get expected error message:MethodNotAllowedError")

        self.log('info', 'Attempt a litp remove command on path /litp/logging')
        _, stderr, _ = self.execute_cli_remove_cmd(
            self.ms1, self.logging_url,
            expect_positive=False)

        self.log('info', 'Assert Expected Error: MethodNotAllowedError '
                         'is returned')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr),
            "did not get expected error message:MethodNotAllowedError")

        self.log('info', 'Attempt a litp create command on path /litp')
        _, stderr, _ = self.execute_cli_create_cmd(
            self.ms1, self.litp_path, "litp-service",
            "logging", expect_positive=False)

        self.log('info', 'Assert Expected Error: MethodNotAllowedError '
                         'is returned')
        self.assertTrue(self.is_text_in_list(
            "litp create: error:", stderr),
            "did not get expected litp create error message")

        self.log('info', 'Attempt a litp remove command on path /litp')
        _, stderr, _ = self.execute_cli_remove_cmd(
            self.ms1, self.litp_path,
            expect_positive=False)

        self.log('info', 'Assert Expected Error: MethodNotAllowedError '
                         'is returned')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr),
            "did not get expected error message:MethodNotAllowedError")
