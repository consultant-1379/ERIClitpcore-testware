'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2013
@author:    Luke Murphy
@summary:   Integration test to access specific
            version of API identified by specific URL
            Agile: EPIC-183, STORY-230, Sub-Task: STORY-230
'''
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
import os


class Story230(GenericTest):
    """
    As a REST API user I want to access a specific
    version of the API identified by a specific URL
    """

    def setUp(self):
        """Run before every test"""
        super(Story230, self).setUp()
        self.cli = CLIUtils()
        self.test_ms = self.get_management_node_filename()

        # get master server ip address
        self.ms_ip = self.get_node_att(self.test_ms, 'ipv4')
        self.assertNotEqual("", self.ms_ip)

        # init RestUtils
        self.rest = RestUtils(self.ms_ip)

    def tearDown(self):
        """Run after every test"""
        super(Story230, self).tearDown()

    def assert_expected_failure(self, std_out,
                                std_err, return_code, err_msg):
        """Given std_out, std_err and a return code of an invalid REST
           request, we check that std_err is empty (payload comes in
           std_out), return_code is '404' and a valid error message is
           present in the std_out (error message should contain invalid
           path to the user / something useful)"""
        self.assertEqual("", std_err)
        self.assertFalse(self.rest.is_status_success(return_code))
        self.assertTrue(err_msg in std_out)

    @attr('all', 'revert', 'story230', 'story230_tc01')
    def test_01_p_version_output(self):
        """
            Description:
                Verify that REST interface is the correct version
            Actions:
                1. run GET on url
                2. assert we get expected returns
                3. assert that the correct version number is in the ouput
                4. assert that version is a major number only
            Result:
                Correct version for REST interface is validated
        """
        # 1. run 'GET' with '-v' option
        std_out, std_err, return_code = self.rest.get("/", '-v')

        # when passing option to 'curl', verbose output comes back
        # in the standard error stream
        verbose_out = std_err

        # 2. assert we get expected values (success)
        self.assertNotEqual([], std_out)
        self.assertNotEqual("", verbose_out)
        self.assertTrue(
            self.rest.is_status_success(return_code),
            "'GET' request to {0} failed".format(self.rest.get_rest_uri())
        )

        # 3. assert version number in the returned output
        rest_version_num = self.rest.restpath.split('/')[-1]
        self.assertTrue(rest_version_num in verbose_out)

        # 4. assert major number only
        try:
            int(rest_version_num.split('v')[1])
            is_major_number = True
        except ValueError:
            is_major_number = False

        self.assertTrue(is_major_number)

    @attr('all', 'revert', 'story230', 'story230_tc02', 'cdb_priority1')
    def test_02_p_verify_json_return(self):
        """
            Description:
                Verify that the payload returned
                from a 'GET' request is type - JSON
            Actions:
                1. run 'GET' on this url
                2. assert we got expected values
                3. assert that converting the output to json
                   works correctly
            Result:
                Payload type is verified
        """
        # 1. run 'GET'
        std_out, std_err, return_code = self.rest.get("/", "-v")
        out_dict, errors = self.rest.get_json_response(std_out)

        # std_err contains '-v' output
        verbose_out = std_err

        # 3. assert we get expected values (success)
        self.assertEqual([], errors)
        self.assertNotEqual("", verbose_out)
        self.assertTrue(
            self.rest.is_status_success(return_code),
            "'GET' request to {0} failed".format(self.rest.restpath)
        )

        # 4. assert that the payload was json
        self.assertNotEqual([], out_dict)
        self.assertEqual([], errors)

        self.assertTrue(
            "Payload was not returned as JSON",
            "Content-Type: application/json" in verbose_out
        )

    @attr('all', 'revert', 'story230', 'story230_tc03', 'cdb_priority1')
    def test_03_n_request_versions(self):
        """
            Negative tests for restful service - incorrect versions
            used in requests.
            Steps:
                Validate that requesting (GET):
                    a) incorrect minor version
                    b) incorrect major version
                    c) no version
                and updating (PUT):
                    d) incorrect minor version
                of the REST interface will return the expected failures
            Actions:
                1. GET on incorrect minor version of REST interface
                2. GET on incorrect major version of REST interface
                3. GET on incorrect no version of REST interface
                4. PUT update on incorrect minor version of REST interface
            Result:
                Requesting incorrect versions fails as expected
            Note: Added to CDB Priority because it adds a quick and yet
            comprehensive verification of REST functionality, not because of
            the version checking!
        """
        # 1. override rest instance with incorrect minor version
        self.rest = RestUtils(self.ms_ip, rest_version="v1.0.3")
        std_out, std_err, return_code = self.rest.get("/")
        self.assert_expected_failure(
            std_out, std_err, return_code, self.rest.restpath
        )

        # 2. override rest instance with incorrect major version
        self.rest = RestUtils(self.ms_ip, rest_version="v0")
        std_out, std_err, return_code = self.rest.get("/")
        self.assert_expected_failure(
            std_out, std_err, return_code, self.rest.restpath
        )

        # 3. override rest instance with empty rest version
        self.rest = RestUtils(self.ms_ip, rest_version="")
        std_out, std_err, return_code = self.rest.get("/")
        self.assert_expected_failure(
            std_out, std_err, return_code, self.rest.restpath
        )

        # 4. attempt an update on incorrect minor version
        self.rest = RestUtils(self.ms_ip, rest_version="v1.0.3")
        profile_url = "/software/profiles"
        std_out, std_err, return_code = self.rest.put(
            profile_url,
            self.rest.HEADER_JSON,
            """
            {
                "id": "test1",
                "type": "os-profile",
                "properties": {
                    "name": "sample-profile", "version": "6.2"
                }
            }
            """
        )
        self.assert_expected_failure(
            std_out, std_err, return_code,
            os.path.join(self.rest.restpath, "software/profiles")
        )

    @attr('all', 'revert', 'story230', 'story230_tc04')
    def test_04_n_object_create(self):
        """
            Description:
                Validate that is not possible to create object
                when passing incorrect REST version number
            Actions:
                1. override REST interface with incorrect version number
                2. perform 'POST' on profile_url
                3. assert we get expected failure
            Result:
                Object creation with incorrect REST version
                is proven to not work as expected
        """
        # 1. override REST interface
        self.rest = RestUtils(self.ms_ip, rest_version="v1.0.3")

        # 2. perform POST on URL
        profile_url = "/software/profiles"
        std_out, std_err, return_code = self.rest.post(
            profile_url,
            self.rest.HEADER_JSON,
            """
            { "properties": { "new_field": "sample-value" } }
            """
        )
        # 3. assert expected failure
        self.assert_expected_failure(
            std_out, std_err, return_code,
            os.path.join(self.rest.restpath, "software/profiles")
        )

    @attr('all', 'revert', 'story230', 'story230_tc05')
    def test_05_p_correct_root_info(self):
        """
            Description:
                Performing a 'GET' on the base REST url
                gives you the first level of objects under '/'
            Actions:
                1. 'GET' base url
                2. assert we got expected return
                3. get list of ids from REST return dict
                4. do a LITP show on '/'
                5. compare we have the same list of paths
            Result:
                REST base url gives correct output
        """
        # 1. run 'GET'
        std_out, std_err, return_code = self.rest.get("/")
        out_dict, errors = self.rest.get_json_response(std_out)

        # 2. assert we get expected values (success)
        self.assertEqual([], errors)
        self.assertNotEqual([], std_out)
        self.assertEqual("", std_err)
        self.assertTrue(self.rest.is_status_success(return_code))

        # 3. get list of ids from REST
        try:
            rest_paths = [
                item['id'] for item in out_dict['_embedded']['item']
            ]
        except KeyError:
            self.log(
                "error",
                "Failed to get list of ids from {0}".format(
                    out_dict
                )
            )

        # 4. do show on '/'
        std_out, std_err, return_code = self.execute_cli_show_cmd(
            self.test_ms, "/", "-l"
        )

        # get paths from lists
        model_paths = [url.replace('/', '') for url in std_out[1:]]

        # 5. compare we have the same paths
        model_paths.sort()
        rest_paths.sort()
        self.assertEqual(model_paths, rest_paths)
