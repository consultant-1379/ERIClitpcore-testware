"""
COPYRIGHT Ericsson 2023
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2023
@author:    Ruth Evans Paul Chambers Karen Flannery
@summary:   TORF-637552 Verify LITP service on MS is using TLS v1.2
                        rather than v1
"""

from litp_generic_test import GenericTest, attr
import test_constants as const


class Story637552(GenericTest):
    """
       As a LITP User I want TLS v1.2 only to be used by LITP
          service on the LMS
    """

    def setUp(self):
        """Setup variables for every test"""
        super(Story637552, self).setUp()
        self.ms1 = self.get_management_node_filename()

    def tearDown(self):
        """Runs for every test"""
        super(Story637552, self).tearDown()

    @attr('all', 'revert', 'story637552', 'story637552_tc03')
    def test_03_p_verify_litp_service_tls_version(self):
        """
        @tms_id:
            torf_637552_tc03
        @tms_requirements_id:
            TORF-637552
        @tms_title:
            Verify LITP Service TLS version
        @tms_description:
            Verify LITP Service TLS version
        @tms_test_steps:
        @step: Run openssl command with TLS1_2
        @result: Success
        @step: Run openssl command with TLS1_1
        @result: Failure
        @step: Run openssl command with TLS1
        @result: Failure
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        check_ssl_cmd = '{0} "" | openssl s_client -connect localhost:9999 -'\
            .format(const.ECHO_PATH)
        success_message = "Secure Renegotiation IS supported"
        success_ssl_handshake_msg = "SSL handshake has read 1341 bytes and " \
                                    "written 415 bytes"
        fail_message = "Secure Renegotiation IS NOT supported"
        fail_ssl_handshake_msg = "SSL handshake has read 0 bytes and " \
                                 "written 0 bytes"
        tls_versions = ("tls1_2", "tls1_1", "tls1")

        for version in tls_versions:
            cmd = check_ssl_cmd + version
            ssl_response = self.run_command(self.ms1, cmd, su_root=True)

            if "TLSv1.2" in str(ssl_response[0]):
                self.assertTrue(success_message in str(ssl_response),
                                "Secure Renegotiation success message "
                                "not in response")
                self.assertTrue(success_ssl_handshake_msg in str(ssl_response),
                                "SSL handshake was not successful")
            else:
                self.assertTrue(fail_message in str(ssl_response),
                                "Secure Renegotiation fail message not "
                                "in response")
                self.assertTrue(fail_ssl_handshake_msg in str(ssl_response),
                                "Fail SSL handshake message was not in "
                                "response")
