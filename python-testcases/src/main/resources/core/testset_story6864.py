"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2014; Refactored Feb 2019
@author:    Ares; Aisling Stafford
@summary:   LITPCDS-6864:
            As a LITP user, I want the ability to restore the model to the
            latest successful model
"""

import os
import test_constants as const
from litp_generic_test import GenericTest, attr
from redhat_cmd_utils import RHCmdUtils

LOCAL_DIR = os.path.dirname(__file__)


class Story6864(GenericTest):
    """
    LITPCDS-6864:
    As a LITP user, I want the ability to restore the model to the latest
    successful model
    """

    def setUp(self):
        """runs before every test"""
        super(Story6864, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.plugin_id = 'story6864'
        self.ms_configs = self.find(self.ms_node, '/ms',
                                    'collection-of-node-config')[0]

        self.item1_path = '{0}/story6864_tc02_only'.format(self.ms_configs)
        self.item2_path = '{0}/bug7900_only'.format(self.ms_configs)

        self.test_items = [self.item1_path, self.item2_path]

        self.expected_props = [{'name': 'foo'},
                             {'surname': 'bar', 'rename': 'foo'}]

        self.rpm_path = os.path.abspath('{0}/plugins'.format(LOCAL_DIR))

        self.upgrade_rpm_path = os.path.abspath(
                                '{0}/upgrade_plugins'.format(LOCAL_DIR))

    def tearDown(self):
        """runs after every test"""
        super(Story6864, self).tearDown()

    def install_rpms(self, node, local_rpm_dir, rpm_filter):
        """
        Description:
            Install RPMs that match the given filter on MS
        Args:
            node (str): The node on which to install the RPMs
            local_rpm_dir (str): The directory where RPM files are located
            rpm_filter (str): Pattern used to select the RPMs required for
                              testing
        """

        rpms = self.get_local_rpm_path_ls(local_rpm_dir, rpm_filter)

        rpms_to_install = []

        for rpm in rpms:

            pkg_name = self.run_command_local(
                self.rhc.get_package_name_from_rpm(rpm))[0]

            pkg_installed = self.check_pkgs_installed(node, pkg_name)
            if not pkg_installed:
                rpms_to_install.append(rpm)

        if rpms_to_install:
            self.assertTrue(self.copy_and_install_rpms(node, rpms_to_install),
                            "RPM's did not install successfully")

    def upgrade_plugin(self):
        """
        Description:
            Check plugin_id is registered with the model and then upgrade
            the rpm to force the migration operations
        """
        self.log('info', 'Stopping puppet for RPM upgrade')
        self.stop_service(self.ms_node, 'puppet')

        try:
            local_rpms = self.get_local_rpm_path_ls(self.upgrade_rpm_path,
                                                    self.plugin_id)
            pkg_names = []
            for rpm in local_rpms:
                self.assertTrue(self.copy_file_to(self.ms_node,
                                                  rpm,
                                                  const.LITP_PKG_REPO_DIR,
                                                  root_copy=True,
                                                  add_to_cleanup=False),
                                'All RPMs were not copied to "{0}" '
                                'successfully'.format(const.LITP_PKG_REPO_DIR))

                pkg_name = self.run_command_local(
                self.rhc.get_package_name_from_rpm(rpm))[0]

                pkg_names.append(pkg_name[0])

            self.run_command(self.ms_node, self.rhc.get_createrepo_cmd(
                             const.LITP_PKG_REPO_DIR), su_root=True,
                             default_asserts=True)

            self.upgrade_rpm_on_node(self.ms_node, pkg_names)

        finally:
            self.start_service(self.ms_node, 'puppet')
            self.restart_litpd_service(self.ms_node)

    def create_item(self, item_path):
        """
        Description: Create item type "story6864-node-config" on the MS

        Args:
            item_path (str): Path to the item to create
        """

        self.execute_cli_create_cmd(self.ms_node, item_path,
                                    "story6864-node-config")

    def verify_item_state(self, item_path, expected_props, expected_state):
        """
        Description: Verifies the state of the item and verifies expected
                     properties and values of the item
        Args:
            item_path (str): Path to the item
            expected_props (lst): List of properties and values expected
            expected_state (str): Expected state of the item in the model
        """

        self.assertTrue(self.is_expected_state(self.ms_node,
                        item_path, expected_state),
                        'item "{0}" not in expected state "{1}"'.format(
                                                        item_path,
                                                        expected_state))

        item_props = self.get_props_from_url(self.ms_node,
                                                  item_path)

        missing_props = ['name']

        if len(expected_props) == 1:
            missing_props = ['rename', 'surname']

        for prop, value in item_props.iteritems():

            self.assertEqual(expected_props[prop], value,
                                'unexpected value "{0}" for property '
                                ' "{1}"'.format(value, prop))

            for missing_prop in missing_props:
                self.assertNotEqual(missing_prop, prop, 'Unexpected prop '
                                '"{0}" found'.format(missing_prop))

    @attr('all', 'non-revert', 'story6864', '6864_tc02')
    def test_02_p_restore_model_upgrade_migration(self):
        """
        @tms_id: litpcds_6864_tc02
        @tms_requirements_id: LITPCDS-6864
        @tms_title: Verify that "restore_model" doesn't revert model migration.
        @tms_description: Verify that given an applied LITP deployment where
            the model is updated, when an extension is upgraded using a
            migration script, if the "litp restore_model" command is executed,
            then the update will be reverted in the model but anything added
            by the upgrade process will remain in the model.
            NOTE: also LITPCDS-7900 bugfix
        @tms_test_steps:
        @step: create and deploy an item (item1) of type "story6864_tc02_only"
        @result: Item deployed successfully
        @step: check state and properties of created model item
        @result: The item is in "Applied" state
        @result: The "name" property is set to "foo"
        @result: The "surname" and "rename" properties do not exist
        @step: Create another item (item2) of type "story6864_tc02_only"
               in the model
        @result: Item created successfully
        @step: Create the plan
        @result: Plan created successfully
        @step: Upgrade the "story6864_tc02_only" extension
        @result: Extension upgraded successfully
        @result: Plan state has been set to "Invalid" (bug LITPCDS-7900)
        @result: Applied item1's state transitioned to "Updated"
        @result: Property "name" has been removed from item1
        @result: Property "surname" of item1 is set to "bar"
        @result: Property "rename" of item1 is set to "foo"
        @result: item2's state is still "Initial"
        @result: Property "name" has been removed from item2
        @result: Property "surname" of item2 is set to "bar"
        @result: Property "rename" of item2 is set to "foo"
        @step: Issue a "litp remove" command on item1
        @result: item1 is in "ForRemoval" state
        @step: Execute the "litp restore_model" command and verify
               that migration changes on item remain intact
        @result: item1's state transitioned to "Updated"
        @result: All properties of item1 remained unchanged
        @result: item2 is no longer in the model
        @tms_test_precondition: A dummy plugin and extension of type
            "story6864_tc02_only" is available. An upgraded version of the same
            plugin and extension that will change the property of items of
            type "story6864_tc02_only" via migration script is available
        @tms_execution_type: Automated
        """

        self.log('info', '1. Install plugin required for this test')

        self.install_rpms(self.ms_node, self.rpm_path, self.plugin_id)

        try:
            self.log('info', '2. Create and deploy item "{0}" of type '
                     '"story6864-node-config"'.format(
                                    self.item1_path.split('/')[-1]))

            self.create_item(self.item1_path)

            self.run_and_check_plan(self.ms_node, const.PLAN_COMPLETE, 10)

            self.log('info', '3. Check that the deployed item has expected'
                     ' "name" property and no "surname" property')

            self.verify_item_state(self.item1_path, self.expected_props[0],
                                   "Applied")

            self.log('info', '4. Create a second item "{0}" of type '
                     '"story6864-node-config" in the model'.format(
                                    self.item2_path.split('/')[-1]))

            self.create_item(self.item2_path)

            self.execute_cli_createplan_cmd(self.ms_node)

            self.assertEqual(const.PLAN_NOT_RUNNING,
                             self.get_current_plan_state(self.ms_node),
                             "Plan is not in state '{0}' as expected"
                             .format(const.PLAN_NOT_RUNNING))

            self.verify_item_state(self.item2_path, self.expected_props[0],
                                   "Initial")

            self.log('info', '5. Upgrade the test plugin and check that the '
                     'plan state has been set to "Invalid" (LITPCDS-7900) '
                     'and check that the migrator\'s addition of a property '
                     'caused the "Applied" item "{0}" to transition to the '
                     '"Updated" state'.format(self.item1_path.split('/')[-1]))

            self.upgrade_plugin()

            self.assertEqual(const.PLAN_INVALID,
                             self.get_current_plan_state(self.ms_node),
                             "Plan not in state '{0}' as expected".format(
                                                      const.PLAN_INVALID))

            self.log('info',
            '6. Check that the created items are in correct state and have '
               'upgraded properties')

            for item, state in zip(self.test_items, ["Updated", "Initial"]):
                self.verify_item_state(item, self.expected_props[1],
                                       state)

            self.log('info', '7. Mark the item "{0}" that was in "Applied" '
                     'State "ForRemoval"'.format(
                                        self.item1_path.split('/')[-1]))

            self.execute_cli_remove_cmd(self.ms_node, self.item1_path)

            self.assertTrue(self.is_expected_state(self.ms_node,
                            self.item1_path, "ForRemoval"),
                            'item "{0}" not in expected state "ForRemoval"'
                            .format(self.item1_path))

            self.log('info', '8. Execute the "litp restore_model" command and '
                     'verify that migration changes on item "{0}" remain '
                     'intact'.format(self.item1_path))

            self.execute_cli_restoremodel_cmd(self.ms_node)

            self.verify_item_state(self.item1_path, self.expected_props[1],
                                   "Updated")

            self.assertEqual([], self.find(self.ms_node,
                                           self.item2_path,
                                           "story6864-node-config",
                                           assert_not_empty=False),
                        'item "{0}" should not be present in the '
                        'model'.format(self.item2_path))

        finally:
            self.log('info', 'FINALLY: Remove the item deployed in this test')
            self.execute_cli_remove_cmd(self.ms_node,
                                        self.item1_path)
            self.run_and_check_plan(self.ms_node, const.PLAN_COMPLETE, 10)
