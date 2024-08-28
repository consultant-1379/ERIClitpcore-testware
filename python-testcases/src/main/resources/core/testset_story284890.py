"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2018
@author:    Padraic Doyle
@summary:   TORF-284890
            As a LITP User I want the directory listing on the LMS to be
            removed to improve security. Directory listings are the ability of
            a user to view the contents of a directory.
"""

from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
import re


class Story284890(GenericTest):
    """
        As a LITP User I want the directory listing on the LMS to be removed to
        improve security.
    """

    def setUp(self):
        """ Runs before every single test. """
        super(Story284890, self).setUp()
        self.redhatutils = RHCmdUtils()
        self.ms_node = self.get_management_node_filename()

    def tearDown(self):
        """ Runs after every single test. """
        super(Story284890, self).tearDown()

    def check_indexes_in_apache_config_file(self):
        """
        Description:
            Check that in the Apache config file has the directory listings
            option switched off with the '-Indexes' option.
            Asserts that the directory contents are as expected.
        """
        self.log("info", "Retrieve the Apache config file.")
        http_conf_list = self.get_file_contents(
            self.ms_node, const.HTTPD_CFG_FILE, su_root=True)

        self.log("info", "Convert the returned list to a single string.")
        http_conf = ''.join(http_conf_list)

        self.log("info", "Define and compile a regexp to match the expected "
                 "configuration.")
        regular_expression = \
            '.*?(<Directory "{0}").*?(-Indexes).*?(<\\/Directory>)'\
            .format(const.PARENT_PKG_REPO_DIR[:-1])
        reg = re.compile(regular_expression, re.DOTALL)

        self.log("info", "Check the file matches the regular expression.")
        match_obj = reg.search(http_conf)

        self.log("info", "Assert a match object was created, match successful")
        self.assertTrue(
            match_obj,
            "String didn't match regexp {0}".format(regular_expression))
        start_tag = match_obj.group(1)
        index_option = match_obj.group(2)
        end_tag = match_obj.group(3)
        self.log(
            "info", "Option '{0}' found between tags {1} and {2}".format(
                index_option, start_tag, end_tag))

    @attr('all', 'revert', 'story284890', 'story284890_tc02')
    def test_02_p_directory_listings_config_enforced(self):
        """
            @tms_id: torf_284890_tc02
            @tms_requirements_id: TORF-284890
            @tms_title:  The directory listings configuration is enforced by
                puppet.
            @tms_description:
                Verify that the directory listings configuration is enforced
                by puppet by removing the '-Indexes' option from the Apache
                config file on the MS (/etc/httpd/conf/httpd.conf) and
                checking that puppet restores it.
            @tms_test_steps:
                @step:  Remove the '-Indexes' option from the Apache config
                    file on the MS: /etc/httpd/conf/httpd.conf
                @result:  The '-Indexes' option is removed from the
                    'directories' sections of the config file.
                @step:  Wait for a puppet run to complete.
                @result:  The '-Indexes' option is reset in the 'directories'
                    sections of the config file.
            @tms_test_precondition: NA
            @tms_execution_type: Automated
        """
        self.log(
            "info", "1. Remove the '-Indexes' option from the Apache "
            "config file on the MS: {0}".format(const.HTTPD_CFG_FILE))
        replace_cmd = self.redhatutils.get_replace_str_in_file_cmd(
            "-Indexes", "Indexes", const.HTTPD_CFG_FILE)
        self.run_command(
            self.ms_node, replace_cmd, default_asserts=True, su_root=True)

        self.log("info", "2. Start a puppet run and wait for it to complete.")
        self.wait_full_puppet_run(self.ms_node)

        self.log(
            "info", "3. Verify that the '-Indexes' option is reset in the "
            "'directories' sections of the config file.")
        self.check_indexes_in_apache_config_file()

    @attr('all', 'revert', 'story284890', 'story284890_tc03')
    def test_03_n_ms_directory_listing_not_served(self):
        """
            @tms_id: torf_284890_tc03
            @tms_requirements_id: TORF-284890
            @tms_title: Directory listing on the LITP Management server are not
                served.
            @tms_description:
               Verify that directory listing on the LITP Management server are
               not served.
            @tms_test_steps:
                @step: On the MS, attempt to retrieve a web directory listing.'
                @result: Verify that the Status code is 403 - Forbidden.
                Verify that the request returns an error to say that
                the user doesn't have permission to access the directory.
            @tms_test_precondition: NA
            @tms_execution_type: Automated
        """
        self.log("info", "1. Attempt to retrieve a directory listing.")
        url = "http://localhost/litp/"
        curl_cmd = "{0} {1} -D {2}".format(const.CURL_PATH,
                                           url,
                                           const.STDOUT_PATH)
        stdout, _, returnc = self.run_command(self.ms_node, curl_cmd)

        self.log("info", "2. Verify that the http status code is 403.")
        self.assertEqual(0, returnc, "The 'curl' command failed.")

        self.assertTrue("HTTP/1.1 403 Forbidden" in stdout,
                        "Unexpected curl response.")

        self.log(
            "info", "3. Verify that the command returns an error to say that "
            "the user doesn't have permission to access the directory.")
        xml = ''.join(stdout)
        self.assertTrue("You don't have permission to access /litp/" in xml,
                        "Unexpected curl response.")

    @attr('all', 'revert', 'story284890', 'story284890_tc04')
    def test_04_p_ms_content_is_served(self):
        """
            @tms_id: torf_284890_tc04
            @tms_requirements_id: TORF-284890
            @tms_title: Content in the accessible directories is served.
            @tms_description:
                Verify that content in the accessible directories is served.
            @tms_test_steps:
                @step: On the MS, attempt to retrieve a file.
                @result: The HTTP status code is 200 - OK.
                    The user is able to download the "comps.xml" file.
            @tms_test_precondition: NA
            @tms_execution_type: Automated
        """
        self.log("info", "1. Attempt to retrieve a file.")
        url = "http://localhost/litp/comps.xml"
        curl_cmd = "{0} {1} -D {2}".format(const.CURL_PATH,
                                           url,
                                           const.STDOUT_PATH)
        stdout, _, returnc = self.run_command(self.ms_node, curl_cmd)

        self.log("info", "2. The HTTP status code is 200 - OK")
        curl_out = ''.join(stdout)
        self.assertEqual(0, returnc, "The 'curl' command failed.")
        self.assertTrue("HTTP/1.1 200 OK" in curl_out,
                        "Unexpected curl response.")

        self.log("info", "3. The user can download the 'comps.xml' file.")
        self.assertTrue("LITP provided packages" in curl_out,
                        "Unexpected curl response.")
