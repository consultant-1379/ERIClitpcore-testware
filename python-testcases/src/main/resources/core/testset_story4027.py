'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     May 2014
@author:    Ares
@summary:   Integration test for LITPCDS-4027
            Agile:
                Epic: N/A
                Story: LITPCDS-4027
                Sub-Task: N/A
'''

import os
import test_constants as const
from litp_generic_test import GenericTest
from redhat_cmd_utils import RHCmdUtils


class Story4027(GenericTest):
    """
    LITPCDS-4027:
        As a LITP Developer I want to block plug-ins from making property
        changes to model items via links so that they do not inadvertently make
        unwanted global changes.
    """

    def setUp(self):
        """
        runs before every test to perform required setup
        """
        # call super class setup
        super(Story4027, self).setUp()
        # initialise test items
        self.management_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.plugin_id = 'story4027'
        self.item_type = 'story4027'
        self.collection_type = '{0}-items'.format(self.item_type)

    def tearDown(self):
        """
        runs after every test to perform required cleanup/teardown
        """

        # call super class teardown
        super(Story4027, self).tearDown()

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

    def install_rpms(self):
        """install test plugin rpms"""

        # since the copy_and_install_rpms method in the framework, doesn't
        # check if the package is already installed, we must check if the
        # package does indeed need to be installed - if we don't, and the
        # package is installed, the test will fail
        _, _, rcode = self.run_command(
            self.management_node,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )

        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.join(
                    os.path.dirname(repr(__file__).strip("'")), "plugins"
                ),
                self.plugin_id
            )

            self.assertTrue(
                self.copy_and_install_rpms(
                    self.management_node, local_rpm_paths
                )
            )

    def exec_common_methods(self, model_item, collection_item, item_type,
                                                                name_property):
        """execute common methods to all tests"""

        # As all test cases are obsolete for Story4027
        # Fix Pylint errors by commenting exec_common_methods
        # and replace by pass statement
        pass

#        # get collection path from model
#        model_collection_path = self.find(
#            self.management_node, '/software', collection_item, False)[0]
#
#        # join the model item to be created to the parent collection of items
#        # path
#        model_item_path = os.path.join(
#            model_collection_path, model_item)
#
#        # execute the create command
#        self.execute_cli_create_cmd(
#            self.management_node,
#            model_item_path,
#            item_type,
#            name_property
#        )
#
#        # check the item is created with the default property value expected,
#        # as defined by the test model item extension
#        self.assertEqual(
#            'true',
#            self.execute_show_data_cmd(
#                self.management_node,
#                model_item_path,
#                'updatable'
#            )
#        )
#
#        # for each node, link the created test model item
#        for node in self.find(self.management_node, '/deployments', 'node'):
#            self.execute_cli_link_cmd(
#                self.management_node,
#                os.path.join(
#                    self.find(
#                        self.management_node, node, 'software-item', False
#                    )[0],
#                    model_item
#                ),
#                item_type,
#                name_property
#            )

    def obsolete_01_n_update_property_of_reference(self):
        """
        Description:
            Given a query item has returned a reference to a model item that
            has a plugin updatabale property, when the plugin attempts to
            update the property, the update will fail, an exception will be
            logged and the plan execution will fail.

        Pre-Test Steps:
            1.  Create a new dummy item type extension as described in the
                LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to make use of a plugin updatable property and
                query item
            4.  Build and install the item type extension
            5.  Build and install the plugin

        Steps:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli link command to link the test item to a node(s)
            3.  Execute the cli create_plan command
            4.  Execute the cli run_plan command
            4.  Check the plan execution fails
            5.  Check /var/log/messages for logged exception

        Result:
            The plan execution will fail and the error/exception will be logged
            to /var/log/messages

        TC no longer valid due to link removal. Inherit not applicable to this
        case as updates to children are allowed.
        """

        # install plugin rpm
        self.install_rpms()

        # execute the common test methods
        self.exec_common_methods(
            self.item_type,
            'software-item',
            self.item_type,
            'name=\'test_01\''
        )

        # execute the create_plan command
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the run_plan command and wait for plan to fail
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.management_node,
                const.PLAN_FAILED
            )
        )

        # check /var/log/messages for error
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                const.GEN_SYSTEM_LOG_PATH,
                ['Cannot update field updatable in link.*story4027']
            ),
            su_root=True
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def obsolete_02_n_update_property_of_child_of_reference(self):
        """
        Description:
            Given a query item has returned a child object of a reference to a
            model item that has a plugin updatabale property, when the plugin
            attempts to update the property, the update will fail, an exception
            will be logged and the plan execution will fail.

        Pre-Test Steps:
            1.  Create a new dummy item type extension as described in the
                LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to make use of a plugin updatable property and
                query item
            4.  Build and install the item type extension
            5.  Build and install the plugin

        Steps:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli create command to create a child test item,
                under the test item, in the model
            3.  Execute the cli link command to link the test item to a node(s)
            4.  Execute the cli create_plan command
            5.  Execute the cli run_plan command
            6.  Check the plan execution fails
            7.  Check /var/log/messages for logged exception

        Result:
            The plan execution will fail and the error/exception will be logged
            to /var/log/messages

        TC no longer valid due to link removal. Inherit not applicable to this
        case as updates to children are allowed.
        """

        # install plugin rpms
        self.install_rpms()

        # execute common test methods to create the collection item
        self.exec_common_methods(
            '{0}_collection'.format(self.item_type),
            'software-item',
            self.collection_type,
            'name=\'test_02\''
        )

        # execute the common methods to create the child model item of created
        # collection item
        self.exec_common_methods(
            '{0}_item'.format(self.item_type),
            self.item_type,
            self.item_type,
            'name=\'test_02\''
        )

        # execute the create_plan command
        self.execute_cli_createplan_cmd(self.management_node)

        # execute the run_plan command and wait for plan to fail
        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.management_node,
                const.PLAN_FAILED
            )
        )

        # check /var/log/messages for error
        stdout, stderr, rcode = self.run_command(
            self.management_node,
            self.rhc.get_grep_file_cmd(
                const.GEN_SYSTEM_LOG_PATH,
                ['Cannot update field updatable in link.*story4027']
            ),
            su_root=True
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

    def obsolete_03_p_retrieve_model_item_from_ref_update_property(self):
        """
        Description:
            Given a query item has returned a reference, or child item, to a
            model item that has a plugin updatabale property, when the plugin
            queries the model item, by following the reference back to the
            actual model item; when the plugin attempts to update the model
            item's property, the update will succeed and the plan execution
            will complete successfully.

        Pre-Test Steps:
            1.  Create a new dummy item type extension as described in the
                LITP 2 SDK
            2.  Create a new dummy plugin as described in the LITP 2 SDK
            3.  Edit the plugin to make use of a plugin updatable property and
                query item
            4.  Build and install the item type extension
            5.  Build and install the plugin

        Steps:
            1.  Execute the cli create command to create a test item in the
                model
            2.  Execute the cli create command to create a child test item,
                under the test item, in the model
            3.  Execute the cli link command to link the test item to a node(s)
            4.  Execute the cli create_plan command
            5.  Execute the cli run_plan command
            6.  Check the plan execution succeeds
            7.  Check test item property and child test item property are
                successfully updated

        Result:
            The plan execution will succeed and the properties for both the
            test item and its child will be updated

        TC no longer valid due to link removal. Inherit not applicable to this
        case as updates to children are allowed.
        """

        # install plugin rpm
        self.install_rpms()

        # execute the common test methods to created the model item extension
        # collection of test items
        self.exec_common_methods(
            '{0}_collection'.format(self.item_type),
            'software-item',
            self.collection_type,
            'name=\'test_03\''
        )

        # execute the common test methods to create the child model items for
        # the test item collection
        self.exec_common_methods(
            '{0}_item'.format(self.item_type),
            self.item_type,
            self.item_type,
            'name=\'test_03\''
        )

        # execute the create_plan command and wait for plan execution to
        # complete
        self.execute_cli_createplan_cmd(self.management_node)

        self.execute_cli_runplan_cmd(self.management_node)
        self.assertTrue(
            self.wait_for_plan_state(
                self.management_node,
                const.PLAN_COMPLETE
            )
        )

        # check the collection item updatable property is successfully updated
        for model_item in self.find(self.management_node, '/software',
                                                        self.collection_type):
            self.assertEqual(
                'false',
                self.execute_show_data_cmd(
                    self.management_node, model_item, 'updatable')
            )

        # check the child of collection model item updatable property is
        # successfully updated
        for model_item in self.find(self.management_node, '/software',
                                                            self.item_type):
            self.assertEqual(
                'false',
                self.execute_show_data_cmd(
                    self.management_node, model_item, 'updatable')
            )
