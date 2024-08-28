'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     July 2014
@author:    Ares
@summary:   Integration test for LITPCDS-1126
                                 LITPCDS-2075
                                 LITPCDS-5568
'''

import os
import test_constants as const
from litp_generic_test import GenericTest
from litp_generic_test import attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils


class Story1126Story2509Story5568(GenericTest):
    """
    LITPCDS-1126:
        As a Site Engineer I want model migration to handle
        addition/updates/deletion+deprecation of item properties, so that I can
        upgrade LITP 2.x.x to 2.x.x+1
    LITPCDS-2509:
        As a Plugin Developer I want to be able to create my own migration
        operations, so that the I can adapt to the new model when upgrading
        LITP 2.x.x to 2.x.x+1
    LITPCDS-5568:
        As a LITP Developer, I want to LITP to support migration of Collections
        in the model migration framework
    """

    def setUp(self):
        """runs before every test to perform required setup"""
        # call super class setup
        super(Story1126Story2509Story5568, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.rhc = RHCmdUtils()
        self.cli = CLIUtils()
        self.plugin_id = 'story1126_2509_5568'
        self.item_type = 'migrations-node-config'
        self.backup_filepath = '/tmp/'
        self.log_path = const.GEN_SYSTEM_LOG_PATH
        self.litp_model_path = const.LITP_LIB_MODEL_PATH
        # due to the nature of these migration tests and the impossibility of
        # removal, especially in negative/failed cases, we need to backup the
        # initial model or else we cannot restore the model at the end of test;
        # Since there are no plans executed, the one test item created is
        # always in Initial state and has no actual impact on the model, so
        # restoration is a non-issue as far as system state consistency goes
        self.db_backup_path = os.path.join(self.backup_filepath, 'LITP.sql')
        self.litpd_service = 'litpd'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        # call super class teardown
        super(Story1126Story2509Story5568, self).tearDown()

    @staticmethod
    def get_local_rpm_paths(path, rpm_substring, tc_identifier=None):
        """
        given a path (which should contain some RPMs) and a substring
        which is present in the RPM names you want, return a list of
        absolute paths to the RPMS that are local to your test
        args:
            path (str): the local path to the rpm files
            rpm_substring (str): a string to denote which rpm to use
                                 i.e. a story number or rpm identifier
            tc_identifier (str): optional identifier only used for upgrade rpms
        """
        # get all RPMs in 'path' that contain 'rpm_substring' in their name
        rpm_names = [rpm for rpm in os.listdir(path) if rpm_substring in rpm]
        if tc_identifier:
            rpm_names[:] = [rpm for rpm in rpm_names if tc_identifier in rpm]
        if not rpm_names:
            return None
        # return a list of absolute paths to the RPMs found in 'rpm_names'
        return [
            os.path.join(rpath, rpm)
            for rpath, rpm in
            zip([os.path.abspath(path)] * len(rpm_names), rpm_names)
        ]

    def backup_db(self):
        """
        Backup LITP's postgres db
        """
        cmd = ("sudo -u postgres -- sh -c 'cd && pg_dump -h {0} -Fc -c"
               " -f {1} litp'".format(self.ms1, self.db_backup_path))
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

    def restore_db_backup(self):
        """
        Restore the LITP database from a backup file
        """
        self.stop_service(self.ms1, 'litpd', assert_success=False)
        cmd = ("sudo -u postgres -- sh -c 'cd && pg_restore -h {0} -d "
               "litp -c {1}'".format(self.ms1, self.db_backup_path))
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)
        self.start_service(self.ms1, 'litpd')

    def install_plugin(self):
        """
        check if a plugin/extension rpm is installed and if not, install it
        """
        _, _, rcode = self.run_command(
            self.ms1,
            self.rhc.check_pkg_installed([self.plugin_id]),
            su_root=True
        )
        if rcode == 1:
            # copy over and install RPMs
            local_rpm_paths = self.get_local_rpm_paths(
                os.path.abspath(
                    os.path.join(os.path.dirname(__file__), 'plugins')
                ),
                self.plugin_id
            )
            self.assertTrue(
                self.copy_and_install_rpms(
                    self.ms1, local_rpm_paths
                )
            )
            self.assertTrue(
                self.is_itemtype_registered(self.ms1, self.item_type)
            )
            return [
                rpm.split('/')[-1].strip('.rpm') for rpm in local_rpm_paths
            ]
        return []

    def upgrade_plugin(self, tc_identifier):
        """upgrade the plugin"""
        local_rpm_paths = list()
        # copy local rpms to the test node if they contains the plugin_id AND
        # tc_identifier strings in their file names
        local_rpm_paths = self.get_local_rpm_paths(
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), 'upgrade_plugins')
            ),
            self.plugin_id,
            tc_identifier
        )
        self.assertNotEqual([], local_rpm_paths)
        for rpm_path in local_rpm_paths:
            self.assertTrue(
                self.copy_file_to(
                    self.ms1, rpm_path,
                    const.LITP_PKG_REPO_DIR, True, False
                )
            )
        # execute the createrepo; yum clean all commands
        _, stderr, rcode = self.run_command(
            self.ms1,
            self.rhc.get_createrepo_cmd(const.LITP_PKG_REPO_DIR),
            su_root=True
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        # execute the yum upgrade command
        # the upgrade plugins for these test have a test case identifier string
        # appended to the rpm file name to assist with copying the rpm required
        # for each test to be executed; however, they are not part of the rpm
        # db information so we need to remove them from the yum upgrade command
        rpm_names = [
            rpm_name.split('/')[-1].replace(
                '_{0}.rpm'.format(tc_identifier), ''
            )
            for rpm_name in local_rpm_paths
        ]
        stdout, stderr, rcode = self.upgrade_rpm_on_node(
            self.ms1, rpm_names
        )
        self.assertEqual(0, rcode)
        self.assertEqual([], stderr)
        self.assertNotEqual([], stdout)

        # Restart litpd service
        stdout, stderr, _ = self.restart_service(self.ms1,
                                                 self.litpd_service,
                                                 assert_success=False,
                                                 su_root=True,
                                                 su_timeout_secs=60)

        self.assertEqual([], stdout)
        self.assertEqual([], stderr)

        return rpm_names

    def remove_plugin(self, rpm_names):
        """
        Description:
            remove the installed plugin
        Args:
            rpm_names (list): rpm to remove from system
        """
        stdout, _, _ = self.remove_rpm_on_node(self.ms1, rpm_names)
        self.assertNotEqual([], stdout)
        self.restore_db_backup()

    def create_ms_config_items(self, item_id, properties):
        """create test items; their type extends node-config base type"""
        test_path = '/ms/configs/{0}'.format(item_id)
        # this path will test updatecollectiontype migration where the item
        # type collection is successfully migrated to its supertype parent i.e.
        # migration-config is subtype of node-config and will be migrated to
        # node-config
        test_collection_path_01 = \
            '{0}/migration_items_collection'.format(test_path)
        # this path will test updatecollectiontype migration where the item
        # type collection will fail because a non empty collection can only be
        # migrated to a super type i.e. migration-config is unrelated to
        # software-item and must fail
        test_collection_path_02 = '{0}/collection_not_empty'.format(test_path)
        # the third collection path "../collection_empty" created by the
        # plugin that does not have children and will be successfully migrated
        # to software-item item type because if the collection is empty the
        # item type may be migrated to anything
        test_collection_path_03 = '{0}/collection_empty'.format(test_path)
        test_paths = (
            test_path, test_collection_path_01, test_collection_path_02,
            test_collection_path_03
        )
        self.execute_cli_create_cmd(
            self.ms1, test_path, self.item_type, properties
        )
        self.execute_cli_create_cmd(
            self.ms1,
            '{0}/migration_config_01'.format(test_collection_path_01),
            'migration-config'
        )
        self.execute_cli_create_cmd(
            self.ms1,
            '{0}/migration_config_02'.format(test_collection_path_02),
            'migration-config'
        )
        return test_paths

    def execute_common(self, item_id, properties, log_msgs, rpm_names,
                       expect_logs=True):
        """execute common methods to all tests"""
        # get the start of the logs for the tests
        start_log_position = self.get_file_len(self.ms1, self.log_path)
        # create test items
        test_paths = self.create_ms_config_items(item_id, properties)
        # get the current test identifier from the name property of the test
        # item and match it to the required upgradable plugin; then upgrade the
        # plugin and save the installed plugin rpms for removal later
        name_value = self.execute_show_data_cmd(
            self.ms1, test_paths[0], 'name'
        )
        # modify the current rpm_names list to remove any extensions previously
        # installed so they do not conflict with the extension upgrades
        rpm_names[:] = [rpm for rpm in rpm_names if 'api' not in rpm]
        rpm_names.extend(self.upgrade_plugin(name_value))

        # check the logs for expected messages
        messages = self.wait_for_log_msg(self.ms1,
                                         log_msgs,
                                         log_len=start_log_position,
                                         return_log_msgs=expect_logs)
        self.assertNotEqual([], messages)
        return test_paths, rpm_names

    def check_values_in_paths(self, expect_values):
        """
        check expected values in model paths
        args:
            expect_values (dict): expected values to check in the model
                                  a dict of dict
                    ex. {model_path: {property: value, property2: value2}}
        """
        for test_path in expect_values.keys():
            for property_key, property_value in \
                expect_values[test_path].iteritems():
                # assert each positive migration operation
                self.assertEqual(
                    property_value,
                    self.execute_show_data_cmd(self.ms1,
                                               test_path,
                                               property_key))

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc01')
    def test_01_n_add_property_missing_fail_service_start(self):
        """
        Description:
            A negative test to add a property to the model during a LITP
            plugin upgrade, using a migration script, even though the
            property doesn't exist in the upgraded plugin code.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to AddProperty()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check add property failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The AddProperty method must fail with error message.
        """
        # backup the initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc01'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'add_property_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "ERROR: error applying migration:",
                "Invalid property:"
            ]
            # execute common methods to tests
            _, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc02')
    def test_02_n_add_invalid_property_value_fail_service_start(self):
        """
        Description:
            A negative test to add a property to the model during a LITP
            plugin upgrade, using a migration script, that contains an invalid
            value and should fail validation.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to AddProperty()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check add property failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The AddProperty method must fail with error message.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # NOTE: This test, as it is currently, will allow the migration to
            # proceed and will add the property, even though the value passed
            # is invalid, based on its regex. The create_plan will fail the
            # validation. This is subject to change in a future story and when
            # it is, this test will be updated.
            item_id = '{0}_tc02'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'add_invalid_property_value'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "INFO: forwards migrations to_apply:",
                "Adding property"
            ]
            # execute common methods to tests
            _, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.ms1, expect_positive=False
            )
            self.assertTrue(self.is_text_in_list('ValidationError', stderr))
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc03')
    def test_03_n_rename_property_missing_fail_service_start(self):
        """
        Description:
            A negative test to rename a property on the model during a LITP
            plugin upgrade, using a migration script, even though the original
            property was removed from the upgrade code.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to RenameProperty()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check rename property failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The RenameProperty method must fail with error message.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            item_id = '{0}_tc03'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'rename_property_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "ERROR: error applying migration:",
                "Invalid property:"
            ]
            # execute common methods to tests
            _, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc04')
    def test_04_n_remove_property_missing(self):
        """
        Description:
            A negative test to remove a property on the model during a LITP
            plugin upgrade, using a migration script, even though the property
            never existed in the first place.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to RemoveProperty()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check remove property failed, log messages and created model
                items remain unchanged

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The RemoveProperty method must fail and the model items must remain
            unchanged.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc04'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'remove_property_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "INFO: forwards migrations to_apply:",
                "INFO: Removing property"
            ]
            # execute the test methods
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            # expect the property removal failed and name property and its
            # values still exist
            values_dict = {
                test_paths[0]: {property_key: property_value}
            }
            # negative test, no damage to litpd service, check values remain
            # unchanged
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start
            # the service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc05')
    def test_05_n_rename_itemtype_missing(self):
        """
        Description:
            A negative test to rename an item type on the model during a LITP
            plugin upgrade, using a migration script, even though the item type
            never existed in the first place.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to RenameItemType()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check migration renamed the item type failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The RenameItemType method must fail with error message.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc05'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'rename_item_type_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "ERROR: error applying migration:",
                "Invalid item type"
            ]
            # execute the test methods
            _, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc06')
    def test_06_n_add_collection_missing_fail_service_start(self):
        """
        Description:
            A negative test to add a collection on the model during a LITP
            plugin upgrade, using a migration script, even though the
            collection never existed in the first place.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to AddCollection()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check collection addition failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The AddCollection() method must fail with error message.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # NOTE: there is no error message after the failure applicable to
            # addcollection; this will be handled in a future story; currently
            # this test will not fail, even though it should. The way
            # collection migration is handled may leave the model in an
            # inconsistent state. The test will be updated when this issue is
            # resolved.
            item_id = '{0}_tc06'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'add_collection_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                    "INFO: forwards migrations to_apply:",
                    "Creating Collection"
            ]
            # execute common methods to tests
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            # expect the property removal failed and name property and its
            # values still exist
            values_dict = {
                '{0}/collection_items_missing'.format(test_paths[0]): {
                    'type': 'collection-of-software-item'
                },
                '{0}/migration_config_02/collection_items_missing'.format(
                    test_paths[2]
                ): {
                    'type': 'collection-of-software-item'
                }
            }
            # negative test, no damage to litpd service, check values remain
            # unchanged
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start
            # the service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc07')
    def test_07_n_add_refcollection_missing_fail_service_start(self):
        """
        Description:
            A negative test to add a ref-collection on the model during a LITP
            plugin upgrade, using a migration script, even though the
            collection never existed in the first place.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to AddRefCollection()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check rename item type failed and log messages

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The AddRefCollection() method must fail with error message.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # NOTE: there is no error message after the failure applicable to
            # addrefcollection; this will be handled in a future story;
            # currently this test will not fail, even though it should. The way
            # collection migration is handled may leave the model in an
            # inconsistent state. The test will be updated when this issue is
            # resolved.
            item_id = '{0}_tc07'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'add_refcollection_missing'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                    "INFO: forwards migrations to_apply:",
                    "Creating RefCollection"
            ]
            # execute common methods to tests
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            # expect the property removal failed and name property and its
            # values still exist
            values_dict = {
                '{0}/collection_items_missing'.format(test_paths[0]): {
                    'type': 'ref-collection-of-software-item'
                },
                '{0}/migration_config_02/collection_items_missing'.format(
                    test_paths[2]
                ): {
                    'type': 'ref-collection-of-software-item'
                }
            }
            # negative test, no damage to litpd service, check values remain
            # unchanged
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start
            # the service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc08')
    def test_08_n_update_collectiontype_no_collection(self):
        """
        Description:
            A negative test to update the collection item type on the model
            during a LITP plugin upgrade, using a migration script, even though
            the collection never existed, in the model, in the first place.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to UpdateCollectionType()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check rename item type failed, log messages and created model
                items remain unchanged

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The UpdateCollectionType() method must fail and the model items
            must remain unchanged.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc08'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'update_collection_type_no_collection'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = ["INFO: forwards migrations to_apply:"]
            # execute the test methods
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            self.execute_cli_show_cmd(
                self.ms1,
                '{0}/collection_items_missing_no_appear'.format(test_paths[0]),
                expect_positive=False
            )
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc09')
    def test_09_p_update_collectiontype_supertype(self):
        """
        Tests for updating item type in an item collection.

        Steps:
            A positive test to update the collection item type on the model
            during a LITP plugin upgrade, using a migration script, and check
            that the update is successful only if the collection is changed to
            a supertype or the collection has not children.
            The collection item type update will succeed if the collection is
            empty, in this case the item type may be anything.
            The collection item type update will succeed if the collection is
            non-empty, has child objects, if and only if the new item type is a
            supertype of the current one and will fail if the new collection
            item type is not a supertype of the current one.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script to UpdateCollectionType()
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check update collection item type succeeds only if the
                collection is moved to a supertype of the current type or to
                anything if it had not child items

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The UpdateCollectionType() method must succeed for model items that
            have children only if the new item is a supertype or if the
            collection had no children to begin with.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc09'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'update_collection_type_supertype'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                    "INFO: forwards migrations to_apply:",
                    "Cannot convert collection",
                    "non-supertype",
                    "Converting collection"
            ]
            # execute the test methods
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            # expect property remove migration failed and property name and its
            # values still exist
            values_dict = {
                test_paths[0]: {property_key: property_value},  # props;
                                                                # no change
                test_paths[1]: {
                    'type': 'collection-of-node-config'
                },  # supert; migrate success
                test_paths[2]: {
                    'type': 'collection-of-migration-config'
                },  # fail; no change
                test_paths[3]: {
                    'type': 'collection-of-software-item'
                }  # empty; migrate success
            }
            # positive test, no damage to litpd service, check migration
            # success
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc10')
    def test_10_n_invalid_path_migration_ignored(self):
        """
        Description:
            A negative test where an upgrade of a LITP plugin, using migration
            script, will fail, even if everything in the code/migration are
            correct if the path to the migration script does not meet the
            standard defined in the SDK.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script held under an invalid
                migration script path
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check migration failed, log messages and created model items
                remain unchanged.

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The migration script must fail and all created model item must
            remain unchanged.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc10'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'no_valid_path_ignore'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages - in this case correct
            # behaviour would be the absense of migration messages
            log_msgs = ["INFO: forwards migrations to_apply:"]
            # execute the test methods
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names, expect_logs=False
            )
            # expect item type to remain unchanged
            values_dict = {
                test_paths[0]: {
                    'type': self.item_type,
                    property_key: property_value
                }
            }
            # negative test, no damage to litpd service, check values remain
            # unchanged
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)

    @attr('all', 'non-revert', 'story1126_2509_5568',
            'story1126_2509_5568_tc11')
    def test_11_p_all_success_migration_operations(self):
        """
        Description:
            A positive migration test where an upgrade of LITP plugin, using
            migration scripts, must succeed for all operations defined in the
            migration script.

        Pre-Requisites:
            1. A running litpd service
            2. A test plugin installed and in use by the model

        Pre-Test Steps:
            1.  Create a test extension/plugin as described in the LITP2 SDK
            2.  Create a second test extension that will upgrade the first
                extension and add a migration script
            3.  Install the extension/plugin version 1

        Test Steps:
            1.  Create a number of model items for the installed
                extension/plugin
            2.  Upgrade the extension
            3.  Check migration succeeded, log messages and created model items
                are all changed as expected

        Restore Steps:
            1.  Remove the created model items
            2.  Remove/Uninstall the extension/plugin

        Expected Result:
            The migration script must succeed and all migration operations must
            be included in the model.
        """
        # backup initial litp model
        self.backup_db()
        # install the plugin
        rpm_names = self.install_plugin()
        self.assertNotEqual([], rpm_names)
        try:
            # the model item id is the current test
            item_id = '{0}_tc11'.format(self.plugin_id)
            # this is the property
            property_key = 'name'
            # the property value is the tc_identifier
            property_value = 'all_success_migration_operations'
            properties = '{0}=\'{1}\''.format(property_key, property_value)
            # expected logs from /var/log/messages
            log_msgs = [
                "INFO: forwards migrations to_apply:",
                "INFO: Adding property",
                "INFO: Renaming property",
                "INFO: Removing property",
                "INFO: Creating Collection",
                "INFO: Creating RefCollection",
                "INFO: Converting collection",
                "to item type"
            ]
            # execute the test methods
            test_paths, rpm_names = self.execute_common(
                item_id, properties, log_msgs, rpm_names
            )
            # check property removed
            self.execute_show_data_cmd(
                self.ms1, test_paths[0], 'toberemoved', expect_positive=False
            )
            # expect item type migrations to be successful
            values_dict = {
                test_paths[0]: {
                    'type': 'migrated-node-config',  # rename item type
                    'renamed': property_value,  # rename property; same value
                    'surname': 'bar',  # add property; default value
                },
                '{0}/migration_collection_added'.format(test_paths[0]): {
                    'type': 'collection-of-migration-config'
                },  # added collection
                '{0}/migration_refcollection_added'.format(test_paths[0]): {
                    'type': 'ref-collection-of-migration-config'
                },  # added ref-collection
                test_paths[1]: {
                    'type': 'collection-of-node-config'
                }  # updated collection type
            }
            # positive test, check migrations
            self.check_values_in_paths(values_dict)
        finally:
            # remove the plugin, restore the last known config and start the
            # service and turn debug on
            self.remove_plugin(rpm_names)
