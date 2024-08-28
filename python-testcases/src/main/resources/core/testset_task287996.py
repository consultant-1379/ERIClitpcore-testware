"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@date:      March 2019
@author:    Eduard Vasile
@summary:   TORF-287996
            As a LITP user, I want to verify audit.rules and
            audit.log for successful mount/umount.
"""

from litp_generic_test import GenericTest, attr
import test_constants as const


class Story287996(GenericTest):
    """
    TORF-287996
        As a LITP user, I want to verify audit.rules and
        audit.log for successful mount/umount.
    """

    def setUp(self):
        """
        Description:
            Runs before every single test
        """
        super(Story287996, self).setUp()

        self.test_node = self.get_management_node_filename()
        self.testiso = "test_mount.iso"
        self.testdir = "test_mount"
        self.mkisofs_path = "/usr/bin/mkisofs"

        self.run_commands(self.test_node,
                          ["{0} {1}".format(const.MKDIR_PATH,
                                            self.testdir),
                           "{0} -input-charset default -o {1} {2}"
                           .format(self.mkisofs_path,
                                   self.testiso,
                                   self.testdir)])

    def tearDown(self):
        """
        Description:
            Runs after every single test
        """
        super(Story287996, self).tearDown()

    def cleanup_test(self):
        """
        Description:
            Manual cleanup after test.
        """
        self.log('info', 'Run manual cleanup.')

        self.run_command(self.test_node,
                         "{0} {1}".format(const.UMOUNT_PATH,
                                          self.testdir),
                         su_root=True)

        self.run_commands(self.test_node,
                          ["{0} {1}".format(
                              const.RM_RF_PATH,
                              self.testdir),
                           "{0} {1}".format(
                               const.RM_RF_PATH,
                               self.testiso)])

    @attr('all', 'revert', 'Story287996', 'TORF_287996_tc06')
    def test_06_p_mount_partition(self):
        """
        @tms_id: TORF_287996_tc06
        @tms_requirements_id: TORF-287996
        @tms_title: Test audit rules for mount option.
        @tms_description:
            Verify that the audit.rules and audit.log have a new
            audit rule/log entry for the unmount option.
            This verifies TORF-287996.
        @tms_test_steps:
            @step: Verify audit.rules if the following rule exists:
                "-a always,exit -F arch=b64 -S mount -S
                umount2 -k mount_umount"
            @result: Line exists in the file.
            @step: Mount test .iso.
            @result: Filesystem is mounted.
            @step: Verify audit.log for a mount log entry.
            @result: Log entry exists and contains the following strings:
                success=yes, key="mount_umount", comm="mount".
            @step: Manual cleanup.
            @result: Revert environment to initial state.
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        try:
            self.log('info', '1 Check the {0} for the new rule.'
                     .format(const.AUDIT_RULES_FILE))
            expected_rules = "-a always,exit -F arch=b64 -S mount " \
                             "-S umount2 -k mount_umount"
            found_rules = self.check_for_log(self.test_node,
                                             "mount_umount",
                                             const.AUDIT_RULES_FILE,
                                             log_len=0,
                                             return_log_msg=True)

            self.assertEqual(found_rules[0], expected_rules,
                             'Rule "{0}" missing from {1}'
                             .format(expected_rules, const.AUDIT_RULES_FILE))

            self.log('info', '2 Get log file EOF index before '
                             'mounting .iso.')
            log_len = self.get_file_len(self.test_node,
                                        const.AUDIT_RULES_LOG)

            self.log('info', '3 Mount {0}.'.format(self.testiso))
            self.run_command(self.test_node,
                             "{0} -o loop {1} {2}".format(const.MOUNT_PATH,
                                                          self.testiso,
                                                          self.testdir),
                             su_root=True)

            # Check if filesystem is mounted
            is_mounted = self.is_filesystem_mounted(self.test_node,
                                                    self.testdir)
            self.assertTrue(is_mounted, 'Failed to mount {0}.'
                            .format(self.testiso))

            self.log('info', '4 Check the {0} for a successful mount '
                             'log entry.'.format(const.AUDIT_RULES_LOG))
            expected_in_log = ['success=yes', 'key=\"mount_umount\"',
                               'comm=\"mount\"']
            log = self.wait_for_log_msg(self.test_node, "mount",
                              log_file=const.AUDIT_RULES_LOG, log_len=log_len,
                              rotated_log='/var/log/audit/audit.log',
                              return_log_msgs=True)

            for item in expected_in_log:
                self.assertTrue(self.is_text_in_list(item, log),
                               '{0} missing from {1}'
                               .format(item, const.AUDIT_RULES_LOG))
        finally:
            self.cleanup_test()

    @attr('all', 'revert', 'Story287996', 'TORF_287996_tc07')
    def test_07_p_umount_partition(self):
        """
        @tms_id: TORF_287996_tc07
        @tms_requirements_id: TORF-287996
        @tms_title: Test audit rules for unmount option.
        @tms_description:
            Verify that the audit.rules and audit.log have a new
            audit rule/log entry for the unmount option.
            This verifies TORF-287996.
        @tms_test_steps:
            @step: Verify audit.rules if the following rule exists:
                "-a always,exit -F arch=b64 -S mount -S
                umount2 -k mount_umount"
            @result: Line exists in the file.
            @step: Mount test .iso.
            @result: Filesystem is mounted.
            @step: Unmount test .iso.
            @result: Filesystem is unmounted.
            @step: Verify audit.log for a mount log entry.
            @result: Log entry exists and contains the following strings:
                success=yes, key="mount_umount", comm="umount".
            @step: Manual cleanup.
            @result: Revert environment to initial state.
        @tms_test_precondition: N/A
        @tms_execution_type: Automated
        """
        try:
            self.log('info', '1 Check the {0} for the new rule.'
                     .format(const.AUDIT_RULES_FILE))
            expected_rules = "-a always,exit -F arch=b64 -S mount " \
                             "-S umount2 -k mount_umount"
            found_rules = self.check_for_log(self.test_node,
                                             "mount_umount",
                                             const.AUDIT_RULES_FILE,
                                             log_len=0,
                                             return_log_msg=True)

            self.assertEqual(found_rules[0], expected_rules,
                             'Rule "{0}" missing from {1}'
                             .format(expected_rules, const.AUDIT_RULES_FILE))

            self.log('info', '2 Mount {0}.'.format(self.testiso))
            self.run_command(self.test_node,
                             "{0} -o loop {1} {2}".format(const.MOUNT_PATH,
                                                          self.testiso,
                                                          self.testdir),
                            su_root=True)
            # Check if filesystem is mounted
            is_mounted = self.is_filesystem_mounted(self.test_node,
                                                    self.testdir)
            self.assertTrue(is_mounted, 'Failed to mount {0}.'
                            .format(self.testiso))

            self.log('info', '3 Get log file EOF index before '
                             'unmounting .iso.')
            log_len = self.get_file_len(self.test_node, const.AUDIT_RULES_LOG)

            self.log('info', '4 Unmount {0}.'.format(self.testiso))
            self.run_command(self.test_node,
                             "{0} {1}".format(const.UMOUNT_PATH, self.testdir),
                             su_root=True)
            # Check if filesystem is umounted
            is_mounted = self.is_filesystem_mounted(self.test_node,
                                                    self.testdir)
            self.assertFalse(is_mounted, 'Failed to unmount {0}.'
                             .format(self.testiso))

            self.log('info', '5 Check the {0} for a successful '
                             'unmount log entry.'
                     .format(const.AUDIT_RULES_LOG))
            expected_in_log = ['success=yes', 'key=\"mount_umount\"',
                               'comm=\"umount\"']
            log = self.check_for_log(self.test_node,
                                     "mount_umount",
                                     const.AUDIT_RULES_LOG,
                                     log_len=log_len,
                                     return_log_msg=True)

            for item in expected_in_log:
                self.assertTrue(item in log[0], '{0} missing from {1}'
                                .format(expected_in_log[0],
                                        const.AUDIT_RULES_LOG))

        finally:
            self.cleanup_test()
