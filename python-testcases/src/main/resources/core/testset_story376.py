#!/usr/bin/env pythoJSONUtilsn

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     November 2013
@author:    priyanka
@summary:   Integration test for Delete Object and Delete link
            Agile: EPIC-183, STORY-376
'''
from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
from litp_cli_utils import CLIUtils
from json_utils import JSONUtils
import os


class Story376(GenericTest):

    '''
    As a REST Client developer I want to Delete Object and Delete link
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
        super(Story376, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]

        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.rest = RestUtils(self.ms_ip_address)

        self.profile_path = self.find(self.test_node, "/", "profile", False)[0]
        self.node_path = self.find(
            self.test_node, "/deployments", "node", False)[0]
        self.osprofile_path = self.find(
            self.test_node, "/software", "os-profile", True)[0]
        self.deployment_path = self.find(
            self.test_node, "/", "deployment", False)[0]

        self.cli = CLIUtils()
        self.json = JSONUtils()
        self.remove = os.path.join(self.profile_path, "test376")

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
        super(Story376, self).tearDown()

    def create_376object(self):
        """
        This function creates test296 Object
         """
        message_data = "{\"id\": \"test376\"," \
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
        message_data = "{\"id\": \"nod376\"," \
            "\"type\": \"node\"," \
            "\"properties\": " \
            "{\"hostname\": \"myhost\"}}"
        self.rest.post(
            self.node_path,
            self.rest.HEADER_JSON,
            data=message_data)

        # RUN COMMAND ON PROFILE ELEMENT OF TYPE OS
        stdout, stderr, status = self.rest.inherit_cmd_rest(
            self.node_path + "/nod376/os", self.osprofile_path)
        #message_data = "{\"id\": \"os\"," \
        #    "\"link\": \"os-profile\"," \
        #    "\"properties\": {\"name\": \"os-profile\"," \
        #    "\"version\": \"rhel6\"}}"
        #stdout, stderr, status = self.rest.post(self.node_path + "/nod376",
        #                                        self.rest.HEADER_JSON,
        #                                        data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)
        return stdout, stderr, status

    @attr('all', 'revert', 'story376', 'story376_tc1')
    def test_01_p_delete_object(self):
        """
        Description:
            This test Deletes the Object and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the Object
            3. Check the Deleted Object with cli

        Result:
            Http return code is 200
            Payload is in json format
        """

        # Call test296 function
        stdout, _, _, = self.create_376object()

        # RUN COMMAND TO CHECK PROFILE ELEMENTS
        litp_element_before_delete, errors = \
            self.rest.get_json_response(stdout)
        self.assertEqual([], errors)

        stdout, stderr, status, = self.rest.delete(self.remove)
        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        litp_element_after_delete, errorlist = \
            self.rest.get_json_response(stdout)
        self.assertEquals(errorlist, [],
                          "Errors returned {0}".format(errorlist))
        self.assertEqual(1, len(litp_element_after_delete["_embedded"]))

        self.assertNotEqual(
            litp_element_after_delete["_embedded"]["item"][0]["id"],
            litp_element_before_delete["id"]
        )

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=True, has_props=False
            )
        )

        # CHECK THE DELETED OBJECT WITH CLI
        path = "/software/profiles/test376"
        _, stderr, _ = self.execute_cli_show_cmd(
            self.test_node, path, "-j", expect_positive=False
        )
        # CHECK THE OUTPUT
        self.assertTrue(
            self.is_text_in_list(
                "InvalidLocationError",
                stderr
            )
        )

    @attr('all', 'revert', 'story376', 'story376_tc2')
    def test_02_p_delete_link(self):
        """
        Description:
            This test Deletes the link and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the link
            3. Check the Object with cli

        Result:
            Http return code is 200
            Payload is in json format
        """

        # Call test296 function
        stdout, _, _, = self.create_link()

        # RUN COMMAND TO DELETE LINK
        litp_element_before_delete, errors = \
            self.rest.get_json_response(stdout)
        self.assertEqual([], errors)

        stdout, stderr, status, = self.rest.delete(self.node_path +
                                                   "/nod376/os")
        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        litp_element_after_delete, errorlist = \
            self.rest.get_json_response(stdout)

        self.assertEquals([], errorlist)
        self.assertTrue(1, len(litp_element_after_delete["_embedded"]))

        self.assertFalse(
            litp_element_after_delete["_embedded"]["item"][0]["id"]
            == litp_element_before_delete["id"])

        # CHECK THE DELETED OBJECT WITH CLI
        path = "/software/profiles/test376"
        _, stderr, _ = self.execute_cli_show_cmd(
            self.test_node, path, "-j", expect_positive=False
        )

        # CHECK THE OUTPUT
        self.assertTrue(
            self.is_text_in_list(
                "InvalidLocationError",
                stderr
            )
        )

        # CHECK THE DELETED LINK WITH CLI
        path = self.node_path + "/nod376/os"
        stdout, stderr, status = self.execute_cli_show_cmd(
            self.test_node, path, "-j", expect_positive=False
        )

        # CHECK THE OUTPUT
        self.assertTrue(
            self.is_text_in_list(
                "InvalidLocationError",
                stderr
            )
        )

    @attr('all', 'revert', 'story376', 'story376_tc3')
    def test_03_n_delete_non_existing_object(self):
        """
        Description:
            This test Deletes the non existing Object and
            Ensures return code is 404 Not Found
            Output is in json format

        Actions:
            1. Perform a delete command
            2. Check 404 Not Found Status

        Result:
            Http return code is 404 Not Found
            Payload is in json format
        """

        # RUN COMMAND TO DELETE INVALID PROFILE ELEMENT
        stdout, stderr, status, = self.rest.delete(self.profile_path +
                                                   "/INVALID")

        # CHECK OUTPUT
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert', 'story376', 'story376_tc4')
    def test_04_n_delete_parent_instance_and_delete_child(self):
        """
        Description:
            This test Deletes the Parent instance and
            try to delete the child
            Ensures return code is 200 when parent instance deleted
            Ensures return code is 404 when child deleted
            Output is in json format

        Actions:
            1. Perform a create command for parent
            2. Perform a create command for child
            3. Delete the parent instance
            4. Delete the child Object

        Result:
            Http return code is 404
            Payload is in json format
        """
        # RUN COMMAND ON PROFILE ELEMENT OF TYPE DEPLOYMENT(parent)
        message_data = "{\"id\": \"dep376\"," \
            "\"type\": \"deployment\"}"
        stdout, stderr, status = self.rest.post(self.deployment_path,
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        # RUN COMMAND ON PROFILE ELEMENT OF TYPE CLUSTER(child)
        message_data = "{\"id\": \"cluster376\"," \
            "\"type\": \"cluster\"}"
        stdout, stderr, status = self.rest.post(self.deployment_path +
                                                "/dep376/clusters",
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        # RUN COMMAND TO DELETE LINK
        litp_element_before_delete, errors = \
            self.rest.get_json_response(stdout)
        self.assertEqual([], errors)

        stdout, stderr, status, = self.rest.delete(self.deployment_path +
                                                   "/dep376")
        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        litp_element_after_delete, errorlist = \
            self.rest.get_json_response(stdout)
        self.assertEquals([], errorlist)
        self.assertTrue(len(litp_element_after_delete["_embedded"]) == 1)

        self.assertFalse(
            litp_element_after_delete["_embedded"]["item"][0]["id"]
            == litp_element_before_delete["id"])

        # RUN COMMAND TO DELETE CHILD ELEMENT
        stdout, stderr, status, = self.rest.delete(self.deployment_path +
                                                   "/dep376/clusters/"
                                                   "cluster376")
        # CHECK OUTPUT
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert', 'story376', 'story376_tc5')
    def test_05_n_delete_root(self):
        """
        Description:
            This test Deletes root and
            Ensures return code is 405 MethodNotAllowedError
            Output is in json format

        Actions:
            1. Perform a Delete command on root
            2. Check 405 MethodNotAllowedError Status

        Result:
            Http return code is 405 MethodNotAllowedError
            Payload is in json format
        """

        # RUN COMMAND TO DELETE ROOT
        stdout, stderr, status, = self.rest.delete("/")
        # CHECK OUTPUT
        self.assertTrue("MethodNotAllowedError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(405, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=True, has_props=False
            )
        )

    @attr('all', 'revert', 'story376', 'story376_tc6')
    def test_06_n_delete_collections(self):
        """
        Description:
            This test Deletes the Collections and
            Ensures return code is 405 MethodNotAllowedError
            Output is in json format

        Actions:
            1. Perform a Delete command
            2. Check 405 MethodNotAllowedError Status

        Result:
            Http return code is 405 MethodNotAllowedError Status
            Payload is in json format
        """

        # RUN COMMAND TO DELETE COLLECTIONS
        stdout, stderr, status, = self.rest.delete(self.deployment_path)
        # CHECK OUTPUT
        self.assertTrue("MethodNotAllowedError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(405, status)

    @attr('all', 'revert', 'story376', 'story376_tc7')
    def test_07_n_delete_invalid_version_object(self):
        """
        Description:
            This test Deletes the Object with invalid version and
            Ensures return code is 404
            Output is in json format

        Actions:
            1. Delete the Object with invalid version
            2. Check 404 Not Found Status

        Result:
            Http return code is 404
            Payload is in json format
        """

        # RUN COMMAND TO DELETE PROFILE ELEMENT WITH INVALID VERSION
        self.rest.restpath = '/litp/rest/v1.0.3'
        stdout, stderr, status, = self.rest.delete(self.remove)
        # CHECK OUTPUT
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert', 'story376', 'story376_tc8')
    def test_08_n_delete_rest_and_cli(self):
        """
        Description:
            This test Deletes the Object with rest and
            again deletes the same Object with cli
            Ensures return code is 200 when deletes with rest
            Ensures exit code not 0 when deletes with cli
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the Object with rest
            3. Delete the same Object with cli

        Result:
            Http return code is 404
            Payload is in json format
        """

        # Call test296 function
        stdout, _, _, = self.create_376object()

        # RUN COMMAND TO DELETE PROFILE ELEMENT
        litp_element_before_delete, errors = \
            self.rest.get_json_response(stdout)
        self.assertEqual([], errors)

        stdout, stderr, status, = self.rest.delete(self.remove)
        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        litp_element_after_delete, errorlist = \
            self.rest.get_json_response(stdout)

        self.assertEquals([], errorlist)
        self.assertTrue(len(litp_element_after_delete["_embedded"]) == 1)

        self.assertFalse(
            litp_element_after_delete["_embedded"]["item"][0]["id"]
            == litp_element_before_delete["id"])

        stdout, stderr, status = self.execute_cli_remove_cmd(
            self.test_node, "/software/profiles/test376", "-j",
            expect_positive=False
        )
        self.assertTrue('InvalidLocationError    Path not found',
                        "No Item exists in model: test376")

    @attr('all', 'revert', 'story376', 'story376_tc9')
    def test_09_n_delete_no_version(self):
        """
        Description:
            This test Deletes the Object with no version and
            Ensures return code is 404
            Output is in json format

        Actions:
            1. Delete the Object with no version
            2. Delete the Object
            3. Check 404 Not Found Status

        Result:
            Http return code is 404
            Payload is in json format
        """

        # RUN COMMAND TO DELETE PROFILE ELEMENT WITH NO VERSION
        self.rest.restpath = '/litp/rest'
        stdout, stderr, status, = self.rest.delete(self.remove)
        # CHECK OUTPUT
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert', 'story376', 'story376_tc10')
    def test_10_n_delete_object_twice(self):
        """
        Description:
            This test Deletes the Object twice and
            Ensures return code is 200 when first time deleted
            Ensures return code is 404 when second time deleted
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the Object
            3. Delete the Object second time
            4. Check 404 Not Found Status

        Result:
            Http return code is 404
            Payload is in json format
        """

        # Call test296 function
        stdout, _, _, = self.create_376object()

        # RUN COMMAND TO DELETE PROFILE ELEMENT
        litp_element_before_delete, errorlist = \
            self.rest.get_json_response(stdout)

        self.assertEquals([], errorlist)
        stdout, stderr, status, = self.rest.delete(self.remove)

        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        litp_element_after_delete, errorlist = \
            self.rest.get_json_response(stdout)

        self.assertEquals([], errorlist)
        self.assertTrue(len(litp_element_after_delete["_embedded"]) == 1)
        self.assertFalse(
            litp_element_after_delete["_embedded"]["item"][0]["id"]
            == litp_element_before_delete["id"])

        # RUN COMMAND TO DELETE PROFILE ELEMENT AGAIN
        stdout, stderr, status, = self.rest.delete(self.remove)

        # CHECK OUTPUT
        self.assertTrue("InvalidLocationError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(404, status)

    @attr('all', 'revert', 'story376', 'story376_tc11')
    def test_11_n_delete_resource_linked(self):
        """
        Description:
            This test Deletes the resource linked and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the Object
            3. Create a new LITP PLAN.
            4. Check the PLAN Creation is failing and a
               CardinalityError message is thrown.
        Result:
            REST API is not allowing the user to create a LITP PLAN
            when we Deletes resource which is linked.
        """

        # Call test296 function
        self.create_376object()
        self.create_link()

        # RUN COMMAND TO DELETE PROFILE ELEMENT
        stdout, stderr, status, = self.rest.delete(self.remove)

        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        self.assertNotEqual("", stdout)

        # RUN CREATE PLAN CMD
        message_data = "{\"id\": \"plan\"," \
                       "\"type\": \"plan\"}"

        stdout, stderr, status = self.rest.post("/plans", \
                              self.rest.HEADER_JSON, message_data)
        self.assertEqual(422, status)
        self.assertNotEqual("", stdout)

        # CHECK CardinalityError
        # CHECK THE OUTPUT
        self.assertTrue("CardinalityError" in stdout,
                        "CardinalityError message is missing")

    @attr('all', 'revert', 'story376', 'story376_tc12')
    def test_12_n_delete_parent_resource_linked(self):
        """
        Description:
            This test Deletes parent resource which is linked and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a create command
            2. Delete the Object
            3. Create a new LITP PLAN.
            4. Check the PLAN Creation is failing and a
               the resulting response payload is HAL complient,
               and CardinalityError, MissingRequiredItemError and
               UnresolvedLinkError messages are thrown.
        Result:
            REST API is not allowing the user to create a LITP PLAN
            when we Deletes parent resource which is linked.
        """
        # CREATE STORAGE PROFILE IN MODEL THAT IS ALSO IN XML FILE
        storage_url = self.find(
            self.test_node, "/infrastructure",
            "storage-profile-base", False)[0]

        # RUN COMMAND ON PROFILE ELEMENT OF TYPE STORAGE-PROFILE
        message_data = "{\"id\": \"storage376\"," \
            "\"type\": \"storage-profile\"}"
        stdout, stderr, status = self.rest.post(storage_url,
                                                self.rest.HEADER_JSON,
                                                data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        storage_profile_url = storage_url + "/storage376"
        vg_url = storage_profile_url + "/volume_groups/vg2"
        props = "volume_group_name='vg2_root'"
        self.execute_cli_create_cmd(
            self.test_node, vg_url, "volume-group", props)

        fs1_url = vg_url + "/file_systems/root"
        props = "type='ext4' mount_point='/' size='16G'"
        self.execute_cli_create_cmd(
            self.test_node, fs1_url, "file-system", props)

        fs2_url = vg_url + "/file_systems/swap"
        props = "type='swap' mount_point='swap' size='8G'"
        self.execute_cli_create_cmd(
            self.test_node, fs2_url, "file-system", props)

        pd_url = vg_url + "/physical_devices/internal"
        props = "device_name='sda'"
        self.execute_cli_create_cmd(
            self.test_node, pd_url, "physical-device", props)

        # RUN COMMAND ON PROFILE ELEMENT OF TYPE NODE
        message_data = "{\"id\": \"nod376\"," \
            "\"type\": \"node\"," \
            "\"properties\": " \
            "{\"hostname\": \"myhost\"}}"
        self.rest.post(
            self.node_path,
            self.rest.HEADER_JSON,
            data=message_data)

        # RUN COMMAND ON PROFILE ELEMENT OF TYPE STORAGE-PROFILE
        stdout, stderr, status = self.rest.inherit_cmd_rest(
            self.node_path + "/nod376/storage_profile", \
            storage_profile_url)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(201, status)

        # RUN COMMAND TO DELETE PROFILE ELEMENT
        stdout, stderr, status, = self.rest.delete(storage_profile_url)

        # CHECK JSON OUTPUT
        self.assertEqual("", stderr)
        self.assertEqual(200, status)
        self.assertNotEqual("", stdout)

        # RUN CREATE PLAN CMD
        message_data = "{\"id\": \"plan\"," \
                       "\"type\": \"plan\"}"
        stdout, stderr, status = self.rest.post("/plans", \
                              self.rest.HEADER_JSON, message_data)
        self.assertEqual(422, status)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False
            )
        )

        # CHECK CardinalityError MissingRequiredItemError
        # are present
        invalid_reference_error = 0
        expected_errs = ["MissingRequiredItemError",
                         "CardinalityError",
                         "os",
                         "system"
                         ]

        for item in expected_errs:
            if stdout.find(item) != -1:
                invalid_reference_error += 1
        self.assertEqual(4, invalid_reference_error)

    @attr('all', 'revert', 'story376', 'story376_tc13')
    def test_13_n_delete_itemtypes(self):
        """
        Description:
            This test Deletes the item_types and
            Ensures return code is 405
            Output is in json format

        Actions:
            1. Delete item_types
            2. Check the Output
            3. Check 405 MethodNotAllowedError Status

        Result:
            Http return code is 405
            Payload is in json format
        """
        # RUN COMMAND TO DELETE ITEMTYPES
        stdout, stderr, status, = self.rest.delete("/item-types")
        # CHECK OUTPUT
        self.assertTrue("MethodNotAllowedError" in stdout)
        self.assertEqual("", stderr)
        self.assertEqual(405, status)
