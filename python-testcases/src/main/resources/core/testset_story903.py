'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Decemeber 2013
@author:    Luke Murphy
@summary:   Integration test for model validation framework
            Agile: EPIC-667, STORY-903, Sub-Task: STORY-979
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils


class Story903(GenericTest):
    """As a Plugin Developer I want to register validator methods
        per ItemType so that validation can be perfomed on model
        items at CRUD operations
    """

    def setUp(self):
        """Run before every test"""
        super(Story903, self).setUp()
        self.cli = CLIUtils()
        self.test_node = self.get_management_node_filename()
        self.setup_cmds = []
        self.results = []

    def tearDown(self):
        """run after each test"""
        super(Story903, self).tearDown()

    def get_libvirt_url(self):
        """Gets the libvirt url"""
        return self.find(
            self.test_node, "/infrastructure", "libvirt-provider", True
        )[0]

    def get_node_url(self):
        """Gets the node url """
        return self.find(self.test_node, "/deployments", "node", False)[0]

    def get_item_url(self):
        """Get LITP full item url"""
        # run find command
        return self.find(
            self.test_node, "/software", "software-item", False
        )[0]

    @attr('all', 'revert')
    def obsolete_01_n_validate_errors_singleblade(self):
        """
            Description:
                Assert that a number of validation errors on create commands
                are functioning correctly
            Actions:
                1. get necessary urls using find command calls
                2. create libvirt sys with invalid type
                3. create libvirt sys with invalid property
                4. create libvirt sys with invalid regex
                5. create node with missing mandatory property
                6. create package with missing mandatory property
                7. assert invalid path error
            Results:
                A number of validation errors are proved to be working
        """
        # 1. get necessary urls
        libvirt_url = self.get_libvirt_url()
        node_url = self.get_node_url()
        item_url = self.get_item_url()

        # 2. create libvirt sys with invalid type
        url = libvirt_url + "/systems/vm_903"
        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
                    "invalid-type", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("InvalidTypeError", std_err),
            "InvalidTypeError message missing")

        # 3. create libvirt sys with invalid property
        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
            "libvirt-system", "invalid_property='VM1'", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("PropertyNotAllowedError", std_err),
            "PropertyNotAllowedError message missing")

        # 4. create libvirt sys with invalid regex
        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
               "libvirt-system", "ram='0B'", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("RegexError", std_err),
            "RegexError message missing")

        # 5. create node with missing mandatory property
        url = node_url + "/node903"
        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
               "node", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("MissingRequiredPropertyError", std_err),
            "MissingRequiredPropertyError message missing")

        # 6. create package with missing mandatory property
        url = item_url + "/package903"
        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
         "package", "name=test_package release='9.0.3'", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("InvalidPropertyError", std_err),
            """ invalidPropertyError message missing,
                got {0} instead!""".format(std_err))

        # 7. assert invalid path error
        url = "/invalid_path/system_903"

        _, std_err, _ = self.execute_cli_create_cmd(self.test_node, url, \
         "libvirt-system", expect_positive=False)

        # assert we get correct error message
        self.assertTrue(
            self.is_text_in_list("InvalidLocationError", std_err),
            "InvalidLocationError message missing")

    @attr('all', 'revert')
    def obsolete_02_n_link_prop_and_type_singleblade(self):
        """
            Descriptions:
                Create a libvirt system and a test node. Link with invalid
                property, then check we get an error message
                with PropertyNotAllowedError
            Actions:
                1. get necessary urls
                2. get libvirt create command, append to setup_cmds
                3. get node create command, append to setup_cmds
                4. run commands from 3 + 4 and assert no errors
                5. link libvirt sys with invalid property
                6. run command from step 5, assert errors (invalid prop)
                7. link libvirt sys with invalid type
                8. run command from step 7, assert errors (invalid type)
           Results:
                Failure to link libvirt to system
                with incorrect property and type
        """

        # Fix for Pylint error
        # Comment Obsolete test case and replace with pass statement
        pass

#        # 1. get necessary urls
#        libvirt_url = self.get_libvirt_url()
#        node_url = self.get_node_url()
#
#        # 2. create libvirt system
#        libvirt_sys_url = libvirt_url + "/systems/vm903"
#
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            libvirt_sys_url, "libvirt-system", \
#                "system_name='VM903' ram='4096M'", expect_positive=True)
#
#        # 3. create test node
#        node_903_url = node_url + "/node903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            node_903_url, "node", \
#                "hostname='node903'", expect_positive=True)
#
#        # 5. link libvirt to system with invalid property
#        system_url = node_url + "/node903/system"
#        _, std_err, _ = self.execute_cli_link_cmd(self.test_node, \
#            system_url, "libvirt-system", \
#                "system_name='VM903' invalid_property='VM903'", \
#                    expect_positive=False)
#
#        # check for 'PropertyNotAllowedError' in standard error
#        self.assertTrue(
#            self.is_text_in_list("PropertyNotAllowedError", std_err),
#            "PropertyNotAllowedError message missing")
#
#        # 7. link libvirt to system with invalid type
#        node_system_url = node_url + "/system"
#
#        _, std_err, _ = self.execute_cli_link_cmd(self.test_node, \
#            node_system_url, "os-profile", \
#                "system_name='VM903'", \
#                    expect_positive=False)
#
#        # check for 'InvalidChildTypeError' in standard out
#        self.assertTrue(
#            self.is_text_in_list("InvalidChildTypeError", std_err),
#            "InvalidChildTypeError message missing")

    @attr('all', 'revert')
    def obsolete_03_n_link_invalid_regex_singleblade(self):
        """
            Description:
                Create a libvirt system and a test node. Link with empty
                system name, then check we get an error message with RegexError
            Actions:
                1. get necessary urls
                2. get libvirt create command and append to setup_cmds
                3. get node create command and append to setup_cmds
                4. run commands from 3 + 4 and assert no errors
                5. link libvirt sys with empty system path
                6. run command from step 6, assert expected errors
            Results:
                Failure to link libvirt to system with invalid regex
        """

        # Fix for Pylint error
        # Comment Obsolete test case and replace with pass statement
        pass

#        # 1. find the libvirt1 path
#        libvirt_path = self.get_libvirt_url()
#        node_url = self.get_node_url()
#
#        # 2. get libvirt create command
#        vm_url = libvirt_path + "/systems/vm903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            vm_url, "libvirt-system", \
#                "system_name='VM903' ram='4096M'", expect_positive=True)
#
#        # 3. get node create command
#        node_url = node_url + "/node903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            node_url, "node", \
#                "hostname='node903'", expect_positive=True)
#
#        # 5. link libvirt to empty system path
#        system_url = node_url + "/system"
#        _, std_err, _ = self.execute_cli_link_cmd(self.test_node, \
#            system_url, "libvirt-system", \
#                "system_name=''", \
#                    expect_positive=False)
#
#        # assert RegExError in standard error
#        self.assertTrue(
#            self.is_text_in_list("RegexError", std_err),
#            "RegexError message missing")

    @attr('all', 'revert')
    def obsolete_04_n_link_child_disallowed_singleblade(self):
        """
            Description:
                link system to a node, then check we
                get an error message with ChildNotAllowedError
            Actions:
                1. get necessary urls
                2. get libvirt create command
                3. get node1 create command
                4. run commands from 2, 3 and assert no errors
                5. get libvirt link command
                6. run command and assert expected errors
            Results:
                Failure to link node to libvirt
        """

        # Fix for Pylint error
        # Comment Obsolete test case and replace with pass statement
        pass

#        # 1. find necessary urls
#        libvirt_path = self.get_libvirt_url()
#        full_node_url = self.get_node_url()
#
#        # 2. get libvirt create command
#        vm_url = libvirt_path + "/systems/vm903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            vm_url, "libvirt-system", \
#                "system_name='VM903' ram='4096M'", expect_positive=True)
#
#        # 3. get node create command
#        node1_url = full_node_url + "/node1_test"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            node1_url, "node", \
#                "hostname='node903'", expect_positive=True)
#
#        # 5. get libvirt link command
#        system_url = full_node_url + "/node1_test/system903"
#        _, std_err, _ = self.execute_cli_link_cmd(self.test_node, \
#            system_url, "libvirt-system", expect_positive=False)
#
#        # assert childNotAllowedError in standard error
#        self.assertTrue(
#            self.is_text_in_list("ChildNotAllowedError", std_err),
#            "ChildNotAllowedError message missing")

    @attr('all', 'revert')
    def obsolete_05_n_link_invalid_link_singleblade(self):
        """
            Description:
                Create a libvirt system and 2 test nodes, link same libvirt
                system two times, then check plan creation returns
                with ExclusiveLinkError error message
            Actions:
                1. get libvirt + node urls
                2. create libvirt item in tree
                3. create node1
                    a. link ip to node1
                    b. link os to node1
                4. create node2
                    a. link ip to node2
                    b. link os to node2
                5. link node1 with libvirt
                6. link node2 with libvirt
                7. run commands from previous actions and assert no errors
                8. create plan and assert expected errors
            Results:
                Plan create fails with appropriate error
        """

        # Fix for Pylint error
        # Comment Obsolete test case and replace with pass statement
        pass

#        # 1. find necessary urls
#        libvirt_path = self.get_libvirt_url()
#        full_node_url = self.get_node_url()
#
#        # 2. get libvirt create command
#        vm_url = libvirt_path + "/systems/vm903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            vm_url, "libvirt-system", \
#                "system_name='VM903' ram='4096M'", expect_positive=True)
#
#        # 3. get create node1_903
#        node1_url = full_node_url + "/node1_903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#            node1_url, "node", \
#                "hostname='node903'", expect_positive=True)
#
#        # a. link ip1 with node1
#        ip1_url = node1_url + "/ipaddresses/ip1"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          ip1_url, "ip-range", "network_name='nodes'", expect_positive=True)
#
#        # b. link os1 with node1
#        os1_url = node1_url + "/os"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          os1_url, "os-profile", "name='sample-profile' version='rhel6'", \
#                    expect_positive=True)
#
#        # 4. get node2_903 create command
#        node2_url = full_node_url + "/node2_903"
#        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
#          node2_url, "node", "hostname='node903'", \
#                    expect_positive=True)
#
#        # a. link ip2 with node2
#        ip2_url = node2_url + "/ipaddresses/ip1"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          ip2_url, "ip-range", "network_name='nodes'", \
#                    expect_positive=True)
#
#        # b. link os2 with node2
#        os2_url = node2_url + "/os"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          os2_url, "os-profile", "name='sample-profile' version='rhel6'", \
#                    expect_positive=True)
#
#        # 5. link libvirt system with node1
#        system1_url = node1_url + "/system"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          system1_url, "libvirt-system", "system_name='VM903'", \
#                    expect_positive=True)
#
#        # 6. link libvirt system with node2
#        system2_url = node2_url + "/system"
#        _, _, _ = self.execute_cli_link_cmd(self.test_node, \
#          system2_url, "libvirt-system", "system_name='VM903'", \
#                    expect_positive=True)
#
#        # 8. create plan and assert expected errors
#        _, std_err, _ = self.execute_cli_createplan_cmd(self.test_node, \
#            expect_positive=False)
#
#        # check for 'ExclusiveLinkError' in standard error
#        self.assertTrue(
#            self.is_text_in_list("ExclusiveLinkError", std_err),
#            "ExclusiveLinkError message missing")

    @attr('all', 'revert')
    def obsolete_06_n_update_prop_regex_singleblade(self):
        """
            Description:
                validate that when trying to update some properties,
                we get correct validation errors
            Actions:
                1. get libvirt url
                2. create system named vm903_1
                3. create incorrect properties
                4. for each prop in properties, assert we get the
                   correct error message
                5. create an incorrect property
                6. run update command
                7. assert correct validation error message
            Results:
                Update validation errors are proven to be working
        """
        # 1. get necessary urls
        libvirt_url = self.get_libvirt_url()

        # 1. create valid libvirt system in tree
        libvirt_sys_url = libvirt_url + "/systems/vm903_1"
        _, _, _ = self.execute_cli_create_cmd(self.test_node, \
            libvirt_sys_url, "libvirt-system", \
                "system_name=system", expect_positive=True)

        # 3. create a bunch of incorrect properties
        props = ["ram='XYZ'",
                 "disk_size='n-2452'",
                 "cpus='asdasdas'",
                 "path='NOT_A_PATH'"]

        # 4. test we cannot update these errors
        update_url = libvirt_url + "/systems/" + "vm903_1"
        for prop in props:
            self.log("info", "running update for %s" % prop)
            _, std_err, _ = self.execute_cli_update_cmd(self.test_node, \
                update_url, prop, expect_positive=False)

            self.assertTrue(
                self.is_text_in_list("RegexError", std_err),
                "RegexError message is missing")

        # 5. attempt to update with invalid property
        invalid_prop = "type='gobbeldygook'"
        _, std_err, _ = self.execute_cli_update_cmd(self.test_node, \
            update_url, invalid_prop, expect_positive=False)

        self.assertTrue(
            self.is_text_in_list("PropertyNotAllowed", std_err),
            "PropertyNotAllowed message is missing")
