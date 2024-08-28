# -*- coding: utf-8 -*-
# coding: utf-8

"""
COPYRIGHT Ericsson 2019
The copyright to the computer program(s) herein is the property of
Ericsson Inc. The programs may be used and/or copied only with written
permission from Ericsson Inc. or in accordance with the terms and
conditions stipulated in the agreement/contract under which the
program(s) have been supplied.

@since:     June 2015
@author:    Jose Martinez
@summary:   Integration test for story 6915: As a packager of LITP when I build
            an ISO via LITP_iso repo then the ISO structure should reflect the
            LITP Compliant ISO structure
            Agile: STORY-6915
"""

from litp_generic_test import GenericTest, attr
from litp_cli_utils import CLIUtils
import os
import re
import sys
import socket
import exceptions
import time
from redhat_cmd_utils import RHCmdUtils
import test_constants


class Story6915(GenericTest):
    """
    Description:
        When I build an ISO via LITP_iso repo then the ISO structure should
        reflect the LITP Compliant ISO structure
    """
    def setUp(self):
        """ Setup variables for every test """
        super(Story6915, self).setUp()
        self.ms_node = self.get_management_node_filename()
        self.mn_nodes = self.get_managed_node_filenames()
        self.cli = CLIUtils()
        self.rhcmd = RHCmdUtils()
        self.iso_remote_path = "/tmp/story6915/"
        self.plan_timeout_mins = 10

    def tearDown(self):
        """ Called after every test"""
        super(Story6915, self).tearDown()

    def _package_imported(self, rpm_list, repo):
        """ Check if rpms are in repo."""
        repo_base_dir = test_constants.PARENT_PKG_REPO_DIR
        repo_dir = os.path.join(repo_base_dir, repo)

        for rpm in rpm_list:
            rpm_path = os.path.join(repo_dir, rpm)
            self.assertTrue(self.remote_path_exists(self.ms_node, rpm_path))

    @classmethod
    def _ii_done_msg(cls, msg_log_strs):
        """
        Determine if there is a message in the message log saying that the
        import_iso command is done.
        Args:
           msg_log_strs (list of strings):  Message log as a list of strings.

        Returns:
          Bool : Whether import_iso done message was found.
          ret_code:  (str) The exit code that import_iso reported.
        """
        ret_code = None
        for text_str in msg_log_strs:
            if text_str:
                sreg = ("ISO Importer exiting with (\\d+)")
                reg = re.compile(sreg, re.DOTALL)
                reg_match = reg.search(str(text_str))
                if reg_match:
                    ret_code = reg_match.group(1)
                    return True, ret_code
        return False, ret_code

    def _verify_packages_upgraded(self, rpm_list):
        """ Verify that rpms are upgraded in MS"""
        for rpm in rpm_list:
            cmd_rpm_info = "rpm -qp --qf '%{name} %{version}' " + rpm
            rpm_info, err, rc = self.run_command(self.ms_node, cmd_rpm_info)
            self.assertEqual(0, rc)
            self.assertEqual([], err)

            rpm_name, rpm_ver = rpm_info[0].split(" ")
            cmd_pkg_info = "rpm -qa --qf '%{version}' " + rpm_name
            pkg_info, err, rc = self.run_command(self.ms_node, cmd_pkg_info)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            if len(pkg_info):
                pkg_ver = pkg_info[0]
                self.assertEqual(rpm_ver, pkg_ver,
                                 "Version does not match in package" +
                                  rpm_name)

    def _set_litp_mmode(self, enable=True):
        """ Set the maintenance mode of litp. Defaults to enabling it. """
        if enable:
            prop_val = "enabled=true"
        else:
            prop_val = "enabled=false"
        self.execute_cli_update_cmd(self.ms_node,
                                    '/litp/maintenance',
                                    prop_val)

    def _snapshot_item_exists(self):
        """
        Description:
            Determine if a snapshot item exists in the model.
        Results:
            Boolean, True if exists or False otherwise
         """
        snapshot_url = self.find(self.ms_node, "/snapshots",
                              "snapshot-base", assert_not_empty=False)
        if snapshot_url:
            return True
        else:
            return False

    def create_snapshot(self):
        """
        Create the snapshot
        """
        #1. If snapshot exists, remove it
        if self._snapshot_item_exists():
            self.execute_cli_removesnapshot_cmd(self.ms_node)

            # 1.b Verify that the remove snapshot plan succeeds.
            self.assertTrue(self.wait_for_plan_state(self.ms_node,
                test_constants.PLAN_COMPLETE, self.plan_timeout_mins))

        # 2. Execute create_snapshot command
        self.execute_cli_createsnapshot_cmd(self.ms_node)

        # 2.b Verify that the create snapshot plan succeeds
        self.assertTrue(self.wait_for_plan_state(self.ms_node,
                test_constants.PLAN_COMPLETE, self.plan_timeout_mins))

    def _verify_restore_snapshot_completes(self):
        """
            verify restore snapshot completes
        """
        self.assertTrue(self._node_rebooted(self.ms_node))
        self.assertTrue(self._litp_up())
        self.assertTrue(self._m_nodes_up())

    def _up_time(self, node):
        """
            Return uptime of node
        """
        cmd = self.rhcmd.get_cat_cmd('/proc/uptime')
        out, err, ret_code = self.run_command(node, cmd, su_root=True)
        self.assertEqual(0, ret_code)
        self.assertEqual([], err)
        self.assertNotEqual([], out)
        uptime_seconds = float(out[0].split()[0])
        return uptime_seconds

    def _node_rebooted(self, node):
        """
            Verify that a node  has rebooted.
        """
        node_restarted = False
        max_duration = 1800
        elapsed_sec = 0
        # uptime before reboot
        up_time_br = self._up_time(node)
        while elapsed_sec < max_duration:
            #if True:
            try:
                # uptime after reboot
                up_time_ar = self._up_time(node)
                self.log("info", "{0} is up for {1} seconds"
                         .format(node, str(up_time_ar)))

                if up_time_ar < up_time_br:
                    self.log("info", "{0} has been rebooted"
                             .format(node))
                    node_restarted = True
                    break
            except (socket.error, exceptions.AssertionError):
                self.log("info", "{0} is not up at the moment"
                         .format(node))
            except:
                self.log("error", "Reboot check. Unexpected Exception: {0}"
                         .format(sys.exc_info()[0]))
                self.disconnect_all_nodes()

            time.sleep(10)
            elapsed_sec += 10

        if not node_restarted:
            self.log("error", "{0} not rebooted in last {1} seconds."
                     .format(node, str(max_duration)))
        return node_restarted

    def _litp_up(self):
        """
            Verify that the MS has a working litp instance
        """
        litp_up = False
        max_duration = 300
        elapsed_sec = 0

        while elapsed_sec < max_duration:

            try:
                out, err, _ = self.get_service_status(self.ms_node,
                                                       'litpd',
                                                       assert_running=False)
                self.assertEqual([], err)

                if self.is_text_in_list("is running", out):
                    self.log("info", "Litp is up")
                    litp_up = True
                    break
                else:
                    self.log("info", "Litp is not up.")

            except (socket.error, exceptions.AssertionError):
                self.log("info", "Litp is not up after {0} seconds"
                         .format(elapsed_sec))
            except:
                self.log("error", "Unexpected Exception: {0}"
                         .format(sys.exc_info()[0]))

            time.sleep(10)
            elapsed_sec += 10

        if not litp_up:
            self.log("error", "Litp is not up in last {0} seconds."
                     .format(str(max_duration)))
        return litp_up

    def _m_nodes_up(self):
        """
            Verify that the MN node is up
        """
        m_nodes_up = False
        max_duration = 300
        elapsed_sec = 0
        cmd = "/bin/hostname"
        while elapsed_sec < max_duration:
            try:
                #for node in self.mn_nodes:
                node = self.mn_nodes[0]
                _, _, ret_code = self.run_command(node, cmd)
                self.assertEqual(0, ret_code)
                if ret_code == 0:
                    m_nodes_up = True
                    break
                else:
                    self.log("info", "Node {0} is not up in last {1} seconds."
                          .format(node, elapsed_sec))
            except (socket.error, exceptions.AssertionError):
                self.log("info", "Litp is not up after {0} seconds"
                         .format(elapsed_sec))
            except:
                self.log("error", "Unexpected Exception: {0}"
                         .format(sys.exc_info()[0]))

            time.sleep(10)
            elapsed_sec += 10

        if not m_nodes_up:
            self.log("error", "Node {0} is not up in last {1} seconds."
                     .format(node, str(max_duration)))

        return m_nodes_up

    @attr('manual-test', 'revert', 'story6915', 'story6915_tc01')
    def test_01_p_installer_script_installs_LITP_successfully(self):
        """
        Description:
            This test will verify that when user runs the installer.sh script
            LITP will be installed on the MS successfully
        Actions:
            1. Mount an ISO
            2. Run installer.sh
            3. Verify LITP is installed successfully
            4. Unmount ISO

        Result:
            LITP is installed in MS

        MANUAL
        """

    @attr('manual-test', 'revert', 'story6915', 'story6915_tc02')
    def test_02_p_litp_import_3pp_and_litp_succeeds(self):
        """
        Description:
            This test will verify that when user runs litp import in 3pp and
            litp repos the packages are imported successfully
        Actions:
            1. copy rpms to MS
            1. import package into 3pp repo
            2. import package into litp repo
            3. Verify packages are imported

        Result:
            rpms are imported into litp and 3pp

        MANUAL
        """

    @attr('manual-test', 'revert', 'story6915', 'story6915_tc03')
    def test_03_p_import_iso_updates_plugins_and_3pp(self):
        """
        Description:
            This test will verify that when user runs import_iso the litp
            packages are upgraded
        Actions:
            1. Create snapshot
            2. Mount an ISO
            3. Call 'litp import_iso' on a directory.
            4. Wait for import to complete.
            5. Verify packages were upgraded on MS
            6. Restore snapshot

        Result:
            LITP packages are upgraded in MS
        """

        # ISO to be imported
        # Change 'iso' with the name of the downloaded and copied iso to
        # the 6915_isos/iso_dir_03/
        iso = "ERIClitp_CXP9024296-2.23.36.iso"
        iso_local = os.path.join(os.path.dirname(__file__), "6915_isos/")
        iso_local = os.path.join(iso_local, "iso_dir_03")
        iso_local = os.path.join(iso_local, iso)

        iso_remote = self.iso_remote_path

        mount_point = "/mnt/"

        try:

            self.log("info", "# 1. Create snapshot.")
            self.create_snapshot()

            self.log("info", "# 2. Mount an ISO")
            # copy iso file to remote
            self.create_dir_on_node(self.ms_node, self.iso_remote_path)
            self.assertTrue(self.copy_file_to(self.ms_node,
                                              iso_local,
                                              iso_remote))
            # mount iso file
            cmd_mount = "mount -o loop " + iso_remote + iso + " " + mount_point
            out, err, rc = self.run_command(self.ms_node,
                                            cmd_mount,
                                            su_root=True)
            self.assertEqual(0, rc)
            self.assertEqual([], err)
            self.assertEqual([], out)

            self.log("info", "# 3. Call 'litp import_iso' on a directory.")
            self.execute_cli_import_iso_cmd(self.ms_node, mount_point)

            self.log("info", "# 4. Wait for import to complete.")
            self.assertTrue(self.wait_for_log_msg(self.ms_node,
                                "Importer is finished, exiting with 0"))

            self.log("info", "# 5. Verify packages were upgraded on MS.")
            cmd_rpm_list = "find {0} -type f | grep 'E.*litp.*rpm$'".\
                           format(mount_point)
            rpm_list, err, rc = self.run_command(self.ms_node, cmd_rpm_list)
            self.assertEqual(0, rc)
            self.assertEqual([], err)

            self._verify_packages_upgraded(rpm_list)

        finally:

            self._set_litp_mmode(False)

            self.log("info", "# 6. Restore snapshot.")
            cmd_restore = self.cli.get_restore_snapshot_cmd()
            self.run_command(self.ms_node, cmd_restore)

            self._verify_restore_snapshot_completes()
