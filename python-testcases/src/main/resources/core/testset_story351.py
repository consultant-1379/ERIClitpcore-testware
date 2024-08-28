#!/usr/bin/env python

"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     October 2013
@author:    priyanka
@summary:   Integration test for REST API "Create"
            Agile: EPIC-183, STORY-351, Sub-task: STORY-xxxx
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
from litp_generic_utils import GenericUtils
from json_utils import JSONUtils

import os


class Story351(GenericTest):

    """
    Description:
        As a REST Client developer I want to perform Create operation on
        model resources so I can add items to the object models.
    """

    def setUp(self):
        super(Story351, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]
        self.cli = CLIUtils()
        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.restutils = RestUtils(self.ms_ip_address)
        self.genericutils = GenericUtils()
        self.profile_path = self.get_path_url("/software", "profile")
        self.osprofile_path = self.find(
            self.test_node, "/software", "os-profile", True)[0]
        self.node_path = self.find(
            self.test_node, "/deployments", "node", False
        )[0]
        self.json = JSONUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
            super class prints out end test diagnostics
        """
        self.restutils.clean_paths()
        super(Story351, self).tearDown()

    def get_path_url(self, path, resource):
        """
        Description:
            Gets the url path
        Actions:
            1. Perform find command + return item
       Results:
           Returns the path url for the current environment
        """
        # 1 RUN FIND
        return self.find(self.test_node, path, resource, False)[0]

    def create_node(self, name):
        """
        Run curl "POST" command to create a new litp node.
        Check that the return code is "201" which means that the
        Resource was created successfully.
        """
        # RUN CURL POST COMMAND TO CREATE NODE351
        stdout, stderr, status = \
            self.restutils.post(self.node_path,
                                "Content-Type:application/json",
                                "{\"id\":\"%s\",\"type\":\"node\","
                                "\"properties\":{\"hostname\":\"myhost\"}}"
                                % name)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        return stdout, stderr, status

    @attr('all', 'revert', 'story351', 'story351_tc01')
    def test_01_p_create_object(self):
        """
        @tms_id: litpcds_351_tc01
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create a valid LITP item using REST API.
        @tms_description: Create a valid LITP item using REST API.
        @tms_test_steps:
         @step: Run curl "POST" command to create an os-profile test351 under
               /software/profiles, store response and convert to json format
         @result: return code should be "201" which means that the
               Resource was created successfully
         @step: Run curl "GET" command for reading the previously created
               "test351" os-profile.
         @result: output returned
         @step: Compare the outputs returned by "POST" and "GET" Commands.
         @result: outputs should not differ
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'RUN CURL POST COMMAND TO CREATE A NEW OS-PROFILE')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")
        self.assertNotEqual(stdout, "", "POST command output is empty")

        self.log('info', 'COMPARE THE CREATED PROPERTIES AND DATA')
        litp_element_after_create, errors = \
            self.restutils.get_json_response(stdout)

        self.assertEqual([], errors)

        self.log('info', 'CHECK JSON OUTPUT')
        self.assertEqual("", stderr)
        self.assertEqual(201, status)
        self.assertEqual(
            "sample-profile",
            litp_element_after_create["properties"].get("name")
        )
        self.assertEqual(
            "test351", litp_element_after_create["id"]
        )
        self.assertTrue(
            "os-profile", litp_element_after_create["item-type-name"]
        )

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'RUN CURL GET COMMAND TO READ THE PREVIOUSLY '
                         'CREATED OS-PROFILE')
        stdout, stderr, status = self.restutils.get(self.profile_path +
                                                    '/test351')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'GET ALL LITP PROFILES URLS PRESENT UNDER /SOFTWARE')
        profile_urls = self.find(self.test_node, '/software', 'os-profile')
        self.log("info", profile_urls)

        profile_to_create = [
            profile_url for profile_url in profile_urls \
                if "test351" in profile_url
        ]
        self.assertNotEqual([], profile_to_create)
        self.assertEqual(1, len(profile_to_create))

        self.log('info', 'RUN "SHOW" COMMAND USING test351 URL')
        stdout, _, _ = self.execute_cli_show_cmd(
            self.test_node, profile_to_create[0], "-j"
        )

        self.log('info', 'CHECK THE PROPERTIES OF "test351" os-profile.')
        properties = self.cli.get_properties(stdout)
        self.log('info', properties)

        self.assertEqual("rhel7", properties["version"])
        self.assertEqual("sample-profile", properties["name"])
        self.assertEqual("redhat", properties["breed"])
        self.assertEqual("/var/www/html/7.9/os/x86_64/", properties["path"])
        self.assertEqual("x86_64", properties["arch"])
        self.assertEqual("console=ttyS0,115200", properties["kopts_post"])

    @attr('all', 'revert', 'story351', 'story351_tc02')
    def test_02_n_create_duplicate_object(self):
        """
        @tms_id: litpcds_351_tc02
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create a duplicate LITP item using REST API.
        @tms_description: Negative test to check that REST API
            is not allowing the user to create duplicate LITP items.
        @tms_test_steps:
         @step: Run curl "POST" command to create "test351" os-profile under
               /software/profiles.
         @result: HTTP Response should be "HTTP 201" Resource
               created successfully.
         @step: Run curl "POST" command again to create a duplicate
               test351 os-profile.
         @result: REST API should return "409" Item already exists error.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\": "
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        self.log('info', 'RUN CURL POST COMMAND TO CREATE '
                         'A DUPLICATE OS-PROFILE')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"version\":\"rhel7\"}}")

        self.log('info', ' REST API returns "409" Item already exists error.')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(409, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIENT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("ItemExistsError" in stdout,
                        "ItemExistsError message is missing")

    @attr('all', 'revert', 'story351', 'story351_tc03')
    def test_03_n_invalid_version_object(self):
        """
        @tms_id: litpcds_351_tc03
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create a LITP item with invalid version property
            using REST API.
        @tms_description: Negative test to check that REST API
            is not allowing the user to create a LITP os-profile
            having an invalid version.
        @tms_test_steps:
         @step: Run curl "POST" command to create a LITP os-profile by passing
               an empty version.
         @result: REST API should return "422" : Invalid value for property
               type error
         @step: Run curl "POST" command to create a LITP os-profile by passing
               an incorrect version : &&.
         @result: REST API should return "422" : Invalid value for property
               type error.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'RUN CURL POST COMMAND TO CREATE A NEW OS-PROFILE'
                         ' USING EMPTY VERSION')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"\"}}")
        self.assertNotEqual(stdout, "", "POST command output is empty")
        self.assertEqual(stderr, "", "POST command error not empty")
        self.assertEqual(status, 422, "HTTP Response was not 422")

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("ValidationError" in stdout,
                        "ValidationError message is missing")
        self.assertTrue("Invalid value" in stdout)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A NEW '
                         'OS-PROFILE USING INVALID INPUT FOR VERSION')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"version\":\"&&\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("ValidationError" in stdout)
        self.assertTrue("Invalid value" in stdout)
        self.assertTrue("MissingRequiredPropertyError" in stdout)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

    @attr('all', 'revert', 'story351', 'story351_tc04')
    def test_04_n_invalid_property_ipaddress(self):
        """
        @tms_id: litpcds_351_tc04
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create a LITP item with invalid ip-address property
            using REST API.
        @tms_description: Negative test to check that REST API is
            not allowing the user to create a LITP os-profile having
            an invalid ip address.
        @tms_test_steps:
         @step: Run curl 'POST' command to create a LITP os-profile using an
               invalid "ipaddress" value.
         @result: REST API should return "422" : Property not allowed error
               message.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'RUN CURL POST COMMAND TO CREATE A NEW OS-PROFILE '
                         'USING INVALID VALUE FOR IPADDRESS')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"ipaddress\": \"10.242.22.33\","
                                "\"version\":\"rhel7\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertTrue("PropertyNotAllowedError" in stdout)

    @attr('all', 'revert', 'story351', 'story351_tc05')
    def test_05_n_create_node_without_mandatory_field(self):
        """
        @tms_id: litpcds_351_tc05
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create an invalid LITP item using REST API
            (missing mandatory fields).
        @tms_description: Negative test to check that REST API
            is not allowing the user to create LITP Objects
            without specifying mandatory fields.
        @tms_test_steps:
         @step: Run curl "POST" command to create a LITP NODE Object
               but without passing all required properties.
         @result: REST API should return "422" :
               Missing Required Property Error message.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'RUN CURL POST COMMAND TO CREATE A LITP NODE '
                         'WITHOUT SPECIFYING MANDATORY FIELDS')

        stdout, stderr, status = \
            self.restutils.post(self.node_path,
                                "Content-Type:application/json",
                                "{\"id\":\"node351\","
                                "\"type\":\"node\"}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("MissingRequiredPropertyError" in stdout)

    @attr('all', 'revert', 'story351', 'story351_tc06')
    def test_06_n_invalid_url(self):
        """
        @tms_id: litpcds_351_tc06
        @tms_requirements_id: LITPCDS-351
        @tms_title: Check for 404 Invalid Location Error on requests
            to non existing path
        @tms_description: Negative test to check that REST API
            is not allowing the user to create a LITP os-profile
            using an invalid rest path.
        @tms_test_steps:
         @step: Run curl "POST" command to create a LITP os-profile using an
            invalid rest path.
         @result: REST API should return "404": "Invalid Location Error".
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CHANGE THE REST PATH TO A NON EXISTING URL')
        self.restutils.restpath = '/litp/rest/v1/invalid'

        self.log('info', 'RUN curl COMMAND ON PROFILE ELEMENT with wrong url')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

    @attr('all', 'revert', 'story351', 'story351_tc07')
    def test_07_n_html_format(self):
        """
        @tms_id: litpcds_351_tc07
        @tms_requirements_id: LITPCDS-351
        @tms_title: POST body with invalid Content-Type
        @tms_description: Negative test to check that REST API
            is not allowing the user to create a LITP os-profile
            using invalid content-type.
        @tms_test_steps:
         @step: Run curl "POST" command to create a LITP os-profile with an
               invalid content-type (application/html).
         @result: REST API should return "406": "invalid 'Content-Type'
               header type."
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'RUN curl COMMAND ON PROFILE ELEMENT'
                         ' with invalid html header')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/html",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(406, status)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("HeaderNotAcceptableError" in stdout)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

    @attr('all', 'revert', 'story351', 'story351_tc08')
    def test_08_n_create_duplicate_object_using_cli(self):
        """
        @tms_id: litpcds_351_tc08
        @tms_requirements_id: LITPCDS-351
        @tms_title: Duplicate items created in parallel via CLI and REST
        @tms_description: Negative test to check that creation of duplicate
            items is not possible if user attempts to recreate via CLI
            an item previously created via REST.
        @tms_test_steps:
         @step: Run curl 'POST' command to create test351 os-profile using
            valid parameters.
         @result: Item should be created successfully, 201 returned
         @step: Run LITP CLI "create" command for creating the same test351
            os-profile.
         @result: LITP CLI "create" command should fail with error message
            ItemExistsErrorItem already exists in model
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE OBJECT USING REST')
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")

        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        self.log('info', 'CREATE THE SAME OBJECT USING CLI')
        profile_url = self.profile_path + "/test351"
        props = "name='sample-profile' version='rhel6'"
        _, stderr, _ = self.execute_cli_create_cmd(
        self.test_node, profile_url, "os-profile",
        props, expect_positive=False, add_to_cleanup=False
        )

        self.log('info', 'CHECK EXPECTED ERROR MESSAGE POSTED')
        self.assertTrue(
            self.is_text_in_list(
                'ItemExistsError    Item already exists in model:',
                stderr
            )
        )

    @attr('all', 'revert', 'story351', 'story351_tc09')
    def test_09_p_update_using_cli(self):
        """
        @tms_id: litpcds_351_tc09
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create item using REST API, update Property using CLI.
        @tms_description: Create object using REST API,
            update Property of the object using CLI.
        @tms_test_steps:
         @step: Run curl 'POST' command to create "test351" os-profile under
              /software/profiles by using valid parameters.
         @result: Item should be created successfully, 201 returned
         @step: Run a valid LITP CLI update command for updating name
            and version properties.
         @result: LITP CLI update command should be applied successfully
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE OBJECT USING REST')

        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel7\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        self.log('info', 'UPDATE THE OBJECT USING CLI')
        profile_url = self.profile_path + "/test351"
        props = "name='test'"
        _, stderr, _ = self.execute_cli_update_cmd(
            self.test_node, profile_url, props)

    @attr('all', 'revert', 'story351', 'story351_tc10')
    def test_10_n_create_object_with_http(self):
        """
        @tms_id: litpcds_351_tc10
        @tms_requirements_id: LITPCDS-351
        @tms_title: Create item using HTTP.
        @tms_description: Create object using HTTP protocol.
        @tms_test_steps:
         @step: Run curl 'POST' command for creating test351 os-profile using
              the "http" protocol.
         @result: 'POST' command should fail with a error message
             Unable to establish HTTPS connection as http protocol
             is not allowed.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        stdout, stderr, status = \
            self.restutils.request(
                "http://%s:%s%s%s" %
                (self.restutils.server,
                 self.restutils.port,
                 self.restutils.restpath,
                 self.profile_path),
                "Content-Type:application/json",
                "GET",
                "{\"id\": \"test351\","
                "\"type\": \"os-profile\","
                "\"properties\": "
                "{\"name\": \"sample-profile\","
                "\"breed\": \"redhat\","
                "\"path\": \"/var/www/html/7.9/os/x86_64/\","
                "\"arch\": \"x86_64\","
                "\"kopts_post\": \"console=ttyS0,115200\","
                "\"version\": \"rhel7\"}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertTrue(
            self.is_text_in_list(
                "The client sent a plain HTTP request, but this server "
                "only speaks HTTPS on this port.",
                [stdout]
            )
        )
        self.assertEqual(400, status)

    @attr('all', 'revert', 'story351', 'story351_tc11')
    def test_11_p_inherit_item_rest(self):
        """
        @tms_id: litpcds_351_tc11
        @tms_requirements_id: LITPCDS-351
        @tms_title: Inherit item using REST API.
        @tms_description: Create a valid LITP inheritance using REST API.
        @tms_test_steps:
         @step: Run curl "POST" command to inherit an os-profile item,
            store output in json format
         @result: return code should be "201" which means that the
               Resource was created successfully.
         @step: Run curl "GET" command for reading the previously inherited
               os-profile item.
         @result: inherited os-profile item returned
         @step: Compare the outputs returned by "POST" and "GET" Commands.
         @result: There should be no difference between responses
            of POST and GET commands.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE OS OS-PROFILE LINK')
        self.log('info', 'Execute REST inherit command')
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'COMPARE THE CREATED LINK PROPERTIES')
        litp_element_after_create, errors = \
            self.restutils.get_json_response(stdout)
        self.assertEqual([], errors)

        self.log('info', 'CHECK JSON OUTPUT')
        self.assertEqual("", stderr)
        self.assertEqual(201, status)
        self.assertEqual("os-profile1", litp_element_after_create[
            "properties"].get("name")
        )
        self.assertEqual("os", litp_element_after_create["id"])
        self.assertEqual(
            "reference-to-os-profile",
            litp_element_after_create["item-type-name"]
        )

        self.log('info', 'RUN CURL GET COMMAND TO READ THE PREVIOUSLY '
                         'CREATED OS-PROFILE')
        stdout, stderr, status = self.restutils.get(self.node_path +
                                                    "/node351/os")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        self.log('info', 'GET "os" LITP PROPERTIES AS THEY APPEAR '
                         'IN THE LITP TREE')
        path = os.path.join(self.node_path, "node351/os")
        self.log('info', 'RUN "SHOW" COMMAND USING "os" URL')
        self.execute_cli_show_cmd(self.test_node, path, "-j")

        self.log('info', 'CHECK THE PROPERTIES OF "OS" OS-PROFILE LINK.')
        properties = self.cli.get_properties(stdout)
        self.log('info', properties)

        self.assertEqual("os-profile1", properties["name"])
        self.assertEqual("rhel7", properties["version"])

    @attr('all', 'revert', 'story351', 'story351_tc12')
    def test_12_n_create_existing_inheritance_rest(self):
        """
        @tms_id: litpcds_351_tc12
        @tms_requirements_id: LITPCDS-351
        @tms_title: Test creation of an existing inheritance via REST
        @tms_description: Negative test to check that REST API
            is returning a proper error message when the user is
            trying to create a duplicate os-profile inheritance.
        @tms_test_steps:
         @step: Run curl "POST" command to inherit new os-profile item.
         @result: return code should be "201" which means that the
               Resource was created successfully.
         @step: Run curl "POST" command again to inherit os-profile item
            where previously inherited one exists.
         @result: REST API should return "409" Item already exists error
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A PROFILE '
                         'ELEMENT OF TYPE OS')
        self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path)

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A DUPLICATE '
                         'PROFILE ELEMENT OF TYPE OS')
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
                self.node_path + "/node351/os", self.osprofile_path)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(409, status)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue("ItemExistsError" in stdout)

    @attr('all', 'revert', 'story351', 'story351_tc13')
    def test_13_n_inherit_invalid_version_rest(self):
        """
        @tms_id: litpcds_351_tc13
        @tms_requirements_id: LITPCDS-351
        @tms_title: Test inheriting of item with invalid version via REST
        @tms_description: Negative test to check that REST API is not
            allowing the user to inherit a LITP os-profile item with
            an invalid version in REST request
        @tms_test_steps:
         @step: Run curl "POST" command to inherit a LITP os-profile item by
               passing an incorrect empty version
         @result: REST API should return "422" : RegexError errors
         @step: Run curl "POST" command to inherit a LITP os-profile item by
               passing an incorrect "&&" version
         @result: REST API should return "422" : RegexError errors
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMANDS TO CREATE A PROFILE ELEMENT '
                         'OF TYPE OS WITH PROPERTIES WITH EMPTY VERSION '
                         'VALUE')
        message_data = {}
        message_data["name"] = "sample-update"
        message_data["version"] = "/"
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path, message_data)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertTrue("ValidationError" in stdout)

        self.log('info', 'RUN CURL POST COMMANDS TO CREATE A PROFILE ELEMENT '
                         'OF TYPE OS WITH PROPERTIES WITH INVALID '
                         '\'&&\' VERSION VALUE')
        message_data = {}
        message_data["name"] = "sample-update"
        message_data["version"] = "&&"
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path, message_data)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertTrue("ValidationError" in stdout)

    @attr('all', 'revert', 'story351', 'story351_tc14')
    def test_14_n_inherit_invalid_property_ipaddress_rest(self):
        """
        @tms_id: litpcds_351_tc14
        @tms_requirements_id: LITPCDS-351
        @tms_title: Test inheriting os-item with invalid ip address via REST
        @tms_description: Negative test to check that REST API is not allowing
            the user to inherit a LITP os-profile item with an invalid
            "ip address" property.
        @tms_test_steps:
         @step: Run curl 'POST' command to create a LITP os-profile link
               using an invalid pi address property 10.242.22.33.
         @result: REST API should return "422" : Property not allowed error
               message.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A PROFILE ELEMENT'
                         ' OF TYPE OS')
        message_data = {}
        message_data["name"] = "sample-profile"
        message_data["ipaddress"] = "10.242.22.33"
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path, message_data)

        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertTrue("PropertyNotAllowedError" in stdout)

    @attr('all', 'revert', 'story351', 'story351_tc15')
    def test_15_n_missing_property_inherit_rest(self):
        """
        @tms_id: litpcds_351_tc15
        @tms_requirements_id: LITPCDS-351
        @tms_title: Test inheriting item via REST with missing property
        @tms_description: Negative test to check that litp is not allowing
            the user to create PLAN when inheritance with missing properties
            done via REST
        @tms_test_steps:
         @step: Run curl "POST" command to inherit a new os-profile item
            with no properties.
         @result: Return code should be "201" which means that the
            Resource was created successfully.
         @step: execute litp create_plan command
         @result: Plan creation should fail with a CardinalityError
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A PROFILE '
                         'ELEMENT OF TYPE OS')
        message_data = {}
        message_data["version"] = "rhel7"
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", self.osprofile_path, message_data)

        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        self.log('info', 'RUN CREATE PLAN CMD')
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False
        )

        self.log('info', 'CHECK CardinalityError')
        invalid_reference_error = False
        for line in stderr:
            if "CardinalityError" in line:
                invalid_reference_error = True

        self.assertTrue(
            "CardinalityError message is missing",
            invalid_reference_error
        )

    @attr('all', 'revert', 'story351', 'story351_tc16')
    def test_16_n_inherit_points_to_diff_property(self):
        """
        @tms_id: litpcds_351_tc16
        @tms_requirements_id: LITPCDS-351
        @tms_title:This tests an invalid source path when executing an
            inheritance command via REST
        @tms_description: Negative test to check that REST API is not allowing
            the user to inherit a LITP os-profile item using invalid types.
        @tms_test_steps:
         @step: Run curl 'POST' command to inherit a LITP os-profile item
            using an invalid type for link property.
         @result: REST API should return "404" : InvalidLocationError error
               message.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A PROFILE ELEMENT '
                         'OF TYPE OS')
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", "cut", )

        self.log('info', 'CHECK InvalidLocationError')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)
        self.assertTrue("InvalidLocationError" in stdout)

        self.log('info', 'CHECK RESPONSE PAYLOAD IS HAL COMPLIANT')
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

    @attr('all', 'revert', 'story351', 'story351_tc17')
    def test_17_n_inherit_points_to_diff_resource(self):
        """
        @tms_id: litpcds_351_tc17
        @tms_requirements_id: LITPCDS-351
        @tms_title: This tests the source path being of a different type when
            executing the inherit command via REST
        @tms_description: Negative test to check that REST API is not allowing
            the user to inherit a LITP os-profile item using invalid
            child types.
        @tms_test_steps:
         @step: Run curl 'POST' command to inherit a LITP os-profile item
            using an invalid type for link property.
         @result: REST API should return "422" : InvalidChildTypeError error
               message.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'CREATE NODE351')
        self.create_node("node351")

        self.log('info', 'RUN CURL POST COMMAND TO CREATE A PROFILE ELEMENT '
                         'OF TYPE OS')
        storageprofile_path = self.find(
            self.test_node, "/infrastructure", "storage-profile", True)[0]
        stdout, stderr, status = self.restutils.inherit_cmd_rest(
            self.node_path + "/node351/os", storageprofile_path, )

        self.log('info', 'CHECK InvalidChildTypeError')
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )
        self.assertTrue("InvalidChildTypeError" in stdout)
