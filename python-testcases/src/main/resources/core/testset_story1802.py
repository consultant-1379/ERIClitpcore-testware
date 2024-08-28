#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    Maria Varley
@summary:   Integration test
            Agile: STORY-1802
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from rest_utils import RestUtils
from litp_generic_utils import GenericUtils
from json_utils import JSONUtils


class Story1802(GenericTest):

    """
    Description:
       As a Product Designer I want the REST response payload to be HAL
       compliant, so that it is also aligned with
       Ericsson wider adopted specifications
    """

    def setUp(self):
        super(Story1802, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]
        self.cli = CLIUtils()
        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.restutils = RestUtils(self.ms_ip_address)
        self.genericutils = GenericUtils()
        self.profile_path = self.get_path_url("/software", "profile", False)
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
        # 1. Cleanup
        self.restutils.clean_paths()
        # 2. Call superclass teardown
        super(Story1802, self).tearDown()

    def get_path_url(self, path, resource, returnchildren):
        """
        Description:
            Gets the url path
        Actions:
            1. Perform find command
            2. Assert find command returns item
            3. Return item
       Results:
           Returns the path url for the current environment
        """
        # 1 RUN FIND
        path_found = self.find(
            self.test_node, path, resource, returnchildren)
        # 2 ASSERT FIND RETURNS ITEM
        self.assertNotEqual([], path_found)

        # 3 RETURN ITEM
        return path_found[0]

    def update_default_gateway(self, default_network_path, default_value):
        """
        Description:
            Update the default gateway property to value passed
        """
        message_data = """
            {"properties": {"default_gateway" : "%s"}}
        """ % default_value
        stdout, stderr, status = self.restutils.put(
        default_network_path, self.restutils.HEADER_JSON, data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

    @attr('all', 'revert')
    def test_01_n_check_ChildNotAllowedError(self):
        """
        Description:
            Throw ChildNotAllowedError using REST API.
        Actions:
            1. Run curl "POST" command to attempt to throw ChildNotAllowedError
            2. Check reponse for ChildNotAllowedError
            3. Get the response payload is HAL Complient
        Results:
            ChildNotAllowedError thrown by the REST API.
        """
        # RUN CURL POST
        deployment_path = self.get_path_url(
            "/deployments", "deployment", True)
        stdout, stderr, status = \
            self.restutils.post(deployment_path,
                                "Content-Type:application/json",
                                "{\"id\":\"single-blade2\","
                                "\"type\":\"deployment\"}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False))

        # CHECK THE OUTPUT
        self.assertTrue("ChildNotAllowedError" in stdout,
                        "ChildNotAllowedError message is missing")

    @attr('all', 'revert')
    def obsolete_02_n_check_ExclusiveLinkError_singleblade(self):
        """
        Description:
            Throw ExclusiveLinkError using REST API.
            Test can only be executed on sinagleblade
            with a minimum of 2 managed nodes
            ExclusiveLinkError will be thrown when
            2 nodes link to the same libvirt system
        Actions:
            1. FIND PATH TO LIBVIRT SYSTEMS
            2. ASSERT SYSTEM HAS AT LEAST 2 MANAGED NODES
            3. SAVE LIBVIRT SYSTEM NAMES OF NODE1 AND NODE2
            4. UPDATE NODE1 TO LINK TO NODE2 LIBVIRT SYSTEM NAME
            5. CREATE PLAN
            6. CHECK RESPONSE PAYLOAD IS HAL COMPLIANT
            7. CHECK ERROR THROWN IS ExclusiveLinkError
            8. REVERT CHANGE
        Result:
            ExclusiveLinkError thrown by the REST API at create_plan.
        """
        # FIND PATH TO LIBVIRT SYSTEMS
        libvirt_paths = self.find(
            self.test_node, "/deployments", "libvirt-system", True)

        # ASSERT SYSTEM HAS AT LEAST 2 MANAGED NODES
        self.assertTrue(len(libvirt_paths) > 1, \
            "System must have 2 nodes to proceed")

        # SAVE LIBVIRT SYSTEM NAMES OF NODE1 AND NODE2
        libvirt_sys1 = libvirt_paths[0]
        libvirt_sys2 = libvirt_paths[1]
        prop_sys1 = self.get_props_from_url(
            self.test_node, libvirt_sys1, "system_name")
        prop_sys2 = self.get_props_from_url(
            self.test_node, libvirt_sys2, "system_name")

        # UPDATE NODE1 TO LINK TO NODE2 LIBVIRT SYSTEM NAME
        message_data = """
            {"properties": {"system_name" : "%s"}}
        """ % prop_sys2
        stdout, stderr, status = self.restutils.put(
            libvirt_sys1, self.restutils.HEADER_JSON, data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

        # CREATE PLAN
        message_data = "{\"id\": \"plan\"," \
                       "\"type\": \"plan\"}"
        stdout, stderr, status = self.restutils.post("/plans", \
                              self.restutils.HEADER_JSON, message_data)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertNotEqual("", stdout)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False))

        # CHECK ERROR THROWN IS ExclusiveLinkError
        self.assertTrue("ExclusiveLinkError" in stdout,
                        "ExclusiveLinkError message is missing")

        # REVERT CHANGE
        message_data = """
            {"properties": {"system_name" : "%s"}}
        """ % prop_sys1
        stdout, stderr, status = self.restutils.put(
            libvirt_sys1, self.restutils.HEADER_JSON, data=message_data)
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(200, status)

    @attr('all', 'revert')
    def test_03_n_check_InvalidRequestError(self):
        """
        Description:
            Throw InvalidRequestError using REST API.
        Actions:
            1. Run curl "POST" command to attempt to throw InvalidRequestError
            2. Check reponse for InvalidRequestError
            3. Get the response payload is HAL Complient
        Results:
            InvalidRequestError thrown by the REST API.
        """
        # RUN CURL POST WITH MISSING BRACKET
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"test351\","
                                "\"type\":\"os-prof\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/profiles/node-iso/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel6\"}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False))

        # CHECK THE OUTPUT
        self.assertTrue("InvalidRequestError" in stdout,
                        "InvalidRequestError message is missing")

    @attr('all', 'revert')
    def test_04_n_check_InvalidPropertyError(self):
        """
        Description:
            Throw ValidationError using REST API.
        Actions:
            1. Run curl "POST" command to attempt to throw ValidationError
            2. Check reponse for ValidationError
            3. Get the response payload is HAL Complient
        Results:
            ValidationError thrown by the REST API.
        """
        # RUN CURL POST
        stdout, stderr, status = \
            self.restutils.post(self.profile_path,
                                "Content-Type:application/json",
                                "{\"id\":\"s%%adgu\","
                                "\"type\":\"os-profile\","
                                "\"properties\":"
                                "{\"name\":\"sample-profile\","
                                "\"breed\": \"redhat\","
                                "\"path\": \"/profiles/node-iso/\","
                                "\"arch\": \"x86_64\","
                                "\"kopts_post\": \"console=ttyS0,115200\","
                                "\"version\":\"rhel6\"}}")
        self.assertNotEqual("", stdout)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)

        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False))

        # CHECK THE OUTPUT
        self.assertTrue("ValidationError" in stdout,
                        "ValidationError message is missing")

        self.assertTrue("Invalid value for item id" in stdout)

    @attr('all', 'revert')
    def obsolete_05_n_check_ValidationError_singleblade(self):
        """
        Description:
            Throw ValidationError using REST API.
        Actions:
            1. Run curl "POST" command to attempt to throw ValidationError
            2. Check reponse for ValidationError
            3. Get the response payload is HAL Complient
        Results:
            ValidationError thrown by the REST API.
        """
        # RUN CURL PUT
        network_paths = self.find(
            self.test_node, "/infrastructure", "network", True)

        for item in network_paths:
            props = self.get_props_from_url(
                self.test_node, item, "default_gateway")
            if props == "true":
                default_network_url = item
                break

        self.update_default_gateway(default_network_url, "false")

        # Create plan
        message_data = "{\"id\": \"plan\"," \
                       "\"type\": \"plan\"}"
        stdout, stderr, status = self.restutils.post(
            "/plans", self.restutils.HEADER_JSON, message_data)
        self.assertEqual("", stderr)
        self.assertEqual(422, status)
        self.assertNotEqual("", stdout)
        # CHECK RESPONSE PAYLOAD IS HAL COMPLIENT
        self.assertTrue(self.json.is_json_hal_complient(
            json_output=stdout, has_children=False, has_props=False))

        # CHECK THE OUTPUT
        self.assertTrue("ValidationError" in stdout,
                        "ValidationError message is missing")

        # UNDO UPDATE
        self.update_default_gateway(default_network_url, "true")
