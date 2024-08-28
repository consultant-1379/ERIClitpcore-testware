#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     November 2013
@author:    priyanka
@summary:   Integration test for Update Object and Update link
            Agile: EPIC-183, STORY-296
'''

from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
from json_utils import JSONUtils
import os


class Story296(GenericTest):

    '''
    As a REST Client developer I want to Update Object and Update link
     through the REST API
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
        super(Story296, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]

        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.rest = RestUtils(self.ms_ip_address)

        self.profile_path = self.find(self.test_node, "/", "profile", False)[0]
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
       Results:
            Items used in the test are cleaned up and the
            super class prints out end test diagnostics
        """
        self.rest.clean_paths()
        super(Story296, self).tearDown()

    def create_296object(self):
        """
        This function creates test296 Object
        """
        message_data = "{\"id\": \"test296\"," \
            "\"type\": \"os-profile\"," \
            "\"properties\": {\"name\": \"os-profile\"," \
            "\"breed\": \"redhat\"," \
            "\"path\": \"/var/www/html/7.9/os/x86_64/\"," \
            "\"kopts_post\": \"console=ttyS0,115200\"," \
            "\"arch\": \"x86_64\"," \
            "\"version\": \"rhel7\"}}"
        stdout, stderr, status = self.rest.post(self.profile_path,
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)
        return stdout, stderr, status

    def create_link(self):
        """
        This function creates link
        """
        message_data = "{\"id\": \"nod296\"," \
            "\"type\": \"node\"," \
            "\"properties\": " \
            "{\"hostname\": \"myhost\"}}"
        self.rest.post(
            self.node_path,
            self.rest.HEADER_JSON,
            data=message_data)

        # Execute inherit command
        self.rest.inherit_cmd_rest(
            self.node_path + "/nod296/os", self.osprofile_path)

    @attr('all', 'revert')
    def test_01_p_update_object(self):
        """
        Description:
            This test Updates the Object with valid properties and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create command
            2. Update the Object with valid property values
            3. Do a compare with updated properties
            4. Compare the properties with cli

        Result:
            Http return code is 200
            Payload is in json format
        """

            # Call test296 function
        self.create_296object()

            # UPDATE PROPERTIES WITH VALID VALUES
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"breed\": \"updated\"}}"
        stdout, stderr, status, = self.rest.put(self.profile_path +
                                                "/test296",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

        # COMPARE THE UPDATED PROPERTIES
        litp_element_after_update, errors = self.rest.get_json_response(stdout)

        self.assertEqual([], errors)
        self.assertEqual(
            "sample-update", litp_element_after_update["properties"].get(
                "name"
            )
        )
        self.assertEqual("test296", litp_element_after_update["id"])
        self.assertEqual(
            "os-profile", litp_element_after_update["item-type-name"]
        )

        # CHECK PROPERTIES WITH CLI
        url = "/software/profiles/test296"
        args = "-j"
        stdout = self.execute_cli_show_cmd(self.test_node, url, args)
        properties = self.cli.get_properties(stdout[0])

        self.assertEqual("sample-update", properties["name"])
        self.assertEqual("updated", properties["breed"])

    @attr('all', 'revert')
    def test_02_p_update_link(self):
        """
        Description:
            This test Updates the link with valid properties and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create link command
            2. Update the link with valid property values
            3. Do a compare with updated properties
            4. Compare the properties with cli

        Result:
            Http return code is 200
            Payload is in json format
        """
        # Call link function
        self.create_link()

        # UPDATE PROPERTIES WITH VALID VALUES
        # Execute inherit command
        message_data = "{\"properties\": {\"name\": \"sample-update\"}}"
        stdout, stderr, status, = self.rest.put(self.node_path +
                                                "/nod296" + "/os",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        litp_element_after_update, errors = self.rest.get_json_response(stdout)
        self.assertEqual([], errors)

        # COMPARE UPDATED PROPERTIES
        self.assertEqual(
            "sample-update",
            litp_element_after_update["properties"].get("name")
        )
        self.assertEqual("os", litp_element_after_update["id"])
        self.assertEqual(
            "reference-to-os-profile",
            litp_element_after_update["item-type-name"]
        )

        # CHECK PROPERTIES WITH CLI
        url = os.path.join(self.node_path, "nod296/os")
        args = "-j"
        stdout = self.execute_cli_show_cmd(self.test_node, url, args)
        properties = self.cli.get_properties(stdout[0])

        self.assertEqual("sample-update", properties["name"])

    @attr('all', 'revert')
    def test_03_n_update_object_invalid_property_value(self):
        """
        Description:
            This test Updates the Object with invalid property value and
            Ensures return code is 422
            Output is in json format

        Actions:
            1. Perform a create command
            2. Update the Object with invalid property values
            3. Check the output

        Result:
            Http return code is 422
            Payload is in json format
        """

        # Call test296 function
        self.create_296object()

        # UPDATE PROPERTIES WITH INVALID PROPERTY VALUE
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"version\": \"\"}}"
        stdout, stderr, status, = self.rest.put(self.profile_path + "/test296",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        # CHECK OUTPUT
        self.assertTrue("ValidationError" in stdout)
        self.assertTrue("Invalid value" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

    @attr('all', 'revert')
    def test_04_n_update_link_invalid_property_value(self):
        """
        Description:
            This test Updates the link with invalid property value and
            Ensures return code is 422
            Output is in json format

        Actions:
            1. Perform a create link command
            2. Update the link with invalid property values
            3. Check the output

        Result:
            Http return code is 422
            Payload is in json format
        """

            # Call link function
        self.create_link()

        # UPDATE PROPERTIES WITH INVALID PROPERTY VALUE
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"version\": \"&&\"}}"
        stdout, stderr, status, = self.rest.put(self.node_path +
                                                "/nod296" + "/os",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        # CHECK OUTPUT
        self.assertTrue("ValidationError" in stdout)
        self.assertTrue("Invalid value" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

    @attr('all', 'revert')
    def test_05_n_update_object_mandatory_field(self):
        """
        Description:
            This test Updates the Object with empty mandatory field and
            Ensures return code is 422
            Output is in json format

        Actions:
            1. Perform a create command
            2. Update the Object with empty mandatory field
            3. Check the output

        Result:
            Http return code is 422 Payload is in json format
        """

        message_data = "{\"id\": \"nod296\"," \
            "\"type\": \"node\"," \
            "\"properties\": " \
            "{\"hostname\": \"myhost\"}}"
        self.rest.post(self.node_path, self.rest.HEADER_JSON,
                       data=message_data)

        # UPDATE PROPERTIES WITH INVALID PROPERTY VALUE
        message_data = "{\"properties\": " \
            "{\"hostname\": null}}"

        stdout, stderr, status, = self.rest.put(self.node_path + "/nod296",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        # CHECK OUTPUT
        self.assertTrue("MissingRequiredPropertyError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=True, has_props=True
            )
        )

    @attr('all', 'revert')
    def test_06_n_update_object_invalid_property(self):
        """
        Description:
            This test Updates the Object with invalid property and
            Ensures return code is 422
            Output is in json format

        Actions:
            1. Perform a create command
            2. Update the Object with invalid property
            3. Check the output

        Result:
            Http return code is 422
            Payload is in json format
        """

            # Call test296 function
        self.create_296object()

        # UPDATE PROPERTIES WITH INVALID PROPERTY
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"invalid_property_ipaddress\": \"10.242.22.33\"}}"
        stdout, stderr, status, = self.rest.put(self.profile_path + "/test296",
                                                self.rest.HEADER_JSON,
                                                data=message_data)

        # CHECK OUTPUT
        self.assertTrue("PropertyNotAllowedError" in stdout)
        self.assertEqual("", stderr)

        self.assertEqual(422, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=True
            )
        )

    @attr('all', 'revert')
    def test_07_n_update_link_invalid_property(self):
        """
        Description:
            This test Updates the link with invalid property and
            Ensures return code is 422
            Output is in json format

        Actions:
            1. Perform a create link command
            2. Update the link with invalid property
            3. Check the output

        Result:
            Http return code is 422
            Payload is in json format
        """

            # Call link function
        self.create_link()

        # UPDATE PROPERTIES WITH INVALID PROPERTY
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"invalid_property_ipaddress\": \"10.242.22.33\"}}"
        stdout, stderr, status = self.rest.put(self.node_path +
                                               "/nod296" + "/os",
                                               self.rest.HEADER_JSON,
                                               data=message_data)

        # CHECK OUTPUT
        self.assertTrue("PropertyNotAllowedError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

    @attr('all', 'revert')
    def test_08_n_update_invalid_path_object(self):
        """
        Description:
            This test Updates the Object with invalid path and
            Ensures return code is 404
            Output is in json format

        Actions:
            1. Perform a create command
            2. Update the Object with invalid path
            3. Check the output

        Result:
            Http return code is 404
            Payload is in json format
        """

            # Call test296 function
        self.create_296object()

        # UPDATE PROPERTIES WITH INVALID PATH
        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"version\": \"6.4\"}}"
        stdout, stderr, status, = self.rest.put(self.profile_path +
                                                "/invalid/path/test296",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        # CHECK OUTPUT
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert')
    def test_09_n_update_invalid_path_link(self):
        """
        Description:
            This test Updates the link with invalid path and
            Ensures return code is 404
            Output is in json format

        Actions:
            1. Perform a create link command
            2. Update the link with invalid path
            3. Check the output

        Result:
            Http return code is 404
            Payload is in json format
        """

            # Call link function
        self.create_link()

        # UPDATE PROPERTIES WITH INVALID PATH

        message_data = "{\"properties\": {\"name\": \"sample-update\"," \
            "\"version\": \"rhel7\"}}"
        stdout, stderr, status, = self.rest.put(self.node_path + "/nod296" +
                                                "/invalid/path/os",
                                                self.rest.HEADER_JSON,
                                                data=message_data)

        # CHECK OUTPUT
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert')
    def test_10_n_update_itemtypes(self):
        """
        Description:
            This test Updates the itemtypes and
            Ensures return code is 405
            Output is in json format

        Actions:
            1. Update the itemtypes
            2. Check the output

        Result:
            Http return code is 405
            Payload is in json format
        """
        # UPDATE ITEMTYPES WITH INVALID VALUE
        message_data = "{\"description\": \"profile item.\"}"
        stdout, stderr, status, = self.rest.put("/item-types/profile",
                                                self.rest.HEADER_JSON,
                                                data=message_data)

        # CHECK OUTPUT
        self.assertTrue("MethodNotAllowedError" in stdout)
        self.assertEqual(405, status)
        self.assertEqual("", stderr)
