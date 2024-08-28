'''
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     March 2014
@author:    Jacek Spera
@summary:   Integration test for story 2084: As an admin I want to import
            software into yum repositories, so that they are available for
            upgrade
            Agile: STORY-2084
'''
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import os
from redhat_cmd_utils import RHCmdUtils
from test_constants import LITP_PKG_REPO_DIR
from time import sleep


class Story2084(GenericTest):
    """
    Description:
        I want to import software into yum repositories,
        so that they are available for upgrade
    Prerequisites:
        1+ nodes deployment is in place
    """
    def setUp(self):
        """ Setup variables for every test """
        super(Story2084, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

        self.rpm_file_name = "pico-5.07-5.2.x86_64.rpm"

        self.rpm_local_path = os.path.join(os.path.dirname(__file__),
                                           self.rpm_file_name)
        self.rpm_pkg_name = self.rpm_file_name.split('-')[0]
        self.rpm_remote_dir = '/tmp/story2084/'
        self.rpm_remote_path = os.path.join(self.rpm_remote_dir,
                                            self.rpm_file_name)
        self.new_repo_dir = '/var/www/story2084repo'

        self.create_dir_on_node(self.ms_node, self.rpm_remote_dir)

    def tearDown(self):
        """ Called after every test"""
        super(Story2084, self).tearDown()

    @staticmethod
    def _get_invalid_path_error_msg(path):
        """ Create expected stderr for an invalid path """
        return "Path {0} is not valid".format(path)

    def _put_rpm_on_ms(self, as_root=False):
        """ Copy RPMs to the MS """
        return self.copy_file_to(
            self.ms_node,
            self.rpm_local_path,
            self.rpm_remote_path, root_copy=as_root)

    def _rpm_available_on_nodes(self, pkg_name, repo_name):
        """ Check if rpm is available on managed nodes from a specific repo
        Assumes repo names are upcase versions of repo dirs on ms"""
        cmd = self.rhcmd.get_yum_cmd(
            'search {0} --disablerepo="*" --enablerepo="{1}"'.format(
                pkg_name, repo_name.upper()))
        node = self.get_managed_node_filenames()[0]
        stdout, stderr, returnc = self.run_command(node, cmd)
        self.assertTrue(stdout)
        self.assertFalse(stderr)
        self.assertEqual(0, returnc)

        return not self.is_text_in_list('No matches found', stderr)

    @attr('all', 'revert', 'story2084', 'story2084_tc01')
    def test_01_p_litp_help_gives_correct_usage_for_import_command(self):
        """
        Description:
            Verifies that
            $ litp -h
            gives info about correct usage for import command
        Actions:
            1. Execute command on ms
            2. Compare output of litp import to fixture
        Results:
            Output equal fixture (TBA)
        """
        cmd = self.cli.get_help_cmd(help_arg='--help')
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd)
        expected = \
            "import              Imports packages into Yum repositories."

        self.assertEquals(0, returnc)
        self.assertEquals([], stderr)
        self.assertTrue(self.is_text_in_list(expected, stdout))

    @attr('all', 'revert', 'story2084', 'story2084_tc02')
    def test_02_p_litp_import_specific_help_gives_correct_usage(self):
        """
        Description:
            Tests correctness of
            $ litp import -h
            output
        Actions:
            1. Execute command on ms
            2. Compare output of litp import to fixture
        Results:
            Output equal fixture (TBA)
        """
        cmd = self.cli.get_help_cmd(help_arg='--help', help_action='import')
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd,
                                                   add_to_cleanup=False)
        self.assertEquals(0, returnc)
        self.assertEquals([], stderr)
        self.assertTrue(
            self.is_text_in_list(
                'Usage: litp import [-h] [-j] source_path destination_path',
                stdout
            )
        )

    @attr('all', 'revert', 'story2084', 'story2084_tc03')
    def test_03_p_rpms_avail_on_nodes_on_rpm_dir_import_to_repo(self):
        """
        Description:
            Verify that a user can import a set of rpms (a folder containing
            rpms) into an pre existing yum repo which then become available
            from all configured nodes
            (Also covers:
            Verify that a user can import a directory of litp rpms using the
            litp flag, check available from all nodes)
        Actions:
            1. Copy 1 rpm file into a directory on MS
            2. Execute litp import command on that directory path
            3. Check if yum install/upgrade <rpm> is possible on all configured
            nodes

        Results:
            All configured nodes can install/upgrade the rpm after import
        """
        try:
            self._put_rpm_on_ms()

            cmd = self.cli.get_import_cmd(self.rpm_remote_dir, "litp")
            self.assertEquals(([], [], 0), self.run_command(
                self.ms_node, cmd))

            sleep(5)  # give it time to perform tasks on nodes
            self.assertTrue(self._rpm_available_on_nodes(self.rpm_pkg_name,
                                                         'litp'))

        finally:
            self.remove_item(self.ms_node,
                             os.path.join(LITP_PKG_REPO_DIR,
                                          self.rpm_file_name),
                             su_root=True)
            self.run_command(self.ms_node,
                             self.rhcmd.get_createrepo_cmd(LITP_PKG_REPO_DIR),
                             su_root=True)

    @attr('all', 'revert', 'story2084', 'story2084_tc04')
    def test_04_p_new_repo_created_and_rpms_avail_on_nodes(self):
        """
        Description:
            Verify that when user imports a set of rpms (a folder containing
            rpms) into a dir path that is not an rpm repo a new repo is created
            Verify the rpms in the new repo are available on all configured
            nodes
        Actions:
            1  Copy 1 rpm file into a directory on MS
            2. Create a new repo-to-be directory in path served by apache
            3. Execute litp import command on that directory path
            4. Verify a new repository has been created
        Results:
            New repo created
            All configured nodes can install/upgrade rpms contained in the new
            repo
        """
        try:
            self._put_rpm_on_ms()

            self.create_dir_on_node(self.ms_node, self.new_repo_dir,
                                    su_root=True)
            cmd = self.cli.get_import_cmd(self.rpm_remote_dir,
                                          self.new_repo_dir)
            self.assertEquals(([], [], 0), self.run_command(self.ms_node, cmd))

            # look for repodata dir in self.new_repo_dir
            repodata_path = os.path.join(self.new_repo_dir, 'repodata')
            self.assertTrue(self.remote_path_exists(self.ms_node,
                                                    repodata_path,
                                                    False))
        finally:
            self.remove_item(self.ms_node, self.new_repo_dir, su_root=True)

    @attr('all', 'revert', 'story2084', 'story2084_tc05')
    def test_05_p_single_rpm_available_on_nodes_after_import(self):
        """
        Description:
            Verify that a user can import a single rpm file into an existing
            rpm repo and that this rpm becomes available to install on all
            configured nodes
        Actions:
            1. Copy 1 rpm file onto MS
            2. Execute litp import command on that file on MS
            3. Verify that this rpm can be installed/upgraded on all configured
            nodes
        Results:
            All configured nodes can install/upgrade that particular rpm
            contained in the new repo
        """
        try:
            self._put_rpm_on_ms()

            cmd = self.cli.get_import_cmd(self.rpm_remote_path, "litp")
            self.assertEquals(([], [], 0), self.run_command(self.ms_node, cmd))

            sleep(5)  # give it time to perform tasks on nodes
            self.assertTrue(self._rpm_available_on_nodes(self.rpm_pkg_name,
                                                         'litp'))
        finally:
            # repo cleanup
            self.remove_item(self.ms_node,
                             os.path.join(LITP_PKG_REPO_DIR,
                                          self.rpm_file_name),
                             su_root=True)
            self.run_command(self.ms_node,
                             self.rhcmd.get_createrepo_cmd(LITP_PKG_REPO_DIR),
                             su_root=True)

    @attr('all', 'revert', 'story2084', 'story2084_tc07')
    def test_07_n_error_when_importing_path_without_any_rpms(self):
        """
        Description:
            Verify that litp issues a error when a user attempts to import a
            directory without any rpm files in it.
        Actions:
            1. Create empty directory on MS
            2. Execute litp import command on that directory path
            3. Compare command error to the fixture
        Results:
            Litp issues a error about lack of rpms in imported directory
        """
        error = self._get_invalid_path_error_msg(self.rpm_remote_dir)
        cmd = self.cli.get_import_cmd(self.rpm_remote_dir, "litp")
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd)
        self.assertNotEqual(0, returnc)
        self.assertFalse(stdout)
        self.assertTrue(self.is_text_in_list(error, stderr))

    @attr('all', 'revert', 'story2084', 'story2084_tc08')
    def test_08_n_error_when_importing_from_nonexistent_path(self):
        """
        Description:
            Verify that litp issues an error when a user attempts to import a
            directory without any rpm files in it.
        Actions:
            1. Pick a path guaranteed not to exist on MS
            2. Execute litp import command on that directory path
            3. Compare command's error output to the fixture
        Results:
            Litp issues an error about nonexisting path
        """
        path = os.path.join(self.rpm_remote_dir,
                            'sure_as_hell_theres_no_dir_like_me')
        error = self._get_invalid_path_error_msg(path)
        cmd = self.cli.get_import_cmd(path, "litp")
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd)
        self.assertNotEqual(0, returnc)
        self.assertFalse(stdout)
        self.assertTrue(self.is_text_in_list(error, stderr))

    @attr('all', 'revert', 'story2084', 'story2084_tc09')
    def test_09_n_error_when_importing_non_rpm_single_file(self):
        """
        Description:
            Verify that litp issues an error when a user attempts to import a
            single non-rpm file.
        Actions:
            1. Create 1 file that isn't an rpm on MS
            2. Execute litp import command on that file's path
            3. Compare command's error output to the fixture
        Results:
            Litp issues an error about file not being an rpm
        """
        self._put_rpm_on_ms()
        # rename .rpm to .txt
        file_path = os.path.join(self.rpm_remote_dir, 'file.txt')
        self.mv_file_on_node(self.ms_node, self.rpm_remote_path,
                             file_path)

        error = self._get_invalid_path_error_msg(file_path)
        cmd = self.cli.get_import_cmd(file_path, "litp")
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd)
        self.assertNotEqual(0, returnc)
        self.assertFalse(stdout)
        self.assertTrue(self.is_text_in_list(error, stderr))

    @attr('all', 'revert', 'story2084', 'story2084_tc10')
    def test_10_n_no_rpms_get_imported_from_subdir_in_path(self):
        """
        Description:
            Verify that litp doesn't ascend into subdirectories when importing
            rpms from a dir path.
        Actions:
            1. Create a dir with a subdir on MS
            2. Copy 1 rpm file into the subdir on MS
            2. Execute litp import command on that file's path
            3. Compare command's error output to the fixture
        Results:
            Litp issues a error about lack of rpms in imported directory
        """
        self.rpm_remote_path = os.path.join(
            self.rpm_remote_dir, 'subdir', self.rpm_file_name)
        self.create_dir_on_node(self.ms_node,
                                os.path.join(self.rpm_remote_dir, 'subdir'))

        self._put_rpm_on_ms()

        error = self._get_invalid_path_error_msg(self.rpm_remote_dir)
        cmd = self.cli.get_import_cmd(self.rpm_remote_dir, "litp")
        stdout, stderr, returnc = self.run_command(self.ms_node, cmd)
        self.assertNotEqual(0, returnc)
        self.assertFalse(stdout)
        self.assertTrue(self.is_text_in_list(error, stderr))
