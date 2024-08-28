"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2018
@author:    karen.flannery@ammeon.com
@summary:   TORF-299751
            As a LITP User, I want to remove Apache and CherryPy server
            signatures to improve security
"""


from litp_generic_test import GenericTest, attr
from test_constants import HTTPD_CFG_FILE, CURL_PATH
import os


class Story299751(GenericTest):
    """
        Asserts that all Apache version information and CherryPy signatures are
        removed from curl http(s) responses (except for Apache name in http
        header response)
    """

    def setUp(self):
        """
            Runs before every single test
        """

        super(Story299751, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip = self.get_node_att(self.ms_node, 'ipv4')
        self.append_file = "story299751_httpd_snippet_to_append_to_conf_file"
        self.apache_signature = "Apache/2.2.15 (Red Hat)"
        self.apache_name = "Apache"
        self.cherrypy_signature = "CherryPy"
        self.error_msg_404 = "404 Not Found"
        self.error_msg_403 = "403 Forbidden"
        self.error_msg_not_present = 'ERROR: "{0}" was not present'
        self.error_msg_present = 'ERROR: "{0}" was present'

    def tearDown(self):
        """
            Runs after every single test
        """
        super(Story299751, self).tearDown()
        self.log("info", "Restart httpd service to pick up config file "
                         "update")
        self.restart_service(self.ms_node, "httpd")

    def check_response_content(self, response, string_to_check):
        """
            Checks for a string in response

            Args:
                response (list): http(s) response
                string_to_check (str): string to check for in response

            Returns:
                 bool. True if string is found in response. Otherwise False
        """
        for line in response:
            if string_to_check in line:
                self.log("info", 'Line ===> {0}: contains "{1}"'
                         .format(line, string_to_check))
                return True
        self.log("info", '"{0}" was not found'.format(string_to_check))
        return False

    def send_curl_request_and_verify_response(self, cmd, error_msg, signature,
                                              check_present=True):
        """
            Sends http(s) request and verifies response

            Args:
                cmd (str): curl command
                error_msg (str): type of error response i.e. 403/404
                signature (str): string to check response for i.e. Apache/
                                 CherryPy
                check_present (bool): whether to check if present or not
                                      present. Default is True.
        """
        http_response, _, _ = self.run_command(self.ms_node, cmd.format(
            CURL_PATH, self.ms_ip))
        self.assertTrue(self.check_response_content(http_response, error_msg),
                        self.error_msg_not_present)

        if not check_present:
            self.assertFalse(self.check_response_content(http_response,
                                                         signature),
                             self.error_msg_present)
        else:
            self.assertTrue(self.check_response_content(http_response,
                                                        signature),
                            self.error_msg_not_present)

    def send_multiple_requests(self, dictionary, error_msg):
        """
            Sends multiple curl requests from dictionary

            Args:
                dictionary (dict): dictionary of curl cmds/
                                     apache_signature/name
                error_msg (str): type of error response i.e. 403/404
        """
        for cmd, sig in dictionary.iteritems():
            if sig == self.apache_signature:
                check = False
            else:
                check = True

            self.send_curl_request_and_verify_response(cmd, error_msg, sig,
                                                       check)

    @attr('all', 'revert', 'story299751', 'story299751_tc01')
    def test_01_p_verify_apache_signature_is_not_http_403_response(self):
        """
            @tms_id: torf_299751_tc01
            @tms_requirements_id: TORF-299751
            @tms_title: Verify Apache version information is not in http(s) 403
                        response
            @tms_description: When user sends a http/https request to generate
                 a 403 forbidden error no additional Apache information is seen
                 except for the name Apache in header
            @tms_test_steps:
             @step: Back up the default httpd config file
             @result: httpd config file is backed up
             @step: Append contents of story299751_httpd_snippet_to_append_to_
                    conf_file to httpd config file
             @result: Contents are appended
             @step: Restart httpd service to pick up config change
             @result: httpd service is restarted with config change picked up
             @step: Send http/https request to generate 403 forbidden error
                 from curl command
             @result: http/https response contains no Apache information except
                 for the name Apache in header
            @tms_test_precondition: Apache web server running on the MS in a
                LITP deployment.
            @tms_execution_type: Automated
        """

        self.log("info", '#1. Update "{0}" to allow 403 error'.format(
            HTTPD_CFG_FILE))
        self.backup_file(self.ms_node, HTTPD_CFG_FILE,
                         restore_after_plan=True)

        self.copy_file_to(self.ms_node, os.path.join(os.path.dirname
                                                     (os.path.realpath(__file__
                                                                       )),
                                                     self.append_file),
                          "/tmp/{0}".format(self.append_file))

        self.append_files(self.ms_node, HTTPD_CFG_FILE,
                          "/tmp/{0}".format(self.append_file))

        self.log("info", "#2. Restart httpd service to pick up config file "
                         "update")
        self.restart_service(self.ms_node, "httpd")

        request_data = {"{0} http://{1}/test2": self.apache_signature,
                        "{0} -Is http://{1}/test2": self.apache_name}

        self.log("info", "#3. Send http(s) requests to generate 403 error by "
                         "curl and verify responses do not contain Apache "
                         "version information but header response contains "
                         "Apache name")
        self.send_multiple_requests(request_data, self.error_msg_403)

    @attr('all', 'revert', 'story299751', 'story299751_tc02')
    def test_02_p_verify_apache_signature_is_not_http_404_response(self):
        """
            @tms_id: torf_299751_tc02
            @tms_requirements_id: TORF-299751
            @tms_title: Verify Apache signature is not in http(s) 404 response
            @tms_description: When user sends a http/https request to generate
                 a "404 Not Found" error no additional Apache information is
                 seen except for the name Apache in header
            @tms_test_steps:
             @step: Send http/https request to generate "404 Not Found" error
                 from curl command
             @result: http/https response contains no Apache information except
                 for the name Apache in header
            @tms_test_precondition: Apache web server running on the MS in a
                LITP deployment.
            @tms_execution_type: Automated
        """

        request_data = {"{0} http://{1}/xyz": self.apache_signature,
                        "{0} -Is http://{1}/xyz": self.apache_name}

        self.log("info", "#1. Send http(s) requests to generate 404 error by "
                         "curl and verify responses do not contain Apache "
                         "version information but header response contains "
                         "Apache name")
        self.send_multiple_requests(request_data, self.error_msg_404)

    @attr('all', 'revert', 'story299751', 'story299751_tc03')
    def test_03_p_verify_CherryPy_signature_is_not_http_404_response(self):
        """
            @tms_id: torf_299751_tc03
            @tms_requirements_id: TORF-299751
            @tms_title: Verify CherryPy signature in not in https 404 response
            @tms_description: When user sends a https request to generate
                a "404 Not Found" error no information relating to CherryPy
                is seen
            @tms_test_steps:
             @step: Send https request to generate "404 Not Found" error from
                 curl command
             @result: https response contains no CherryPy information
            @tms_test_precondition: CherryPy web server running on the MS in a
                LITP deployment
            @tms_execution_type: Automated
        """

        self.log("info", "#1. Send https request by curl and verify response "
                         "does not contain CherryPy signature")
        self.send_curl_request_and_verify_response("{0} -k "
                                                   "https://{1}:9999/xyz",
                                                   self.error_msg_404,
                                                   self.cherrypy_signature,
                                                   False)
