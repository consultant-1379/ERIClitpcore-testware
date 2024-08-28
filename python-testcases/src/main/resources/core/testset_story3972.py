#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2014
@author:    Priyanka/Maria
@summary:   As a LITP User I want a type for collections,
            so that I can uniquely identify collections in the XML format
            Agile: STORY LITPCDS-3972
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from xml_utils import XMLUtils
import os


class Story3972(GenericTest):

    '''
        As a LITP User I want a type for collections,
        so that I can uniquely identify collections in the XML format
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
        super(Story3972, self).setUp()
        self.test_node = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.xml = XMLUtils()

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
        super(Story3972, self).tearDown()

    def _get_route_path(self):
        """ Returns route path"""

        return self.find(self.test_node, "/deployments",
                         "ref-collection-of-route-base", True)[0]

    def _get_cluster_path(self):
        """ Returns clusters path"""

        return self.find_children_of_collect(self.test_node,
                        "/deployments", "cluster")[0]

    def _get_cluster_collection_path(self):
        """ Returns cluster path"""

        return self.find(self.test_node,
                         "/deployments",
                         "cluster", False)[0]

    def _get_network_path(self):
        """ Returns network path"""

        return self.find(self.test_node,
                         "/deployments",
                         "collection-of-network-interface", True)[0]

    def _log_non_applied_items(self):
        """log any non applied items in the model for debug on test failure"""
        print 'checking paths...'
        model_paths = list()
        if not self.is_all_applied(self.test_node):
            print 'got here...'
            stdout, stderr, rcode = self.execute_cli_show_cmd(
                self.test_node, '/', '-r'
            )
            self.assertEqual(0, rcode)
            self.assertEqual([], stderr)
            self.assertNotEqual([], stdout)
            for line in stdout:
                if line.startswith('/'):
                    model_paths.append(line)
            model_paths[:] = [
                path for path in model_paths if not path.startswith('/plans')
            ]
            model_paths[:] = [
                path for path in model_paths if not path.startswith('/litp')
            ]
        for path in model_paths:
            if self.get_item_state(self.test_node, path) != 'Applied':
                self.log(
                    'error', 'Item not in Applied state: {0}'.format(path)
                )

    def _export_import_collection(self, export_path, load_path):
        """
        Description:
        Method that export and load collection using both
        --merge and --replace arguments and checks that the
        state is "Applied"
        """
        # Execute the export command
        self.execute_cli_export_cmd(
            self.test_node, export_path, "xml_export_load_coll_story3972.xml")

        # Load the exported xml file using the litp load command
        # with the --merge argument
        self.execute_cli_load_cmd(
            self.test_node, load_path,
            "xml_export_load_coll_story3972.xml", "--merge")

        # check the state of all items in the model
        self._log_non_applied_items()
        self.assertTrue(self.is_all_applied(self.test_node))

        # Load the exported xml file using the litp load command
        # with the --replace argument
        self.execute_cli_load_cmd(
            self.test_node, load_path,
            "xml_export_load_coll_story3972.xml", "--replace")

        # check the state of all items in the model
        self._log_non_applied_items()
        self.assertTrue(self.is_all_applied(self.test_node))

    def _copy_xml_file_onto_MS(self, xml_filename):
        """
        Description:
        Method tocopy an xml file onto the MS
        """
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + xml_filename
        xml_filepath = "/tmp/" + xml_filename
        self.copy_file_to(
            self.test_node, local_xml_filepath, xml_filepath)

        return xml_filepath

    @attr('all', 'revert' 'story3972', 'story3972_tc01', 'cdb_priority1')
    def test_01_p_export_cluster_software_collections(self):
        """
        Description:
        Verify that collections can be uniquely identified when loading XML
        Attempt to export and load a cluster software collection
        Bug: LITPCDS-3742

        Actions:
        1. Find the cluster software path
        2. Export the cluster software collection
        3. Load the exported xml file using the litp load command
           with the --merge argument
        4. Check the state of the loaded cluster software collection
        5. Load the exported xml file using the litp load command
           with the --replace argument
        6. Check the state of the loaded cluster software collection

        Result:
        Successful export and load of software collection

        """
        # Find the cluster path
        cluster_path = self._get_cluster_path()

        software_path = cluster_path + "/software"

        # Call Method to export and load collection using both
        # --merge and --replace arguments and checks that the
        # state is "Applied"
        self._export_import_collection(software_path, cluster_path)

    @attr('all', 'revert', 'story3972', 'story3972_tc02', 'cdb_priority1')
    def test_02_p_check_cluster_collections(self):
        """
        Description:
        Export clusters collection and load at valid path

        Actions:
        1. Export clusters collection
        2. Load the exported xml file into valid path
        3. Check the state of the loaded clusters collection
           using the --merge argument
        4. Load the exported xml file into valid path
           using the --replace argument
        5. Check the state of the loaded clusters collection

        Result:
        Successful export and load of cluster collection

        """
        # Find the cluster path
        clusters_path = self._get_cluster_path()

        # Find the cluster collections path
        cluster_collection_path = self._get_cluster_collection_path()

        # Call Method to export and load collection using both
        # --merge and --replace arguments and checks that the
        # state is "Applied"
        self._export_import_collection(clusters_path, cluster_collection_path)

    @attr('all', 'revert', 'story3972', 'story3972_tc03', 'cdb_priority1')
    def test_03_n_check_export_validation(self):
        """
        Description:
        This test checks Validation
        Actions:
        1. Attempt to export an invalid collection
        Result:
        Export fails with correct validation error

        """
        # Attempt to export an invalid collection
        existing_route_path = self._get_route_path() + "/configs"
        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, existing_route_path,
            "xml_test02_story3972.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError ", stderr))

    @attr('all', 'revert', 'story3972', 'story3972_tc04', 'cdb_priority1')
    def test_04_n_check_merge_validation(self):
        """
        Description:
        This test checks --merge argument Validation

        Actions:
        1. Export routes collection
        2. Attempt to merge exported xml when invalid path given
        3. Attempt to merge exported xml when invalid item is given
        4. Export network collection
        5. Attempt to merge network collection into plans collection
        6. Create a deployment object
        7. Export Created deployment object
        8. Attempt to merge the exported with missing child elements

        Result:
        Load fails with correct validation error

        """
        # Export routes collection
        existing_route_path = self._get_route_path()
        self.execute_cli_export_cmd(
            self.test_node, existing_route_path,
            "xml_test04a_story3972.xml")

        # Attempt to merge exported xml when invalid path given
        existing_invalid_path = self._get_route_path() + "/INVALID_PATH"
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, existing_invalid_path,
            "xml_test04a_story3972.xml", "--merge", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError ", stderr))

        # Attempt to merge exported xml when invalid item given
        existing_clusters_path = self._get_cluster_path()
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, existing_clusters_path,
            "xml_test04a_story3972.xml", "--merge", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError ", stderr))

        # Export network collection
        existing_network_path = self._get_network_path()
        self.execute_cli_export_cmd(
            self.test_node, existing_network_path,
            "xml_test04b_story3972.xml")

        # Attempt to merge network_profile collection into plans collection
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, "/plans", "xml_test04b_story3972.xml",
            "--merge", expect_positive=False)
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        # Create deployment object
        deployment_url = "/deployments/dep3972"
        self.execute_cli_create_cmd(
            self.test_node, deployment_url, "deployment")

        # Export Created deployment object
        self.execute_cli_export_cmd(
            self.test_node, deployment_url, "xml_test04c_story3972.xml")

        # Attempt to merge the exported xml with missing child elements
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, deployment_url, "xml_test04c_story3972.xml",
            "--merge", expect_positive=False)
        self.assertTrue(
            self.is_text_in_list('InvalidXMLError', stderr)
        )
        self.assertTrue(
            self.is_text_in_list('Missing child element', stderr)
        )

    @attr('all', 'revert', 'story3972', 'story3972_tc05', 'cdb_priority1')
    def test_05_n_check_replace_validation(self):
        """
        Description:
        This test checks --replace argument Validation

        Actions:
        1. Export network collection
        2. Attempt to load the exported network collection xml
           into plans collection using the --replace argument
        3. Create a deployment object
        4. Export created deployment object
        5. Attempt to load the exported xml with missing child elements
           using the --replace argument

        Result:
        Load fails with correct validation error

        """
        # Export network collection
        existing_network_path = self._get_network_path()
        self.execute_cli_export_cmd(
            self.test_node, existing_network_path, "xml_test05_story3972.xml")

        # Attempt to load the exported network collection xml
        # into plans collection using the --replace argument
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, "/plans", "xml_test05_story3972.xml",
            "--replace", expect_positive=False)
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        # Create deployment object
        deployment_url = "/deployments/dep3972"
        self.execute_cli_create_cmd(
            self.test_node, deployment_url, "deployment")

        # Export created deployment object
        self.execute_cli_export_cmd(
            self.test_node, deployment_url, "xml_test05_story3972.xml")

        # Attempt to load the exported xml with missing child elements
        # using the --replace argument
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, deployment_url, "xml_test05_story3972.xml",
            "--replace", expect_positive=False)
        self.assertTrue(self.is_text_in_list(
            "InvalidXMLError", stderr),
            "did not get expected error message")

    @attr('all', 'revert', 'story3972', 'story3972_tc06')
    def test_06_n_min_occurs_and_max_occurs_validation(self):
        """
        Description:
        Verify MinOccurs and MaxOccurs are validated

        Actions:
        1.Copy xml file onto MS which
          contains a duplicate collection
        2.Load the xml file into a valid path
        3.Check the correct validation error
        4.Copy xml file onto MS which
          contains < min number of collections
        5.load xml file into a valid path
        6.Check the correct validation error
        7.Copy xml file onto MS which
          contains > max number of collections
        8.load xml file into a valid path
        9.Check the correct validation error

        Result:
        fails with correct validation error
        """

        # Copy xml file onto MS which
        # contains a duplicate collection
        xml_filename1 = "xml_same_collection.xml"
        xml_filepath1 = self._copy_xml_file_onto_MS(xml_filename1)

        # Load the xml file into a valid path
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, "/software",
            xml_filepath1, expect_positive=False)

        # Check the correct validation error
        errmsg = (
            "InvalidXMLError    This element is not expected")
#        errmsg = ("InvalidXMLError Element "
#                  "'software-profiles-collection': "
#                  "This element is not expected")
        self.assertTrue(self.is_text_in_list(errmsg, stderr))

        # Copy xml file onto MS which
        # contains < min number of collections
        xml_filename2 = "xml_min_occurs_cluster.xml"
        xml_filepath2 = self._copy_xml_file_onto_MS(xml_filename2)

        # load xml file into a vallid path
        cluster_collection_path = self._get_cluster_collection_path()
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, cluster_collection_path,
            xml_filepath2, expect_positive=False)

        # Check correct validation error
        self.assertTrue(self.is_text_in_list('InvalidXMLError', stderr))
        self.assertTrue(self.is_text_in_list('Missing child element', stderr))

        # Copy xml file onto MS which
        # contains > max number of collections
        xml_filename3 = "xml_max_occurs_cluster.xml"
        xml_filepath3 = self._copy_xml_file_onto_MS(xml_filename3)

        # load xml file into a valid path
        cluster_collection_path = self._get_cluster_collection_path()
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, cluster_collection_path,
            xml_filepath3, expect_positive=False)

        # Check correct validation error
        self.assertTrue(self.is_text_in_list('InvalidXMLError', stderr))
