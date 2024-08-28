#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     February 2014
@author:    priyanka/Maria
@summary:   Integration test for export and import the current deployment
                 model to an XML file
            Agile: STORY LITPCDS-212 and LITPCDS-239
'''

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from lxml.etree import fromstring
from xml_utils import XMLUtils
import os
import test_constants
from rest_utils import RestUtils
from redhat_cmd_utils import RHCmdUtils


class Story212Story239(GenericTest):

    '''
    As a system admin I want to export and import the current deployment model
    to an XML file(s) so that I can use it as a basis for a future deployment
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
        super(Story212Story239, self).setUp()
        self.test_node = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.xml = XMLUtils()
        self.rhc = RHCmdUtils()
        self.ms_ip_address = self.get_node_att(self.test_node, 'ipv4')
        self.rest = RestUtils(self.ms_ip_address)
        self.profile_type = "os-profile"
        self.plugin_id = 'story2240'  # reuses plugin from another testsuite

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
        super(Story212Story239, self).tearDown()

    def get_ms_node(self):
        """what says on the tin"""
        return self.find(self.test_node, '/', 'ms')[0]

    def create_ms_config_item(self, item_id):
        """create test items; their type extends node-config base type"""
        ms_ = self.get_ms_node()
        path = '{0}/configs/{1}'.format(ms_, item_id)
        _, _, rcode = self.execute_cli_create_cmd(self.test_node, path,
                                                  "story2240-node-config",
                                                  "name='initial_name'")
        if rcode == 0:
            return path

    def update_ms_config_item(self, item_id, name):
        """create test items; their type extends node-config base type"""
        ms_ = self.get_ms_node()
        path = '{0}/configs/{1}'.format(ms_, item_id)
        self.execute_cli_update_cmd(self.test_node, path,
                "name='{0}'".format(name))

    def create_lock(self, lock_file):
        """create lock file that'll keep a task from succeeding"""
        self.run_command(self.test_node, "touch {0}".format(lock_file))

    def release_lock(self, lock_file):
        """remove lock file that keeps a task from succeeding"""
        self.run_command(self.test_node, "rm -f {0}".format(lock_file))

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

    def _install_item_extension(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """
        _, _, rcode = self.run_command(
            self.test_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             'plugins')), self.plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.test_node, local_rpm_paths
                )
            )

    def _check_options_in_output(self, expected_help_options, help_stdout):
        """ Check help for export command options """
        for expected_option in expected_help_options:
            self.assertTrue(expected_option in help_stdout)

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

    def _get_route_path(self):
        """ Returns route path"""

        return self.find(self.test_node,
                         "/deployments", "route", True)[0]

    def _get_storage_profile_path(self):
        """ Returns storage_profile path"""

        return self.find(self.test_node,
                         "/deployments",
                         "reference-to-storage-profile", True)[0]

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc01', \
        'cdb_priority1')
    def test_01_p_export_import_xml(self):
        """
        @tms_id: litpcds_212_239_tc01
        @tms_requirements_id: LITPCDS-212
        @tms_title: Exports and imports a part of the model in xml format
        @tms_description: Checks export and import of a created item and
            compares the created xml with an expected xml
        @tms_test_steps:
         @step: Perform a create command
         @result: Item sucessfully created
         @step: Export the Created item
         @result: Item successfully exported
         @step: Compare the exported file
         @result: Exported file matches expected
         @step: Delete Created item
         @result: Item successfully deleted
         @step: Load xml file into the model
         @result: Xml imported successfully
         @step: Export the root item
         @result: Root exported successfully
         @step: Assert the exported root file is valid
         @result: Exported root file is valid
         @step: Execute litp export command with -j optional argument
         @result: litp: error: unrecognized arguments: -j should be posted
         @step: Load item with -j optional argument
         @result: Raw output should contain no errors, i.e. should be "{}"
         @step: Delete the test profile
         @result: Test profile successfully deleted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self.log('info', 'perform a create command')
        existing_profile_path = self._get_profile_path()
        profileitem = existing_profile_path + "/test212"

        self.log('info', 'ENTER THE PROPERTIES WITH VALUES')
        properties = {
            'name': 'test-profile',
            'version': 'rhel7',
            'path': '/var/www/html/7/os/x86_64/',
            'arch': 'x86_64',
            'breed': 'test'
        }
        self.log('info', 'CREATE TEST PROFILE WITH CLI')
        props = "name='{0}' version='{1}' path='{2}' " \
            "arch='{3}' breed='{4}'".format(properties['name'],
                                            properties['version'],
                                            properties['path'],
                                            properties['arch'],
                                            properties['breed'])
        self.execute_cli_create_cmd(self.test_node, profileitem, "os-profile",
                                    props, "-j")

        self.log('info', 'EXPORT CREATED PROFILE ITEM')
        self.execute_cli_export_cmd(self.test_node, profileitem,
                                    "xml_expected_test01_story212.xml")
        self.log('info', 'COMPARE THE EXPORTED FILE')
        file_contents = ""
        local_path = os.path.dirname(repr(__file__).strip('\''))
        with open(local_path + "/xml_files/" +
                  "xml_expected_item_story212.xml", "rb") as fobj:
            for line in fobj:
                file_contents += line

        xml_doc = fromstring(file_contents)
        num_matched_props = 0
        for props in properties:
            for element in xml_doc.getchildren():
                if element.tag == props:
                    self.assertEqual(properties[props], element.text)
                    num_matched_props += 1
        self.assertEqual(num_matched_props, len(properties),
                         "properties count was not same")
        self.log('info', 'CHECK THE OUTPUT OF SHOW COMMAND, '
                         'CHECK NO ERRORS OCCURRED')
        stdout, _, _ = self.execute_cli_show_cmd(self.test_node, profileitem,
                                                 "-j")
        self.log('info', 'CHECK THE PROPERTIES OF "OS" OS-PROFILE')
        properties = self.cli.get_properties(stdout)
        self.log('info', properties)
        self.assertEqual(properties["name"], "test-profile",
                         "name is not test-profile")
        self.assertEqual(properties["version"], "rhel7",
                         "os version is not rhel7")
        self.assertEqual(properties["path"], "/var/www/html/7/os/x86_64/",
                         "os path is not /var/www/html/7/os/x86_64/")
        self.assertEqual(properties["arch"], "x86_64",
                         "os arch is not x86_64")
        self.assertEqual(properties["breed"], "test",
                         "os breed is not test")

        self.log('info', 'DELETE TEST PROFILE')
        self.execute_cli_remove_cmd(self.test_node, profileitem)

        self.log('info', 'We have a try/finally because '
                         'import is not auto cleaned up')
        try:
            self.log('info', 'LOAD THE EXPORTED PROFILE ITEM')
            self.execute_cli_load_cmd(self.test_node, existing_profile_path,
                                      "xml_expected_test01_story212.xml")
            self.log('info', 'Execute litp export command with given path = /')
            self.execute_cli_export_cmd(self.test_node, "/",
                                        "xml_expected_root_story212.xml")

            self.log('info', 'Assert file is valid xml')
            cmd = self.xml.get_validate_xml_file_cmd("xml_expected_"
                                                     "root_story212.xml")
            stdout, stderr, exit_code = self.run_command(self.test_node, cmd)
            self.assertNotEqual(stdout, [], "Export command output is empty")
            self.assertEqual(exit_code, 0, "Error during executing command")
            self.assertEqual(stderr, [],
                             "Errors returned {0}".format(stderr))

            self.log('info', 'EXPORT TEST PROFILE WITH USING "-J"')
            _, stderr, _ = self.execute_cli_export_cmd(
                self.test_node, profileitem,
                "xml_expected_test01_story212.xml", args="-j",
                expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "litp: error: unrecognized arguments: -j",
                stderr), "did not get "
                "expected not found error")
            self.execute_cli_remove_cmd(self.test_node, profileitem)

            self.log('info', 'LOAD TEST PROFILE WITH USING "-J"')
            stdout, stderr, _ = self.execute_cli_load_cmd(
                self.test_node, existing_profile_path,
                "xml_expected_test01_story212.xml", args="-j", load_json=False)
            self.assertTrue(self.is_text_in_list("{}",
                                                 stdout), "did not get "
                            "expected Item not found")

        finally:

            self.log('info', 'DELETE TEST PROFILE AT THE END OF TEST CASE')
            self.execute_cli_remove_cmd(self.test_node, profileitem)

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc02', \
        'cdb_priority1')
    def test_02_n_export_import_xml_invalid(self):
        """
        @tms_id: litpcds_212_239_tc02
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test exports a part of the model with
             invalid path and invalid item
        @tms_description: This test exports a part of the model with
             invalid path and invalid item, imports invalid file.
             All expected to fail.
        @tms_test_steps:
         @step: Attempt to export xml when invalid path given
         @result: InvalidLocationError should be posted
         @step: Attempt to export xml when invalid item is given
         @result: InvalidLocationError should be posted
         @step: Attempt to import xml when invalid path is given
         @result: InvalidLocationError should be posted
         @step: Execute litp export on valid litp path
         @result: litp path is exported to xml file
         @step: Attepmt to import with invalid file
         @result: [Errno 2] No such file or directory error should be posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'Attempt to export xml when invalid path given')
        path = "/INVALIDPATH"
        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, path,
            "xml_expected_test02_story212.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr), "did not get "
                        "expected Item not found")

        self.log('info', 'Attempt to export xml when invalid item is given')
        self.log('info', 'GET PROFILES PATH')
        profile_path = self.find(self.test_node, "/", "profile", False)
        profile_path = profile_path[0]

        invalid_path = profile_path + "/INVALIDITEM"

        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, invalid_path,
            "xml_expected_test02_story212.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr), "did not get "
                        "expected not found error")

        self.log('info', 'Attempt to export xml with valid path given')
        self.execute_cli_export_cmd(self.test_node, profile_path,
                                    "xml_expected_test02_story212.xml")
        self.log('info', 'Attempt to import xml when invalid path is given')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, invalid_path,
            "xml_expected_test02_story212.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr), "did not get "
                        "expected Item not found")

        self.log('info', 'Attempt to import invalid xml file')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, profile_path,
            "xml_invalid_test02_story212.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list(
            "[Errno 2] No such file or directory:", stderr),
            "did not get expected Item not found")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc03')
    def test_03_n_export_xml_plan(self):
        """
        @tms_id: litpcds_212_239_tc03
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test exports the root with Created plan
        @tms_description: Negative testcase checking behaviour
         on attempt to export root when a Plan is created.
        @tms_test_steps:
         @step: Make changes to the model and create plan
         @result: Plan should be created successfully
         @step: Execute litp export command with given path = /
         @result: Plan should not be exported
         @step: Execute litp export command with given path /plans/plan
         @result: MethodNotAllowedError should be posted
         @step: Execute litp export command wirth invalid path
         @result: InvalidLocationError should be posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
         """
        self.log('info', 'Execute litp export command with given path = /')
        stdout1, _, _ = self.execute_cli_export_cmd(
            self.test_node, "/", "xml_exported_test03_story212.xml")
        self.log('info', 'GET ITEMS PATH')
        items_path = self.find(
            self.test_node, "/software", "software-item", False)[0]
        ms_path = self.find(
            self.test_node, "/ms", "software-item", False, find_refs=True
        )[0]

        self.log('info', 'CREATE A PACKAGE WITH CLI')
        package_url = items_path + "/telnet"
        props = "name='telnet' "
        self.execute_cli_create_cmd(self.test_node,
                                    package_url, "package", props,
                                    expect_positive=True)

        self.log('info', 'Inherit item to ms')
        ms_url = ms_path + "/telnet"
        self.execute_cli_inherit_cmd(self.test_node, ms_url, package_url)

        self.log('info', 'CREATE PLAN')
        self.execute_cli_createplan_cmd(self.test_node)

        self.log('info', 'Execute litp export command with given path = /')
        stdout2, _, _ = self.execute_cli_export_cmd(
            self.test_node, "/", "xml_exported_test03_root_story212.xml")
        self.log('info', 'CHECK PLAN HAS NOT EXPORTED')
        self.assertEqual(stdout1, stdout2,
                         "plan has not exported")

        self.log('info', 'Execute litp export command with '
                         'given path /plans/plan')
        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, "/plans/plan",
            "xml_test03_plan_story212.xml", expect_positive=False)

        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr),
            "did not get expected MethodNotAllowedError")

        self.log('info', 'EXPORT INVALID PATH USING LITP EXPORT COMMAND')
        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, "/planshjghhj",
            "xml_test03_plan_story212.xml", expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc04')
    def test_04_n_export_xml_empty_missing_property(self):
        """
        @tms_id: litpcds_212_239_tc04
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test exports a part of model with missing property
        @tms_description: Negative testcase checking behaviour
         on attempt to export a part of model with missing property
        @tms_test_steps:
         @step: Attempt litp export command without specifying target file
         @result: error should be posted: litp export: error: argument -
            f/--file: expected one argument
         @step: 'Attempt litp export command with empty path argument
         @result: error should be posted: litp export: error: argument -p
            /--path: expected one argument
         @step: Attempt litp export command with missing -p argument
         @result: error should be posted: argument -p/ --path is required
         @step: Attempt litp export without any arguments
         @result: error should be posted litp export: error: argument -p
                                             /--path is required
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        self.log('info', 'Attempt litp export command with '
                         'missing properties')
        ms_path = self.find(
            self.test_node, "/ms", "software-item", False, find_refs=True
        )[0]

        self.log('info', 'Attempt litp export command '
                         'with empty export file')
        cmd = "{0} {1} {2} {3} {4}".format(self.cli.litp_path, "export",
                                           "-p", ms_path,
                                           "-f")
        stdout, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(return_code, 0,
                            "export was successful when error is expected")
        self.assertEqual(stdout, [], "Standard output is not empty")
        self.assertNotEqual(stderr, [], "Standard errorput is empty")

        self.log('info', 'Check expected error message posted')
        self.assertTrue(self.is_text_in_list("litp export: error: argument -"
                                             "f/--file: expected one argument",
                                             stderr), "did not get "
                        "expected litp export: error")

        self.log('info', 'Attempt litp export command with empty '
                         'path argument')
        cmd = "{0} {1} {2} {3} {4}".format(self.cli.litp_path, "export",
                                           "-p", "-f",
                                           "xml_test04_story212.xml")
        stdout, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(return_code, 0,
                            "export was successful when error is expected")
        self.assertEqual(stdout, [], "Standard output is not empty")
        self.assertNotEqual(stderr, [], "Standard errorput is empty")

        self.assertTrue(self.is_text_in_list("litp export: error: argument -p"
                                             "/--path: expected one argument",
                                             stderr), "did not get "
                        "expected litp export: error")
        self.log('info',
                 'Attempt litp export command with missing -p argument')
        cmd = "{0} {1} {2} {3}".format(self.cli.litp_path, "export",
                                       "-f", "xml_test04_story212.xml")
        stdout, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(return_code, 0,
                            "export was successful when error is expected")
        self.assertEqual(stdout, [], "Standard output is not empty")
        self.assertNotEqual(stderr, [], "Standard errorput is empty")

        self.assertTrue(self.is_text_in_list("litp export: error: argument -p"
                                             "/--path is required",
                                             stderr), "did not get "
                        "expected litp export: error")

        self.log('info', 'Attempt litp export without any arguments')
        cmd = "{0} {1}".format(self.cli.litp_path, "export")
        stdout, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(return_code, 0,
                            "export was successful when error is expected")
        self.assertEqual(stdout, [], "Standard output is not empty")
        self.assertNotEqual(stderr, [], "Standard errorput is empty")

        self.assertTrue(self.is_text_in_list("litp export: error: argument -p"
                                             "/--path is required",
                                             stderr), "did not get "
                        "expected litp export: error")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc05')
    def test_05_pn_export_import_xml_nodes(self):
        """
        @tms_id: litpcds_212_239_tc05
        @tms_requirements_id: LITPCDS-212
        @tms_title: Tests for exporting nodes
        @tms_description: Tests to verify xml export and import of nodes
        @tms_test_steps:
         @step: Export node to xml
         @result: Export should be successful
         @step: Assert created file is a valid xml
         @result: Xml file generated on export should be valid
         @step: Attempt to import generated xml file
         @result: ItemExistsError should be posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
         """
        self.log('info', 'Export node to xml')
        node_path = self.find(self.test_node,
                              "/deployments", "node", False)
        node_path = node_path[0]

        self.execute_cli_export_cmd(self.test_node, node_path,
                                    "xml_test05_story212.xml")

        self.log('info', 'Assert created file is valid xml')
        cmd = self.xml.get_validate_xml_file_cmd("xml_test05"
                                                 "_story212.xml")
        stdout, stderr, exit_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(stdout, [], "Export command output is empty")
        self.assertEqual(exit_code, 0, "Error during executing command")
        self.assertEqual(stderr, [],
                         "Errors returned {0}".format(stderr))

        self.log('info', 'Attempt to import generated xml file')
        cluster_path = self.find_children_of_collect(
            self.test_node, "/deployments", "cluster")[0]

        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 cluster_path,
                                                 "xml_test05_story212.xml",
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("ItemExistsError", stderr),
                        "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc06')
    def test_06_n_export_deleted_item(self):
        """
        @tms_id: litpcds_212_239_tc06
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test tries to export the deleted profile item
        @tms_description: Negative tests for behaviour on attempt to export
            a deleted item
        @tms_test_steps:
         @step: Create the profile item
         @result: Item creation should be successful
         @step: Remove the previously created profile item
         @result: Item removal should be successful
         @step: Attempt to export the previously removed item
         @result: InvalidLocationError should be posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
         """

        existing_profile_path = self._get_profile_path()
        profileitem = existing_profile_path + "/test212"

        self.log('info', 'CREATE TEST PROFILE WITH CLI')
        props = "name='test-profile' version='rhel7' " \
            " path='{0}' arch='x86_64' breed='redhat'".format(
                test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7)
        self.execute_cli_create_cmd(self.test_node, profileitem, "os-profile",
                                    props, "-j")
        self.log('info', 'DELETE TEST PROFILE')
        self.execute_cli_remove_cmd(self.test_node, profileitem)

        self.log('info', 'EXPORT THE DELETED PROFILE ITEM')
        _, stderr, _ = self.execute_cli_export_cmd(self.test_node, profileitem,
                                                   "xml_test06_story212.xml",
                                                   expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr), "did not get "
                        "expected not found error")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc07')
    def test_07_n_export_while_plan_running(self):
        """
        @tms_id: litpcds_212_239_tc07
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test Attempts to export a running plan
        @tms_description: Negative tests for behaviour on attempt to issue
            export while plan is running
        @tms_test_steps:
         @step: Make changes in the model, create and run plan
         @result: Plan runs successfully
         @step: Attempt to export the /plans/plan path
         @result: InvalidRequestError should be posted
         @result: plan executes successfully
        @tms_test_precondition: NA
        @tms_execution_type: Automated
         """
        self._install_item_extension()

        lock_item = "story212_tc07_lock"
        lock_path = "/tmp/" + lock_item
        try:
            self.create_ms_config_item(lock_item)

            self.log('info', 'CREATE PLAN')
            self.execute_cli_createplan_cmd(self.test_node)

            self.create_lock(lock_path)

            self.log('info', 'RUN PLAN')
            self.execute_cli_runplan_cmd(self.test_node)

            self.log('info', 'Execute litp export command with '
                             'given path /plans/plan')
            _, stderr, _ = self.execute_cli_export_cmd(
                self.test_node, "/plans/plan",
                "xml_test07_story212.xml", expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "InvalidRequestError", stderr),
                "did not get expected error message")

        finally:
            self.release_lock(lock_path)
            self.log('info', 'Wait plan to be finished to update '
                             'the original properties')
            self.wait_for_plan_state(self.test_node,
                                     test_constants.PLAN_COMPLETE)
            self.log('info', 'Restore the original property value '
                             '(in finally)')

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc08')
    def test_08_n_export_import_item_on_running_plan(self):
        """
        @tms_id: litpcds_212_239_tc08
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test Attempts to export an item while running plan
        @tms_description: Negative tests for behaviour on attempt to issue
            export/import commands on valid items while plan is running
        @tms_test_steps:
         @step: Make changes in the model, create and run plan
         @result: Plan runs successfully
         @step: Attempt to export a valid item
         @result: InvalidRequestError should be posted
         @step: Attempt to load xml while plan running
         @result: InvalidRequestError should be posted
         @result: plan executes successfully
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        self._install_item_extension()

        lock_item = "story212_tc08_lock"
        lock_path = "/tmp/" + lock_item
        try:
            self.log('info', 'GET ITEMS PATH')
            items_path = self.find(
                self.test_node, "/software", "software-item", False)[0]

            lock_item_path = self.create_ms_config_item(lock_item)
            self.log('info', 'CREATE PLAN')
            self.execute_cli_createplan_cmd(self.test_node)
            self.create_lock(lock_path)
            self.log('info', 'RUN PLAN')
            self.execute_cli_runplan_cmd(self.test_node)
            self.log('info', 'Execute litp export command '
                             'with a valid item path')
            _, stderr, _ = self.execute_cli_export_cmd(self.test_node,
                                                       lock_item_path,
                                                       "xml_test08_"
                                                       "story212.xml",
                                                       expect_positive=False)

            self.assertTrue(self.is_text_in_list(
                "InvalidRequestError", stderr),
                "did not get expected error message")

            self.log('info', 'Execute litp load command')
            profile_xml_filename = "xml_expected_item_story239.xml"
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath = local_filepath + "/xml_files/" \
                + profile_xml_filename
            profile_xml_filepath = "/tmp/" + profile_xml_filename
            self.copy_file_to(self.test_node, local_xml_filepath,
                              profile_xml_filepath)

            _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                     items_path,
                                                     profile_xml_filepath,
                                                     expect_positive=False)
            self.assertTrue(self.is_text_in_list("InvalidRequestError",
                                                 stderr),
                            "did not get expected error message")

        finally:
            self.release_lock(lock_path)
            self.log('info', 'Wait plan to be finished to update '
                             'the original properties')
            self.wait_for_plan_state(self.test_node,
                                     test_constants.PLAN_COMPLETE)
            self.log('info', 'Restore the original property value '
                             '(in finally)')

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc09')
    def test_09_p_export_item_on_same_file(self):
        """
        @tms_id: litpcds_212_239_tc09
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test checks target file overwritten
            on export to same file
        @tms_description: Test checks behaviour on exporting
            different items to same xml file
        @tms_test_steps:
         @step: Export Clusters to test212.xml
         @result: Clusters should export successfully
         @step: Assert that a valid xml file was created on export
         @result: The created xml should be well formed
         @step: Create a test profile for export
         @result: Item created
         @step: Export the created item to same file test212.xml
         @result: Export shpuld be successful
         @step: Check test212.xml file
         @result: test212.xml is a well formed xml, content overwritten
            not appended
         @step: remove previously created test profile item
         @result: Remove should be possible
         @step: Attempt to import xml to the removed profile item
         @result: InvalidLocationError should be posted
        @tms_test_precondition: NA
        @tms_execution_type: Automated
         """

        cluster_path = self.find(self.test_node,
                                 "/deployments", "node")
        cluster_path = cluster_path[0]

        self.log('info', 'EXPORT CLUSTER ITEM TO A FILE TEST212.XML')
        self.execute_cli_export_cmd(self.test_node, cluster_path,
                                    "xml_test09_story212.xml")
        self.log('info', 'Assert file is valid xml')
        cmd = self.xml.get_validate_xml_file_cmd("xml_test09_story212.xml")
        stdout1, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(stdout1, [], "Validate command output is empty")
        self.assertEqual(return_code, 0, "Error during executing command")
        self.assertEqual(stderr, [],
                         "Errors returned {0}".format(stderr))

        existing_profile_path = self._get_profile_path()
        profileitem = existing_profile_path + "/test212"

        self.log('info', 'CREATE TEST PROFILE WITH CLI')
        props = "name='test-profile' version='rhel7' " \
            " path='{0}' arch='x86_64' breed='redhat'".format(
                test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7)

        self.execute_cli_create_cmd(self.test_node, profileitem, "os-profile",
                                    props, "-j")

        self.log('info', 'EXPORT THE PROFILE ITEM TO SAME FILE TEST212.XML')
        self.execute_cli_export_cmd(self.test_node, profileitem,
                                    "xml_test09_story212.xml")
        self.log('info', 'Assert file is valid xml')
        cmd = self.xml.get_validate_xml_file_cmd("xml_test09_story212.xml")
        stdout2, stderr, return_code = self.run_command(self.test_node, cmd)
        self.assertNotEqual(stdout2, [], "Validate command output is empty")
        self.assertEqual(return_code, 0, "Error during executing command")
        self.assertEqual(stderr, [],
                         "Errors returned {0}".format(stderr))

        self.log('info', 'CHECK THAT THE FIRST OUTPUT IS NOT '
                         'APPENDED ON SECOND OUTPUT')
        self.assertFalse(stdout1 in stdout2,
                         "xml output is not appended")

        self.log('info', 'Remove profile item to load in the model')
        self.execute_cli_remove_cmd(self.test_node, profileitem)

        self.log('info', 'Execute litp load command')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 profileitem,
                                                 "xml_test09_story212.xml",
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError",
                                             stderr),
                        "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc10')
    def test_10_n_export_import_not_access_file(self):
        """
        @tms_id: litpcds_212_239_tc10
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test tries to export storage profile to a file
            to which litp-admin doesn't have access.
        @tms_description: Test checks behaviour on exporting
            different items to same xml file
        @tms_test_steps:
         @step: Attempt to export an item to a file
            that has access rights for root only
         @result: [Errno 13] Permission denied error should be posted
         @step: Attempt to import an xml file when no access rights to it
         @result: [Errno 13] Permission denied error should be posted
        @tms_test_precondition: File with permissions for no one except owner
            i.e. root
        @tms_execution_type: Automated
         """
        self.log('info', 'Create an xml file with permissions '
                         'for no one except owner')
        create_cmd = "touch /tmp/xml_test_10_no_permission.xml"
        stdout, stderr, returnc = self.run_command(
            self.test_node, create_cmd, su_root=True)
        self.assertEqual(
            stdout, [], "Create command output is empty")
        self.assertEqual(
            returnc, 0, "Error during executing command")
        self.assertEqual(
            stderr, [], "Errors returned {0}".format(stderr))

        cmd = "chmod -rwx /tmp/xml_test_10_no_permission.xml"
        stdout, stderr, returnc = self.run_command(
            self.test_node, cmd, su_root=True)
        self.assertEqual(
            stdout, [], "change permission command output is empty")
        self.assertEqual(
            returnc, 0, "Error during executing command")
        self.assertEqual(
            stderr, [], "Errors returned {0}".format(stderr))

        storage_path = self.find(
            self.test_node, "/", "storage-profile-base", False)[0]

        self.log('info', 'Attempt to export an item to a file '
                         'with no access rights')
        _, stderr, _ = self.execute_cli_export_cmd(
            self.test_node, storage_path,
            "/tmp/xml_test_10_no_permission.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list(
            "[Errno 13] Permission denied:", stderr),
            "did not get expected permissions error")

        self.log('info', 'Attempt to import an xml file '
                         'when no access rights to it')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, storage_path,
            "/tmp/xml_test_10_no_permission.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list(
            "[Errno 13] Permission denied:", stderr),
            "did not get expected permissions error")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc12')
    def test_12_n_import_missing_child_elements(self):
        """
        @tms_id: litpcds_212_239_tc12
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test tries to import deployments with missing
            child elements
        @tms_description: Test checks behaviour on exporting
            deployments with missing child elements and then importing
            it
        @tms_test_steps:
         @step: Create a deployment object with no child items
         @result: Item should be created
         @step: Export the created deployment object to xml
         @result: Export should be successful
         @step: Attempt to import the generated xml file
         @result: InvalidXMLError should be posted
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
         """
        self.log('info', 'Create deployment object')
        deployment_url = "/deployments/dep239"
        self.execute_cli_create_cmd(self.test_node,
                                    deployment_url, "deployment")

        self.log('info', 'Export Created deployment object (expect succeed)')
        self.execute_cli_export_cmd(self.test_node,
                                    deployment_url, "xml_test12_story212.xml")

        self.log('info', 'Attempt to import the generated '
                         'xml_test12_story212.xml (expect fail)')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, deployment_url,
            "xml_test12_story212.xml", expect_positive=False)
        self.assertTrue(self.is_text_in_list(
            "InvalidXMLError", stderr), \
            "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc14', \
        'cdb_priority1')
    def test_14_p_import_root(self):
        """
        @tms_id: litpcds_212_239_tc14
        @tms_requirements_id: LITPCDS-239
        @tms_title: Import entire model xml into an existing model
            using the merge flag
        @tms_description: Test checks behaviour on exporting
            root and importing the created xml file
        @tms_test_steps:
         @step: Export / (root) to root_story239.xml
         @result: Xml file should be created
         @step: Import the created xml file to / (root)
         @result: Import should fail with ItemExistsError
         @step: Execute create_plan command to assure there's no
            changes in model
         @result: Plan creation should fail with DoNothingPlanError
         @step:  Import the created xml file to / (root) with -merge flag
         @result: Should be successful
         @step: Check the state of all items in the model
         @result: All should be applied
         @step: create_plan to make sure no changes made in model on merge
         @result: Plan creation should fail with DoNothingPlanError
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', 'EXPORT / USING LITP EXPORT COMMAND')
        self.execute_cli_export_cmd(self.test_node, "/", "root_story239.xml")

        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 "/", "root_story239.xml",
                                                 expect_positive=False)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("ItemExistsError ", stderr))

        self.log('info', 'CREATE PLAN TO CHECK LOAD WITHOUT MERGE'
                         ' DOES NOT CHANGE THE MODEL')
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False)
        self.assertTrue(self.is_text_in_list("DoNothingPlanError ", stderr))

        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND'
                         ' WITH -MERGE FLAG')
        self.execute_cli_load_cmd(self.test_node,
                                  "/", "root_story239.xml", "--merge")

        self.log('info', 'check the state of all items in the model')
        self.assertTrue(self.is_all_applied(self.test_node))

        self.log('info', 'CREATE PLAN TO ENSURE MODEL IS NOT CHANGED'
                         ' WHEN MERGE USED')
        _, stderr, _ = self.execute_cli_createplan_cmd(
            self.test_node, expect_positive=False)
        self.assertTrue(self.is_text_in_list("DoNothingPlanError ", stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc15')
    def test_15_p_import_merge_rules(self):
        """
        @tms_id: litpcds_212_239_tc15
        @tms_requirements_id: LITPCDS-239
        @tms_title: Import entire model xml into an existing model
            using the merge flag, check behaviour on differences
        @tms_description: Check behaviour on import with merge flag:
            Items present in the model but not in the imported file
            should be preserved in the model unchanged.
            Items present both in the model and in the imported xml file
            should be updated as per xml file.
            Items present in the imported xml file and not in the model
            should be created.
        @tms_test_steps:
         @step: Create a storage profile in model that matches one existing
            in the predefined xml file xml_test15_node3_story239
         @result: Storage profile item should be created
         @step: Import xml file without merge flag containing:
            -Created storage profile in model with
            -Node3 with nherited route,
            os-profile, storage-profile and
            system that is the same as node1,
            -system_providers, vm3
         @result: Import should fail with ItemExistsError
         @step: Import above xml file with merge flag
         @result: Import should be successful
         @step: Check node3 has been imported
         @result: node3 should be imported
         @step: Check properties of imported node3
         @result: Properties of node3 should be imported
         @step: Check storage_profile_name has been updated
         @result: storage_profile name should be updated
         @step: Check system_provider has been imported
         @result: system_provider should be imported
         @step: Check properties of imported vm3
         @result: Properties of vm3 imported
         @step: remove all imported items and run litp create_plan
         @result: DoNothingPlanError, plan should not be created
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        try:
            self.log('info', 'save the cluster value before the test')
            clusters = self.find(
                self.test_node, '/deployments', 'vcs-cluster'
            )
            for cluster in clusters:
                self.backup_path_props(self.test_node, cluster)

            self.log('info', 'CREATE STORAGE PROFILE IN MODEL'
                             ' THAT IS ALSO IN XML FILE')
            storage_url = self.find(
                self.test_node, "/infrastructure",
                "storage-profile-base", False)

            storage_profile_url = storage_url[0] + "/profile_story239"
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

            self.log('info', 'Save number of managed nodes'
                             ' and system_providers')
            nodes = self.find(
                self.test_node, "/deployments", "node", True)

            orig_number_nodes = len(nodes)

            sys_pros = self.find(
                self.test_node, "/infrastructure", "blade", True)

            orig_sys_pros = len(sys_pros)

            self.log('info', ' Copy node3 XML file onto node')
            profile_xml_filename = "xml_test15_node3_story239.xml"
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath = local_filepath + "/xml_files/" \
                + profile_xml_filename
            profile_xml_filepath = "/tmp/" + profile_xml_filename
            self.copy_file_to(
                self.test_node, local_xml_filepath, profile_xml_filepath)

            self.log('info', 'Import node3 without merge flag')
            _, stderr, _ = self.execute_cli_load_cmd(
                self.test_node, "/", profile_xml_filepath,
                expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "ItemExistsError", stderr),
                "did not get expected error message")

            self.log('info', 'Import node3 with merge flag')
            self.execute_cli_load_cmd(
                self.test_node, "/", profile_xml_filepath,
                args="--merge", expect_positive=True)

            self.log('info', 'Check node 3 has been imported')
            nodes_url = self.find(
                self.test_node, "/deployments", "node", True)
            self.assertEqual(orig_number_nodes + 1, len(nodes_url))
            for item in nodes_url:
                if "node_story239" in item:
                    node3_url = item

            self.log('info', 'Check properties of imported node3')
            props = self.get_props_from_url(
                self.test_node, node3_url, "hostname")
            self.assertEqual("nodestory239", props)

            system_url = node3_url + "/system"
            props = self.get_props_from_url(
                self.test_node, system_url, "system_name")
            self.assertEqual("ST21223RY9", props)

            self.log('info', 'Check snap_size in root fs has been updated')
            props = self.get_props_from_url(
                self.test_node, fs1_url, "snap_size")
            self.assertEqual("10", props)

            self.log('info', 'Check system_provider has been imported')
            systems_url = self.find(
                self.test_node, "/infrastructure", "blade", True)
            self.assertEqual(orig_sys_pros + 1, len(systems_url))
            for item in systems_url:
                if "sysStory239" in item:
                    sys3_url = item

            self.log('info', 'Check properties of imported vm3')
            props = self.get_props_from_url(
                self.test_node, sys3_url, "system_name")
            self.assertEqual("ST21223RY9", props)

        finally:
            self.log('info', 'Remove imported items')
            nodes_url = self.find(self.test_node, "/deployments", "node", True)
            for item in nodes_url:
                if "node_story239" in item:
                    node3_url = item
                    self.execute_cli_remove_cmd(self.test_node, node3_url)

            systems_url = self.find(
                self.test_node, "/infrastructure", "blade", True)
            for item in systems_url:
                if "sysStory239" in item:
                    sys3_url = item
                    self.execute_cli_remove_cmd(self.test_node, sys3_url)

            self.log('info', 'ENSURE CREATE_PLAN DOES NOT CREATE A PLAN '
                     'AS MODEL IS IN SAME STATE AS BEFORE EXPORT')
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.test_node, expect_positive=False)
            self.assertTrue(self.is_text_in_list(
                "DoNothingPlanError", stderr), "Expected DoNothingPlanError")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc16')
    def test_16_n_import_xml_missing_mandatory_property(self):
        """
        @tms_id: litpcds_212_239_tc16
        @tms_requirements_id: LITPCDS-212
        @tms_title: Attempt to import a type: os-profile
            when the xml is missing a mandatory property
        @tms_description: Attempt to import a type: os-profile
            when the xml is missing a mandatory 'name' property
        @tms_test_steps:
         @step: Attempt to import faulty os-profile item from file
            without merge flag
         @result: InvalidXMLError should be posted
         @step: Attempt to import faulty os-profile item from file
            with merge flag
         @result: InvalidXMLError should be posted
        @tms_test_precondition: predefined file
            xml_os_profile_missing_prop_story239.xml copied to ms
        @tms_execution_type: Automated
        """

        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'Copy profile XML file to node')
        profile_xml_filename1 = "xml_os_profile_missing_prop_story239.xml"
        local_filepath1 = os.path.dirname(__file__)
        local_xml_filepath1 = local_filepath1 + "/xml_files/" \
            + profile_xml_filename1
        profile_xml_filepath1 = "/tmp/" + profile_xml_filename1
        profile_xml_filename2 = "xml_os_profile_invalid_prop_story239.xml"
        local_filepath2 = os.path.dirname(__file__)
        local_xml_filepath2 = local_filepath2 + "/xml_files/" \
            + profile_xml_filename2
        profile_xml_filepath2 = "/tmp/" + profile_xml_filename2
        self.copy_file_to(
            self.test_node, local_xml_filepath1, profile_xml_filepath1)
        self.copy_file_to(
            self.test_node, local_xml_filepath2, profile_xml_filepath2)

        self.log('info', 'Import a type: os-profile without merge flag')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 self._get_profiles_path(),
                                                 profile_xml_filepath1,
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr),
                        "did not get expected error message")

        self.log('info', 'Import a type: os-profile with merge flag')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 self._get_profiles_path(
                                                 ), profile_xml_filepath2,
                                                 args="--merge",
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr),
                        "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc17')
    def test_17_n_import_invalid_collection(self):
        """
        @tms_id: litpcds_212_239_tc17
        @tms_requirements_id: LITPCDS-212
        @tms_title: Attempt to import a type: collection-of-node
            xml to a path of different type
        @tms_description: Attempt to import a type: collection-of-node
            xml to a path of different type. Load fails with
            and without merge flag as path is invalid
        @tms_test_steps:
         @step: Export an existing collection-of-node item to xml
         @result: Export should be possible
         @step: Attempt to import the collection-of-node item to an
            invalid location in the model without the merge flag
         @result: InvalidLocationError should be posted
         @step: Attempt to import the collection-of-node item to an
            invalid location in the model with the merge flag
         @result: InvalidLocationError should be posted
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', '1. Find the node1 nodes collection')
        existing_node_path = self._get_node_path()

        self.log('info', '2. Save an invalid path')
        invalid_node_path = self._get_node_path() + "/invalidcollection"

        self.log('info', '3. Export the existing nodes collection model item')
        node_xml_file = "story239_test05_nodes.xml"
        self.execute_cli_export_cmd(self.test_node,
                                existing_node_path, filepath=node_xml_file)

        self.log('info', '4. Load the type: collection-of-node '
                         'without merge flag')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 invalid_node_path,
                                                 node_xml_file,
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr),
                        "did not get expected error message")

        self.log('info', '5. Load the type: collection-of-node '
                         'with merge flag')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 invalid_node_path,
                                                 node_xml_file, args="--merge",
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr),
                        "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc18')
    def test_18_n_import_xml_invalid_property(self):
        """
        @tms_id: litpcds_212_239_tc18
        @tms_requirements_id: LITPCDS-212
        @tms_title: Attempt to import a type: os-profile
            when the xml contains an unexpected property
        @tms_description: Attempt to import a type: os-profile
            when the xml contains an unexpected property.
            (os_version instead of version).
            Load should fail with and without merge.
        @tms_test_steps:
         @step: Attempt to import the predefined xml file without merge flag
         @result: InvalidXMLError should be posted
         @step: Attempt to import the predefined xml file with the merge flag
         @result: InvalidXMLError should be posted
        @tms_test_precondition: predefined file
            xml_os_profile_invalid_prop_story239.xml copied to ms
        @tms_execution_type: Automated
        """

        # save the cluster value before the test
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'Copy profile XML file to node')
        profile_xml_filename = "xml_os_profile_invalid_prop_story239.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + profile_xml_filename
        profile_xml_filepath = "/tmp/" + profile_xml_filename
        self.copy_file_to(self.test_node,
                          local_xml_filepath, profile_xml_filepath)

        self.log('info', '2. Import a type: os-profile without merge flag')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 self._get_profiles_path(
                                                 ), profile_xml_filepath,
                                                 expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr),
                        "did not get expected error message")

        self.log('info', '3. Import a type: os-profile with merge flag')
        self.execute_cli_load_cmd(self.test_node, self._get_profiles_path(),
                                  profile_xml_filepath, args="--merge",
                                  expect_positive=False)
        self.assertTrue(self.is_text_in_list("InvalidXMLError", stderr),
                        "did not get expected error message")

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc19')
    def test_19_n_import_item_type_marked_ForRemoval(self):
        """
        @tms_id: litpcds_212_239_tc19
        @tms_requirements_id: LITPCDS-212
        @tms_title: Import xml file overwriting a model item
            that is marked ForRemoval
        @tms_description: Import xml file overwriting a model item
            that is marked ForRemoval
        @tms_test_steps:
         @step: Create a config item, create and run plan
         @result: Newly created should be in Applied state
         @step: Export the created model item to xml file
            (referred to as original)
         @result: Xml file should be created
         @step: Delete the created model item with litp remove
         @result: Item should be in ForRemoval state
         @step: Load the xml file with --merge flag
         @result: Item restored to Applied state
         @step: Update items name and export to a new xml file
            (referred to as new xml file)
         @result: Item exported in an Updated state
         @step: Restore items initial name
         @result: Item restored to Applied state
         @step: Load new xml file with merge
         @result: Item should be in Updated state
         @step: Load original xml file with merge
         @result: Item should be in Applied state
         @step: Create and run the plan
         @result: Plan executes successfuly
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        self._install_item_extension()

        lock_item = "story212_239_tc19_lock"
        lock_path = "/tmp/" + lock_item
        filepath = '/tmp/{0}.xml'.format(lock_item)
        filepath_update = '/tmp/{0}_update.xml'.format(lock_item)
        try:
            self.log('info', 'Create config item')
            lock_item_path = self.create_ms_config_item(lock_item)
            self.log('info', 'execute the create_plan command')
            self.execute_cli_createplan_cmd(self.test_node)
            self.log('info',
                     'create lock file that\'s checked by callback task')
            self.create_lock(lock_path)
            self.log('info', 'execute the run_plan command')
            self.execute_cli_runplan_cmd(self.test_node)
            self.assertTrue(self.wait_for_plan_state(self.test_node,
                                            test_constants.PLAN_IN_PROGRESS))
            self.release_lock(lock_path)
            self.assertTrue(self.wait_for_plan_state(
                self.test_node, test_constants.PLAN_COMPLETE))

            self.log('info', 'Export the created item')
            self.execute_cli_export_cmd(self.test_node, lock_item_path,
                                        filepath)
            # check for fix LITPCDS-7381
            self.log('info', 'get the ms url')
            ms_ = self.find(self.test_node, '/', 'ms')[0]
            configs_path = self.find(self.test_node, ms_,
                                        'node-config',
                                        rtn_type_children=False)[0]
            self.log('info', 'Remove the item')
            self.execute_cli_remove_cmd(self.test_node, lock_item_path)
            self.assertEqual('ForRemoval', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.log('info',
                     'load previously created xml file with merge flag')
            self.execute_cli_load_cmd(self.test_node, configs_path,
                                        filepath, '--merge')
            self.log('info', 'check item restored to applied state')
            self.assertEqual('Applied', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.log('info', 'update config item name property '
                             'and export to file')
            self.update_ms_config_item(lock_item, 'updated_name')
            self.execute_cli_export_cmd(self.test_node, lock_item_path,
                                        filepath_update)
            self.assertEqual('Updated', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.log('info', 'restore item to Applied state')
            self.update_ms_config_item(lock_item, 'initial_name')
            self.assertEqual('Applied', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.log('info', 'load xml file with --merge')
            self.execute_cli_load_cmd(self.test_node, configs_path,
                                        filepath_update, '--merge')
            self.assertEqual('Updated', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.log('info', 'load original xml file with --merge')
            self.execute_cli_load_cmd(self.test_node, configs_path,
                                        filepath, '--merge')
            self.assertEqual('Applied', self.execute_show_data_cmd(
                            self.test_node, lock_item_path, 'state'))
            self.execute_cli_remove_cmd(self.test_node, lock_item_path)
            self.execute_cli_createplan_cmd(self.test_node)
            self.execute_cli_runplan_cmd(self.test_node)
        finally:
            self.release_lock(lock_path)
            self.run_command(self.test_node, "rm -f {0}".format(filepath))
            self.run_command(self.test_node, "rm -f {0}".format(
                            filepath_update))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc20')
    def test_20_n_import_root_invalid_path(self):
        """
        @tms_id: litpcds_212_239_tc20
        @tms_requirements_id: LITPCDS-212
        @tms_title: import entire model xml into an exisitng model
            with invalid path
        @tms_description: Check behaviour on attempt to import entire model
            on an invalid path
        @tms_test_steps:
         @step: Export from / to xml_test20_story239.xml
         @result: Xml should be created
         @step: Attempt to import the root xml to an invalid path in model
            (node level within deployments)
         @result: InvalidLocationError should be posted
         @step: Attempt to import the root xml to a non existing path
            (/invalid)
         @result: InvalidLocationError should be posted
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'EXPORT / USING LITP EXPORT COMMAND')
        self.execute_cli_export_cmd(self.test_node, "/",
                                    "xml_test20_story239.xml")

        existing_node_path = self._get_node_path()
        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND '
                         'TO AN INVALID PATH')
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 existing_node_path,
                                                 "xml_test20_story239.xml",
                                                 expect_positive=False)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr))

        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND '
                         'TO A NON EXISTING PATH')
        invalid_path = "/invalid"
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 invalid_path,
                                                 "xml_test20_story239.xml",
                                                 expect_positive=False)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("InvalidLocationError", stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc21', \
        'cdb_priority1')
    def test_21_n_import_anywhere_in_model(self):
        """
        @tms_id: litpcds_212_239_tc21
        @tms_requirements_id: LITPCDS-212
        @tms_title: import xml into an existing model with invalid locations
        @tms_description: Check behaviour on attempt to import xml with
            profile in invalid locations in the tree, import should fail
            InvalidLocationError posted.
        @tms_test_steps:
         @step: Export profile item to xml_test21_story239.xml
         @result: Xml should be created
         @step: Attempt to import the xml to an invalid path in model
            (node level within deployments)
         @result: ChildNotAllowedError should be posted
         @step: Attempt to import the xml to an invalid path in model
            (routes level within deployments)
         @result: MethodNotAllowedError should be posted
         @step: Attempt to import the xml to an invalid path in model
            (storage profile level within deployments)
         @result: MethodNotAllowedError should be posted
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """

        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'EXPORT PROFILE ITEM USING LITP EXPORT COMMAND')
        existing_profile_path = self._get_profiles_path()
        self.execute_cli_export_cmd(
            self.test_node, existing_profile_path, "xml_test21_story239.xml")

        # Scenario:1
        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND '
                         'IN NODES')
        existing_node_path = self._get_node_path()
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, existing_node_path,
            "xml_test21_story239.xml", expect_positive=False)

        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("ChildNotAllowedError", stderr))

        # Scenario:2
        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND '
                         'IN IP-RANGE')
        existing_route_path = self._get_route_path()
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 existing_route_path,
                                                 "xml_test21_story239.xml",
                                                 expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        # Scenario:3
        self.log('info', 'IMPORT EXPORTED FILE USING LITP LOAD COMMAND '
                         'IN STORAGE-PROFILE')
        existing_storage_profile_path = self._get_storage_profile_path()
        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 existing_storage_profile_path,
                                                 "xml_test21_story239.xml",
                                                 expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc22')
    def test_22_n_export_import_itemtypes(self):
        """
        @tms_id: litpcds_212_239_tc22
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test tries to export and import /item-types
        @tms_description: Check behaviour on attempt to import and export
            xml to and from /item-types and is expected to fail with
            MethodNotAllowedError
        @tms_test_steps:
         @step: Attempt to export /item-types to xml file
         @result: MethodNotAllowedError should be posted
         @step: Attempt to import xml_expected_item_story212.xml to
            /item-types
         @result: MethodNotAllowedError should be posted
        @tms_test_precondition: xml_expected_item_story212.xml copied to ms
        @tms_execution_type: Automated
        """

        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'EXPORT /item-types USING LITP EXPORT COMMAND')
        itemtypes_path = "/item-types"
        _, stderr, _ = self.execute_cli_export_cmd(self.test_node,
                                                   itemtypes_path,
                                                   "xml_test22_story239.xml",
                                                   expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        self.log('info', 'Execute litp load command')
        profile_xml_filename = "xml_expected_item_story212.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + profile_xml_filename
        profile_xml_filepath = "/tmp/" + profile_xml_filename
        self.copy_file_to(self.test_node, local_xml_filepath,
                          profile_xml_filepath)

        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 itemtypes_path,
                                                 profile_xml_filepath,
                                                 expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc23')
    def test_23_n_export_import_propertytypes(self):
        """
        @tms_id: litpcds_212_239_tc23
        @tms_requirements_id: LITPCDS-212
        @tms_title: This test tries to export and import /property-types
        @tms_description: Check behaviour on attempt to import and export
            xml to and from /property-types and is expected to fail with
            MethodNotAllowedError
        @tms_test_steps:
         @step: Attempt to export /property-types to xml file
         @result: MethodNotAllowedError should be posted
         @step: Attempt to import xml_expected_item_story212.xml to
            /property-types
         @result: MethodNotAllowedError should be posted
        @tms_test_precondition: xml_expected_item_story212.xml copied to ms
        @tms_execution_type: Automated
        """

        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'EXPORT /property-types USING LITP EXPORT COMMAND')
        propertytypes_path = "/property-types"
        _, stderr, _ = self.execute_cli_export_cmd(self.test_node,
                                                   propertytypes_path,
                                                   "xml_test22_story239.xml",
                                                   expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list("MethodNotAllowedError", stderr))

        self.log('info', 'Execute litp load command')
        profile_xml_filename = "xml_expected_item_story212.xml"
        local_filepath = os.path.dirname(__file__)
        local_xml_filepath = local_filepath + "/xml_files/" \
            + profile_xml_filename
        profile_xml_filepath = "/tmp/" + profile_xml_filename
        self.copy_file_to(self.test_node, local_xml_filepath,
                          profile_xml_filepath)

        _, stderr, _ = self.execute_cli_load_cmd(self.test_node,
                                                 propertytypes_path,
                                                 profile_xml_filepath,
                                                 expect_positive=False)
        self.log('info', 'CHECK THE OUTPUT')
        self.assertTrue(self.is_text_in_list(
            "MethodNotAllowedError", stderr))

    @attr('all', 'revert', 'tooltest', 'story212_239', 'story212_239_tc24')
    def test_24_n_type_check_litpcds5391(self):
        """
        @tms_id: litpcds_212_239_tc24
        @tms_requirements_id: LITPCDS-239
        @tms_title: This test ensures that a type check is performed at merge
        @tms_description: This test ensures that a type check is performed
            at merge. Type change must not be allowed on merge.
        @tms_test_steps:
         @step: Attempt to load --merge a vcs-cluster item type
            into a cluster item type
         @result: InvalidXMLError should be posted
         @step: Attempt to load --merge a cluster item type
            into a vcs-cluster item type
            @result: InvalidXMLError should be posted
        @tms_test_precondition: files xml_test24_cluster_bug5391.xml,
                             xml_test24_vcscluster_bug5391.xml copied to ms
        @tms_execution_type: Automated

        """
        self.log('info', 'save the cluster value before the test')
        clusters = self.find(
            self.test_node, '/deployments', 'vcs-cluster'
        )
        for cluster in clusters:
            self.backup_path_props(self.test_node, cluster)

        self.log('info', 'Find cluster path')
        cluster_path = self.find(
            self.test_node, "/deployments", "cluster", False)[0]

        self.log('info', '1. Copy cluster XML files onto ms')
        cluster_xml_files = ['xml_test24_cluster_bug5391.xml',
                             'xml_test24_vcscluster_bug5391.xml']
        for xmlfile in cluster_xml_files:
            local_filepath = os.path.dirname(__file__)
            local_xml_filepath = local_filepath + "/xml_files/" \
                + xmlfile
            cluster_xml_filepath = "/tmp/" + xmlfile
            self.copy_file_to(
                self.test_node, local_xml_filepath, cluster_xml_filepath)

        self.log('info', '2. Load the cluster xml into the model')
        self.execute_cli_load_cmd(
            self.test_node, cluster_path,
            "/tmp/xml_test24_cluster_bug5391.xml", args="--merge")

        self.log('info', '3. Attempt to merge a vcs-cluster item type into '
                         'a cluster item type')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, cluster_path,
            "/tmp/xml_test24_vcscluster_bug5391.xml",
            args="--merge", expect_positive=False)

        self.log('info', 'Check expected message is present')
        msg = "InvalidXMLError    " + \
            "Cannot merge from cluster to vcs-cluster"
        self.assertTrue(self.is_text_in_list(msg, stderr))

        self.log('info', '4. Remove imported cluster item type')
        self.execute_cli_remove_cmd(
            self.test_node, cluster_path + "/clusterBug5391")

        self.log('info', '5. Load the vcs cluster xml into the model')
        self.execute_cli_load_cmd(
            self.test_node, cluster_path,
            "/tmp/xml_test24_vcscluster_bug5391.xml", args="--merge")

        self.log('info', '6. Attempt to merge a cluster item type into '
                         'a vcs-cluster item type')
        _, stderr, _ = self.execute_cli_load_cmd(
            self.test_node, cluster_path,
            "/tmp/xml_test24_cluster_bug5391.xml",
            args="--merge", expect_positive=False)

        self.log('info', 'Check expected message is present')
        msg = "InvalidXMLError    " + \
            "Cannot merge from vcs-cluster to cluster"
        self.assertTrue(self.is_text_in_list(msg, stderr))

        self.log('info', '7. Remove imported vcs cluster item type')
        self.execute_cli_remove_cmd(
            self.test_node, cluster_path + "/clusterBug5391")
