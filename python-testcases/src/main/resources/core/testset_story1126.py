#!/usr/bin/env python

'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    Maria
@summary:   Integration test for litp migration support
            Agile: LITPCDS-1126
'''
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants
import os


class Story1126(GenericTest):

    '''
    As a Site Engineer I want model migration to handle
    addition/updates/deletion+deprecation
    of item properties, so that I can upgrade
    LITP 2.x.x to 2.x.x+1 (Part 1/2 - basic migration framework)
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
        # Call super class setup
        super(Story1126, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.ms_ip_address = self.get_node_att(self.ms_node, 'ipv4')
        self.cli = CLIUtils()
        self.redhatutils = RHCmdUtils()
        # Test Attributes
        self.tmp_conf = "/tmp"

    def create_mig_dir(self):
        """
        Method to create migrations directory if it does not exist already
        """
        if self.remote_path_exists(
                self.ms_node, test_constants.LITP_MIG_PATH):
            self.log("info", "Cannot create directory, already exists")
        else:
            self.assertTrue(self.create_dir_on_node(
                    self.ms_node, test_constants.LITP_MIG_PATH, su_root=True))

    def migration_setup(self, ext):
        """
        This function creates a directory for
        the affected plugin containing
        an init file and the migration script
        """
        ext_path = test_constants.LITP_MIG_PATH + ext + "_extension"
        self.assertTrue(self.create_dir_on_node(
            self.ms_node, ext_path, su_root=True))

        cmd = "/bin/touch {0}/__init__.py".format(ext_path)
        stdout, stderr, returnc = self.run_command(
            self.ms_node, cmd, su_root=True)
        self.assertEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, returnc)

        # COPY _extension.conf TO /TMP
        conf_file_path = test_constants.LITP_EXT_PATH + ext + "_extension.conf"
        self.assertTrue(
            self.cp_file_on_node(
                self.ms_node, conf_file_path, self.tmp_conf, su_root=True))

    def change_config_version(self, ext, new_version):
        """
        Method that changes the plugin version
        in the config file
        """
        conf_file_path = test_constants.LITP_EXT_PATH + ext + "_extension.conf"
        print conf_file_path
        conf_file = self.get_file_contents(self.ms_node, conf_file_path)
        for line in conf_file:
            if "version" in line:
                local_lineparts = line.split("=")
                ver_num = local_lineparts[len(local_lineparts) - 1]
                cmd = self.redhatutils.get_replace_str_in_file_cmd(
                    ver_num, new_version, conf_file_path, sed_args='-i')
                stdout, stderr, returnc = self.run_command(
                    self.ms_node, cmd, su_root=True)
                self.assertEqual([], stdout)
                self.assertEqual([], stderr)
                self.assertEqual(0, returnc)

    def cp_mig_script_to_node(self, mig_script, ext):
        """
        Method that copies migration script onto MS
        """
        # COPY MIGRATION SCRIPT ONTO MS
        local_filepath = os.path.dirname(__file__)
        local_migration_filepath = local_filepath + \
            "/migration_scripts/" + mig_script
        ext_path = test_constants.LITP_MIG_PATH + ext + "_extension"
        migration_filepath = ext_path + "/" + mig_script
        self.assertTrue(self.copy_file_to(self.ms_node, \
            local_migration_filepath, migration_filepath, root_copy=True))

    def migration_cleanup(self, ext):
        """
        Method to copy orignal config file back and
        delete migration scripts
        """
        path = test_constants.LITP_EXT_PATH + ext + "_extension.conf"
        tmp_conf = self.tmp_conf + "/" + ext + "_extension.conf"
        self.assertTrue(self.cp_file_on_node(
            self.ms_node, tmp_conf, path, su_root=True))

        script_path = test_constants.LITP_MIG_PATH + ext + "_extension/*.py"
        self.remove_item(self.ms_node, script_path, su_root=True)

    def log_search(self, log, test_logs_len):
        """
        Method that searches /var/log/messages for a
        particular log
        """
        cmd = RHCmdUtils().get_grep_file_cmd(
            test_constants.GEN_SYSTEM_LOG_PATH, log, \
            file_access_cmd="tail -n {0}".format(test_logs_len))
        stdout, stderr, returnc = self.run_command(
        self.ms_node, cmd, add_to_cleanup=False)
        self.assertNotEqual([], stdout)
        self.assertEqual([], stderr)
        self.assertEqual(0, returnc)

    def check_test_03_migration(self):
        """
        Method that contains all checks to ensure
        migration was triggered
        """
        # Check that migration script was triggered and
        # the model has been updated accordingly
        # GET FILE SYSTEM PATH
        # Save size property value before test
        fs_path = self.find(self.ms_node, \
            "/infrastructure", "file-system", True)

        for line in fs_path:
            # CHECK PROPERTY HAS BEEN ADDED BY MIGRATION SCRIPT
            props = self.get_props_from_url(self.ms_node, \
                line, "prop3")
            self.assertEqual("item", props)
            # CHECK PROPERTY HAS BEEN REMOVED
            self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                line, "size"))

        # GET PHYSICAL DEVICE PATH
        phy_path = self.find(self.ms_node, \
                    "/infrastructure", "physical-device", True)
        for line in phy_path:
            # CHECK PROPERTY HAS BEEN ADDED
            props = self.get_props_from_url(
                self.ms_node, line, "prop4")
            self.assertEqual("prp", props)

        # GET VOLUME GROUP PATH
        vol_grp = self.find(self.ms_node, \
                    "/infrastructure", "volume-group", True)
        for line in vol_grp:
            # CHECK PROPERTY HAS BEEN ADDED
            props = self.get_props_from_url(
                self.ms_node, line, "prop2")
            self.assertEqual("null", props)

        # GET OS PROFILES PATH
        os_pro = self.find(self.ms_node, \
                    "/software", "os-profile", True)
        for line in os_pro:
            # CHECK PROPERTY HAS BEEN ADDED BY MIGRATION SCRIPT
            props = self.get_props_from_url(self.ms_node, \
                line, "prop1")
            self.assertEqual("ghi", props)
            # CHECK PROPERTY HAS BEEN REMOVED
            self.assertTrue("None", self.get_props_from_url(
                self.ms_node, line, "path"))
            # CHECK PROPERTY HAS BEEN RENAMED
            props = self.get_props_from_url(self.ms_node, \
                line, "name")
            self.assertTrue("None", props)
            self.assertTrue("nodes", self.get_props_from_url(
                self.ms_node, line, "updatedprop"))

        # GET NETWORK PATH
        net_path = self.find(self.ms_node, \
            "/infrastructure", "network", True)
        for line in net_path:
            # CHECK PROPERTY HAS BEEN ADDED BY MIGRATION SCRIPT
            props = self.get_props_from_url(self.ms_node, \
                line, "type")
            self.assertEqual("GSM", props)
            # CHECK PROPERTY HAS BEEN RENAMED
            props = self.get_props_from_url(
                self.ms_node, line, "default_gateway")
            self.assertTrue("None", props)
            props = self.get_props_from_url(
                self.ms_node, line, "gateway_used")
            self.assertNotEqual("None", props)

    @attr('manual-test')
    def test_01_p_fwd_bk_migration(self):
        """
        Description:
        Test it is possible to update the existing model
        using migration scripts forwards and backwards

        Actions:
        1. Get the start of test log file position
        2. Migration Test Setup
        3. Change version in .config file to initial version
           to be used during test
        4. Restart litpd service
        5. Get current log position
        6. Copy migration scripts onto MS
        7. Change version in .config file to match version
           in migration scripts
        8. Restart litpd service
        9.Check log for forwards migration INFO log
        10.Check Updates were made to model by the migration scripts
        11.Change version in .config file back to initial version
           to be used during test
        12.Restart litpd service
        13.Check log for backwards migration INFO log
        14.Check updates have been reversed by the migration scripts
        15.Move original network_extension.conf back
        16.Restart litpd service

        Result:
        Any forward version changes to litp model extensions
        will be detected and migration scripts will update
        the existing model accordingly.
        Likewise any backwards version changes will revert
        model
        """
        try:
            #Test Attributes
            script1 = "story1126_test_01_script1.py"
            script2 = "story1126_test_01_script2.py"
            script3 = "story1126_test_01_script3.py"
            old_version = "1.1.10"
            new_version = "1.1.11"

            # Get the start of test log file position
            fwd_log = "INFO: forwards migrations to_apply:"
            bk_log = "INFO: backwards migrations to_apply:"
            logfile = "story1126_test_01_logs.txt"
            start_log_pos = self.get_file_len(self.ms_node, \
                test_constants.GEN_SYSTEM_LOG_PATH)

            # Migration Test Setup
            self.create_mig_dir()
            self.migration_setup("network")
            self.migration_setup("core")

            # Change version in .config file to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)
            self.get_file_contents(
                self.ms_node,
                test_constants.LITP_EXT_PATH + "core_extension.conf")
            # Restart litpd service
            self.restart_litpd_service(self.ms_node)
            self.get_file_contents(
                self.ms_node,
                test_constants.LITP_EXT_PATH + "core_extension.conf")
            # Get current log position
            curr_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)
            test_logs_len = curr_log_pos - start_log_pos

            # Copy migration scripts onto MS
            self.cp_mig_script_to_node(script1, "network")
            self.cp_mig_script_to_node(script2, "core")
            self.cp_mig_script_to_node(script3, "core")

            # Change version in .config file to match version
            # in migration scripts
            self.change_config_version("core", new_version)
            self.change_config_version("network", new_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for forwards migration INFO log
            self.log_search(fwd_log, test_logs_len)

            local_filepath = os.path.dirname(__file__)
            log_filepath = local_filepath + \
            "/migration_scripts/" + logfile

            log_file = open(log_filepath, 'r')
            for line in log_file:
                self.log_search(line, test_logs_len)
            log_file.close()

            # Confirm forwards migration
            # GET NETWORK PROFILE PATH
            net_pro = self.find(self.ms_node, \
                "/infrastructure", "network-profile", True)

            for line in net_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                #Check all expected props are here
                self.assertTrue("prop4" in props.keys(), "Property is missing")
                #Check we have expected value
                self.assertEqual("ghi", props["prop4"])
                #Check property has been renamed
                self.assertFalse("management_network" in props.keys(), \
                    "Unexpected property is present")
                self.assertTrue("mgmt_network" in props.keys(), \
                    "Property is missing")

            # GET STORAGE PROFILES PATH
            stor_pro = self.find(self.ms_node, \
                "/infrastructure", "storage-profile", True)
            for line in stor_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                # Check property has been added
                self.assertTrue("prop1" in props.keys(), "Property is missing")
                self.assertEqual("storage1", props["prop1"])
                # Check property has been removed
                self.assertFalse("storage_profile_name" in props.keys(), \
                    "Unexpected property is present")

            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            for line in os_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                # Check property has been added
                self.assertTrue("prop1" in props.keys(), "Property is missing")
                self.assertEqual("os-profile-1", props["prop1"])
                # Check property has been removed
                self.assertFalse("arch" in props.keys(), \
                    "Unexpected property is present")
                self.assertFalse("kopts_post" in props.keys(), \
                    "Unexpected property is present")

            # Change version in .config file back to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)
            self.get_file_contents(
                self.ms_node,
                test_constants.LITP_EXT_PATH + "core_extension.conf")
            # Restart litpd service
            self.restart_litpd_service(self.ms_node)
            self.get_file_contents(
                self.ms_node,
                test_constants.LITP_EXT_PATH + "core_extension.conf")
            # Check log for backwards migration INFO log
            self.log_search(bk_log, test_logs_len)

            # Confirm backwards migration
            for line in net_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                # Check property has been removed by backwards migration
                self.assertFalse("prop4" in props.keys(), \
                    "Unexpected property is present")
                self.assertFalse("mgmt_network" in props.keys(), \
                    "Unexpected property is present")
                self.assertTrue("prop1" in props.keys(), \
                    "Property is missing")
                self.assertEqual("os-profile-1", props["prop1"])

            # GET STORAGE PROFILES PATH
            stor_pro = self.find(self.ms_node, \
                "/infrastructure", "storage-profile", True)
            for line in stor_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                # Check property has been removed
                self.assertFalse("prop1" in props.keys(), \
                    "Unexpected property is present")
                # Check property has been restored
                self.assertTrue("storage_profile_name" in props.keys(), \
                    "Property is missing")

            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            for line in os_pro:
                #Load props to dict
                props = self.get_props_from_url(self.ms_node, line)
                # Check property has been removed
                self.assertFalse("prop1" in props.keys(), \
                    "Unexpected property is present")
                # Check property has been restored
                self.assertTrue("x86_64" in props.keys(), \
                    "Property is missing")
                self.assertTrue("kopts_post" in props.keys(), \
                    "Property is missing")

        finally:
            self.log('info', 'FINALLY')
            # Move original conf back
            self.migration_cleanup("network")
            self.migration_cleanup("core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # CREATE PLAN TO LOAD WITHOUT MERGE DOES NOT CHANGE THE MODEL
            #_, stderr, _ = self.execute_cli_createplan_cmd(
            #    self.ms_node, expect_positive=False)
            #self.assertTrue(
            #    self.is_text_in_list("DoNothingPlanError ", stderr))

    @attr('manual-test')
    def test_02_n_fwd_bk_migration_script_errors(self):
        """
        Description:
        Test case covers negative scenarios:
        Migration Script1:Contains python Error
        Migration Script2:Contains incorrect Class Name
        Migration Script3:Contains empty operation
        Migration Script4:Contains operation error

        Actions:
        1. Get the start of test log file position
        2. Migration Test Setup
        3. Change version in .config file to initial version
           to be used during test
        4. Restart litpd service
        5. Copy migration scripts onto MS
        6. Change version in .config file to match version
           in migration scripts
        7. Restart litpd service
        8. Get current log position
        9. Check expected log was outputed during the test
           for offending migration script 4
        10.Remove script causing error
        11.Restart litpd service
        12.Check expected log was outputed during the test
           for offending migration script 1
        13.Remove script causing error
        14.Restart litpd service
        15.Check log for forwards migration INFO log
        16.Check property has not been added by the migration scripts
        17.Change version in .config file back to initial version
           to be used during test
        18.Restart litpd service
        20.Check log for backwards migration INFO log
        21.Check property has not been added by the migration scripts
        22.Move original .conf back
        24.Restart litpd service

        Result:
        Only 1 of the migration scripts is executed(script3)
        and no operations are correclty performed
        """
        try:
            # Test Attributes
            script1 = "story1126_test_02_script1.py"
            script2 = "story1126_test_02_script2.py"
            script3 = "story1126_test_02_script3.py"
            script4 = "story1126_test_02_script4.py"

            old_version = "1.1.10"
            new_version = "1.1.15"

            # Get the start of test log file position
            fwd_log = "INFO: forwards migrations to_apply:"
            bk_log = "INFO: backwards migrations to_apply:"
            error1 = "ERROR: error instanciating migration:"
            error2 = "ERROR: error applying migration:"
            restart_err1 = \
            "'AddProperty' is not defined"
            restart_err2 = \
            "'list' object has no attribute 'mutate_forward'"
            start_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)

            # Migration Test Setup
            self.create_mig_dir()
            self.migration_setup("core")

            # Change version in .config file to initial version
            # to be used during test
            self.change_config_version("core", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Copy migration scripts onto MS
            self.cp_mig_script_to_node(script1, "core")
            self.cp_mig_script_to_node(script2, "core")
            self.cp_mig_script_to_node(script3, "core")
            self.cp_mig_script_to_node(script4, "core")

            # Change version in .config file to match version
            # in migration scripts
            self.change_config_version("core", new_version)

            # Restart litpd service
            cmd = "/sbin/service litpd restart"
            stdout, stderr, returnc = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual([], stderr)
            self.assertTrue(self.is_text_in_list(restart_err1, stdout))
            self.assertEqual(1, returnc)

            # Get current log position
            curr_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)
            test_logs_len = curr_log_pos - start_log_pos

            # Check expected log was outputed during the test
            # for offending migration script 4
            self.log_search(error1, test_logs_len)

            # Remove script causing error
            script_path = test_constants.LITP_MIG_PATH \
                + "core_extension/" + script4
            self.remove_item(self.ms_node, script_path, su_root=True)

            # Restart litpd service
            cmd = "/sbin/service litpd restart"
            stdout, stderr, returnc = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual([], stderr)
            self.assertTrue(self.is_text_in_list(restart_err2, stdout))
            self.assertEqual(1, returnc)

            # Check expected log was outputed during the test
            # for offending migration script 1
            self.log_search(error2, test_logs_len)

            # Remove script causing error
            script_path = test_constants.LITP_MIG_PATH + \
                "core_extension/" + script1
            self.remove_item(self.ms_node, script_path, su_root=True)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for forwards migration INFO log
            self.log_search(fwd_log, test_logs_len)

            # Check property has not been added by the migration scripts
            # GET IP RANGE PATH
            ip_path = self.find(self.ms_node, \
                            "/infrastructure", "ip-range", True)
            for line in ip_path:
                # Check property has not been added by the migration scripts
                self.assertTrue("None", self.get_props_from_url(
                    self.ms_node, line, "prop1"))

            # Change version in .config file back to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for backwards migration INFO log
            self.log_search(bk_log, test_logs_len)

            # Check property has not been added by the migration scripts
            # GET IP RANGE PATH
            ip_path = self.find(self.ms_node, \
                            "/infrastructure", "ip-range", True)
            for line in ip_path:
                # Check property has not been added by the migration scripts
                self.assertTrue("None", self.get_props_from_url(self.ms_node, \
                    line, "prop1"))

        finally:
            # Move original .conf file back
            self.migration_cleanup("core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

    @attr('manual-test')
    def test_03_p_migration_multiple_steps(self):
        """
        Description:
        Testing migration scripts for various versions are triggered
        when the version of the plugin extension is updated to a version
        that surpasses the versions in these scripts(i.e. several migration
        scripts will be triggered at once)

        Actions:
        1. Save property size value so that it can be reset later
        2. Get current log position
        3. Create /opt/ericsson/nms/litp/etc/migrations
        4. Create /opt/ericsson/nms/litp/etc/migrations/network_extension/
        5. Copy *_extension.conf TO /TMP
        6. Change version in .config file to initial version
           to be used during test
        7. Restart litpd service
        8. Change version in .config file to match version
           in migration scripts
        9. Copy migration scripts onto MS
        10. Restart litpd service
        11.Check log for forwards migration INFO log
        12.Check that migration script was triggered and
           the model has been updated accordingly
        13.Change version in .config file back to initial version
           to be used during test
        14.Restart litpd service
        15.Check log for backwards migration INFO log
        16.Check that backwards migration was triggered and
           the model has been reverted
        17.Move original network_extension.conf back
        18.Restart litpd service
        19.Update size property to saved values

        Result:
        Version changes to litp model extensions
        are detected and the migration scripts are
        triggered and updates made to the existing model
        Backwards version changes will revert
        model
        """
        try:
            # Test Attributes
            script1 = "story1126_test_03_script1.py"
            script2 = "story1126_test_03_script2.py"
            script3 = "story1126_test_03_script3.py"
            script4 = "story1126_test_03_script4.py"

            old_version = "1.1.10"
            new_version = "1.1.20"

            # Save size property value before test
            fs_path = self.find(self.ms_node, \
                            "/infrastructure", "file-system", True)

            size_prop = dict()
            for path in fs_path:
                size_val = self.execute_show_data_cmd(
                    self.ms_node, path, "size")
                size_prop[path] = size_val

            # Get the start of test log file position
            fwd_log = "INFO: forwards migrations to_apply:"
            bk_log = "INFO: backwards migrations to_apply:"
            start_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)

            # Migration Test Setup
            self.create_mig_dir()
            self.migration_setup("network")
            self.migration_setup("core")

            # Change version in .config file to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Get current log position
            curr_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)
            test_logs_len = curr_log_pos - start_log_pos

            # COPY MIGRATION FILE ONTO NODE
            self.cp_mig_script_to_node(script1, "core")
            self.cp_mig_script_to_node(script2, "core")
            self.cp_mig_script_to_node(script3, "core")
            self.cp_mig_script_to_node(script4, "network")

            # CHANGE VERSION IN .CONF FILE
            self.change_config_version("core", new_version)
            self.change_config_version("network", new_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for forwards migration INFO log
            self.log_search(fwd_log, test_logs_len)

            # Check that migration script was triggered and
            # the model has been updated accordingly
            # GET FILE SYSTEM PATH
            self.check_test_03_migration()

            # Change version in .config file back to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for backwards migration INFO log
            self.log_search(bk_log, test_logs_len)

            # Check that backwards migration was triggered and
            # the model has been reverted
            # GET FILE SYSTEM PATH
            fs_path = self.find(self.ms_node, \
                            "/infrastructure", "file-system", True)
            for line in fs_path:
                # CHECK PROPERTY HAS BEEN ADDED BY MIGRATION SCRIPT
                props = self.get_props_from_url(self.ms_node, \
                    line, "size")
                self.assertEqual("100", props)
                # CHECK PROPERTY HAS BEEN REMOVED
                self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                    line, "prop3"))

            # GET PHYSICAL DEVICE PATH
            phy_path = self.find(self.ms_node, \
                            "/infrastructure", "physical-device", True)
            for line in phy_path:
                # CHECK PROPERTY HAS BEEN REMOVED
                self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                    line, "prop4"))

            # GET VOLUME GROUP PATH
            vol_grp = self.find(self.ms_node, \
                            "/infrastructure", "volume-group", True)
            for line in vol_grp:
                # CHECK PROPERTY HAS BEEN REMOVED
                self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                    line, "prop2"))

            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            for line in os_pro:
                # CHECK PROPERTY HAS BEEN REMOVED BY MIGRATION SCRIPT
                self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                    line, "prop1"))
                # CHECK PROPERTY HAS BEEN ADDED
                props = self.get_props_from_url(self.ms_node, \
                    line, "path")
                self.assertEqual("/profiles", props)
                # CHECK PROPERTY HAS BEEN RENAMED
                self.assertTrue("[]", self.get_props_from_url(self.ms_node, \
                    line, "updatedprop"))
                self.assertTrue("rhel6", props)
                self.assertTrue("rhel6", self.get_props_from_url(
                    self.ms_node, line, "name"))

             # GET NETWORK PATH
            net_path = self.find(self.ms_node, \
                "/infrastructure", "network", True)
            for line in net_path:
                # CHECK PROPERTY HAS BEEN REMOVED BY MIGRATION SCRIPT
                props = self.get_props_from_url(self.ms_node, \
                    line, "type")
                self.assertTrue("None", props)
                # CHECK PROPERTY HAS BEEN RENAMED
                props = self.get_props_from_url(
                    self.ms_node, line, "gateway_used")
                self.assertTrue("None", props)
                props = self.get_props_from_url(
                    self.ms_node, line, "default_gateway")
                self.assertNotEqual("None", props)

        finally:
            # Move original .conf Back
            self.migration_cleanup("network")
            self.migration_cleanup("core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Update name property
            fs_path = self.find(self.ms_node, \
                            "/infrastructure", "file-system", True)
            for path in fs_path:
                props = "size='{0}'".format(size_prop[path])
                self.execute_cli_update_cmd(self.ms_node, path, props)

            # CREATE PLAN TO LOAD WITHOUT MERGE DOES NOT CHANGE THE MODEL
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.ms_node, expect_positive=False)
            self.assertTrue(
                self.is_text_in_list("DoNothingPlanError ", stderr))

    @attr('manual-test')
    def test_04_n_fwd_bk_migration_non_existant_duplicate_prop(self):
        """
        Description:
        Test that if a migration script attemtps to add a duplicate property,
        the existing property is updated with the new value, if the migration
        script attempts to remove a property that doesnot exist, nothing
        happens on forwards migration, but the property is added on backwards
        migration

        Actions:
        1. Get the start of test log file position
        2. Migration Test Setup
        3. Change version in .config file to initial version
           to be used during test
        4. Restart litpd service
        5. Get current log position
        6. Copy migration scripts onto MS
        7. Change version in .config file to match version
           in migration scripts
        8. Restart litpd service
        9. Get current log position
        10.Check log for forwards migration INFO log
        11.Check Updates were made to model by the migration scripts
        12.Change version in .config file back to initial version
           to be used during test
        13.Restart litpd service
        14.Check log for backwards migration INFO log
        15.Check updates have been reversed by the migration scripts
        16.Move original network_extension.conf back
        17.Restart litpd service

        Result:
        Any forward version changes to litp model extensions
        will be detected and migration scripts will update
        the existing model accordingly.
        Likewise any backwards version changes will revert
        model
        """
        try:
            #Test Attributes
            script1 = "story1126_test_04_script1.py"
            script2 = "story1126_test_04_script2.py"
            script4 = "story1126_test_04_script4.py"
            old_version = "1.1.10"
            new_version = "1.1.11"
            cleanup_version = "1.1.12"

            # Get the start of test log file position
            fwd_log = "INFO: forwards migrations to_apply:"
            bk_log = "INFO: backwards migrations to_apply:"
            start_log_pos = self.get_file_len(self.ms_node, \
                test_constants.GEN_SYSTEM_LOG_PATH)

            # Migration Test Setup
            self.migration_setup("core")

            # Change version in .config file to initial version
            # to be used during test
            self.change_config_version("core", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Get current log position
            curr_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)
            test_logs_len = curr_log_pos - start_log_pos

            # Copy migration script onto MS
            self.cp_mig_script_to_node(script1, "core")
            self.cp_mig_script_to_node(script2, "core")

            # Change version in .config file to match version
            # in migration scripts
            self.change_config_version("core", new_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log do not contain INFO log
            self.log_search(fwd_log, test_logs_len)

            # Confirm forwards migration did not take place
            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            for line in os_pro:
                # CHECK DUPLICATE PROPERTY HAS NOT BEEN ADDED
                # BY MIGRATION SCRIPT
                props = self.get_props_from_url(self.ms_node, \
                    line, "name")
                self.assertTrue("os-profile-1", props)
                # CHECK PROPERTIES HAVE BEEN ADDED
                self.assertTrue("None", self.get_props_from_url(
                    self.ms_node, line, "prop_1"))
                self.assertTrue("None", self.get_props_from_url(
                    self.ms_node, line, "prop_2"))

            # Change version in .config file back to initial version
            # to be used during test
            self.change_config_version("core", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for backwards migration INFO log
            self.log_search(bk_log, test_logs_len)

            # Confirm backwards migration
            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            for line in os_pro:
                # CHECK PROPERTY HAS NOT REMOVED BY MIGRATION SCRIPT
                self.assertTrue("sample-profile", self.get_props_from_url(
                    self.ms_node, line, "name"))
                # CHECK PROPERTIES HAS BEEN ADDED
                self.assertTrue("value_1", self.get_props_from_url(
                    self.ms_node, line, "prop_1"))
                self.assertTrue(
                    "value_2", self.get_props_from_url(
                    self.ms_node, line, "prop_2"))

            # Copy migration script onto MS
            self.cp_mig_script_to_node(script4, "core")

            # Change version in .config file to match version
            # in migration scripts
            self.change_config_version("core", cleanup_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Confirm Cleanup
            props = self.get_props_from_url(self.ms_node, \
                    line, "name")
            self.assertTrue("sample-profile", props)
            # CHECK PROPERTIES HAS BEEN REMOVED
            self.assertTrue("None", self.get_props_from_url(
                self.ms_node, line, "prop_1"))
            self.assertTrue("None", self.get_props_from_url(
                self.ms_node, line, "prop_2"))

        finally:
            # Move original conf back
            self.migration_cleanup("core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

    @attr('manual-test')
    def test_05_n_fwd_bk_migration_missing_operation_arguments(self):
        """
        Description:
        Test if a migration script operations are missing arguments,
        the operations update model but properties contain no values

        Actions:
        1. Save name property value
        2. Get the start of test log file position
        3. Migration Test Setup
        4. Change version in .config file to initial version
           to be used during test
        5. Restart litpd service
        6. Get current log position
        7. Copy migration scripts onto MS
        8. Change version in .config file to match version
           in migration scripts
        9. Restart litpd service
        10.Get current log position
        11.Check log for forwards migration INFO log
        12.Check Updates were made to model by the migration scripts
        13.Change version in .config file back to initial version
           to be used during test
        14.Restart litpd service
        15.Check log for backwards migration INFO log
        16.Check updates have been reversed by the migration scripts
        17.Move original network_extension.conf back
        18.Restart litpd service
        19.Revert name property to original saved value

        Result:
        Any forward version changes to litp model extensions
        will be detected and migration scripts will update
        the existing model accordingly.
        Likewise any backwards version changes will revert
        model
        """
        try:
            #Test Attributes
            script1 = "story1126_test_05_script1.py"
            script2 = "story1126_test_05_script2.py"
            error1 = "ERROR: error instanciating migration:"
            restart_err1 = "Starting litp daemon: Error starting service:"
            old_version = "1.1.10"
            new_version = "1.1.11"

            # GET OS PROFILES PATH
            os_pro = self.find(self.ms_node, \
                            "/software", "os-profile", True)
            os_pro_url = os_pro[0]
            # Save name property value
            for line in os_pro:
                name_prop = self.get_props_from_url(
                    self.ms_node, line, "name")

            # Get the start of test log file position
            fwd_log = "INFO: forwards migrations to_apply:"
            bk_log = "INFO: backwards migrations to_apply:"
            start_log_pos = self.get_file_len(self.ms_node, \
                test_constants.GEN_SYSTEM_LOG_PATH)

            # Migration Test Setup
            self.migration_setup("core")

            # Change version in .config file to initial version
            # to be used during test
            self.change_config_version("core", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Get current log position
            curr_log_pos = self.get_file_len(
                self.ms_node, test_constants.GEN_SYSTEM_LOG_PATH)
            test_logs_len = curr_log_pos - start_log_pos

            # Copy migration script onto MS
            self.cp_mig_script_to_node(script1, "core")

            # Change version in .config file to match version
            # in migration scripts
            self.change_config_version("core", new_version)

            # Restart litpd service
            cmd = "/sbin/service litpd restart"
            stdout, stderr, returnc = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual([], stderr)
            self.assertTrue(self.is_text_in_list(restart_err1, stdout))
            self.assertEqual(1, returnc)

            # Check expected log was outputed during the test
            # for offending migration script 1
            self.log_search(error1, test_logs_len)

            # Remove script causing error
            script_path = test_constants.LITP_MIG_PATH + \
                "core_extension/" + script1
            self.remove_item(self.ms_node, script_path, su_root=True)

            # Copy migration script onto MS
            self.cp_mig_script_to_node(script2, "core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log do not contain INFO log
            self.log_search(fwd_log, test_logs_len)

            # Change version in .config file back to initial version
            # to be used during test
            self.change_config_version("core", old_version)
            self.change_config_version("network", old_version)

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Check log for backwards migration INFO log
            self.log_search(bk_log, test_logs_len)

            # Confirm backwards migration
            for line in os_pro:
                # CHECK PROPERTY HAS NOT REMOVED BY MIGRATION SCRIPT
                # but has a value of None
                self.assertTrue("None", self.get_props_from_url(
                    self.ms_node, line, "name"))

        finally:
            # Move original conf back
            self.migration_cleanup("core")

            # Restart litpd service
            self.restart_litpd_service(self.ms_node)

            # Update name property
            props = "name='{0}'".format(name_prop)
            self.execute_cli_update_cmd(self.ms_node, os_pro_url, props)

            # CREATE PLAN TO LOAD WITHOUT MERGE DOES NOT CHANGE THE MODEL
            _, stderr, _ = self.execute_cli_createplan_cmd(
                self.ms_node, expect_positive=False)
            self.assertTrue(
                self.is_text_in_list("DoNothingPlanError ", stderr))
