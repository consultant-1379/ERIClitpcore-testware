'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2014
@author:    Ares
@summary:   Integration test for ___
            Agile:
                Epic: N/A
                Story: LITPCDS-4347
                Sub-Task: N/A
'''

import os
import test_constants as const
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils


class Story4347(GenericTest):
    """
    LITPCDS-4347:
    As a LITP Developer, I want subclass model items so that I can more
    efficiently create populated items, but with their own configurable
    properties.
    """

    def setUp(self):
        """runs before every test to perform required setup"""

        # call super class setup
        super(Story4347, self).setUp()
        self.management_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.item = 'story_4347'
        self.path = '/tmp'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""

        # call super class teardown
        super(Story4347, self).tearDown()

    def copy_xml_file_to_management_node(self, filename):
        """copy the XML file required for test to the test node"""

        # locate given XML file in test file directory and copy it to the
        # management server to be used by the test
        self.assertTrue(
            self.copy_file_to(
                self.management_node,
                os.path.join(
                    os.path.abspath(
                        os.path.join(os.path.dirname(__file__), 'xml_files'),
                    ),
                    filename
                ),
                self.path
            )
        )

    @attr('all', 'revert', 'story4347', 'story4347_tc01', 'cdb_priority1')
    def test_01_p_inherit_export_xml(self):
        """
        Description:
        Given I have executed the CLI inherit command to reference(subclass) a
        model item for my deployment, when I execute the CLI export command to
        create an XML for the reference, then a new inherit type will be
        included in the XML.

        Steps:
            1.  Execute the CLI create command to create a package item in the
                software model
            2.  Execute the CLI create command to create a package-list item in
                the software model
            3.  Execute the CLI create command to create a package item child
                of the package-list
            4.  Execute the CLI inherit command to reference the created
                package to a node
            5.  Execute the CLI inherit command to reference the created
                package-list to a node
            6.  Execute the CLI export command to export the reference to an
                XML file
            7.  Check the XML file is successfully created with the model items

        Restore Steps:
            1.  Execute the CLI remove command to remove the package reference
                from the node
            2.  Execute the CLI remove command to remove the package-list
                reference from the node
            3.  Execute the CLI remove command to remove the package from the
                software model
            4.  Execute the CLI remove command to remove the package-list from
                the software model
            5.  Remove the XML file created by the test

        Result:
        The inherited reference must be successfully exported to an XML file.
        """

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get /ms/items path
        ms_ = self.find(
            self.management_node, '/ms', 'software-item', False, find_refs=True
        )[0]

        # create package item under software item path
        package_path = os.path.join(
            software_item_path, '{0}_1'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_path, 'package', 'name=\'finger\''
        )

        # create inherit reference of package to node
        inherit_ref_path = os.path.join(ms_, '{0}_1'.format(self.item))
        self.execute_cli_inherit_cmd(
            self.management_node, inherit_ref_path, package_path
        )

        # execute the show command and check property is inherited
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_path, 'name', ''
        )
        self.assertEqual('finger [*]', package_name_value)

        # create package list item under software item path
        package_list_path = os.path.join(
            software_item_path, '{0}_list'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_list_path, 'package-list',
            'name=\'{0}\''.format(self.item)
        )

        # create package item under package list item
        self.execute_cli_create_cmd(
            self.management_node,
            os.path.join(
                package_list_path, 'packages/{0}_2'.format(self.item)
            ),
            'package', 'name=\'tftp\''.format(self.item)
        )

        # create inherit reference of package list to node
        inherit_ref_collection = os.path.join(ms_, self.item)
        self.execute_cli_inherit_cmd(
            self.management_node, inherit_ref_collection, package_list_path,
            'name=\'{0}_overwrite\''.format(self.item)
        )

        # execute the show command and check property is overwritten
        package_list_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_collection, 'name', ''
        )
        self.assertEqual(
            '{0}_overwrite'.format(self.item), package_list_name_value
        )

        # execute the show command on child of reference and check property is
        # inherited
        inherit_ref_collection_child = os.path.join(
            inherit_ref_collection, 'packages/{0}_2'.format(self.item)
        )
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_collection_child, 'name', ''
        )
        self.assertEqual('tftp [*]', package_name_value)

        # update/overwrite a property of child of reference
        self.execute_cli_update_cmd(
            self.management_node,
            inherit_ref_collection_child,
            'name=\'firefox\''
        )

        # execute the show command on child of reference and check property is
        # overwritten now
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_collection_child, 'name', ''
        )
        self.assertEqual('firefox', package_name_value)

        # try to export the child of the reference
        self.execute_cli_export_cmd(
            self.management_node, inherit_ref_collection_child,
            '{0}/{1}_export_child.xml'.format(self.path, self.item)
        )

        # try to load child
        self.execute_cli_load_cmd(
            self.management_node,
            os.path.join(inherit_ref_collection, 'packages'),
            '{0}/{1}_export_child.xml'.format(self.path, self.item), '--merge'
        )

        # construct XML filepath
        filepath = os.path.join(
            self.path, '{0}_export_no_overwrite.xml'.format(self.item)
        )

        # export inherit reference path to XML where the property was not
        # overwritten
        self.execute_cli_export_cmd(
            self.management_node, inherit_ref_path, filepath
        )

        # grep the exported XML file
        std_out, std_err, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, [self.item, 'finger']
            )
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], std_err)
        self.assertNotEqual([], std_out)

        # construct XML filepath
        filepath = os.path.join(
            self.path, '{0}_export_overwrite.xml'.format(self.item)
        )

        # export inherit reference path to XML where the property was
        # overwritten
        self.execute_cli_export_cmd(
            self.management_node, inherit_ref_collection,
            '/tmp/{0}_export_overwrite.xml'.format(self.item)
        )

        # grep the exported XML file
        std_out, std_err, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                filepath, [self.item, 'firefox']
            )
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], std_err)
        self.assertNotEqual([], std_out)

    @attr('all', 'revert', 'story4347', 'story4347_tc02', 'cdb_priority1')
    def test_02_n_inherit_load_xml_no_source(self):
        """
        Description:
        Given I have an XML inherit reference file, when I execute the CLI load
        command to import the reference type into my deployment model, if the
        source path for the reference does not exist in the model, then the
        reference import will fail with an error message.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
            1.  Execute the CLI load command to import an inherit reference XML
                file into the model, that uses a non-existent source path
            2.  Check for error message

        Result:
        The attempted load of the inherited reference will fail with an error
        for missing source path.
        """

        # copy the required XML file to the management_node
        self.copy_xml_file_to_management_node('no_source_path.xml')

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # execute the load command and check for error
        _, std_err, _ = self.execute_cli_load_cmd(
            self.management_node, node,
            os.path.join(self.path, 'no_source_path.xml'),
            expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InvalidXMLError', std_err)
        )
        self.assertTrue(
            self.is_text_in_list(
                'attribute \'source_path\' is required but missing', std_err
            )
        )

    @attr('all', 'revert', 'story4347', 'story4347_tc03', 'cdb_priority1')
    def test_03_n_inherit_load_invalid_xml_file(self):
        """
        Description:
        Given I have an XML inherit reference file, which is syntactically
        incorrect/inconsistent with the XSD schema definition, when I execute
        the CLI load command, the reference import will fail with an error
        message.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
            1.  Execute the CLI load command to import an invalid inherit
                reference XML file into the model
            2.  Check for error message

        Result:
        The attempted load of the inherited reference will fail with an error
        for invalid syntax in the XML file.
        """

        # copy the required XML file to the management_node
        self.copy_xml_file_to_management_node('invalid_inherit_schema.xml')

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # create package item under software item path
        self.execute_cli_create_cmd(
            self.management_node,
            os.path.join(software_item_path, '{0}_1'.format(self.item)),
            'package', 'name=\'finger\''
        )

        # execute the load command and check for error
        _, std_err, _ = self.execute_cli_load_cmd(
            self.management_node, node,
            os.path.join(self.path, 'invalid_inherit_schema.xml'),
            expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InvalidXMLError', std_err)
        )
        self.assertTrue(
            self.is_text_in_list('package-inhert', std_err)
        )

    @attr('all', 'revert', 'story4347', 'story4347_tc04', 'cdb_priority1')
    def test_04_n_inherit_load_invalid_xml_property_value_update(self):
        """
        Description:
        Given I have an XML inherit reference file, which contains an invalid
        property value, when I execute the CLI load (--merge) command, the
        reference import will fail, with an error message.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
            1.  Execute the CLI load command to import an inherit reference XML
                file, that contains an invalid property value, into the model
            2.  Check for error message
            3.  Execute the CLI load --merge command to import an inherit
                reference XML file, that contains an invalid property value,
                into the model
            4.  Check for error message

        Result:
        The attempted load of the inherited reference will fail with an error
        for invalid property value.
        """

        # copy the required XML file to the management_node
        self.copy_xml_file_to_management_node('invalid_inherit_property.xml')
        self.copy_xml_file_to_management_node(
            'invalid_inherit_property_value.xml'
        )

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # create package item under software item path
        self.execute_cli_create_cmd(
            self.management_node,
            os.path.join(software_item_path, '{0}_1'.format(self.item)),
            'package', 'name=\'finger\' version=\'0.17\' release=\'39.el6\''
        )

        # execute the load command and check for error
        _, std_err, _ = self.execute_cli_load_cmd(
            self.management_node, node,
            os.path.join(self.path, 'invalid_inherit_property.xml'),
            expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InvalidXMLError', std_err)
        )
        self.assertTrue(
            self.is_text_in_list(
                'attribute \'sourc_path\'',
                std_err
            )
        )

        _, std_err, _ = self.execute_cli_load_cmd(
            self.management_node, node,
            os.path.join(self.path, 'invalid_inherit_property_value.xml'),
            expect_positive=False
        )
        self.assertTrue(
            self.is_text_in_list('InvalidLocationError', std_err)
        )

    @attr('all', 'revert', 'story4347', 'story4347_tc05', 'cdb_priority1')
    def test_05_p_inherit_load_xml_check_inherited_reference(self):
        """
        Description:
        Given I have an XML inherit reference file, when I execute the CLI load
        command, the reference import will succeed and the source item will be
        reference.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
            1.  Execute the CLI create command to create a package item in the
                software model
            2.  Execute the CLI create command to create a package-list item in
                the software model
            3.  Execute the CLI create command to create a package child item
                of the package-list
            4.  Execute the CLI load command to import an inherit reference XML
                file, referencing the created package
            5.  Execute the CLI load command to import an inherit reference XML
                file, referencing the created package-list
            6.  Check the package is referenced with all the properties
                inherited from the source
            7.  Check the package-list is referenced with all the properties
                inherited from the source

        Restore Steps:
            1.  Execute the CLI remove command to remove the package reference
                from the node
            2.  Execute the CLI remove command to remove the package-list
                reference from the node
            3.  Execute the CLI remove command to remove the package from the
                software model
            4.  Execute the CLI remove command to remove the package-list from
                the software model
            5.  Remove the XML file created by the test

        Result:
        The inherited reference must be successfully loaded(imported) from an
        XML file.
        """

        # copy the required XML files to the management_node
        self.copy_xml_file_to_management_node('valid_inherit_package.xml')
        self.copy_xml_file_to_management_node('valid_inherit_package_list.xml')

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # create package item under software item path
        package_path = os.path.join(
            software_item_path, '{0}_1'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_path, 'package', 'name=\'finger\''
        )

        # get software item path of node
        node_software_item_path = self.find(
            self.management_node, node, 'software-item', False, find_refs=True
        )[0]

        # execute the load command
        self.execute_cli_load_cmd(
            self.management_node, node_software_item_path,
            os.path.join(self.path, 'valid_inherit_package.xml')
        )

        # execute the show command and check property is inherited
        inherit_ref_path = os.path.join(node, 'items/{0}_1'.format(self.item))
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_path, 'name', ''
        )
        self.assertEqual('finger [*]', package_name_value)

        # create package list item under software item path
        package_list_path = os.path.join(
            software_item_path, '{0}_list'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_list_path, 'package-list',
            'name=\'{0}\''.format(self.item)
        )

        # create package item under package list item
        self.execute_cli_create_cmd(
            self.management_node,
            os.path.join(
                package_list_path, 'packages/{0}_2'.format(self.item)
            ),
            'package', 'name=\'tftp\''.format(self.item)
        )

        # execute the load command
        self.execute_cli_load_cmd(
            self.management_node, node_software_item_path,
            os.path.join(self.path, 'valid_inherit_package_list.xml')
        )

        # execute the show command and check property is not overwritten
        inherit_ref_collection = os.path.join(
            node_software_item_path, '{0}_list'.format(self.item)
        )
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_collection, 'name', ''
        )
        self.assertEqual('{0} [*]'.format(self.item), package_name_value)
        # execute the show command on child of reference and check property is
        # inherited also
        inherit_ref_collection_child = os.path.join(
            inherit_ref_collection, 'packages/{0}_2'.format(self.item)
        )
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_collection_child, 'name', ''
        )
        self.assertEqual('tftp [*]', package_name_value)

    @attr('all', 'revert', 'story4347', 'story4347_tc06', 'cdb_priority1')
    def test_06_p_inherit_load_xml_merge_check_reference_overwritten(self):
        """
        Description:
        Given I have an XML inherit reference file, when I execute the CLI load
        --merge command, the reference import will succeed and the source item
        will be referenced and, where applicable, properties will be
        overwritten.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
        1.  Execute the CLI create command to create a package item in the
            software model
        2.  Execute the CLI load command to import an inherit reference XML
            file, intended to reference the created package
        3.  Execute the CLI load --merge command to import an inherit reference
            XML file, intended to overwrite the created package property
        4.  Check that a property is overwritten
        5.  Check that another property is not overwritten

        Restore Steps:
        1.  Execute the CLI remove command to remove the package reference from
            the node
        2.  Execute the CLI remove command to remove the package from the
            software model
        3.  Remove the XML file created by the test

        Result:
        The inherited reference must be successfully loaded(imported) from an
        XML file and any properties that must be overwritten, are successfully
        done so.
        """

        # copy the required XML files to the management_node
        self.copy_xml_file_to_management_node('valid_inherit_package.xml')
        self.copy_xml_file_to_management_node('valid_inherit_overwrite.xml')

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get a node from the model
        node = self.find(self.management_node, '/deployments', 'node')[0]

        # create package item under software item path
        package_path = os.path.join(
            software_item_path, '{0}_1'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_path, 'package',
            'name=\'finger\' version=\'0.17\' release=\'39.el6\''
        )

        # get software item path of node
        node_software_item_paths = self.find(
            self.management_node, node, 'software-item', False, find_refs=True
        )

        node_software_item_paths[:] = [
            node_software_item_path
            for node_software_item_path in node_software_item_paths
            if '/items' in node_software_item_path
        ]

        for node_software_item_path in node_software_item_paths:
            # execute the load command
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_package.xml')
            )

            # execute the show command and check property is inherited
            inherit_ref_path = os.path.join(
                node_software_item_path, '{0}_1'.format(self.item)
            )
            package_name_value = self.get_props_from_url(
                self.management_node, inherit_ref_path, 'name', ''
            )
            self.assertEqual('finger [*]', package_name_value)
            package_version_value = self.get_props_from_url(
                self.management_node, inherit_ref_path, 'version', ''
            )
            self.assertEqual('0.17 [*]', package_version_value)

        # get a node from the list to use for overwrite
        node_overwrite = node_software_item_paths[0]

        # execute the load command with --merge
        self.execute_cli_load_cmd(
            self.management_node, node_overwrite,
            os.path.join(self.path, 'valid_inherit_overwrite.xml'), '--merge'
        )

        # execute the show command and check property is overwritten
        inherit_ref_path = os.path.join(
            node_overwrite, '{0}_1'.format(self.item)
        )
        package_name_value = self.get_props_from_url(
            self.management_node, inherit_ref_path, 'name', ''
        )
        self.assertEqual('finger [*]', package_name_value)
        package_version_value = self.get_props_from_url(
            self.management_node, inherit_ref_path, 'version', ''
        )
        self.assertEqual('0.18', package_version_value)

        for node_software_item_path in node_software_item_paths:
            if node_software_item_path != node_overwrite:
                # for all other ndoes execute the show command and check
                # propertye is inherited
                package_name_value = self.get_props_from_url(
                    self.management_node, inherit_ref_path, 'name', ''
                )
                self.assertEqual('finger [*]', package_name_value)
                package_version_value = self.get_props_from_url(
                    self.management_node, inherit_ref_path, 'version', ''
                )
                self.assertEqual('0.17 [*]', package_version_value)

    def obsolete_07_p_inherit_load_xml_check_states(self):
        """
        Obsolete - already tested by UTs

        Description:
        Given I have an XML inherit reference file, when I execute the CLI load
        (--merge) command, to reference a model item to the deployment model,
        the reference item state(s) will reflect each change to the reference.

        Pre-Test Steps:
            1.  Copy test related XML files

        Steps:
            1.  Execute the CLI create command to create a package item in the
                software model
            2.  Execute the CLI load command to import an inherit reference XML
                file, referencing the created package to a node
            3.  Execute the CLI load command to import an inherit reference XML
                file, referencing the created package to a second node
            4.  Execute the CLI create_plan command
            5.  Check the source item state is Initial
            6.  Check the reference state is Initial
            7.  Execute the CLI run_plan command
            8.  Wait for the plan to successfully complete
            9.  Check the source item state is Applied
            10. Check the reference state is Applied on all nodes
            11. Execute the CLI load --merge command to import an inherit
                reference XML file, overwriting a property
            12. Check the source item state is Applied
            13. Check the reference state is Applied on node where the
                reference was not overwritten
            14. Check the property value on node where the reference was not
                overwritten matches source item property value
            15. Check the reference state is Updated on node where the
                reference was overwritten
            16. Check the property value on node where the reference was
                overwritten does not match source item property value

        Restore Steps:
            1.  Execute the CLI remove command to remove the package reference
                from the node(s)
            2.  Execute the CLI create_plan command
            3.  Execute the CLI run_plan command
            4.  Wait for the plan to successfully complete
            5.  Execute the CLI remove command to remove the package from the
                software model
            6.  Execute the CLI create_plan command
            7.  Execute the CLI run_plan command
            8.  Wait for the plan to successfully complete
            9.  Remove the XML file created by the test

        Result:
        The states of inherit reference items must reflect each change to the
        reference.
        """

        inherited_ref_paths = list()
        node_software_item_paths = list()

        # copy the required XML files to the management_node
        self.copy_xml_file_to_management_node('valid_inherit_package.xml')
        self.copy_xml_file_to_management_node('valid_inherit_overwrite.xml')

        # get /software/items path
        software_item_path = self.find(
            self.management_node, '/software', 'software-item', False
        )[0]

        # get a node from the model
        nodes = self.find(self.management_node, '/deployments', 'node')

        # create package item under software item path
        package_path = os.path.join(
            software_item_path, '{0}_1'.format(self.item)
        )
        self.execute_cli_create_cmd(
            self.management_node, package_path, 'package',
            'name=\'finger\' version=\'0.17-39.el6\''
        )

        for node in nodes:
            # get software item path of node
            node_software_item_path = self.find(
                self.management_node, node, 'software-item', False
            )[0]
            node_software_item_paths.append(node_software_item_path)

            # execute the load command
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_package.xml')
            )

            # check item state is Initial
            inherit_ref_path = os.path.join(
                node_software_item_path, '{0}_1'.format(self.item)
            )
            inherited_ref_paths.append(inherit_ref_path)
            self.assertEqual(
                'Initial',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'state'
                )
            )

        try:
            # execute the create_plan command
            self.execute_cli_createplan_cmd(self.management_node)

            # execute the run_plan command and wait for plan completion
            self.execute_cli_runplan_cmd(self.management_node)
            self.assertTrue(
                self.wait_for_plan_state(
                    self.management_node, const.PLAN_COMPLETE
                )
            )

            for inherit_ref_path in inherited_ref_paths:
                # check item state is Applied
                self.assertEqual(
                    'Applied',
                    self.execute_show_data_cmd(
                        self.management_node, inherit_ref_path, 'state'
                    )
                )

            node_software_item_path = node_software_item_paths[0]
            for inherit_path in inherited_ref_paths:
                if node_software_item_path in inherit_path:
                    inherit_ref_path = inherit_path

            # test LITPCDS-5237 with --merge
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_package.xml'), '--merge'
            )
            self.execute_cli_createplan_cmd(
                self.management_node, expect_positive=False
            )

            self.assertEqual(
                'Applied',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'state'
                )
            )
            self.assertEqual(
                '0.17-39.el6 [*]',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'version'
                )
            )
            # test LITPCDS-5237 with --replace
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_package.xml'),
                '--replace'
            )
            self.execute_cli_createplan_cmd(
                self.management_node, expect_positive=False
            )

            self.assertEqual(
                'Applied',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'state'
                )
            )
            self.assertEqual(
                '0.17-39.el6 [*]',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'version'
                )
            )

            # restore original value from source
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_overwrite.xml'),
                '--replace'
            )
            self.execute_cli_update_cmd(
                self.management_node, inherit_ref_path, 'version=\'\''
            )
            self.assertEqual(
                '0.17-39.el6 [*]',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'version'
                )
            )
            self.assertEqual(
                'Applied',
                self.execute_show_data_cmd(
                    self.management_node, node_software_item_path, 'state'
                )
            )

            # execute the load command with --merge to update the version
            # property
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_overwrite.xml'),
                '--merge'
            )
            self.assertEqual(
                '0.18',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'version'
                )
            )
            self.assertEqual(
                'Updated',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'state'
                )
            )

            # restore original value from source
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_package.xml'),
                '--replace'
            )
            self.assertEqual(
                '0.17-39.el6 [*]',
                self.execute_show_data_cmd(
                    self.management_node, inherit_ref_path, 'version'
                )
            )
            self.assertEqual(
                'Applied',
                self.execute_show_data_cmd(
                    self.management_node, node_software_item_path, 'state'
                )
            )

            node_software_item_path = node_software_item_paths[0]

            # execute the load command
            self.execute_cli_load_cmd(
                self.management_node, node_software_item_path,
                os.path.join(self.path, 'valid_inherit_overwrite.xml'),
                '--merge'
            )

            for inherit_ref_path in inherited_ref_paths:
                if node_software_item_path in inherit_ref_path:
                    # check property value is overwritten
                    self.assertEqual(
                        '0.18',
                        self.execute_show_data_cmd(
                            self.management_node, inherit_ref_path, 'version'
                        )
                    )
                    # check item state is Updated
                    self.assertEqual(
                        'Updated',
                        self.execute_show_data_cmd(
                            self.management_node, inherit_ref_path, 'state'
                        )
                    )
                else:
                    # check value of node is not overwritten
                    self.assertEqual(
                        '0.17-39.el6 [*]',
                        self.execute_show_data_cmd(
                            self.management_node, inherit_ref_path, 'version'
                        )
                    )
                    # check item state is Applied
                    self.assertEqual(
                        'Applied',
                        self.execute_show_data_cmd(
                            self.management_node, inherit_ref_path, 'state'
                        )
                    )

        except AssertionError:
            raise

        finally:
            # cleanup
            for inherit_ref_path in inherited_ref_paths:
                self.execute_cli_remove_cmd(
                    self.management_node, inherit_ref_path
                )
                self.execute_cli_createplan_cmd(self.management_node)
                self.execute_cli_runplan_cmd(self.management_node)
                self.wait_for_plan_state(
                    self.management_node, const.PLAN_COMPLETE
                )
            self.execute_cli_remove_cmd(self.management_node, package_path)
            self.execute_cli_createplan_cmd(self.management_node)
            self.execute_cli_runplan_cmd(self.management_node)
            self.wait_for_plan_state(self.management_node, const.PLAN_COMPLETE)
