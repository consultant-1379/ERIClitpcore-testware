"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Jan 2018
@author:    Bryan McNulty
@summary:   TORF-231269:
            As a LITP user I want puppet manifest directories and files which
            contain passwords to not be world readable.
"""
from litp_generic_test import GenericTest, attr
import test_constants


class Story231269(GenericTest):
    """
    TORF-231269:
        A test on the permissions on puppet manifest files and
        directories delivered by rpms under the puppet module directory,
        created by ERIClitpcore and EXTRlitppuppetpostgresql on the
        Management Server.
        All directories should have permissions set to 750, user = root and
        group = puppet. The permissions for the files are set as 640, user =
        celery and group = puppet.
    """
    def setUp(self):
        """runs before every test to perform required setup"""
        super(Story231269, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mod_dir = test_constants.PUPPET_MODULES_DIR
        self.find_file_perms_str = '{0} {1} -perm 0640 -user {2}'\
            ' -group puppet -type f'
        self.directories = ['yum',
                        'sshd',
                        'postgresql_litp',
                        'litp']
        self.root_user = 'root'
        self.celery_user = 'celery'

    def tearDown(self):
        """runs after every test to perform required cleanup/teardown"""
        super(Story231269, self).tearDown()

    def check_dir_perms(self, file_path):
        """
        Checks permission, owner & group on a directory.
        It is expected that their permission is 750, owner is root, and group
        is puppet.

        Args:
            file_path (str): The complete file path of the directory to be
            checked on the MS.
        """
        cmd = '{0} --format %a:%U:%G {1}'.format(test_constants.STAT_PATH,
                                                                file_path)
        std_out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
            default_asserts=True)
        self.assertEqual(['750:root:puppet'], std_out)

    @attr('all', 'revert', 'Story231269', 'Story231269_tc04')
    def test_04_p_verify_subdir_permission_under_modules_directory(self):
        """
        @tms_id: TORF-231269_tc04
        @tms_requirements_id: TORF-231269
        @tms_title: Verify subdirectory permissions, owner & group for
            puppet modules directory for yum, sshd, postgresql_litp & litp.
        @tms_description: Verify permissions, owner & group on an
            environment for sub directories yum, sshd, postgresql_litp & litp
            under /opt/ericsson/nms/litp/etc/puppet/modules/ directory.
        @tms_test_steps:
            @step: Navigate to the following directory on the MS
                /opt/ericsson/nms/litp/etc/puppet/modules/
            @result: Navigation successful.
            @step: Check the permissions, ownership & group of the directories
                within.
            @result: The directories yum, sshd, postgresql_litp & litp have
                permissions of 750, owner id of root, group id of puppet.
            @step: Check the permissions, ownership & group of all
                subdirectories within yum, sshd, postgresql_litp & litp
                directories.
            @result: All the subdirectories have permissions of 750, owner id's
                of root, group id of puppet.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        subdir_w_perms_list = []
        subdir_list = []
        for direct in self.directories:
            self.log('info', '1. Check permissions, owner, and group'\
                ' for top level directory {0}.'.format(direct))
            self.check_dir_perms('{0}{1}'.format(self.mod_dir, direct))
            self.log('info', '2. Add all subdirectories inside of {0} to'\
                ' subdirectory list.'.format(direct))
            find_cmd = '{0} {1}{2} -type d'.format(test_constants.FIND_PATH,
                                                        self.mod_dir, direct)
            std_out, _, _ = self.run_command(self.ms_node, find_cmd,
                su_root=True, default_asserts=True)
            subdir_list.extend(std_out)

            self.log('info', '3. Add all subdirectories inside of {0} to'\
                ' list of subdirectories which have the right permissions,'
                ' owner and group.'.format(direct))
            find_w_perms_cmd = '{0} {1}{2} -perm 0750 -user root -group'\
                ' puppet -type d'.format(test_constants.FIND_PATH,
                                                        self.mod_dir, direct)
            std_out, _, _ = self.run_command(self.ms_node, find_w_perms_cmd,
                su_root=True, default_asserts=True)
            subdir_w_perms_list.extend(std_out)
        self.log('info', '4. Assert that the two lists are equal.')
        self.assertEqual(subdir_w_perms_list, subdir_list)

    @attr('all', 'revert', 'Story231269', 'Story231269_tc05')
    def test_05_p_verify_file_permissions_under_modules_dir(self):
        """
        @tms_id: TORF-231269_tc05
        @tms_requirements_id: TORF-231269
        @tms_title: Verify file permissions, owner & group for files within
            subdirectories of puppet modules.
        @tms_description: Verify file permissions, owner & group for files
            within the subdirectories of puppet modules: yum, sshd,
            postgresql_litp & litp.
        @tms_test_steps:
            @step: Navigate to the following directory on the MS
                /opt/ericsson/nms/litp/etc/puppet/modules/
            @result: Navigation successful.
            @step: Navigate through the following directories yum, sshd,
                postgresql_litp & litp.
            @result: All the have permissions of "640 -rw-r-----", owner id
                of root, group id of puppet.
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self.log('info', '1. Create subdirectory list for all sub directories'\
            ' contained in the top level directories.')
        files_list = []
        for direct in self.directories:
            find_cmd = '{0} {1}{2} -type f'.format(test_constants.FIND_PATH,
                                                    self.mod_dir, direct)
            std_out, _, _ = self.run_command(self.ms_node, find_cmd,
                su_root=True, default_asserts=True)
            files_list.extend(std_out)

        self.log('info', '2. Remove the pem files from this list.')
        pem_list = ['server_private.pem', 'server_public.pem']
        files_list = [x for x in files_list if x.split('/')[-1] not in
            pem_list]
        self.log('info', '3. Go through the directories and fill a list'\
            ' of file paths with only the files where the permissions for'\
            ' the files are set as 640, user root, group puppet.')
        files_w_perms_list = []
        for direct in self.directories:
            find_perms_cmd = self.find_file_perms_str.format(
                                    test_constants.FIND_PATH, '{0}{1}'.format(
                                                    self.mod_dir, direct),
                                                    self.root_user)
            files_w_perms, _, _ = self.run_command(self.ms_node,
                find_perms_cmd, su_root=True, default_asserts=True)
            files_w_perms_list.extend(files_w_perms)

        self.log('info', '4. Assert that the two lists are equal.')
        self.assertEqual(files_w_perms_list, files_list)

    @attr('all', 'revert', 'Story231269', 'Story231269_tc06')
    def test_06_p_verify_permissions_under_plugins_directory(self):
        """
        @tms_id: TORF-231269_tc06
        @tms_requirements_id: TORF-231269
        @tms_title: Verify file permissions, owner & group for manifest files
            generated by litp located in /plugins/ directory.
        @tms_description: Verify the permissions, owner & group for manifest
            files in puppet manifest files generated by Litp and located in
            /opt/ericsson/nms/litp/etc/puppet/manifests/plugins/
        @tms_test_steps:
            @step: Navigate to the following directory on the MS
                /opt/ericsson/nms/litp/etc/puppet/manifests/plugins/
            @result: Navigation successful.
            @step: Check the file permissions of the files within.
            @result: All the files have permissions of 640, owner = celery and
                group = puppet
        @tms_test_precondition: None
        @tms_execution_type: Automated
        """
        self.log('info', '1. Create a list and fill it with all files in'\
            ' the manifests/plugins/ directory.')
        find_cmd = '{0} {1} -type f '.format(
            test_constants.FIND_PATH, test_constants.PUPPET_MANIFESTS_DIR)
        std_out, _, _ = self.run_command(self.ms_node, find_cmd, su_root=True,
            default_asserts=True)
        self.log('info', '2. Create a list of files in the manifest/plugins/'
            ' files which have the correct permissions, owner, and group.')
        find_perms_cmd = self.find_file_perms_str.format(
            test_constants.FIND_PATH, test_constants.PUPPET_MANIFESTS_DIR,
            self.celery_user)
        files_w_perms, _, _ = self.run_command(self.ms_node, find_perms_cmd,
            su_root=True, default_asserts=True)
        self.log('info', '3. Assert that the two lists are equal.')
        self.assertEqual(std_out, files_w_perms)
