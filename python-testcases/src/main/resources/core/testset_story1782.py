'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    joe
@summary:   Integration test for litp version commands
            Agile: LITPCDS-1782
'''


from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
import test_constants

VERSION_FILE = test_constants.LITP_PATH + ".version"
INSTALL_FILE = test_constants.LITP_PATH + ".upgrade.history"

LITP_GROUP = "LITP2"


class Story1782(GenericTest):

    '''
    As a LITP User I want to be able to retrieve the version information,
    so that I can provide this info when troubleshooting issues
    '''

    def setUp(self):
        """
        Description:
            Runs before every single test
        Actions:
            1. Call the super class setup method
            2. Set up variables used in the tests
        Results:
            The super class prints out diagnostics and variables
            common to all tests are available.
        """
        # 1. Call super class setup
        super(Story1782, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip_address = self.get_node_att(self.ms_node, 'ipv4')
        ms_node_username = self.get_node_att(self.ms_node, "username")
        ms_node_password = self.get_node_att(self.ms_node, "password")
        self.rest = RestUtils(self.ms_ip_address, username=ms_node_username,
                              password=ms_node_password)

    def _run_cmd(self, cmd, add_to_cleanup=True, su_root=False,
                 expect_positive=True):
        """
        Run a command asserting success or error (returns: stdout / stderr)
        """
        stdout, stderr, exit_code = self.run_command(
            self.ms_node, cmd, add_to_cleanup=add_to_cleanup, su_root=su_root)
        if expect_positive:
            self.assertNotEqual("", stdout)
            self.assertEqual([], stderr)
            self.assertEqual(0, exit_code)
            result = '\n'.join(stdout)
        else:
            self.assertEqual([], stdout)
            self.assertNotEqual("", stderr)
            self.assertNotEqual(0, exit_code)
            result = '\n'.join(stderr)
        return result

    def _assert_in(self, expected_in, actual):
        """
        Method for check for something that is expected
        """
        self.assertTrue(expected_in in actual,
                        "'%s' not in '%s'" % (expected_in, actual))

    def _get_litp_packages(self):
        """
        Method to get list of installed LITP packages
        """
        litp_pkgs_cmd = (
           "/bin/rpm -qa --qf '%-{name} %-{version}\\n' | sort -k1 | "
           "egrep \"`yum groupinfo " + LITP_GROUP + "| grep CXP | "
           "tr -d ' ' | tr '\\n' '|' | sed 's/|$//g'`\"")
        return self._run_cmd(litp_pkgs_cmd, su_root=True)

    @attr('all', 'revert')
    def obsolete_05_p_retrieve_version_info_rest(self):
        """
        Description:
            Test getting version info from REST

        Actions:
            1. Run REST get on "/"
            2. Ensure version in response
            3. Ensure install info in response
            4. Ensure LITP packages in response

        Result:
            The REST response contains the correct version info

        Test case obsolete with removal of version file
        """
        # 1. Run REST get on "/"
        rest_response, stderr, status = self.rest.get("/")
        self.assertEqual(200, status)
        self.assertEqual("", stderr)
        self.assertNotEqual("", rest_response)
        response, _ = self.rest.get_json_response(rest_response)

        # 2. Ensure version in response
        version_file = "".join(self.get_file_contents(
            self.ms_node, VERSION_FILE))
        self._assert_in(version_file, response.get("version"))

        # 3. Ensure install info in response
        install_file = "".join(self.get_file_contents(
            self.ms_node, INSTALL_FILE))
        for line in install_file.split('\n'):
            if line:
                self._assert_in(install_file, response.get("install-info"))

        # 4. Ensure LITP packages in response
        litp_pkgs = self._get_litp_packages()
        litp_pkgs_list = [p['package'] + " " + p['version']
                           for p in response.get("litp-packages")]
        for pkg_info in litp_pkgs.split('\n'):
            if pkg_info:
                self._assert_in(pkg_info, litp_pkgs_list)
