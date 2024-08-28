"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@date:      January 2019
@author:    Bryan McNulty
@summary:   Verify litpd_error.log and litpd_access.log recreation
            if deleted.
"""

from litp_generic_test import GenericTest, attr
import test_constants as const


class Story319742(GenericTest):
    """
    TORF-319742
    Setup logging/filehandler for litpd_error.log at litp service startup
    so correct ownership of file is preserved if the file is removed.
    """

    def setUp(self):
        """ Runs before every single test """
        super(Story319742, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.perms_expect = '644 celery celery'
        self.perms_err_msg = "The file permissions on the file '{0}' are " \
            "'{1}' and not '{2}'."
        self.files_returned_err_msg = "The file {0} has not been moved" \
                 " back to its location '{1}' as expected."
        self.access_msg = 'cannot access {0}: No such file or directory'
        self.access_err_msg = "The file '{0}' was not removed from '{1}'" \
            " as expected."
        self.file_exists_err_msg = "The file '{0}' does not exist in " \
            "the location '{1}' as expected."

    def tearDown(self):
        """ Runs after every single test """
        super(Story319742, self).tearDown()

    @staticmethod
    def _get_filename(file_path):
        """
        Description:
            Returns the filename for the full file path specified.
        Args:
            file_path (str): The full file path for the file.
        """
        return file_path.split('/')[-1]

    def _rm_file_test(self, step_num, file_path):
        """
        Description:
            Firstly confirm that the file is located on the file path.
            Secondly verify the file permissions.
            Thirdly remove this file.
            Fourthly verify that the file has been removed.
        Args:
            step_num (int): This is the step number to use in the first
                message this function's logs to test output.
            file_path (str): This is the full file path of the file to be
                removed.
        """
        filename = self._get_filename(file_path)
        self.log("info", "{0}.  Check status of file '{1}'.".format(step_num,
                                                                 file_path))
        self.assertTrue(self.remote_path_exists(self.ms_node,
            file_path, su_root=True),
            self.file_exists_err_msg.format(filename, file_path))

        self._verify_file_permissions(step_num + 1, file_path)
        self.log("info", "{0}.  Remove & confirm removal of file "
                "'{1}'.".format(step_num + 2, file_path))
        self.assertTrue(self.remove_item(self.ms_node, file_path,
                                         su_root=True),
            self.access_err_msg.format(filename, file_path))

    def _assert_log_files_restored(self, step_num, file_path):
        """
        Description:
            This verifies that a file has be recreated on the file path
            provided.
        Args:
            step_num (int): This is the step number to use in the first
                message this function's logs to test output.
            file_path (str): This is the full file path of the file to be
                checked.
        """
        filename = self._get_filename(file_path)
        self.log("info", "{0}.  Check that the file '{1}' has been restored" \
            " in it's location '{2}'.".format(step_num, filename, file_path))

        self.assertTrue(self.remote_path_exists(self.ms_node,
            file_path, su_root=True),
            self.file_exists_err_msg.format(filename, file_path))

    def _verify_file_permissions(self, step_num, file_path):
        """
        Description:
            This function asserts that the provided file has it's file
            permissions, owner and group are set to '644 celery celery'.
        Args:
            step_num (int): This is the step number to use in the first
                message this function's logs to test output.
            file_path (str): This is the full file path of the file to be
                checked.
        """
        self.log("info", "{0}. Verify that the file permissions for '{1}' "
            "are as expected.".format(step_num, file_path))
        cmd = '{0} -c "%a %U %G" {1}'.format(const.STAT_PATH, file_path)
        perms, _, _ = self.run_command(self.ms_node, cmd, su_root=True)
        self.assertEqual(perms[0],
                self.perms_expect,
                self.perms_err_msg.format(file_path,
                    perms[0], self.perms_expect))

    @attr('all', 'revert', 'story_319742', 'story_319742_tc1')
    def test_01_p_verify_litpd_error_log_recreation(self):
        """
        @tms_id: torf_319742_tc01
        @tms_requirements_id: TORF-289907
        @tms_title: Verify litpd_error.log recreation if deleted.
        @tms_description: Verify that litpd_error.log is re-created with
            correct ownership & permissions in the event that it is removed.
        @tms_test_steps:
            @step: Check that the following file exists.
                '/var/log/litp/litpd_error.log'
            @result: File exists as expected.
            @result: File has it's file permissions, owner and group set
                to '644 celery celery'.
            @step: Delete this file.
            @result: File is deleted successfully.
            @step: Restart the litpd service.
            @result: File is recreated successfully.
            @result: File has file permissions, owner's and group set to
                '644 celery celery' as expected.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self._rm_file_test(1, const.LITPD_ERROR_LOG)

        self.log('info', '4.  Restart litpd service.')
        self.restart_litpd_service(self.ms_node)

        self._assert_log_files_restored(5, const.LITPD_ERROR_LOG)
        self._verify_file_permissions(6, const.LITPD_ERROR_LOG)

    @attr('all', 'revert', 'story_319742', 'story_319742_tc2')
    def test_02_litpd_access_log_recreation(self):
        """
        @tms_id: torf_319742_tc02
        @tms_requirements_id: TORF-289907
        @tms_title: Verify litpd_access.log recreation if deleted.
        @tms_description: Verify that litpd_access.log are re-created with
            correct ownership & permissions in the event that they are
            removed.
        @tms_test_steps:
            @step: Check that the following file exist.
                '/var/log/litp/litpd_access.log'
            @result: File exists as expected.
            @step: Delete this file.
            @result: File is deleted successfully.
            @step:  Perform a 'litp show -p /' command.
            @result: File is recreated successfully.
            @result: '/var/log/litp/litpd_access.log' has file permissions,
                owner and group set to '644 celery celery' as expected.
            @result: Check for logging in '/var/log/litp/litpd_access.log'.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self._rm_file_test(1, const.LITPD_ACCESS_LOG)

        self.log("info", "4.  Perform a 'litp show -p /' command on the MS.")
        self.execute_cli_show_cmd(self.ms_node, '/')

        self._assert_log_files_restored(5, const.LITPD_ACCESS_LOG)
        self._verify_file_permissions(6, const.LITPD_ACCESS_LOG)

        self.log("info", "7.  Check for logging in the 'litpd_access.log'" \
            " file.")
        expected_log_entry = "GET /litp/rest/v1/ HTTP/1.1"
        self.assertTrue(self.check_for_log(self.ms_node,
            expected_log_entry, const.LITPD_ACCESS_LOG, 0),
            "Expected log entry '{0}' not found in {1}.".format(
                 expected_log_entry, const.LITPD_ACCESS_LOG))
