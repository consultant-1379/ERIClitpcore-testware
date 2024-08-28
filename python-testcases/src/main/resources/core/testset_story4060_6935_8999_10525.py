# -*- coding: utf-8 -*-
# coding: utf-8

"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     September 2015
@author:    Maria Varley
@summary:   Integration test for story 4060: As a packager of a product to be
            deployed on LITP I want the contents of my LITP compliant ISO to be
            imported.
            Agile: STORY-4060
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import re
import os
import json
from redhat_cmd_utils import RHCmdUtils
from time import sleep
import test_constants


class Story4060(GenericTest):
    """
    Description:
    I want the contents of my LITP compliant ISO to be imported.

    Original Tests have been refactored as follows:
    test_01_p_the_litpd_mmode_until_import_finishes_successfully
    covered by:test_01_p_import_compliant_dir_iso_success

    test_02_p_no_mmode_preliminary_validation_checks_fail
    covered by: test_03_n_import_compliant_dir_iso_validation

    test_03_p_RPMs_in_litp_plugins_dir_are_be_added_to_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_04 and test_05 not in original test file

    test_06_p_RPMs_litp_plugins_project_dir_added_new_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_07_p_RPMs_in_repos_project_dir_added_to_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_08_p_RPMs_repos_project_subproj_added_new_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_09_p_RPMs_repos_project_subproj_dir_added_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_10_p_images_in_path_images_project_dir_imported
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_11_p_images_in_images_project_subproject_dir_imported
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_12_p_no_chksum_generate_one
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_13_p_chksum_doesnt_match
    covered by:test_03_n_import_compliant_dir_iso_validation

    test_14_p_chksum_file_exists_no_image_file
    covered by:test_03_n_import_compliant_dir_iso_validation

    test_15_p_rpms_and_xml_files_imported_others_ignored
    covered by:test_01_p_import_compliant_dir_iso_success

    test_16 not in original test file

    test_17_p_md5_files_imported_chksums_generated
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_18_p_import_fails_litpd_remains_in_mmode
    covered by:test_04_n_import_compliant_dir_iso_failure

    test_19_p_the_RPMs_in_litp_3pp_dir_added_to_3PP_yum_repo
    covered by:test_01_p_import_compliant_dir_iso_success

    test_20_p_import_handles_filenames_all_chars
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_21_p_import_handles_directory_all_chars
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_22_p_import_modify_permissions_to_min
    covered by:test_05_p_import_compliant_dir_iso_permissions

    test_23_p_import_modify_perms_to_a_min_on_dst_folders
    covered by:test_05_p_import_compliant_dir_iso_permissions

    test_24_p_import_fails_RPM_file_rsync_fails
    covered by:test_04_n_import_compliant_dir_iso_failure

    test_25_p_import_fails_image_rsync_fails
    covered by:test_04_n_import_compliant_dir_iso_failure

    test_27_p_import_iso_succeeds_if_overwriting_files_on_dst
    covered by:test_02_p_images_in_path_images_project_dir_imported

    test_28_p_import_success_chksum_no_read_permissions
    covered by:test_05_p_import_compliant_dir_iso_permissions

    test_29_p_an_error_is_returned_if_files_are_zero_length
    covered by:test_03_n_import_compliant_dir_iso_validation

    test_30, test_31 and test_32 not in original file

    test_33_p_the_import_succeeds_for_very_long_filenames
    remains

    test_34_p_the_import_succeeds_for_multiple_projects
    covered by:test_01_p_import_compliant_dir_iso_success

    test_35 not in original test file

    test_36_p_the_import_process_terminates_cleanly_on_success
    covered by:test_01_p_import_compliant_dir_iso_success

    test_37_p_the_import_process_terminates_cleanly_on_failure
    covered by:test_04_n_import_compliant_dir_iso_failure

    test_38 not in original test file

    test_39_p_help_for_the_import_iso_command
    moved to ERIClitpcli

    test_40_p_empty_project_directories_still_generate_a_new_repo
    remains

    test_41_p_litp_plugins_project_added_to_plugins
    covered by:test_01_p_import_compliant_dir_iso_success

    test_42_p_litp_plugins_repository_is_enforced_by_puppet
    remains

    test_43_p_import_succeeds_status_file_removed
    covered by:test_01_p_import_compliant_dir_iso_success

    test_44_p_import_fails_litpd_in_mmode_status_file_fail
    covered by:test_04_n_import_compliant_dir_iso_failure

    test_45_p_mmode_no_status_file_litpd_restart
    remains

    test_46_p_mmode_litpd_restarted_state_running
    remains

    test_47_p_exception_if_iso_is_empty
    covered by:test_03_n_import_compliant_dir_iso_validation
    """

    def setUp(self):
        """ Setup variables for every test """
        super(Story4060, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.all_nodes = [self.ms_node] + self.mn_nodes
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()

        self.iso_remote_path = "/tmp/story4060/"
        self.plan_timeout_mins = 10
        self.puppet_agent_lock_file = "/var/lib/puppet/state/"\
            "agent_disabled.lock"
        self.audit_key = "agentaudit"
        self.maintenance_url = "/litp/maintenance"
        self.audit_config = "/usr/lib/systemd/system/auditd.service"

    def tearDown(self):
        """ Called after every test"""
        super(Story4060, self).tearDown()

    def _do_cleanup(self, files, restore):
        """
        Does cleanup: deletes files and repos that were added
            by the import_iso command.
            files: list of  files that need to be removed(paths)
            restore: filepaths to be restored (filepath where
                   the current file is with, and where it used
                   to be as a list of tuples)
        """
        for filename in files:
            cmd = "/bin/rm -rf  {0}".format(filename)
            self.run_command(self.ms_node, cmd, su_root=True)

        if restore:
            for filename, expath in restore:
                cmd = "ls -rf  {0}".format(filename)
                _, _, ret_code = self.run_command(
                    self.ms_node, cmd + ' 2>/dev/null', su_root=True)
                if ret_code == 0:
                    cmd = "/bin/mv -fT {0} {1}".format(filename, expath)
                    self.run_command(self.ms_node, cmd, su_root=True)

        self._clean_yum_cache()

    def _clean_yum_cache(self):
        """ Clear cached yum metadata on the MS """
        # Run these command as both litp-admin and root, to clear
        # the per-user cache in /var/tmp/yum-litp-admin-*/
        # and the system-wide cache in /var/cache/yum/

        cmd = self.rhcmd.get_yum_cmd('clean metadata')

        for su_root in (True, False):
            node = self.ms_node
            _, _, returnc = self.run_command(node, cmd, su_root=su_root)
            if returnc != 0:
                return False
        return True

    def _mount_image(self, iso_id, as_root=True):
        """ Simulate mounting an ISO on the MS by copying an image directory
        to the MS.

        All images will be in the test scripts local directory ./4060_isos/
        They will be named "iso_dir_<iso_id>
        e.g.  .../core/4060_isos/iso_dir_01/
        """
        iso_dir = "iso_dir_{0}".format(iso_id)
        tar_filename = iso_dir + ".gz.tar"
        iso_local_path = os.path.join(os.path.dirname(__file__), "4060_isos/")
        local_tar_file = iso_local_path + tar_filename

        self.create_dir_on_node(self.ms_node, self.iso_remote_path)

        # 1. Tar up local directory
        tar_cmd = self.rhcmd.get_tar_cmd("czvf", local_tar_file, iso_dir)
        cmd = "cd {0} ; ".format(iso_local_path) + tar_cmd
        self.run_command_local(cmd)

        # 2. Copy tar file to MS
        self.copy_file_to(self.ms_node,
                          local_tar_file,
                          self.iso_remote_path,
                          root_copy=as_root)

        # 3. Untar the tar file in /tmp
        dest_dir = "--directory={0}".format(self.iso_remote_path)
        untar_cmd = self.rhcmd.get_tar_cmd("xmzvf", self.iso_remote_path +
                                           tar_filename,
                                           dest=dest_dir)

        out, err, ret_code = self.run_command(self.ms_node, untar_cmd)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertNotEqual([], out)

        # 4. Remove local tar files
        cmd = "/bin/rm {0}".format(local_tar_file)
        self.run_command_local(cmd)

    def _generate_random_file(self,
                              iso_id,
                              file_name,
                              space,
                              local_folder="images/img-proj"):
        """ File generation by using GNU fallocate command, faster than
        using a random generator.

        File will be created under iso_remote_path/iso_dir_<iso_id>/
        <local_folder> with size indicated in space. I.e. 8.4GB = 8589934592
        e.g.  /tmp/story4060/iso_dir_50/images/myimages/a_file_name.img
        """
        iso_dir = "iso_dir_{0}".format(iso_id)

        local_folder_cmd = os.path.join(os.path.dirname(__file__),
                                        "4060_isos/" + iso_dir)
        self.run_command_local("/bin/mkdir -p " + local_folder_cmd + "/" +
                               local_folder)

        iso_file_local_path = os.path.join(os.path.dirname(
            __file__), "4060_isos/" + iso_dir + "/" + local_folder)

        # 1. Allocate space for file
        if space != "0":
            fallocate_cmd = self.rhcmd.get_fallocate_cmd("-l " + space,
                                                         file_name)
            cmd = "cd {0} ; ".format(iso_file_local_path) + fallocate_cmd
        else:
            cmd = "/bin/touch " + iso_file_local_path + "/" + file_name
        _, err, ret_code = self.run_command_local(cmd)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)

    def _rpm_or_image_available_on_ms(self, pkg_name, repo_name,
                                      check_www=False,
                                      filepart=None,
                                      is_img=False):
        """ Check if rpm is available on ms in a specific repo.
            pkg_name: package name to look for
            repo_name: repo where to look
            check_www: flag to show whether to look in the www folder or
                     do a repo query
            filepart: helps build the filepath ( eg for
                     <repo_path>/repodata/repomd.xml)
            is_img: this is a flag to say if this is an image or not
                   Different rules apply to images.
        """
        if not check_www:
            cmd = self.rhcmd.get_yum_cmd(
                'search {0} --disablerepo="*" --enablerepo="{1}"'.format(
                    pkg_name, repo_name.upper()))
            node = self.ms_node
            _, _, returnc = self.run_command(node, cmd)
            if returnc == 0:
                return True
            else:
                return False
        else:
            if not is_img:
                result = (self.remote_path_exists(
                    self.ms_node,
                    os.path.join(test_constants.PARENT_PKG_REPO_DIR,
                                 filepart,
                                 'repodata/repomd.xml')) and
                          self.remote_path_exists(self.ms_node,
                          os.path.join(test_constants.PARENT_PKG_REPO_DIR,
                                       filepart, pkg_name)))
            else:
                result = self.remote_path_exists(self.ms_node,
                                                 os.path.
                                                 join(test_constants.
                                                      PARENT_PKG_REPO_DIR,
                                                      filepart, pkg_name))
            return result

    def _litp_in_mmode(self):
        """ Determine if litp is in maintenance mode. """
        # Modified the path as in LITPCDS-8999 '/litp/maintenance' will be
        # exposed
        show_cmd = self.cli.get_show_cmd("/")
        _, err, _ = self.run_command(self.ms_node, show_cmd)
        exp_err = ["ServerUnavailableError    LITP is in maintenance mode"]
        return err == exp_err

    def _set_litp_mmode(self, enable=True):
        """ Set the maintenance mode of litp. Defaults to enabling it. """
        if enable:
            prop_val = "enabled=true"
        else:
            prop_val = "enabled=false"
        self.execute_cli_update_cmd(
            self.ms_node, '/litp/maintenance', prop_val)

    def _litp_enters_mmode(self, log_len=0):
        """ Wait for log message saying litp has entered maintenance mode. """
        match = self._wait_for_message(
                    '/litp/maintenance',
                    "INFO: Updated item /litp/maintenance. "
                    "Updated properties: 'enabled': true",
                    log_len=log_len,
                    timeout_sec=180)
        return match is not None

    def _get_sys_log_len(self):
        """ Find length (in lines) of system log file. """
        return self.get_file_len(self.ms_node,
                                 test_constants.GEN_SYSTEM_LOG_PATH)

    def _wait_for_message(self, grep_filter, message_expr,
                          log_len=0, timeout_sec=180):
        """ Wait for a message to appear in the system log.
            The check looks at all lines added to the log beyond the
            length specified as log_len. (Or the current length, if
            log_len is zero.)  We first grep for lines matching 'grep_filter',
            then search those for lines matching the regex 'message_expr'
            which may contain regex groups, etc.
            The return value is the match object as returned by re.search(),
            or None if the timeout is reached without seeing a match.
        """
        elapsed_sec = 0
        interval_sec = 5
        log_path = test_constants.GEN_SYSTEM_LOG_PATH

        # Get current log length
        if log_len == 0:
            log_len = self._get_sys_log_len()
        self.assertTrue(log_len != 0, "Log file not found")

        reg = re.compile(message_expr, re.DOTALL)

        while elapsed_sec < timeout_sec:
            # Check if message is in the latest messages
            curr_log_pos = self.get_file_len(self.ms_node, log_path)
            test_logs_len = curr_log_pos - log_len
            cmd = self.rhcmd.get_grep_file_cmd(log_path, grep_filter,
                                               file_access_cmd="tail -n {0}"
                                               .format(test_logs_len))
            out, err, ret_code = self.run_command(self.ms_node, cmd)
            self.assertTrue(ret_code < 2)
            self.assertEqual([], err)

            for line in out:
                match = reg.search(line)
                if match:
                    return match

            self.log("info", "ISO Importer message not found in last "
                     "{0} seconds.".format(str(elapsed_sec)))
            sleep(interval_sec)
            elapsed_sec += interval_sec

    def _get_job_state(self):
        """
        Fetch information about the state of the import_iso job as indicated by
        the status file.

        Returns a 3-tuple:   (exists, pid, status)

        exists    - true if the job status file exists, false otherwise
        pid       - the pid value from the file.  None if exists is false.
        status    - the status value from the file.  None if exists is false.
        """

        filecheck = "ls " + test_constants.LITP_MAINT_STATE_FILE
        _, _, ret_code = self.run_command(self.ms_node, filecheck,
                                          su_root=True,
                                          su_timeout_secs=600)
        if ret_code != 0:
            return False, None, None

        filecontents = self.get_file_contents(self.ms_node,
                                              test_constants.
                                              LITP_MAINT_STATE_FILE,
                                              tail=None,
                                              su_root=True)

        data = json.loads(filecontents[0])
        return True, data['pid'], data['state']

    def _run_ms_cmd_ok(self, cmd):
        """
        Run command on MS, assert it exits zero and produces nothing on stderr
        """
        _, err, ret_code = self.run_command(self.ms_node, cmd,
                                            su_root=True,
                                            su_timeout_secs=600)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)

    def _remove_state_file(self):
        """
        Remove the file that holds import_iso job state.
        """
        cmd = "/bin/rm -f {0}".format(test_constants.LITP_MAINT_STATE_FILE)
        self._run_ms_cmd_ok(cmd)

    def _write_state_file(self, pid, state):
        """
        Write the file that holds import_iso job state.
        """
        state_data = {'pid': pid, 'state': state}
        json_data = json.dumps(state_data)
        cmd = "/bin/echo '{0}' > {1}".format(
            json_data, test_constants.LITP_MAINT_STATE_FILE)
        self._run_ms_cmd_ok(cmd)

    def _backup_repos(self, repos=None):
        """
        Backup the yum repositories. By default it backs up '3pp_rhel7',
        'litp" & 'litp_plugins'. If a repo doesn't exist it creates a
        directory: '<reponame>_none'
        """
        if repos is None:
            repos = ["3pp_rhel7", "litp", "litp_plugins"]

        repo_paths = [os.path.join(test_constants.PARENT_PKG_REPO_DIR, repo)
                      for repo in repos]

        for repo in repo_paths:
            if self.remote_path_exists(self.ms_node, repo, expect_file=False):
                cmds = ["/bin/mv {0} {0}_bak".format(repo),
                        "/usr/bin/rsync -azH  {0}_bak/ {0}/".format(repo)]
                for cmd in cmds:
                    out, err, ret_code = self.run_command(self.ms_node,
                                                          cmd,
                                                          su_root=True,
                                                          su_timeout_secs=600)
                    self.assertEqual(0, ret_code)
                    self.assertEqual([], err)
                    self.assertEqual([], out)
            else:
                cmd = "/bin/mkdir {0}_none".format(repo)
                out, err, ret_code = self.run_command(self.ms_node,
                                                      cmd,
                                                      su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                self.assertEqual([], out)

    def _restore_repos(self, repos=None):
        """ Restore the repos that were backed up by _backup_repos(). """
        if repos is None:
            repos = ["3pp_rhel7", "litp", "litp_plugins"]

        repo_paths = [os.path.join(test_constants.PARENT_PKG_REPO_DIR, repo)
                      for repo in repos]

        for repo in repo_paths:
            if self.remote_path_exists(self.ms_node, "{0}_bak".format(repo),
                                       expect_file=False):
                cmds = ["/bin/rm -rf {0}".format(repo),
                        "/bin/mv -fT {0}_bak/ {0}/".format(repo)]
                for cmd in cmds:
                    self.run_command(self.ms_node, cmd, su_root=True)

            elif self.remote_path_exists(self.ms_node, "{0}_none"
                                         .format(repo),
                                         expect_file=False):
                cmds = ["/bin/rm -rf {0}".format(repo),
                        "/bin/rmdir {0}_none".format(repo)]
                for cmd in cmds:
                    self.run_command(self.ms_node, cmd, su_root=True)

        self._clean_yum_cache()

    def _uninstall_packages(self, nodes, test_pkgs, nodeps=False):
        """ Uninstall test_pkgs from the nodes """
        for node in nodes:
            for package in test_pkgs:
                cmd = "/bin/rpm -e "
                cmd += "--nodeps " if nodeps else ''
                cmd += package
                _, _, ret_code = self.run_command(node, cmd, su_root=True)
                self.assertTrue(ret_code in [0, 1])

    def _verify_test_pkgs_removed(self, nodes, rpms):
        """ Verify packages removed"""

        for node in nodes:
            cmd = self.rhcmd.check_pkg_installed(rpms)
            rpm_ver, err, ret_code = self.run_command(node, cmd)
            self.assertEqual([], rpm_ver)
            self.assertEqual([], err)
            self.assertTrue(ret_code <= 1)

    def _are_rpms_available(self, node_list, rpms_list):
        """ Check if rpms are available on nodes."""
        _rpm_availability_list = []
        for node in node_list:
            for rpm in rpms_list:
                cmd = ("repoquery -q --qf "
                       "'%{name}-%{version}-%{release}.%{arch}' " + rpm)
                out, err, ret_code = self.run_command(node,
                                                      cmd,
                                                      su_root=True)
                self.assertFalse(err)
                self.assertEqual(0, ret_code)
                result = self.is_text_in_list(rpm, out)
                _rpm_availability_list.append(result)

        return "False" in _rpm_availability_list

    def _import_rpms(self, rpms, repo=test_constants.OS_UPDATES_PATH_RHEL7):
        """
        Description:
            This method will import some rpms to test the upgrade process.
            Kernel upgrades's require the node to be rebooted after the package
            is installed so we support with and without kernel packages.
        Actions:
            1. Select RPM packages to upgrade.
            2. Create a directory for rpms
            3. Copy RPMs into /tmp on the MS.
            4. Import RPMs with LITP import cmd into update repo.
        """
        rpms_local_paths = []
        rpms_remote_paths = []
        rpm_remote_dir = '/tmp/story4060'
        dir_to_import = rpm_remote_dir + "/rpm_to_import"
        rpm_local_dir = "4060_rpms/"
        for rpm in rpms:
            rpms_local_paths.append(os.path.join(os.path.dirname(__file__),
                                                 rpm_local_dir + rpm)
                                    )

            rpms_remote_paths.append(os.path.join(dir_to_import,
                                                  rpm)
                                     )

        # 1. Select RPM packages to upgrade.
        local_file_paths = rpms_local_paths

        # 2. Create a directory for rpms to import. If it exists, remove it and
        # create it again
        self.create_dir_on_node(self.ms_node, rpm_remote_dir)
        if self.remote_path_exists(self.ms_node,
                                   dir_to_import,
                                   expect_file=False):
            self.assertTrue(self.remove_item(self.ms_node, dir_to_import))

        self.create_dir_on_node(self.ms_node, dir_to_import)

        # 3. Copy RPMs into /tmp on the ms
        for loc_path in local_file_paths:
            self.assertTrue(self.copy_file_to(self.ms_node,
                                              loc_path,
                                              dir_to_import))

        # 4. Import them with LITP import cmd into update repo
        self.execute_cli_import_cmd(self.ms_node,
                                    dir_to_import,
                                    repo)

    def _cleanup_repos(self, nodes, rpm_list, repo_path, nodeps=False):
        """
        This method downgrades packages to prev version and cleans up yum repos
        after running tests.
            1. Remove RPMs from the yum repository on MS.
            2. Update the yum repository.
            3. Clean the yum cache so queries will use actual repo contents.
            4. Verify on MS, that new rpms are not available".
            5. Uninstall test packages
        """
        all_nodes = nodes + [self.ms_node]

        # 1. Remove RPMs from the yum repository on MS.
        for rpm in rpm_list:
            self.log("info", "Removing: {0} from the repo: {1}"
                     .format(rpm, repo_path))
            repo_to_rm = repo_path + '/' + rpm
            self.assertTrue(self.remove_item(self.ms_node,
                                             repo_to_rm,
                                             su_root=True))

        # 2. Update the yum repository.
        cmd = "/usr/bin/createrepo --update " + repo_path

        _, err, ret_code = self.run_command(self.ms_node,
                                            cmd,
                                            su_root=True,
                                            su_timeout_secs=120)
        self.assertEqual(0, ret_code)
        self.assertFalse(err)

        # 3. Clean the yum cache.
        cmd = self.rhcmd.get_yum_cmd("clean all")
        for node in all_nodes:
            _, err, ret_code = self.run_command(node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            self.assertFalse(err)

        # 4. Verify on ms, that new rpms are not available.
        pkg_list = [rpm.split('-')[0] for rpm in rpm_list]
        self.assertFalse(self._are_rpms_available(all_nodes, pkg_list))

        for package in rpm_list:
            cmd = "/bin/rpm -e " + "--nodeps " if nodeps else ''
            cmd += package.split('-')[0]
            _, err, ret_code = self.run_command(self.ms_node, cmd,
                                                su_root=True)
            self.assertTrue(ret_code in [0, 1])
            self._verify_test_pkgs_removed([self.ms_node],
                                           [package.split('-')[0]])

    def _create_my_repo(self, repo_dir):
        """
        Function which creates a test repo to be used for these tests
        """
        cmd = "/bin/mkdir {0}".format(repo_dir)
        self.run_command(self.ms_node, cmd,
                         su_root=True, default_asserts=False)
        cmd = self.rhcmd.get_createrepo_cmd(repo_dir, update=False)
        self.run_command(
            self.ms_node, cmd, su_root=True)
        self._check_yum_repo_is_present(repo_dir)

    def _check_yum_repo_is_present(self, repo_path):
        """
        Check that file /repodata/repomd.xml file exist under repo folder
        """
        repmod_path = repo_path + '/repodata/repomd.xml'
        self.assertTrue(self.remote_path_exists(self.ms_node, repmod_path),
                        '<{0}> not found'.format(repmod_path))

    def _set_auditctl_rules(self, nodes, filename, permissions, keyname):
        """
        sets filters for auditctls, returns current
        time on nodes
        """
        old_str = 'RefuseManualStop=yes'
        new_str = 'RefuseManualStop=no'
        times = dict()
        # restart auditd
        cmd = self.rhcmd.get_replace_str_in_file_cmd(old_str, new_str,
                                                     self.audit_config,
                                                     sed_args='-i')
        for node in nodes:
            self.run_command(node, cmd, su_root=True, default_asserts=True)
            self.systemctl_daemon_reload(node)

            self.restart_service(node, "auditd", assert_success=True)
            # set rules
            self.run_command(node, "/sbin/auditctl -w {0} -p {1} -k {2}".
                             format(filename, permissions, keyname),
                             su_root=True)
            time, _, _ = self.run_command(node, "/bin/date +%T")
            times[node] = time[0]
        return times

    def _check_maintenance_properties(self, enabled, initiator, status=None):
        """ Check maintenance properties """
        maintenance_props = self.get_props_from_url(self.ms_node,
                                                    self.maintenance_url)

        self.assertEqual(maintenance_props['enabled'],
                         enabled,
                         "Unexpected value in 'enabled' property")

        self.assertEqual(maintenance_props['initiator'],
                         initiator,
                         "Unexpected value in 'initiator' property")

        if status:
            self.assertEqual(maintenance_props['status'], status)

    def check_for_audit_message(self, node, keyname, action,
                                starttime, endtime):
        """
        checks whether the action is found in audit logs between starttime and
        endtime
        """
        _, _, rc = self.run_command(node,
                                    '/sbin/ausearch -k {0} -ts {1} '
                                    '-te {2}| grep objtype={3}'.
                                    format(keyname, starttime,
                                           endtime, action), su_root=True)
        return rc == 0

    def _remove_auditctl_rules(self, nodes, filename, permissions, keyname):
        """
        removes filters for auditctls
        """
        # restart auditd
        for node in nodes:
            # remove rules
            self.run_command(node, "/sbin/auditctl -W {0} -p {1} -k {2}".
                             format(filename, permissions, keyname),
                             su_root=True)

    def _litp_in_mmode_after_restart(self):
        """ Determine if litp is in maintenance mode after restarting litp. """
        # Check text in messages log
        log_path = test_constants.GEN_SYSTEM_LOG_PATH

        log_len = self.get_file_len(self.ms_node, log_path)
        self.assertTrue(log_len, "Log file not found")

        text_to_find = "Updated item /litp/maintenance. " +\
            "Updated properties: 'enabled': true"

        # Restart litpd process.
        self.restart_litpd_service(self.ms_node, debug_on=False)
        self.assertTrue(self.wait_for_log_msg(self.ms_node, text_to_find,
                        timeout_sec=20, log_len=log_len))

        # Modified the path as in LITPCDS-8999 '/litp/maintenance' will be
        # exposed
        show_cmd = self.cli.get_show_cmd("/")
        _, err, _ = self.run_command(self.ms_node, show_cmd)
        exp_err = ["ServerUnavailableError    LITP is in maintenance mode"]
        return err == exp_err

    def _run_yum_once_and_then_lock(self):
        """ Execute yum command and then create yum lock"""
        # 1. Replace the yum binary with a dummy that returns non-zero
        yum_path = self.rhcmd.get_yum_cmd("").strip()

        cmd = self.rhcmd.get_move_cmd(yum_path,
                                      (yum_path + "_old"))

        out, _, _ = self.run_command(self.ms_node, cmd, su_root=True,
                                     default_asserts=True)
        self.assertEqual([], out)

        file_contents = [
                '#!/bin/bash',
                'output=$(/usr/bin/yum_old $@)',
                'rc=$?',
                '/bin/echo "1" > /var/run/yum.pid',
                'echo $output',
                'exit $rc'
                ]

        create_success = self.create_file_on_node(self.ms_node, yum_path,
                                                  file_contents,
                                                  su_root=True,
                                                  add_to_cleanup=False)
        self.assertTrue(create_success, "File could not be created")

        cmd = "/bin/chmod +x " + yum_path
        self.run_command(self.ms_node, cmd, su_root=True, default_asserts=True)

    def _fix_yum(self):
        """ Restore original yum to the proper location. """
        yum_path = self.rhcmd.get_yum_cmd("").strip()
        cmd = self.rhcmd.get_move_cmd((yum_path + "_old"), yum_path, True)

        self.run_command(self.ms_node, cmd, su_root=True)

        cmd = "rm -rf /var/run/yum.pid"
        self.run_command(self.ms_node, cmd, su_root=True)

    def _update_maintenance_property(self, prop, value, assert_success=True):
        """ Update property in maintenance """
        cmd_update_status = self.cli.get_update_cmd(self.maintenance_url,
                                                    "{0}={1}".format(prop,
                                                                     value))
        out, err, rc = self.run_command(self.ms_node, cmd_update_status)

        if assert_success:
            self.assertEqual([], err)
            self.assertEqual(rc, 0)
        else:
            expected_error = "Unable to modify readonly property"
            self.assertTrue(self.is_text_in_list(expected_error, err))
            self.assertEqual([], out)
            self.assertEqual(rc, 1)

    @attr('all', 'revert', 'story4060', 'story4060_tc01', 'bur_only_test')
    def test_01_p_import_compliant_dir_iso_success(self):
        """
        @tms_id: litpcds_4060_tc01
        @tms_requirements_id: LITPCDS-4600
        @tms_title: Verify import iso functionality
        @tms_description: Description:
        -This test will verify that the RPMs present in the
        <path>/repos/<project> directory are added to a yum repository
        named "<project>". (Repo doesn't exist)
        -This test will verify that the RPMs present in the
        <path>/repos/<project> directory are added to a yum repository
        named "<project>"  (Repo already exists)
        -This test will verify that the RPMs present in the
        <path>/repos/<project>/<subproject> directory are added to a yum
        repository named "<project>_<subproject>". (destination directory
        doesn't exist)
        -This test will verify that the RPMs present in the
        <path>/litp/3pp/ directory are added to the 3PP yum repository.
        The repo are recreated and the new RPMs are available.
        -When "litp import_iso <path>" is executed on a compliant directory
        structure then the litpd service will enter maintenance mode,
        the RPMs present in the <path> will be added to the LITP yum
        repository and the litpd service will remain in maintenance mode
        until the import_iso is complete
        -This test will verify that all rpms (and a comps.xml file if it
        exists) are imported and other files are ignored.
        -This test will verify that the RPMs present in the
        <path>/litp/plugins/<project> directory are added to a yum
        repository named "litp_plugins"

        STORY 6935:
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure the packages from LITP_PLUGINS repo,
        excluding packages that match ERIClitpmn*, are installed/upgraded
        on the MS
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure the upgrades from 3PP repo are
        updated on the MS if it was previously installed
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure the new packages from 3PP repo
        will be installed only if LITP or LITP_PLUGINS packages depend
        on them
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure the new packages from OS and
        UPDATES repo will be installed only if LITP, LITP_PLUGINS or 3PP
        packages depend on them and the previously installed will be
        updated
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure the already installed packages
        from <PROJECT> and <PROJECT>_<SUBPROJECT> repo are upgraded on
        the MS
        -This test verifies that yum gets locked while packages are
        getting installed

        STORY 8999_10525
        -This test will verify that when user runs import_iso on a LITP
        compliant directory structure and the proccess is ongoing,
        the 'status' and 'initiator' properties in maintenance item are
        'Running' and 'import_iso', and when it finishes successfully
        the 'status' and 'initiator' properties are 'Done' and
        'import_iso' and puppet is enabled
        @tms_test_steps:
            @step: Backup the  Litp repositories
            @result: The backup is successful.
            @step: Import packages to OS and UPDATES repos
            @result: Packages are imported and updated
            @step: Install old versions of test packages
            @result: The old versions of test packages are installed
            @step: Model repos in LITP including:
                Run createrepo command for test repo
                Create yum repo in LITP model for each
                The MS inherits from yum repo item
            @result: LITP model is updated
            @step: Create and run plan
            @result: The plan is running.
            @step: Copy the initial LITP compliant iso archive with
               a compliant directory structure to the MS
            @result: The iso structure is copied to the MS
            @step: Start auditing puppet lockfiles
            @result: Filters for auditctls, returns correct
                time from nodes
            @step: Execute "litp import_iso" on the directory
                and Verify that litp is in maintenance mode.
            @result: The iso is imported and litp is in maintenance mode.
            @step: Check maintenance item properties during import_iso
            @result: The import_iso item properties values are correct.
            @step: Check maintenance item properties during import_iso
            @result: The import_iso item properties values are correct.
            @step: Try to acquire yum lock
            @result: The yum lock is in place.
            @step: Check if puppet is enabled after the import.
            @result: puppet status is correct.
            @step: Check maintenance item properties after import_iso.
            @result: The status is correct and the system is not in
                maintenance state.
            @step: Verify that packages were installed/upgraded/no installed
            @result: Packages are correct.
            @step: Verify that packages were installed/upgraded/no installed
            @result: Packages are correct.
            @step: Check that the RPMs present in the right path
            @result: The path is as expected.
            @step: Check that the RPMs present in the right path
            @result: The path is as expected.
        @tms_test_precondition: The iso structure which is used can
            be found here:
            "python-testcases/src/main/resources/core/4060_isos/
            iso_dir_4060_6935_8999_10525"
            The rpm's used during the test can be found here:
            "python-testcases/src/main/resources/core/4060_rpms"
        @tms_execution_type: Automated
        """
        file_action = "CREATE"
        repos = ["3pp_rhel7", "litp", "litp_plugins"]

        # Name of test repos
        test_repos = ["repo1", "repo1_sub", "empty_repo"]
        test_repo_dirs = [r + '_rhel7' for r in test_repos]

        # Get path in model of software items.
        sw_items = self.find(self.ms_node,
                             "/software",
                             "collection-of-software-item")
        self.assertNotEqual([], sw_items)
        sw_items_path = sw_items[0]

        # Get MS path
        ms_path = self.find(self.ms_node, "/ms", "ms", True)
        ms_sw_items_url = ms_path[0] + "/items"

        # dictionary of test packages and regex to use in verifying if the
        # package is installed
        test_pkgs = {"litp_plugin1": "litp_plugin1",
                     "litp_plugin2": "litp_plugin2",
                     "litp_3pp1": "litp_3pp1",
                     "litp_3pp2": "litp_3pp2",
                     "litp_3pp_noinstall1": "litp_3pp_noinstall1",
                     "litp_project1": "litp_project1",
                     "litp_sub_project1": "litp_sub_project1",
                     "3pptestpkg": "3pptestpkg",
                     "litptestpkg": "litptestpkg",
                     "updatestestpkg": "updatestestpkg",
                     "update_noinstall1": "update_noinstall1",
                     "ostestpkg": "ostestpkg",
                     "os_noinstall1": "os_noinstall1",
                     "bar": "^bar$",
                     "foo": "^foo$",
                     "ERIClitpmntestpackage": "ERIClitpmntestpackage",
                     "longpackage": "longpackage"
                    }

        old_pkgs = ["litp_plugin1-1.0-1.x86_64.rpm",
                    "litp_3pp1-1.0-1.x86_64.rpm",
                    "litp_3pp2-1.0-1.x86_64.rpm",
                    "litp_project1-1.0-1.x86_64.rpm",
                    "litp_sub_project1-1.0-1.x86_64.rpm"]

        iso_image_id = "4060_6935_8999_10525"
        local_base_path = os.path.dirname(os.path.abspath(__file__))
        base_path = "iso_dir_" + iso_image_id
        iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id

        try:
            self.log("info", "# 1. Backup the  Litp repositories")
            self._backup_repos(repos + test_repo_dirs)

            self.log("info", "# 2. Import packages to OS and UPDATES repos.")
            self._import_rpms(["updatestestpkg-1.0-1.x86_64.rpm",
                               "update_noinstall1-1.0-1.x86_64.rpm"],
                               test_constants.OS_UPDATES_PATH_RHEL7)
            self._import_rpms(["ostestpkg-1.0-1.x86_64.rpm",
                               "os_noinstall1-1.0-1.x86_64.rpm"],
                               '{0}Packages'.format(
                        test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7))

            self.log("info", "# 3. Install old versions of test packages")
            local_rpms = [os.path.join(os.path.dirname(__file__),
                                       "4060_rpms", rpm)
                          for rpm in old_pkgs]
            self.copy_and_install_rpms(self.ms_node, local_rpms)
            self.log("info", "# 4. Model repos in LITP")
            for repo_name, repo_dir_name in zip(test_repos, test_repo_dirs):
                self.log("info", "# 4.1 Run createrepo command for test repo.")
                self._create_my_repo(test_constants.PARENT_PKG_REPO_DIR +
                                     repo_dir_name)

                self.log("info", "# 4.2. Create yum repo in LITP model for "
                         "each")
                sw_items_url = sw_items_path + "/{0}".format(repo_name)
                props = "name='{0}' ms_url_path='/{1}'".format(repo_name,
                                                               repo_dir_name)
                self.execute_cli_create_cmd(self.ms_node,
                                            sw_items_url,
                                            "yum-repository",
                                            props)

                self.log("info", "# 4.3. The MS inherits from yum repo item.")
                self.execute_cli_inherit_cmd(self.ms_node,
                                             "{0}/{1}"
                                             .format(ms_sw_items_url,
                                                     repo_name),
                                             "{0}/{1}".format(sw_items_path,
                                                              repo_name))

                self.log("info", "# Delete repo client files")
                self.del_file_after_run(self.ms_node,
                                        "/etc/yum.repos.d/{0}.repo".
                                        format(repo_name))

            self.log("info", "# 5. Create and run plan")
            self.execute_cli_createplan_cmd(self.ms_node)
            self.execute_cli_runplan_cmd(self.ms_node)
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                            test_constants.PLAN_COMPLETE,
                            self.plan_timeout_mins))

            self.log("info", "# 6. Copy the initial LITP compliant iso "
                     "archive with a compliant directory structure to the MS")
            self._mount_image(iso_image_id)

            # Create an empty repo
            self.create_dir_on_node(self.ms_node,
                                    iso_path + "/repos/empty_repo")

            self.log("info", "# 7. start auditing puppet lockfiles")
            start_times = self._set_auditctl_rules(self.all_nodes,
                                                   self.puppet_agent_lock_file,
                                                   "war",
                                                   self.audit_key)

            self.log("info", "# 8. Execute \"litp import_iso\" on the "
                     "directory")
            log_len = self._get_sys_log_len()
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)

            self.log("info", "# 9. Verify that litp is in maintenance mode.")
            self.assertTrue(self._litp_enters_mmode(log_len=log_len))

            self.log("info", "# 10. Check maintenance item properties during "
                     "import_iso")
            self._check_maintenance_properties(enabled="true",
                                               initiator="import_iso",
                                               status="Running")

            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  "INFO: Asking yum to "
                                                  "install/update package: "
                                                  "longpackage"))

            self.log("info", "# 11. Try to acquire yum lock")
            out, _, rc = self.run_command(self.ms_node,
                                          "/usr/bin/yum check-update",
                                          connection_timeout_secs=10,
                                          execute_timeout=5, su_root=True)

            self.assertTrue("Existing lock /var/run/yum.pid: another copy is "
                            "running as pid" in out[2],
                            "was able to get yum lock")
            self.assertEqual(-1, rc)

            self.log("info", "# 12. Create file to stop installation.")
            # this allows the package longpackage to continue installation
            self.create_file_on_node(self.ms_node, "/tmp/stop", " ")

            self.log("info", "# 13. Wait for import to complete")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  "ISO Importer is finished,"
                                                  " exiting with 0"))

            self.log("info", "# 14. Check if puppet was disabled in the "
                     "mean time")
            for node in self.all_nodes:
                found = self.check_for_audit_message(node, self.audit_key,
                                                     file_action,
                                                     start_times[node], "now")
                self.assertEqual(found, True, "{0} action not found".format(
                    file_action))
                self.log("info", " # Check puppet is enabled after "
                         "import_iso")
                self.assertFalse(self.remote_path_exists(
                    node, self.puppet_agent_lock_file, su_root=True))

            self.log("info", "# 15. Verify success")

            self.log("info", "# 15.1 Check maintenance item properties "
                     "after import_iso")
            self._check_maintenance_properties(enabled="false",
                                               initiator="import_iso",
                                               status="Done")

            self.log("info", "# 15.2 Verify that the status file does not "
                     "exist")
            exists, pid, status = self._get_job_state()
            self.assertFalse(exists)
            self.assertTrue(pid is None)
            self.assertTrue(status is None)

            self.log("info", "# 15.3 Verify that litp is no longer in "
                     "maintenance mode.")
            self.assertFalse(self._litp_in_mmode())

            self.log("info", "# 16. Verify that packages were "
                     "installed/upgraded/no installed")

            self.assertTrue(self.
                            check_pkgs_installed(self.ms_node,
                                                 ["litp_plugin1-2.0-1.x86_64",
                                                  "litp_plugin2-1.0-1.x86_64",
                                                  "litp_3pp1-2.0-1.x86_64",
                                                  "litp_3pp2-2.0-1.x86_64",
                                                  "foo-1.0-1.x86_64",
                                                  "bar-1.0-1.x86_64",
                                                  "updatestestpkg-1.0-"
                                                  "1.x86_64",
                                                  "ostestpkg-1.0-1.x86_64",
                                                  "3pptestpkg-1.0-1.x86_64",
                                                  "litptestpkg-1.0-1.x86_64",
                                                  "litp_project1-2.0-1.x86_64",
                                                  "litp_sub_project1-2.0-1"
                                                  ".x86_64",
                                                  "longpackage-1.1-1."
                                                  "el6.x86_64"
                                                  ]))

            not_installed_pkgs = ["ERIClitpmntestpackage-1.0-1.x86_64",
                                  "litp_3pp_noinstall1-1.0-1.x86_64",
                                  "os_noinstall1-1.0-1.x86_64",
                                  "update_noinstall1-1.0-1.x86_64"]

            for pkg in not_installed_pkgs:
                self.assertFalse(self.check_pkgs_installed(self.ms_node,
                                                           [pkg]))

            self.log("info", "# 17. Check that the RPMs present in the "
                     "right path")

            self.log("info", "# 17.1 <path>/litp/repo/<project> directory "
                     "are added to a repository named project and they are "
                     "available on MS")
            project_dir = 'repos/repo1/'
            project_repo_dir = 'repo1_rhel7'

            rpm_list = [filename for filename
                        in os.listdir(
                                      os.path.
                                      join(local_base_path,
                                           '4060_isos',
                                           base_path,
                                           project_dir))
                        if filename.endswith('.rpm')]
            for pkg in rpm_list:
                check_pkg = \
                    self._rpm_or_image_available_on_ms(pkg, project_dir.
                                                     split('/')[1],
                                                     check_www=True,
                                                     filepart=project_repo_dir)
                self.assertEquals(check_pkg, True)

            self.log("info", "# 17.2 <path>/litp/repo/<project>/<subproject> "
                     "directory are added to a repository named "
                     "project_subproject")
            project_subdir = 'repos/repo1/sub'
            project_sub_repo_dir = 'repo1_sub_rhel7'

            rpm_list1 = [filename for filename in os.listdir(
                os.path.join(local_base_path,
                             '4060_isos',
                             base_path,
                             project_subdir))
                         if filename.endswith('.rpm')]

            for pkg in rpm_list1:
                pkg_chk = self._rpm_or_image_available_on_ms(
                                               pkg,
                                               project_subdir,
                                               check_www=True,
                                               filepart=project_sub_repo_dir)
                self.assertEquals(pkg_chk, True)

            self.log("info", "# 17.3 <path>/litp/plugins/<project> directory "
                     "are added to a yum repository named \"litp_plugins\"")
            plugin_subdir = 'litp/plugins/story_6935_test_01'

            rpm_list = rpm_list + [filename for filename in os.listdir(
                os.path.join(local_base_path,
                             '4060_isos',
                             base_path,
                             plugin_subdir))
                if filename.endswith('.rpm')]

            for pkg in rpm_list:
                self.assertEquals(
                    self._rpm_or_image_available_on_ms(pkg.split('-')[0],
                                                       'litp_plugins'),
                    True)

            self.log("info", "# 17.4 Check that 3PP rpms are available")
            pp3_pkgs = ["3pptestpkg", "bar", "litp_3pp1",
                        "litp_3pp2", "litp_3pp_noinstall"]
            for pkg in pp3_pkgs:
                self.assertTrue(
                    self._rpm_or_image_available_on_ms(pkg, '3pp'))

            self.log("info", "# 17.5 Verify empty repo was imported")
            self._check_yum_repo_is_present(test_constants.
                                            PARENT_PKG_REPO_DIR +
                                            "empty_repo_rhel7")

            self.log("info", "# 17.6.Verify files should be ignored")
            file_no_import = ["noimport_15", "litp/3pp/noimport_15",
                              "litp/plugins/harxmless",
                              "litp/plugins/noimport_15",
                              "litp/plugins/list_of_escarpments"]
            for path in file_no_import:
                self.assertFalse(self.remote_path_exists(
                     self.ms_node, test_constants.
                     PARENT_PKG_REPO_DIR +
                     path))

            self.log("info", "# 17.7 Verify comps.xml file is imported")
            self.assertTrue(self.remote_path_exists(
                     self.ms_node, test_constants.
                     PARENT_PKG_REPO_DIR +
                     project_repo_dir + "/comps.xml"))

        finally:
            # make sure import_iso is done
            # Create file to stop installation.
            # this allows the package longpackage to continue installation
            self.create_file_on_node(self.ms_node, "/tmp/stop", " ")
            counter = 0
            while (self.get_props_from_url(self.ms_node, "/litp/maintenance",
                                           filter_prop="status") ==
                   "Running" and counter < 600):
                sleep(10)
                counter += 10
            self._set_litp_mmode(False)
            self._remove_auditctl_rules(self.all_nodes,
                                        self.puppet_agent_lock_file,
                                        "war",
                                        self.audit_key)
            self._restore_repos(repos + test_repo_dirs)
            self._uninstall_packages([self.ms_node], test_pkgs, nodeps=True)
            # Verify test packages are not on the nodes.
            self._verify_test_pkgs_removed([self.ms_node], test_pkgs.values())
            self._cleanup_repos([],
                                ["updatestestpkg-1.0-1.x86_64.rpm",
                                 "update_noinstall1-1.0-1.x86_64.rpm"],
                                 test_constants.OS_UPDATES_PATH_RHEL7,
                                nodeps=True)

            self._cleanup_repos([],
                                ["ostestpkg-1.0-1.x86_64.rpm",
                                 "os_noinstall1-1.0-1.x86_64.rpm"],
                                '{0}Packages'.format(
                        test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7),
                                nodeps=True)

    @attr('all', 'revert', 'story4060', 'story4060_tc02', 'bur_only_test')
    def test_02_p_images_in_path_images_project_dir_imported(self):
        """
        @tms_id: litpcds_4060_tc02
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that the images and corresponding checksum
            are added to "/var/www/html/images/<project>" and where a
            checksum file doesn't exist we generate one and import it.
        @tms_description: This test will verify that the images and
        corresponding checksum files if present in the <path>/images/<project>
        directory are added to a directory named
        "/var/www/html/images/<project>"
        This test will verify that where a checksum file doesn't exist we
        generate one and import it to the destination directory
        @tms_test_steps:
            @step: Backup the  Litp repositories and copy iso image to ms
            @result: The backup is successful.
            @step: Execute import iso command with different images:
                Image with all permissible characters
                Image with the same name as already present in destination.
            @result: Files are copied into the correct folders on the ms.
            @step: Verify the checksum has been created on destination
            @result: The checksum is correct.
            @step: Verify that the import handles directories with all
                permissible characters, and import_iso successfully
                overwrites a file that already existed
                at the destination.
            @result: The directories are imported, and the file is
                 overwritten .
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # Test Attributes
        # Checksum files
        files = ["image_with_checksum.qcow2",
                 "image_with_checksum.qcow2.md5",
                 "no_checksum_image.qcow2",
                 "random_non_.qcow2_file",
                 "xml_file.xml"]

        # Define paths
        sub_files = [os.path.join(test_constants.PARENT_PKG_REPO_DIR,
                                  "images/ENM/SUB",
                                  "sub_" + filename)
                     for filename in files]

        file_paths = [os.path.join(test_constants.PARENT_PKG_REPO_DIR,
                                   "images/ENM",
                                   filename)
                      for filename in files + sub_files]

        # Create directories and files with all permissible characters
        uncommon_chars_dir1 = r"\!\\\"Â£\$%\^\&\*\(\)_+-\="
        uncommon_chars_file1 = "name1"
        uncommon_chars_file2 = r"\!\\\"Â£\$%\^\&\*\(\)_+-\=.gcow2"
        uncommon_chars_file3 = \
            r"\\\"\\\'\}\{\]\[\#\@\~\;\:\,\.\>\<\?\.gcow2"
        swedish_chars_dir1 = r"Ã…Ã¥Ã„Ã¤Ã–Ã¶"
        swedish_chars_file1 = "name3"
        swedish_chars_file2 = r"Ã…Ã¥Ã„Ã¤Ã–Ã¶.gcow2"

        chars_list1 = [uncommon_chars_file1,
                       uncommon_chars_file2,
                       uncommon_chars_file3]
        chars_list2 = [swedish_chars_file1,
                       swedish_chars_file2]

        remote_proj = "images/chärs3t/"

        project_subdir = ['images/projectname_tc111/subprojectname_tc111/',
                          'images/projectname_tc111/subprojectname_tc112/',
                          'images/projectname_tc112/subprojectname_tc111/',
                          'images/projectname_tc112/subprojectname_tc113/']

        iso_image_id = 'test2'

        try:
            self.log('info', 'Backup the  Litp repositories and copy iso'
                     ' image to ms')
            # 1. Backup the  Litp repositories.
            self._backup_repos(["images"])

            for path in chars_list1:
                self._generate_random_file(iso_id=iso_image_id,
                                           file_name=path,
                                           local_folder=remote_proj +
                                           uncommon_chars_dir1,
                                           space="4096")

            for path in chars_list2:
                self._generate_random_file(iso_id=iso_image_id,
                                           file_name=path,
                                           local_folder=remote_proj +
                                           swedish_chars_dir1,
                                           space="4096")

            sleep(30)
            # 2. Copy iso archive to ms.
            local_base_path = os.path.dirname(os.path.abspath(__file__))
            base_path = "iso_dir_" + iso_image_id
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id
            self._mount_image(iso_id=iso_image_id)

            allowed_exts = ['.qcow2', '.md5']
            image_list1 = [filename for filename
                           in os.listdir(
                                         os.path.
                                         join(local_base_path,
                                              '4060_isos',
                                              base_path,
                                              project_subdir[0]))
                           if (filename.endswith(allowed_exts[0]) or
                               filename.endswith(allowed_exts[1]))]
            image_list2 = [filename for filename
                           in os.listdir(os.path.join(local_base_path,
                                                      '4060_isos',
                                                      base_path,
                                                      project_subdir[1]))
                           if (filename.endswith(allowed_exts[0]) or
                               filename.endswith(allowed_exts[1]))]
            image_list3 = [filename for filename
                           in os.listdir(os.path.join(local_base_path,
                                                      '4060_isos',
                                                      base_path,
                                                      project_subdir[2]))
                           if (filename.endswith(allowed_exts[0]) or
                               filename.endswith(allowed_exts[1]))]
            image_list4 = [filename for filename
                           in os.listdir(os.path.join(local_base_path,
                                                      '4060_isos',
                                                      base_path,
                                                      project_subdir[3]))
                           if (filename.endswith(allowed_exts[0]) or
                               filename.endswith(allowed_exts[1]))]

            # 3. Create a .md5 file in dst with same name than the one
            # to be generated
            fallocate_cmd = self.rhcmd.get_fallocate_cmd(
                "-l 33", "{0}/an_image.gcow2.md5".
                format(test_constants.VM_IMAGE_MS_DIR + "imgproj"))
            cmd = "/usr/sbin/setenforce 0; mkdir -p " +\
                test_constants.VM_IMAGE_MS_DIR + "imgproj; cd " + \
                  test_constants.VM_IMAGE_MS_DIR + "imgproj;"
            _, _, ret_code = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            _, _, ret_code = self.run_command(
                self.ms_node, fallocate_cmd, su_root=True)
            self.assertEqual(0, ret_code)
            create_time = self.get_file_modify_time(self.ms_node,
                                                    test_constants.
                                                    VM_IMAGE_MS_DIR +
                                                    "imgproj/" +
                                                    "an_image.gcow2.md5")
            self.log('info', 'Execute import iso command with different images'
                     ': Image with all permissible characters, '
                     'Image with the same name as already present '
                     'in destination.')
            # 2. Execute import iso command
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)

            # 3. Wait for import to complete
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  "ISO Importer is finished,"
                                                  " exiting with 0"))
            self.log('info', 'Check that images are present in '
                     'the correct directory structure')
            # 4. Check that images are present in the correct directory
            #    structure
            for img in image_list1:
                self.assertEquals(self._rpm_or_image_available_on_ms(
                    img, project_subdir[0].split('/')[1] + '/' +
                    project_subdir[0].split('/')[2],
                    check_www=True,
                    filepart=project_subdir[0], is_img=True),
                    True)
            for img in image_list2:
                self.assertEquals(self._rpm_or_image_available_on_ms(
                    img, project_subdir[1].split('/')[1] + '/' +
                    project_subdir[0].split('/')[2],
                    check_www=True,
                    filepart=project_subdir[1], is_img=True),
                    True)
            for img in image_list3:
                self.assertEquals(self._rpm_or_image_available_on_ms(
                    img, project_subdir[2].split('/')[1] + '/' +
                    project_subdir[0].split('/')[2],
                    check_www=True,
                    filepart=project_subdir[2], is_img=True),
                    True)
            for img in image_list4:
                self.assertEquals(self._rpm_or_image_available_on_ms(
                    img, project_subdir[3].split('/')[1] + '/' +
                    project_subdir[0].split('/')[2],
                    check_www=True,
                    filepart=project_subdir[3], is_img=True),
                    True)

            self.log('info', 'Verify the checksum has been '
                     'created on destination')
            # 5. Verify the checksum has been created on destination
            for filename in file_paths:
                self.assertTrue(
                    self.remote_path_exists(self.ms_node, filename))
            self.log('info', 'Verify that the import handles directories with '
                     'all permissible characters, and import_iso successfully '
                     'overwrites a file that already existed '
                     'at the destination.')
            # 6. Verify that the import handles directories with all
            #    permissible characters
            for img in chars_list1:
                self.assertEquals(
                    self._rpm_or_image_available_on_ms(
                        uncommon_chars_dir1 + "/" + img,
                        remote_proj.split("/")[0],
                        check_www=True, filepart=remote_proj,
                        is_img=True), True)

            for img in chars_list2:
                self.assertEquals(
                    self._rpm_or_image_available_on_ms(
                        swedish_chars_dir1 + "/" + img,
                        remote_proj.split("/")[0],
                        check_www=True, filepart=remote_proj,
                        is_img=True), True)
            self.log('info', 'Verify that import_iso successfully overwrites a'
                     ' file that already existed at the destination')
            # 7. Verify that import_iso successfully
            #    overwrites a file that already existed
            #    at the destination
            modify_time = self.get_file_modify_time(self.ms_node,
                                                    test_constants.
                                                    VM_IMAGE_MS_DIR +
                                                    "imgproj/" +
                                                    "an_image.gcow2.md5")
            self.assertTrue(modify_time > create_time)

        finally:
            self._do_cleanup(files=['{0}/{1}'.format(
                             test_constants.PARENT_PKG_REPO_DIR,
                             project_subdir[0].split('/')[0])], restore=None)

            self._restore_repos(["images"])

    @attr('all', 'revert', 'story4060', 'story4060_tc03', 'bur_only_test')
    def test_03_n_import_compliant_dir_iso_validation(self):
        """
        @tms_id: litpcds_4060_tc03
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify when the "import iso" command fails
            then the litpd service will remain in maintenance mode.
        @tms_description: When the "import iso" command fails
            then the litpd service will remain in maintenance mode
            and a suitable error will be output to the logs
            If the litpd service has not entered maintenance mode,
            and the command, "import_iso" fails,
            the litpd service will return a suitable error response to
            the client
            When the "import_iso" command fails,
            the litpd service will remain in maintenance mode
            and a suitable error will be output to the logs
            If the checksum validation fails, then the import_iso command
            will fail
        @tms_test_steps:
            @step: Execute 'litp import_iso' on a directory that doesn't exist
            @result: An error is returned and litp is not in maintenance mode
            @step: Generate a rpm and image of size 0, copy the iso archive
                to MS and execute 'litp import_iso' on the directory
            @result: An error is returned and litp is not in maintenance mode
            @step: Copy empty iso to ms (only contain basic empty folders), and
                call 'litp import_iso' on a directory
            @result: An error is returned and puppet is enabled
            @step: Execute 'litp import_iso' on a directory where a checksum
                file doesn't 'match' the image
            @result: The system logs contain error and the status file
                indicates failure and litp is in maintenance mode
            @step: Execute 'litp import_iso' on a directory where a checksum
                 file has no corresponding image file
            @result: Validation error is generated, the system logs contain
                error, the litpd service is not in maintenance mode, and
                puppet is enabled
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        try:
            self.log('info', 'Execute "litp import_iso" on a directory that'
                     ' doesn\'t exist')
            # test_02_p_no_mmode_preliminary_validation_checks_fail
            # 1.Execute 'litp import_iso' on a directory that doesn't exist
            _, err, _ = self.execute_cli_import_iso_cmd(
                self.ms_node, "/tmp/no_such_dir", expect_positive=False)

            # 1a. Verify that an error is returned.
            expect_err = ('ValidationError    Source directory '
                          '"/tmp/no_such_dir" does not exist.')
            self.assertTrue(self.is_text_in_list(expect_err, err))

            # 1b.Verify that litp is not in maintenance mode.
            self.assertFalse(self._litp_in_mmode())
            self.log('info', 'Generate a rpm and image of size 0,'
                     ' copy the iso archive to MS and execute '
                     ' "litp import_iso" on the directory')
            # test_29_p_an_error_is_returned_if_files_are_zero_length
            # 2. Generate a rpm and image of size 0
            self._generate_random_file(
                iso_id='29', file_name="empty_rpm.rpm",
                local_folder="repos/rpm-proj", space="0")
            self._generate_random_file(
                iso_id='29', file_name="empty_image.gcow2",
                local_folder="images/proj", space="0")

            # 2a.Copy iso archive to MS
            self._mount_image(iso_id='29')
            # 2b. Execute 'litp import_iso' on the directory
            _, err, ret_code = self.execute_cli_import_iso_cmd(
                self.ms_node, "/tmp/story4060/iso_dir_29/", "", False)
            self.assertNotEqual(0, ret_code)
            self.assertNotEqual([], err)
            # 2c. Verify that an error is returned
            self.assertTrue(self.is_text_in_list("ValidationError", err))
            self.assertTrue(self.is_text_in_list("is of zero length", err))
            # 2d. Verify that litp is not in maintenance mode
            self.assertFalse(self._litp_in_mmode())
            self.log('info', 'Copy empty iso to ms (only contain basic '
                     'empty folders), and call "litp import_iso" on '
                     'a directory')
            # test_47_p_exception_if_iso_is_empty
            # 3. Copy empty iso to ms
            #  (only contain basic empty folders)
            iso_image_id = "47"
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id

            cmd = "mkdir -p /tmp/story4060/iso_dir_47/litp"
            self.run_command(self.ms_node, cmd)
            cmd = "mkdir -p /tmp/story4060/iso_dir_47/repos"
            self.run_command(self.ms_node, cmd)

            # 3a.Call 'litp import_iso' on a directory
            _, err, ret_code = self.execute_cli_import_iso_cmd(
                self.ms_node, iso_path, expect_positive=False)
            # 3b.Verify error
            self.assertNotEqual(ret_code, 0)
            expected_err = {
                            'url': '/litp/import-iso',
                            'msg': 'ValidationError    No LITP compliant ISO '
                            'to import',
                            }
            missing, extra = self.check_cli_errors([expected_err], err)
            self.assertEquals(missing, [])
            self.assertEquals(extra, [])
            # 3c.Verify puppet is enabled
            self.assertTrue(self.check_mco_puppet_is_enabled(self.ms_node))
            self.log('info', 'Execute "litp import_iso" on a directory '
                     'where a checksum file doesn\'t \'match\' the image')
            # test_13_p_chksum_doesnt_match
            # 4. Execute 'litp import_iso' on a directory where a checksum file
            #    doesn't 'match' the image
            iso_image_id = "13"
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id
            log_path = test_constants.GEN_SYSTEM_LOG_PATH
            log_len = self.get_file_len(self.ms_node, log_path)

            # 4a.Mount the ISO
            self._mount_image("13")
            # 4b.Execute 'litp import_iso' on the directory
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)
            # 4c.Wait for import command to fail
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished, '
                                                  'exiting with 1'))
            # 4d.Check the server logs contain error
            expected_msg = ('failed checksum test')
            self.assertTrue(self.wait_for_log_msg(self.ms_node, expected_msg,
                                                  timeout_sec=10,
                                                  log_len=log_len),
                            'expected error message not found in syslog')
            # 4e.Verify that the status file indicates failure and litp is
            # in maintenance mode
            exists, _, status = self._get_job_state()
            self.assertTrue(exists)
            self.assertEquals(status, 'Failed')
            self.assertTrue(self._litp_in_mmode())
            # 4f.Disable maintenance mode
            self._set_litp_mmode(False)
            self.log('info', 'Execute "litp import_iso" on a directory where '
                     'a checksum file has no corresponding image file')
            # test_14_p_chksum_file_exists_no_image_file
            # 5. Execute 'litp import_iso' on a directory where a checksum file
            #   has no corresponding image file
            iso_image_id = "14"
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id
            log_path = test_constants.GEN_SYSTEM_LOG_PATH
            log_len = self.get_file_len(self.ms_node, log_path)

            # 5a.Wait for import command to fail
            self._mount_image(iso_image_id)
            _, err, _ = self.execute_cli_import_iso_cmd(
                self.ms_node, iso_path, expect_positive=False)
            # 5b.Check the returned error is as expected
            md5_file = iso_path + "/images/ENM/idontmatch.qcow2.md5"
            img_file = iso_path + "/images/ENM/idontmatch.qcow2"
            expt_err = ('Checksum file "{0}" exists but image '
                        'file "{1}" does not'.format(md5_file, img_file))
            self.assertTrue(self.is_text_in_list(expt_err, err))
            # 5c.Check the server logs contain error
            expt_err = "ERROR: Failure: "
            self.assertTrue(self.wait_for_log_msg(self.ms_node, expt_err,
                                                  timeout_sec=10,
                                                  log_len=log_len),
                            'expected error message not found in syslog')
            # 5d.Check that the litpd service is not in maintenance mode
            self.assertFalse(self._litp_in_mmode())

            # 6. Verify puppet is enabled
            self.assertTrue(self.check_mco_puppet_is_enabled(self.ms_node))

        finally:
            # Ensure litp not in maintenance mode
            self._set_litp_mmode(False)

    @attr('all', 'revert', 'story4060', 'story4060_tc04', 'bur_only_test')
    def test_04_n_import_compliant_dir_iso_failure(self):
        """
        @tms_id: litpcds_4060_tc04
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that when the "import iso" command fails,
             the litpd service will remain in maintenance mode
        @tms_description: When the "import iso" command fails,
             the process terminates cleanly, and the litpd service will
              remain in maintenance mode, status file will be updated and a
               suitable error will be output to the logs
        @tms_test_steps:
            @step: Backup the  Litp repositories, generate an image of
                 1 and 10 MB, and copy iso image to ms
            @result: The backup is successful and the files are transfered.
            @step: Execute a set of commands which are causing
                 RPM cannot be copied(rsynched)
                    to the destination E.G. Fill Disk
            @result: The new filesystem is created and mounted
            @step: Call 'litp import_iso' on a directory and expect rsync
                 to fail
            @result: The command 'litp import_iso' fails.
            @step: Verify the status file exists as litp is in maintenance mode
            @result: The status is correct and litp is in maintenance mode
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        repos = ["3pp", "litp", "litp_plugins", "images"]
        fs_quota = "/var/www/quotafs"
        try:
            self.log('info', 'Backup the  Litp repositories, generate an '
                     'image of 1 and 10 MB, and copy iso image to ms')
            # 1. Backup the  Litp repositories
            self._backup_repos(repos)

            # 1. Generate an image of 1 and 10 MB
            self._generate_random_file(
                iso_id='25', file_name="a_small_image.gcow2",
                local_folder="images/imgproj", space="1048576")
            self._generate_random_file(
                iso_id='25', file_name="a_bigger_image.gcow2",
                local_folder="images/imgproj", space="10485760")

            # 2. Copy iso archive to ms
            self._mount_image(iso_id='25')
            self.log('info', 'Execute a set of commands which are causing'
                     ' RPM cannot be copied(rsynched) to the destination '
                     'E.G. Fill Disk')
            # 3. Ensure RPM cannot be copied(rsynched)
            #    to the destination E.G. Fill Disk
            allocate_cmds = ["/bin/mkdir -p {0}".format(fs_quota),
                             "cd /var/www/quotafs",
                             # Create fs and 10 MB quota for dst
                             # disk-quota.ext4 is a file of 20480 * 512 KB
                             "/bin/dd if=/dev/zero of=./disk-quota.ext4 " +
                             "count=20480",
                             # Which is transformed into a FS of 10 MB
                             "/sbin/mkfs -t ext4 -q disk-quota.ext4 -F",
                             "/bin/mount -o loop,rw,usrquota,grpquota " +
                             "disk-quota.ext4 {0}".format(
                                test_constants.PARENT_PKG_REPO_DIR),
                             "/usr/sbin/setenforce 0"]

            for cmd in allocate_cmds:
                _, err, ret_code = self.run_command(self.ms_node, cmd,
                                                    su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
            self.log('info', 'Call "litp import_iso" on a directory and expect'
                     ' rsync to fail')
            # 4. Call 'litp import_iso' on a directory and expect rsync
            #  to fail
            self.execute_cli_import_iso_cmd(self.ms_node,
                                            "/tmp/story4060/iso_dir_25/")

            # 5. Wait for the 'litp import_iso' command to fail
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 1'))
            self.log('info', 'Verify the status file exists as litp is in '
                     'maintenance mode')
            # 6. Verify the status file exists as litp is in maintanence mode
            fileexist, _, lockstate = self._get_job_state()
            self.assertEqual(True, fileexist)

            # 7. Verify that the status file indicates failure
            self.assertEqual('Failed', lockstate)

        finally:
            # 8. Remove FS
            cmd = "/bin/umount {0}".format(fs_quota)
            self.run_command(self.ms_node, cmd, su_root=True)

            cmd = "/bin/umount " + test_constants.PARENT_PKG_REPO_DIR
            self.run_command(self.ms_node, cmd, su_root=True)

            cmd = "/bin/rm -rf /var/www/quotafs"
            self.run_command(self.ms_node, cmd, su_root=True)

            # 9. Restore the original Litp repositories
            self._restore_repos(repos)

            # 10.Disable maintenance mode
            self._set_litp_mmode(False)

    @attr('all', 'revert', 'story4060', 'story4060_tc05', 'bur_only_test')
    def test_05_p_import_compliant_dir_iso_permissions(self):
        """
        @tms_id: litpcds_4060_tc05
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that importing ISO depending on file permissions.
        @tms_description: Tests for importing ISO depending on
             file permissions.
            Images will be imported with permissions in dst:
            755 for folders and 644 for files and
            import_iso succeeds even if md5
            files do not have read rights
        @tms_test_steps:
            @step: Copy iso archive to ms, change permits of *.md5 in src
                 folder to be accessible only from root, call 'litp import_iso'
                  on a directory
            @result: The import command succeed.
            @step: Copy iso archive to ms, change permits of *.md5 in src
                 folder to be read only, call 'litp import_iso'
                  on a directory
            @result: The import command succeed and the permissions are
                 644.
            @step: Change permits in dst folder to only read
               (exec perm should be added) and call 'litp import_iso'
            @result: The correct directory structure has been created
               with the correct permisisons.
            @step: Change permits in dst folder to only write (read
               and exec should be added) and call 'litp import_iso'
            @result: Verify images will be imported with permissions in dst:
                 755 for folders and 644 for files
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        try:
            # Test Attributes
            remote_proj = "images/imgproj"
            iso_id = '28'

            # 1. Backup the  Litp repositories
            self._backup_repos(["images"])

            # test_28_p_import_success_chksum_no_read_permissions
            # 2. Verify files are imported even if md5 files don't
            #    have read permissions
            # 2a.Copy iso archive to ms
            self._mount_image(iso_id)
            self.log('info', 'Copy iso archive to ms, change permits of '
                     '*.md5 in src folder to be accessible only from root, '
                     ' call "litp import_iso" on a directory')
            # 2b.Change permits of *.md5 in src folder to only read
            cmd = "/bin/chmod 000 /tmp/story4060/iso_dir_28/images/imgproj/" +\
                  "*.md5"
            _, err, ret_code = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 2c.Call 'litp import_iso' on a directory and verify it passes
            #    Will import files even if md5 files don't have read perms
            _, err, ret_code = self.execute_cli_import_iso_cmd(self.ms_node,
                                                               '/tmp/story4060'
                                                               '/iso_dir_28/')
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 0'))
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.log('info', 'Copy iso archive to ms, change permits of *.md5 '
                     'in src folder to be read only, call "litp import_iso" '
                     'on a directory')
            # test_22_p_import_modify_permissions_to_min
            # 3. Verify imported files have permissions changed to be 644
            # 3a.Copy another iso archive to ms
            iso_id = '22'
            self._mount_image(iso_id=iso_id)

            # 3b.Change permits in src files to only write
            cmd = "/bin/chmod 111 /tmp/story4060/iso_dir_22/images/" +\
                "imgproj/an_image.gcow2"
            _, err, ret_code = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            cmd = "/bin/chmod 555 /tmp/story4060/iso_dir_22/images/" +\
                "imgproj/another_image.gcow2"
            _, err, ret_code = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 3c.Call 'litp import_iso' on a directory and verify it passes
            _, err, ret_code = self.execute_cli_import_iso_cmd(
                  self.ms_node, "/tmp/story4060/iso_dir_22/")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 0'))
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 3d. Check imported Files will have permissions changed to be 644
            cmd = '/usr/bin/stat -c "%a %n" ' +\
                  test_constants.VM_IMAGE_MS_DIR +\
                  'imgproj/an_image.gcow2 | /bin/awk {\'print $(1)\'}'
            out, _, ret_code = self.run_command(self.ms_node, cmd)
            self.assertNotEqual(out[0], "111")
            self.assertEqual(out[0], "644")
            cmd = '/usr/bin/stat -c "%a %n" ' +\
                  test_constants.VM_IMAGE_MS_DIR +\
                  'imgproj/another_image.gcow2 | /bin/awk {\'print $(1)\'}'
            out, _, ret_code = self.run_command(self.ms_node, cmd)
            self.assertNotEqual(out[0], "555")
            self.assertEqual(out[0], "644")
            self.log('info', 'Change permits in dst folder to only read'
                     '(exec perm should be added) and call "litp import_iso"')
            # test_23_p_import_modify_perms_to_a_min_on_dst_folders
            # 4. Verify that destination folders to be rsynced
            #    (Existing or newly created) will have their permissions
            #    modified to a minimum to make them available to the apache
            #    server
            # 4a.Change permits in dst folder to only read
            # (exec perm should be added)
            cmd = "/bin/chmod 444 " + test_constants.VM_IMAGE_MS_DIR
            _, err, ret_code = self.run_command(self.ms_node, cmd,
                                                su_root=True)
            self.assertEqual(ret_code, 0)

            self._mount_image(iso_id)

            # 4b.Call 'litp import_iso' on a directory and verify it passes
            _, err, ret_code = self.execute_cli_import_iso_cmd(self.ms_node,
                                                               '/tmp/story406'
                                                               '0/iso_dir_22/')
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 0'))
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 4c.Check that the correct directory structure has been created
            #    with the correct permisisons
            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       " | /bin/awk {'print $(1)'} | /bin/sed -n '2 p'"
            out, _, _ = self.run_command(self.ms_node, cmdperms, su_root=True)
            self.assertEqual("dr--r--r--.", out[0])

            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       "imgproj | /bin/awk {'print $(1)'} | /bin/sed -n '2 p'"
            out, _, _ = self.run_command(self.ms_node, cmdperms, su_root=True)
            self.assertEqual("drwxr-xr-x.", out[0])

            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       "imgproj/an_image.gcow2 " +\
                       "| /bin/awk {'print $(1)'} | /bin/sed -n '1 p'"
            out, _, _ = self.run_command(self.ms_node, cmdperms, su_root=True)
            self.assertEqual("-rw-r--r--.", out[0])

            self._do_cleanup(files=['{0}/{1}'.format(
                test_constants.PARENT_PKG_REPO_DIR,
                remote_proj)], restore=None)
            self.log('info', 'Change permits in dst folder to only write'
                     '(read and exec should be added) and call '
                     '"litp import_iso"')
            # 4d.Change permits in dst folder to only write (read
            #    and exec should be added)
            cmd = "/bin/chmod 222 " + test_constants.VM_IMAGE_MS_DIR
            _, err, ret_code = self.run_command(self.ms_node, cmd,
                                                su_root=True)
            self.assertEqual(ret_code, 0)

            # 4e.Mount again
            self._mount_image(iso_id)

            # 4f.Call 'litp import_iso' on a directory and verify it passes
            _, err, ret_code = self.execute_cli_import_iso_cmd(
                self.ms_node, "/tmp/story4060/iso_dir_22/")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished, '
                                                  'exiting with 0'))
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            # 4g.Verify images will be imported with permissions in dst:
            #    755 for folders and 644 for files
            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       " | /bin/awk {'print $(1)'} | /bin/sed -n '2 p'"
            out, _, _ = self.run_command(
                self.ms_node, cmdperms, su_root=True)
            self.assertEqual("d-w--w--w-.", out[0])

            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       "imgproj | /bin/awk {'print $(1)'} | /bin/sed -n '2 p'"
            out, _, _ = self.run_command(
                self.ms_node, cmdperms, su_root=True)
            self.assertEqual("drwxr-xr-x.", out[0])

            cmdperms = "/bin/ls -alF " + test_constants.VM_IMAGE_MS_DIR +\
                       "imgproj/an_image.gcow2 " +\
                       "| /bin/awk {'print $(1)'} | /bin/sed -n '1 p'"
            out, _, _ = self.run_command(
                self.ms_node, cmdperms, su_root=True)
            self.assertEqual("-rw-r--r--.", out[0])

        finally:
            # 5. Restore LITP Repositories
            self._restore_repos(["images"])

    @attr('all', 'revert', 'story4060', 'story4060_tc33', 'bur_only_test')
    def test_33_p_the_import_succeeds_for_very_long_filenames(self):
        """
        @tms_id: litpcds_4060_tc33
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify import ISO with long filenames.
        @tms_description: This test will verify that the import succeeds
            for very long filenames.
        @tms_test_steps:
            @step: Call 'litp import_iso' on a directory
            @result: The import command succeed.
        @tms_test_precondition: Generate long name image (255 characters,
                max. length allowed in linux) and copy it to ms.
        @tms_execution_type: Automated
        """
        try:
            # 1. Backup the  Litp repositories
            self._backup_repos(["images"])
            self.log('info', 'Generate long name image (255 characters,'
                     'max. length allowed in linux) and copy it to ms.')
            # 2. Generate long name image (255 characters, max. length allowed
            #    in linux)
            longname = "1234567890" * 24 + "12345.gcow2"
            # The image generated will have 255 characters in its name
            self._generate_random_file(iso_id='33', file_name=longname,
                                       local_folder="images/img-proj",
                                       space="4096")

            # 3. Copy iso archive to ms
            self._mount_image(iso_id='33')
            self.log('info', 'Call "litp import_iso" on a directory')
            # 4. Call 'litp import_iso' on a directory.
            _, err, ret_code = self.execute_cli_import_iso_cmd(
             self.ms_node, "/tmp/story4060/iso_dir_33")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 0'))
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

        finally:
            # 5. Restore the  Litp repositories
            self._restore_repos(["images"])

    @attr('all', 'revert', 'story4060', 'story4060_tc40', 'bur_only_test')
    def test_40_p_empty_project_directories_still_generate_a_new_repo(self):
        """
        @tms_id: litpcds_4060_tc40
        @tms_requirements_id: LITPCDS-4060, TORF-107192, TORF-119350
        @tms_title: Verify a new repo is generated from an empty project.
        @tms_description: This test will verify that empty project directories
            still generate a new repo.
            Also verify story TORF-107192
            (test_06_p_import_iso_metrics_collection)
        @tms_test_steps:
            @step: Backup the  Litp repositories
            @result: The backup is successful.
            @step: Copy empty iso archive to ms
               (only contain litp compliant empty folders)
            @result: Needed folder structure is created
            @step: Call 'litp import_iso' on a directory.
            @result: The import succeeded
            @step: Verify folders were created even when empty
            @result: The folder structure is correct
            @step: Check metrics messages and metrics values
            @result: Expected metrics are present with correct values (type)
            @step: Restore the LITP repositories
            @result: The repositories are restored
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        repos = ["litp", "litp_plugins", "images"]
        metrics_file_path = '/var/log/litp/metrics.log'
        metrics_file_path_1 = '/var/log/litp/metrics.log.1'

        try:
            self.log('info', 'Backup the  Litp repositories')
            # 1. Backup the  Litp repositories
            self._backup_repos(repos)
            self.log('info', 'Copy empty iso archive to ms'
                     ' only contain litp compliant empty folders')
            # 2. Copy empty iso archive to ms
            #  (only contain litp compliant empty folders)
            cmd = "/bin/mkdir -p /tmp/story4060/iso_dir_40/images" +\
                "/imgproject/imgsubproj"
            _, _, ret_code = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, ret_code)
            cmd = "/bin/mkdir -p /tmp/story4060/iso_dir_40/repos" +\
                "/project/subproject"
            _, _, ret_code = self.run_command(self.ms_node, cmd)
            self.assertEqual(0, ret_code)
            self.log('info', 'Call \'litp import_iso\' on a directory.')
            # 3. Call 'litp import_iso' on a directory.
            # Changes to litp import_iso for TORF-528266 will add suffix
            # _rhel7 to new folders in /var/www/html/
            # Hence project_rhel7 and project_subproject_rhel7
            cursor_metrics = self.get_file_len(self.ms_node, metrics_file_path)
            self.execute_cli_import_iso_cmd(
                self.ms_node, "/tmp/story4060/iso_dir_40/")

            self.assertTrue(self.
                            wait_for_log_msg(self.ms_node,
                                             "ISO Importer is finished, "
                                             "exiting with 0"))

            self.log('info', 'Verify folders were created even when empty')
            # 4. Verify folders were created even when empty
            dir_paths = [test_constants.LITP_PKG_REPO_DIR,
                         test_constants.PP_PKG_REPO_DIR,
                         test_constants.PARENT_PKG_REPO_DIR + "litp_plugins",
                         test_constants.PARENT_PKG_REPO_DIR + "project_rhel7",
                         test_constants.PARENT_PKG_REPO_DIR +
                         "project_subproject_rhel7",
                         test_constants.VM_IMAGE_MS_DIR + "imgproject",
                         test_constants.VM_IMAGE_MS_DIR +
                         "imgproject/imgsubproj"]

            for path in dir_paths:
                cmd = "/bin/ls " + path
                _, err, ret_code = self.run_command(
                    self.ms_node, cmd, su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)

            self.log('info', 'Check "import_iso" metrics')
            lines = self.wait_for_log_msg(self.ms_node,
                                          'ISO',
                                          log_file=metrics_file_path,
                                          timeout_sec=10,
                                          log_len=cursor_metrics,
                                          rotated_log=metrics_file_path_1,
                                          return_log_msgs=True)

            actual_metrics = {}
            for line in lines:
                parts = line.split('=')
                actual_metrics[parts[0]] = parts[1]

            expected_metrics = {
               '[ISO][Import][DisablePuppet].TimeTaken': float,
               '[ISO][Import][ImageRsync].TimeTaken': float,
               '[ISO][Import][YumDiscardMetadata].TimeTaken': float,
               '[ISO][Import][YumUpgrade].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMS].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMNs].TimeTaken': float,
               '[ISO][Import][RestartLITPD].TimeTaken': float,
               '[ISO][Import].TimeTaken': float,
               '[ISO][Import][RepoRsync][project_rhel7].TimeTaken': float,
               '[ISO][Import][RepoRsync][project_subproject_rhel7].TimeTaken':
               float,
               '[ISO][Import][CreateRepo][project_rhel7].TimeTaken': float,
               '[ISO][Import][CreateRepo][project_subproject_rhel7].TimeTaken':
               float
            }

            for exp_key, exp_type in expected_metrics.iteritems():
                for act_key, act_val in actual_metrics.iteritems():
                    if act_key.endswith(exp_key):
                        try:
                            act_val = exp_type(act_val)
                        except ValueError:
                            act_val = None
                        self.assertNotEqual(None, act_val,
                                            'Wrong value type for'
                                            ' metric "{0}"'.
                                            format(exp_key))
                        break
                else:
                    self.fail('Metrics not found for "{0}"'.format(exp_key))

        finally:
            self.log('info', 'Restore the LITP repositories')
            # 5. Restore the LITP repositories
            self._do_cleanup(files=[
                '{0}/{1}'.format(test_constants.PARENT_PKG_REPO_DIR,
                                 "project_rhel7"),
                '{0}/{1}'.format(test_constants.PARENT_PKG_REPO_DIR,
                                 "project_subproject_rhel7"),
                '{0}/{1}'.format(test_constants.VM_IMAGE_MS_DIR,
                                 "imgproject")],
                             restore=None)

            self._restore_repos(repos)

    @attr('all', 'revert', 'story4060', 'story4060_tc42', 'bur_only_test')
    def test_42_p_litp_plugins_repository_is_enforced_by_puppet(self):
        """
        @tms_id: litpcds_4060_tc42
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify litp_plugins repository is controlled by
            puppet.
        @tms_description: This test will verify that the litp_plugins
            repository is enforced by puppet.
        @tms_test_steps:
            @step: Delete the yum repositories on the MS
            @result: The repositories are deleted.
            @step: Run mco command to puppet reload manifests.
            @result: The manifests are reloaded.
            @step: Check if the repositories are recreated by puppet on MS.
            @result: The litp_plugins repository is enforced by puppet.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        try:
            self.log('info', 'Delete the yum repositories on the MS')
            # 1. Delete the yum repos on MS
            repo_name = 'LITP_PLUGINS.repo'
            cmd = "/bin/mkdir -p /tmp/tmp4060/"
            _, err, ret_code = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)

            cmd = "/bin/mv /etc/yum.repos.d/{0} /tmp/tmp4060".format(repo_name)
            _, err, ret_code = self.run_command(
                self.ms_node, cmd, su_root=True)
            self.assertEqual(0, ret_code)
            self.assertEqual([], err)
            self.log('info', 'Run mco command to puppet reload manifests.')
            # 2. Kick puppet
            mco_cmd = self.cli.get_mco_cmd("puppet runall 10")
            out, err, ret_code = self.run_mco_command(self.ms_node, mco_cmd)
            self.assertTrue((ret_code == 0), "Command failed")
            self.assertEqual([], err)
            self.assertTrue(self.is_text_in_list("Running", out),
                            "Unexpected mco puppet kick response")
            self.log('info', 'Check if the repositories are recreated by '
                     'puppet on MS.')
            # 3. Check that the repositories are recreated by puppet on MS
            pp_interval = self.get_puppet_interval(self.ms_node)
            self.assertTrue(isinstance(pp_interval, int))
            poll_loops = int(((pp_interval * 2) / 10))
            ms_repos_reset = False
            for _ in range(poll_loops):
                out, err, ret_code = self.run_command(self.ms_node,
                                                      "yum repolist",
                                                      su_root=True)
                self.assertEqual(0, ret_code)
                self.assertEqual([], err)
                if self.is_text_in_list("LITP_PLUGINS", out):
                    ms_repos_reset = True
                    break
                sleep(10)
            self.assertTrue(ms_repos_reset, ("Repos haven't been "
                            "enforced in 6 mins on MS"))
        finally:
            self._do_cleanup(files=['/etc/yum.repos.d/LITP_PLUGINS.repo'],
                             restore=[('/tmp/tmp4060/LITP_PLUGINS.repo',
                                       '/etc/yum.repos.d/LITP_PLUGINS.repo')])

    @attr('all', 'revert', 'story4060', 'story4060_tc45', 'bur_only_test')
    def test_45_p_mmode_no_status_file_litpd_restart(self):
        """
        @tms_id: litpcds_4060_tc45
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify Litp remains in maintenance mode even without
            present status file.
        @tms_description: This test will verify that if litp is in maintenance
             mode and there is no 'status' file, and litpd restarts it
              stays in maintenance mode.
        @tms_test_steps:
            @step: Remove the file that holds import_iso job state.
            @result: The file is removed.
            @step: Put Litp in maintenance mode and restart Litp
            @result: Litp is in maintenance mode
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        try:
            self.log('info', 'Remove the file that holds import_iso '
                     'job state.')
            # 1. Remove state file
            self._remove_state_file()
            self.log('info', 'Put Litp in maintenance mode and restart Litp')
            # 2. Put Litp in maintenance mode
            self._set_litp_mmode(True)
            self.assertTrue(self._litp_in_mmode())

            # 3. Restart Litp
            # If we try to enable debug on startup it will fail, as we
            # are in maintenance mode.
            self.restart_litpd_service(self.ms_node, debug_on=False)

            # 4. Verify litp is in maintenance mode
            self.assertTrue(self._litp_in_mmode())

        finally:
            # Disable Maintenance Mode
            self._set_litp_mmode(False)

            # Enable debug
            prop_val = "enabled=false"
            url = "/litp/logging"
            update_cmd = self.cli.get_update_cmd(url, prop_val)
            self.run_command(self.ms_node, update_cmd)

    @attr('all', 'revert', 'story4060', 'story4060_tc46', 'bur_only_test')
    def test_46_p_mmode_litpd_restarted_state_running(self):
        """
        @tms_id: litpcds_4060_tc46
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify Litp is still in maintenance mode when is restarted
            with "state == running".
        @tms_description:
            This test will verify that if litp is in maintemance mode and litpd
            is restarted and the 'state = running' it stays in maintenance
            mode.
        @tms_test_steps:
            @step: Put Litp in maintenance mode
            @result: Litp is in maintenance mode.
            @step: Write state file with 'Running' set and restart Litp
            @result: Litp is still in maintenance mode
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        try:
            self.log('info', 'Put Litp in maintenance mode and restart Litp')
            # 1. Put Litp in maintenance mode
            self._set_litp_mmode(True)
            self.log('info', 'Write state file with "Running"'
                     ' set and restart Litp')
            # 2. Write state file with 'Running' set
            self._write_state_file(1, 'Running')

            # Verify litp is in maintenance mode
            self.assertTrue(self._litp_in_mmode())

            # 3. Restart Litp
            # If we try to enable debug on startup it will fail, as we
            # are in maintenance mode.
            self.restart_litpd_service(self.ms_node, debug_on=False)

            # 4. Verify litp is in maintenance mode
            self.assertTrue(self._litp_in_mmode())
        finally:
            # Disable Maintenance Mode
            self._set_litp_mmode(False)

            # Enable debug
            prop_val = "enabled=false"
            url = "/litp/logging"
            update_cmd = self.cli.get_update_cmd(url, prop_val)
            self.run_command(self.ms_node, update_cmd)

    @attr('all', 'revert', 'story4060', 'story4060_tc50', 'bur_only_test')
    def test_50_p_import_iso_completes_if_litpd_restarted(self):
        """
        @tms_id: litpcds_4060_tc50
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that the import_iso plan completes if
            litpd process is restarted
        @tms_description:
            This test will verify that the import_iso plan completes if
            litpd process is restarted.
        @tms_test_steps:
            @step: Mount image with RPMs to be imported and call
                 'litp import_iso' on a directory.
            @result: import_iso process is started.
            @step: Restart Litp during import_iso
            @result: Litp is still in maintenance mode and import_iso
                 is completed successfully
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        try:
            iso_image_id = "50"
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id
            self.log("info", "# 1. Backup of repos to be modified.")
            self._backup_repos(["litp_plugins"])
            self.log('info', 'Mount image with RPMs to be imported and call'
                     ' "litp import_iso" on a directory.')
            self.log("info", "# 2. Mount image with RPMs to be imported.")
            self._mount_image(iso_image_id)
            rpms_to_import = ["updatestestpkg-1.0-1.x86_64.rpm"]
            litp_plugins_repo = test_constants.OS_UPDATES_PATH_RHEL7
            self._import_rpms(rpms_to_import, repo=litp_plugins_repo)
            rpms_to_import = ["ostestpkg-1.0-1.x86_64.rpm"]
            litp_plugins_repo = '{0}Packages'.format(
                        test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7)
            self._import_rpms(rpms_to_import, repo=litp_plugins_repo)
            self.log("info", "# 3. Call 'litp import_iso' on a directory.")
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)
            self.log('info', 'Restart Litp during import_iso')
            self.log("info", "# 4. Verify maintenance mode after restart.")
            self.assertTrue(self._litp_in_mmode_after_restart())
            self.log("info", "# 5. Verify import_iso completed successfully.")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  'ISO Importer is finished,'
                                                  ' exiting with 0'))

        finally:
            self.log('info', '# 6. Force leave maintenance and remove pid '
                     'file.')
            self._set_litp_mmode(False)
            if os.path.exists(test_constants.LITP_MAINT_STATE_FILE):
                self.assertTrue(self._remove_state_file(),
                                "Error removing pid file")
            self.log("info", "# 7. Restore repo backups.")
            self._restore_repos(["litp_plugins"])
            test_pkgs = ["litptestpkg",
                         "3pptestpkg"]
            self._uninstall_packages([self.ms_node], test_pkgs)
            self._verify_test_pkgs_removed([self.ms_node], test_pkgs)
            self._cleanup_repos([],
                                ["updatestestpkg-1.0-1.x86_64.rpm"],
                                test_constants.OS_UPDATES_PATH_RHEL7,
                                nodeps=True)
            self._cleanup_repos([], ["ostestpkg-1.0-1.x86_64.rpm"],
                    '{0}Packages'.format(
                        test_constants.LITP_DEFAULT_OS_PROFILE_PATH_RHEL7),
                        nodeps=True)
            self._cleanup_repos([],
                                ["3pptestpkg-1.0-1.x86_64.rpm"],
                                test_constants.PP_PKG_REPO_DIR,
                                nodeps=True)

    @attr('all', 'revert', 'story4060', 'story4060_tc51', 'bur_only_test')
    def test_51_n_import_iso_fails_if_yum_throws_exception(self):
        """
        @tms_id: litpcds_4060_tc51
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that  the import_iso plan fails if yum has
            missing dependencies.
        @tms_description: This test will verify that  the import_iso plan
            fails if yum has missing dependencies.
            NOTE: The package litptestpkg requires two packages that are not
            available on the system
            Also verify story TORF-107192
            (test_07_n_import_iso_failed_metrics_collection)
        @tms_test_steps:
            @step: Backup the  Litp repositories
            @result: The backup is successful.
            @step: Mount image with RPMs to be imported,
                and start auditing puppet lockfiles.
            @result: The image is mounted, and puppet time is
                specified.
            @step: Call 'litp import_iso' on a directory.
            @result: The expected error message is present
            @step: Check puppet is disabled
            @result: puppet is disabled
            @step: Check maintenance item properties after
                "litp import_iso"
            @result: The mainenance is enabled and the status is Failed
            @step: Check metrics messages and metrics values
            @result: Only expected metrics are present with
                correct values (type):
               '[ISO][Import][DisablePuppet].TimeTaken': float,
               '[ISO][Import][ImageRsync].TimeTaken': float,
               '[ISO][Import][YumDiscardMetadata].TimeTaken': float,
               '[ISO][Import][YumUpgrade].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMS].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMNs].TimeTaken': float,
               '[ISO][Import][RestartLITPD].TimeTaken': float,
               '[ISO][Import].TimeTaken': float
            @step: Restore repo backups.
            @result: The repository is restored
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        metrics_file_path = '/var/log/litp/metrics.log'
        metrics_file_path_1 = '/var/log/litp/metrics.log.1'
        file_action = "CREATE"
        try:
            iso_image_id = "51"
            iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id

            self.log("info", "# 1. Backup of repos to be modified.")
            self._backup_repos(["litp_plugins"])

            self.log("info", "# 2. Mount image with RPMs to be imported.")
            self._mount_image(iso_image_id)

            self.log("info", "# 3. start auditing puppet lockfiles")
            start_times = self._set_auditctl_rules(self.all_nodes,
                                                   self.puppet_agent_lock_file,
                                                   "war",
                                                   self.audit_key)

            self.log("info", "# 4. Call 'litp import_iso' on directory.")
            cursor_metrics = self.get_file_len(self.ms_node, metrics_file_path)
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)

            self.log("info", "# 5. Verify error messages appear.")
            self.assertTrue(
                self.wait_for_log_msg(self.ms_node,
                                      [
                                       "ERROR: import_iso encountered a"
                                       " yum dependency error.",
                                       ["3pptestpkg-1.0-1.x86_64 requires"
                                       " ostestpkg",
                                       "3pptestpkg-1.0-1.x86_64 requires"
                                       " updatestestpkg"],
                                       "INFO: ISO Importer is finished,"
                                       " exiting with 1"
                                       ]))

            self.log("info",
                     "# 6. Check if puppet was disabled in the mean time")
            for node in self.all_nodes:
                found = self.check_for_audit_message(node, self.audit_key,
                                                     file_action,
                                                     start_times[node], "now")
                self.assertEqual(found, True)

            self.log("info", "# 7. Check puppet is disabled")
            for node in self.all_nodes:
                self.assertTrue(self.
                                remote_path_exists(node,
                                                   self.
                                                   puppet_agent_lock_file,
                                                   su_root=True))

            self.log("info", "# 8. Check maintenance item properties after"
                     "import_iso")
            self._check_maintenance_properties(enabled="true",
                                               initiator="import_iso",
                                               status="Failed")

            self.assertFalse(self.check_pkgs_installed(self.ms_node,
                                                       ["testpackage-1.1-1"
                                                        ".el6.x86_64"]))

            self.log('info', 'Check "import_iso" metrics')
            lines = self.wait_for_log_msg(self.ms_node,
                                          'ISO',
                                          log_file=metrics_file_path,
                                          timeout_sec=10,
                                          log_len=cursor_metrics,
                                          rotated_log=metrics_file_path_1,
                                          return_log_msgs=True)

            actual_metrics = {}
            for line in lines:
                parts = line.split('=')
                actual_metrics[parts[0]] = parts[1]

            expected_metrics = {
               '[ISO][Import][DisablePuppet].TimeTaken': float,
               '[ISO][Import][ImageRsync].TimeTaken': float,
               '[ISO][Import][YumDiscardMetadata].TimeTaken': float,
               '[ISO][Import][YumUpgrade].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMS].TimeTaken': float,
               '[ISO][Import][RunPuppetOnMNs].TimeTaken': float,
               '[ISO][Import][RestartLITPD].TimeTaken': float,
               '[ISO][Import].TimeTaken': float
            }

            for exp_key, exp_type in expected_metrics.iteritems():
                for act_key, act_val in actual_metrics.iteritems():
                    if act_key.endswith(exp_key):
                        try:
                            act_val = exp_type(act_val)
                        except ValueError:
                            act_val = None
                        self.assertNotEqual(None, act_val,
                                            'Wrong value type '
                                            'for metric "{0}"'.
                                            format(exp_key))
                        break
                else:
                    if exp_key not in [
                                    '[ISO][Import][RunPuppetOnMS].TimeTaken',
                                    '[ISO][Import][RunPuppetOnMNs].TimeTaken',
                                    '[ISO][Import][ImageRsync].TimeTaken']:
                        self.fail('Metrics not found for "{0}"'.
                                  format(exp_key))

        finally:
            self._set_litp_mmode(False)
            self._remove_auditctl_rules(self.all_nodes,
                                        self.puppet_agent_lock_file,
                                        "war",
                                        self.audit_key)
            self.log("info", "# 9. Restore repo backups.")
            self._restore_repos(["litp_plugins"])

    @attr('all', 'revert', 'story4060', 'story4060_tc52', 'bur_only_test')
    def test_52_n_verify_yum_lock_is_recognized_by_import_iso(self):
        """
        @tms_id: litpcds_4060_tc52
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that the import_iso plan fails if
             cannot get the yum lock
        @tms_description:
            This test verifies that if import_iso cannot get the yum lock no
            packages are installed and import_iso fails
        @tms_test_steps:
            @step: Mount an ISO and modify yum to run once and then lock
            @result: The ISO is mounted and yum is locked.
            @step: Call 'litp import_iso' on a directory.
            @result: import_iso process is started.
            @step: Wait for lock log message and check the test packages are
                 installed.
            @result: The yum exception is caught in import_iso and
                 the packages were not installed.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """
        # Packages that will be installed during this test
        test_pkgs = ["ERIClitpmntestpackage", "testpackage", "world"]

        # ISO to be imported
        iso_image_id = "52"
        iso_path = self.iso_remote_path + "iso_dir_" + iso_image_id

        try:
            self.log('info', 'Mount an ISO and modify yum to run '
                     'once and then lock')
            self.log("info", "# 1. Backup the  Litp repositories.")
            self._backup_repos(["litp_plugins"])

            self.log("info", "# 2. Mount an ISO")
            self._mount_image(iso_image_id)

            self.log("info", "# 3. Modify yum to run once and then lock")
            self._run_yum_once_and_then_lock()

            self.log("info", "# 4. Call 'litp import_iso' on a directory.")
            self.execute_cli_import_iso_cmd(self.ms_node, iso_path)

            self.log('info', 'Wait for lock log message and check the test '
                     'packages are installed.')
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                                  ['import_iso failed. '
                                                   'Could not get yum lock '
                                                   'after 60 seconds',
                                                   'INFO: ISO Importer is '
                                                   'finished, exiting with 1']
                                                  ))
            self.log("info", "# 6. Verify packages were not installed")
            for pkg in test_pkgs:
                self.assertFalse(self.check_pkgs_installed(self.ms_node,
                                                           [pkg]))

        finally:
            self.log("info", "# 7. Revert yum changes")
            self._fix_yum()

            # make sure import_iso is done
            counter = 0
            maint_status = self.get_props_from_url(self.ms_node,
                                                   '/litp/maintenance',
                                                   filter_prop="status")
            while maint_status == "Running" and counter < 600:
                sleep(10)
                counter += 10

            self.log("info", "# 8. Uninstall test packages")
            self._uninstall_packages([self.ms_node], test_pkgs)
            # Verify test packages are not on the nodes.
            self._verify_test_pkgs_removed([self.ms_node], test_pkgs)
            self._set_litp_mmode(False)

            self.log("info", "# 9. Restore the original Litp repositories.")
            self._restore_repos(["litp_plugins"])

    @attr('all', 'revert', 'story4060', 'story4060_tc53', 'bur_only_test')
    def test_53_p_maintenance_status_when_changed_manually(self):
        """
        @tms_id: litpcds_4060_tc53
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify 'initiator' property behavior from maintenance mode.
        @tms_description:
            Verify that when user sets manually the maintenance mode to
            'true', the 'initiator' property should be 'user'. And when
            it is set to 'false' the value should keep being 'user'. 'status'
            property should not change.
        @tms_test_steps:
            @step: Set maintenance mode manually and check 'status' and
                 'initiator' properties.
            @result: When maintenance mode is either "true" or "false", the
                 "initiator" property is "user", and "status" property
                  will remains the same as before.
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        maintenance_props = self.get_props_from_url(self.ms_node,
                                                    self.maintenance_url)
        try:
            for enabled in [True, False]:
                self.log('info', 'Set maintenance mode manually and check '
                         '"status" and "initiator" properties.')
                self._set_litp_mmode(enabled)

                self.log("info", "# 2. Check maintenance item properties")
                self._check_maintenance_properties(
                                            enabled=str(enabled).lower(),
                                            initiator="user",
                                            status=maintenance_props['status'])

        finally:
            self._set_litp_mmode(False)

    @attr('all', 'revert', 'story4060', 'story4060_tc54', 'bur_only_test')
    def test_54_p_maintenance_properties_not_updatable(self):
        """
        @tms_id: litpcds_4060_tc54
        @tms_requirements_id: LITPCDS-4060
        @tms_title: Verify that maintenance properties 'status' and
             'initiator' are not updatable
        @tms_description:
            Verify that maintenance properties 'status' and 'initiator' are
            not updatable
        @tms_test_steps:
            @step: Set maintenance mode manually and check 'status' and
                 'initiator' properties.
            @result: The properties are read only
        @tms_test_precondition: NA
        @tms_execution_type: Automated
        """

        for prop in ['status', 'initiator']:
            self._update_maintenance_property(prop,
                                              'story8999_10525_tc04',
                                              assert_success=False)
