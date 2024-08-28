"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@date:      March 2019
@author:    George-Claudiu Carcadia
@summary:   Test to verify that the LITP backup script is capable of handling
            the case where an existing backup is corrupt
"""

from litp_generic_test import GenericTest, attr
from test_constants import BASH_PATH, GZIP_PATH, DD_PATH, ECHO_PATH


class Story315425(GenericTest):
    """
        Description:
            Test to verify that the LITP backup script is capable
            of handling the case where an existing backup is corrupt.
    """

    def setUp(self):
        """Run before every test"""
        super(Story315425, self).setUp()
        self.backup_dir = '/tmp/litp_archives'
        self.backup_command = \
            '{0} -x /opt/ericsson/nms/litp/bin/litp_state_backup.sh {1}'\
            .format(BASH_PATH, self.backup_dir)
        self.ms_node = self.get_management_node_filename()

        self.log('info', 'Creating the backup directory')
        self.create_dir_on_node(node=self.ms_node,
                                su_root=True,
                                remote_filepath=self.backup_dir,
                                add_to_cleanup=True)

    def tearDown(self):
        """Run after every test"""
        super(Story315425, self).tearDown()

    @attr('all', 'revert', 'Story315425', 'TORF_315425_tc03')
    def test_03_p_corrupted_backup(self):
        """
            @tms_id: TORF_315425_tc03
            @tms_requirements_id: TORF-107258
            @tms_title: Test creation of a new LITP backup file if
                        the existing one is corrupted
            @tms_description: Test to verify that the LITP backup script is
                              capable of handling the case where an existing
                              backup is corrupt
                              This verifies TORF-315425
            @tms_test_steps:
             @step:   Execute the LITP backup script
             @result: Ensure a backup file has been generated
             @step:   Corrupt the generated backup file
             @result: Ensure the backup file is corrupted
             @step:   Execute the LITP backup script again
             @result: The script should detect that the backup file is
                      corrupted and should generate a new backup file
            @tms_test_precondition: NA
            @tms_execution_type: Automated
        """

        self.log('info', '1. Creating the backup archive')
        corrupted_archive_file_name = self.run_command(
                                      node=self.ms_node,
                                      cmd=self.backup_command,
                                      su_root=True)[0][-1].split()[-1]

        self.log('info', 'Created backup file {0}'
                 .format(corrupted_archive_file_name))

        self.log('info', 'Checking initial backup file')
        check_initial_archive_command = \
            '{0} -t {1} && {2} ok || {2} bad'\
            .format(GZIP_PATH, corrupted_archive_file_name, ECHO_PATH)
        std_out = self.run_command(node=self.ms_node,
                                   cmd=check_initial_archive_command,
                                   su_root=True)[0]
        self.assertTrue('ok' in std_out, 'The file {0} is corrupted!'
                        .format(corrupted_archive_file_name))

        self.log('info', '2. Corrupting the existing backup file')
        corrupt_archive_command = \
            '{0} seek=4000 bs=1 count=1 of={1} <<<"111100000000000000"'\
            .format(DD_PATH, corrupted_archive_file_name)
        self.run_command(node=self.ms_node,
                         cmd=corrupt_archive_command,
                         su_root=True)

        self.log('info', 'Checking if the backup file is indeed corrupted')
        check_initial_archive_command = \
            '{0} -t {1} 2> /dev/null && {2} ok || {2} bad'\
            .format(GZIP_PATH, corrupted_archive_file_name, ECHO_PATH)
        std_out = self.run_command(node=self.ms_node,
                                   cmd=check_initial_archive_command,
                                   su_root=True)[0]
        self.assertTrue('bad' in std_out,
                        'The file {0} should have been corrupted!'
                        .format(corrupted_archive_file_name))

        self.log('info', '3. Checking if a new backup file is created '
                         'if the existing backup file is corrupted')
        good_archive_file_name = self.run_command(
                                 node=self.ms_node,
                                 cmd=self.backup_command,
                                 su_root=True)[0][-1].split()[-1]

        self.log('info', 'Checking if the name of the newly generated '
                         'file is different from the existing one')

        self.assertNotEquals(
            corrupted_archive_file_name, good_archive_file_name,
            'The newly generated file name should not have '
            'the same name as the previous backup file {0}!'
            .format(good_archive_file_name))

        self.log('info', 'Testing the newly generated backup file {0}'
                 .format(good_archive_file_name))
        check_good_archive_command = \
            '{0} -t {1} && {2} ok || {2} bad'\
            .format(GZIP_PATH, good_archive_file_name, ECHO_PATH)
        std_out = self.run_command(node=self.ms_node,
                                   cmd=check_good_archive_command,
                                   su_root=True)[0]

        self.assertTrue('ok' in std_out, 'The file {0} is corrupted!'
                        .format(good_archive_file_name))
