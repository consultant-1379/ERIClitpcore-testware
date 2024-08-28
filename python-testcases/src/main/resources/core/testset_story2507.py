#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     April 2014
@author:    Maria
@summary:   Integration test for import with --replace argument
            Agile: STORY LITPCDS-2507
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from xml_utils import XMLUtils
import os
import test_constants


class Story2507(GenericTest):

    '''
    As a LITP administrator I want to be able to import an XML file into an
    existing model so that I can replace the existing model
    with the contents of the file
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
        super(Story2507, self).setUp()
        self.test_node = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.xml = XMLUtils()
        self.profile_type = "os-profile"
        self.plugin_id = 'story2240'

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
        super(Story2507, self).tearDown()

    @staticmethod
    def get_local_rpm_paths(path, rpm_substring):
        """
        given a path (which should contain some RPMs) and a substring
        which is present in the RPM names you want, return a list of
        absolute paths to the RPMS that are local to your test
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_substring in rpm]

        if not rpm_names:
            return None

        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
        ]

    def _install_item_extension(self, plugin_id):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """
        _, _, rcode = self.run_command(
            self.test_node,
            self.rhc.check_pkg_installed([plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'plugins')), plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.test_node, local_rpm_paths
                )
            )

    def create_lock(self, lock_file):
        """create lock file that'll keep a task from succeeding"""
        self.run_command(self.test_node, "touch {0}".format(lock_file))

    def release_lock(self, lock_file):
        """remove lock file that keeps a task from succeeding"""
        self.run_command(self.test_node, "rm -f {0}".format(lock_file))

    def get_ms_node(self):
        """what says on the tin"""
        return self.find(self.test_node, '/', 'ms')[0]

    def create_ms_config_item(self, item_id):
        """create test items; their type extends node-config base type"""
        ms_ = self.get_ms_node()
        path = '{0}/configs/{1}'.format(ms_, item_id)
        _, _, rcode = self.execute_cli_create_cmd(self.test_node, path,
                                                  "story2240-node-config")
        if rcode == 0:
            return path

    def _get_profiles_path(self):
        """ Returns os profiles path"""

        return self.find(self.test_node,
                         "/software", "os-profile", True)[0]

    def _get_profile_path(self):
        """ Returns os profiles path"""

        return self.find(self.test_node,
                         "/software", "profile", False)[0]

    def _get_node_path(self):
        """ Returns nodes path"""

        return self.find(self.test_node,
                         "/deployments", "node", True)[0]

    def _get_ip_range_path(self):
        """ Returns ip-range path"""

        return self.find(self.test_node,
                         "/deployments", "reference-to-ip-range", True)[0]

    def _get_ip_range_coll_path(self):
        """ Returns ip-range path"""

        return self.find(self.test_node,
                         "/deployments", "ref-collection-of-ip-range",
                         True)[0]

    def _get_storage_profile_path(self):
        """ Returns storage_profile path"""

        return self.find(self.test_node,
                         "/deployments",
                         "reference-to-storage-profile", True)[0]

    def get_software_node(self):
        """what says on the tin"""
        return self.find(self.test_node, "/", "software")[0]

    def create_source_and_inherited_items(self, source_id, inherited_id):
        """create test item of story2507-software-item type
        and it's reference under /ms/items"""
        ms_ = self.get_ms_node()
        soft = self.get_software_node()
        source_item_path = '{0}/items/{1}'.format(soft, source_id)
        inherited_item_path = '{0}/items/{1}'.format(ms_, inherited_id)
        self.execute_cli_create_cmd(
            self.test_node, source_item_path, "story2507-software-item")

        self.execute_cli_inherit_cmd(
            self.test_node, inherited_item_path, source_item_path)

        return source_item_path, inherited_item_path

    @attr('all', 'revert', 'tooltest')
    def test_02_p_load_replace_scenario1_3(self):
        """
        Description:
        GIVEN a valid XML file with a clusterZ nodeX AND the model contains
        clusterZ with nodeX and nodeY
        WHEN I load the file with --replace
        THEN merge continues for nodeX and nodeY is removed

        Actions:
        1. Create cluster_story2507 in the model containing node_story2507_1,
           node_story2507_2 and node_story2507_3
        2. Load --replace using an xml file containing cluster_story2507,
           node_story2507_1 with the same properties
           and node_story2507_3 with different properties
           (some new, some updated)

        Result:
        cluster_story2507, node_story2507_1 has been replaced, node_story2507_2
        is removed and node_story2507_3 has been updated with new properties
        """
        # Find cluster path
        cluster_path = self.find(
            self.test_node, "/deployments", "cluster", False)[0]

        # Save number of clusters, managed nodes on that
        # cluster and systeims
        clusters = self.find_children_of_collect(
            self.test_node, "/deployments", "cluster")
        orig_number_clusters = len(clusters)

        nodes = self.find(self.test_node, "/deployments", "node", True)
        orig_number_nodes = len(nodes)

        sys_pros = self.find(
            self.test_node, "/infrastructure", "blade", True)
        orig_sys_pros = len(sys_pros)

        try:
            # Copy XML files onto node
            xml_filename1 = "/xml_cZ_nX_nY_nZ_story2507.xml"
            xml_filename2 = "/xml_cZ_nX_nZ_story2507.xml"
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath1 = local_filepath + "/xml_files" + xml_filename1
            xml_filepath1 = "/tmp" + xml_filename1
            local_xml_filepath2 = local_filepath + "/xml_files" + xml_filename2
            xml_filepath2 = "/tmp" + xml_filename2
            self.assertTrue(self.copy_file_to(
                self.test_node, local_xml_filepath1, xml_filepath1))
            self.assertTrue(self.copy_file_to(
                self.test_node, local_xml_filepath2, xml_filepath2))

            # load xml so that model contains clusterZ with nodeX and nodeY
            self.execute_cli_load_cmd(
                self.test_node, "/", xml_filepath1, args="--merge")

            # Compare number of clusters, managed nodes
            # and systems after initial load
            clusters = self.find_children_of_collect(
                        self.test_node, "/deployments", "cluster")
            self.assertEqual(orig_number_clusters + 1, len(clusters))

            nodes = self.find(self.test_node, "/deployments", "node", True)
            self.assertEqual(orig_number_nodes + 3, len(nodes))

            sys_pros = self.find(
                self.test_node, "/infrastructure", "blade", True)
            self.assertEqual(orig_sys_pros + 3, len(sys_pros))

            # load xml file containing clusterZ with nodeX using --replace
            self.execute_cli_load_cmd(
                self.test_node, cluster_path, xml_filepath2, args="--replace")

            # Check nodeY has been removed
            nodes = self.find(
                self.test_node, "/deployments", "node", True)
            self.assertEqual(orig_number_nodes + 2, len(nodes))

            # Check properties of imported nodeX
            for item in nodes:
                if "node1_story2507" in item:
                    node1_url = item
                    props = self.get_props_from_url(
                        self.test_node, node1_url, "hostname")
                    self.assertEqual("node1", props)
                    system_url = node1_url + "/system"
                    props = self.get_props_from_url(
                        self.test_node, system_url, "system_name")
                    self.assertEqual("CZ2507STORY1", props)

                # Check that the address property has been updated
                # when the xml was loaded
                elif "node3_story2507" in item:
                    node3_url = item
                    node3_ip_url = self.find(self.test_node, node3_url, \
                        "eth", True)[0]
                    props = self.get_props_from_url(
                        self.test_node, node3_ip_url, "ipaddress")
                    self.assertEqual("10.10.10.104", props)

            # Check validation errors at create_plan
            #_, stderr, _ = self.execute_cli_createplan_cmd(
            #    self.test_node, expect_positive=False)
            #self.assertTrue(self.is_text_in_list("UnresolvedLinkError", \
            #    stderr), "Expected UnresolvedLinkError")

        finally:
            # Remove imported items
            # Define list
            del_rm_list = []
            root_url, _, _ = self.execute_cli_show_cmd(
                self.test_node, "/", args='-rl')
            for url in root_url:
                if "story2507" in url:
                    del_rm_list.append(self.cli.get_remove_cmd(url))

            self.run_commands(self.test_node, del_rm_list)

            #ENSURE CREATE_PLAN DOES NOT CREATE A PLAN
            # AS MODEL IS IN SAME STATE AS BEFORE EXPORT
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.test_node, expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "DoNothingPlanError", stderr), "Expected DoNothingPlanError")

    @attr('all', 'revert', 'tooltest')
    def test_03_p_load_replace_scenario2(self):
        """
        Description:
        GIVEN a valid XML file with a clusterZ nodeX AND the model contains
        clusterZ with nodeY
        WHEN I load the file with --replace
        THEN nodeX is created and nodeY is for removal

        Actions:
        1. Create cluster_story2507 in the model containing node_story2507_1
        2. Load --replace using an xml file containing cluster_story2507,
           node_story2507_2

        Result:
        cluster_story2507, node_story2507_1 is removed.
        node_story2507_2 is created in the model
        """
        # Find cluster path
        cluster_path = self.find(
            self.test_node, "/deployments", "cluster", False)[0]

        # Save number of clusters, managed nodes on that
        # cluster and systems
        clusters = self.find_children_of_collect(
                    self.test_node, "/deployments", "cluster")
        orig_number_clusters = len(clusters)

        nodes = self.find(self.test_node, "/deployments", "node", True)
        orig_number_nodes = len(nodes)

        sys_pros = self.find(
            self.test_node, "/infrastructure", "blade", True)
        orig_sys_pros = len(sys_pros)

        try:
            # Copy XML files onto node
            xml_filename1 = "/xml_cZ_nX_story2507.xml"
            xml_filename2 = "/xml_cZ_nY_story2507.xml"
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath1 = local_filepath + "/xml_files" + xml_filename1
            xml_filepath1 = "/tmp" + xml_filename1
            local_xml_filepath2 = local_filepath + "/xml_files" + xml_filename2
            xml_filepath2 = "/tmp" + xml_filename2
            self.assertTrue(self.copy_file_to(
                self.test_node, local_xml_filepath1, xml_filepath1))
            self.assertTrue(self.copy_file_to(
                self.test_node, local_xml_filepath2, xml_filepath2))

            # Create items that are inherited by imported node
            storage_url = self.find(
                self.test_node, "/infrastructure",
                "storage-profile-base", False)

            storage_profile_url = storage_url[0] + "/profile_story2507"
            self.execute_cli_create_cmd(
                self.test_node, storage_profile_url,
                "storage-profile")

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

            system_url = self.find(
                self.test_node, "/infrastructure",
                "collection-of-system", True)[0]
            sys_url = system_url + "/story2507_sys1"
            self.execute_cli_create_cmd(
                self.test_node, sys_url, "blade", "system_name='STORY2507'")

            # load xml so that model contains clusterZ with nodeX
            self.execute_cli_load_cmd(
                self.test_node, cluster_path, xml_filepath1, args="--merge")

            # Compare number of clusters, managed nodes
            # and systems after initial load
            clusters = self.find_children_of_collect(
                        self.test_node, "/deployments", "cluster")
            self.assertEqual(orig_number_clusters + 1, len(clusters))

            nodes = self.find(self.test_node, "/deployments", "node", True)
            self.assertEqual(orig_number_nodes + 1, len(nodes))

            sys_pros = self.find(
                self.test_node, "/infrastructure", "blade", True)
            self.assertEqual(orig_sys_pros + 1, len(sys_pros))

            # load xml file containing clusterZ with nodeY using --replace
            self.execute_cli_load_cmd(
                self.test_node, cluster_path, xml_filepath2, args="--replace")

            # Check nodeY has been removed
            nodes = self.find(
                self.test_node, "/deployments", "node", True)
            self.assertEqual(orig_number_nodes + 1, len(nodes))

            # Check properties of imported nodeX
            for item in nodes:
                if "node2_story2507" in item:
                    node2_url = item
                    props = self.get_props_from_url(
                        self.test_node, node2_url, "hostname")
                    self.assertEqual("node2", props)
                self.assertFalse("node1_story2507" in item)

        finally:
            # Remove imported items
            # Define list
            del_rm_list = []
            root_url, _, _ = self.execute_cli_show_cmd(
                self.test_node, "/", args='-rl')
            for url in root_url:
                if "story2507" in url:
                    del_rm_list.append(self.cli.get_remove_cmd(url))

            self.run_commands(self.test_node, del_rm_list)

            #ENSURE CREATE_PLAN DOES NOT CREATE A PLAN
            # AS MODEL IS IN SAME STATE AS BEFORE EXPORT
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.test_node, expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "DoNothingPlanError", stderr), "Expected DoNothingPlanError")

    @attr('all', 'revert', 'tooltest')
    def test_04_n_load_replace_merge(self):
        """
        Description:
        This test attempts to use the
        --merge and --replace optional parameters together

        Actions:
        1. Export an item
        2. Attempt to load the exported xml file
           using the following command:
           litp load -p /path/to/item/ -f /path/to/exported/xml/file
           --merge --replace
        3. Attempt to load the exported xml file
           using the following command:
           litp load -p /path/to/item/ -f /path/to/exported/xml/file
           --replace --merge
        Result:
        Import using --replace and --merge fails
        and appropriate error given to user
        """
        # Test Attributes
        error1 = "argument --replace: not allowed with argument --merge"
        error2 = "argument --merge: not allowed with argument --replace"

        # 1. Export the existing profile model item
        existing_node_path = self._get_node_path()

        node_xml_file = "xml_test04_story2507.xml"
        self.execute_cli_export_cmd(
            self.test_node, existing_node_path, filepath=node_xml_file)

        # 2. Load the exported xml with the merge and replace arguments
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, existing_node_path, node_xml_file, \
            args="--merge --replace", expect_positive=False)
        self.assertEqual([], stdout)
        self.assertTrue(self.is_text_in_list(error1, stderr),
            "did not get expected error message")
        self.assertEqual(2, errorcode)

        # 2. Load the exported xml with the replace and merge arguments
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, existing_node_path, node_xml_file, \
            args="--replace --merge", expect_positive=False)
        self.assertEqual([], stdout)
        self.assertTrue(self.is_text_in_list(error2, stderr),
            "did not get expected error message")
        self.assertEqual(2, errorcode)

    @attr('all', 'revert', 'tooltest')
    def test_05_n_load_replace_while_plan_running(self):
        """
        Description:
        This test attempts to load a XML file while a plan is running

        Actions:
        1. Make changes to the model
        2. Create plan
        3. run plan
        4. execute litp load command using --replace option

        Result:
        Load using --replace fails while plan is running
        """

        # reuse plugin from another test suite
        self._install_item_extension('story2240')

        lock_item = "story2507_05_lock"
        lock_path = "/tmp/" + lock_item
        try:
            # create config item
            path = self.create_ms_config_item(lock_item)
            # export created item to xml file
            self.execute_cli_export_cmd(
                self.test_node, path, "xml_test05_story2507.xml"
            )
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.test_node)
             # create lock file that's checked by callback task
            self.create_lock(lock_path)
            # execute the run_plan command
            self.execute_cli_runplan_cmd(self.test_node)
            self.assertTrue(self.wait_for_plan_state(self.test_node,
                                    test_constants.PLAN_IN_PROGRESS))
            # Execute litp load command with --replace argument
            errmsg = "Operation not allowed while plan is running/stopping"
            stdout, stderr, errorcode = self.execute_cli_load_cmd(
                self.test_node, path, "xml_test05_story2507.xml", \
                args="--replace", expect_positive=False)
            self.assertEqual([], stdout)
            self.assertTrue(self.is_text_in_list("InvalidRequestError", \
                stderr), "did not get expected error message")
            self.assertTrue(self.is_text_in_list(errmsg, \
                            stderr), "did not get expected error message")
            self.assertEqual(1, errorcode)

        finally:
            self.release_lock(lock_path)

    @attr('all', 'revert', 'tooltest')
    def test_06_n_load_replace_empty_branch(self):
        """
        Description:
        This test attempts to execute the litp load command with
        --replace argument on an empty branch of the model

        Actions:
        1. Create an empty branch by creating a cluster
        2. Copy an xml file onto the MS that can be loaded into
           the nodes branch of the cluster branch
        3. load xml file using --replace into an empty branch
           of the created cluster

        Result:
        Xml file successfully loaded
        """
        # Find the cluster path
        cluster_path = self.find(
            self.test_node, "/deployments", "cluster", False)[0]

        # Create an empty cluster
        cluster_item_path = cluster_path + "/story2507_c1"
        self.execute_cli_create_cmd(
            self.test_node, cluster_item_path, "cluster")

        # Copy file onto MS
        xml_filename = "xml_test06_story2507.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" + xml_filename
        xml_filepath = "/tmp/" + xml_filename
        self.assertTrue(self.copy_file_to(
            self.test_node, local_xml_filepath, xml_filepath))

        try:
            # Find the created cluster nodes path
            nodes_path = self.find(
                self.test_node, "/deployments", "node", False)

            for item in nodes_path:
                if "story2507" in item:
                    # Load the xml file using the --replace argument
                    # onto the empty path
                    self.execute_cli_load_cmd(
                        self.test_node, item, xml_filepath, "--replace")

                    # Execute a show on the loaded item
                    self.execute_cli_show_cmd(self.test_node, item)

        finally:
            # Delete the imported item (will cleanup do this?)
            self.execute_cli_remove_cmd(self.test_node, cluster_item_path)

    @attr('all', 'revert', 'tooltest')
    def test_07_p_load_replace_root(self):
        """
        Description:
        load entire model xml into an exisitng model using the replace argument

        Actions:
        1. Export from / to foo.xml
        2. load -p / --replace -f foo.xml
        3. Check state of items in tree
        4. Create plan
        5. Create an item in the model that
           will not exist in the xml file
        6. Load the exported xml file using
           the litp load command
           with the --replace argument
        7. Check state of items in tree
        8. Create plan

        Results:
        Load is successful and create plan does not create a plan
        affirming that the model is the same as it was before the load
        """
        # Export / using the litp export command
        self.execute_cli_export_cmd(
            self.test_node, "/", "xml_test07_story2507.xml")

        # Load the exported xml file using the litp load command
        # with the --replace argument
        self.execute_cli_load_cmd(
            self.test_node, "/", "xml_test07_story2507.xml", "--replace")

        # check the state of all items in the model
        self.assertTrue(self.is_all_applied(self.test_node))

        # Create plan to ensure model has not changed when --replace used
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False)
        self.assertTrue(self.is_text_in_list("DoNothingPlanError ", stderr))

        # Create an item in the model that will not exist in the xml file
        # Find the cluster path
        cluster_path = self.find(
            self.test_node, "/deployments", "cluster", False)[0]

        # Create an empty cluster
        cluster_item_path = cluster_path + "/story2507_c1"
        self.execute_cli_create_cmd(
            self.test_node, cluster_item_path, "cluster")

        # Load the exported xml file using the litp load command
        # with the --replace argument
        self.execute_cli_load_cmd(
            self.test_node, "/", "xml_test07_story2507.xml", "--replace")

        # Show will fail as item has been removed from tree
        _, stderr, _ = self.execute_cli_show_cmd(
            self.test_node, cluster_item_path, expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError ", stderr))

        # check the state of all items in the model
        self.assertTrue(self.is_all_applied(self.test_node))

        # Create plan to ensure model has not changed when --replace used
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False)
        self.assertTrue(self.is_text_in_list("DoNothingPlanError ", stderr))

    @attr('all', 'revert', 'tooltest')
    def test_08_n_load_replace_incorrect_collection(self):
        """
        Description:
        Attempt to load --replace a valid collection into an
        invalid location that is of type collection and non-collection

        Actions:
        1. Export profiles collection to a file xml_test08_story2507.xml
        2. load the exported profiles collection into ip-range collection
           path using the --replace argument

        Results:
        Replace fails with correct validation error: InvalidChildTypeError
        """

        # EXPORT /SOFTWARE/PROFILES USING LITP EXPORT COMMAND
        self.execute_cli_export_cmd(self.test_node, self._get_profile_path(),
                                    "xml_test08_story2507.xml")

        # IMPORT EXPORTED FILE USING LITP LOAD COMMAND WITH REPLACE FLAG
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, self._get_storage_profile_path(), \
            "xml_test08_story2507.xml", args="--replace", \
            expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr))

        # IMPORT COLLECTION INTO A NON-COLLECTION TYPE
        # Find items_path = self.find(
        items_path = self.find(self.test_node, "/software", "ntp-service")[0]
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, items_path, \
            "xml_test08_story2507.xml", args="--replace", \
            expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr))

    # WARNING Do not add this test to CDB as the tests there may fall over if
    # they find the undocumented test item type that is used by the tc

    @attr('all', 'non-revert', 'tooltest')
    def test_09_n_load_replace_item_type_marked_ForRemoval(self):
        """
        Description:
        Attempt to load a model item using the --replace argument
        when that item has been marked for removal

        Actions:
        1. Create a software-item in the model and inherit it in ms
        2. Create plan
        3. Run plan
        4. Wait for plan ot complete
        5. Export source model item
        7. Remove the existing source model item and inherited model item
           (Mark ForRemoval)
        8. Import the existing source model item with the replace argument
        9. Check state of both model items
        10. Import an xml file containing an update to the source model item
            item with the replace argument
        11. Check state of package item-type

        Results:
        Import successful, item marked "ForRemoval" recreates and updated
        """
        self._install_item_extension('story2507')

        source_item = "story2507_tc09_source"
        inherited_item = "story2507_tc09_inherited"

        # create source story2507-software-item in /software/items and then
        # inherited item in /ms/items
        (source_item_path,
            inherited_item_path) = self.create_source_and_inherited_items(
                source_item, inherited_item)
        try:
            # CREATE PLAN
            self.execute_cli_createplan_cmd(self.test_node)

            # SHOW PLAN FOR DEBUGGING
            # self.execute_cli_showplan_cmd(self.test_node)

            # RUN PLAN
            self.execute_cli_runplan_cmd(self.test_node)

            # WAIT FOR PLAN TO COMPLETE
            plan_state = self.wait_for_plan_state(
                self.test_node, test_constants.PLAN_COMPLETE)
            self.assertTrue(plan_state, "Adding story2507-software-item on ms "
                            "not completed successfully")

            # Export the source model item
            self.execute_cli_export_cmd(
                self.test_node, source_item_path, "xml_test09_story2507.xml")

            # Delete the existing package model item
            self.execute_cli_remove_cmd(self.test_node, inherited_item_path)
            self.execute_cli_remove_cmd(self.test_node, source_item_path)

            # find the 'state' value of the returned package item
            get_data_cmd = self.cli.get_show_data_value_cmd(
                source_item_path, "state")
            stdout, stderr, returnc = self.run_command(
                self.test_node, get_data_cmd)
            self.assertEqual([], stderr)
            self.assertEqual(0, returnc)
            stdout = "".join(stdout)
            self.assertEqual("ForRemoval", stdout)
            get_data_cmd = self.cli.get_show_data_value_cmd(
                inherited_item_path, "state")
            stdout, stderr, returnc = self.run_command(
                self.test_node, get_data_cmd)
            self.assertEqual([], stderr)
            self.assertEqual(0, returnc)
            stdout = "".join(stdout)
            self.assertEqual("ForRemoval", stdout)

            # Copy updated packaged XML file to node
            # be careful! the ID of the story2507-software-item has to be equal
            # to source_item value
            item_xml_filename = "xml_test09_package_updated_story2507.xml"
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath = local_filepath + "/xml_files/" \
                + item_xml_filename
            remote_xml_filepath = "/tmp/" + item_xml_filename
            self.assertTrue(self.copy_file_to(
                self.test_node, local_xml_filepath, remote_xml_filepath))

            # Load the model item marked ForRemoval with an xml file
            # in which a property has been updated using the --replace argument
            source_collection = "/software/items"
            self.execute_cli_load_cmd(self.test_node, source_collection,
                                      remote_xml_filepath, args="--replace")

            # find the 'state' value of the source item
            get_data_cmd = self.cli.get_show_data_value_cmd(source_item_path,
                                                            "state")
            stdout, stderr, returnc = self.run_command(self.test_node,
                                                       get_data_cmd)
            self.assertEqual([], stderr)
            self.assertEqual(0, returnc)
            stdout = "".join(stdout)
            self.assertEqual("Updated", stdout)

        finally:
            self.execute_cli_remove_cmd(self.test_node, inherited_item_path)
            self.execute_cli_remove_cmd(self.test_node, source_item_path)

            self.execute_cli_createplan_cmd(self.test_node)
            self.execute_cli_runplan_cmd(self.test_node)
            self.assertTrue(self.wait_for_plan_state(
                self.test_node, test_constants.PLAN_COMPLETE))

    @attr('all', 'revert', 'tooltest')
    def test_10_n_load_replace_anywhere_in_model(self):
        """
        Description:
        load xml into an exisitng model with invalid places

        Actions:
        1. Export profile item to xml_test10_story2507.xml
        2. load xml_test10_story2507.xml using --replace argument
           into different paths in the model

        Results:
        Unsuccessful loads
        """
        # EXPORT PROFILE ITEM USING LITP EXPORT COMMAND
        existing_profile_path = self._get_profiles_path()
        self.execute_cli_export_cmd(
            self.test_node, existing_profile_path, "xml_test10_story2507.xml")

        # Scenario:1
        # IMPORT EXPORTED FILE USING LITP LOAD COMMAND IN NODES
        existing_node_path = self._get_node_path()
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, existing_node_path, \
            "xml_test10_story2507.xml", expect_positive=False)

        # CHECK THE OUTPUT
        self.assertEqual([], stdout)
        self.assertEqual(1, errorcode)
        self.assertTrue(self.is_text_in_list("ChildNotAllowedError", stderr))

        # Scenario:2
        # IMPORT EXPORTED FILE USING LITP LOAD COMMAND IN STORAGE-PROFILE
        existing_storage_path = self._get_storage_profile_path()
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, existing_storage_path, \
            "xml_test10_story2507.xml", expect_positive=False)

        # CHECK THE OUTPUT
        self.assertEqual([], stdout)
        self.assertEqual(1, errorcode)
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        # Scenario:3
        # IMPORT EXPORTED FILE USING LITP LOAD COMMAND IN STORAGE-PROFILE
        existing_storage_profile_path = self._get_storage_profile_path()
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, existing_storage_profile_path, \
            "xml_test10_story2507.xml", expect_positive=False)

        # CHECK THE OUTPUT
        self.assertEqual([], stdout)
        self.assertEqual(1, errorcode)
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

    @attr('all', 'revert', 'tooltest')
    def test_11_n_load_replace_xml_file_validation_errors(self):
        """
        Description:
        Attempt to replace a type: os-profile
        when the xml file containing a item with no id and
        an item with invalid property name

        Actions:
        1. Copy xml file to MS
           File contains:
           os-profile xml file with invalid property name
        2. load profile XML file with replace argument
        3. Copy xml file to MS
           File contains:
           os-profile xml file with no id
        4. load profile XML file with replace argument
        Results:
        loads fail with correct validation error
        """

        # Copy profile XML file containing an invalid property onto node
        profile_xml_filename = "xml_os_profile_invalid_prop_story239.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + profile_xml_filename
        profile_xml_filepath = "/tmp/" + profile_xml_filename
        self.assertTrue(self.copy_file_to(
            self.test_node, local_xml_filepath, profile_xml_filepath))

        # load profile XML file using the replace argument
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, self._get_profiles_path(), profile_xml_filepath, \
            args="--replace", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr), \
            "did not get expected error message")
        self.assertEqual([], stdout)
        self.assertEqual(1, errorcode)

        # Copy profile XML file with a missing id onto node
        profile_xml_filename = "xml_test11_story2507.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + profile_xml_filename
        profile_xml_filepath = "/tmp/" + profile_xml_filename
        self.assertTrue(self.copy_file_to(
            self.test_node, local_xml_filepath, profile_xml_filepath))

        # load the profile XML file using the replace argument
        stdout, stderr, errorcode = self.execute_cli_load_cmd(
            self.test_node, self._get_profiles_path(), profile_xml_filepath, \
            args="--replace", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr), \
        "did not get expected error message")
        self.assertEqual([], stdout)
        self.assertEqual(1, errorcode)

    @attr('all', 'revert', 'tooltest')
    def test_12_n_load_replace_xml_check_links(self):
        """
        Description:
        Test when the "links to" item-type is replaced with
        load --replace, the links are marked "ForRemoval"

        Actions:
        1. Export /infrastructure path
        2. load exported XML file with replace argument
        3. Check links in /deployments path are in
           the correct state
        Results:
        Links are in state "Applied"
        """
        # Store the state of the links in the node1 path
        # Find node1 path
        node1_path = self._get_node_path()
        node_items, _, _ = self.execute_cli_show_cmd(
            self.test_node, node1_path, "-rl")

        orig_values = dict()
        for path in node_items:
            orig_values[path] = self.execute_show_data_cmd(
            self.test_node, node1_path, "state")

        # Export /infrastructure path using the litp export command
        self.execute_cli_export_cmd(
            self.test_node, "/infrastructure", "xml_test12_story2507.xml")

        # Load the exported xml file using the litp load command
        # with the --replace argument
        self.execute_cli_load_cmd(
            self.test_node, "/", "xml_test12_story2507.xml", "--replace")

        # Check links in /deployments path are in
        # the correct state
        for path in node_items:
            self.assertTrue(
                orig_values[path], self.execute_show_data_cmd(
                self.test_node, node1_path, "state"))

        # Create plan to ensure model has not changed when --replace used
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False)
        self.assertTrue(self.is_text_in_list("DoNothingPlanError ", stderr))
