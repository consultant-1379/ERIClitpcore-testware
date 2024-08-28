"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     Feb 2016
@author:    Roman Jarzebiak
@summary:   TORF-138482
            As an ENM User I want to modify the instructions for a
            Management Server Restore to replace instructions to
            restore LAST_KNOWN_CONFIG with the LITP DB
"""
from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
from redhat_cmd_utils import RHCmdUtils
import test_constants as const
import re
import os
from vcs_utils import VCSUtils


class Story138482(GenericTest):
    """
    As an ENM User I want to modify the instructions for a
    Management Server Restore to replace instructions to
    restore LAST_KNOWN_CONFIG with the LITP DB
    """

    def setUp(self):
        """ Setup variables for every test """
        super(Story138482, self).setUp()
        self.ms1 = self.get_management_node_filename()
        self.mns = self.get_managed_node_filenames()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()
        self.vcs = VCSUtils()
        self.backup_script = const.LITP_BACKUP_SCRIPT
        self.restore_script = const.LITP_RESTORE_SCRIPT
        self.backup_dir = "/tmp/litp_backup/"
        self.timeout_mins = 10
        # Get software-items
        self.items_path = self.find(
            self.ms1, "/software", "collection-of-software-item")[0]
        # Get items in ms
        self.ms_sw_items_url = self.find(
            self.ms1, "/ms", "ref-collection-of-software-item")[0]

        self.cmd_puppet_enable = "/usr/bin/puppet agent --enable"
        self.cmd_puppet_disable = "/usr/bin/puppet agent --disable"

    def tearDown(self):
        """ Runs for every test """
        super(Story138482, self).tearDown()

    def verify_file_name(self, backup_file):
        """ Verify name for backup file """
        pattern = re.compile(r'^litp_backup_\d{14}$')
        self.assertNotEqual(None, pattern.match(backup_file))

    def create_package_item(self, package="nano", wait_for_plan=True):
        """ Add a package item in the model """
        # Create a package item
        self.execute_cli_create_cmd(
            self.ms1, "{0}/{1}".format(self.items_path, package),
            'package', props="name={0}".format(package))
        # Inherit the item in the ms
        self.execute_cli_inherit_cmd(
            self.ms1, "{0}/{1}".format(self.ms_sw_items_url, package),
            "{0}/{1}".format(self.items_path, package))
        if wait_for_plan:
            # Create and run plan
            self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                    self.timeout_mins)

    def remove_package_item(self, package="nano", wait_for_plan=True):
        """ Remove package item from the model """
        self.execute_cli_remove_cmd(
            self.ms1, "{0}/{1}".format(self.items_path, package))

        if wait_for_plan:
            # Create and run plan
            self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                    self.timeout_mins)

    def run_plan(self, package="nano", wait_for_plan=True):
        """ Create and remove items from model """
        cmd = self.cli.get_show_cmd("{0}/{1}".format(self.items_path, package))

        _, err, _ = self.run_command(self.ms1, cmd)

        if self.is_text_in_list("InvalidLocationError    Not found", err):
            self.create_package_item(package, wait_for_plan)
        else:
            self.remove_package_item(package, wait_for_plan)

    def import_rpms(self, rpms, repo=const.OS_UPDATES_PATH):
        """
            This method will import some RPMs to test the upgrade process.
            Kernel upgrades require the node to be rebooted after the package
            is installed so we support with and without kernel packages.
        """
        rpms_local_paths = []
        rpms_remote_paths = []
        # Reusing existing RPMs
        rpm_remote_dir = '/tmp/story12927'
        dir_to_import = rpm_remote_dir + "/rpm_to_import"
        rpm_local_dir = "12927_rpms/"
        for rpm in rpms:
            rpms_local_paths.append(os.path.join(
                os.path.dirname(__file__), rpm_local_dir + rpm))

            rpms_remote_paths.append(os.path.join(dir_to_import, rpm))

        # Select RPM packages to upgrade
        local_file_paths = rpms_local_paths

        # Create directory for RPMs to import. If it exists,
        # remove it and create it again
        self.create_dir_on_node(self.ms1, rpm_remote_dir)
        if self.remote_path_exists(self.ms1, dir_to_import, expect_file=False):
            self.assertTrue(self.remove_item(self.ms1, dir_to_import))

        self.create_dir_on_node(self.ms1, dir_to_import)

        # Copy RPMs into /tmp on the MS
        for loc_path in local_file_paths:
            self.assertTrue(
                self.copy_file_to(self.ms1, loc_path, dir_to_import))

        # Import them with LITP import cmd into update repo
        self.execute_cli_import_cmd(self.ms1, dir_to_import, repo)

    def cleanup_repos(self, nodes, rpm_list, repo_path):
        """
        This method downgrades packages to previous version and
        cleans up yum repos after running tests.
        """
        all_nodes = nodes + [self.ms1]
        self.run_command(self.ms1, self.cmd_puppet_disable,
                         default_asserts=True, su_root=True)

        # Remove RPMs from the yum repository on MS
        for rpm in rpm_list:
            self.log("info",
                     "Removing: {0} from repo: {1}".format(rpm, repo_path))
            repo_to_rm = repo_path + '/' + rpm
            self.remove_item(self.ms1, repo_to_rm, su_root=True)

        # Update the yum repository
        cmd = "/usr/bin/createrepo --update " + repo_path
        self.run_command(self.ms1, cmd, su_root=True, su_timeout_secs=120)

        # Clean the yum cache
        cmd = self.rhcmd.get_yum_cmd("clean all")
        for node in all_nodes:
            self.run_command(node, cmd, su_root=True)

        # Uninstall test packages
        for node in nodes:
            for package in rpm_list:
                pkg = package.split("-")[0]
                cmd = "/bin/rpm -e " + pkg
                self.run_command(node, cmd, su_root=True)

    def restore_MS_snapshot(self, nodes):
        """ Restore LITP snapshot on MS manually """
        self.log("info", "Disable puppet on nodes.")
        for node in nodes:
            self.run_command(node, self.cmd_puppet_disable,
                             default_asserts=True, su_root=True)

        self.log("info", "Restore snapshot on MS.")
        cmd = "/bin/ls -1 {0}L_*".format(const.LITP_SNAPSHOT_PATH)
        snaps = self.run_command(self.ms1, cmd, default_asserts=True)[0]
        for snap in snaps:
            cmd = "/sbin/lvconvert --merge {0}".format(snap)
            self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log("info", "Reboot MS.")
        cmd = "(sleep 1; {0} -r now) &".format(const.SHUTDOWN_PATH)
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

        self.log("info", "Wait for the MS node to become unreachable.")
        ms_ip = self.get_node_att(self.ms1, 'ipv4')
        self.assertTrue(self.wait_for_ping(ms_ip, False, self.timeout_mins),
                        "Node has not gone down")

        self.log("info", "Wipe active SSH connections to force a reconnect.")
        self.disconnect_all_nodes()

        self.log("info", "Wait for MS to be reachable again after reboot.")
        self.wait_for_node_up(self.ms1)

        self.log("info", "Wait for litpd service to be running.")
        cmd = self.rhc.get_service_running_cmd('litpd')
        self.assertTrue(self.wait_for_cmd(self.ms1, cmd, 0, timeout_mins=5),
                        "litpd service is not online")

        self.log("info", "Wait for snapshot to merge.")
        cmd = "/sbin/lvs | /bin/awk '{print $3}' | /bin/grep 'Owi'"
        self.assertTrue(self.wait_for_cmd(
            self.ms1, cmd, 1, timeout_mins=self.timeout_mins, su_root=True))

    def restore_litp_backup(self, backup_path):
        """ Restore LITP backup """
        self.log("info", "Stop litpd service.")
        self.stop_service(self.ms1, "litpd")

        self.log("info", "Disable puppet on MS.")
        self.run_command(self.ms1, self.cmd_puppet_disable,
                         default_asserts=True, su_root=True)

        self.log("info", "Copy back the backup file from gateway to the MS.")
        self.copy_file_to(self.ms1, backup_path, "/tmp/")

        self.log("info", "Restore the backup file.")
        self.run_restore_script("/tmp/{0}".format(backup_path.split("/")[-1]))

        self.log("info", "Start litpd service.")
        self.start_service(self.ms1, "litpd")

        self.log("info", "Enable puppet on MS.")
        self.run_command(self.ms1, self.cmd_puppet_enable,
                         default_asserts=True, su_root=True)

    def run_backup_script(self):
        """
            Runs the backup script. In case of errors, retries 3 times.
        """
        if not self.remote_path_exists(
                self.ms1, self.backup_dir, expect_file=False):
            self.create_dir_on_node(self.ms1, self.backup_dir)

        cmd = "{0} {1}".format(self.backup_script, self.backup_dir)
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

    def run_restore_script(self, backup):
        """
            Runs the restore script to restore backup
            archive specified by backup argument.
        """
        cmd = "{0} {1}".format(self.restore_script, backup)
        self.run_command(self.ms1, cmd, su_root=True, default_asserts=True)

    def list_backups(self, folder=None):
        """
            Lists files in folder on MS (by default /tmp/litp_backup/)
        """
        if not folder:
            folder = self.backup_dir
        cmd = "/bin/ls -1t {0}".format(folder)
        bkp_files = self.run_command(self.ms1, cmd, default_asserts=True)[0]
        return bkp_files

    def verify_backup_is_created(
            self, backup_files, expect_created=True, compare=True):
        """
            Runs the backup script.
            If compare is set to True (default), verifies that a backup has
            been created and compares it to the expect_created parameter.

            Returns a directory listing of the backup directory.
        """
        self.run_backup_script()
        curr_backup_files = self.list_backups()
        if compare:
            # Verify backup file was(n't) created
            if expect_created:
                self.assertNotEqual(curr_backup_files, backup_files)
            else:
                self.assertEqual(curr_backup_files, backup_files)
        return curr_backup_files

    @attr('all', 'revert', 'story138482', 'story138482_tc01', 'bur_only_test')
    def test_01_p_restore_with_valid_DB_dump(self):
        """
            @tms_id: torf_138482_tc01
            @tms_requirements_id: TORF-138482
            @tms_title: Verify restore backup procedure
            @tms_description:
                Verify that when the MS is restored to a state before the last
                successful plan run (e.g. package install plan) and the backup
                was taken at a time when no plan was running, when the backed
                up files are put back in place, then the system is functional.
            @tms_test_steps:
                @step: Run backup script
                @result: Backup archive created
                @step: Create snapshot
                @result: Snapshot created
                @step: Run backup script
                @result: Second backup archive created
                @step: Install "nano" package
                @result: Package successfully installed
                @step: Run backup script and copy archive to gateway
                @result: Another backup archive created and copied
                @step: Restore LITP snapshot on MS
                @result: Snapshot restored
                @result: Package "nano" not present
                @step: Restore LITP backup
                @result: Backup restored
                @step: Run a puppet cycle
                @result: Package "nano" installed
                @step: Enable puppet on nodes
                @result: Puppet enabled
            @tms_test_precondition: N/A
            @tms_execution_type: Automated
        """
        try:
            self.log("info", "#1. Run backup script.")
            backup_file = self.verify_backup_is_created(None)

            self.log("info", "#2. Create snapshot.")
            self.execute_and_wait_createsnapshot(self.ms1)

            self.log("info", "#3. Run backup script again.")
            backup_file = self.verify_backup_is_created(backup_file)

            self.log("info", "#4. Install package 'nano'.")
            self.create_package_item()

            self.log("info", "#5. Run backup script.")
            backup_file = self.verify_backup_is_created(backup_file)

            self.log("info", "#6. Copy the backup to the gateway.")
            local_dir = os.path.dirname(__file__)
            backup_file_name = backup_file[0].split("/")[-1]
            remote_filepath = "{0}{1}".format(self.backup_dir, backup_file[0])
            local_filepath = "{0}/{1}".format(local_dir, backup_file_name)
            self.download_file_from_node(self.ms1, remote_filepath,
                                          local_filepath, root_copy=True)

            self.log("info", "#7. Restore LITP snapshot on MS.")
            self.restore_MS_snapshot(self.mns)

            self.log("info", "#8. Check package 'nano' is not installed.")
            self.assertFalse(self.check_pkgs_installed(self.ms1, ["nano"]))

            self.log("info", "#9. Restore LITP backup.")
            self.restore_litp_backup(local_filepath)

            self.log("info", "#10. Run a puppet cycle and verify package "
                             "'nano' is installed")
            self.wait_for_puppet_idle(self.ms1)
            self.run_puppet_once(self.ms1)
            self.wait_for_puppet_action(self.ms1, self.ms1,
                check_cmd='{0} -qa | {1} "nano"'.format(
                const.RPM_PATH, const.GREP_PATH), expected_rc=0)

            self.log("info", "#11. Enable puppet on nodes.")
            for node in self.mns:
                self.run_command(node, self.cmd_puppet_enable,
                   default_asserts=True, su_root=True)
        finally:
            self.start_service(self.ms1, "litpd")
            for node in self.mns + [self.ms1]:
                self.run_command(node, self.cmd_puppet_enable,
                    default_asserts=True, su_root=True)

    @attr('all', 'revert', 'story138482', 'story138482_tc03', 'expansion')
    def test_03_p_restore_expansion(self):
        """
            @tms_id: torf_138482_tc03
            @tms_requirements_id: TORF-138482
            @tms_title: Restore backup taken while plan incomplete.
            @tms_description:
                Verify that when the MS is restored to a state before the last
                successful plan run and the last backup was taken right after
                a node has been successfully applied and the plan stopped,
                and the backed up files are put back in place, then the system
                functions as required and when a plan is created again the node
                finishes installation successfully.
            @tms_test_steps:
                @step: Create snapshot
                @result: Snapshot created successfully
                @step: Execute the expand script for
                    expanding cluster 1 with node2
                @result: Node added to cluster
                @step: Create and run plan
                @result: Plan is created and runs successfully
                @step: Wait for the new node to be in state "Applied"
                @result: Node applied
                @step: Stop plan
                @result: Plan stops
                @step: Create backup archive and copy it to gateway
                @result: Backup archive created
                @step: Restore snapshot on the MS
                @result: Snapshot restores successfully
                @step: Restore LITP backup
                @result: Backup restored successfully
                @step: Enable puppet on node1
                @result: Puppet enabled
                @step: Create and run plan
                @result: Plan runs to success
                @step: Remove snapshot
                @result: Snapshot removed
                @step: Create snapshot
                @result: Snapshot created
                @step: Restore snapshot
                @result: Snapshot restored
                @step: Return environment back to 1 cluster/1 node
                @result: Added node successfully removed
            @tms_test_precondition: one node system
            @tms_execution_type: Automated
        """
        self.log("info", "#1. Create Snapshot.")
        self.execute_and_wait_createsnapshot(self.ms1, add_to_cleanup=False)

        self.log("info", "#2. Execute expansion script for "
                         "expanding cluster1 with node2.")
        self.execute_expand_script(self.ms1, 'expand_cloud_c1_mn2.sh',
                        cluster_filename='RHEL7_192.168.0.42_4node.sh')

        timeout_mins = 60
        self.log("info", "#3. Create and run plan.")
        self.execute_cli_createplan_cmd(self.ms1)
        self.execute_cli_runplan_cmd(self.ms1, add_to_cleanup=False)

        # At this point, the node is already in Applied state so
        # next time the plan is recreated, it will not run from
        # the very top and it will take less time to complete
        wait_task = 'Lock VCS on node "{0}"'.format(self.mns[0])
        self.assertTrue(self.wait_for_task_state(self.ms1, wait_task,
                                                 const.PLAN_TASKS_SUCCESS,
                                                 ignore_variables=False,
                                                 timeout_mins=timeout_mins))

        self.log("info", "#4. Stop plan once node is applied.")
        self.execute_cli_stopplan_cmd(self.ms1)

        self.log("info", "#5. Run backup script.")
        self.run_backup_script()

        cmd_list_backup_dir = "/bin/ls -1t {0}".format(self.backup_dir)
        backup_file, _, _ = self.run_command(self.ms1, cmd_list_backup_dir,
                                             default_asserts=True)
        self.assertTrue(1 == len(backup_file))

        self.log("info", "#6. Copy the backup to the gateway.")
        local_dir = os.path.dirname(__file__)
        backup_file_name = backup_file[0].split("/")[-1]
        remote_filepath = "{0}{1}".format(self.backup_dir, backup_file[0])
        local_filepath = "{0}/{1}".format(local_dir, backup_file_name)
        self.download_file_from_node(self.ms1, remote_filepath,
                                     local_filepath, root_copy=True)

        self.log("info", "#7. Restore LITP snapshot on MS.")
        self.restore_MS_snapshot([self.mns[0]])

        self.log("info", "#8. Restore LITP backup.")
        self.restore_litp_backup(local_filepath)

        self.log("info", "#9. Enable puppet on node1.")
        cmd = "/usr/bin/puppet agent --enable"
        self.run_command(self.mns[0], cmd, default_asserts=True, su_root=True)

        self.log("info", "#10. Create and run plan.")
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)

        self.log("info", "#11. Verify snapshot can be removed.")
        self.execute_and_wait_removesnapshot(self.ms1, add_to_cleanup=False)

        self.log("info", "#12. Verify snapshot can be created.")
        self.execute_and_wait_createsnapshot(self.ms1, add_to_cleanup=False)

        self.log("info", "#13. Verify snapshot can be restored.")
        self.execute_and_wait_restore_snapshot(self.ms1)

        self.log("info", "#14. Return environment back to 1 cluster/1 node.")
        node2 = self.get_managed_node_filenames()[1]
        node2_url = self.find(self.ms1, '/deployments', 'node')[1]
        node2_url_sys = self.find(self.ms1, node2_url, 'reference-to-blade')[0]
        # Find inherited system path of node2
        inherited_sys = self.execute_show_data_cmd(
            self.ms1, node2_url_sys, filter_value='inherited from')

        self.log("info", "#14.1. Set passwords on restored node.")
        self.assertTrue(self.set_pws_new_node(self.ms1, node2),
                        "Failed to set passwords on restored node.")

        self.log("info", "#14.2. Log onto restored node"
                         " and stop VCS running on it.")
        stop_vcs_cmd = self.vcs.get_hastop_force('-local')
        _, stderr, rc = self.run_command(node2, stop_vcs_cmd, su_root=True)
        self.assertEqual(0, rc)
        self.assertEqual([], stderr)

        self.log("info", "#14.3. Remove restored node"
                         " and its inherited system.")
        self.execute_cli_remove_cmd(self.ms1, node2_url)
        self.execute_cli_remove_cmd(self.ms1, inherited_sys)
        self.log("info", "#14.4. Create and run plan to remove node.")
        self.run_and_check_plan(self.ms1, const.PLAN_COMPLETE,
                                timeout_mins, add_to_cleanup=False)
