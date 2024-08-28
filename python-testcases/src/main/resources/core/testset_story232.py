'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     January/February 2014
@author:    Pat Bohan/Maria Varley
@summary:   Integration test for rest API for READ operations
            Agile: STORY LITPCDS-232
'''


from litp_generic_test import GenericTest, attr
from rest_utils import RestUtils
import json
from litp_cli_utils import CLIUtils


class Story232(GenericTest):
    '''
    As a REST Client developer I want to CRUD on execution manager so I can
    create, review and execute a plan through the REST API
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
        super(Story232, self).setUp()
        self.test_nodes = self.get_management_node_filenames()
        self.assertNotEqual([], self.test_nodes)
        self.test_node = self.test_nodes[0]
        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.restutils = RestUtils(self.ms_ip_address)
        self.cli = CLIUtils()

    def tearDown(self):
        """
        Description:
            Runs after every single test
        Actions:
            1. Perform Test Cleanup
            2. Call superclass teardown
        Results:
            Items used in the test are cleaned up and the
        """
        super(Story232, self).tearDown()

    def create_curl_command(self, protocol_str="https", rest_port="9999"):
        """
        Simple function which returns a specific curl
        command given a protocol and port
        Returns:
        Standard output and errorput strings corresponding to the REST
        request output, and HTTP response status
        """
        std_out, std_err, status = \
            self.restutils.request(protocol_str + "://" +\
                   self.ms_ip_address +\
                   ":" +\
                   rest_port +\
                   "/litp/rest/v1/deployments/")
        return std_out, std_err, status

    @attr('all', 'revert', 'story232', 'story232_tc1')
    def test_01_p_read_json_output(self):
        """
        Description:
            This test reads all items in tree and
            Ensures return code is 200
            Output is in json format

        Actions:
            1. Perform a find command under /deployments for a node item
            2. Execute rest command via curl and examine http return code and
               payload format for each node item

        Result:
            Http return code is 200
            Payload is in json format
        """
        # Perform a find command under /deployments for a node item
        node_url = self.find(self.test_node, "/deployments",
            "node", False)

        # Execute rest command via curl and examine http return code and
        # payload format for each node item
        for item in node_url:
            stdout, errorlist, status = self.restutils.get(item)
            self.assertEqual(200, status)
            self.assertEquals("", errorlist)

            try:
                json.loads(stdout)
            except ValueError:
                self.assertFalse(True, \
                    "item didn't return json formatted string")

    @attr('all', 'revert', 'story232', 'story232_tc2')
    def test_02_n_read_url_format(self):
        """
        Description:
            This test will examine the response to invalid REST requests

            Steps:
                1. Incorrect port
                2. Unsupported protocol
                3. Invalid protocol

        Results:
            None of the requests should succeed
        """
        # Incorrect port
        outlist, errorlist, httpcode = \
            self.create_curl_command(rest_port="9998")
        self.assertNotEqual("", errorlist)
        self.assertNotEqual(200, httpcode)
        self.assertEquals("", outlist)

        # Unsupported protocol
        outlist, errorlist, httpcode = \
            self.create_curl_command(protocol_str="http")
        self.assertEquals(400, httpcode)
        self.assertEquals("", errorlist)
        self.assertNotEqual("", outlist)

        # Invalid protocol
        outlist, errorlist, httpcode = \
            self.create_curl_command(protocol_str="htp")
        self.assertNotEqual("", errorlist)
        self.assertNotEqual(200, httpcode)
        self.assertEquals("", outlist)
