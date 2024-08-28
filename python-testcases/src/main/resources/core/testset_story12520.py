'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January 2016, Refactored on April 2019
@author:    Jose Martinez & Jenny Schulze , Yashi Sahu
@summary:   Integration test for story 12520: As a ENM user of LITP I want
            trace disabled on the LITP MS Apache Server so my deployment is
            secure
            Agile: STORY-12520
'''

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const


class Story12520(GenericTest):
    """
        As a ENM user of LITP I want trace disabled on the LITP MS Apache
        Server so my deployment is secure
    """

    def setUp(self):
        """Runs before every test"""
        super(Story12520, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhcmd = RHCmdUtils()
        self.httpd_service = 'httpd'
        self.httpd_conf = const.HTTPD_CFG_FILE

    def tearDown(self):
        """Runs for every test"""
        super(Story12520, self).tearDown()

    def verify_http_file_contents(self, trace_enable="Off"):
        """
        Description:
            Verifies TraceEnable value in  http.conf file
        Kwargs:
            trace_enable(str): Set to Off by default,
                               ON otherwise.
        """
        parameter = "TraceEnable {0}".format(trace_enable)
        cmd_grep = self.rhcmd.get_grep_file_cmd(self.httpd_conf,
                                                parameter)
        stdout = self.run_command(self.ms_node, cmd_grep,
                                  default_asserts=True)[0]
        self.assertTrue(len(stdout) == 1, "No output returned for "
                                          "command '{0}'".format(cmd_grep))
        self.assertEqual(parameter, stdout[0], "Expected value for "
                                               "TraceEnable not found")

    def execute_replace_str_in_file_cmd(self, original_value, new_value,
                                        search_file, default_asserts=True):
        """
        Description
            Replaces all matching strings in a given file on MS
        Args:
            original_value (str): The old string that should be
                                 replaced.
            new_value (str): The new string.
            search_file (str): The filepath
        Kwargs:
            default_asserts(bool): By default set to True, false
                                  otherwise
        """

        cmd_sed = self.rhcmd.get_replace_str_in_file_cmd(original_value,
                                                         new_value,
                                                         search_file,
                                                             sed_args='-i')

        self.run_command(self.ms_node, cmd_sed, su_root=True,
                         default_asserts=default_asserts)

    def verify_curl_trace(self, message, assert_err=False):
        """
        Description:
            Run curl trace command and verify output
        Args:
            message(str) : Message to verify
        Kwarg:
            assert_err(bool) :By default assert_err is False
                              True otherwise.
        """
        cmd_curl = "{0} -v -s -X TRACE http://{1}".format(const.CURL_PATH,
                                                          self.ms_node)
        stderr, rc = self.run_command(self.ms_node, cmd_curl)[1:]

        if assert_err:
            self.assertTrue(self.is_text_in_list(message, stderr),
                            "Command returned errors '{0}'".format(cmd_curl))

        self.assertEqual(0, rc, "No output returned for "
                                "command '{0}'".format(cmd_curl))

    @attr('all', 'revert', 'story12520', 'story12520_tc03')
    def test_03_p_puppet_restores_changes(self):
        """
        @tms_id: Story12520_tc03
        @tms_requirements_id: TORF-12520
        @tms_title: Verify that when users manually edit the option
                   'TraceEnable Off'
                   to be 'TraceEnable On' puppet restores the change
                   and it is effective.
        @tms_description: Verify that when users manually edit the option
                  'TraceEnable Off'
                  to be 'TraceEnable On' puppet restores the change and
                  it is effective.
        @tms_test_steps:
            @step: Verify that "TraceEnable Off"
            @result: Option "TraceEnable Off" is verified
            @step: Run curl trace command and verify output
            @result: Command executed and output is
                      verified.
            @step: Disable puppet
            @result: Puppet is successfully disabled.
            @step: Wait for puppet run to finish
            @result: Puppet run successfully finished.
            @step: Change option to "TraceEnable On"
            @result: Option successfully changed to
                        "TraceEnable On"
            @step: Restart httpd server
            @result: Httpd server successfully restarted.
            @step:  Verify trace is enabled with curl
            @result: Trace is successfully enabled
                     with curl.
            @step: Enable puppet
            @result: Puppet is successfully enabled .
            @step: Run puppet cycle
            @result: Puppet cycle ran successfully.
            @step:  Verify puppet restores value to
                       "TraceEnable Off"
            @result: Puppet successfully restores value
                        to  "TraceEnable Off".
            @step: Set disable 'Trace' and enable
                        puppet in case of error
            @result: 'Trace' successfully disabled
            @step: Enables puppet agent on MS node
            @result: Puppet agent successfully enabled.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        try:
            self.log("info", "1. Verify that \"TraceEnable Off\"")
            self.verify_http_file_contents()

            self.log("info", "2. Run curl trace command and "
                             "verify output")
            self.verify_curl_trace("405 Method Not Allowed")

            self.log("info", "3. Disable puppet")
            self.toggle_puppet(self.ms_node, enable=False)

            self.log("info", "4. Wait for puppet run to finish")
            self.assertTrue(self.wait_for_puppet_idle(self.ms_node),
                           "Puppet run did not complete within"
                           " timeout as puppet not idle")

            self.log("info", "5. Change option to \"TraceEnable On\"")
            self.execute_replace_str_in_file_cmd("TraceEnable Off",
                                                    "TraceEnable On",
                                                    self.httpd_conf)

            self.log("info", "6. restart httpd server")
            self.restart_service(self.ms_node, self.httpd_service,
                                 su_root=True)

            self.log("info", "7. Verify trace is enabled with curl")
            self.verify_curl_trace("200 OK")

            self.log("info", "8. Enable puppet")
            self.toggle_puppet(self.ms_node)

            self.log("info", "9. Run puppet cycle")
            self.wait_full_puppet_run(self.ms_node)

            self.log("info", "10. Verify puppet restores value to "
                             "\"TraceEnable Off\"")
            self.verify_http_file_contents()
            self.verify_curl_trace("405 Method Not Allowed")

        finally:
            self.log("info", "11. Set disable 'Trace' and enable "
                             "puppet in case of error")
            self.execute_replace_str_in_file_cmd("TraceEnable On",
                                                "TraceEnable Off",
                                                self.httpd_conf,
                                                 default_asserts=False)

            self.log("info", "12. Enables puppet agent on MS node")
            self.toggle_puppet(self.ms_node)
